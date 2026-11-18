"""Unit tests for PublicAgentSandboxRenderer interactive E2E HTML rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.public_agent import PublicAgentSandboxRenderer


def test_default_sandbox_renderer_embeds_all_omnichannel_and_audit_routes() -> None:
    """Verifies default HTML rendering injects boolean auth flags and mounts all E2E routes."""
    renderer = PublicAgentSandboxRenderer()
    rendered_html = renderer.render_sandbox_html(
        whatsapp_auth_enabled=True,
        bearer_auth_enabled=False,
    )

    assert "<!DOCTYPE html>" in rendered_html
    assert "__AGRISTACK_SANDBOX_CONFIG_JSON__" not in rendered_html
    assert '{"whatsappAuthEnabled": true, "bearerAuthEnabled": false}' in rendered_html

    expected_endpoints = (
        "/healthz",
        "/v1/webhooks/whatsapp",
        "/v1/webhooks/ussd",
        "/v1/webhooks/sms",
        "/v1/webhooks/ivr",
        "/v1/webhooks/payments/callback",
        "/v1/caseworker/cases",
        "/v1/audit/funnel",
        "/v1/audit/history/",
    )
    for endpoint_path in expected_endpoints:
        assert endpoint_path in rendered_html


def test_sandbox_renderer_raises_file_not_found_for_missing_template(tmp_path: Path) -> None:
    """Verifies PublicAgentSandboxRenderer fails fast when template file is missing."""
    missing_template_path = tmp_path / "nonexistent_sandbox.html"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        PublicAgentSandboxRenderer(template_path=missing_template_path)


def test_sandbox_renderer_raises_value_error_when_placeholder_missing(tmp_path: Path) -> None:
    """Verifies PublicAgentSandboxRenderer rejects templates missing the config placeholder."""
    invalid_template_path = tmp_path / "invalid_sandbox.html"
    invalid_template_path.write_text("<html><body>No config token</body></html>", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required placeholder"):
        PublicAgentSandboxRenderer(template_path=invalid_template_path)
