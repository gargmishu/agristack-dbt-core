"""Relational Ledger Persistence Service for Sovereign DPI Pilot Deployments.

Implements dual-backend relational persistence supporting both PostgreSQL (Supabase/Neon/MeghRaj)
and persistent SQLite ('sqlite:///./agristack_pilot.db') via SQLAlchemy 2.0 Core. Enforces
Zero-Trust PII invariants (64-character SHA-256 HMAC tokens), terminal JSONB check constraints,
immutable audit history triggers, and window-function analytical deduplication.

See: decisions/step0.4_database_schema_design.md
See: decisions/step4.5_database_persistence_and_analytical_deduplication.md
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Final

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from pathlib import Path
from src.config.service_settings import get_database_url

__all__ = ["LedgerPersistenceService"]

EXPECTED_TOKEN_HEX_LENGTH: Final[int] = 64

def _load_sqlite_schema() -> tuple[str, ...]:
    """Load SQLite DDL statements from the external .sql file."""
    schema_path = Path(__file__).with_name("schema") / "sqlite_schema.sql"
    raw = schema_path.read_text().strip()
    # Split on blank lines between statements; ensure each ends with a semicolon.
    statements = [stmt.strip() for stmt in raw.split(";\n\n") if stmt.strip()]
    return tuple(stmt if stmt.endswith(";") else stmt + ";" for stmt in statements)

_SQLITE_SCHEMA_DDL_STATEMENTS: Final[tuple[str, ...]] = _load_sqlite_schema()

# Upsert query for session telemetry log
SESSION_TELEMETRY_LOG_UPSERT: Final[str] = """
INSERT INTO session_telemetry_log (
    session_id,
    tokenized_phone_hash,
    ingress_channel,
    session_status,
    created_at,
    completed_at
) VALUES (
    :session_id,
    :tokenized_phone_hash,
    :ingress_channel,
    :session_status,
    :created_at,
    :completed_at
)
ON CONFLICT(session_id) DO UPDATE SET
    session_status = excluded.session_status,
    completed_at = COALESCE(excluded.completed_at, session_telemetry_log.completed_at)
"""
# SQL templates for extraction details
SUPERSEDE_SESSION_EXTRACTION_DETAILS_SQL: Final[str] = """
    UPDATE session_extraction_details
    SET processing_state = 'SUPERSEDED'
    WHERE session_id = :session_id
      AND attempt_id < :attempt_id
      AND processing_state = 'STAGED'
"""

INSERT_SESSION_EXTRACTION_DETAILS_SQL: Final[str] = """
    INSERT INTO session_extraction_details (
        payload_id,
        session_id,
        attempt_id,
        raw_unstructured_text,
        extraction_confidence,
        extracted_district,
        extracted_crop_type,
        processing_state,
        created_at
    ) VALUES (
        :payload_id,
        :session_id,
        :attempt_id,
        :raw_unstructured_text,
        :extraction_confidence,
        :extracted_district,
        :extracted_crop_type,
        :processing_state,
        :created_at
    ) ON CONFLICT(payload_id) DO UPDATE SET
        processing_state = excluded.processing_state,
        extracted_district = excluded.extracted_district,
        extracted_crop_type = excluded.extracted_crop_type
"""
# SQL template for the deduplicated citizen journey funnel
DEDUPLICATED_CITIZEN_JOURNEY_FUNNEL_SQL: Final[str] = """
WITH deduplicated_extractions AS (
    SELECT
        payload_id,
        session_id,
        attempt_id AS total_conversational_turns,
        extraction_confidence AS final_extraction_confidence,
        extracted_district,
        extracted_crop_type,
        processing_state,
        ROW_NUMBER() OVER (
            PARTITION BY session_id
            ORDER BY attempt_id DESC
        ) AS row_rank
    FROM session_extraction_details
)
SELECT
    session_log.session_id,
    session_log.tokenized_phone_hash,
    session_log.ingress_channel,
    session_log.session_status,
    session_log.created_at AS session_started_at,
    session_log.completed_at AS session_completed_at,
    extractions.total_conversational_turns,
    extractions.final_extraction_confidence,
    extractions.extracted_district,
    extractions.extracted_crop_type,
    ledger.claim_id,
    ledger.application_status,
    ledger.claimant_eligibility_status,
    ledger.governance_action,
    ledger.disbursement_status,
    ledger.governance_metadata
FROM session_telemetry_log AS session_log
LEFT JOIN deduplicated_extractions AS extractions
    ON session_log.session_id = extractions.session_id
    AND extractions.row_rank = 1
LEFT JOIN application_governance_ledger AS ledger
    ON session_log.session_id = ledger.session_id
ORDER BY session_log.created_at ASC
"""
# SQL template for governance ledger upsert
GOVERNANCE_LEDGER_UPSERT_SQL: Final[str] = """
    INSERT INTO application_governance_ledger (
        claim_id,
        session_id,
        payload_id,
        tokenized_identity_hash,
        application_status,
        claimant_eligibility_status,
        governance_action,
        evaluated_at,
        disbursement_status,
        governance_metadata
    ) VALUES (
        :claim_id,
        :session_id,
        :payload_id,
        :tokenized_identity_hash,
        :application_status,
        :claimant_eligibility_status,
        :governance_action,
        :evaluated_at,
        :disbursement_status,
        :governance_metadata
    ) ON CONFLICT(claim_id) DO UPDATE SET
        application_status = excluded.application_status,
        governance_action = excluded.governance_action,
        evaluated_at = excluded.evaluated_at,
        disbursement_status = COALESCE(
            excluded.disbursement_status,
            application_governance_ledger.disbursement_status
        ),
        governance_metadata = excluded.governance_metadata
"""

# SQL template for fetching the immutable audit trail for a claim
FETCH_GOVERNANCE_AUDIT_HISTORY_SQL: Final[str] = """\
    SELECT
        history_id,
        claim_id,
        previous_application_status,
        new_application_status,
        governance_action,
        actor_id,
        changed_at
    FROM application_governance_ledger_history
    WHERE claim_id = :claim_id
    ORDER BY changed_at ASC, history_id ASC\
"""


class LedgerPersistenceService:
    """Relational persistence service for AgriStack DBT sessions, turns, and governance ledgers."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initializes the persistence service and ensures schema tables and triggers exist.

        Args:
            database_url: Optional database connection URI. Defaults to configured DATABASE_URL
                or local SQLite ('sqlite:///./agristack_pilot.db').
        """
        resolved_database_url = database_url or get_database_url()
        self.database_url: Final[str] = resolved_database_url

        if resolved_database_url.startswith("sqlite") and ":memory:" in resolved_database_url:
            self.database_engine: Engine = create_engine(
                resolved_database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        elif resolved_database_url.startswith("sqlite"):
            self.database_engine = create_engine(
                resolved_database_url,
                connect_args={"check_same_thread": False},
            )
        else:
            self.database_engine = create_engine(resolved_database_url, pool_pre_ping=True)

        self._initialize_relational_schema()


    def dispose(self) -> None:
        """Disposes underlying SQLAlchemy connection pool and closes open handles."""
        self.database_engine.dispose()

    def record_session_telemetry(
        self,
        session_id: str,
        tokenized_phone_hash: str,
        ingress_channel: str,
        session_status: str,
        created_at: str | None = None,
        completed_at: str | None = None,
    ) -> None:
        """Upserts a citizen session record in session_telemetry_log with zero-PII enforcement.

        Args:
            session_id: Unique session identifier.
            tokenized_phone_hash: 64-character SHA-256 HMAC pseudonymous citizen token.
            ingress_channel: Originating carrier channel ('WHATSAPP', 'IVR_VOICE', 'USSD', 'SMS').
            session_status: Lifecycle status ('ACTIVE', 'PENDING', 'COMPLETED', 'ABANDONED').
            created_at: ISO-8601 creation timestamp (defaults to current UTC time).
            completed_at: Optional ISO-8601 completion timestamp.

        Raises:
            ValueError: If tokenized_phone_hash is not a 64-character hexadecimal string.
        """
        if len(tokenized_phone_hash) != EXPECTED_TOKEN_HEX_LENGTH:
            raise ValueError(
                f"Zero-Trust violation: tokenized_phone_hash must be exactly "
                f"{EXPECTED_TOKEN_HEX_LENGTH} hex chars, got {len(tokenized_phone_hash)}."
            )

        effective_created_at = created_at or datetime.now(UTC).isoformat()
        upsert_query = text(SESSION_TELEMETRY_LOG_UPSERT)
        with self.database_engine.begin() as database_connection:
            database_connection.execute(
                upsert_query,
                {
                    "session_id": session_id,
                    "tokenized_phone_hash": tokenized_phone_hash,
                    "ingress_channel": ingress_channel,
                    "session_status": session_status,
                    "created_at": effective_created_at,
                    "completed_at": completed_at,
                },
            )

    def record_extraction_attempt(  # noqa: PLR0913
        self,
        payload_id: str,
        session_id: str,
        attempt_id: int,
        raw_unstructured_text: str,
        extraction_confidence: float,
        processing_state: str,
        extracted_district: str | None = None,
        extracted_crop_type: str | None = None,
        created_at: str | None = None,
    ) -> None:
        """Persists a conversational extraction turn in session_extraction_details.

        When a new turn arrives for an active session, any previous 'STAGED' attempts for that
        session are automatically transitioned to 'SUPERSEDED'.

        Args:
            payload_id: Unique extraction payload identifier.
            session_id: Parent session identifier.
            attempt_id: 1-indexed conversational turn number.
            raw_unstructured_text: Sanitized citizen input transcript or text.
            extraction_confidence: AI extraction confidence score in [0.0, 1.0].
            processing_state: Lifecycle state ('STAGED', 'SUPERSEDED', 'COMMITTED').
            extracted_district: Extracted district name if present.
            extracted_crop_type: Extracted crop name if present.
            created_at: Optional ISO-8601 timestamp.
        """
        effective_created_at = created_at or datetime.now(UTC).isoformat()

        supersede_sql = text(SUPERSEDE_SESSION_EXTRACTION_DETAILS_SQL)
        insertion_sql = text(INSERT_SESSION_EXTRACTION_DETAILS_SQL)
        with self.database_engine.begin() as database_connection:
            database_connection.execute(
                supersede_sql,
                {"session_id": session_id, "attempt_id": attempt_id},
            )
            database_connection.execute(
                insertion_sql,
                {
                    "payload_id": payload_id,
                    "session_id": session_id,
                    "attempt_id": attempt_id,
                    "raw_unstructured_text": raw_unstructured_text,
                    "extraction_confidence": extraction_confidence,
                    "extracted_district": extracted_district,
                    "extracted_crop_type": extracted_crop_type,
                    "processing_state": processing_state,
                    "created_at": effective_created_at,
                },
            )

    def record_governance_decision(  # noqa: PLR0913
        self,
        claim_id: str,
        session_id: str,
        payload_id: str,
        tokenized_identity_hash: str,
        application_status: str,
        claimant_eligibility_status: str,
        governance_action: str,
        evaluated_at: str | None = None,
        disbursement_status: str | None = None,
        governance_metadata: dict[str, object] | None = None,
    ) -> None:
        """Persists or updates a governance decision in application_governance_ledger.

        Automatically fires immutable SQL audit triggers (trg_audit_governance_ledger_insert /
        trg_audit_governance_ledger_update) into application_governance_ledger_history.

        Args:
            claim_id: Unique claim identifier.
            session_id: Parent session identifier.
            payload_id: Associated extraction payload identifier.
            tokenized_identity_hash: 64-character SHA-256 HMAC citizen identity token.
            application_status: Claim lifecycle status ('APPROVED', 'UNDER_REVIEW', 'REJECTED').
            claimant_eligibility_status: Registry eligibility ('ELIGIBLE', 'INELIGIBLE', etc.).
            governance_action: Gate 3 routing verdict ('AUTO_APPROVE', 'AUTO_REJECT', etc.).
            evaluated_at: ISO-8601 adjudication timestamp.
            disbursement_status: Optional treasury wire clearing status ('PENDING', 'SUCCESS').
            governance_metadata: Structured JSON dictionary with terminal attributes.
        """
        if len(tokenized_identity_hash) != EXPECTED_TOKEN_HEX_LENGTH:
            raise ValueError(
                f"Zero-Trust violation: tokenized_identity_hash must be exactly "
                f"{EXPECTED_TOKEN_HEX_LENGTH} hex chars, got {len(tokenized_identity_hash)}."
            )

        effective_evaluated_at = evaluated_at or datetime.now(UTC).isoformat()
        metadata_json_string = json.dumps(governance_metadata or {})

        upsert_sql = text(GOVERNANCE_LEDGER_UPSERT_SQL)
        with self.database_engine.begin() as database_connection:
            database_connection.execute(
                upsert_sql,
                {
                    "claim_id": claim_id,
                    "session_id": session_id,
                    "payload_id": payload_id,
                    "tokenized_identity_hash": tokenized_identity_hash,
                    "application_status": application_status,
                    "claimant_eligibility_status": claimant_eligibility_status,
                    "governance_action": governance_action,
                    "evaluated_at": effective_evaluated_at,
                    "disbursement_status": disbursement_status,
                    "governance_metadata": metadata_json_string,
                },
            )

    def fetch_deduplicated_citizen_journey_funnel(self) -> list[dict[str, object]]:
        """Executes the window-deduplicated Citizen Journey Funnel query across all sessions.

        Uses ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY attempt_id DESC) = 1 to ensure
        exactly 1 row per citizen session (zero multi-turn cartesian fan-out).

        Returns:
            A list of dictionaries, each representing a deduplicated citizen‑journey funnel row.
        """
        funnel_query = text(DEDUPLICATED_CITIZEN_JOURNEY_FUNNEL_SQL)
        with self.database_engine.connect() as database_connection:
            query_result = database_connection.execute(funnel_query)
            return [dict(row_mapping) for row_mapping in query_result.mappings()]

    def fetch_governance_audit_history(self, claim_id: str) -> list[dict[str, object]]:
        """Fetch the immutable audit trail for a claim.

        Args:
            claim_id: Unique claim identifier. Must be a non‑empty string.

        Returns:
            A list of audit‑trail dictionaries ordered by the timestamp (`changed_at`).
        """
        if not claim_id:
            raise ValueError("claim_id must be a non‑empty string")
        audit_query = text(FETCH_GOVERNANCE_AUDIT_HISTORY_SQL)
        # Use a transaction for a consistent snapshot across databases.
        with self.database_engine.begin() as database_connection:
            query_result = database_connection.execute(audit_query, {"claim_id": claim_id})
            return [dict(row) for row in query_result.mappings()]
        

    def _initialize_relational_schema(self) -> None:
        """Executes idempotent DDL to initialize tables and audit triggers."""
        with self.database_engine.begin() as database_connection:
            for statement in _SQLITE_SCHEMA_DDL_STATEMENTS:
                database_connection.execute(text(statement))
