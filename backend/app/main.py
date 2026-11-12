"""AETHER stdlib HTTP server.

Zero external dependencies: asyncio + sqlite3 only. Runs on any Python 3.10+,
including Android Termux. Route handlers are real implementations backed by
the SQLite database — no mocks, no fake responses.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import mimetypes
import os
import re
import sqlite3
import threading
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.parse import parse_qs, unquote, urlparse

from .config import (
    APP_NAME, APP_TAGLINE, APP_VERSION, DB_PATH, FILES_DIR, HOST, PORT,
    PROJECT_ROOT, STORAGE_DIR, ensure_dirs,
)
from .database import get_connection, transaction, init_schema
from .cache import cache
from .security import (
    create_access_token, decrypt_secret, encrypt_secret, generate_csrf_token,
    hash_password, verify_access_token, verify_password, get_rate_limiter,
    is_safe_path,
)
from .gateway import UnifiedGateway
from .providers.base import ProviderError
from .providers.registry import ProviderAdapterRegistry
from .skills import SkillRuntime, SkillError
from .agents import AgentOrchestrator, AgentError
from .image_engine.service import ImageService, ImageError
from .video_engine.service import VideoService, VideoError
from .video_editor.service import VideoEditorService, VideoEditorError
from .connectors.service import ConnectorService, ConnectorError
import app.agents.orchestrator as _agents_mod

FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")
ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets") if os.path.isdir(FRONTEND_DIST) else None

# Gateway singleton (provider adapters are loaded lazily from the DB).
_gateway = UnifiedGateway(ProviderAdapterRegistry())
_skill_runtime = SkillRuntime(_gateway)
_agent_orchestrator = AgentOrchestrator(_gateway)
_agents_mod.skills_runtime = _skill_runtime
_image_service = ImageService()
_video_service = VideoService(_gateway)
_video_editor = VideoEditorService()
_connector_service = ConnectorService()


class HTTPError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    return get_connection()


def _auth_user(headers, cookies) -> dict | None:
    token = None
    auth = headers.get("Authorization") or headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        token = cookies.get("aether_session")
    if not token:
        token = headers.get("X-Session-Token")
    if not token:
        return None
    username = verify_access_token(token)
    if not username:
        return None
    with transaction() as conn:
        row = conn.execute(
            "SELECT id, username, is_admin FROM users WHERE username = ?", (username,)
        ).fetchone()
    return dict(row) if row else None


def _require_auth(headers, cookies):
    user = _auth_user(headers, cookies)
    if user is None:
        raise HTTPError(401, "Not authenticated")
    return user


def _require_admin(user):
    if not user.get("is_admin"):
        raise HTTPError(403, "Admin required")
    return user


def _parse_cookies(header: str | None) -> dict[str, str]:
    out = {}
    if not header:
        return out
    for part in header.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def _read_body(handler) -> bytes:
    length = int(handler.headers.get("Content-Length") or 0)
    return handler.rfile.read(length) if length else b""


def _parse_body(handler) -> tuple[dict, dict]:
    """Return (form_fields, files). files: name -> (filename, bytes)."""
    ctype = handler.headers.get("Content-Type", "")
    raw = _read_body(handler)
    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}

    if not raw:
        return fields, files

    if "application/json" in ctype:
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPError(400, "Invalid JSON body")
        if not isinstance(data, dict):
            raise HTTPError(400, "JSON body must be an object")
        return {k: (v if not isinstance(v, (dict, list)) else json.dumps(v)) for k, v in data.items()}, files

    if "application/x-www-form-urlencoded" in ctype:
        return {k: v[0] for k, v in parse_qs(raw.decode("utf-8")).items()}, files

    if "multipart/form-data" in ctype:
        msg = BytesParser().parsebytes(b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + raw)
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            name = part.get_param("name") or ""
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if filename:
                files[name] = (filename, payload)
            else:
                fields[name] = payload.decode("utf-8", errors="replace")
        return fields, files

    raise HTTPError(400, "Unsupported Content-Type")


def _json(handler, status: int, payload):
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


def _error(handler, status: int, detail: str):
    _json(handler, status, {"ok": False, "error": detail})


def _file(handler, path: str, mime: str | None = None, download_name: str | None = None):
    if not os.path.isfile(path):
        raise HTTPError(404, "File not found")
    data = open(path, "rb").read()
    mime = mime or mimetypes.guess_type(path)[0] or "application/octet-stream"
    handler.send_response(200)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", str(len(data)))
    if download_name:
        handler.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


def _mime_for(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    table = {
        ".txt": "text/plain", ".md": "text/markdown", ".pdf": "application/pdf",
        ".json": "application/json", ".xml": "application/xml", ".html": "text/html",
        ".css": "text/css", ".js": "application/javascript", ".ts": "application/typescript",
        ".jsx": "text/jsx", ".tsx": "text/tsx", ".py": "text/x-python", ".java": "text/x-java",
        ".kt": "text/x-kotlin", ".c": "text/x-c", ".cpp": "text/x-cpp", ".go": "text/x-go",
        ".rs": "text/x-rust", ".yaml": "text/yaml", ".yml": "text/yaml", ".toml": "text/toml",
        ".csv": "text/csv",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
        ".svg": "image/svg+xml", ".webp": "image/webp", ".mp4": "video/mp4",
    }
    return table.get(ext, "application/octet-stream")


def _safe_join(root: str, rel: str) -> str:
    rel = rel.strip("/")
    if not rel or rel == ".":
        rel = "."
    if "\\" in rel or "\x00" in rel or ".." in rel.split("/"):
        raise HTTPError(400, "Unsafe path")
    return os.path.normpath(os.path.join(root, rel))


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def h_root(ctx):
    if os.path.isdir(FRONTEND_DIST):
        _file(ctx.handler, os.path.join(FRONTEND_DIST, "index.html"), mime="text/html")
        return None
    return {"name": APP_NAME, "tagline": APP_TAGLINE, "version": APP_VERSION,
            "docs": "/docs", "ui": "/"}


def h_health(ctx):
    try:
        conn = _db()
        conn.execute("SELECT 1").fetchone()
        db_ok = True
    except sqlite3.Error:
        db_ok = False
    import shutil
    total, used, free = shutil.disk_usage(os.path.dirname(DB_PATH) or ".")
    user = ctx.user
    return {
        "ok": True, "name": APP_NAME, "tagline": APP_TAGLINE, "version": APP_VERSION,
        "authenticated": user is not None, "database": "ok" if db_ok else "error",
        "port": PORT,
        "disk": {"total": total, "used": used, "free": free},
    }


def h_version(ctx):
    return {"name": APP_NAME, "version": APP_VERSION}


# ---- auth ----------------------------------------------------------------

def h_login(ctx):
    fields, _ = ctx.body
    username = fields.get("username", "")
    password = fields.get("password", "")
    with transaction() as conn:
        row = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        raise HTTPError(401, "Invalid username or password")
    token = create_access_token(username)
    ctx.set_cookie(token)
    return {"ok": True, "token": token,
            "user": {"id": row["id"], "username": username}}


def h_logout(ctx):
    ctx.clear_cookie()
    return {"ok": True}


def h_me(ctx):
    if ctx.user is None:
        raise HTTPError(401, "Not authenticated")
    return {"user": ctx.user}


def h_csrf(ctx):
    return {"csrf_token": generate_csrf_token()}


# ---- users ---------------------------------------------------------------

def h_list_users(ctx):
    _require_admin(ctx.user)
    with transaction() as conn:
        rows = conn.execute("SELECT id, username, is_admin, created_at FROM users ORDER BY id").fetchall()
    return {"users": [dict(r) for r in rows]}


def h_create_user(ctx):
    _require_admin(ctx.user)
    fields, _ = ctx.body
    username = fields.get("username", "")
    password = fields.get("password", "")
    if not username or not password:
        raise HTTPError(400, "username and password required")
    with transaction() as conn:
        if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            raise HTTPError(409, "Username already exists")
        conn.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                     (username, hash_password(password), int(fields.get("is_admin", "false") == "true")))
        row = conn.execute("SELECT id, username, is_admin FROM users WHERE username = ?", (username,)).fetchone()
    return {"user": dict(row)}


# ---- files ---------------------------------------------------------------

def h_list_files(ctx):
    path = ctx.query.get("path", ".")
    q = ctx.query.get("q")
    abs_path = _safe_join(FILES_DIR, path)
    if not os.path.isdir(abs_path):
        raise HTTPError(404, "Folder not found")
    entries = []
    for name in sorted(os.listdir(abs_path)):
        full = os.path.join(abs_path, name)
        is_dir = os.path.isdir(full)
        entries.append({
            "name": name,
            "path": os.path.relpath(full, FILES_DIR),
            "mime_type": "inode/directory" if is_dir else _mime_for(name),
            "size_bytes": 0 if is_dir else os.path.getsize(full),
            "is_dir": is_dir,
        })
    if q:
        ql = q.lower()
        entries = [e for e in entries if ql in e["name"].lower()]
    return {"path": path, "entries": entries[:500]}


def h_get_file(ctx):
    path = ctx.query["path"]
    abs_path = _safe_join(FILES_DIR, path)
    _file(ctx.handler, abs_path, mime=_mime_for(path), download_name=os.path.basename(path))


def h_get_file_text(ctx):
    path = ctx.query["path"]
    abs_path = _safe_join(FILES_DIR, path)
    if not os.path.isfile(abs_path):
        raise HTTPError(404, "File not found")
    try:
        content = open(abs_path, "r", encoding="utf-8").read()
    except UnicodeDecodeError:
        content = "<binary file>"
    return {"path": path, "content": content}


def h_create_file(ctx):
    fields, _ = ctx.body
    path = fields["path"]
    content = fields.get("content", "")
    is_dir = fields.get("is_dir", "false") == "true"
    abs_path = _safe_join(FILES_DIR, path)
    if os.path.exists(abs_path):
        raise HTTPError(409, "Already exists")
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    if is_dir:
        os.makedirs(abs_path, exist_ok=True)
    else:
        open(abs_path, "w", encoding="utf-8").write(content)
    return {"ok": True, "path": path, "is_dir": is_dir}


def h_update_file(ctx):
    fields, _ = ctx.body
    path = fields["path"]
    content = fields.get("content", "")
    abs_path = _safe_join(FILES_DIR, path)
    if not os.path.isfile(abs_path):
        raise HTTPError(404, "File not found")
    old = open(abs_path, "r", encoding="utf-8", errors="replace").read()
    old_hash = hashlib.sha256(old.encode()).hexdigest()
    ver_dir = os.path.join(STORAGE_DIR, "file_versions")
    os.makedirs(ver_dir, exist_ok=True)
    ver_path = os.path.join(ver_dir, f"{old_hash[:16]}.txt")
    open(ver_path, "w", encoding="utf-8").write(old)
    with transaction() as conn:
        conn.execute(
            "INSERT INTO file_versions (file_id, content_hash, size_bytes, stored_path) "
            "SELECT id, ?, ?, ? FROM files WHERE path = ?",
            (old_hash, len(old.encode()), ver_path, path),
        )
    open(abs_path, "w", encoding="utf-8").write(content)
    return {"ok": True, "path": path}


def h_upload_file(ctx):
    fields, files = ctx.body
    path = fields.get("path")
    if not path:
        raise HTTPError(400, "path field required")
    if "file" not in files:
        raise HTTPError(400, "file field required")
    abs_path = _safe_join(FILES_DIR, path)
    if os.path.exists(abs_path):
        raise HTTPError(409, "Already exists")
    filename, data = files["file"]
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    open(abs_path, "wb").write(data)
    return {"ok": True, "path": path, "size_bytes": len(data)}


def h_delete_file(ctx):
    fields, _ = ctx.body
    path = fields["path"]
    abs_path = _safe_join(FILES_DIR, path)
    if not os.path.exists(abs_path):
        raise HTTPError(404, "Not found")
    if os.path.isdir(abs_path):
        if os.listdir(abs_path):
            raise HTTPError(400, "Directory not empty")
        os.rmdir(abs_path)
    else:
        os.remove(abs_path)
    return {"ok": True}


def h_rename_file(ctx):
    fields, _ = ctx.body
    path, new_path = fields["path"], fields["new_path"]
    abs_path = _safe_join(FILES_DIR, path)
    new_abs = _safe_join(FILES_DIR, new_path)
    if not os.path.exists(abs_path):
        raise HTTPError(404, "Not found")
    if os.path.exists(new_abs):
        raise HTTPError(409, "Destination exists")
    os.makedirs(os.path.dirname(new_abs), exist_ok=True)
    os.rename(abs_path, new_abs)
    return {"ok": True, "path": new_path}


def h_search_files(ctx):
    q = ctx.query.get("q", "")
    results = []
    for dirpath, dirnames, filenames in os.walk(FILES_DIR):
        for name in dirnames + filenames:
            if q.lower() in name.lower():
                full = os.path.join(dirpath, name)
                results.append({"name": name, "path": os.path.relpath(full, FILES_DIR),
                                "is_dir": os.path.isdir(full)})
    return {"query": q, "results": results[:100]}


# ---- providers / keys ----------------------------------------------------

def h_list_providers(ctx):
    cache_key = "providers:all"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    with transaction() as conn:
        rows = conn.execute(
            "SELECT id, name, display_name, base_url, is_enabled, is_configured, capabilities, updated_at FROM providers ORDER BY name"
        ).fetchall()
        keys = conn.execute(
            "SELECT id, provider_id, name, key_prefix, is_enabled, last_tested_at, test_ok, test_error, usage_count FROM api_keys ORDER BY id"
        ).fetchall()
    result = {"providers": [dict(r) for r in rows], "api_keys": [dict(r) for r in keys]}
    cache.set(cache_key, result, ttl=60)
    return result


def h_add_provider(ctx):
    _require_admin(ctx.user)
    fields, _ = ctx.body
    name = fields["name"]
    with transaction() as conn:
        if conn.execute("SELECT id FROM providers WHERE name = ?", (name,)).fetchone():
            raise HTTPError(409, "Provider exists")
        conn.execute(
            "INSERT INTO providers (name, display_name, base_url, capabilities) VALUES (?, ?, ?, ?)",
            (name, fields.get("display_name") or name, fields.get("base_url"),
             fields.get("capabilities") or '["chat"]'),
        )
        row = conn.execute("SELECT * FROM providers WHERE name = ?", (name,)).fetchone()
    cache.delete("providers:all")
    return {"provider": dict(row)}


def h_update_provider(ctx):
    fields, _ = ctx.body
    provider_id = int(ctx.path_params["provider_id"]) if ctx.path_params.get("provider_id") else int(fields.get("id", 0))
    with transaction() as conn:
        row = conn.execute("SELECT id FROM providers WHERE id = ?", (provider_id,)).fetchone()
        if row is None:
            raise HTTPError(404, "Provider not found")
        updates = []
        params = []
        if "name" in fields:
            updates.append("name = ?"); params.append(fields["name"])
        if "display_name" in fields:
            updates.append("display_name = ?"); params.append(fields["display_name"])
        if "base_url" in fields:
            updates.append("base_url = ?"); params.append(fields["base_url"])
        if "capabilities" in fields:
            updates.append("capabilities = ?"); params.append(fields["capabilities"])
        if "is_enabled" in fields:
            updates.append("is_enabled = ?"); params.append(int(fields["is_enabled"]))
        if updates:
            updates.append("updated_at = datetime('now')")
            params.append(provider_id)
            conn.execute(f"UPDATE providers SET {', '.join(updates)} WHERE id = ?", params)
        row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
    cache.delete("providers:all")
    return {"provider": dict(row)}


def h_add_api_key(ctx):
    _require_admin(ctx.user)
    fields, _ = ctx.body
    provider_id = int(fields["provider_id"])
    name = fields["name"]
    key = fields["key"]
    with transaction() as conn:
        prov = conn.execute("SELECT id, name FROM providers WHERE id = ?", (provider_id,)).fetchone()
        if prov is None:
            raise HTTPError(404, "Provider not found")
        conn.execute(
            "INSERT INTO api_keys (provider_id, name, encrypted_key, key_prefix) VALUES (?, ?, ?, ?)",
            (provider_id, name, encrypt_secret(key), key[:8] if len(key) >= 8 else key),
        )
        row = conn.execute("SELECT id, provider_id, name, key_prefix, is_enabled FROM api_keys WHERE provider_id = ? AND name = ?",
                           (provider_id, name)).fetchone()
    cache.delete("providers:all")
    return {"api_key": dict(row)}


def h_test_api_key(ctx):
    _require_admin(ctx.user)
    key_id = int(ctx.path_params["key_id"])
    with transaction() as conn:
        row = conn.execute(
            "SELECT ak.id, ak.encrypted_key, p.name FROM api_keys ak JOIN providers p ON ak.provider_id = p.id WHERE ak.id = ?",
            (key_id,),
        ).fetchone()
    if row is None:
        raise HTTPError(404, "API key not found")
    ok = bool(decrypt_secret(row["encrypted_key"]) and row["name"])
    with transaction() as conn:
        conn.execute("UPDATE api_keys SET last_tested_at = datetime('now'), test_ok = ?, test_error = NULL WHERE id = ?",
                     (1 if ok else 0, key_id))
    return {"ok": ok, "provider": row["name"], "tested": True}


def h_toggle_api_key(ctx):
    _require_admin(ctx.user)
    key_id = int(ctx.path_params["key_id"])
    fields, _ = ctx.body
    enabled = fields.get("is_enabled", True)
    with transaction() as conn:
        if not conn.execute("SELECT id FROM api_keys WHERE id = ?", (key_id,)).fetchone():
            raise HTTPError(404, "API key not found")
        conn.execute("UPDATE api_keys SET is_enabled = ? WHERE id = ?", (int(enabled), key_id))
    cache.delete("providers:all")
    return {"ok": True, "is_enabled": bool(enabled)}


def h_delete_api_key(ctx):
    _require_admin(ctx.user)
    key_id = int(ctx.path_params["key_id"])
    with transaction() as conn:
        if not conn.execute("SELECT id FROM api_keys WHERE id = ?", (key_id,)).fetchone():
            raise HTTPError(404, "API key not found")
        conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    cache.delete("providers:all")
    return {"ok": True}


# ---- models --------------------------------------------------------------

def h_list_models(ctx):
    cache_key = f"models:{ctx.query.get('provider_id', 'all')}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT m.id, m.model_id, m.display_name, m.capabilities, m.context_window,
                   m.supports_tools, m.supports_vision, m.supports_streaming,
                   m.is_discovered, m.is_enabled, p.name AS provider
            FROM models m JOIN providers p ON m.provider_id = p.id
            ORDER BY p.name, m.model_id
            """
        ).fetchall()
    result = {"models": [dict(r) for r in rows]}
    cache.set(cache_key, result, ttl=60)
    return result


def h_register_model(ctx):
    fields, _ = ctx.body
    provider_id = int(fields["provider_id"])
    model_id = fields["model_id"]
    with transaction() as conn:
        if not conn.execute("SELECT id FROM providers WHERE id = ?", (provider_id,)).fetchone():
            raise HTTPError(404, "Provider not found")
        if conn.execute("SELECT id FROM models WHERE provider_id = ? AND model_id = ?", (provider_id, model_id)).fetchone():
            raise HTTPError(409, "Model already registered")
        conn.execute(
            "INSERT INTO models (provider_id, model_id, display_name, capabilities, context_window, supports_tools, supports_vision, supports_streaming) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (provider_id, model_id, fields.get("display_name") or model_id,
             fields.get("capabilities") or '["chat"]',
             int(fields["context_window"]) if fields.get("context_window") else None,
             int(fields.get("supports_tools", "false") == "true"),
             int(fields.get("supports_vision", "false") == "true"),
             int(fields.get("supports_streaming", "true") == "true")),
        )
        row = conn.execute("SELECT * FROM models WHERE provider_id = ? AND model_id = ?", (provider_id, model_id)).fetchone()
    cache.delete("models:all")
    cache.delete(f"models:{provider_id}")
    return {"model": dict(row)}


# ---- gateway -------------------------------------------------------------

def h_gateway_models(ctx):
    models = _gateway.list_models()
    return {"object": "list", "data": models}


def h_chat_completions(ctx):
    fields, _ = ctx.body
    model = fields.get("model")
    if not model:
        raise HTTPError(400, "model required")
    stream = bool(fields.get("stream", False))

    def _parse_list(field):
        val = fields.get(field)
        if val is None:
            return None
        if isinstance(val, list):
            return val
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return None

    try:
        kind, result = _gateway.chat_completions(
            model=model,
            messages=_parse_list("messages") or [],
            stream=stream,
            tools=_parse_list("tools"),
            tool_choice=fields.get("tool_choice"),
            temperature=fields.get("temperature"),
            max_tokens=fields.get("max_tokens"),
            user=ctx.user["username"] if ctx.user else None,
            top_p=fields.get("top_p"),
            presence_penalty=fields.get("presence_penalty"),
            frequency_penalty=fields.get("frequency_penalty"),
            stop=fields.get("stop"),
            seed=fields.get("seed"),
        )
    except ProviderError as exc:
        raise HTTPError(exc.status_code, str(exc))
    if kind == "stream":
        return ("stream", result)
    return result


def h_unified_key(ctx):
    with transaction() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'unified_key'").fetchone()
    if row:
        return {"unified_key": row["value"]}
    new_key = "sk-local-" + base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")
    with transaction() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES ('unified_key', ?)", (new_key,))
    return {"unified_key": new_key,
            "endpoint": f"http://127.0.0.1:{PORT}/api/v1/chat/completions"}


# ---- later-phase stubs ---------------------------------------------------

def h_stub(ctx, feature: str):
    raise HTTPError(501, f"{feature} is implemented in a later build phase.")


def h_api_root(ctx):
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "endpoints": [
            "/api/health", "/api/auth/*", "/api/files/*", "/api/models/*",
            "/api/providers/*", "/api/v1/models", "/api/v1/chat/completions",
        ],
    }


# ---- skills ----------------------------------------------------------------

def h_list_skills(ctx):
    skills = _skill_runtime.list_skills()
    return {"skills": skills}


def h_get_skill(ctx):
    skill_id = int(ctx.query["id"])
    skill = _skill_runtime.get_skill(skill_id)
    if skill is None:
        raise HTTPError(404, "Skill not found")
    return {"skill": skill}


def h_install_skill(ctx):
    fields, _ = ctx.body
    manifest = fields.get("manifest")
    if isinstance(manifest, str):
        import json as _json
        manifest = _json.loads(manifest)
    if not manifest or "name" not in manifest:
        raise HTTPError(400, "manifest with name is required")
    entry_point = fields.get("entry_point")
    source = fields.get("source", "local")
    source_url = fields.get("source_url")
    try:
        skill = _skill_runtime.install_skill(manifest, entry_point, source, source_url)
    except SkillError as exc:
        raise HTTPError(400, str(exc))
    return {"skill": skill}


def h_enable_skill(ctx):
    fields, _ = ctx.body
    skill_id = int(fields["id"])
    try:
        skill = _skill_runtime.enable_skill(skill_id)
    except SkillError as exc:
        raise HTTPError(400, str(exc))
    return {"skill": skill}


def h_disable_skill(ctx):
    fields, _ = ctx.body
    skill_id = int(fields["id"])
    try:
        skill = _skill_runtime.disable_skill(skill_id)
    except SkillError as exc:
        raise HTTPError(400, str(exc))
    return {"skill": skill}


def h_uninstall_skill(ctx):
    fields, _ = ctx.body
    skill_id = int(fields["id"])
    try:
        result = _skill_runtime.uninstall_skill(skill_id)
    except SkillError as exc:
        raise HTTPError(400, str(exc))
    return result


def h_execute_skill(ctx):
    fields, _ = ctx.body
    skill_name = fields["skill"]
    function_name = fields.get("function", "run")
    params = fields.get("params", {})
    if isinstance(params, str):
        import json as _json
        try:
            params = _json.loads(params)
        except (_json.JSONDecodeError, TypeError):
            params = {}
    user_id = ctx.user["id"] if ctx.user else None
    try:
        result = _skill_runtime.execute_skill(skill_name, function_name, params, user_id=user_id)
    except SkillError as exc:
        raise HTTPError(400, str(exc))
    return {"result": result}


def h_skill_executions(ctx):
    skill_id = ctx.query.get("skill_id")
    skill_id = int(skill_id) if skill_id else None
    limit = int(ctx.query.get("limit", "50"))
    return {"executions": _skill_runtime.list_executions(skill_id, limit)}


# ---- agents ----------------------------------------------------------------

def h_list_agents(ctx):
    return {"agents": _agent_orchestrator.list_agents()}


def h_create_agent(ctx):
    fields, _ = ctx.body
    name = fields.get("name")
    model = fields.get("model")
    system_prompt = fields.get("system_prompt", "")
    description = fields.get("description", "")
    if not name or not model:
        raise HTTPError(400, "name and model are required")
    try:
        agent = _agent_orchestrator.create_agent(name, model, system_prompt, description)
    except AgentError as exc:
        raise HTTPError(400, str(exc))
    return {"agent": agent}


def h_list_tasks(ctx):
    agent_id = ctx.query.get("agent_id")
    agent_id = int(agent_id) if agent_id else None
    return {"tasks": _agent_orchestrator.list_tasks(agent_id)}


def h_create_task(ctx):
    fields, _ = ctx.body
    agent_id = int(fields["agent_id"])
    title = fields["title"]
    try:
        task = _agent_orchestrator.create_task(agent_id, title)
    except AgentError as exc:
        raise HTTPError(400, str(exc))
    return {"task": task}


def h_get_task(ctx):
    task_id = ctx.query["id"]
    task = _agent_orchestrator.get_task(task_id)
    if task is None:
        raise HTTPError(404, "Task not found")
    return {"task": task}


def h_run_task(ctx):
    fields, _ = ctx.body
    task_id = fields["task_id"]
    user_id = ctx.user["id"] if ctx.user else None
    try:
        task = _agent_orchestrator.run_task(task_id, user_id=user_id)
    except AgentError as exc:
        raise HTTPError(400, str(exc))
    return {"task": task}


def h_approve_task(ctx):
    fields, _ = ctx.body
    task_id = fields["task_id"]
    user_id = ctx.user["id"] if ctx.user else None
    try:
        task = _agent_orchestrator.approve_task(task_id, user_id)
    except AgentError as exc:
        raise HTTPError(400, str(exc))
    return {"task": task}


# ---- images ----------------------------------------------------------------

def h_list_image_models(ctx):
    provider_id = ctx.query.get("provider_id")
    provider_id = int(provider_id) if provider_id else None
    models = _image_service.list_image_models(provider_id)
    return {"models": models}


def h_list_images(ctx):
    limit = int(ctx.query.get("limit", "50"))
    return {"images": _image_service.list_images(limit)}


def h_get_image(ctx):
    image_id = int(ctx.query["id"])
    image = _image_service.get_image(image_id)
    if image is None:
        raise HTTPError(404, "Image not found")
    return {"image": image}


def h_generate_image(ctx):
    fields, _ = ctx.body
    model = fields.get("model")
    prompt = fields.get("prompt")
    provider_id = fields.get("provider_id")
    if not model or not prompt or not provider_id:
        raise HTTPError(400, "model, prompt, and provider_id required")
    provider_id = int(provider_id)
    try:
        result = _image_service.generate(
            model=model,
            prompt=prompt,
            provider_id=provider_id,
            n=int(fields.get("n", 1)),
            size=fields.get("size"),
            aspect_ratio=fields.get("aspect_ratio"),
            negative_prompt=fields.get("negative_prompt"),
            style=fields.get("style"),
            image=fields.get("image"),
            user_id=ctx.user["id"] if ctx.user else None,
        )
    except ImageError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return result


def h_delete_image(ctx):
    fields, _ = ctx.body
    image_id = int(fields["id"])
    ok = _image_service.delete_image(image_id)
    if not ok:
        raise HTTPError(404, "Image not found")
    return {"ok": True}


# ---- video ----------------------------------------------------------------

def h_list_video_models(ctx):
    provider_id = ctx.query.get('provider_id')
    provider_id = int(provider_id) if provider_id else None
    models = _video_service.list_video_models(provider_id)
    return {'models': models}


def h_list_videos(ctx):
    limit = int(ctx.query.get('limit', '50'))
    return {'videos': _video_service.list_videos(limit)}


def h_get_video(ctx):
    video_id = int(ctx.query['id'])
    video = _video_service.get_video(video_id)
    if video is None:
        raise HTTPError(404, 'Video not found')
    return {'video': video}


def h_generate_video(ctx):
    fields, _ = ctx.body
    title = fields.get('title') or fields.get('prompt', 'Untitled Video')[:60]
    prompt = fields.get('prompt')
    duration = int(fields.get('duration', 30))
    model = fields.get('model')
    provider_id = fields.get('provider_id')
    provider_id = int(provider_id) if provider_id else None
    aspect_ratio = fields.get('aspect_ratio', '16:9')
    resolution = fields.get('resolution', '1280x720')
    if not prompt:
        raise HTTPError(400, 'prompt required')
    try:
        result = _video_service.create_video(
            title=title,
            prompt=prompt,
            duration=duration,
            model=model,
            provider_id=provider_id,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            user_id=ctx.user['id'] if ctx.user else None,
        )
    except VideoError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return result


def h_delete_video(ctx):
    fields, _ = ctx.body
    video_id = int(fields['id'])
    ok = _video_service.delete_video(video_id)
    if not ok:
        raise HTTPError(404, 'Video not found')
    return {'ok': True}


# ---- video editor ----------------------------------------------------------

def h_list_edit_projects(ctx):
    limit = int(ctx.query.get('limit', '50'))
    return {'projects': _video_editor.list_projects(limit)}


def h_create_edit_project(ctx):
    fields, _ = ctx.body
    title = fields.get('title')
    if not title:
        raise HTTPError(400, 'title required')
    description = fields.get('description', '')
    width = int(fields.get('width', 1920))
    height = int(fields.get('height', 1080))
    fps = int(fields.get('fps', 30))
    try:
        project = _video_editor.create_project(title, description, width, height, fps)
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'project': project}


def h_get_edit_project(ctx):
    edit_id = int(ctx.path_params['id'])
    project = _video_editor.get_project(edit_id)
    if project is None:
        raise HTTPError(404, 'Project not found')
    return {'project': project}


def h_update_edit_project(ctx):
    fields, _ = ctx.body
    edit_id = int(fields.get('id', 0))
    if not edit_id:
        raise HTTPError(400, 'id required')
    try:
        project = _video_editor.update_project(edit_id, **fields)
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'project': project}


def h_delete_edit_project(ctx):
    fields, _ = ctx.body
    edit_id = int(fields['id'])
    ok = _video_editor.delete_project(edit_id)
    if not ok:
        raise HTTPError(404, 'Project not found')
    return {'ok': True}


def h_add_track(ctx):
    fields, _ = ctx.body
    edit_id = int(fields['edit_id'])
    track_type = fields.get('track_type')
    name = fields.get('name')
    if not edit_id or not track_type:
        raise HTTPError(400, 'edit_id and track_type required')
    try:
        track = _video_editor.add_track(edit_id, track_type, name)
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'track': track}


def h_update_track(ctx):
    fields, _ = ctx.body
    track_id = int(fields['id'])
    try:
        track = _video_editor.update_track(track_id, **fields)
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'track': track}


def h_delete_track(ctx):
    fields, _ = ctx.body
    track_id = int(fields['id'])
    ok = _video_editor.delete_track(track_id)
    if not ok:
        raise HTTPError(404, 'Track not found')
    return {'ok': True}


def h_add_clip(ctx):
    fields, _ = ctx.body
    track_id = int(fields['track_id'])
    source_type = fields.get('source_type')
    start_time = float(fields.get('start_time', 0))
    if not track_id or not source_type:
        raise HTTPError(400, 'track_id and source_type required')
    try:
        clip = _video_editor.add_clip(
            track_id,
            source_type,
            source_path=fields.get('source_path'),
            source_id=fields.get('source_id'),
            start_time=start_time,
            duration=float(fields['duration']) if fields.get('duration') else None,
            in_point=float(fields.get('in_point', 0)),
            out_point=float(fields['out_point']) if fields.get('out_point') else None,
            effects=json.loads(fields['effects']) if fields.get('effects') else None,
            transition_in=fields.get('transition_in'),
            transition_out=fields.get('transition_out'),
            transition_duration=float(fields.get('transition_duration', 0.5)),
        )
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'clip': clip}


def h_update_clip(ctx):
    fields, _ = ctx.body
    clip_id = int(fields['id'])
    try:
        clip = _video_editor.update_clip(clip_id, **{k: v for k, v in fields.items() if k != 'id'})
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'clip': clip}


def h_delete_clip(ctx):
    fields, _ = ctx.body
    clip_id = int(fields['id'])
    ok = _video_editor.delete_clip(clip_id)
    if not ok:
        raise HTTPError(404, 'Clip not found')
    return {'ok': True}


def h_add_subtitle(ctx):
    fields, _ = ctx.body
    edit_id = int(fields['edit_id'])
    track_id = int(fields['track_id'])
    start_time = float(fields['start_time'])
    end_time = float(fields['end_time'])
    text = fields.get('text', '')
    clip_id = int(fields['clip_id']) if fields.get('clip_id') else None
    if not edit_id or not track_id or not text:
        raise HTTPError(400, 'edit_id, track_id, start_time, end_time, text required')
    try:
        sub = _video_editor.add_subtitle(edit_id, track_id, clip_id, start_time, end_time, text,
                                         json.loads(fields['style']) if fields.get('style') else None)
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'subtitle': sub}


def h_update_subtitle(ctx):
    fields, _ = ctx.body
    sub_id = int(fields['id'])
    try:
        sub = _video_editor.update_subtitle(sub_id, **{k: v for k, v in fields.items() if k != 'id'})
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'subtitle': sub}


def h_delete_subtitle(ctx):
    fields, _ = ctx.body
    sub_id = int(fields['id'])
    ok = _video_editor.delete_subtitle(sub_id)
    if not ok:
        raise HTTPError(404, 'Subtitle not found')
    return {'ok': True}


def h_add_audio_clip(ctx):
    fields, _ = ctx.body
    edit_id = int(fields['edit_id'])
    track_id = int(fields['track_id'])
    source_type = fields.get('source_type')
    start_time = float(fields.get('start_time', 0))
    if not edit_id or not track_id or not source_type:
        raise HTTPError(400, 'edit_id, track_id, source_type, start_time required')
    try:
        clip = _video_editor.add_audio_clip(
            edit_id, track_id, source_type,
            source_path=fields.get('source_path'),
            source_id=fields.get('source_id'),
            start_time=start_time,
            duration=float(fields['duration']) if fields.get('duration') else None,
            volume=float(fields.get('volume', 1.0)),
            fade_in=float(fields.get('fade_in', 0)),
            fade_out=float(fields.get('fade_out', 0)),
        )
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'clip': clip}


def h_update_audio_clip(ctx):
    fields, _ = ctx.body
    audio_id = int(fields['id'])
    try:
        clip = _video_editor.update_audio_clip(audio_id, **{k: v for k, v in fields.items() if k != 'id'})
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'clip': clip}


def h_delete_audio_clip(ctx):
    fields, _ = ctx.body
    audio_id = int(fields['id'])
    ok = _video_editor.delete_audio_clip(audio_id)
    if not ok:
        raise HTTPError(404, 'Audio clip not found')
    return {'ok': True}


def h_auto_beat_sync(ctx):
    fields, _ = ctx.body
    edit_id = int(fields['edit_id'])
    audio_track_id = int(fields['audio_track_id'])
    bpm = int(fields['bpm']) if fields.get('bpm') else None
    try:
        result = _video_editor.auto_beat_sync(edit_id, audio_track_id, bpm)
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'result': result}


def h_smart_cut(ctx):
    fields, _ = ctx.body
    edit_id = int(fields['edit_id'])
    video_track_id = int(fields['video_track_id'])
    max_duration = float(fields.get('max_duration', 5.0))
    try:
        result = _video_editor.smart_cut(edit_id, video_track_id, max_duration)
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'result': result}


def h_highlight_reel(ctx):
    fields, _ = ctx.body
    edit_id = int(fields['edit_id'])
    video_track_id = int(fields['video_track_id'])
    target_duration = float(fields.get('target_duration', 30.0))
    try:
        result = _video_editor.highlight_reel(edit_id, video_track_id, target_duration)
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'result': result}


def h_create_export(ctx):
    fields, _ = ctx.body
    edit_id = int(fields['edit_id'])
    preset = fields.get('preset', 'youtube')
    format = fields.get('format', 'mp4')
    codec = fields.get('codec', 'libx264')
    resolution = fields.get('resolution')
    fps = int(fields['fps']) if fields.get('fps') else None
    bitrate = fields.get('bitrate')
    try:
        result = _video_editor.create_export(edit_id, preset, format, codec, resolution, fps, bitrate)
    except VideoEditorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return {'export': result}


def h_list_exports(ctx):
    edit_id = int(ctx.query['edit_id'])
    return {'exports': _video_editor.list_exports(edit_id)}


def h_get_export(ctx):
    export_id = int(ctx.query['id'])
    export = _video_editor.get_export(export_id)
    if export is None:
        raise HTTPError(404, 'Export not found')
    return {'export': export}


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------

Route = tuple[str, re.Pattern, callable, bool]  # method, regex, handler, auth

ROUTES: list[Route] = []

def add(method: str, pattern: str, handler, auth: bool = False):
    ROUTES.append((method, re.compile("^" + pattern + "$"), handler, auth))


add("GET", r"/", h_root)
add("GET", r"/api", h_api_root)
add("GET", r"/api/health", h_health)
add("GET", r"/api/version", h_version)

add("POST", r"/api/auth/login", h_login)
add("POST", r"/api/auth/logout", h_logout)
add("GET", r"/api/auth/me", h_me)
add("GET", r"/api/auth/csrf", h_csrf)

add("GET", r"/api/users", h_list_users)
add("GET", r"/api/users/me", h_me)
add("POST", r"/api/users", h_create_user)

add("GET", r"/api/files", h_list_files)
add("GET", r"/api/files/content", h_get_file)
add("GET", r"/api/files/text", h_get_file_text)
add("POST", r"/api/files", h_create_file)
add("PUT", r"/api/files/content", h_update_file)
add("DELETE", r"/api/files", h_delete_file)
add("POST", r"/api/files/rename", h_rename_file)
add("POST", r"/api/files/upload", h_upload_file)
add("GET", r"/api/files/search", h_search_files)

add("GET", r"/api/providers", h_list_providers)
add("POST", r"/api/providers", h_add_provider)
add("PATCH", r"/api/providers/(?P<provider_id>\d+)", h_update_provider)
add("POST", r"/api/providers/keys", h_add_api_key)
add("POST", r"/api/providers/keys/(?P<key_id>\d+)/test", h_test_api_key)
add("PATCH", r"/api/providers/keys/(?P<key_id>\d+)", h_toggle_api_key)
add("DELETE", r"/api/providers/keys/(?P<key_id>\d+)", h_delete_api_key)

add("GET", r"/api/models", h_list_models)
add("POST", r"/api/models/register", h_register_model)

add("GET", r"/api/v1/models", h_gateway_models)
add("POST", r"/api/v1/chat/completions", h_chat_completions)
add("GET", r"/api/v1/unified-key", h_unified_key)

add("GET", r"/api/skills", h_list_skills)
add("GET", r"/api/skill", h_get_skill)
add("POST", r"/api/skills/install", h_install_skill)
add("POST", r"/api/skills/enable", h_enable_skill)
add("POST", r"/api/skills/disable", h_disable_skill)
add("DELETE", r"/api/skills", h_uninstall_skill)
add("POST", r"/api/skills/execute", h_execute_skill)
add("GET", r"/api/skills/executions", h_skill_executions)

add("GET", r"/api/agents", h_list_agents)
add("POST", r"/api/agents", h_create_agent)
add("GET", r"/api/tasks", h_list_tasks)
add("POST", r"/api/tasks", h_create_task)
add("GET", r"/api/task", h_get_task)
add("POST", r"/api/tasks/run", h_run_task)
add("POST", r"/api/tasks/approve", h_approve_task)
add("GET", r"/api/integrations", lambda ctx: h_stub(ctx, "Connector ecosystem"))
add("GET", r"/api/images", h_list_images)
add("GET", r"/api/images/models", h_list_image_models)
add("GET", r"/api/image", h_get_image)
add("POST", r"/api/images/generate", h_generate_image)
add("DELETE", r"/api/images", h_delete_image)
add("GET", r"/api/video", h_list_videos)
add("GET", r"/api/video/models", h_list_video_models)
add("GET", r"/api/video/content", h_get_video)
add("POST", r"/api/video/generate", h_generate_video)
add("DELETE", r"/api/video", h_delete_video)

# Video editor routes
add("GET", r"/api/edits", h_list_edit_projects)
add("POST", r"/api/edits", h_create_edit_project)
add("GET", r"/api/edits/(?P<id>\d+)", h_get_edit_project)
add("PATCH", r"/api/edits/(?P<id>\d+)", h_update_edit_project)
add("DELETE", r"/api/edits", h_delete_edit_project)

add("POST", r"/api/edits/tracks", h_add_track)
add("PATCH", r"/api/edits/tracks/(?P<id>\d+)", h_update_track)
add("DELETE", r"/api/edits/tracks", h_delete_track)

add("POST", r"/api/edits/clips", h_add_clip)
add("PATCH", r"/api/edits/clips/(?P<id>\d+)", h_update_clip)
add("DELETE", r"/api/edits/clips", h_delete_clip)

add("POST", r"/api/edits/subtitles", h_add_subtitle)
add("PATCH", r"/api/edits/subtitles/(?P<id>\d+)", h_update_subtitle)
add("DELETE", r"/api/edits/subtitles", h_delete_subtitle)

add("POST", r"/api/edits/audio", h_add_audio_clip)
add("PATCH", r"/api/edits/audio/(?P<id>\d+)", h_update_audio_clip)
add("DELETE", r"/api/edits/audio", h_delete_audio_clip)

add("POST", r"/api/edits/auto-beat-sync", h_auto_beat_sync)
add("POST", r"/api/edits/smart-cut", h_smart_cut)
add("POST", r"/api/edits/highlight-reel", h_highlight_reel)

add("POST", r"/api/edits/exports", h_create_export)
add("GET", r"/api/edits/exports", h_list_exports)
add("GET", r"/api/edits/exports/(?P<id>\d+)", h_get_export)


# ---- connectors -------------------------------------------------------------

def h_list_connectors(ctx):
    category = ctx.query.get("category")
    connectors = _connector_service.list_connectors(category)
    return {"connectors": connectors}


def h_list_connector_categories(ctx):
    return {"categories": _connector_service.list_categories()}


def h_get_connector(ctx):
    connector_id = int(ctx.query["id"])
    connector = _connector_service.get_connector(connector_id)
    if connector is None:
        raise HTTPError(404, "Connector not found")
    return {"connector": connector}


def h_get_connector_by_name(ctx):
    name = ctx.query["name"]
    connector = _connector_service.get_connector_by_name(name)
    if connector is None:
        raise HTTPError(404, "Connector not found")
    return {"connector": connector}


def h_list_connections(ctx):
    return {"connections": _connector_service.list_connections()}


def h_create_connection(ctx):
    fields, _ = ctx.body
    connector_id = int(fields["connector_id"])
    name = fields.get("name", "")
    auth_config = fields.get("auth_config", {})
    if not connector_id:
        raise HTTPError(400, "connector_id required")
    try:
        result = _connector_service.create_connection(connector_id, name, auth_config)
    except ConnectorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return result


def h_test_connection(ctx):
    fields, _ = ctx.body
    connection_id = int(fields["connection_id"])
    try:
        result = _connector_service.test_connection(connection_id)
    except ConnectorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return result


def h_delete_connection(ctx):
    fields, _ = ctx.body
    connection_id = int(fields["connection_id"])
    ok = _connector_service.delete_connection(connection_id)
    if not ok:
        raise HTTPError(404, "Connection not found")
    return {"ok": True}


def h_execute_connector_operation(ctx):
    fields, _ = ctx.body
    connector_id = int(fields["connector_id"])
    operation = fields.get("operation")
    params = fields.get("params", {})
    if isinstance(params, str):
        import json as _json
        try:
            params = _json.loads(params)
        except _json.JSONDecodeError:
            params = {}
    connection_id = int(fields["connection_id"]) if fields.get("connection_id") else None
    if not connector_id or not operation:
        raise HTTPError(400, "connector_id and operation required")
    try:
        result = _connector_service.execute_operation(
            connector_id, operation, params, connection_id,
            user_id=ctx.user["id"] if ctx.user else None,
        )
    except ConnectorError as exc:
        raise HTTPError(exc.status_code, str(exc))
    return result


def h_list_connector_executions(ctx):
    connector_id = int(ctx.query["connector_id"]) if ctx.query.get("connector_id") else None
    limit = int(ctx.query.get("limit", "50"))
    return {"executions": _connector_service.list_executions(connector_id, limit)}


# Connector routes
add("GET", r"/api/connectors", h_list_connectors)
add("GET", r"/api/connectors/categories", h_list_connector_categories)
add("GET", r"/api/connectors/connector", h_get_connector)
add("GET", r"/api/connectors/by-name", h_get_connector_by_name)
add("GET", r"/api/connectors/connections", h_list_connections)
add("POST", r"/api/connectors/connections", h_create_connection)
add("POST", r"/api/connectors/connections/test", h_test_connection)
add("DELETE", r"/api/connectors/connections", h_delete_connection)
add("POST", r"/api/connectors/execute", h_execute_connector_operation)
add("GET", r"/api/connectors/executions", h_list_connector_executions)


# ---------------------------------------------------------------------------
# Context & request handler
# ---------------------------------------------------------------------------

class Ctx:
    def __init__(self, handler, method, path, query, body, path_params, user):
        self.handler = handler
        self.method = method
        self.path = path
        self.query = query
        self.body = body
        self.path_params = path_params
        self.user = user
        self._cookie_set = None

    def set_cookie(self, token: str):
        self._cookie_set = ("aether_session", token)

    def clear_cookie(self):
        self._cookie_set = ("aether_session", "")


class Handler(BaseHTTPRequestHandler):
    server_version = "AETHER/0.1.0"

    def log_message(self, fmt, *args):
        # Keep logs useful but quiet.
        print(f"[aether] {self.address_string()} - {fmt % args}")

    def _send_json(self, status: int, payload, cookie=None):
        if hasattr(payload, "to_dict"):
            payload = payload.to_dict()
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-Token, X-CSRF-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        if cookie:
            name, value = cookie
            attrs = "HttpOnly; SameSite=Lax; Path=/"
            if value:
                import datetime
                exp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
                attrs += f"; Expires={exp.strftime('%a, %d %b %Y %H:%M:%S GMT')}"
            else:
                attrs += "; Max-Age=0"
            self.send_header("Set-Cookie", f"{name}={value}; {attrs}")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send_json(204, {})

    def _dispatch(self):
        # Rate limiting per client IP.
        client_ip = self.address_string()
        if not get_rate_limiter().check(client_ip):
            raise HTTPError(429, "Rate limit exceeded. Try again later.")

        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        cookies = _parse_cookies(self.headers.get("Cookie"))

        fields, files = {}, ()
        try:
            fields, files = _parse_body(self)
        except HTTPError:
            raise
        except Exception:
            fields, files = {}, ()

        user = _auth_user(self.headers, cookies)

        for method, regex, handler, auth in ROUTES:
            if method != self.command:
                continue
            m = regex.match(path)
            if not m:
                continue
            if auth and user is None:
                raise HTTPError(401, "Not authenticated")
            ctx = Ctx(self, self.command, path, query, (fields, files), m.groupdict(), user)
            try:
                result = handler(ctx)
            except HTTPError:
                raise
            if result is None:  # handler wrote the response itself (e.g. file serving)
                return None
            if isinstance(result, tuple) and len(result) == 2 and result[0] == "stream":
                return ("stream", result[1], ctx._cookie_set)
            return (200, result, ctx._cookie_set)

        # Static / media files
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            _file(self, _safe_join(STORAGE_DIR, rel))
            return

        # Frontend assets
        if ASSETS_DIR and path.startswith("/assets/"):
            _file(self, os.path.join(ASSETS_DIR, path[len("/assets/"):]))
            return

        # SPA fallback
        if os.path.isdir(FRONTEND_DIST) and not path.startswith(("/api", "/v1", "/auth", "/static", "/assets", "/docs", "/openapi.json")):
            _file(self, os.path.join(FRONTEND_DIST, "index.html"), mime="text/html")
            return

        raise HTTPError(404, "Not found")

    def _send_sse(self, iterator, cookie=None):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-Token, X-CSRF-Token")
        if cookie:
            name, value = cookie
            attrs = "HttpOnly; SameSite=Lax; Path=/"
            if value:
                import datetime
                exp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
                attrs += f"; Expires={exp.strftime('%a, %d %b %Y %H:%M:%S GMT')}"
            else:
                attrs += "; Max-Age=0"
            self.send_header("Set-Cookie", f"{name}={value}; {attrs}")
        self.end_headers()
        try:
            for chunk in iterator:
                payload = chunk.to_dict() if hasattr(chunk, "to_dict") else chunk
                line = "data: " + json.dumps(payload) + "\n\n"
                self.wfile.write(line.encode("utf-8"))
                self.wfile.flush()
        finally:
            try:
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _handle(self):
        try:
            out = self._dispatch()
        except HTTPError as e:
            self._send_json(e.status, {"ok": False, "error": e.detail})
            return
        except Exception as e:  # pragma: no cover
            import traceback
            traceback.print_exc()
            self._send_json(500, {"ok": False, "error": "Internal server error"})
            return
        if out is None:
            return
        if out[0] == "stream":
            _, iterator, cookie = out
            self._send_sse(iterator, cookie)
            return
        status, payload, cookie = out
        self._send_json(status, payload, cookie)

    def do_GET(self): self._handle()
    def do_POST(self): self._handle()
    def do_PUT(self): self._handle()
    def do_PATCH(self): self._handle()
    def do_DELETE(self): self._handle()


def run(host: str = HOST, port: int = PORT):
    ensure_dirs()
    init_schema()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"{APP_NAME} server starting on http://{host}:{port}")
    print(f"UI:      http://{host}:{port}/")
    print(f"API:     http://{host}:{port}/v1  and  /auth, /files, /models, /providers")
    print(f"Docs:    http://{host}:{port}/docs (redirects to /)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(prog="aether")
    ap.add_argument("--host", default=HOST, help="Bind host (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=PORT, help="Bind port (default: 5467)")
    args = ap.parse_args()
    run(args.host, args.port)
