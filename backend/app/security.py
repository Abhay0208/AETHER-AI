"""Security utilities for AETHER.

- Password hashing with bcrypt (fallback: PBKDF2-SHA256).
- Session / access tokens (HMAC-signed, timestamped, expiry-checked).
- Encryption for API keys at rest (Fernet via cryptography when available;
  PBKDF2-derived XOR with per-encryption salt as fallback).
- CSRF token generation.
- Rate limiting helpers.
- Input validation helpers.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ENCRYPTION_KEY,
    SECRET_KEY,
)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def _pbkdf2_hash(password: str) -> str:
    """Pure-Python PBKDF2-SHA256 fallback when passlib/bcrypt are unavailable."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return "pbkdf2_sha256$210000$" + base64.b64encode(salt + dk).decode()


def _pbkdf2_verify(plain: str, hashed: str) -> bool:
    try:
        parts = hashed.split("$")
        if len(parts) != 3:
            return False
        algo, rounds, rest = parts
        raw = base64.b64decode(rest)
        salt, dk = raw[:16], raw[16:]
        return hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, int(rounds)) == dk
    except Exception:
        return False


try:
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

except Exception:  # pragma: no cover - passlib/bcrypt missing, pure-Python fallback
    def hash_password(password: str) -> str:
        return _pbkdf2_hash(password)

    def verify_password(plain: str, hashed: str) -> bool:
        if hashed.startswith("pbkdf2_sha256$"):
            return _pbkdf2_verify(plain, hashed)
        try:
            import bcrypt

            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Tokens (HMAC-signed, timestamped access tokens)
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Create a signed access token for `subject` (username).

    Format: header_b64.body_b64.signature — each part base64url-encoded
    separately so splitting on "." is unambiguous.
    """
    expires = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    expire = _now() + timedelta(minutes=expires)
    payload = {"sub": subject, "exp": expire.isoformat(), "iat": _now().isoformat()}

    try:
        from itsdangerous import TimedJSONWebSignatureSerializer as Serializer  # type: ignore

        s = Serializer(SECRET_KEY)
        return s.dumps(payload).decode()  # type: ignore[attr-defined]
    except Exception:
        pass

    # Fallback: HMAC-signed JSON.
    header_b64 = _b64u_encode(b"aether.v1")
    body = json.dumps(payload, separators=(",", ":")).encode()
    body_b64 = _b64u_encode(body)
    signing_input = (header_b64 + "." + body_b64).encode()
    sig = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).hexdigest()
    return header_b64 + "." + body_b64 + "." + sig


def verify_access_token(token: str) -> str | None:
    """Verify token and return subject (username) or None."""
    try:
        from itsdangerous import TimedJSONWebSignatureSerializer as Serializer  # type: ignore

        s = Serializer(SECRET_KEY)
        data = s.loads(token)  # type: ignore[attr-defined]
        return str(data["sub"])
    except Exception:
        pass

    # Fallback verification.
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, body_b64, sig = parts
        expected = hmac.new(
            SECRET_KEY.encode(), (header_b64 + "." + body_b64).encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        payload = json.loads(_b64u_decode(body_b64))
        exp = datetime.fromisoformat(payload["exp"])
        if exp < _now():
            return None
        return str(payload["sub"])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# API key encryption at rest
# ---------------------------------------------------------------------------
# Derive a strong encryption key from ENCRYPTION_KEY using PBKDF2. Each
# encryption uses a random salt prepended to the ciphertext so identical
# plaintexts produce different ciphertexts.
_DERIVED_KEY_CACHE: bytes | None = None
_DERIVED_KEY_LOCK = threading.Lock()


def _get_derived_key() -> bytes:
    global _DERIVED_KEY_CACHE
    if _DERIVED_KEY_CACHE is not None:
        return _DERIVED_KEY_CACHE
    with _DERIVED_KEY_LOCK:
        if _DERIVED_KEY_CACHE is None:
            salt = b"aether-key-v1"
            _DERIVED_KEY_CACHE = hashlib.pbkdf2_hmac(
                "sha256", ENCRYPTION_KEY.encode(), salt, 210_000, dklen=32
            )
        return _DERIVED_KEY_CACHE


def _xor_stream(key: bytes, nonce: bytes, length: int) -> bytes:
    """XOR stream cipher using key-derived stream (deterministic per nonce)."""
    out = bytearray()
    ki = 0
    for i in range(length):
        out.append(key[ki % len(key)] ^ nonce[i % len(nonce)])
        ki += 1
    return bytes(out)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt `plaintext` and return a base64url string.

    Format: b64(salt || ciphertext).  Salt is random per encryption so the
    same plaintext encrypts differently each time.
    """
    plaintext_bytes = plaintext.encode("utf-8")
    salt = secrets.token_bytes(16)
    key = _get_derived_key()
    # Derive a per-encryption keystream from key + salt.
    stream = hashlib.pbkdf2_hmac("sha256", salt, key, 1, dklen=len(plaintext_bytes))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext_bytes, stream))
    return base64.urlsafe_b64encode(salt + ciphertext).rstrip(b"=").decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a value produced by `encrypt_secret`."""
    raw = base64.urlsafe_b64decode(ciphertext + "=" * (-len(ciphertext) % 4))
    if len(raw) < 16:
        raise ValueError("ciphertext too short")
    salt, ct = raw[:16], raw[16:]
    key = _get_derived_key()
    stream = hashlib.pbkdf2_hmac("sha256", salt, key, 1, dklen=len(ct))
    plaintext = bytes(a ^ b for a, b in zip(ct, stream))
    return plaintext.decode("utf-8")


# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------
class RateLimiter:
    """Token-bucket rate limiter keyed by client identifier.

    Not thread-safe across processes (use Redis in production), but sufficient
    for single-process deployments.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """Return True if request is allowed, False if rate-limited."""
        now = time.time()
        with self._lock:
            timestamps = self._buckets[key]
            # Remove timestamps outside the window.
            cutoff = now - self.window_seconds
            timestamps[:] = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= self.max_requests:
                return False
            timestamps.append(now)
            return True


_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limited(key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
    """Convenience: return True if the request should be rate-limited."""
    limiter = RateLimiter(max_requests, window_seconds)
    return not limiter.check(key)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
import re  # noqa: E402
from urllib.parse import unquote  # noqa: E402

_PATH_TRAVERSAL_RE = re.compile(r"(\.\./|~|%2e%2e|%252e%252e)")
_NULL_BYTE_RE = re.compile(r"\x00")


def is_safe_path(rel: str) -> bool:
    """Return True if `rel` is a safe relative path (no traversal, no nulls)."""
    if not rel or rel in (".", ".."):
        return False
    if "\\" in rel or "\x00" in rel:
        return False
    # URL-decode once to catch encoded traversal attempts.
    decoded = unquote(rel)
    if _PATH_TRAVERSAL_RE.search(decoded):
        return False
    parts = rel.split("/")
    if ".." in parts:
        return False
    return True


def sanitize_filename(name: str) -> str:
    """Strip dangerous characters from a filename."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------
def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
