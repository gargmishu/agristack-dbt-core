#!/usr/bin/env bash
# ==============================================================================
# AgriStack Zero-Trust Sovereign DPI Orchestrator - Environment Setup Script
# ==============================================================================
# This script sets up the local Python virtual environment (.venv), installs all
# core runtime, database driver, and development dependencies declared in pyproject.toml,
# and verifies environment sanity via static analysis toolchains.
# ==============================================================================

set -euo pipefail

# Determine project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "======================================================================"
echo "  AgriStack DPI Orchestrator - Environment & Dependency Setup"
echo "======================================================================"
echo "Project Root: ${PROJECT_ROOT}"
echo "Python Executable: $(which python3)"
echo "----------------------------------------------------------------------"

# Step 1: Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[1/4] Creating virtual environment in .venv..."
    python3 -m venv .venv
else
    echo "[1/4] Existing virtual environment found at .venv"
fi

# Step 2: Activate virtual environment
echo "[2/4] Activating virtual environment..."
# shellcheck source=/dev/null
source .venv/bin/activate

# Step 3: Install dependencies listed in pyproject.toml
echo "[3/4] Installing dependencies declared in pyproject.toml..."

if command -v uv &> /dev/null; then
    echo "  Using 'uv' fast installer..."
    uv pip install -e ".[dev]"
else
    echo "  Using standard 'pip' installer..."
    pip install --upgrade pip setuptools wheel 2>/dev/null || true
    
    # Try standard editable install first, fallback to reading pyproject.toml directly
    if ! pip install -e ".[dev]"; then
        echo "  Standard build failed, retrying with --no-build-isolation..."
        if ! pip install --no-build-isolation -e ".[dev]"; then
            echo "  Parsing dependencies directly from pyproject.toml..."
            DEPS=$(python3 -c 'import sys; sys.version_info >= (3, 11) or sys.exit("Python 3.11+ required for tomllib"); import tomllib; f=open("pyproject.toml","rb"); d=tomllib.load(f); deps=d.get("project",{}).get("dependencies",[])+d.get("project",{}).get("optional-dependencies",{}).get("dev",[]); print(" ".join(deps))')
            echo "  Installing parsed dependencies: ${DEPS}"
            # shellcheck disable=SC2086
            pip install ${DEPS}
        fi
    fi
fi

# Step 4: Verify environment setup
echo "[4/4] Verifying static analysis & test tooling..."
echo "----------------------------------------------------------------------"
echo "pytest version: $(pytest --version 2>&1 | head -n 1)"
echo "ruff version:   $(ruff --version 2>&1)"
echo "mypy version:   $(mypy --version 2>&1)"
echo "----------------------------------------------------------------------"

if [ -f "src/__init__.py" ]; then
    echo "Running ruff & mypy verification..."
    ruff check .
    mypy src
else
    echo "Note: 'src/__init__.py' not found. Skipping mypy and ruff checks."
fi

echo "======================================================================"
echo "  Success! Environment setup is complete."
echo "  To activate in your current shell, run:"
echo "    source .venv/bin/activate"
echo "======================================================================"