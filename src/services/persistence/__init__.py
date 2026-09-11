"""Relational Database Persistence & Analytical Deduplication Service Package.

Provides dual-mode relational database persistence (PostgreSQL for cloud/MeghRaj pilots
and SQLite for local/offline field demonstrations) enforcing Zero-Trust PII invariants,
immutable governance audit triggers, and window-function analytical deduplication.
"""

from src.services.persistence.ledger_persistence_service import LedgerPersistenceService

__all__ = ["LedgerPersistenceService"]
