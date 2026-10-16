# End-to-End Architecture & Workflow: Citizen Ingress to Outcome Delivery

This document traces a citizen interaction through the **AgriStack DBT Core** Zero-Trust architecture: channel ingress, secure intake, governance evaluation, outcome handling, and citizen notification. It distinguishes the synchronous interaction from asynchronous payment settlement and treats persistence as cross-cutting rather than a final runtime step.

The detailed flow follows meaningful runtime boundaries rather than forcing a fixed number of stages: channel ingress and perimeter security, Layer 3 intake, Layer 4 validation and adjudication, and outcome handling. Persistence and analytics are shown separately because they span or follow those runtime boundaries.

---

## 1. Master End-to-End Sequence Diagram

The master view shows the major system handoffs. Modality and governance branches are detailed under their lifecycle boundaries below. Payment settlement is asynchronous and separate from the citizen request path.

```mermaid
sequenceDiagram
    autonumber
    actor Citizen as Citizen
    participant L1 as Layer 1<br/>Channels
    participant L2 as Layer 2<br/>Security
    participant L3 as Layer 3<br/>Intake
    participant AI as AI Services<br/>ASR / SLM
    participant L4 as Layer 4<br/>Governance
    participant DPI as DPI<br/>Registries
    participant Deliv as Notification<br/>Delivery

    %% Channel ingress
    Citizen->>L1: Submit Citizen Interaction
    Note over L1: Validate carrier protocol

    %% Layer 2 perimeter
    L1->>L2: Forward Raw Interaction
    Note over L2: Authenticate and rate-limit<br/>Scan, tokenize, redact, validate
    L2-->>L3: Send Sanitized Intake Contract

    %% Layer 3 intake and entity extraction

    rect rgb(240, 248, 255)
    Note over L3,AI: Gate 1: Modality Handling & Entity Extraction
    alt Audio
        L3->>AI: Transcribe Audio
        AI-->>L3: Text Transcript
        L3->>AI: Extract Domain Entities
        AI-->>L3: Entities & Confidence Score
    else Menu / DTMF Selection
        Note over L3: Deterministic Fast Path<br/>Validated mapping, fixed baseline, no model inference
    else Free Text
        L3->>AI: Extract Domain Entities
        AI-->>L3: Entities & Confidence Score
    end
    end

    %% Layer 4 claim orchestration and governance
    L3->>L4: Send Intake & Extracted Entities

    %% Gate 2: Mandatory Entity Completeness & Multi-Turn Reprompts
    rect rgb(255, 250, 240)
    Note over L4: Gate 2: Intent & Completeness Validation
    alt Required Details Missing, Attempts below 3
        L4-->>Citizen: Request Missing Details
    end
    end

    %% Gate 3: Policy Adjudication Matrix
    rect rgb(240, 255, 240)
    Note over L4: Gate 3: Policy Adjudication
    L4->>DPI: Verify Identity Token
    DPI-->>L4: Identity Result
    L4->>DPI: Check Land, Crop & Season
    DPI-->>L4: Entitlement Result
    Note over L4: Prevent Duplicate Seasonal Claims
    end

    %% Post-decision execution
    rect rgb(255, 245, 245)
    Note over L4,DPI: Decision Execution & Notification
    alt AUTO_APPROVE: eligible, unique, score >= 0.85
        L4->>DPI: Initiate Payment
        DPI-->>L4: Payment Result
        L4->>Deliv: Send Approval Notice
    else ROUTE_FOR_MANUAL_REVIEW: low score, flagged, or retry limit
        L4->>L4: Stage Review Case
        L4->>Deliv: Send Review Notice
    else AUTO_REJECT: ineligible or duplicate claim
        L4->>Deliv: Send Rejection Notice
    end
    Deliv->>L1: Send Channel-Adapted Notice
    L1->>Citizen: Deliver Confirmation
    end
```

---

## 2. Detailed Flow by Lifecycle Boundary

Color key: **blue** ingress · **amber** security · **teal** intake and delivery · **indigo** governance · **green** approval · **orange** review · **red** rejection · **purple** persistence.

### Layer 1 Ingress: Carrier Interaction

The originating channel validates its transport protocol and forwards the interaction. Raw identifiers and content remain transient and are passed only to Layer 2 for sanitization.

```mermaid
flowchart LR
    A["Citizen interaction"] --> B["Layer 1: Validate channel protocol"]
    B -- "Valid carrier event" --> C["Forward raw interaction to Layer 2"]
    B -- "Invalid carrier event" --> D["Reject at channel boundary"]
    classDef ingress fill:#e8f0fe,stroke:#4c78a8,color:#172b4d,stroke-width:1.5px
    classDef reject fill:#fde8e8,stroke:#b94a48,color:#4a1515,stroke-width:1.5px
    class A,B,C ingress
    class D reject
```

### Layer 2 Security: Standardized Zero-PII Intake Contract

Layer 2 authenticates and rate-limits the carrier request, screens content, tokenizes approved identifiers, canonicalizes the interaction, and fails closed if cleartext PII remains.

```mermaid
flowchart TD
    A["Raw carrier interaction"] --> B["Authenticate carrier request<br/>Constant-time HMAC-SHA-256 check"]
    B -- "Invalid or missing signature" --> B1["Fail closed"]
    B -- "Valid signature" --> C["Apply rate limit"]
    C -- "Quota exceeded" --> C1["Reject request"]
    C -- "Within quota" --> D["Screen for adversarial content"]
    D --> E["Canonicalize interaction"]
    E --> F["HMAC-tokenize approved identifiers"]
    F --> G{"Any cleartext PII remains?"}
    G -- "Yes" --> G1["Fail closed; block handoff"]
    G -- "No" --> H["Standardized zero-PII intake contract"]
    classDef security fill:#fff4dd,stroke:#c28a1a,color:#49330b,stroke-width:1.5px
    classDef reject fill:#fde8e8,stroke:#b94a48,color:#4a1515,stroke-width:1.5px
    classDef contract fill:#e5f5f2,stroke:#3b8f83,color:#123c37,stroke-width:1.5px
    class A,B,C,D,E,F,G security
    class B1,C1,G1 reject
    class H contract
```

### Layer 3 Intake & Extraction: Extracted Domain Entity Contract

Layer 3 converts each supported modality into the same intent-and-entity contract. Structured menu selections bypass model inference but still proceed through Layer 4 intent and completeness validation.

```mermaid
flowchart TD
    A["Standardized zero-PII intake contract"] --> B{"Modality"}
    B -- "Audio" --> C["Speech transcription and translation"]
    C --> D["Language-model entity extraction"]
    B -- "Free text" --> D
    B -- "Structured menu" --> E["Deterministic entity mapping<br/>Fixed confidence baseline: 1.0"]
    D --> F["Extracted domain entity contract"]
    E --> F
    classDef intake fill:#e5f5f2,stroke:#3b8f83,color:#123c37,stroke-width:1.5px
    classDef contract fill:#e8f0fe,stroke:#4c78a8,color:#172b4d,stroke-width:1.5px
    classDef governance fill:#eef2ff,stroke:#5968a8,color:#252b55,stroke-width:1.5px
    class A,C,D,E intake
    class B governance
    class F contract
```

### Layer 4 Governance: Claim Evaluation & Governance Outcome

Gate 2 handles intent and intake completeness. Status and scheme inquiries follow a read-only route, while appeals go to caseworker review. District and crop are required at intake; a survey number may be resolved during registry matching. A citizen clarification reply is a new ingress interaction, not a bypass around the perimeter controls. Gate 3 verifies identity and entitlement against sovereign registries.

```mermaid
flowchart TD
    A["Extracted domain entity contract"] --> B["Gate 2: Validate intent and completeness"]
    B --> C{"Adversarial signal?"}
    C -- "Yes" --> S["Manual security review"]
    C -- "No" --> D{"Intent"}
    D -- "Status or scheme inquiry" --> E["Read-only inquiry result"]
    D -- "Appeal" --> R["Caseworker review"]
    D -- "Claim" --> F{"Required details complete?"}
    F -- "No; attempts remain" --> G["Request clarification<br/>Reply re-enters through Layer 1"]
    F -- "No; limit reached" --> R
    F -- "Yes" --> H["Gate 3: Verify identity, landholding,<br/>crop, season, and duplicate status"]
    H --> I{"Authoritative result"}
    I -- "Eligible, unique, confidence >= 0.85" --> J["Approve claim<br/>Disbursement status: PENDING"]
    I -- "Low confidence or unresolved result" --> R
    I -- "Ineligible or duplicate" --> K["Reject claim with reason"]
    classDef contract fill:#e8f0fe,stroke:#4c78a8,color:#172b4d,stroke-width:1.5px
    classDef governance fill:#eef2ff,stroke:#5968a8,color:#252b55,stroke-width:1.5px
    classDef success fill:#e6f4ea,stroke:#4a8f5b,color:#173b20,stroke-width:1.5px
    classDef review fill:#fff0db,stroke:#c27a24,color:#4d310d,stroke-width:1.5px
    classDef reject fill:#fde8e8,stroke:#b94a48,color:#4a1515,stroke-width:1.5px
    class A contract
    class B,C,D,F,H,I governance
    class E,G,R review
    class S,R review
    class J success
    class K reject
```

**Outcome rules:** Claims with confidence of at least `0.85` and verified as eligible and unique are approved. Adversarial signals route to manual security review. Confidence below `0.85`, unresolved verification, or exhausted clarification attempts route to manual case review. Only authoritative ineligibility or a duplicate active claim results in rejection; an unavailable or inconclusive registry result is not proof of ineligibility. Payment dispatch follows approval asynchronously and does not change the governance outcome.

### Notification Egress: Channel-Adapted Citizen Notice

Notification delivery consumes inquiry responses, appeal acknowledgments, clarification requests, and governance outcomes. Payment settlement can later produce a separate status notice. The notification is rendered for the originating channel; the carrier acknowledgment is recorded when available.

```mermaid
flowchart TD
    A["Inquiry response, clarification request,<br/>appeal acknowledgment, or governance outcome"] --> B["Compose channel-adapted notice"]
    C["Reconciled payment status"] --> B
    B --> D["Dispatch through originating channel"]
    D --> E["Carrier acknowledgment, when available"]
    classDef delivery fill:#e3f6f8,stroke:#348998,color:#123b42,stroke-width:1.5px
    classDef outcome fill:#e8f0fe,stroke:#4c78a8,color:#172b4d,stroke-width:1.5px
    class A,C outcome
    class B,D,E delivery
```

---

## 3. Persistence & Analytics: Operational Records & Analytical Read Models

Session, extraction, governance, and financial records are persisted as the interaction progresses; persistence is not a post-delivery stage. Only tokenized identifiers and redacted content cross the durable-storage boundary. Governance and financial state changes are captured in an append-only audit history. Analytical views are downstream read models, not part of the citizen request path.

```mermaid
flowchart LR
    A["Sanitized interaction"] --> S["Session record"]
    A --> T["Extraction attempt records"]
    T -->|Final committed attempt| G["Governance record"]
    G --> H["Append-only audit history"]
    S & T & G --> V["Analytics read model"]
    classDef persistence fill:#f1eafe,stroke:#7955a1,color:#33214e,stroke-width:1.5px
    classDef analytics fill:#e8f0fe,stroke:#4c78a8,color:#172b4d,stroke-width:1.5px
    class A,S,T,G,H persistence
    class V analytics
```

Multi-turn attempts remain distinguishable so analytics can select the committed extraction for a governance outcome without counting every clarification turn as a separate claim. The audit history records governance-state changes with actor attribution.

---

## 4. Data Contract Lifecycle & Transformation Progression

| Lifecycle Boundary | Active Data Contract | Key Attributes & Invariants | Consuming Architectural Layer |
| :--- | :--- | :--- | :--- |
| **Layer 1 Ingress** | *Carrier Interaction* | Raw identifiers and content are transient and passed only to perimeter security for sanitization. | Layer 2 Perimeter Security |
| **Layer 2 Security** | *Standardized Zero-PII Intake Contract* | Approved identifiers are HMAC-tokenized; cleartext PII is removed before the Layer 3 handoff. | Layer 3 Intake |
| **Layer 3 Intake & Extraction** | *Extracted Domain Entity Contract* | Intent, extracted entities, confidence, and security signal; structured menu input is mapped without model inference. | Layer 4 Governance |
| **Layer 4 Governance** | *Claim Evaluation & Governance Outcome* | Approval, manual review, or rejection with the applicable transaction, case, or reason details. | Payment Rails, Caseworker Queue, and Notification Delivery |
| **Notification Egress** | *Channel-Adapted Citizen Notice* | Content is rendered for the originating channel; a carrier receipt records transport feedback. | Originating Channel |
| **Persistence & Analytics** | *Operational Records & Analytical Read Models* | Tokenized and redacted records, auditable state changes, and deduplicated views for reporting. | Relational Store and Analytics |
