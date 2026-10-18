CREATE TABLE IF NOT EXISTS session_telemetry_log (
    session_id TEXT PRIMARY KEY,
    tokenized_phone_hash TEXT NOT NULL CHECK (length(tokenized_phone_hash) = 64),
    ingress_channel TEXT NOT NULL
        CHECK (ingress_channel IN ('WHATSAPP', 'IVR_VOICE', 'USSD', 'SMS')),
    session_status TEXT NOT NULL
        CHECK (session_status IN ('ACTIVE', 'PENDING', 'COMPLETED', 'ABANDONED', 'TIMEOUT')),
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS session_extraction_details (
    payload_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session_telemetry_log(session_id) ON DELETE CASCADE,
    attempt_id INTEGER NOT NULL CHECK (attempt_id > 0),
    raw_unstructured_text TEXT NOT NULL,
    extraction_confidence REAL NOT NULL
        CHECK (extraction_confidence >= 0.0 AND extraction_confidence <= 1.0),
    extracted_district TEXT,
    extracted_crop_type TEXT,
    processing_state TEXT NOT NULL
        CHECK (processing_state IN ('STAGED', 'SUPERSEDED', 'COMMITTED')),
    created_at TEXT NOT NULL,
    UNIQUE (session_id, attempt_id)
);

CREATE TABLE IF NOT EXISTS application_governance_ledger (
    claim_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session_telemetry_log(session_id),
    payload_id TEXT NOT NULL REFERENCES session_extraction_details(payload_id),
    tokenized_identity_hash TEXT NOT NULL CHECK (length(tokenized_identity_hash) = 64),
    application_status TEXT NOT NULL,
    claimant_eligibility_status TEXT NOT NULL,
    governance_action TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    disbursement_status TEXT,
    governance_metadata TEXT NOT NULL DEFAULT '{}',
    CHECK (
        governance_action NOT IN ('AUTO_APPROVE', 'AUTOMATED_PAYOUT', 'MANUAL_APPROVE')
        OR json_extract(governance_metadata, '$.approval_amount') IS NOT NULL
    ),
    CHECK (
        governance_action NOT IN ('AUTO_REJECT', 'MANUAL_REJECT')
        OR json_extract(governance_metadata, '$.rejection_reason') IS NOT NULL
    )
);

CREATE TABLE IF NOT EXISTS application_governance_ledger_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL
        REFERENCES application_governance_ledger(claim_id) ON DELETE CASCADE,
    previous_application_status TEXT,
    new_application_status TEXT NOT NULL,
    governance_action TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    changed_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS trg_audit_governance_ledger_insert
AFTER INSERT ON application_governance_ledger
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
        NULL,
        NEW.application_status,
        NEW.governance_action,
        COALESCE(json_extract(NEW.governance_metadata, '$.reviewer_id'), 'SYSTEM:DEFAULT'),
        NEW.evaluated_at
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_governance_ledger_update
AFTER UPDATE OF application_status, governance_action ON application_governance_ledger
WHEN OLD.application_status IS NOT NEW.application_status
  OR OLD.governance_action IS NOT NEW.governance_action
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
        COALESCE(json_extract(NEW.governance_metadata, '$.reviewer_id'), 'SYSTEM:DEFAULT'),
        NEW.evaluated_at
    );
END;
