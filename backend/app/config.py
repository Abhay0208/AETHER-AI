"""AETHER application configuration.

All settings are read from environment variables with safe defaults for
local-first, self-hosted operation. Never ship secrets in this file.
"""
from __future__ import annotations

import os
from functools import lru_cache

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# backend/app -> backend -> project root
PROJECT_ROOT = os.path.dirname(BASE_DIR)

DATA_DIR = os.environ.get("AETHER_DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
STORAGE_DIR = os.environ.get("AETHER_STORAGE_DIR", os.path.join(DATA_DIR, "storage"))
DB_PATH = os.environ.get("AETHER_DB_PATH", os.path.join(DATA_DIR, "aether.db"))
LOG_DIR = os.environ.get("AETHER_LOG_DIR", os.path.join(DATA_DIR, "logs"))
GENERATED_DIR = os.path.join(STORAGE_DIR, "generated")
FILES_DIR = os.path.join(STORAGE_DIR, "files")
SKILLS_DIR = os.path.join(STORAGE_DIR, "skills")
CONNECTORS_DIR = os.path.join(STORAGE_DIR, "connectors")
VIDEOS_DIR = os.path.join(STORAGE_DIR, "videos")
IMAGES_DIR = os.path.join(STORAGE_DIR, "images")

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
HOST = os.environ.get("AETHER_HOST", "127.0.0.1")
PORT = int(os.environ.get("AETHER_PORT", "5467"))
DEBUG = os.environ.get("AETHER_DEBUG", "false").lower() in ("1", "true", "yes")
SECRET_KEY = os.environ.get("AETHER_SECRET_KEY")
# Fallback dev-only secret. Production installs must set AETHER_SECRET_KEY.
if not SECRET_KEY:
    SECRET_KEY = "dev-only-insecure-change-me-" + os.urandom(16).hex()

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("AETHER_TOKEN_EXPIRE_MINUTES", "43200"))  # 30 days

# ---------------------------------------------------------------------------
# Security / encryption
# ---------------------------------------------------------------------------
# API keys at rest are encrypted with a key derived from this.
ENCRYPTION_KEY = os.environ.get("AETHER_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = os.urandom(32).hex()

SESSION_COOKIE_NAME = "aether_session"
CSRF_TOKEN_NAME = "X-CSRF-Token"

# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------
GATEWAY_BASE_URL = os.environ.get(
    "AETHER_GATEWAY_URL", f"http://{HOST}:{PORT}/v1"
)
UNIFIED_KEY_PREFIX = "sk-local-"

# ---------------------------------------------------------------------------
# Feature toggles (Phase 1 = core; later phases flip these on)
# ---------------------------------------------------------------------------
ENABLE_AGENTS = os.environ.get("AETHER_ENABLE_AGENTS", "false").lower() in ("1", "true", "yes")
ENABLE_SKILLS = os.environ.get("AETHER_ENABLE_SKILLS", "false").lower() in ("1", "true", "yes")
ENABLE_IMAGES = os.environ.get("AETHER_ENABLE_IMAGES", "false").lower() in ("1", "true", "yes")
ENABLE_VIDEO = os.environ.get("AETHER_ENABLE_VIDEO", "false").lower() in ("1", "true", "yes")
ENABLE_CONNECTORS = os.environ.get("AETHER_ENABLE_CONNECTORS", "false").lower() in ("1", "true", "yes")

APP_NAME = "AETHER"
APP_TAGLINE = "One Platform. Limitless Intelligence."
APP_VERSION = "0.1.0-phase1"


@lru_cache
def get_settings() -> "Settings":
    return Settings()


class Settings:  # kept for compatibility; module-level constants are the source of truth
    pass


def ensure_dirs() -> list[str]:
    """Create all runtime directories. Returns list of created paths."""
    dirs = [
        DATA_DIR, STORAGE_DIR, LOG_DIR, GENERATED_DIR, FILES_DIR,
        SKILLS_DIR, CONNECTORS_DIR, VIDEOS_DIR, IMAGES_DIR,
    ]
    created = []
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        created.append(d)
    return created
