# AgriStack DBT Core: Sovereign Zero-Trust DPI Orchestrator & Governance Engine

[![Python: >=3.11](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checking: Mypy Strict](https://img.shields.io/badge/type%20checking-mypy%20strict-blue.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**AgriStack DBT Core** is a sovereign-aligned, Zero-Trust Direct Benefit Transfer (DBT) simulation and orchestration platform built on Digital Public Infrastructure (DPI) principles. It connects multi-channel citizen entry points (IVR Voice, WhatsApp Messaging, USSD Menu Signaling) with sovereign AI language blocks for intent and entity extraction, cross-matches claims against federated agricultural land registries, enforces deterministic governance routing, and interfaces with sovereign clearing rails with strict Zero-PII guarantees.

---

## 🏛️ Architectural Overview (4-Layer System)

> 📘 **Deep Dive:** For detailed Mermaid sequence and step-by-step pipeline diagrams from channel ingress to final decision, see the [End-to-End Architecture & Code Flow Guide](docs/end_to_end_code_flow.md).
> 🏛️ **Government Pilot Proposal:** For the 60-day single-district pilot blueprint, KPI matrix, and RFP procurement clauses, see the [Sovereign DPI Pilot Proposal](docs/government_pilot_proposal.md).

```
[ Citizen Channels: WhatsApp | IVR Voice | USSD | SMS ]
                        │ (Raw carrier payloads: audio URLs, text, DTMF)
                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Channel Edge Connectors                                       │
│ • WhatsApp Connector • IVR SIP Gateway • USSD Menu Adapter • SMS Relay │
└───────────────────────────────────────┬────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Perimeter Security Gateway                                    │
│ • Carrier Transport Authenticator (Webhook HMAC / Bearer verification) │
│ • Zero-Trust Identity Tokenizer (RAM-only SHA-256 HMAC pseudonymization)│
│ • PII Purge Sentinel (In-memory Zero-PII sanitizer & assertion guard)  │
│ • Adversarial Prompt Firewall (Injection & system override defense)    │
│ • Rate Limiter (Token bucket quota guard)                              │
│ • Payload Canonicalizer (Transforms raw ingress into canonical intake) │
│ • Perimeter Security Gateway (Unified perimeter security facade)       │
└───────────────────────────────────────┬────────────────────────────────┘
                                        │
                                        ▼ (Standardized Intake Contract)
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Public Agent Intake Gateway                                   │
│ • Public Agent Gateway (Perimeter event intake & workflow coordinator) │
│ • Intake Entity Extractor (Speech ASR, USSD bypass & SLM entity parsing)│
└───────────────────────────────────────┬────────────────────────────────┘
                                        │
                                        ▼ (Extracted Domain Entity Contract)
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 4: Orchestrator Brain & Governance                               │
│ • Claim Orchestration Engine (Completeness validation & policy engine) │
│ • Claim Policy Adjudicator (Automated Payout vs. Review vs. Reject)    │
│ • Case Management Service (Internal review queues & OpenSPP sync)      │
└───────────────────────────────────────┬────────────────────────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────────────┐
│ Sovereign AI Blocks      │ │ Multichannel Delivery    │ │ Authoritative Registries │
│ • Bhashini Services      │ │ • Adaptive Multi-Channel │ │ • Identity Verification  │
│   (ASR / NMT / TTS)      │ │   Notification Engine    │ │ • AgriRegistry Service   │
│ • Sovereign SLM Extractor│ │   (Adaptive 4-Channel    │ │ • SocialRegistry Service │
│ • Simulation Fixtures    │ │    Dispatch Engine)      │ │ • PaymentRail Service    │
└──────────────────────────┘ └──────────────────────────┘ └──────────────────────────┘
```

---

## 🔒 Zero-Trust Security & PII Architecture

1. **In-Memory RAM-Only Tokenization**: Cleartext citizen identifiers (MSISDN phone numbers, 12-digit Aadhaar IDs) are tokenized at the Layer 2 ingestion boundary using a cryptographically peppered SHA-256 HMAC function (*Zero-Trust Identity Tokenizer*). Raw PII is never persisted to disk or written to database ledgers.
2. **Carrier Callback Authentication**: Depending on the carrier integration, the perimeter verifies a request-body HMAC signature or checks the supplied `Authorization: Bearer` token against an explicitly configured shared secret. Bearer-token matching uses a constant-time comparison and rejects missing or malformed credentials. This check confirms possession of the shared secret; it does not encrypt traffic, authenticate the request body, or prevent replay. Use TLS, and retain request-signature verification where the carrier supports it.
3. **Zero-PII Purge Guard Sentinel**: The *PII Purge Sentinel* strictly scans every canonicalized contract before passing into Layer 3, asserting that only 64-character hexadecimal HMAC tokens (`tokenized_citizen_id`) exist.
4. **Adversarial Prompt Injection Defense**: The *Adversarial Prompt Firewall* inspects text inputs for system overrides, role usurpation, delimiter hijacking, and database injection attempts. Flagged attempts immediately neutralize AI confidence scores to `0.0` and wipe extracted entities.
5. **Strict Immutability & Extra Key Prohibition**: All domain models enforce strict immutability, extra key prohibition, whitespace stripping, and runtime type assignment validation.

---

## 📂 Repository Package Structure

```
agristack-dbt-core/
├── .agents/skills/                  # Agentic coding, modeling, security & documentation standards
│   ├── architecture-standards/
│   ├── coding-standards/
│   ├── documentation-standards/
│   ├── domain-modeling/
│   └── zero-trust-security/
├── decisions/                       # Architecture Decision Records (ADRs)
│   ├── step0.0_master_project_and_business_requirements.md
│   ├── step0.1_database_evaluation.md
│   ├── step0.2_data_model_design.md
│   ├── step0.3_hashing_algorithm_evaluation.md
│   ├── step0.3_token_service_README.md
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
│   ├── step3.5_adaptive_multichannel_confirmation_delivery.md
│   ├── step3.6_live_service_integration.md
│   ├── step3.6_speech_and_translation_evaluation.md
│   ├── step4.1_multichannel_ingress_and_modality_convergence.md
│   ├── step4.2_security_firewall_and_zero_trust_pii_auditing.md
│   ├── step4.3_three_gate_governance_and_conversational_loops.md
│   ├── step4.4_outbound_confirmation_and_financial_callbacks.md
│   └── step4.5_database_persistence_and_analytical_deduplication.md
├── design-specs/                    # Declarative system specs & workflow schemas
│   ├── step0-env-readiness/
│   ├── step1-journey-channels/
│   ├── step2-data-schemas/schema.sql
│   ├── step2-system-dependencies/
│   ├── step3-guardrails/
│   ├── step4-dpi-workflow/
│   ├── step5-public-agent/
│   └── step6-metrics/
├── docs/                            # End-to-end architecture flows & pilot blueprints
│   ├── end_to_end_code_flow.md
│   └── government_pilot_proposal.md
├── src/                             # Core Python application modules
│   ├── connectors/                  # Layer 1 Channel Edge Connectors
│   ├── gateway/                     # Layer 2 Gateway & Perimeter Security
│   ├── public_agent/                # Layer 3 Public Agent Intake Gateway
│   ├── orchestrator/                # Layer 4 Orchestrator Brain & Governance
│   ├── services/                    # Foundational AI, Notification, Persistence & DPI Services
│   │   ├── ai/                      # Bhashini ASR/NMT/TTS & SLM Entity Extractor
│   │   ├── notification/            # Adaptive 4-Channel Notification Dispatch Service
│   │   ├── persistence/             # Relational Ledger & Audit Persistence Service
│   │   └── dpi/                     # Identity, Cadastral, OpenSPP & Payment Rails
│   ├── data_models/                 # Canonical domain contracts
│   │   ├── common/                  # Base models, Enums, Constrained Types
│   │   ├── raw_ingress/             # WhatsApp, IVR, USSD raw carrier contracts
│   │   ├── public_agent/            # Standardized Intake Contracts
│   │   ├── governance/              # Governance Outcome & Entity Contracts
│   │   ├── caseworker/              # Case Review & Caseworker Adjudication Contracts
│   │   ├── notification/            # Outbound Notification & Request Contracts
│   │   └── disbursement/            # Payment Clearing Callback Contracts
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
| [`step0.3`](decisions/step0.3_hashing_algorithm_evaluation.md) | Hashing Evaluation | Cryptographic evaluation of SHA-256 HMAC vs. Argon2/Bcrypt for citizen tokens. |
| [`step0.3`](decisions/step0.3_token_service_README.md) | Token Service Architecture | Zero-Trust identity tokenizer design, pepper management, and RAM-only contracts. |
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
| [`step3.6`](decisions/step3.6_live_service_integration.md) | Live Service Integration | Live sovereign AI and DPI service adapters with dual-mode runtime switching. |
| [`step3.6`](decisions/step3.6_speech_and_translation_evaluation.md) | Speech & Translation Evaluation | Evaluation of Bhashini ASR/NMT/TTS pipelines and sovereign Indic language support. |
| [`step4.1`](decisions/step4.1_multichannel_ingress_and_modality_convergence.md) | Ingress Convergence | Multichannel ingress verification across audio and text modalities. |
| [`step4.2`](decisions/step4.2_security_firewall_and_zero_trust_pii_auditing.md) | Security & Zero-Trust PII | Automated security firewall, HMAC tokenization, and Zero-PII verification. |
| [`step4.3`](decisions/step4.3_three_gate_governance_and_conversational_loops.md) | Three-Gate & Loop Verification | Three-gate precedence, multi-turn conversational loops, and review escalation. |
| [`step4.4`](decisions/step4.4_outbound_confirmation_and_financial_callbacks.md) | Outbound & Financial Callbacks | Native confirmation dispatch and asynchronous bank disbursement webhooks. |
| [`step4.5`](decisions/step4.5_database_persistence_and_analytical_deduplication.md) | Persistence & Deduplication | Relational persistence, window-function deduplication, and audit history triggers. |

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
