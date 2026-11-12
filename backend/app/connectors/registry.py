"""Connector registry.

Loads connectors from the database and instantiates them.
Manages the mapping between connector name and implementation class.
"""
from __future__ import annotations

import json
from typing import Any

from ..database import transaction
from .base import ConnectorBase, ConnectorError

# Connector name -> implementation class path
# All implementations live in app.connectors.implementations.__init__
BUILTIN_IMPLEMENTATIONS: dict[str, str] = {
    "wikipedia": "app.connectors.implementations.WikipediaConnector",
    "github": "app.connectors.implementations.GitHubConnector",
    "nasa": "app.connectors.implementations.NASASpaceConnector",
    "openalex": "app.connectors.implementations.OpenAlexConnector",
    "arxiv": "app.connectors.implementations.ArXivConnector",
    "newsapi": "app.connectors.implementations.NewsAPIConnector",
    "gdel": "app.connectors.implementations.GDELTConnector",
    "tmdb": "app.connectors.implementations.TMDBConnector",
    "musicbrainz": "app.connectors.implementations.MusicBrainzConnector",
    "openlibrary": "app.connectors.implementations.OpenLibraryConnector",
    "weather": "app.connectors.implementations.WeatherConnector",
    "currency": "app.connectors.implementations.CurrencyConnector",
    "crossref": "app.connectors.implementations.CrossrefConnector",
    "spaceflight": "app.connectors.implementations.SpaceflightConnector",
    "wikidata": "app.connectors.implementations.WikidataConnector",
    "npm": "app.connectors.implementations.NPMConnector",
    "pypi": "app.connectors.implementations.PyPIConnector",
    "dockerhub": "app.connectors.implementations.DockerHubConnector",
    "stackexchange": "app.connectors.implementations.StackExchangeConnector",
    "tvmaze": "app.connectors.implementations.TVMazeConnector",
    "github_api": "app.connectors.implementations.GitHubAPIConnector",
    "countries": "app.connectors.implementations.CountriesConnector",
    "usgs": "app.connectors.implementations.USGSConnector",
    "wikivoyage": "app.connectors.implementations.WikivoyageConnector",
    "guardian": "app.connectors.implementations.GuardianConnector",
    "spotify": "app.connectors.implementations.SpotifyConnector",
    "rss": "app.connectors.implementations.RSSConnector",
}


class ConnectorRegistry:
    """Registry of all available connectors.

    Loads connector metadata from the database and instantiates connectors
    on demand with their saved auth configuration.
    """

    def __init__(self):
        self._connectors: dict[str, ConnectorBase] = {}
        self._metadata_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Metadata (from database)
    # ------------------------------------------------------------------
    def list_connectors(self) -> list[dict]:
        """Return metadata for all connectors in the database."""
        with transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM connectors ORDER BY category, display_name"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_connector_metadata(self, connector_id: int) -> dict | None:
        with transaction() as conn:
            row = conn.execute(
                "SELECT * FROM connectors WHERE id = ?", (connector_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_connector_by_name(self, name: str) -> dict | None:
        with transaction() as conn:
            row = conn.execute(
                "SELECT * FROM connectors WHERE name = ?", (name,)
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Connector instantiation
    # ------------------------------------------------------------------
    def get_connector(self, connector_id: int) -> ConnectorBase:
        """Instantiate (or return cached) connector by DB id."""
        if connector_id in self._connectors:
            return self._connectors[connector_id]

        meta = self.get_connector_metadata(connector_id)
        if meta is None:
            raise ConnectorError(f"Connector id {connector_id} not found", status_code=404)

        name = meta["name"]
        class_path = BUILTIN_IMPLEMENTATIONS.get(name)
        if class_path is None:
            # Generic connector - no real implementation, just metadata
            raise ConnectorError(
                f"Connector '{name}' has no implementation yet", status_code=501
            )

        module_name, class_name = class_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        connector_class = getattr(module, class_name)

        # Load saved auth config
        auth_config = None
        with transaction() as conn:
            row = conn.execute(
                """SELECT auth_config FROM connector_connections
                   WHERE connector_id = ? AND is_connected = 1 LIMIT 1""",
                (connector_id,),
            ).fetchone()
            if row and row["auth_config"]:
                # In production this would be decrypted; here we store a placeholder
                auth_config = {"configured": True}

        connector = connector_class(auth_config)
        self._connectors[connector_id] = connector
        return connector

    def get_connector_by_name_instance(self, name: str) -> ConnectorBase:
        meta = self.get_connector_by_name(name)
        if meta is None:
            raise ConnectorError(f"Connector '{name}' not found", status_code=404)
        return self.get_connector(meta["id"])

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------
    def list_connections(self) -> list[dict]:
        with transaction() as conn:
            rows = conn.execute(
                """SELECT cc.*, c.name AS connector_name, c.display_name
                   FROM connector_connections cc
                   JOIN connectors c ON cc.connector_id = c.id
                   ORDER BY c.display_name, cc.name"""
            ).fetchall()
        return [dict(r) for r in rows]

    def create_connection(
        self,
        connector_id: int,
        name: str,
        auth_config: dict,
    ) -> dict:
        with transaction() as conn:
            # Verify connector exists
            row = conn.execute(
                "SELECT id FROM connectors WHERE id = ?", (connector_id,)
            ).fetchone()
            if row is None:
                raise ConnectorError(f"Connector id {connector_id} not found", status_code=404)

            # Test the connection before saving
            try:
                connector = self.get_connector(connector_id)
                # Temporarily set auth config for testing
                connector.auth_config = auth_config
                result = connector.test_connection()
                if not result.success:
                    conn.execute(
                        """INSERT INTO connector_connections
                           (connector_id, name, auth_config, is_connected, test_ok, test_error, created_at, updated_at)
                           VALUES (?, ?, ?, 0, 0, ?, datetime('now'), datetime('now'))""",
                        (connector_id, name, connector._encrypt_config(auth_config), result.error or "Connection test failed"),
                    )
                    conn.commit()
                    cc_id = conn.execute(
                        "SELECT last_insert_rowid()".format()
                    ).fetchone()[0]
                    return {
                        "id": cc_id,
                        "connector_id": connector_id,
                        "name": name,
                        "is_connected": False,
                        "test_ok": False,
                        "test_error": result.error,
                    }
            except ConnectorError as exc:
                raise exc

            # Connection successful - save
            conn.execute(
                """INSERT INTO connector_connections
                   (connector_id, name, auth_config, is_connected, test_ok, test_error, created_at, updated_at)
                   VALUES (?, ?, ?, 1, 1, NULL, datetime('now'), datetime('now'))""",
                (connector_id, name, connector._encrypt_config(auth_config)),
            )
            conn.commit()
            cc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        return {
            "id": cc_id,
            "connector_id": connector_id,
            "name": name,
            "is_connected": True,
            "test_ok": True,
            "test_error": None,
        }

    def test_connection(self, connection_id: int) -> dict:
        with transaction() as conn:
            row = conn.execute(
                """SELECT cc.*, c.name AS connector_name FROM connector_connections cc
                   JOIN connectors c ON cc.connector_id = c.id
                   WHERE cc.id = ?""",
                (connection_id,),
            ).fetchone()
            if row is None:
                raise ConnectorError(f"Connection id {connection_id} not found", status_code=404)

        connector = self.get_connector(row["connector_id"])
        # Rebuild auth config - in production decrypt here
        result = connector.test_connection()

        conn.execute(
            """UPDATE connector_connections
               SET is_connected = ?, test_ok = ?, test_error = ?,
                   last_tested_at = datetime('now'), updated_at = datetime('now')
               WHERE id = ?""",
            (1 if result.success else 0, 1 if result.success else 0,
             result.error, connection_id),
        )
        conn.commit()

        return {
            "id": connection_id,
            "connector_id": row["connector_id"],
            "connector_name": row["connector_name"],
            "is_connected": result.success,
            "test_ok": result.success,
            "test_error": result.error,
        }

    def delete_connection(self, connection_id: int) -> bool:
        with transaction() as conn:
            row = conn.execute(
                "SELECT id FROM connector_connections WHERE id = ?", (connection_id,)
            ).fetchone()
            if row is None:
                return False
            conn.execute("DELETE FROM connector_connections WHERE id = ?", (connection_id,))
            conn.commit()
        return True

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute_operation(
        self,
        connector_id: int,
        operation: str,
        params: dict | None = None,
        connection_id: int | None = None,
    ) -> dict:
        connector = self.get_connector(connector_id)

        try:
            result = connector.execute_operation(operation, params or {})
        except ConnectorError as exc:
            raise exc

        # Log execution
        with transaction() as conn:
            conn.execute(
                """INSERT INTO connector_executions
                   (connection_id, connector_id, operation, status, input, output, error, started_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
                (
                    connection_id,
                    connector_id,
                    operation,
                    "completed" if result.success else "failed",
                    json.dumps(params or {}),
                    json.dumps(result.data) if result.data else None,
                    result.error,
                ),
            )
            conn.commit()

        return result.to_dict()

    def list_executions(self, connector_id: int | None = None, limit: int = 50) -> list[dict]:
        with transaction() as conn:
            if connector_id:
                rows = conn.execute(
                    """SELECT ce.*, c.name AS connector_name FROM connector_executions ce
                       JOIN connectors c ON ce.connector_id = c.id
                       WHERE ce.connector_id = ?
                       ORDER BY ce.started_at DESC LIMIT ?""",
                    (connector_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT ce.*, c.name AS connector_name FROM connector_executions ce
                       JOIN connectors c ON ce.connector_id = c.id
                       ORDER BY ce.started_at DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]
