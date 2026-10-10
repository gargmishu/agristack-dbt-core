
# Master Architecture Flow

This diagram summarizes the system boundaries. Detailed security and governance decisions are maintained in their respective architecture records.

```mermaid
flowchart TD
    Citizen["Citizen / Carrier"] --> L1["Layer 1: Channel Edge Connectors"]
    L1 -->|Raw carrier ingress| L2["Layer 2: Perimeter Security Gateway"]
    L2 -->|Authenticated, sanitized, zero-PII intake| L3["Layer 3: Public Agent Intake"]
    L3 --> Modality{"Input modality"}
    Modality -->|Structured menu| Direct["Deterministic entity mapping"]
    Modality -->|Audio| Speech["Speech recognition"]
    Modality -->|Free text| Extract["Domain entity extraction"]
    Speech --> Extract
    Direct -->|Extracted domain entities| L4["Layer 4: Governance Engine"]
    Extract --> L4

    L4 --> Complete["Gate 2: Intent and completeness"]
    Complete --> Adjudicate["Gate 3: Deterministic policy adjudication"]
    Adjudicate -->|Eligible and unique| Approve["Approved claim"]
    Adjudicate -->|Low confidence, incomplete, or flagged| Review["Human review"]
    Adjudicate -->|Ineligible or duplicate| Reject["Rejected claim"]
    Approve --> Payment["Sovereign payment rails"]
    Approve --> Notify["Adaptive outbound delivery"]
    Review --> Notify
    Reject --> Notify
```

The decision threshold, state transitions, security response, channel formats, and persistence rules are specified in the linked decision records rather than duplicated in this overview.
