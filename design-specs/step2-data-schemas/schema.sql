-- ==============================================================================
-- 1. TYPE DEFINITIONS (ENUMS)
-- ==============================================================================

CREATE TYPE ingress_channel_type AS ENUM (
    'WHATSAPP', 'IVR_VOICE', 'USSD'
);

CREATE TYPE session_status_enum AS ENUM (
    'ACTIVE', 'PENDING', 'COMPLETED', 'ABANDONED', 'TIMEOUT'
);

CREATE TYPE processing_state_enum AS ENUM (
    'STAGED', 'SUPERSEDED', 'COMMITTED'
);

CREATE TYPE application_status_enum AS ENUM (
    'DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'INFO_REQUESTED', 'APPROVED', 'REJECTED', 'APPEALED'
);

CREATE TYPE eligibility_status_enum AS ENUM (
    'PENDING_VERIFICATION', 'ELIGIBLE', 'INELIGIBLE', 'REQUIRES_REVIEW'
);

CREATE TYPE governance_action_enum AS ENUM (
    'AUTOMATED_PAYOUT', 'AUTO_APPROVE', 'AUTO_REJECT', 'HUMAN_REVIEW', 'ROUTE_FOR_MANUAL_REVIEW', 'REQUEST_MORE_INFO', 'MANUAL_APPROVE', 'MANUAL_REJECT'
);

CREATE TYPE disbursement_status_enum AS ENUM (
    'PENDING', 'INITIATED', 'SUCCESS', 'FAILED', 'RETURNED'
);

-- Consent registry stores tokenized consent pointers (no raw PII)
CREATE TYPE consent_status_enum AS ENUM (
    'GRANTED', 'REVOKED'
);

CREATE TYPE revocation_reason_enum AS ENUM (
    'EXPLICIT_USER_REVOCATION',
    'EXPLICIT_SYSTEM_REVOCATION',
    'NATURAL_EXPIRATION'
);

CREATE TYPE consent_scope_enum AS ENUM (
    'IDENTITY_VERIFICATION',
    'DATA_PROCESSING'
);

-- ==============================================================================
-- 2. TABLE DEFINITIONS
-- ==============================================================================

-- Parent Entity
CREATE TABLE session_telemetry_log (
    session_id UUID PRIMARY KEY,
    tokenized_phone_hash VARCHAR(64) NOT NULL,
    ingress_channel ingress_channel_type NOT NULL,
    session_status session_status_enum NOT NULL,
    session_active BOOLEAN GENERATED ALWAYS AS (session_status = 'ACTIVE') STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Child of session_telemetry_log
CREATE TABLE session_extraction_details (
    payload_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES session_telemetry_log(session_id) ON DELETE CASCADE,
    attempt_id INTEGER NOT NULL CHECK (attempt_id > 0),
    raw_unstructured_text TEXT NOT NULL,
    standardized_english_text TEXT,
    extraction_confidence DECIMAL(4, 3) CHECK (extraction_confidence >= 0.000 AND extraction_confidence <= 1.000),
    extracted_district VARCHAR(100),
    extracted_crop_type VARCHAR(100),
    reported_anomaly VARCHAR(200),
    processing_state processing_state_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_attempt UNIQUE (session_id, attempt_id)
);

-- Child of session_extraction_details & session_telemetry_log
CREATE TABLE application_governance_ledger (
    claim_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES session_telemetry_log(session_id),
    payload_id UUID NOT NULL REFERENCES session_extraction_details(payload_id),
    tokenized_identity_hash VARCHAR(64) NOT NULL,
    application_status application_status_enum NOT NULL,
    claimant_eligibility_status eligibility_status_enum NOT NULL,
    governance_action governance_action_enum,
    evaluated_at TIMESTAMPTZ,
    disbursement_status disbursement_status_enum,
    governance_metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Safety Nets: JSONB Type Constraints
    CONSTRAINT chk_approval_amount_type CHECK (
        governance_metadata->'approval_amount' IS NULL OR jsonb_typeof(governance_metadata->'approval_amount') = 'number'
    ),
    CONSTRAINT chk_rejection_reason_type CHECK (
        governance_metadata->'rejection_reason' IS NULL OR jsonb_typeof(governance_metadata->'rejection_reason') = 'string'
    ),
    
    -- Business Logic: Terminal Decision Constraints
    CONSTRAINT chk_approval_requires_amount CHECK (
        governance_action NOT IN ('AUTO_APPROVE', 'AUTOMATED_PAYOUT', 'MANUAL_APPROVE') OR (governance_metadata ? 'approval_amount')
    ),
    CONSTRAINT chk_rejection_requires_reason CHECK (
        governance_action NOT IN ('AUTO_REJECT', 'MANUAL_REJECT') OR (governance_metadata ? 'rejection_reason')
    )
);

-- Audit Entity
CREATE TABLE application_governance_ledger_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES application_governance_ledger(claim_id) ON DELETE CASCADE,
    previous_application_status application_status_enum NULL,
    new_application_status application_status_enum NOT NULL,
    governance_action governance_action_enum,
    actor_id VARCHAR(100) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Consent registry: links tokenized identifiers to consent records
-- Tracks explicit consent for sensitive data access (e.g., identity verification)
-- Consent lifetime is tied to session lifecycle: expires when session ends or immediately if revoked
-- Provenance stores audit trail: consent method, form version, device info, consent timestamp, confirmation token
CREATE TABLE consent_registry (
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session_telemetry_log(session_id) ON DELETE CASCADE,
    tokenized_phone_hash VARCHAR(64),
    tokenized_identity_hash VARCHAR(64),
    consent_status consent_status_enum NOT NULL,
    consent_scope consent_scope_enum[] NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '10 minutes'),
    source ingress_channel_type NOT NULL,
    consent_version TEXT,
    provenance JSONB DEFAULT '{"consent_method": null, "form_version": null, "device_fingerprint": null, "confirmation_token": null}'::jsonb,
    revoked_at TIMESTAMPTZ,
    revocation_reason revocation_reason_enum,
    -- Ensure exactly one token type is provided
    CONSTRAINT chk_one_token_provided CHECK (
        (tokenized_phone_hash IS NOT NULL AND tokenized_identity_hash IS NULL) 
        OR (tokenized_phone_hash IS NULL AND tokenized_identity_hash IS NOT NULL)
    ),
    -- Revocation reason only valid if revoked_at is set
    CONSTRAINT chk_revocation_consistency CHECK (
        (revoked_at IS NOT NULL AND revocation_reason IS NOT NULL) 
        OR (revoked_at IS NULL AND revocation_reason IS NULL)
    )
);

-- ==============================================================================
-- PROVENANCE DOCUMENTATION (Consent Audit Trail)
-- ==============================================================================
-- Provenance JSONB structure captures regulatory-required consent metadata:
--
-- Example structure:
-- {
--   "consent_method": "WHATSAPP_BUTTON_CLICK",       -- How consent was given (button, voice confirmation, etc.)
--   "form_version": "v1.2",                          -- Which consent form/policy version was shown
--   "device_fingerprint": "abc123def456",            -- Anonymized device identifier
--   "user_agent": "WhatsApp/2.26.1",                 -- Client application info
--   "consent_timestamp_utc": "2026-07-14T10:30:15Z", -- Precise moment of consent
--   "confirmation_token": "tok_xyz789",              -- Unique proof/receipt of consent
--   "ip_address_country": "IN",                      -- Anonymized to country level only
--   "consent_language": "HI"                         -- Language in which consent was presented
-- }
--
-- Note: NO raw IP addresses, phone numbers, or Aadhaar hashes stored here.
--       Sensitive fields are anonymized or omitted to prevent secondary exposure.

-- ==============================================================================
-- 3. INDEXES (Optimized for BI & Fast API Lookups)
-- ==============================================================================

-- Drop-off Prevention / Chatbot Session Resume (Partial Index)
CREATE INDEX idx_active_session_resume 
ON session_telemetry_log (tokenized_phone_hash, created_at DESC) 
WHERE session_status = 'ACTIVE';

-- Analytics Deduplication
CREATE INDEX idx_session_extraction_session_attempt 
ON session_extraction_details (session_id, attempt_id DESC);

-- Operational Visibility / Funnel Joins
CREATE INDEX idx_application_governance_session 
ON application_governance_ledger (session_id, evaluated_at DESC);

-- Double-Dipping Fraud Prevention / Status API
CREATE INDEX idx_governance_identity_lookup 
ON application_governance_ledger (tokenized_identity_hash, evaluated_at DESC);

-- SLA Time-in-State Tracking
CREATE INDEX idx_governance_history_claim_time 
ON application_governance_ledger_history (claim_id, changed_at DESC);


-- Index for checking active consent (not expired, not explicitly revoked)
CREATE INDEX idx_consent_active ON consent_registry (tokenized_phone_hash, tokenized_identity_hash, expires_at, revoked_at) 
WHERE revoked_at IS NULL AND expires_at > NOW();

-- Index for token-based consent lookups
CREATE INDEX idx_consent_identity ON consent_registry (tokenized_identity_hash) 
WHERE tokenized_identity_hash IS NOT NULL;

-- ==============================================================================
-- 4. DATABASE TRIGGERS (Immutable Audit Trail)
-- ==============================================================================

CREATE OR REPLACE FUNCTION log_governance_ledger_history()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO application_governance_ledger_history (
        claim_id,
        previous_application_status,
        new_application_status,
        governance_action,
        actor_id,
        changed_at
    ) VALUES (
        NEW.claim_id,
        OLD.application_status, 
        NEW.application_status,
        NEW.governance_action,
        COALESCE(NEW.governance_metadata->>'reviewer_id', 'SYSTEM:DEFAULT'),
        COALESCE(NEW.evaluated_at, NOW())
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger captures state changes (AFTER UPDATE)
CREATE TRIGGER trg_audit_governance_ledger_update
AFTER UPDATE OF application_status, governance_action ON application_governance_ledger
FOR EACH ROW
WHEN (OLD.application_status IS DISTINCT FROM NEW.application_status OR OLD.governance_action IS DISTINCT FROM NEW.governance_action)
EXECUTE FUNCTION log_governance_ledger_history();

-- Trigger captures initial claim creation (AFTER INSERT)
CREATE TRIGGER trg_audit_governance_ledger_insert
AFTER INSERT ON application_governance_ledger
FOR EACH ROW
EXECUTE FUNCTION log_governance_ledger_history();

-- ==============================================================================
-- 5. ANALYTICS VIEWS (Schema Contracts for DBT / BI)
-- ==============================================================================

-- 5.1 Deduplication Filter
CREATE OR REPLACE VIEW staging_committed_extractions AS
SELECT * 
FROM session_extraction_details 
WHERE processing_state = 'COMMITTED';

-- 5.2 JSON Unpacking (Schema Contract)
CREATE OR REPLACE VIEW staging_flattened_governance_ledger AS
SELECT 
    claim_id,
    session_id,
    payload_id,
    tokenized_identity_hash,
    application_status,
    claimant_eligibility_status,
    governance_action,
    evaluated_at,
    disbursement_status,
    (governance_metadata->>'approval_amount')::numeric AS approval_amount,
    (governance_metadata->>'rejection_reason')::text AS rejection_reason,
    (governance_metadata->>'reviewer_id')::text AS reviewer_id,
    (governance_metadata->>'review_notes')::text AS review_notes,
    (governance_metadata->>'fraud_flag_code')::text AS fraud_flag_code,
    (governance_metadata->>'disbursement_txn_id')::text AS disbursement_txn_id,
    ARRAY(SELECT jsonb_array_elements_text(governance_metadata->'missing_info_fields')) AS missing_info_fields
FROM application_governance_ledger;

-- 5.3 The Unified Dashboard View (OBT)
CREATE OR REPLACE VIEW citizen_journey_funnel AS
SELECT 
    t.session_id,
    t.tokenized_phone_hash,
    t.ingress_channel,
    t.session_status,
    t.created_at AS session_started_at,
    t.completed_at AS session_completed_at,
    e.payload_id,
    e.extracted_district,
    e.extracted_crop_type,
    e.reported_anomaly,
    e.extraction_confidence,
    g.claim_id,
    g.tokenized_identity_hash,
    g.application_status,
    g.claimant_eligibility_status,
    g.governance_action,
    g.evaluated_at,
    g.disbursement_status,
    g.approval_amount,
    g.rejection_reason,
    g.fraud_flag_code,
    g.disbursement_txn_id
FROM session_telemetry_log t
LEFT JOIN staging_committed_extractions e 
    ON t.session_id = e.session_id
LEFT JOIN staging_flattened_governance_ledger g 
    ON e.payload_id = g.payload_id;

-- 5.4 Active Consent Status (Consent is valid if: granted, not revoked, and expires_at is in future or NULL while session active)
CREATE OR REPLACE VIEW active_consent_registry AS
SELECT 
    cr.*,
    st.session_status,
    CASE 
        WHEN cr.consent_status = 'GRANTED' 
        AND cr.revoked_at IS NULL 
        AND (cr.expires_at > NOW() OR (cr.expires_at IS NULL AND st.session_status = 'ACTIVE')) 
        THEN TRUE
        ELSE FALSE
    END AS is_consent_active
FROM consent_registry cr
INNER JOIN session_telemetry_log st ON cr.session_id = st.session_id;