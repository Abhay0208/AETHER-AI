"""Unit tests for AETHER security module.

Run with: python3 -m unittest tests.test_security -v
"""
from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token,
    encrypt_secret,
    decrypt_secret,
    generate_csrf_token,
    is_safe_path,
    sanitize_filename,
    get_rate_limiter,
)


class SecurityTests(unittest.TestCase):
    """Tests for security utilities."""

    def test_password_hashing(self):
        """Password hashing and verification should work."""
        pwd = "s3cret-p@ssw0rd"
        hashed = hash_password(pwd)
        self.assertNotEqual(hashed, pwd)
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_access_token_roundtrip(self):
        """Access tokens should encode and decode correctly."""
        token = create_access_token("alice", expires_minutes=60)
        self.assertIsInstance(token, str)
        self.assertEqual(verify_access_token(token), "alice")

    def test_access_token_expiry(self):
        """Expired tokens should fail verification."""
        token = create_access_token("bob", expires_minutes=-1)  # already expired
        self.assertIsNone(verify_access_token(token))

    def test_access_token_tampering(self):
        """Tampered tokens should fail verification."""
        token = create_access_token("carol")
        # Tamper with the signature part
        parts = token.split(".")
        if len(parts) == 3:
            parts[2] = "0" * len(parts[2])
            tampered = ".".join(parts)
            self.assertIsNone(verify_access_token(tampered))

    def test_secret_encryption_roundtrip(self):
        """Encrypted secrets should decrypt correctly."""
        secret = "sk-abc123def456ghi789"
        encrypted = encrypt_secret(secret)
        self.assertNotEqual(encrypted, secret)
        self.assertEqual(decrypt_secret(encrypted), secret)

    def test_secret_encryption_different_each_time(self):
        """Same plaintext should encrypt differently each time (salt)."""
        secret = "same-secret"
        e1 = encrypt_secret(secret)
        e2 = encrypt_secret(secret)
        self.assertNotEqual(e1, e2)
        self.assertEqual(decrypt_secret(e1), secret)
        self.assertEqual(decrypt_secret(e2), secret)

    def test_csrf_token(self):
        """CSRF tokens should be non-empty strings."""
        token = generate_csrf_token()
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

    def test_is_safe_path(self):
        """Path traversal should be rejected."""
        self.assertTrue(is_safe_path("folder/file.txt"))
        self.assertTrue(is_safe_path("a/b/c/d.md"))
        self.assertFalse(is_safe_path("../etc/passwd"))
        self.assertFalse(is_safe_path("folder/../../etc/passwd"))
        self.assertFalse(is_safe_path(".."))
        self.assertFalse(is_safe_path("."))
        self.assertFalse(is_safe_path(""))
        self.assertFalse(is_safe_path("folder/..%2fetc/passwd"))
        self.assertFalse(is_safe_path("folder/file\x00.txt"))

    def test_sanitize_filename(self):
        """Dangerous filename characters should be stripped."""
        self.assertEqual(sanitize_filename("normal.txt"), "normal.txt")
        self.assertEqual(sanitize_filename("../etc/passwd"), "_etc_passwd")
        self.assertEqual(sanitize_filename('file<>:"|?*.txt'), "file_______.txt")
        self.assertEqual(sanitize_filename("  spaced  "), "spaced")


class RateLimitTests(unittest.TestCase):
    """Tests for the rate limiter."""

    def test_rate_limiter_allows_within_limit(self):
        """Requests within the limit should be allowed."""
        from app.security import RateLimiter

        limiter = RateLimiter(max_requests=3, window_seconds=60)
        self.assertTrue(limiter.check("client1"))
        self.assertTrue(limiter.check("client1"))
        self.assertTrue(limiter.check("client1"))
        self.assertFalse(limiter.check("client1"))  # 4th request exceeds limit

    def test_rate_limiter_different_keys(self):
        """Different clients should have independent limits."""
        from app.security import RateLimiter

        limiter = RateLimiter(max_requests=2, window_seconds=60)
        self.assertTrue(limiter.check("client1"))
        self.assertTrue(limiter.check("client1"))
        self.assertFalse(limiter.check("client1"))
        # Different client should still be allowed
        self.assertTrue(limiter.check("client2"))

    def test_global_rate_limiter(self):
        """The global rate limiter should be a singleton."""
        from app.security import get_rate_limiter

        l1 = get_rate_limiter()
        l2 = get_rate_limiter()
        self.assertIs(l1, l2)


if __name__ == "__main__":
    unittest.main()
