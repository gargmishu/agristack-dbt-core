"""Offline Mock Fixtures for Authoritative DPI Registries (Step 3.1).

Defines deterministic validation thresholds, simulated failure prefixes, and mock status responses
for identity, cadastral, social welfare, and payment rail services during offline simulation.
"""

UNVERIFIED_IDENTITY_TOKEN_ZERO = "0" * 64
UNVERIFIED_IDENTITY_PREFIX = "ffff0000"

INVALID_LAND_RECORD_PREFIX = "INVALID"
INVALID_SURVEY_NUMBER = "000/0"

MOCK_CASE_REJECT_PREFIX = "SPP-CASE-REJECT"
MOCK_FAIL_STAGE_NOTE = "fail_stage"

MOCK_PAYMENT_FAIL_TRIGGER = "FAIL"
MOCK_PAYMENT_FAILURE_REASON = "ERR_INSUFFICIENT_BANK_ACCOUNT_MAPPING"
