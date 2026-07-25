# Step 2.1: Package Manager & Dependencies Initialization

## 1. Executive Summary

This document records the formal specification and execution details for **Step 2.1 of the Master Roadmap**. Step 2.1 initializes the project package management infrastructure (`pyproject.toml`), defines runtime and development dependencies, configures strict static analysis toolchains (Ruff, Mypy, Pytest), and verifies virtual environment reproducibility.

---

## 2. Dependency Taxonomy & Version Constraints

The project utilizes `pyproject.toml` adhering to PEP 517 / PEP 518 standards with standard `setuptools` build backend.

### 2.1 Core Runtime Dependencies (`[project.dependencies]`)

| Package | Minimum Version | Purpose |
| :--- | :--- | :--- |
| `fastapi` | `>=0.110.0` | High-performance asynchronous REST API framework and dependency injection container. |
| `pydantic` | `>=2.6.0` | Core Zero-Trust data validation engine enforcing `extra="forbid"`, immutability, and runtime typing. |
| `pydantic-settings` | `>=2.2.0` | Environment variable parsing and type-safe settings management. |
| `uvicorn` | `>=0.28.0` | Asynchronous ASGI web server runner for high-throughput HTTP handling. |

### 2.2 Development & Testing Dependencies (`[project.optional-dependencies.dev]`)

| Package | Minimum Version | Purpose |
| :--- | :--- | :--- |
| `pytest` | `>=8.1.0` | Modern Python test framework for unit and integration testing. |
| `pytest-asyncio` | `>=0.23.0` | Async test execution support for coroutine testing (`@pytest.mark.asyncio`). |
| `pytest-cov` | `>=4.1.0` | Test coverage reporting and coverage enforcement. |
| `mypy` | `>=1.9.0` | Static type checker enforcing Zero-Trust strict type safety. |
| `ruff` | `>=0.3.0` | Ultra-fast linter and code formatter replacing Flake8, Black, and Isort. |
| `pre-commit` | `>=3.6.0` | Git hook manager running linters and type checkers on `git commit`. |

---

## 3. Tooling & Linters Configuration (`pyproject.toml`)

### 3.1 Code Format & Linter (`[tool.ruff]`)
- **Python Version:** Python 3.11 (`py311`).
- **Line Length:** 100 characters.
- **Rule Sets Enabled:** `E`, `W` (pycodestyle), `F` (Pyflakes), `B` (flake8-bugbear), `UP` (pyupgrade), `S` (flake8-bandit security), `I` (isort import sorting), `SIM` (flake8-simplify), `PL` (Pylint).
- **Exceptions:** `S101` ignored to permit `assert` statements in test suites.

### 3.2 Type Checker (`[tool.mypy]`)
- **Strict Mode:** Enabled (`strict = true`).
- **Function Signature Enforcement:** Un-typed or incomplete function definitions strictly disallowed (`disallow_untyped_defs = true`).
- **Pydantic Plugin:** Enabled `pydantic.mypy` with `init_forbid_extra = true` and `init_typed = true`.

### 3.3 Test Runner (`[tool.pytest.ini_options]`)
- **Test Directory:** `tests/`.
- **Async Mode:** `asyncio_mode = "auto"`.
- **Pythonpath:** Set to `["."]` for root module imports.
- **Match Patterns:** Files `test_*.py`, functions `test_*`.

---

## 4. Verification & Execution Status

Virtual environment verification performed against local Python 3.11 `.venv`:
- `pytest`: `9.1.1` (Operational)
- `ruff`: `0.15.22` (Operational)
- `mypy`: `2.3.0` (Operational)

---

## 5. Next Steps

With Step 2.1 complete, execution transitions to **Step 2.2: Scaffold 4-Layer Architecture Structure**, implementing the Python package modules (`src/models/`, `src/errors/`, `src/connectors/`, `src/intake/`, `src/orchestrator/`, `src/services/`) and test suites in `tests/`.
