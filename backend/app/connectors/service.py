"""Connector service - bridges database with connector registry.

Handles connector metadata storage, connection management, operation execution,
and execution logging.
"""
from __future__ import annotations

import json
import os
from typing import Any

from ..database import transaction
from ..config import PROJECT_ROOT
from .registry import ConnectorRegistry
from .base import ConnectorError


class ConnectorService:
    def __init__(self):
        self.registry = ConnectorRegistry()
        self._seeded = False

    # ------------------------------------------------------------------
    # Initialization - seed built-in connectors into DB
    # ------------------------------------------------------------------
    def ensure_seeded(self):
        """Seed built-in connector definitions into the database on first run."""
        if self._seeded:
            return
        self._seeded = True
        from .builtin import BUILTIN_CONNECTORS

        with transaction() as conn:
            existing = conn.execute("SELECT name FROM connectors").fetchall()
            existing_names = {r["name"] for r in existing}

            for name, meta in BUILTIN_CONNECTORS.items():
                if name in existing_names:
                    continue
                conn.execute(
                    """INSERT INTO connectors
                       (name, display_name, description, category, category_label,
                        documentation, auth_required, auth_type, auth_field_name,
                        free_paid, rate_limit, rate_limit_unit, base_url,
                        operations, capabilities, is_enabled, is_builtin,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1,
                               datetime('now'), datetime('now'))""",
                    (
                        meta["name"],
                        meta["display_name"],
                        meta["description"],
                        meta["category"],
                        meta["category_label"],
                        meta.get("description"),
                        int(meta.get("auth_required", False)),
                        meta.get("auth_type"),
                        meta.get("auth_field_name"),
                        meta.get("free_paid", "free"),
                        meta.get("rate_limit"),
                        meta.get("rate_limit_unit"),
                        meta.get("base_url"),
                        json.dumps(meta.get("operations", [])),
                        json.dumps(meta.get("capabilities", [])),
                    ),
                )
            conn.commit()

    # ------------------------------------------------------------------
    # Connector metadata
    # ------------------------------------------------------------------
    def list_connectors(self, category: str | None = None) -> list[dict]:
        self.ensure_seeded()
        with transaction() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM connectors WHERE category = ? ORDER BY display_name",
                    (category,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM connectors ORDER BY category, display_name"
                ).fetchall()
        return [dict(r) for r in rows]

    def list_categories(self) -> list[dict]:
        """Return connector categories."""
        from .builtin import CATEGORIES
        return CATEGORIES

    def get_connector(self, connector_id: int) -> dict | None:
        self.ensure_seeded()
        return self.registry.get_connector_metadata(connector_id)

    def get_connector_by_name(self, name: str) -> dict | None:
        self.ensure_seeded()
        return self.registry.get_connector_by_name(name)

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------
    def list_connections(self) -> list[dict]:
        self.ensure_seeded()
        return self.registry.list_connections()

    def create_connection(
        self,
        connector_id: int,
        name: str,
        auth_config: dict,
    ) -> dict:
        self.ensure_seeded()
        return self.registry.create_connection(connector_id, name, auth_config)

    def test_connection(self, connection_id: int) -> dict:
        self.ensure_seeded()
        return self.registry.test_connection(connection_id)

    def delete_connection(self, connection_id: int) -> bool:
        self.ensure_seeded()
        return self.registry.delete_connection(connection_id)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute_operation(
        self,
        connector_id: int,
        operation: str,
        params: dict | None = None,
        connection_id: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        self.ensure_seeded()
        return self.registry.execute_operation(connector_id, operation, params, connection_id)

    def list_executions(
        self,
        connector_id: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        self.ensure_seeded()
        return self.registry.list_executions(connector_id, limit)
