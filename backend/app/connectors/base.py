"""Base classes and data model for connectors.

Every connector implements :class:`ConnectorBase` and exposes:
- :meth:`ConnectorBase.get_metadata` - returns connector metadata
- :meth:`ConnectorBase.test_connection` - tests authentication/connectivity
- :meth:`ConnectorBase.execute_operation` - executes a specific operation
"""
from __future__ import annotations

import abc
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class ConnectorError(Exception):
    """Raised when a connector operation fails."""

    def __init__(self, message: str, status_code: int = 502, connector: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.connector = connector


@dataclass
class ConnectorCategory:
    """A connector category definition."""

    id: str
    label: str
    description: str


@dataclass
class ConnectorResult:
    """Normalized result from a connector operation."""

    success: bool
    data: Any = None
    error: str | None = None
    operation: str | None = None
    connector: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "operation": self.operation,
            "connector": self.connector,
            "timestamp": self.timestamp,
        }


class ConnectorBase(abc.ABC):
    """Abstract base class for all connectors.

    Subclasses must define:
    - NAME: unique connector identifier
    - DISPLAY_NAME: human-readable name
    - DESCRIPTION: what the connector does
    - CATEGORY: category ID
    - CATEGORY_LABEL: human-readable category label
    - AUTH_REQUIRED: whether authentication is needed
    - AUTH_TYPE: none, api_key, oauth, bearer, basic
    - AUTH_FIELD_NAME: label for the auth field shown to users
    - FREE_PAID: free, paid, or freemium
    - RATE_LIMIT: rate limit info string
    - BASE_URL: base API URL
    - OPERATIONS: list of operation dicts with name, description, parameters
    - CAPABILITIES: list of capability strings
    """

    # Subclasses must override these
    NAME: str = ""
    DISPLAY_NAME: str = ""
    DESCRIPTION: str = ""
    CATEGORY: str = ""
    CATEGORY_LABEL: str = ""
    AUTH_REQUIRED: bool = False
    AUTH_TYPE: str | None = None
    AUTH_FIELD_NAME: str | None = None
    FREE_PAID: str = "free"
    RATE_LIMIT: str | None = None
    RATE_LIMIT_UNIT: str | None = None
    BASE_URL: str | None = None
    OPERATIONS: list[dict] = field(default_factory=list)
    CAPABILITIES: list[str] = field(default_factory=list)

    def __init__(self, auth_config: dict | None = None):
        self.auth_config = auth_config or {}
        self._session = None

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "display_name": self.DISPLAY_NAME,
            "description": self.DESCRIPTION,
            "category": self.CATEGORY,
            "category_label": self.CATEGORY_LABEL,
            "auth_required": self.AUTH_REQUIRED,
            "auth_type": self.AUTH_TYPE,
            "auth_field_name": self.AUTH_FIELD_NAME,
            "free_paid": self.FREE_PAID,
            "rate_limit": self.RATE_LIMIT,
            "rate_limit_unit": self.RATE_LIMIT_UNIT,
            "base_url": self.BASE_URL,
            "operations": self.OPERATIONS,
            "capabilities": self.CAPABILITIES,
        }

    # ------------------------------------------------------------------
    # Connection testing
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def test_connection(self) -> ConnectorResult:
        """Test authentication and connectivity. Returns ConnectorResult."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Operation execution
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def execute_operation(self, operation: str, params: dict | None = None) -> ConnectorResult:
        """Execute a named operation with given params. Returns ConnectorResult."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        auth_type = self.AUTH_TYPE
        auth_config = self.auth_config or {}
        if auth_type == "api_key" and auth_config.get("api_key"):
            headers["X-Api-Key"] = auth_config["api_key"]
        elif auth_type == "bearer" and auth_config.get("access_token"):
            headers["Authorization"] = f"Bearer {auth_config['access_token']}"
        elif auth_type == "basic" and auth_config.get("username") and auth_config.get("password"):
            import base64
            creds = f"{auth_config['username']}:{auth_config['password']}"
            headers["Authorization"] = f"Basic {base64.b64encode(creds.encode()).decode()}"
        return headers

    def _encrypt_config(self, config: dict) -> str:
        """Obfuscate (not true encryption) auth config for storage."""
        return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:32]
