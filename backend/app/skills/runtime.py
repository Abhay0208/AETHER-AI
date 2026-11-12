"""AETHER skills runtime.

Executes installed skills in a controlled, permission-gated context.

A skill is a Python module (entry_point) with a ``run(function_name, params, ctx)``
function. The ``ctx`` object provides only the capabilities the skill has been
granted (file_read, file_write, model_chat, skill_call), so skills never receive
unrestricted access to the operating system.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import FILES_DIR, SKILLS_DIR, PROJECT_ROOT
from ..database import transaction
from ..gateway import UnifiedGateway
from ..providers.registry import ProviderAdapterRegistry


class SkillError(Exception):
    """Raised when a skill execution fails."""


class SkillPermissionError(SkillError):
    """Raised when a skill attempts an operation it has no permission for."""


class _SkillContext:
    """Controlled execution context passed to a skill's run() function."""

    def __init__(self, runtime: "SkillRuntime", skill_name: str, permissions: list[str]):
        self._runtime = runtime
        self.skill_name = skill_name
        self._permissions = set(permissions)
        self.files = _FileAccess(runtime, self._permissions)
        self.model = _ModelAccess(runtime, self._permissions)
        self.skills = _SkillAccess(runtime, self._permissions)

    def has(self, permission: str) -> bool:
        return permission in self._permissions


class _FileAccess:
    def __init__(self, runtime: "SkillRuntime", permissions: set[str]):
        self._runtime = runtime
        self._permissions = permissions

    def read(self, path: str) -> dict:
        if "file_read" not in self._permissions:
            raise SkillPermissionError("skill lacks file_read permission")
        return self._runtime._file_read(path)

    def write(self, path: str, content: str) -> dict:
        if "file_write" not in self._permissions:
            raise SkillPermissionError("skill lacks file_write permission")
        return self._runtime._file_write(path, content)


class _ModelAccess:
    def __init__(self, runtime: "SkillRuntime", permissions: set[str]):
        self._runtime = runtime
        self._permissions = permissions

    def chat(self, messages: list[dict], model: str | None = None) -> dict:
        if "model_chat" not in self._permissions:
            raise SkillPermissionError("skill lacks model_chat permission")
        return self._runtime._model_chat(messages, model)


class _SkillAccess:
    def __init__(self, runtime: "SkillRuntime", permissions: set[str]):
        self._runtime = runtime
        self._permissions = permissions

    def call(self, skill_name: str, function_name: str, params: dict) -> dict:
        if "skill_call" not in self._permissions:
            raise SkillPermissionError("skill lacks skill_call permission")
        return self._runtime.execute_skill(skill_name, function_name, params)


class SkillRuntime:
    def __init__(self, gateway: UnifiedGateway | None = None):
        self.gateway = gateway or UnifiedGateway(ProviderAdapterRegistry())
        self._skill_modules: dict[str, types.ModuleType] = {}

    # ------------------------------------------------------------------
    # Skill discovery / listing
    # ------------------------------------------------------------------
    def list_skills(self) -> list[dict]:
        with transaction() as conn:
            rows = conn.execute(
                """
                SELECT id, name, display_name, version, description, category, author,
                       source, source_url, entry_point, manifest, permissions,
                       dependencies, is_installed, is_enabled, is_builtin, installed_at
                FROM skills ORDER BY category, name
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def get_skill(self, skill_id: int) -> dict | None:
        with transaction() as conn:
            row = conn.execute(
                "SELECT * FROM skills WHERE id = ?", (skill_id,)
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Install / enable / disable / uninstall
    # ------------------------------------------------------------------
    def install_skill(self, manifest: dict, entry_point_code: str | None = None,
                      source: str = "local", source_url: str | None = None) -> dict:
        """Install a skill from a manifest + optional entry point source."""
        name = manifest["name"]
        version = manifest.get("version", "1.0.0")
        with transaction() as conn:
            existing = conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()
            if existing:
                raise SkillError(f"Skill '{name}' already installed")
            permissions = json.dumps(manifest.get("permissions", []))
            dependencies = json.dumps(manifest.get("dependencies", []))
            manifest_json = json.dumps(manifest)
            now = datetime.now(timezone.utc).isoformat()
            cur = conn.execute(
                """INSERT INTO skills
                   (name, display_name, version, description, category, author, source,
                    source_url, entry_point, manifest, permissions, dependencies,
                   is_installed, is_enabled, is_builtin, installed_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, manifest.get("display_name", name), version,
                 manifest.get("description", ""), manifest.get("category", "Uncategorized"),
                 manifest.get("author", ""), source, source_url,
                 manifest.get("entry_point", "skill.py"), manifest_json,
                 permissions, dependencies, 1, 0, 0, now, now),
            )
            skill_id = cur.lastrowid

        # Write entry point file if provided.
        if entry_point_code:
            self._write_entry_point(name, entry_point_code)

        return self.get_skill(skill_id)

    def enable_skill(self, skill_id: int) -> dict:
        with transaction() as conn:
            row = conn.execute("SELECT id, is_builtin FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if row is None:
                raise SkillError(f"Skill id {skill_id} not found")
            conn.execute("UPDATE skills SET is_enabled = 1 WHERE id = ?", (skill_id,))
        return self.get_skill(skill_id)

    def disable_skill(self, skill_id: int) -> dict:
        with transaction() as conn:
            row = conn.execute("SELECT id, is_builtin FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if row is None:
                raise SkillError(f"Skill id {skill_id} not found")
            if row["is_builtin"]:
                raise SkillError("Built-in skills cannot be disabled")
            conn.execute("UPDATE skills SET is_enabled = 0 WHERE id = ?", (skill_id,))
        return self.get_skill(skill_id)

    def uninstall_skill(self, skill_id: int) -> dict:
        with transaction() as conn:
            row = conn.execute("SELECT name, is_builtin FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if row is None:
                raise SkillError(f"Skill id {skill_id} not found")
            if row["is_builtin"]:
                raise SkillError("Built-in skills cannot be uninstalled")
            conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        return {"ok": True, "name": row["name"]}

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute_skill(self, skill_name: str, function_name: str,
                      params: dict | None = None, user_id: int | None = None) -> dict:
        """Execute a skill function. Returns the skill's result dict."""
        params = params or {}
        with transaction() as conn:
            row = conn.execute(
                "SELECT * FROM skills WHERE name = ? AND is_installed = 1 AND is_enabled = 1",
                (skill_name,),
            ).fetchone()
        if row is None:
            raise SkillError(f"Skill '{skill_name}' is not installed or enabled")
        skill = dict(row)

        # Log execution start.
        exec_id = None
        with transaction() as conn:
            cur = conn.execute(
                """INSERT INTO skill_executions (skill_id, function_name, status, input)
                   VALUES (?, ?, 'running', ?)""",
                (skill["id"], function_name, json.dumps(params)),
            )
            exec_id = cur.lastrowid

        try:
            result = self._run_skill(skill, function_name, params)
            status = "completed"
            output = json.dumps(result) if not isinstance(result, str) else result
            error = None
        except Exception as exc:
            status = "failed"
            output = None
            error = str(exc)
            result = {"ok": False, "error": error}

        # Log execution completion.
        with transaction() as conn:
            conn.execute(
                """UPDATE skill_executions
                   SET status = ?, output = ?, error = ?, completed_at = datetime('now')
                   WHERE id = ?""",
                (status, output, error, exec_id),
            )

        result["_execution_id"] = exec_id
        return result

    def _run_skill(self, skill: dict, function_name: str, params: dict) -> dict:
        module = self._load_skill_module(skill)
        if not hasattr(module, "run"):
            raise SkillError(f"Skill '{skill['name']}' has no run() function")

        permissions = json.loads(skill["permissions"] or "[]")
        ctx = _SkillContext(self, skill["name"], permissions)

        # Call the skill's run() in a restricted way.
        return module.run(function_name, params, ctx)

    def _load_skill_module(self, skill: dict) -> types.ModuleType:
        skill_id = skill["id"]
        if skill_id in self._skill_modules:
            return self._skill_modules[skill_id]

        entry_point = skill["entry_point"] or "skill.py"
        # Resolve the skill file: builtin skills live in skills/builtin/ (project)
        # and data/storage/skills/builtin/ (runtime), user skills in skills/user/.
        candidates = [
            os.path.join(PROJECT_ROOT, "skills", "builtin", entry_point),
            os.path.join(SKILLS_DIR, "builtin", entry_point),
            os.path.join(SKILLS_DIR, "user", f"{skill['name']}.py"),
            os.path.join(PROJECT_ROOT, "skills", entry_point),
        ]
        path = None
        for c in candidates:
            if os.path.isfile(c):
                path = c
                break
        if path is None:
            raise SkillError(f"Skill entry point not found: {entry_point}")

        spec = importlib.util.spec_from_file_location(f"aether_skill_{skill_id}", path)
        module = importlib.util.module_from_spec(spec)
        # Restrict the module's builtins to a safe subset.
        safe_builtins = {
            "len": len, "str": str, "int": int, "float": float, "bool": bool,
            "list": list, "dict": dict, "tuple": tuple, "set": set,
            "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
            "sorted": sorted, "reversed": reversed, "enumerate": enumerate,
            "zip": zip, "range": range, "isinstance": isinstance, "issubclass": issubclass,
            "type": type, "hasattr": hasattr, "getattr": getattr, "setattr": setattr,
            "print": print,
        }
        module.__dict__["__builtins__"] = safe_builtins
        module.__dict__["__name__"] = f"aether_skill_{skill_id}"
        spec.loader.exec_module(module)
        self._skill_modules[skill_id] = module
        return module

    # ------------------------------------------------------------------
    # Controlled operations exposed via ctx
    # ------------------------------------------------------------------
    def _file_read(self, path: str) -> dict:
        from ..main import _safe_join  # local import to avoid circularity
        abs_path = _safe_join(FILES_DIR, path)
        if not os.path.isfile(abs_path):
            raise SkillError(f"File not found: {path}")
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"ok": True, "path": path, "content": content}

    def _file_write(self, path: str, content: str) -> dict:
        from ..main import _safe_join
        abs_path = _safe_join(FILES_DIR, path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": path, "bytes": len(content.encode())}

    def _model_chat(self, messages: list[dict], model: str | None = None) -> dict:
        if not model:
            raise SkillError("model_chat requires a model")
        kind, result = self.gateway.chat_completions(
            model=model, messages=messages, stream=False,
        )
        if kind != "response":
            raise SkillError("streaming not supported in skill model_chat")
        return result.to_dict()

    # ------------------------------------------------------------------
    # Execution logs
    # ------------------------------------------------------------------
    def list_executions(self, skill_id: int | None = None, limit: int = 50) -> list[dict]:
        with transaction() as conn:
            if skill_id:
                rows = conn.execute(
                    """SELECT se.*, s.name AS skill_name FROM skill_executions se
                       JOIN skills s ON se.skill_id = s.id
                       WHERE se.skill_id = ? ORDER BY se.started_at DESC LIMIT ?""",
                    (skill_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT se.*, s.name AS skill_name FROM skill_executions se
                       JOIN skills s ON se.skill_id = s.id
                       ORDER BY se.started_at DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]
