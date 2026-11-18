"""Layer 3 Interactive End-to-End Sandbox UI Renderer.

Loads and renders the self-contained 3-pane HTML/CSS/JS test dashboard for interactive
verification across Layer 1 omnichannel ingress, Layer 2 RAM-only SHA-256 HMAC tokenization,
Layer 3 modality extraction, and Layer 4 deterministic governance, caseworker review, and
immutable CAG trigger audit trails.

See: decisions/step3.4_layer3_intake_gateway_and_connectors.md
See: decisions/step4.1_multichannel_ingress_and_modality_convergence.md
See: decisions/step4.5_database_persistence_and_analytical_deduplication.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

__all__ = ["PublicAgentSandboxRenderer"]

_SANDBOX_CONFIG_PLACEHOLDER: Final[str] = "__AGRISTACK_SANDBOX_CONFIG_JSON__"
_DEFAULT_TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "static" / "e2e_sandbox.html"
)


class PublicAgentSandboxRenderer:
    """Renders the self-contained interactive End-to-End Zero-Trust Sandbox HTML dashboard."""

    def __init__(self, template_path: Path | None = None) -> None:
        """Initializes the sandbox renderer and validates the static HTML template asset.

        Args:
            template_path: Optional override path to an HTML template file.
        """
        resolved_template_path = template_path or _DEFAULT_TEMPLATE_PATH
        self._template_content = self._load_template_content(resolved_template_path)

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    def render_sandbox_html(
        self,
        *,
        whatsapp_auth_enabled: bool = False,
        bearer_auth_enabled: bool = False,
    ) -> str:
        """Renders the interactive sandbox HTML page with non-sensitive runtime auth flags.

        Why inject only boolean flags?
        Zero-Trust security rules forbid embedding cryptographic secrets, HMAC keys, or
        carrier bearer tokens into client-facing HTML responses. Only boolean enforcement
        indicators are serialized so the dashboard can display active perimeter guards safely.

        Args:
            whatsapp_auth_enabled: True when server enforces X-Hub-Signature-256 verification.
            bearer_auth_enabled: True when server enforces Carrier Bearer token verification.

        Returns:
            Complete HTML5 document string ready for an ASGI HTMLResponse.
        """
        sandbox_runtime_config = {
            "whatsappAuthEnabled": whatsapp_auth_enabled,
            "bearerAuthEnabled": bearer_auth_enabled,
        }
        serialized_config = json.dumps(sandbox_runtime_config)
        return self._template_content.replace(_SANDBOX_CONFIG_PLACEHOLDER, serialized_config, 1)

    # -------------------------------------------------------------------------
    # Private Helpers (Strictly at Bottom)
    # -------------------------------------------------------------------------

    @staticmethod
    def _load_template_content(template_path: Path) -> str:
        """Reads and validates the sandbox HTML asset from disk."""
        if not template_path.is_file():
            raise FileNotFoundError(
                f"Sandbox HTML template asset does not exist at '{template_path}'."
            )
        template_text = template_path.read_text(encoding="utf-8")
        if _SANDBOX_CONFIG_PLACEHOLDER not in template_text:
            raise ValueError(
                f"Sandbox HTML template at '{template_path}' is missing required placeholder "
                f"'{_SANDBOX_CONFIG_PLACEHOLDER}'."
            )
        return template_text
