# Contributor Covenant Code of Conduct & User Safety Policy

## 1. Our Pledge

We as maintainers, contributors, and operators of **AgriStack DBT Core** pledge to make participation in our community and interaction with our Digital Public Infrastructure (DPI) reference workflows a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, caste, religion, regional dialect, or sexual identity and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming, diverse, inclusive, and healthy Digital Public Goods (DPG) ecosystem.

---

## 2. Our Standards for Contributors & Integrators

Examples of behavior that contributes to a positive environment include:
* Demonstrating empathy and kindness toward other contributors, state caseworkers, and rural citizens.
* Being respectful of differing viewpoints, linguistic diversity, and operational constraints across low-connectivity regions.
* Giving and gracefully accepting constructive architectural and security feedback.
* Focusing on what is best for citizen data privacy, financial accuracy, and the broader public good.

Examples of unacceptable behavior include:
* The use of sexualized language or imagery, and sexual attention or advances of any kind.
* Trolling, insulting or derogatory comments, and personal or political attacks.
* Public or private harassment of contributors, reviewers, or users.
* Publishing others' private information or raw Personally Identifiable Information (PII), such as Aadhaar numbers, phone numbers, or physical addresses, without explicit legal authorization.
* Intentionally weakening Zero-Trust PII tokenization guards, adversarial prompt firewalls, or deterministic financial adjudication safeguards.

---

## 3. Citizen & Underage User Safety Policy (DPG Standard Indicator 9C)

In addition to contributor conduct, **AgriStack DBT Core** enforces structural safeguards to protect citizens and prevent harm to underage or vulnerable users:

1. **No Peer-to-Peer or Public User Content Distribution:** The system operates strictly as a one-to-one citizen-to-government intake and benefit orchestration channel across IVR Voice, WhatsApp, USSD (`*99#`), and SMS. Citizens cannot message other users, view other users' submissions, or publish public content, eliminating platform-mediated peer harassment or cyberbullying.
2. **Adult Entitlement & Registry Verification:** Financial Direct Benefit Transfer (DBT) disbursements and agricultural disaster-relief claims are deterministically gated against verified adult landholding records in the Federated Farmer Registry and Aadhaar-seeded adult bank accounts.
3. **Zero Generative AI in Citizen-Facing Decisions:** Generative language blocks are restricted exclusively to input translation and structured entity extraction. All outbound citizen prompts and notifications use pre-approved, deterministic multilingual templates, preventing abusive, hallucinated, or inappropriate responses.
4. **Human-in-the-Loop Recourse:** Any ambiguous intake, low extraction confidence (`< 0.85`), or registry mismatch is automatically routed to a trained district caseworker review queue with full audit logging.

---

## 4. Enforcement & Reporting

Instances of abusive, harassing, or otherwise unacceptable behavior—or reports of security/safety issues—may be reported by opening a confidential security advisory on the repository (`https://github.com/gargmishu/agristack-dbt-core/security/advisories`) or contacting the project maintainer directly via the contact channels listed in [SECURITY.md](./SECURITY.md).

All complaints will be reviewed and investigated promptly and fairly. Maintainers are obligated to respect the privacy and security of the reporter of any incident.

---

## 5. Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org), version 2.1, extended with Digital Public Goods Alliance (DPGA) Indicator 9C citizen and underage safety provisions.
