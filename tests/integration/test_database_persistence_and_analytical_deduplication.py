"""Integration tests for Step 4.5: Database Persistence & Analytical Deduplication.

Executes relational persistence and analytical deduplication test suites verifying:
1. Schema DDL Completeness & Zero-PII Invariants: Verifies
   design-specs/step2-data-schemas/schema.sql defines all required tables, immutable audit triggers,
   partial indexes, analytical views, and 64-character SHA-256 HMAC token columns.
2. Multi-Attempt Conversational Deduplication: Executes SQL window-function deduplication queries
   (ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY attempt_id DESC) = 1 / QUALIFY pattern)
   and COMMITTED state views against multi-turn conversational logs (attempts 1, 2, 3), proving
   zero cartesian fan-out in downstream BI joins.
3. Terminal Constraint & Audit History Invariants: Verifies terminal approval/rejection metadata
   constraints and immutable audit trail generation.

See: decisions/step4.5_database_persistence_and_analytical_deduplication.md
See: design-specs/step2-data-schemas/schema.sql
See: roadmap.md (Phase 4 Step 4.5)
"""

import json
import sqlite3
from pathlib import Path
from typing import Final

import pytest

SCHEMA_SQL_PATH: Final[Path] = (
    Path(__file__).resolve().parents[2] / "design-specs" / "step2-data-schemas" / "schema.sql"
)
SQLITE_SCHEMA_SQL_PATH: Final[Path] = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "services"
    / "persistence"
    / "schema"
    / "sqlite_schema.sql"
)
VALID_CITIZEN_HMAC_ONE: Final[str] = (
    "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105
)
VALID_CITIZEN_HMAC_TWO: Final[str] = (
    "f9e8d7c6b5a4938271605f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c"  # noqa: S105
)
EXPECTED_HMAC_HEX_LENGTH: Final[int] = 64


def _create_in_memory_relational_schema(connection: sqlite3.Connection) -> None:
    """Initializes in-memory relational tables, triggers, and views from sqlite_schema.sql."""
    connection.executescript(SQLITE_SCHEMA_SQL_PATH.read_text(encoding="utf-8"))
    connection.commit()


# =============================================================================
# 1. Schema DDL Completeness & Zero-PII Structural Verification
# =============================================================================


def test_schema_sql_ddl_completeness_and_zero_pii_invariants() -> None:
    """Verifies schema.sql defines all required tables, views, triggers, and zero-PII columns."""
    assert SCHEMA_SQL_PATH.exists(), f"Missing schema.sql at {SCHEMA_SQL_PATH}"
    schema_content = SCHEMA_SQL_PATH.read_text(encoding="utf-8")

    # 1. Required Transactional & Audit Tables
    required_tables = (
        "CREATE TABLE session_telemetry_log",
        "CREATE TABLE session_extraction_details",
        "CREATE TABLE application_governance_ledger",
        "CREATE TABLE application_governance_ledger_history",
        "CREATE TABLE consent_registry",
    )
    for table_ddl in required_tables:
        assert table_ddl in schema_content, f"Missing table definition: {table_ddl}"

    # 2. Required Analytical Views & OBT Funnel
    required_views = (
        "CREATE OR REPLACE VIEW staging_committed_extractions",
        "CREATE OR REPLACE VIEW staging_flattened_governance_ledger",
        "CREATE OR REPLACE VIEW citizen_journey_funnel",
        "CREATE OR REPLACE VIEW active_consent_registry",
    )
    for view_ddl in required_views:
        assert view_ddl in schema_content, f"Missing analytical view definition: {view_ddl}"

    # 3. Required Audit Triggers & Deduplication Indexes
    assert "CREATE TRIGGER trg_audit_governance_ledger_insert" in schema_content
    assert "CREATE TRIGGER trg_audit_governance_ledger_update" in schema_content
    assert "CREATE INDEX idx_session_extraction_session_attempt" in schema_content
    assert "CREATE INDEX idx_governance_identity_lookup" in schema_content

    # 4. Zero-PII Column Invariants (Strict 64-character SHA-256 HMAC tokens)
    assert "tokenized_phone_hash VARCHAR(64) NOT NULL" in schema_content
    assert "tokenized_identity_hash VARCHAR(64) NOT NULL" in schema_content
    assert "chk_approval_requires_amount" in schema_content
    assert "chk_rejection_requires_reason" in schema_content


# =============================================================================
# 2. Multi-Turn Conversational Persistence & Window-Function Deduplication
# =============================================================================


def test_relational_persistence_and_multi_attempt_analytical_deduplication() -> None:
    """Verifies window-function deduplication (ROW_NUMBER() OVER) eliminates multi-turn fan-out."""
    connection = sqlite3.connect(":memory:")
    _create_in_memory_relational_schema(connection)
    cursor = connection.cursor()

    # Insert Session 1: Completed 3-turn loop (Attempts 1 & 2 SUPERSEDED, 3 COMMITTED)
    cursor.execute(
        """
        INSERT INTO session_telemetry_log (
            session_id, tokenized_phone_hash, ingress_channel, session_status,
            created_at, completed_at
        ) VALUES (
            ?, ?, 'WHATSAPP', 'COMPLETED', '2026-09-11T10:00:00Z', '2026-09-11T10:03:00Z'
        )
        """,
        ("sess-3turn-001", VALID_CITIZEN_HMAC_ONE),
    )

    multi_turn_extractions = [
        (
            "payload-turn-1",
            "sess-3turn-001",
            1,
            "Mera fasal kharab ho gaya hai",
            0.55,
            None,
            None,
            "SUPERSEDED",
            "2026-09-11T10:00:10Z",
        ),
        (
            "payload-turn-2",
            "sess-3turn-001",
            2,
            "Mera zila Karnal hai",
            0.72,
            "Karnal",
            None,
            "SUPERSEDED",
            "2026-09-11T10:01:20Z",
        ),
        (
            "payload-turn-3",
            "sess-3turn-001",
            3,
            "Zila Karnal aur fasal Wheat hai, survey 101/2",
            0.96,
            "Karnal",
            "Wheat",
            "COMMITTED",
            "2026-09-11T10:02:45Z",
        ),
    ]
    cursor.executemany(
        """
        INSERT INTO session_extraction_details (
            payload_id, session_id, attempt_id, raw_unstructured_text,
            extraction_confidence, extracted_district, extracted_crop_type,
            processing_state, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        multi_turn_extractions,
    )

    # Insert Governance Ledger entry for the final committed turn (attempt 3)
    approval_metadata = json.dumps(
        {
            "approval_amount": 15000.0,
            "disbursement_txn_id": "TXN-2026-778899",
            "reviewer_id": "SYSTEM:AUTO_ADJUDICATOR",
        }
    )
    cursor.execute(
        """
        INSERT INTO application_governance_ledger (
            claim_id, session_id, payload_id, tokenized_identity_hash,
            application_status, claimant_eligibility_status, governance_action,
            evaluated_at, disbursement_status, governance_metadata
        ) VALUES (
            ?, ?, ?, ?, 'APPROVED', 'ELIGIBLE', 'AUTO_APPROVE',
            '2026-09-11T10:03:00Z', 'PENDING', ?
        )
        """,
        (
            "claim-001",
            "sess-3turn-001",
            "payload-turn-3",
            VALID_CITIZEN_HMAC_ONE,
            approval_metadata,
        ),
    )

    # Insert Session 2: Abandoned 2-turn loop (Turn 1 SUPERSEDED, Turn 2 STAGED)
    cursor.execute(
        """
        INSERT INTO session_telemetry_log (
            session_id, tokenized_phone_hash, ingress_channel, session_status,
            created_at, completed_at
        ) VALUES (?, ?, 'IVR_VOICE', 'ABANDONED', '2026-09-11T11:00:00Z', NULL)
        """,
        ("sess-abandoned-002", VALID_CITIZEN_HMAC_TWO),
    )
    cursor.executemany(
        """
        INSERT INTO session_extraction_details (
            payload_id, session_id, attempt_id, raw_unstructured_text,
            extraction_confidence, extracted_district, extracted_crop_type,
            processing_state, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "payload-s2-turn-1",
                "sess-abandoned-002",
                1,
                "Unclear voice audio transcript",
                0.40,
                None,
                None,
                "SUPERSEDED",
                "2026-09-11T11:00:15Z",
            ),
            (
                "payload-s2-turn-2",
                "sess-abandoned-002",
                2,
                "Zila Pune, fasal missing",
                0.65,
                "Pune",
                None,
                "STAGED",
                "2026-09-11T11:01:05Z",
            ),
        ],
    )
    connection.commit()

    # 1. Verify raw extraction table contains all 5 conversational turns across both sessions
    raw_count = cursor.execute("SELECT COUNT(*) FROM session_extraction_details").fetchone()[0]
    assert raw_count == 5  # noqa: PLR2004

    # 2. Execute Analytical Deduplication Query (QUALIFY ROW_NUMBER() OVER pattern)
    # Selects strictly the latest attempt per session ordered by attempt_id DESC
    deduplicated_rows = cursor.execute(
        """
        WITH ranked_extractions AS (
            SELECT
                session_id,
                payload_id,
                attempt_id,
                extracted_district,
                extracted_crop_type,
                extraction_confidence,
                processing_state,
                ROW_NUMBER() OVER (
                    PARTITION BY session_id
                    ORDER BY attempt_id DESC
                ) AS attempt_rank
            FROM session_extraction_details
        )
        SELECT
            session_id,
            payload_id,
            attempt_id,
            extracted_district,
            extracted_crop_type,
            processing_state
        FROM ranked_extractions
        WHERE attempt_rank = 1
        ORDER BY session_id ASC
        """
    ).fetchall()

    # Deduplication strictly returns 2 rows (1 canonical row per session, zero fan-out)
    assert len(deduplicated_rows) == 2  # noqa: PLR2004
    assert deduplicated_rows[0] == (
        "sess-3turn-001",
        "payload-turn-3",
        3,
        "Karnal",
        "Wheat",
        "COMMITTED",
    )
    assert deduplicated_rows[1] == (
        "sess-abandoned-002",
        "payload-s2-turn-2",
        2,
        "Pune",
        None,
        "STAGED",
    )

    # 3. Verify Unified Citizen Journey Funnel View (OBT) has zero fan-out
    funnel_rows = cursor.execute(
        """
        SELECT
            session_id,
            attempt_id,
            extracted_district,
            extracted_crop_type,
            governance_action,
            approval_amount
        FROM citizen_journey_funnel
        ORDER BY session_id ASC
        """
    ).fetchall()

    assert len(funnel_rows) == 2  # noqa: PLR2004
    assert funnel_rows[0] == ("sess-3turn-001", 3, "Karnal", "Wheat", "AUTO_APPROVE", 15000.0)
    assert funnel_rows[1] == ("sess-abandoned-002", None, None, None, None, None)

    connection.close()


# =============================================================================
# 3. Terminal Constraints & Immutable Audit History Triggers Verification
# =============================================================================


def test_governance_ledger_terminal_constraints_and_audit_history() -> None:
    """Verifies terminal JSON constraints and automatic history trigger population."""
    connection = sqlite3.connect(":memory:")
    _create_in_memory_relational_schema(connection)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO session_telemetry_log (
            session_id, tokenized_phone_hash, ingress_channel, session_status, created_at
        ) VALUES ('sess-audit-001', ?, 'SMS', 'COMPLETED', '2026-09-11T12:00:00Z')
        """,
        (VALID_CITIZEN_HMAC_ONE,),
    )
    cursor.execute(
        """
        INSERT INTO session_extraction_details (
            payload_id, session_id, attempt_id, raw_unstructured_text,
            extraction_confidence, processing_state, created_at
        ) VALUES (
            'payload-audit-001', 'sess-audit-001', 1, 'Sanitized text',
            0.91, 'COMMITTED', '2026-09-11T12:00:10Z'
        )
        """
    )

    # 1. Terminal Constraint: AUTO_APPROVE without approval_amount fails CHECK
    invalid_approval_metadata = json.dumps({"reviewer_id": "SYSTEM:AUTO"})
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO application_governance_ledger (
                claim_id, session_id, payload_id, tokenized_identity_hash,
                application_status, claimant_eligibility_status, governance_action,
                evaluated_at, governance_metadata
            ) VALUES (
                'claim-bad-1', 'sess-audit-001', 'payload-audit-001', ?,
                'APPROVED', 'ELIGIBLE', 'AUTO_APPROVE', '2026-09-11T12:01:00Z', ?
            )
            """,
            (VALID_CITIZEN_HMAC_ONE, invalid_approval_metadata),
        )

    # 2. Terminal Constraint: AUTO_REJECT without rejection_reason fails CHECK
    invalid_rejection_metadata = json.dumps({"reviewer_id": "SYSTEM:AUTO"})
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO application_governance_ledger (
                claim_id, session_id, payload_id, tokenized_identity_hash,
                application_status, claimant_eligibility_status, governance_action,
                evaluated_at, governance_metadata
            ) VALUES (
                'claim-bad-2', 'sess-audit-001', 'payload-audit-001', ?,
                'REJECTED', 'INELIGIBLE', 'AUTO_REJECT', '2026-09-11T12:01:00Z', ?
            )
            """,
            (VALID_CITIZEN_HMAC_ONE, invalid_rejection_metadata),
        )

    # 3. Valid Insert -> Triggers Immutable Audit History Entry #1 (UNDER_REVIEW)
    initial_metadata = json.dumps({"reviewer_id": "SYSTEM:INTAKE_GATE"})
    cursor.execute(
        """
        INSERT INTO application_governance_ledger (
            claim_id, session_id, payload_id, tokenized_identity_hash,
            application_status, claimant_eligibility_status, governance_action,
            evaluated_at, governance_metadata
        ) VALUES (
            'claim-good-1', 'sess-audit-001', 'payload-audit-001', ?,
            'UNDER_REVIEW', 'REQUIRES_REVIEW', 'ROUTE_FOR_MANUAL_REVIEW',
            '2026-09-11T12:01:00Z', ?
        )
        """,
        (VALID_CITIZEN_HMAC_ONE, initial_metadata),
    )

    # 4. Caseworker Manual Approval Update -> Triggers Immutable Audit History Entry #2 (APPROVED)
    manual_approval_metadata = json.dumps(
        {
            "approval_amount": 18000.0,
            "reviewer_id": "CASEWORKER:OFFICER_702",
        }
    )
    cursor.execute(
        """
        UPDATE application_governance_ledger
        SET application_status = 'APPROVED',
            governance_action = 'MANUAL_APPROVE',
            evaluated_at = '2026-09-11T12:15:00Z',
            governance_metadata = ?
        WHERE claim_id = 'claim-good-1'
        """,
        (manual_approval_metadata,),
    )
    connection.commit()

    # 5. Verify Immutable History Table captured both transitions accurately
    history_rows = cursor.execute(
        """
        SELECT
            previous_application_status,
            new_application_status,
            governance_action,
            actor_id
        FROM application_governance_ledger_history
        WHERE claim_id = 'claim-good-1'
        ORDER BY history_id ASC
        """
    ).fetchall()

    assert len(history_rows) == 2  # noqa: PLR2004
    assert history_rows[0] == (
        None,
        "UNDER_REVIEW",
        "ROUTE_FOR_MANUAL_REVIEW",
        "SYSTEM:INTAKE_GATE",
    )
    assert history_rows[1] == (
        "UNDER_REVIEW",
        "APPROVED",
        "MANUAL_APPROVE",
        "CASEWORKER:OFFICER_702",
    )

    connection.close()
