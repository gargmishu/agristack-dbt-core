# Step 2.1: Package Manager & Dependencies Initialization

## 1. Executive Summary

This document records the formal specification and execution details for **Step 2.1 of the Master Roadmap**. Step 2.1 initializes the project package management infrastructure (`pyproject.toml`), defines runtime and development dependencies (including database client drivers and ORM/migration frameworks), configures strict static analysis toolchains (Ruff, Mypy, Pytest), and establishes local database environment specifications.

---

## 2. Dependency Taxonomy & Version Constraints

The project utilizes `pyproject.toml` adhering to PEP 517 / PEP 518 standards with standard `setuptools` build backend.

### 2.1 Core Application Runtime Dependencies (`[project.dependencies]`)

| Package | Minimum Version | Category | Purpose |
| :--- | :--- | :--- | :--- |
| `fastapi` | `>=0.110.0` | Web Framework | High-performance asynchronous REST API framework and dependency injection container. |
| `pydantic` | `>=2.6.0` | Data Validation | Core Zero-Trust data validation engine enforcing `extra="forbid"`, immutability, and runtime typing. |
| `pydantic-settings` | `>=2.2.0` | Configuration | Environment variable parsing and type-safe settings management. |
| `uvicorn` | `>=0.28.0` | ASGI Server | Asynchronous ASGI web server runner for high-throughput HTTP handling. |

### 2.2 Database Client Drivers & ORM Libraries (`[project.dependencies]`)

| Package | Minimum Version | Category | Purpose |
| :--- | :--- | :--- | :--- |
| `asyncpg` | `>=0.29.0` | Database Driver | High-performance async PostgreSQL client driver for Layer 4 state persistence. |
| `psycopg[binary]` | `>=3.1.18` | Database Driver | Sync/async PostgreSQL driver with C extensions and binary protocol support. |
| `sqlalchemy` | `>=2.0.28` | ORM / Core | SQL toolkit and Object Relational Mapper for relational query execution. |
| `alembic` | `>=1.13.1` | DB Migrations | Database schema migration tool managing incremental DDL evolution. |

### 2.3 Development & Testing Dependencies (`[project.optional-dependencies.dev]`)

| Package | Minimum Version | Purpose |
| :--- | :--- | :--- |
| `pytest` | `>=8.1.0` | Modern Python test framework for unit and integration testing. |
| `pytest-asyncio` | `>=0.23.0` | Async test execution support for coroutine testing (`@pytest.mark.asyncio`). |
| `pytest-cov` | `>=4.1.0` | Test coverage reporting and coverage enforcement. |
| `mypy` | `>=1.9.0` | Static type checker enforcing Zero-Trust strict type safety. |
| `ruff` | `>=0.3.0` | Ultra-fast linter and code formatter replacing Flake8, Black, and Isort. |
| `pre-commit` | `>=3.6.0` | Git hook manager running linters and type checkers on `git commit`. |

---

## 3. Local Database Server & Container Environment

To support Phase 0 ground-truth relational storage (`schema.sql`), local development environments are configured to connect to PostgreSQL (or Supabase local CLI / Docker container):

- **Engine:** PostgreSQL 15+
- **Protocol:** `postgresql+asyncpg://`
- **Capabilities:** Native JSONB index support, ACID transaction isolation, foreign key cascading, and SQL windowing functions (`QUALIFY ROW_NUMBER() OVER`).

---

## 4. Tooling & Linters Configuration (`pyproject.toml`)

### 4.1 Code Format & Linter (`[tool.ruff]`)
- **Python Version:** Python 3.11 (`py311`).
- **Line Length:** 100 characters.
- **Rule Sets Enabled:** `E`, `W` (pycodestyle), `F` (Pyflakes), `B` (flake8-bugbear), `UP` (pyupgrade), `S` (flake8-bandit security), `I` (isort import sorting), `SIM` (flake8-simplify), `PL` (Pylint).
- **Exceptions:** `S101` ignored to permit `assert` statements in test suites.

### 4.2 Type Checker (`[tool.mypy]`)
- **Strict Mode:** Enabled (`strict = true`).
- **Function Signature Enforcement:** Un-typed or incomplete function definitions strictly disallowed (`disallow_untyped_defs = true`).
- **Pydantic Plugin:** Enabled `pydantic.mypy` with `init_forbid_extra = true` and `init_typed = true`.

### 4.3 Test Runner (`[tool.pytest.ini_options]`)
- **Test Directory:** `tests/`.
- **Async Mode:** `asyncio_mode = "auto"`.
- **Pythonpath:** Set to `["."]` for root module imports.
- **Match Patterns:** Files `test_*.py`, functions `test_*`.

---

## 5. Verification & Execution Status

Virtual environment verification performed against Python 3.11/3.13 `.venv`:
- `pytest`: `9.1.1` (Operational)
- `ruff`: `0.15.22` (Operational)
- `mypy`: `2.3.0` (Operational)

---

## 6. Next Steps

With Step 2.1 complete, execution transitions to **Step 2.2: Scaffold 4-Layer Architecture Structure**, implementing the Python package modules (`src/models/`, `src/errors/`, `src/connectors/`, `src/intake/`, `src/orchestrator/`, `src/services/`) and test suites in `tests/`.
