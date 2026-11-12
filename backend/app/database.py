"""SQLite database layer for AETHER.

Uses the Python standard-library sqlite3 module so there is no heavy
external dependency. All access goes through a single connection factory
with row_factory and WAL mode for concurrent readers.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator

from .config import DB_PATH, PROJECT_ROOT, ensure_dirs

_lock = threading.RLock()
_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """Return a thread-shared sqlite3 connection (WAL mode, FKs on)."""
    global _connection
    with _lock:
        if _connection is None:
            ensure_dirs()
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
            _connection.row_factory = sqlite3.Row
            _connection.execute("PRAGMA journal_mode=WAL")
            _connection.execute("PRAGMA synchronous=NORMAL")
            _connection.execute("PRAGMA foreign_keys=ON")
        return _connection


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_schema() -> None:
    """Create all Phase 1 tables if they do not exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin     INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id            TEXT PRIMARY KEY,
            user_id       INTEGER NOT NULL,
            expires_at    TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

        CREATE TABLE IF NOT EXISTS providers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL UNIQUE,
            display_name  TEXT NOT NULL,
            base_url      TEXT,
            api_key_env   TEXT,
            is_enabled    INTEGER NOT NULL DEFAULT 1,
            is_configured INTEGER NOT NULL DEFAULT 0,
            capabilities  TEXT,   -- JSON: chat, completions, embeddings, image, video, tools, vision
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id    INTEGER NOT NULL,
            name           TEXT NOT NULL,
            encrypted_key  TEXT NOT NULL,
            key_prefix     TEXT NOT NULL,
            is_enabled     INTEGER NOT NULL DEFAULT 1,
            last_tested_at TEXT,
            test_ok        INTEGER DEFAULT 0,
            test_error     TEXT,
            usage_count    INTEGER NOT NULL DEFAULT 0,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_api_keys_provider ON api_keys(provider_id);

        CREATE TABLE IF NOT EXISTS models (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id    INTEGER NOT NULL,
            model_id       TEXT NOT NULL,
            display_name   TEXT,
            capabilities   TEXT,   -- JSON list
            context_window INTEGER,
            supports_tools INTEGER NOT NULL DEFAULT 0,
            supports_vision INTEGER NOT NULL DEFAULT 0,
            supports_streaming INTEGER NOT NULL DEFAULT 1,
            is_discovered  INTEGER NOT NULL DEFAULT 0,
            is_enabled     INTEGER NOT NULL DEFAULT 1,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE,
            UNIQUE (provider_id, model_id)
        );
        CREATE INDEX IF NOT EXISTS idx_models_provider ON models(provider_id);

        CREATE TABLE IF NOT EXISTS files (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            path          TEXT NOT NULL UNIQUE,
            parent_id     INTEGER,
            mime_type     TEXT,
            size_bytes    INTEGER NOT NULL DEFAULT 0,
            is_dir        INTEGER NOT NULL DEFAULT 0,
            owner_id      INTEGER,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (parent_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent_id);
        CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);

        CREATE TABLE IF NOT EXISTS file_versions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id     INTEGER NOT NULL,
            content_hash TEXT NOT NULL,
            size_bytes  INTEGER NOT NULL DEFAULT 0,
            stored_path TEXT NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id           TEXT PRIMARY KEY,
            type         TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'queued',
            progress     INTEGER NOT NULL DEFAULT 0,
            result       TEXT,
            error        TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

        CREATE TABLE IF NOT EXISTS audit_logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER,
            action    TEXT NOT NULL,
            target    TEXT,
            details   TEXT,
            ip        TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS usage_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER,
            model_id    TEXT,
            tokens_in   INTEGER DEFAULT 0,
            tokens_out  INTEGER DEFAULT 0,
            cost_usd    REAL DEFAULT 0,
            ok          INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_events(created_at);

        -- Phase 3: Skills ecosystem
        CREATE TABLE IF NOT EXISTS skills (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL UNIQUE,
            display_name   TEXT,
            version        TEXT NOT NULL DEFAULT '1.0.0',
            description    TEXT,
            category       TEXT,
            author         TEXT,
            source         TEXT,          -- 'local', 'github', 'marketplace'
            source_url     TEXT,
            entry_point    TEXT,          -- skill file to execute
            manifest       TEXT,          -- JSON manifest
            permissions    TEXT,          -- JSON list of required permissions
            dependencies   TEXT,          -- JSON list of dependencies
            is_installed   INTEGER NOT NULL DEFAULT 0,
            is_enabled     INTEGER NOT NULL DEFAULT 0,
            is_builtin     INTEGER NOT NULL DEFAULT 0,
            installed_at   TEXT,
            updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
        CREATE INDEX IF NOT EXISTS idx_skills_installed ON skills(is_installed);

        CREATE TABLE IF NOT EXISTS skill_executions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id       INTEGER NOT NULL,
            function_name  TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'running',
            input          TEXT,          -- JSON input
            output         TEXT,          -- JSON output
            error          TEXT,
            started_at     TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at   TEXT,
            FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_skill_executions_skill ON skill_executions(skill_id);

        -- Phase 3: Autonomous agents
        CREATE TABLE IF NOT EXISTS agents (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            description    TEXT,
            model          TEXT,
            system_prompt  TEXT,
            is_enabled     INTEGER NOT NULL DEFAULT 1,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS agent_tasks (
            id             TEXT PRIMARY KEY,
            agent_id       INTEGER,
            title          TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'queued',  -- queued, running, completed, failed, awaiting_approval
            progress       INTEGER NOT NULL DEFAULT 0,
            result         TEXT,
            error          TEXT,
            requires_approval INTEGER NOT NULL DEFAULT 0,
            approved_by    INTEGER,
            approved_at    TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at   TEXT,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE SET NULL,
            FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status);

        CREATE TABLE IF NOT EXISTS agent_task_steps (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id        TEXT NOT NULL,
            step_index     INTEGER NOT NULL,
            type           TEXT NOT NULL,  -- plan, think, tool_call, skill_call, file_op, approve
            description    TEXT,
            status         TEXT NOT NULL DEFAULT 'pending',
            input          TEXT,
            output         TEXT,
            error          TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at   TEXT,
            FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_agent_task_steps_task ON agent_task_steps(task_id);

        -- Phase 4: Image generation
        CREATE TABLE IF NOT EXISTS images (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt         TEXT NOT NULL,
            model          TEXT NOT NULL,
            provider       TEXT NOT NULL,
            size           TEXT,
            aspect_ratio   TEXT,
            status         TEXT NOT NULL DEFAULT 'queued',
            file_path      TEXT,
            url            TEXT,
            width          INTEGER,
            height         INTEGER,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_images_status ON images(status);
        CREATE INDEX IF NOT EXISTS idx_images_created ON images(created_at);

        -- Phase 4: Image generation jobs (resumable, background)
        CREATE TABLE IF NOT EXISTS image_jobs (
            id             TEXT PRIMARY KEY,
            image_id       INTEGER NOT NULL,
            status         TEXT NOT NULL DEFAULT 'queued',
            progress       INTEGER NOT NULL DEFAULT 0,
            result         TEXT,
            error          TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at   TEXT,
            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_image_jobs_status ON image_jobs(status);

        -- Phase 5: Video generation
        CREATE TABLE IF NOT EXISTS videos (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT NOT NULL,
            prompt         TEXT NOT NULL,
            script         TEXT,          -- full generated script (JSON)
            duration       INTEGER,       -- requested seconds
            aspect_ratio   TEXT,
            resolution     TEXT,
            status         TEXT NOT NULL DEFAULT 'queued',
            file_path      TEXT,
            width          INTEGER,
            height         INTEGER,
            fps            INTEGER,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
        CREATE INDEX IF NOT EXISTS idx_videos_created ON videos(created_at);

        CREATE TABLE IF NOT EXISTS video_jobs (
            id             TEXT PRIMARY KEY,
            video_id       INTEGER NOT NULL,
            stage          TEXT NOT NULL,  -- script, scenes, clips, assemble, export
            status         TEXT NOT NULL DEFAULT 'queued',
            progress       INTEGER NOT NULL DEFAULT 0,
            result         TEXT,
            error          TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at   TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON video_jobs(status);

        CREATE TABLE IF NOT EXISTS video_clips (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id       INTEGER NOT NULL,
            scene_index    INTEGER NOT NULL,
            scene_title    TEXT,
            prompt         TEXT,
            file_path      TEXT,
            duration       REAL,
            status         TEXT NOT NULL DEFAULT 'queued',
            provider       TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_video_clips_video ON video_clips(video_id);

        -- Phase 6: Automatic video editor (project/timeline)
        CREATE TABLE IF NOT EXISTS video_edits (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT NOT NULL,
            description    TEXT,
            project_data   TEXT,          -- timeline JSON (tracks, clips, transitions, effects)
            status         TEXT NOT NULL DEFAULT 'draft',  -- draft, rendering, completed, failed
            file_path      TEXT,
            width          INTEGER,
            height         INTEGER,
            fps            INTEGER,
            duration       REAL,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_video_edits_status ON video_edits(status);

        CREATE TABLE IF NOT EXISTS edit_tracks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            edit_id        INTEGER NOT NULL,
            track_index    INTEGER NOT NULL,    -- 0 = bottom (background video), higher = overlay
            track_type     TEXT NOT NULL,       -- video, audio, subtitle
            name           TEXT,
            enabled        INTEGER NOT NULL DEFAULT 1,
            locked         INTEGER NOT NULL DEFAULT 0,
            volume         REAL DEFAULT 1.0,     -- for audio tracks
            opacity        REAL DEFAULT 1.0,     -- for video tracks
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (edit_id) REFERENCES video_edits(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_edit_tracks_edit ON edit_tracks(edit_id);

        CREATE TABLE IF NOT EXISTS timeline_clips (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id       INTEGER NOT NULL,
            clip_index     INTEGER NOT NULL,    -- order on track
            source_type    TEXT NOT NULL,       -- video, image, audio, color, text
            source_id      TEXT,                -- reference to video_clips.id, images.id, or generated
            source_path    TEXT,                -- file path for local media
            in_point       REAL NOT NULL DEFAULT 0,      -- trim start (seconds)
            out_point      REAL,                 -- trim end (seconds), null = full
            start_time     REAL NOT NULL,         -- position on timeline (seconds)
            duration       REAL,                 -- effective duration on timeline
            transition_in  TEXT,                -- fade, slide, wipe, zoom, etc.
            transition_out TEXT,
            transition_duration REAL DEFAULT 0.5,
            effects        TEXT,                -- JSON: color_grade, filters, speed, etc.
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (track_id) REFERENCES edit_tracks(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_timeline_clips_track ON timeline_clips(track_id);

        CREATE TABLE IF NOT EXISTS edit_subtitles (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            edit_id        INTEGER NOT NULL,
            track_id       INTEGER NOT NULL,    -- reference to edit_tracks (subtitle track)
            clip_id        INTEGER,             -- reference to timeline_clips
            start_time     REAL NOT NULL,
            end_time       REAL NOT NULL,
            text           TEXT NOT NULL,
            style          TEXT,                -- JSON: font, size, color, position, outline, background
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (edit_id) REFERENCES video_edits(id) ON DELETE CASCADE,
            FOREIGN KEY (track_id) REFERENCES edit_tracks(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_edit_subtitles_edit ON edit_subtitles(edit_id);

        CREATE TABLE IF NOT EXISTS edit_audio (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            edit_id        INTEGER NOT NULL,
            track_id       INTEGER NOT NULL,    -- reference to edit_tracks (audio track)
            clip_index     INTEGER NOT NULL,
            source_type    TEXT NOT NULL,       -- music, voiceover, sfx, generated
            source_path    TEXT,
            source_id      TEXT,                -- reference to external audio
            start_time     REAL NOT NULL,
            duration       REAL,
            volume         REAL DEFAULT 1.0,
            fade_in        REAL DEFAULT 0,
            fade_out       REAL DEFAULT 0,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (edit_id) REFERENCES video_edits(id) ON DELETE CASCADE,
            FOREIGN KEY (track_id) REFERENCES edit_tracks(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_edit_audio_edit ON edit_audio(edit_id);

        CREATE TABLE IF NOT EXISTS edit_exports (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            edit_id        INTEGER NOT NULL,
            preset         TEXT,                -- youtube, tiktok, instagram, custom
            format         TEXT NOT NULL DEFAULT 'mp4',
            codec          TEXT NOT NULL DEFAULT 'libx264',
            resolution     TEXT,
            fps            INTEGER,
            bitrate        TEXT,
            status         TEXT NOT NULL DEFAULT 'queued',
            progress       INTEGER NOT NULL DEFAULT 0,
            file_path      TEXT,
            error          TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at   TEXT,
            FOREIGN KEY (edit_id) REFERENCES video_edits(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_edit_exports_edit ON edit_exports(edit_id);

        -- Phase 7: Connector ecosystem (data sources and integrations)
        CREATE TABLE IF NOT EXISTS connectors (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL UNIQUE,
            display_name   TEXT NOT NULL,
            description    TEXT NOT NULL,
            category       TEXT NOT NULL,
            category_label TEXT NOT NULL,
            documentation  TEXT,
            auth_required  INTEGER NOT NULL DEFAULT 0,
            auth_type      TEXT,                  -- none, api_key, oauth, bearer, basic
            auth_field_name TEXT,                -- e.g. "API Key", "Access Token"
            free_paid      TEXT NOT NULL DEFAULT 'free',  -- free, paid, freemium
            rate_limit     TEXT,
            rate_limit_unit TEXT,                -- per_minute, per_hour, per_day
            base_url       TEXT,
            operations     TEXT,                 -- JSON list of available operations
            capabilities   TEXT,                 -- JSON list of capabilities
            is_enabled     INTEGER NOT NULL DEFAULT 1,
            is_builtin     INTEGER NOT NULL DEFAULT 1,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_connectors_category ON connectors(category);
        CREATE INDEX IF NOT EXISTS idx_connectors_enabled ON connectors(is_enabled);

        CREATE TABLE IF NOT EXISTS connector_connections (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_id   INTEGER NOT NULL,
            name           TEXT NOT NULL,
            auth_config    TEXT,                 -- JSON encrypted auth config
            is_connected   INTEGER NOT NULL DEFAULT 0,
            last_tested_at TEXT,
            test_ok        INTEGER DEFAULT 0,
            test_error     TEXT,
            usage_count    INTEGER NOT NULL DEFAULT 0,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (connector_id) REFERENCES connectors(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_connector_connections_connector ON connector_connections(connector_id);

        CREATE TABLE IF NOT EXISTS connector_executions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_id  INTEGER,
            connector_id   INTEGER NOT NULL,
            operation      TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'queued',
            input          TEXT,                 -- JSON input
            output         TEXT,                 -- JSON output
            error          TEXT,
            started_at     TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at   TEXT,
            FOREIGN KEY (connector_id) REFERENCES connectors(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES connector_connections(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_connector_executions_connector ON connector_executions(connector_id);
        """
    )
    conn.commit()

    # Seed a default local user if none exists.
    cur = conn.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        from .security import hash_password
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", hash_password("admin")),
        )
        conn.commit()

    # Seed built-in providers (disabled until user configures keys).
    cur = conn.execute("SELECT COUNT(*) AS c FROM providers")
    if cur.fetchone()["c"] == 0:
        builtin = [
            ("openai", "OpenAI", "https://api.openai.com/v1", "OPENAI_API_KEY",
             '["chat","completions","tools","vision"]'),
            ("anthropic", "Anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY",
             '["chat","tools","vision"]'),
            ("google", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta", "GOOGLE_API_KEY",
             '["chat","tools","vision"]'),
            ("deepseek", "DeepSeek", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY",
             '["chat","completions"]'),
            ("xai", "xAI", "https://api.x.ai/v1", "XAI_API_KEY",
             '["chat"]'),
            ("mistral", "Mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY",
             '["chat","tools"]'),
            ("groq", "Groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY",
             '["chat","completions","tools"]'),
            ("cohere", "Cohere", "https://api.cohere.ai/v1", "COHERE_API_KEY",
             '["chat"]'),
            ("ollama", "Ollama", "http://localhost:11434/v1", None,
             '["chat","tools","vision"]'),
            ("lmstudio", "LM Studio", "http://localhost:1234/v1", None,
             '["chat","tools"]'),
            ("vllm", "vLLM", "http://localhost:8000/v1", None,
             '["chat","completions","tools"]'),
            ("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
             '["chat","completions","tools","vision"]'),
            ("together", "Together AI", "https://api.together.xyz/v1", "TOGETHER_API_KEY",
             '["chat","completions"]'),
            ("fireworks", "Fireworks AI", "https://api.fireworks.ai/inference/v1", "FIREWORKS_API_KEY",
             '["chat","completions"]'),
            ("cerebras", "Cerebras", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY",
             '["chat","completions"]'),
            ("huggingface", "Hugging Face", "https://api-inference.huggingface.co", "HUGGINGFACE_API_KEY",
             '["chat"]'),
        ]
        for row in builtin:
            conn.execute(
                "INSERT INTO providers (name, display_name, base_url, api_key_env, capabilities) VALUES (?,?,?,?,?)",
                row,
            )
        conn.commit()

    # Seed built-in skills (functional core collection).
    cur = conn.execute("SELECT COUNT(*) AS c FROM skills")
    if cur.fetchone()["c"] == 0:
        import json, os
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        skills_dir = os.path.join(PROJECT_ROOT, "skills", "builtin")
        os.makedirs(skills_dir, exist_ok=True)
        builtin_skills = [
            {
                "name": "file_reader",
                "display_name": "File Reader",
                "version": "1.0.0",
                "description": "Reads files from the AETHER workspace and returns their contents.",
                "category": "File Management",
                "author": "AETHER",
                "source": "builtin",
                "source_url": None,
                "entry_point": "file_reader.py",
                "manifest": json.dumps({
                    "name": "file_reader",
                    "display_name": "File Reader",
                    "version": "1.0.0",
                    "description": "Reads files from the AETHER workspace.",
                    "category": "File Management",
                    "functions": [
                        {
                            "name": "read_file",
                            "description": "Read the contents of a file in the workspace.",
                            "parameters": {
                                "type": "object",
                                "properties": {"path": {"type": "string", "description": "File path relative to workspace"}},
                                "required": ["path"]
                            }
                        }
                    ],
                    "permissions": ["file_read"],
                    "dependencies": []
                }),
                "permissions": json.dumps(["file_read"]),
                "dependencies": json.dumps([]),
                "is_installed": 1,
                "is_enabled": 1,
                "is_builtin": 1,
                "installed_at": now,
            },
            {
                "name": "file_writer",
                "display_name": "File Writer",
                "version": "1.0.0",
                "description": "Creates or overwrites files in the AETHER workspace.",
                "category": "File Management",
                "author": "AETHER",
                "source": "builtin",
                "source_url": None,
                "entry_point": "file_writer.py",
                "manifest": json.dumps({
                    "name": "file_writer",
                    "display_name": "File Writer",
                    "version": "1.0.0",
                    "description": "Creates or overwrites files in the workspace.",
                    "category": "File Management",
                    "functions": [
                        {
                            "name": "write_file",
                            "description": "Write content to a file in the workspace.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "File path relative to workspace"},
                                    "content": {"type": "string", "description": "Content to write"}
                                },
                                "required": ["path", "content"]
                            }
                        }
                    ],
                    "permissions": ["file_write"],
                    "dependencies": []
                }),
                "permissions": json.dumps(["file_write"]),
                "dependencies": json.dumps([]),
                "is_installed": 1,
                "is_enabled": 1,
                "is_builtin": 1,
                "installed_at": now,
            },
            {
                "name": "code_generator",
                "display_name": "Code Generator",
                "version": "1.0.0",
                "description": "Generates code snippets using a connected AI model.",
                "category": "Software Development",
                "author": "AETHER",
                "source": "builtin",
                "source_url": None,
                "entry_point": "code_generator.py",
                "manifest": json.dumps({
                    "name": "code_generator",
                    "display_name": "Code Generator",
                    "version": "1.0.0",
                    "description": "Generates code using a connected AI model via the gateway.",
                    "category": "Software Development",
                    "functions": [
                        {
                            "name": "generate",
                            "description": "Generate code for a given task and language.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "task": {"type": "string", "description": "What code to generate"},
                                    "language": {"type": "string", "description": "Programming language"},
                                    "model": {"type": "string", "description": "Model to use"}
                                },
                                "required": ["task", "language"]
                            }
                        }
                    ],
                    "permissions": ["model_chat"],
                    "dependencies": []
                }),
                "permissions": json.dumps(["model_chat"]),
                "dependencies": json.dumps([]),
                "is_installed": 1,
                "is_enabled": 1,
                "is_builtin": 1,
                "installed_at": now,
            },
            {
                "name": "web_researcher",
                "display_name": "Web Researcher",
                "version": "1.0.0",
                "description": "Searches the web and summarizes results (requires connector or model with tools).",
                "category": "Research",
                "author": "AETHER",
                "source": "builtin",
                "source_url": None,
                "entry_point": "web_researcher.py",
                "manifest": json.dumps({
                    "name": "web_researcher",
                    "display_name": "Web Researcher",
                    "version": "1.0.0",
                    "description": "Researches topics using connected tools.",
                    "category": "Research",
                    "functions": [
                        {
                            "name": "research",
                            "description": "Research a topic and return a summary.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "topic": {"type": "string", "description": "Topic to research"},
                                    "model": {"type": "string", "description": "Model to use"}
                                },
                                "required": ["topic"]
                            }
                        }
                    ],
                    "permissions": ["model_chat"],
                    "dependencies": []
                }),
                "permissions": json.dumps(["model_chat"]),
                "dependencies": json.dumps([]),
                "is_installed": 1,
                "is_enabled": 1,
                "is_builtin": 1,
                "installed_at": now,
            },
        ]
        for s in builtin_skills:
            # Write the skill entry point files.
            skill_file = os.path.join(skills_dir, s["entry_point"])
            if not os.path.exists(skill_file):
                # default content written by runtime installer; create stub here
                os.makedirs(skills_dir, exist_ok=True)
                open(skill_file, "w").write(
                    f'# {s["display_name"]} skill entry point\\n'
                    f'def run(function_name, params, ctx):\\n'
                    f'    return {{"ok": True, "result": "Skill {s["name"]} executed."}}'
                )
            conn.execute(
                """INSERT INTO skills
                   (name, display_name, version, description, category, author, source,
                    source_url, entry_point, manifest, permissions, dependencies,
                   is_installed, is_enabled, is_builtin, installed_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (s["name"], s["display_name"], s["version"], s["description"], s["category"],
                 s["author"], s["source"], s["source_url"], s["entry_point"], s["manifest"],
                 s["permissions"], s["dependencies"], s["is_installed"], s["is_enabled"],
                 s["is_builtin"], s["installed_at"]),
            )
        conn.commit()
    defaults = {
        "app_name": "AETHER",
        "theme": "system",
        "gateway_enabled": "false",
        "gateway_port": "5467",
    }
    for k, v in defaults.items():
        conn.execute(
            "INSERT INTO settings (key, value) SELECT ?, ? WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key=? )",
            (k, v, k),
        )
    conn.commit()
