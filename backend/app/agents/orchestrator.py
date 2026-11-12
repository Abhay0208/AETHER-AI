"""AETHER autonomous agent orchestrator.

Agents decompose a goal into steps and execute them using available tools:
model chat, skills, file operations, and human-approval gates.

Execution is driven through the existing jobs/agent_tasks tables so tasks
survive UI disconnections and can run in the background.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ..database import transaction
from ..gateway import UnifiedGateway
from ..providers.registry import ProviderAdapterRegistry

# Set by main.py after both modules are loaded (avoids circular import).
skills_runtime = None


class AgentError(Exception):
    """Raised when an agent operation fails."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentOrchestrator:
    def __init__(self, gateway: UnifiedGateway | None = None):
        self.gateway = gateway or UnifiedGateway(ProviderAdapterRegistry())

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------
    def list_agents(self) -> list[dict]:
        with transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM agents ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]

    def create_agent(self, name: str, model: str, system_prompt: str,
                     description: str = "") -> dict:
        with transaction() as conn:
            cur = conn.execute(
                """INSERT INTO agents (name, description, model, system_prompt)
                   VALUES (?, ?, ?, ?)""",
                (name, description, model, system_prompt),
            )
            agent_id = cur.lastrowid
            row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
        return dict(row)

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    def create_task(self, agent_id: int, title: str) -> dict:
        task_id = str(uuid.uuid4())
        with transaction() as conn:
            conn.execute(
                """INSERT INTO agent_tasks (id, agent_id, title, status)
                   VALUES (?, ?, ?, 'queued')""",
                (task_id, agent_id, title),
            )
            row = conn.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row)

    def list_tasks(self, agent_id: int | None = None) -> list[dict]:
        with transaction() as conn:
            if agent_id:
                rows = conn.execute(
                    "SELECT * FROM agent_tasks WHERE agent_id = ? ORDER BY created_at DESC",
                    (agent_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM agent_tasks ORDER BY created_at DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    def get_task(self, task_id: str) -> dict | None:
        with transaction() as conn:
            row = conn.execute(
                "SELECT * FROM agent_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if not row:
            return None
        task = dict(row)
        steps = conn.execute(
            "SELECT * FROM agent_task_steps WHERE task_id = ? ORDER BY step_index",
            (task_id,),
        ).fetchall()
        task["steps"] = [dict(s) for s in steps]
        return task

    def approve_task(self, task_id: str, approver_user_id: int) -> dict:
        """Approve a task awaiting human approval."""
        with transaction() as conn:
            row = conn.execute(
                "SELECT id, status, requires_approval FROM agent_tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            if not row:
                raise AgentError(f"Task {task_id} not found")
            if row["status"] != "awaiting_approval":
                raise AgentError(f"Task {task_id} is not awaiting approval")
            if not row["requires_approval"]:
                raise AgentError(f"Task {task_id} does not require approval")
            conn.execute(
                """UPDATE agent_tasks
                   SET status = 'running', requires_approval = 0,
                       approved_by = ?, approved_at = datetime('now'),
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (approver_user_id, task_id),
            )
        return self.get_task(task_id)

    # ------------------------------------------------------------------
    # Run a task (agent loop)
    # ------------------------------------------------------------------
    def run_task(self, task_id: str, user_id: int | None = None) -> dict:
        """Execute an agent task end-to-end.

        The agent:
          1. Plans (decomposes the goal into steps)
          2. Executes each step (model call / skill call / file op)
          3. Pauses for human approval when a step requires it
          4. Records results and updates progress
        """
        task = self.get_task(task_id)
        if not task:
            raise AgentError(f"Task {task_id} not found")
        if task["status"] not in ("queued", "running"):
            raise AgentError(f"Task {task_id} already {task['status']}")

        agent = None
        if task["agent_id"]:
            with transaction() as conn:
                agent = conn.execute(
                    "SELECT * FROM agents WHERE id = ?", (task["agent_id"],)
                ).fetchone()

        # Mark task running.
        self._set_task_status(task_id, "running")

        try:
            # Step 1: Plan - decompose the goal into steps using the model.
            plan = self._plan(task, agent)
            step_results = []
            for idx, step in enumerate(plan):
                step_id = self._create_step(task_id, idx, step)
                try:
                    result = self._execute_step(step, agent, task, user_id)
                    self._complete_step(step_id, "completed", result)
                    step_results.append(result)
                    self._set_task_progress(task_id, int((idx + 1) / len(plan) * 100))
                except AgentApprovalRequired:
                    self._complete_step(step_id, "awaiting_approval", {"approval_required": True})
                    self._set_task_status(task_id, "awaiting_approval")
                    self._set_task_approval(task_id, True)
                    return self.get_task(task_id)
                except Exception as exc:
                    self._complete_step(step_id, "failed", {"error": str(exc)})
                    self._set_task_status(task_id, "failed")
                    self._set_task_error(task_id, str(exc))
                    return self.get_task(task_id)

            self._set_task_status(task_id, "completed")
            self._set_task_progress(task_id, 100)
            self._set_task_result(task_id, json.dumps(step_results))
            return self.get_task(task_id)

        except AgentError:
            raise
        except Exception as exc:
            self._set_task_status(task_id, "failed")
            self._set_task_error(task_id, str(exc))
            return self.get_task(task_id)

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------
    def _plan(self, task: dict, agent: dict | None) -> list[dict]:
        """Ask the model to decompose the goal into executable steps."""
        model = (agent and agent["model"]) or None
        system_prompt = (agent and agent["system_prompt"]) or (
            "You are an autonomous agent planner. Break the user's goal into "
            "simple, executable steps. Each step has a type: 'think' (reason), "
            "'skill_call' (run a skill), 'file_op' (read/write a file), or "
            "'model_chat' (ask the model). Return a JSON array of steps."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",
             "content": f"Goal: {task['title']}\n\n"
                        f"Available skills: file_reader (read_file), file_writer (write_file), "
                        f"code_generator (generate), web_researcher (research).\n"
                        "Return ONLY a JSON array of steps, each with: type, description, "
                        "and params appropriate to the type."},
        ]
        try:
            kind, result = self.gateway.chat_completions(
                model=model or "mock-model", messages=messages, stream=False,
            )
            content = ""
            if kind == "response":
                content = result.choices[0].message.content or ""
            # Extract JSON array from the response.
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                plan = json.loads(content[start:end + 1])
            else:
                plan = []
        except Exception:
            plan = []

        if not plan:
            # Fallback: single model_chat step.
            plan = [
                {"type": "model_chat", "description": "Respond to the user's request",
                 "params": {"messages": [
                     {"role": "user", "content": task["title"]}
                 ], "model": model}}
            ]
        return plan

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------
    def _execute_step(self, step: dict, agent: dict | None, task: dict,
                      user_id: int | None) -> dict:
        step_type = step.get("type", "think")
        params = step.get("params", {}) or {}

        if step_type == "think":
            return {"ok": True, "reasoning": params.get("reasoning", ""),
                    "conclusion": params.get("conclusion", "")}

        if step_type == "model_chat":
            model = params.get("model") or (agent and agent["model"])
            messages = params.get("messages") or [
                {"role": "user", "content": step.get("description", "")}
            ]
            kind, result = self.gateway.chat_completions(model=model, messages=messages, stream=False)
            if kind != "response":
                raise AgentError("streaming not supported in agent steps")
            return {"ok": True, "response": result.choices[0].message.content}

        if step_type == "skill_call":
            if skills_runtime is None:
                raise AgentError("Skills runtime not available")
            skill_name = params.get("skill")
            function_name = params.get("function", "run")
            skill_params = params.get("params", {})
            result = skills_runtime.execute_skill(
                skill_name, function_name, skill_params, user_id=user_id,
            )
            return {"ok": True, "skill": skill_name, "result": result}

        if step_type == "file_op":
            op = params.get("op")
            if op == "read":
                from ..main import _safe_join
                from ..config import FILES_DIR
                import os
                abs_path = _safe_join(FILES_DIR, params.get("path", ""))
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return {"ok": True, "path": params.get("path"), "content": content}
            elif op == "write":
                from ..main import _safe_join
                from ..config import FILES_DIR
                import os
                abs_path = _safe_join(FILES_DIR, params.get("path", ""))
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(params.get("content", ""))
                return {"ok": True, "path": params.get("path")}
            else:
                raise AgentError(f"Unknown file_op: {op}")

        if step_type == "approve":
            raise AgentApprovalRequired(params.get("reason", "Human approval required"))

        raise AgentError(f"Unknown step type: {step_type}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_step(self, task_id: str, index: int, step: dict) -> int:
        with transaction() as conn:
            cur = conn.execute(
                """INSERT INTO agent_task_steps
                   (task_id, step_index, type, description, input, status)
                   VALUES (?, ?, ?, ?, ?, 'pending')""",
                (task_id, index, step.get("type", "think"),
                 step.get("description", ""), json.dumps(step.get("params", {}))),
            )
            return cur.lastrowid

    def _complete_step(self, step_id: int, status: str, output: Any):
        with transaction() as conn:
            conn.execute(
                """UPDATE agent_task_steps
                   SET status = ?, output = ?, completed_at = datetime('now')
                   WHERE id = ?""",
                (status, json.dumps(output) if not isinstance(output, str) else output, step_id),
            )

    def _set_task_status(self, task_id: str, status: str):
        with transaction() as conn:
            conn.execute(
                "UPDATE agent_tasks SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (status, task_id),
            )

    def _set_task_progress(self, task_id: str, progress: int):
        with transaction() as conn:
            conn.execute(
                "UPDATE agent_tasks SET progress = ?, updated_at = datetime('now') WHERE id = ?",
                (progress, task_id),
            )

    def _set_task_result(self, task_id: str, result: str):
        with transaction() as conn:
            conn.execute(
                "UPDATE agent_tasks SET result = ?, updated_at = datetime('now') WHERE id = ?",
                (result, task_id),
            )

    def _set_task_error(self, task_id: str, error: str):
        with transaction() as conn:
            conn.execute(
                "UPDATE agent_tasks SET error = ?, updated_at = datetime('now') WHERE id = ?",
                (error, task_id),
            )

    def _set_task_approval(self, task_id: str, required: bool):
        with transaction() as conn:
            conn.execute(
                "UPDATE agent_tasks SET requires_approval = ?, updated_at = datetime('now') WHERE id = ?",
                (1 if required else 0, task_id),
            )


class AgentApprovalRequired(Exception):
    """Raised when a step requires human approval before continuing."""
    pass
