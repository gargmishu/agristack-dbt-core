# Crop Loss Subsidy: Metrics

This document defines the technical, mathematical, and operational specifications for the observability layer of the automated crop-loss subsidy pipeline. These metrics are designed to be monitored continuously from day one to ensure conversational stability, algorithmic fairness, infrastructure reliability, and strict financial auditability.

---

## 🤖 Layer 1: AI Edge & Conversational Performance

### 1. AI Block Confidence Average
* **Definition:** The arithmetic mean of the probabilistic certainty scores returned by an inference engine during structured data extraction or semantic parsing. It measures the core stability and accuracy of the localized language models.
* **Formula:**
  $$\text{Average Confidence} = \frac{\sum_{i=1}^{N} C_i}{N}$$
  *Where $C_i$ is the confidence coefficient ($0.00 \le C \le 1.00$) of an individual extraction event, and $N$ is the total volume of discrete extraction iterations within the observed window.*
* **Tracking Window:** 
  * *Calculation Interval:* 5-Minute rolling sampling window (for real-time system alerts).
  * *Aggregation Interval:* 24-Hour macro window (for long-term model drift analysis).
* **Target Goal:** $\ge 0.85$.
* **Alerts:** A sustained drop below $0.80$ across three consecutive calculation intervals triggers an operational flag indicating an unhandled dialect or vocabulary drift.

### 2. Human Escalation Rate
* **Definition:** The proportion of total inbound conversational sessions that cannot be fully resolved by automated logic and are programmatically transferred to manual operator or caseworker review queues.
* **Formula:**
  $$\text{Human Escalation Rate (\%)} = \left( \frac{S_{\text{escalated}}}{S_{\text{ingress\_total}}} \right) \times 100$$
  *Where $S_{\text{escalated}}$ is the count of unique sessions requiring human intervention due to low AI confidence, processing faults, or user exceptions, and $S_{\text{ingress\_total}}$ is the gross number of sessions successfully initialized at the perimeter.*
* **Tracking Window:** 
  * *Calculation Interval:* 1-Hour sliding evaluation window.
  * *Aggregation Interval:* Daily summary report.
* **Target Goal:** $\le 15\%$ of total ingress traffic.
* **Alerts:** A breach above $20\%$ within any single window triggers an alert to scale up human administrative staffing.

### 3. Journey Completion Rate (JCR)
* **Definition:** The percentage of users who successfully navigate an interface session from the initial channel connection to the final confirmation delivery without dropping out or encountering system-forced timeouts.
* **Formula:**
  $$\text{JCR}_{\text{channel}} = \left( \frac{S_{\text{completed}}}{S_{\text{initialized\_channel}}} \right) \times 100$$
  *Where $S_{\text{completed}}$ is the number of sessions that successfully reach the final processing state, and $S_{\text{initialized\_channel}}$ is the total number of sessions opened on that specific channel.*
* **Tracking Window:** 
  * *Calculation Interval:* Hourly monitoring per communication protocol.
  * *Aggregation Interval:* Weekly systemic friction audit.
* **Target Goal:** $\ge 80\%$ completion rate for asynchronous or text-based interactive channels (e.g., WhatsApp, USSD); $\ge 70\%$ completion rate for synchronous voice channels (e.g., IVR), accounting for environmental noise drops and spontaneous user hang-ups.
* **Alerts:** A drop below 80% over any rolling 3-hour window triggers an alert to check for external network signaling failures or gateway latency.


---

## 📊 Layer 2: Core Infrastructure & Welfare Delivery

### 4. Volumetric Registry Intake
* **Definition:** The absolute volume of unique, validated application files successfully compiled, matched against reference databases, and committed to the core social protection registry within a specific timeframe.
* **Formula:**
  $$\text{Registry Intake}_{(t_0, t_1)} = \sum \text{Records Committed} \in [t_0, t_1]$$
  *Where the metric accumulates all transactions that successfully transition into a verified, staged database state between timestamps $t_0$ and $t_1$.*
* **Tracking Window:** 
  * *Calculation Interval:* Hourly transactional updates (to verify live API sync health with external registries).
  * *Aggregation Interval:* Daily totals, stacked into Weekly and Monthly seasonal charts.
* **Target Goal:** Zero dropped transactions under load. The ingest infrastructure must maintain an operational throughput baseline of $\ge 500 \text{ concurrent registrations/minute}$ during seasonal demand spikes.
* **Alerts:** A drop to absolute zero writes during active business hours ($09:00 \text{ to } 18:00$) *or* any non-zero count of explicitly dropped writes/ingest packet timeouts within a 5-minute window triggers an immediate critical infrastructure priority alert.

### 5. Automated Disbursement Rate
* **Definition:** The straight-through processing (STP) index that calculates the percentage of registered cases that satisfy all automated evaluation gates and proceed directly to fiscal settlement without requiring manual review.
* **Formula:**
  $$\text{Automated Disbursement Rate}_{(t_0, t_1)} (\%) = \left( \frac{S_{\text{autonomous\_payout}} \in [t_0, t_1]}{S_{\text{registry\_total}} \in [t_0, t_1]} \right) \times 100$$
  *Where the numerator is the count of files routed directly to automated clearing house payment systems, and the denominator is the total number of validly registered files evaluated in that same time block.*
* **Tracking Window:** 
  * *Calculation Interval:* 24-Hour rolling compilation.
  * *Aggregation Interval:* Weekly business rules efficiency trend line.
* **Target Goal:** $\ge 85\%$ straight-through processing efficiency.
* **Alerts:** A drop below $80\%$ indicates data schema mismatches or overly restrictive validation rules between the interface and core registries.

### 6. Sovereign Capital Liquidation
* **Definition:** The absolute cumulative sum of financial relief capital cleared, authorized, and transmitted securely across the central payment rail to citizen bank accounts.
* **Formula:**
  $$\text{Amount Disbursed}_{(t_0, t_1)} = \sum_{k=1}^{P} V_k$$
  *Where $V_k$ is the verified fiat currency value of an individual transaction successfully settled by the central clearing network within the window $[t_0, t_1]$, and $P$ is the total pool of successful settlements.*
* **Tracking Window:** 
  * *Calculation Interval:* Continuous real-time stream accumulation.
  * *Aggregation Interval:* Daily batch totals (for banking reconciliation) and Seasonal macro budgets.
* **Target Goal:** $100\%$ ledger reconciliation accuracy. Liquidated disbursement amounts must perfectly balance against authorized case allocation values with zero mathematical variance.
* **Alerts:** Any non-zero variance between authorized amounts and cleared settlement values triggers an immediate processing halt on the affected transaction batch.

---

## 🛡️ Layer 3: System Integrity & Citizen Experience

### 7. Audit Log Completeness Rate
* **Definition:** A structural data integrity metric verifying that $100\%$ of processed sessions have generated an unalterable, cryptographically signed telemetry and state record before session closure.
* **Formula:**
  $$\text{Audit Completeness (\%)} = \left( \frac{S_{\text{signed\_records}}}{S_{\text{closed\_total}}} \right) \times 100$$
  *Where $S_{\text{signed\_records}}$ is the number of terminated sessions where a valid cryptographic row signature has been written to the ledger, and $S_{\text{closed\_total}}$ is the total number of terminated sessions.*
* **Tracking Window:** 
  * *Calculation Interval:* Evaluated instantly at the micro-level upon every individual session termination event.
  * *Aggregation Interval:* Continuous data-pipeline compliance assertion.
* **Target Goal:** **Hard $100.00\%$ Enforcement.** Any single non-signed, malformed, or missing state record breaks pipeline compliance and triggers an immediate infrastructure isolation protocol.
* **Alerts:** A drop below $100.00\%$ instantly triggers a high-severity security exception, halting engine execution to verify database transaction integrity.

### 8. Citizen Satisfaction Index (CSAT)
* **Definition:** The baseline score measuring citizen sentiment, captured via post-transaction surveys deployed over the native channel immediately following session closure.
* **Formula:**
  $$\text{CSAT} = \frac{\sum_{j=1}^{R} R_j}{R}$$
  *Where $R_j$ is the numerical rank ($1 \text{ to } 5$) submitted by the citizen, and $R$ is the total volume of responses captured inside the evaluation window.*
* **Tracking Window:** 
  * *Calculation Interval:* Rolling 7-day average.
  * *Aggregation Interval:* Monthly program review.
* **Target Goal:** Mean user rating of $\ge 4.2 / 5.0$
* **Alerts:** A drop below $3.8$ on any specific interface channel flags user experience friction, linguistic confusion, or latency issues in the conversational prompts.