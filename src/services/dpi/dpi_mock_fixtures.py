"""Offline Mock Fixtures for Authoritative DPI Registries (Step 3.1).

Defines deterministic validation thresholds, simulated failure prefixes, and mock status responses
for identity, cadastral, social welfare, and payment rail services during offline simulation.

Why deterministic offline mocks?
Under our Inside-Out development methodology, foundational external dependency boundaries must be
completely simulated in memory with zero network calls and predictable data structures. This
prevents dangling wire dependencies during Layer 4 state machine construction and eliminates network
latency during automated verification.

See: decisions/step3.1_foundational_mock_boundaries.md
See: roadmap.md (Phase 3 Step 3.1)
"""

from typing import NamedTuple

UNVERIFIED_IDENTITY_TOKEN_ZERO = "0" * 64
UNVERIFIED_IDENTITY_PREFIX = "ffff0000"

INVALID_LAND_RECORD_PREFIX = "INVALID"
INVALID_SURVEY_NUMBER = "000/0"

MOCK_CASE_REJECT_PREFIX = "SPP-CASE-REJECT"
MOCK_FAIL_STAGE_NOTE = "fail_stage"

MOCK_PAYMENT_FAIL_TRIGGER = "FAIL"
MOCK_PAYMENT_FAILURE_REASON = "ERR_INSUFFICIENT_BANK_ACCOUNT_MAPPING"


class MockCadastralParcel(NamedTuple):
    """Immutable cadastral plot entity for offline AgriStack land registry simulations.

    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.2)
    """

    survey_number: str
    district: str
    taluka: str
    village: str
    owner_hmac_prefix: str
    is_entitled: bool


MOCK_CADASTRAL_REGISTRY: dict[str, MockCadastralParcel] = {
    "LAND-REC-1002": MockCadastralParcel(
        survey_number="124/2A",
        district="Pune",
        taluka="Haveli",
        village="Hadoli",
        owner_hmac_prefix="a1b2c3d4",
        is_entitled=True,
    ),
    "LAND-REC-2004": MockCadastralParcel(
        survey_number="45/1B",
        district="Karnal",
        taluka="Nilokheri",
        village="Sultanpur",
        owner_hmac_prefix="e5f60718",
        is_entitled=True,
    ),
    "LAND-REC-3006": MockCadastralParcel(
        survey_number="99/4C",
        district="Nashik",
        taluka="Dindori",
        village="Palkhed",
        owner_hmac_prefix="c9d8e7f6",
        is_entitled=False,
    ),
}
