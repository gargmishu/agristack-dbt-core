# AgriStack DBT Core: Sovereign Zero-Trust DPI Orchestrator & Governance Engine

[![Python: >=3.11](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checking: Mypy Strict](https://img.shields.io/badge/type%20checking-mypy%20strict-blue.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**AgriStack DBT Core** is a sovereign-aligned, Zero-Trust Direct Benefit Transfer (DBT) simulation and orchestration platform built on Digital Public Infrastructure (DPI) principles. It connects multi-channel citizen entry points (IVR Voice, WhatsApp Messaging, USSD Menu Signaling) with sovereign AI language blocks for intent and entity extraction, cross-matches claims against federated agricultural land registries, enforces deterministic governance routing, and interfaces with sovereign clearing rails with strict Zero-PII guarantees.

---

## 🏛️ Architectural Overview (4-Layer System)

> 📘 **Deep Dive:** For detailed Mermaid sequence and step-by-step pipeline diagrams from channel ingress to final decision, see the [End-to-End Architecture & Code Flow Guide](docs/end_to_end_code_flow.md).

```
[ Citizen Channels: WhatsApp | IVR Voice | USSD | SMS ]
                        │ (Raw carrier payloads: audio URLs, text, DTMF)
                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Channel Edge Connectors (`src/connectors/`)                   │
│ • WhatsAppConnector  • IvrConnector  • UssdConnector  • SmsConnector   │
└───────────────────────────────────────┬────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Gateway & Perimeter Security (`src/gateway/`)                 │
│ • CarrierAuthValidator (Webhook HMAC / Bearer verification)            │
│ • ZeroTrustIdentityTokenizer (RAM-only SHA-256 HMAC pseudonymization)  │
│ • PiiPurgeGuard (In-memory Zero-PII sanitizer & assertion sentinel)    │
│ • AdversarialPromptFirewall (Injection & override defense)             │
│ • RateLimiter (Token bucket quota guard)                               │
│ • PayloadCanonicalizer (Transforms raw ingress into canonical intake)  │
│ • IngestionFirewall (Unified perimeter security facade)                │
└───────────────────────────────────────┬────────────────────────────────┘
                                        │
                                        ▼ (PublicAgentStandardizedIntakePayload)
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Public Agent Intake Gateway (`src/public_agent/`)             │
│ • PublicAgentApi (Standardized event intake & schema gate)             │
│ • IntakePayloadEvaluator (Intent & structure level routing evaluator)  │
└───────────────────────────────────────┬────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 4: Orchestrator Brain & Governance (`src/orchestrator/`)         │
│ • ClaimOrchestrator (3-Gate workflow orchestration & pipeline coordinator) │
│ • ClaimAdjudicator (Automated Payout vs. Caseworker Review vs. Reject) │
│ • CaseManagementService (Internal review queues & OpenSPP ticket sync) │
└───────────────────────────────────────┬────────────────────────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────────────┐
│ Foundational AI Blocks   │ │ Multichannel Delivery    │ │ Authoritative Registries │
│ (`src/services/ai/`)     │ │ (`src/services/delivery/`)│ │ (`src/services/dpi/`)    │
│ • BhashiniService        │ │ • Multichannel-          │ │ • IdentityVerification   │
│   (ASR / NMT / TTS)      │ │   NotificationService    │ │ • AgriRegistryService    │
│ • SlmExtractor           │ │   (Adaptive 4-Channel    │ │ • SocialRegistryService  │
│ • ai_mock_fixtures       │ │    Dispatch Engine)      │ │ • PaymentRailService     │
└──────────────────────────┘ └──────────────────────────┘ └──────────────────────────┘
```

---

## 🔒 Zero-Trust Security & PII Architecture

1. **In-Memory RAM-Only Tokenization**: Cleartext citizen identifiers (MSISDN phone numbers, 12-digit Aadhaar IDs) are tokenized at the Layer 2 ingestion boundary using a cryptographically peppered SHA-256 HMAC function (`ZeroTrustIdentityTokenizer`). Raw PII is never persisted to disk or written to database ledgers.
2. **Zero-PII Purge Guard Sentinel**: `PiiPurgeGuard` strictly scans every canonicalized contract before passing into Layer 3, asserting that only 64-character hexadecimal HMAC tokens (`tokenized_citizen_id`) exist.
3. **Adversarial Prompt Injection Defense**: `AdversarialPromptFirewall` inspects text inputs for system overrides, role usurpation, delimiter hijacking, and database injection attempts. Flagged attempts immediately set AI confidence scores to `0.0` and wipe extracted entities (`validate_adversarial_zeroing`).
4. **Strict Immutability & Extra Key Prohibition**: All domain models inherit from `StrictBaseModel`, enforcing `extra="forbid"`, `frozen=True`, `str_strip_whitespace=True`, and `validate_assignment=True`.

---

## 📂 Repository Package Structure

```
agristack-dbt-core/
├── .agents/skills/coding-standards/ # Coding standards and design guidelines
├── decisions/                       # Architecture Decision Records (ADRs)
│   ├── step0.0_master_project_and_business_requirements.md
│   ├── step0.1_database_evaluation.md
│   ├── step0.2_data_model_design.md
│   ├── step0.3_zero_trust_tokenization.md
│   ├── step0.4_database_schema_design.md
│   ├── step1.1_tech_stack_evaluation.md
│   ├── step1.2_runtime_strictness_linting.md
│   ├── step2.0_canonical_domain_schemas.md
│   ├── step2.1_package_manager_and_dependencies.md
│   ├── step2.2_governance_flows_and_state_transitions.md
│   ├── step3.1_foundational_mock_boundaries.md
│   ├── step3.2_security_and_ingestion_firewalls.md
│   ├── step3.3_layer4_orchestrator_brain.md
│   ├── step3.4_layer3_intake_gateway_and_connectors.md
│   └── step3.5_adaptive_multichannel_confirmation_delivery.md
├── design-specs/                    # Declarative system specs & workflow schemas
│   ├── step0-env-readiness/
│   ├── step1-journey-channels/
│   ├── step2-data-schemas/schema.sql
│   ├── step2-system-dependencies/
│   ├── step3-guardrails/
│   ├── step4-dpi-workflow/
│   ├── step5-public-agent/
│   └── step6-metrics/
├── src/                             # Core Python application modules
│   ├── connectors/                  # Layer 1 Channel Edge Connectors
│   ├── gateway/                     # Layer 2 Gateway & Perimeter Security
│   ├── public_agent/                # Layer 3 Public Agent Intake Gateway
│   ├── orchestrator/                # Layer 4 Orchestrator Brain & Governance
│   ├── services/                    # Foundational AI, Delivery & DPI Services
│   │   ├── ai/                      # Bhashini ASR/NMT/TTS & SLM Entity Extractor
│   │   ├── delivery/                # Adaptive 4-Channel Notification Delivery Service
│   │   └── dpi/                     # Identity, Cadastral, OpenSPP & Payment Rails
│   ├── data_models/                 # Canonical Pydantic v2 schemas
│   │   ├── common/                  # StrictBaseModel, StrEnums, Constrained Types
│   │   ├── raw_ingress/             # WhatsApp, IVR, USSD raw carrier contracts
│   │   ├── public_agent/            # PublicAgentStandardizedIntakePayload
│   │   ├── governance/              # ExtractedEntityPayload, GovernanceOutcomePayload
│   │   ├── caseworker/              # CaseReviewPayload, ReviewOutcomePayload
│   │   ├── delivery/                # NotificationRequestPayload, OutboundNotificationPayload
│   │   └── disbursement/            # DisbursementCallbackPayload
│   └── errors/                      # RFC 7807 problem details exception handlers
├── tests/                           # Unit and integration test suite (1:1 mirror)
├── pyproject.toml                   # Build, dependencies, Ruff, Mypy, and Pytest configs
└── roadmap.md                       # Inside-Out Master Implementation Roadmap
```

---

## 🚀 Quickstart & Development

### Prerequisites
- **Python**: `>=3.11` (Python 3.11 or 3.13 recommended)
- **Virtual Environment**: `.venv`

### Environment Setup
```bash
# Set up virtual environment and install all runtime & dev dependencies
bash scripts/setup_environment.sh

# Activate virtual environment
source .venv/bin/activate
```

### Static Analysis & Testing
```bash
# Run pytest test suite
.venv/bin/pytest

# Run Ruff linter and formatter checks
.venv/bin/ruff check .
.venv/bin/ruff format --check .

# Run Mypy in strict type-checking mode
.venv/bin/mypy src tests
```

---

## 📜 Architectural Decisions (ADR Index)

| ADR Reference | Topic | Summary |
| :--- | :--- | :--- |
| [`step0.0`](decisions/step0.0_master_project_and_business_requirements.md) | Business Requirements | Master business rules and straight-through processing requirements. |
| [`step0.1`](decisions/step0.1_database_evaluation.md) | Database Evaluation | Relational DB evaluation against free-tier, JSONB, and DBT requirements. |
| [`step0.2`](decisions/step0.2_data_model_design.md) | Data Model Design | Entity normalization, cardinality, and physical table naming standards. |
| [`step0.3`](decisions/step0.3_zero_trust_tokenization.md) | Zero-Trust Tokenization | RAM-only cryptographic tokenization and zero-retention logging. |
| [`step0.4`](decisions/step0.4_database_schema_design.md) | Database Schema | Normalization, indexing strategies, audit triggers, and DBT analytical views. |
| [`step1.1`](decisions/step1.1_tech_stack_evaluation.md) | Tech Stack Selection | Application framework, SLM engine, and runtime evaluation. |
| [`step1.2`](decisions/step1.2_runtime_strictness_linting.md) | Runtime Strictness & Linting | Ruff, Mypy strict configuration, and code quality boundaries. |
| [`step2.0`](decisions/step2.0_canonical_domain_schemas.md) | Domain Contracts | Pydantic v2 domain schemas, constrained types, and truth tables. |
| [`step2.1`](decisions/step2.1_package_manager_and_dependencies.md) | Dependencies & Tooling | Package manager configuration, virtual environment, and dependency pins. |
| [`step2.2`](decisions/step2.2_governance_flows_and_state_transitions.md) | Governance Flows | 3-gate state machine, decision routing matrix, and caseworker lifecycle. |
| [`step3.1`](decisions/step3.1_foundational_mock_boundaries.md) | Mock Boundaries | Deterministic offline simulation fixtures for AI and DPI services. |
| [`step3.2`](decisions/step3.2_security_and_ingestion_firewalls.md) | Security Firewalls | Layer 2 perimeter firewall, rate limiting, and adversarial defense. |
| [`step3.3`](decisions/step3.3_layer4_orchestrator_brain.md) | Orchestrator Brain | 3-Gate evaluation pipeline, decision routing, and caseworker staging. |
| [`step3.4`](decisions/step3.4_layer3_intake_gateway_and_connectors.md) | Layer 3 Gateway & Connectors | Standardized event intake, structure evaluation, and carrier edge connectors. |
| [`step3.5`](decisions/step3.5_adaptive_multichannel_confirmation_delivery.md) | Multichannel Delivery | Adaptive outbound dispatch engine for WhatsApp, IVR, USSD, and SMS. |

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
