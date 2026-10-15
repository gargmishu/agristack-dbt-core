# Security Guardrail Flow

This diagram supplements the [master architecture flow](./flowchart.md) with the security branches that gate ingress and govern adversarial routing. The zero-trust PII policy is established in the foundational tokenization decision.

```mermaid
flowchart TD
    Request["Raw carrier request"] --> Auth{"Carrier authentication"}
    Auth -->|Invalid or missing| Deny["Reject at perimeter"]
    Auth -->|Valid| Quota{"Caller within quota?"}
    Quota -->|No| RateReject["Reject before Layer 3 intake"]
    Quota -->|Yes| Transform["Tokenize identifiers and redact PII in memory"]
    Transform --> PiiCheck{"Zero-PII assertion passes?"}
    PiiCheck -->|No| Abort["Abort handoff; record no raw content"]
    PiiCheck -->|Yes| Threat{"Adversarial content detected?"}
    Threat -->|Yes| Flag["Forward sanitized intake with security flag"]
    Threat -->|No| Clean["Forward sanitized intake"]

    Flag --> IntakeProcessing["Layer 3: Intake, modality processing, and entity extraction"]
    IntakeProcessing --> Neutralize["Set adversarial confidence to 0.0 and clear entities"]
    Neutralize --> Governance["Layer 4: Governance routing"]
    Governance -->|Flagged adversarial attempt| SecurityQueue["Security review queue"]

    Clean --> NormalIntakeProcessing["Layer 3: Intake and modality processing"]
    NormalIntakeProcessing --> NormalGovernance["Layer 4: Deterministic governance"]
    NormalGovernance -->|Low confidence, e.g. 0.40| Caseworker["Standard caseworker review"]
    NormalGovernance -->|Eligible and unique| Approved["Approved claim"]
    NormalGovernance -->|Ineligible or duplicate| Rejected["Rejected claim"]
```

An adversarial confidence score of `0.0` is reserved for security neutralization. Benign low-confidence inputs, including unparseable audio, follow the ordinary review path and must not be mislabeled as security threats. Only sanitized content and pseudonymous identifiers may be persisted.
