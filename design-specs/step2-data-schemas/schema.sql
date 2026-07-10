-- Step 0.4 implementation: schema DDL and staging deduplication SQL
-- Conforms to the data model defined in decisions/data_model_design.md
-- and the zero-retention rules from roadmap.md Step 0.3.

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE TYPE IF NOT EXISTS ingress_channel_type AS ENUM ('WHATSAPP', 'IVR_VOICE', 'USSD');

-- Parent table: session lifecycle and channel ingress telemetry.
CREATE TABLE IF NOT EXISTS session_telemetry_log (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tokenized_phone_hash VARCHAR(64) NOT NULL,
    ingress_channel ingress_channel_type NOT NULL,
    session_status VARCHAR(30) NOT NULL CHECK (
        session_status IN (
            'ACTIVE',
            'COMPLETED_SUCCESSFULLY',
            'FAILED_GATEWAY_TIMEOUT',
            'USER_HANGUP',
            'ABORTED_INCOMPLETE',
            'ROUTED_AWAY_GRIEVANCE'
        )
    ),
    session_active BOOLEAN GENERATED ALWAYS AS (session_status = 'ACTIVE') STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_session_resume_lookup
    ON session_telemetry_log (tokenized_phone_hash, session_status, created_at DESC);

-- Child table: sequential extraction attempts and AI retry loops.
CREATE TABLE IF NOT EXISTS session_extraction_details (
    payload_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session_telemetry_log(session_id) ON DELETE CASCADE,
    attempt_id INTEGER NOT NULL CHECK (attempt_id > 0),
    raw_unstructured_text TEXT,
    standardized_english_text TEXT,
    extraction_confidence DECIMAL(4, 3) CHECK (extraction_confidence BETWEEN 0.000 AND 1.000),
    extracted_district VARCHAR(100),
    extracted_crop_type VARCHAR(100),
    extracted_reported_anomaly VARCHAR(200),
    processing_state VARCHAR(20) NOT NULL CHECK (processing_state IN ('STAGED', 'SUPERSEDED', 'COMMITTED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    committed_at TIMESTAMPTZ,
    UNIQUE (session_id, attempt_id)
);

CREATE INDEX IF NOT EXISTS idx_session_extraction_session_attempt
    ON session_extraction_details (session_id, attempt_id DESC);

-- Child table: business claim outcomes and governance decisions.
CREATE TABLE IF NOT EXISTS application_governance_ledger (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session_telemetry_log(session_id) ON DELETE CASCADE,
    payload_id UUID REFERENCES session_extraction_details(payload_id) ON DELETE SET NULL,
    tokenized_identity_hash VARCHAR(64) NOT NULL,
    application_status VARCHAR(30) NOT NULL CHECK (
        application_status IN ('FILED', 'APPROVED', 'REJECTED', 'UNDER_REVIEW', 'APPEALED', 'CLOSED')
    ),
    openspp_case_id VARCHAR(50),
    eligibility_status VARCHAR(30) NOT NULL CHECK (
        eligibility_status IN ('ELIGIBLE', 'INELIGIBLE', 'FUZZY_MATCH')
    ),
    governance_decision VARCHAR(30) NOT NULL CHECK (
        governance_decision IN ('AUTOMATED_PAYOUT', 'CASEWORKER_REVIEW', 'AUTO_REJECTED')
    ),
    rejection_reason VARCHAR(255),
    approval_amount DECIMAL(10, 2),
    disbursement_transaction_id VARCHAR(100),
    caseworker_notes TEXT,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_application_governance_session
    ON application_governance_ledger (session_id, decided_at DESC);

-- Staging view for deduplication of repeated correction loops.
-- This keeps the latest committed extraction event per session for downstream analytics.
CREATE OR REPLACE VIEW staging_latest_extraction_attempts AS
WITH ranked_attempts AS (
    SELECT
        sed.payload_id,
        sed.session_id,
        sed.attempt_id,
        sed.raw_unstructured_text,
        sed.standardized_english_text,
        sed.extraction_confidence,
        sed.extracted_district,
        sed.extracted_crop_type,
        sed.extracted_reported_anomaly,
        sed.processing_state,
        ROW_NUMBER() OVER (
            PARTITION BY sed.session_id
            ORDER BY sed.attempt_id DESC, sed.created_at DESC, sed.payload_id DESC
        ) AS rn
    FROM session_extraction_details AS sed
    WHERE sed.processing_state = 'COMMITTED'
)
SELECT
    payload_id,
    session_id,
    attempt_id,
    raw_unstructured_text,
    standardized_english_text,
    extraction_confidence,
    extracted_district,
    extracted_crop_type,
    extracted_reported_anomaly,
    processing_state
FROM ranked_attempts
WHERE rn = 1;

COMMIT;
