---
name: coding-standards
description: Universal Python coding rules, naming conventions, method visibility, dependency injection, and clean code best practices, independent of specific business logic. Use whenever designing, refactoring, writing, or structuring Python classes, functions, and test suites.
---

# Universal Python Coding Standards & Best Practices

This skill outlines language-level clean coding rules, naming conventions, object-oriented design principles, and verification standards. These guidelines are **independent of business logic** and must be adhered to across all modules.

---

## 1. Naming Conventions & Semantic Clarity

### 1.1 Unambiguous, Self-Documenting Names (Zero Cryptic Abbreviations)
* **Never Use Cryptic Truncations**: Prohibit short-hand abbreviations, truncated names, or single/two-letter identifiers across all classes, functions, arguments, instance attributes, and local variables.
  * **Incorrect**: `orch_result`, `eval_result`, `carrier_ref`, `bank_ref`, `msg`, `kw`, `k`, `res`, `req`, `fw`, `std_payload`, `err`, `loc`, `cid`
  * **Correct**: `orchestration_result`, `evaluation_result`, `carrier_reference_id`, `bank_reference_id`, `message`, `keyword`, `response`, `request`, `firewall`, `standardized_payload`, `error`, `language_locale`, `citizen_identifier`
* **Descriptive Function & Method Names**: Functions and methods must use explicit verb-noun phrases that clearly communicate intent, action, and outcome:
  * **Correct**: `execute_orchestration_cycle`, `dispatch_notification`, `stage_incident_ticket`, `verify_carrier_webhook`, `evaluate_payload`
  * **Incorrect**: `process`, `run`, `handle_data`, `check`, `do_eval`
* **Self-Documenting Arguments**: Parameter names must explicitly describe the expected data contract and semantic role rather than using generic or shortened labels:
  * **Correct**: `def _build_notification_request(intake: PublicAgentStandardizedIntakePayload, orchestration_result: OrchestrationExecutionResult)`
  * **Incorrect**: `def _build_notification_request(intake, orch_result)` or `def _build_notification_request(payload, res)`
* **Descriptive, Role-Based Class Names**: Classes must use full, descriptive nouns or noun phrases representing their domain entity, gateway boundary, or service responsibility:
  * **Correct**: `MultichannelNotificationService`, `PublicAgentStandardizedIntakePayload`, `ZeroTrustIdentityTokenizer`, `ClaimAdjudicator`
  * **Incorrect**: `NotifService`, `AgentAPI`, `Tokenizer`, `AdjudicatorHelper`

### 1.2 Classes and Type Aliases (PascalCase / Upper CamelCase)
* **Acronyms as Capitalized Words**: Treat multi-word acronyms as capitalized words (Upper CamelCase) rather than ALL-CAPS to avoid visual collisions (e.g. `CC` ambiguity) and ensure readability.
  * **Correct**: `IvrIngressPayload`, `UssdIngressPayload`, `HmacCitizenToken`, `WhatsAppIngressPayload`, `HttpClient`, `HttpUrl`
  * **Incorrect**: `IVRIngressPayload`, `USSDIngressPayload`, `HMACCitizenToken`, `WhatsappIngressPayload`

### 1.3 Attributes, Variables, and Functions (`snake_case`)
* All function names, method names, instance attributes, function parameters, and local variables must strictly use `snake_case`.

### 1.4 Constants and Private Module Variables
* **Internal Constants**: Private constants and implementation details must use uppercase `SNAKE_CASE` prefixed with a leading underscore (e.g., `_SIGNATURE_PREFIX`, `_BEARER_PREFIX`, `_MAX_RETRY_COUNT`).
* **Public Constants**: Exported configuration defaults, public policy mappings, and test fixtures may remain unprefixed `UPPER_SNAKE_CASE` when intentionally part of the public module surface.
* **Standard Library Primitives Over Custom Constants**: Never define custom constants or magic integers for domains already standardized in the Python standard library.
  * Specifically, always use `from http import HTTPStatus` (an `IntEnum`) for HTTP status codes rather than declaring module-level `_HTTP_STATUS_* = 200` or raw integer literals.
  * **Incorrect**:
    ```python
    _HTTP_STATUS_OK: Final[int] = 200
    _HTTP_STATUS_UNAUTHORIZED: Final[int] = 401
    if response.status_code == _HTTP_STATUS_OK: ...
    ```
  * **Correct**:
    ```python
    from http import HTTPStatus
    if response.status_code == HTTPStatus.OK: ...
    if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN): ...
    ```

### 1.5 Module-to-Class Naming Symmetry
* For operational components (gateways, connectors, routers, validators, and services), Python filenames in `snake_case` must strictly match their primary class name in `PascalCase`:
  * `carrier_auth_validator.py` $\rightarrow$ `CarrierAuthValidator`
  * `payment_rail_service.py` $\rightarrow$ `PaymentRailService`
  * `claim_adjudicator.py` $\rightarrow$ `ClaimAdjudicator`
* Do not omit descriptive suffixes like `_validator`, `_service`, or `_connector` from module names.

---

## 2. Method Visibility, Ordering & Clean Class Layout

Maintain clean top-down readability and strict encapsulation within every class:

### 2.1 Principle of Least Visibility & Strict Encapsulation
* **Default to Private**: Every method, helper function, validator, and formatter must default to private (prefixed with a leading underscore `_`) unless it is an explicitly designed public API contract.
* **No Leaky Internal Helpers**: Internal formatting routines, state builders, parsing algorithms, and connector dispatches must never be exposed publicly.
* **Encapsulate Collaborators**: Do not expose internal dependency instances (e.g., `self._firewall`, `self._orchestrator`, `self._evaluator`, `self._social_service`) as public properties or getters unless consumers specifically require documented read-only introspection.

### 2.2 Public-First / Private-at-Bottom Ordering Rule
Classes must strictly follow a 4-tier top-down ordering:
1. **Lifecycle & Constructors (Top)**: `__init__`, followed by class factories (`from_env`).
2. **Primary Public Workflow Entrypoints (Upper Middle)**: The primary end-to-end execution methods.
3. **Public Component & Stage Methods (Lower Middle)**: Public sub-stage handlers and modular public entrypoints.
4. **Private Helper Methods (Bottom)**: All internal private methods (prefixed with `_`) must be placed strictly at the **bottom** of the class definition below all public methods, grouped under a clear section banner.

```python
class ComponentService:
    """Service class demonstrating clean method ordering and least visibility."""

    def __init__(self, dependency: DependencyClient | None = None) -> None:
        """Initializes service with required dependency."""
        self._dependency = dependency or DependencyClient()

    @classmethod
    def from_env(cls) -> "ComponentService":
        """Factory constructor building instance from environment."""
        return cls(dependency=DependencyClient.from_env())

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def execute_workflow(self, request: RequestPayload) -> ResponsePayload:
        """Primary public entrypoint executing the end-to-end workflow."""
        validated = self.validate_stage(request)
        return await self._dispatch_internal(validated)

    def validate_stage(self, request: RequestPayload) -> ValidatedPayload:
        """Public validation sub-stage."""
        return self._normalize_payload(request)

    # -------------------------------------------------------------------------
    # Private Helpers (Strictly at Bottom)
    # -------------------------------------------------------------------------

    def _normalize_payload(self, request: RequestPayload) -> ValidatedPayload:
        """Internal private helper normalizing raw request."""
        ...

    async def _dispatch_internal(self, payload: ValidatedPayload) -> ResponsePayload:
        """Internal private helper handling dispatching logic."""
        ...
```

### 2.3 Cross-Module Structural Symmetry
* **Tier-Wide Architectural Consistency**: Components belonging to the same architectural tier (e.g., all live service adapters in `src/services/ai/` and `src/services/dpi/`, or all channel edge connectors in `src/connectors/`) must adhere to identical internal layouts, private helper patterns, and error-handling abstractions.
* **No Single-Method Complacency**: If an abstraction pattern (such as an extracted `_post_json` helper for HTTP transport) is established for one component in an architectural tier, all peer components in that tier must use the same pattern. Never inline repetitive transport or serialization mechanics just because a class currently has only one public endpoint.

---

## 3. Modularity & Single Responsibility Principle (SRP)

### 3.1 Low Cyclomatic Complexity
* Keep branch count and nesting shallow (cyclomatic complexity $< 12$).
* Eliminate complex branching with early returns, lookup dictionaries, or decomposed private helper methods. Avoid `# noqa: PLR0912` suppressions.

### 3.2 Focused Single-Responsibility Functions
* Every function or validator should validate or perform exactly **one concern** (e.g. non-empty check, matrix compatibility, or format validation).

### 3.3 Direct Enum Comparisons
* When comparing `StrEnum` members, compare them directly without redundant `.value` or `str(...)` casting:
  * **Correct**: `if status == ApplicationStatus.APPROVED:`
  * **Incorrect**: `if str(status) == ApplicationStatus.APPROVED.value:`

### 3.4 Dependency Injection & Factory Methods
* **Optional Collaborators**: For internal domain components and stateless collaborators, use standard optional dependency injection in `__init__` (e.g., `service: SomeService | None = None` with `self._service = service or SomeService()`).
* **Environment Configuration**: When construction requires reading secrets or configuration from environment variables (e.g. pepper keys, rate limit settings), use explicit `@classmethod` factories like `from_env(cls)`.
* **No Redundant `from_default()`**: Avoid creating redundant `from_default()` methods when `__init__()` can directly provide the default instantiation.

```python
# CORRECT: Optional dependency injection for internal services
class ClaimOrchestrator:
    def __init__(
        self,
        bhashini_service: BhashiniService | None = None,
        slm_extractor: SlmExtractor | None = None,
    ) -> None:
        self._bhashini = bhashini_service or BhashiniService()
        self._slm_extractor = slm_extractor or SlmExtractor()

# CORRECT: Factory class method for environment-configured components
class ZeroTrustIdentityTokenizer:
    def __init__(self, pepper_key: str) -> None:
        self._pepper_key = pepper_key.encode("utf-8")

    @classmethod
    def from_env(cls) -> "ZeroTrustIdentityTokenizer":
        return cls(pepper_key=get_pepper_secret())
```

---

## 4. Clean Refactoring & Technical Debt Prevention

### 4.1 Atomic Caller Migration
* When renaming a class, method, or function, atomically migrate 100% of internal callers, test cases, and fixture references across the repository in the same change.

### 4.2 Immediate Elimination of Legacy Shims
* Do not retain temporary backward-compatibility aliases, wrappers, or forwarding shims once callers have been migrated.
* Delete deprecated names immediately to eliminate dead code paths, maintain single sources of truth, and keep APIs clean.

---

## 5. Architectural Documentation & Role-Based Terminology

### 5.1 Model-Agnostic Docstrings & Comments
* **Avoid Specific Vendor/Model Names**: Never hardcode specific third-party model, vendor, or framework names (e.g. `Ollama`, `Whisper`, `LLaMA`, `GPT-4`) in code comments or docstrings.
* **Use Architectural Role Terms**: Always describe components by their structural and functional role:
  * **Correct**: `SLM entity extraction pipeline`, `ASR audio transcription worker`, `NMT translation service`
  * **Incorrect**: `Ollama model call`, `Whisper transcription worker`, `GPT-4 fallback`

### 5.2 Explicit "WHY" Rationale Comments
* Always add comments explaining **why** a non-obvious constraint, formula, or boundary condition exists, rather than merely restating what the code does.

---

## 6. Test Hierarchy Symmetry & Verification

### 6.1 1:1 Mirroring
* The test directory tree under `tests/` must mirror `src/` 1:1. Each source module `src/foo/bar.py` must have a corresponding test file `tests/foo/test_bar.py`.

### 6.2 Pre-Commit Verification Suite
Always run the complete verification suite before completing any code change:

```bash
# 1. Format & Linting
.venv/bin/ruff format . && .venv/bin/ruff check --fix .

# 2. Test Suite
.venv/bin/pytest

# 3. Static Type Checking
.venv/bin/mypy src tests
```
