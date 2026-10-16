#!/usr/bin/env bash
# ==============================================================================
# AgriStack Zero-Trust Sovereign DPI Orchestrator - Environment Setup Script
# ==============================================================================
# This script sets up a fully self-healing Python virtual environment (.venv),
# downloads and configures Python 3.13 (via uv), handles macOS code-signing,
# installs all project & dev dependencies, and configures VS Code settings.
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
echo "OS:           $(uname -s) ($(uname -m))"
echo "----------------------------------------------------------------------"

# Ensure PATH includes common uv locations
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:/opt/homebrew/bin:${PATH}"

# Step 1: Check / Install uv
echo "[1/6] Checking for 'uv' package manager..."
if ! command -v uv &> /dev/null; then
    echo "  'uv' not found. Installing uv standalone binary..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
fi
echo "  uv version: $(uv --version)"

# Step 2: Ensure Python 3.13 runtime is installed & signed
echo "[2/6] Provisioning Python 3.13 runtime..."
uv python install 3.13

# Resolve Python 3.13 binary path
PYTHON_BIN="$(uv python find 3.13 2>/dev/null || true)"
if [ -z "${PYTHON_BIN}" ] || [ ! -f "${PYTHON_BIN}" ]; then
    # Fallback search in standard uv python share directory
    PYTHON_BIN="$(find "${HOME}/.local/share/uv/python" -name "python3.13" -type f 2>/dev/null | head -n 1 || true)"
fi

# macOS Gatekeeper / ad-hoc codesign fix for arm64/Apple Silicon
if [[ "$(uname -s)" == "Darwin" ]] && [ -n "${PYTHON_BIN}" ]; then
    echo "  Applying macOS quarantine removal and ad-hoc code signature..."
    PYTHON_DIR="$(dirname "$(dirname "${PYTHON_BIN}")")"
    xattr -r -d com.apple.quarantine "${PYTHON_DIR}" 2>/dev/null || true
    find "${PYTHON_DIR}" \( -name "*.dylib" -o -name "*.so" -o -type f -perm +111 \) -exec codesign --force --sign - {} + 2>/dev/null || true
fi

# Step 3: Create / Rebuild virtual environment (.venv)
echo "[3/6] Configuring virtual environment at .venv..."
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
REBUILD_VENV=0

if [ ! -f "${VENV_PYTHON}" ]; then
    REBUILD_VENV=1
elif ! "${VENV_PYTHON}" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "  Existing .venv interpreter is broken or incompatible (< Python 3.11). Rebuilding..."
    REBUILD_VENV=1
fi

if [ "${REBUILD_VENV}" -eq 1 ]; then
    if [ -n "${PYTHON_BIN}" ] && [ -f "${PYTHON_BIN}" ]; then
        uv venv --python "${PYTHON_BIN}" .venv --clear
    else
        uv venv --python 3.13 .venv --clear
    fi
else
    echo "  Existing valid .venv found."
fi

# Step 4: Install dependencies declared in pyproject.toml
echo "[4/6] Installing dependencies (editable + dev extras)..."
uv pip install -e ".[dev]"

# Step 5: Configure VS Code / IDE settings
echo "[5/6] Ensuring IDE settings (.vscode/settings.json & pyrightconfig.json)..."
mkdir -p .vscode

# Detect python minor version inside .venv for extraPaths
PY_VER="$("${VENV_PYTHON}" -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')"

cat <<EOF > .vscode/settings.json
{
  "python.defaultInterpreterPath": "\${workspaceFolder}/.venv/bin/python",
  "python.analysis.extraPaths": [
    "\${workspaceFolder}",
    "\${workspaceFolder}/src",
    "\${workspaceFolder}/.venv/lib/${PY_VER}/site-packages"
  ],
  "python.autoComplete.extraPaths": [
    "\${workspaceFolder}",
    "\${workspaceFolder}/src",
    "\${workspaceFolder}/.venv/lib/${PY_VER}/site-packages"
  ]
}
EOF

cat <<EOF > pyrightconfig.json
{
  "include": ["src", "tests"],
  "extraPaths": [".", ".venv/lib/${PY_VER}/site-packages"],
  "venvPath": ".",
  "venv": ".venv",
  "executionEnvironments": [
    {
      "root": "."
    }
  ]
}
EOF

# Step 6: Verify environment and run test suite
echo "[6/6] Verifying environment & running test suite..."
echo "----------------------------------------------------------------------"
echo "Python: $("${VENV_PYTHON}" --version)"
echo "Pytest: $("${PROJECT_ROOT}/.venv/bin/pytest" --version | head -n 1)"
echo "Ruff:   $("${PROJECT_ROOT}/.venv/bin/ruff" --version)"
echo "----------------------------------------------------------------------"

echo "Running pytest..."
"${PROJECT_ROOT}/.venv/bin/pytest"

echo "======================================================================"
echo "  Success! Environment setup is complete."
echo "  Selected Interpreter: ${PROJECT_ROOT}/.venv/bin/python"
echo "  To activate in your shell, run:"
echo "    source .venv/bin/activate"
echo "======================================================================"
