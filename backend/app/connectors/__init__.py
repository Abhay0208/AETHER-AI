"""AETHER connectors package - data source and integration ecosystem.

Phase 7: 100+ modular connectors for external data sources and integrations.
Categories:
- Space and Science
- News and Information
- Media and Entertainment
- Development
- Knowledge
- Other (Weather, Currency, Maps, Translation, Government, Financial, Educational)
"""
from .base import ConnectorBase, ConnectorError, ConnectorResult, ConnectorCategory
from .registry import ConnectorRegistry
from .builtin import BUILTIN_CONNECTORS

__all__ = [
    "ConnectorBase",
    "ConnectorError",
    "ConnectorResult",
    "ConnectorCategory",
    "ConnectorRegistry",
    "BUILTIN_CONNECTORS",
]
