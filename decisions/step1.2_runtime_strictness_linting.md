# Runtime Strictness & Code Quality Tooling Design

**Framework Step:** Phase 1 · Step 1.2: Configure Environment Strictness & Code Quality Tools
**Target Architecture:** Ruff + MyPy + Pytest + pre-commit
**Related Documents:**
- [roadmap.md](../roadmap.md)
- [step1.1_tech_stack_evaluation.md](./step1.1_tech_stack_evaluation.md)

---

## 1. Executive Summary

This document defines the implementation specifications for **Step 1.2 of the Master Roadmap**. Static code quality, security boundaries, developer workflow strictness, and automated linting/formatting are enforced using **Ruff** (linting and formatting), **MyPy** (strict static type checking), **pytest** (async test framework), and **pre-commit** hooks configured centrally via `pyproject.toml` and `.pre-commit-config.yaml`.

---

## 2. Tooling Selection & Alternatives Evaluated

To establish code quality and environment sanity, four key tooling decisions were evaluated:

| Concern | Chosen Tool | Alternatives Evaluated | Primary Decision Drivers |
| :--- | :--- | :--- | :--- |
| **Code Linter & Formatter** | **Ruff** | Black + Flake8 + Isort + Bandit + Pylint | 10x-100x speedup (written in Rust), single binary, unified `pyproject.toml` config. |
| **Static Type Checker** | **MyPy** | Pyright, Pytype, Pyre | Official Python standard type checker, native `pydantic.mypy` plugin support, `strict` mode. |
| **Test Runner & Framework** | **Pytest** | `unittest` (std lib), Nose2 | Standard `assert` syntax, rich fixture system, native async support (`pytest-asyncio`). |
| **Git Pre-Commit Automation** | **pre-commit** | Shell `.git/hooks`, Husky | Version-controlled configuration (`.pre-commit-config.yaml`), isolated hook envs. |

### 2.1 Linter & Formatter Selection: **Ruff**
- **Alternatives Evaluated:**
  1. *Traditional Multi-Tool Suite (Flake8 + Black + Isort + Bandit + Pyupgrade + Pylint):* Required 6 separate dependencies with fragmented config files (`.flake8`, `pyproject.toml`, `.isort.cfg`). Running these tools sequentially parses Python AST multiple times, causing high pre-commit latency (5–15 seconds per run).
  2. *Autopep8 / Yapf:* Limited scope (only PEP8 styling); lacks security scanning (Bandit) or AST bug detection (Flake8-bugbear).
- **Decision Rationale:** **Ruff** (written in Rust) replaces Flake8, Black, Isort, Bandit, Pyupgrade, and Pylint with a single binary. It parses AST once and runs in under 100ms (<1% of python linter execution time), providing instantaneous feedback in developer IDEs and pre-commit hooks while standardizing configurations into `pyproject.toml`.

### 2.2 Static Type Checker Selection: **MyPy**
- **Alternatives Evaluated:**
  1. *Pyright / Pylance (Microsoft):* Extremely fast and excellent LSP for VS Code, but relies on Node.js / npm infrastructure or pyright npm binaries, introducing a non-Python runtime dependency into CI pipelines.
  2. *Pytype (Google):* Developed by Google primarily for **type inference** across large legacy Python codebases without requiring upfront type annotations. Pytype runs an abstract bytecode interpreter to infer types from variable usage.
  3. *Pyre (Meta):* High-performance type checker written in OCaml, tailored for Facebook's large monolithic repositories.
- **Decision Rationale:**
  - **Explicit Annotations vs. Type Inference:** While **Pytype** excels at inferring types in legacy codebases (and is widely used across Google), this greenfield project enforces **100% explicit type annotations** (`mypy --strict` with `disallow_untyped_defs = true`). We explicitly want missing type hints to trigger CI failures rather than relying on type inference.
  - **Python 3.11+ Support:** MyPy maintains first-class alignment with CPython typing standards and Python 3.11+ features (`Self`, `TypeVarTuple`, async task types).

### 2.3 Test Framework Selection: **Pytest (+ pytest-asyncio + pytest-cov)**
- **Alternatives Evaluated:**
  1. *`unittest` (Built-in Standard Library):* Requires verbose OOP boilerplate (`unittest.TestCase`), awkward assertion methods (`self.assertEqual`), and clunky async test wrappers (`IsolatedAsyncioTestCase`).
  2. *Nose2:* Legacy framework with declining community ecosystem.
- **Decision Rationale:** **Pytest** provides clean `assert` syntax, robust fixture dependency injection for mocking carrier webhooks and DPI registries, native async test execution via `pytest-asyncio`, and automated test coverage reporting via `pytest-cov`.

### 2.4 Pre-Commit Automation: **pre-commit**
- **Alternatives Evaluated:**
  1. *Custom Bash Hooks (`.git/hooks/pre-commit`):* Fragile, platform-dependent, difficult to share across developer machines, and easily bypassed or lost during repo cloning.
  2. *Husky (Node.js ecosystem):* Requires installing Node.js and `package.json` into a pure Python repository.
- **Decision Rationale:** The **pre-commit** framework is version-controlled via `.pre-commit-config.yaml`, automatically manages isolated virtualenv environments for linters, and guarantees that every commit passes Ruff linting, MyPy static typing, and custom security checks.

---

## 3. Tooling & Infrastructure Specifications

### 3.1 Linter & Formatter (`ruff`)
We adopt **Ruff** as the single unified engine for Python linting and formatting. Ruff is configured via `pyproject.toml` with the following rule suites:

- `E` / `W`: Pycodestyle errors and warnings.
- `F`: Pyflakes logical checks.
- `B`: Flake8-bugbear (common bug patterns).
- `UP`: Pyupgrade (modern Python 3.11+ syntax enforcement).
- `S`: Bandit security checks (detecting hardcoded secrets, unsafe deserialization).
- `I`: Isort (automatic import sorting).
- `SIM`: Code simplification rules.
- `PL`: Pylint rule subset.

```toml
# pyproject.toml snippet
[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "B", "UP", "S", "I", "SIM", "PL"]
ignore = ["S101"] # Allow assert in tests

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

### 3.2 Static Type Checker (`mypy`)
Static typing guarantees that code interfaces match declared signatures before execution.

```toml
[tool.mypy]
python_version = "3.11"
strict = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true
plugins = ["pydantic.mypy"]
```

### 3.3 Pre-Commit Hooks (`.pre-commit-config.yaml`)
To prevent non-compliant code from entering the repository, git pre-commit hooks enforce:
1. `ruff check --fix` and `ruff format`
2. `mypy` strict execution
3. Custom PII check script verifying no cleartext PII field names (e.g. `raw_aadhaar`, `unhashed_phone`) are added to persistent models.

---

## 4. Physical File Configuration Plan

Execution of Step 1.2 requires establishing the following tooling files:

```text
agristack-dbt-core/
├── pyproject.toml                  <-- Ruff, MyPy, pytest configuration
├── .pre-commit-config.yaml         <-- Git hooks config
└── tests/
    ├── unit/                       <-- Test suite root
    └── conftest.py                 <-- Shared Pytest fixtures
```

---

## 5. Implementation Task Checklist

| Task | Component | Key Output Files | Verification Metric |
| :--- | :--- | :--- | :--- |
| **Task 1** | Code Quality Tooling | `pyproject.toml` | `ruff check .` passes with zero errors |
| **Task 2** | Static Type Checker | `pyproject.toml` (`[tool.mypy]`) | `mypy src` passes in strict mode |
| **Task 3** | Test Runner | `tests/conftest.py` | `pytest` runs and executes async test fixtures |
| **Task 4** | Pre-Commit Hooks | `.pre-commit-config.yaml` | `pre-commit run --all-files` succeeds |

---

## 6. Glossary of Acronyms & Technical Terms

| Acronym / Term | Full Name / Expansion | Technical Context & Definition in This Project |
| :--- | :--- | :--- |
| **AST** | **Abstract Syntax Tree** | A tree representation of source code created by a parser. Tools like Ruff and MyPy parse code into an AST to check rules and types. |
| **LSP** | **Language Server Protocol** | Open protocol for code editors to communicate with language tools (e.g. Pyright, Ruff, MyPy) for real-time diagnostics. |
| **PEP** | **Python Enhancement Proposal** | Design specs for Python features (e.g. PEP 8 for style, PEP 484 for type hints). |
