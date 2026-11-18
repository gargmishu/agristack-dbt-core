"""Interactive End-to-End Zero-Trust Sandbox Webapp Launcher.

Starts the local FastAPI ASGI server with offline mock sovereign AI/DPI blocks and an
in-memory (or user-specified) SQLite relational audit ledger, exposing the 3-pane
End-to-End Sandbox UI at `/sandbox` alongside Swagger OpenAPI docs at `/docs`.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/run_e2e_webapp.py
    PYTHONPATH=. .venv/bin/python scripts/run_e2e_webapp.py --port 8080
"""

from __future__ import annotations

import argparse
import os
from typing import Final

import uvicorn

from src.public_agent import create_public_agent_http_app

SANDBOX_PEPPER_SECRET: Final[str] = "sovereign_karnal_pilot_hmac_pepper_2026_secret_key"  # noqa: S105
DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8000
DEFAULT_DATABASE_URL: Final[str] = "sqlite:///:memory:"
BANNER_WIDTH: Final[int] = 84


def _build_argument_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser for the sandbox webapp launcher."""
    parser = argparse.ArgumentParser(
        description="Launch the AgriStack DBT Core 4-Layer Zero-Trust E2E Sandbox Webapp."
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Network bind address (default: {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP listen port (default: {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help=f"SQLAlchemy database URL (default: {DEFAULT_DATABASE_URL}).",
    )
    parser.add_argument(
        "--whatsapp-secret",
        default=None,
        help="Optional WhatsApp HMAC secret to enforce X-Hub-Signature-256 verification.",
    )
    parser.add_argument(
        "--bearer-token",
        default=None,
        help="Optional Carrier Bearer token to enforce Authorization header verification.",
    )
    return parser


def _configure_sandbox_environment() -> None:
    """Configures local sandbox environment defaults when variables are not already set."""
    os.environ.setdefault("AGRISTACK_PEPPER_SECRET", SANDBOX_PEPPER_SECRET)
    os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "120")
    os.environ.setdefault("RATE_LIMIT_CAPACITY", "40")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("SERVICE_RUNTIME_MODE", "MOCK")


def _print_startup_banner(host: str, port: int, database_url: str) -> None:
    """Prints clickable local URLs for the interactive E2E sandbox and OpenAPI docs."""
    base_url = f"http://{host}:{port}"
    print(f"\n{'=' * BANNER_WIDTH}")
    print("  AGRISTACK DBT CORE — 4-LAYER ZERO-TRUST E2E SANDBOX WEBAPP")
    print(f"{'=' * BANNER_WIDTH}")
    print(f"  Interactive E2E Sandbox UI : {base_url}/sandbox")
    print(f"  Swagger OpenAPI Reference  : {base_url}/docs")
    print(f"  Container Liveness Probe   : {base_url}/healthz")
    print(f"  Relational Audit Ledger    : {database_url}")
    print(f"{'=' * BANNER_WIDTH}\n")


def launch_e2e_webapp() -> None:
    """Parses CLI flags, initializes the FastAPI sandbox app, and starts Uvicorn."""
    argument_parser = _build_argument_parser()
    parsed_arguments = argument_parser.parse_args()

    _configure_sandbox_environment()
    fastapi_app = create_public_agent_http_app(
        whatsapp_app_secret=parsed_arguments.whatsapp_secret,
        carrier_bearer_token=parsed_arguments.bearer_token,
        database_url=parsed_arguments.database_url,
        enable_sandbox_ui=True,
    )
    _print_startup_banner(
        host=parsed_arguments.host,
        port=parsed_arguments.port,
        database_url=parsed_arguments.database_url,
    )
    uvicorn.run(
        fastapi_app,
        host=parsed_arguments.host,
        port=parsed_arguments.port,
    )


if __name__ == "__main__":
    launch_e2e_webapp()
