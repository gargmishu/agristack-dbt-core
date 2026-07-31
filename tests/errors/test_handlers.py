from datetime import UTC, datetime

import pytest
from fastapi import Request
from pydantic import ValidationError

from src.data_models.raw_ingress import WhatsAppIngressPayload
from src.errors.handlers import validation_exception_handler


@pytest.mark.asyncio
async def test_validation_exception_handler_rfc7807_format() -> None:
    # Trigger a real Pydantic ValidationError
    try:
        WhatsAppIngressPayload(
            session_id="short",  # min_length=8 violation
            originating_phone_number="invalid",
            channel_message_id="wamid",
            payload_type="invalid_type",  # type: ignore[arg-type]
            received_at=datetime.now(UTC),
        )
    except ValidationError as err:
        validation_error = err

    # Create dummy FastAPI Request
    scope = {"type": "http", "method": "POST", "path": "/api/v1/ingress/whatsapp"}
    request = Request(scope=scope)

    # Execute handler
    response = await validation_exception_handler(request, validation_error)
    assert response.status_code == 422  # noqa: PLR2004

    # Verify RFC 7807 payload fields
    body = bytes(response.body).decode("utf-8")
    assert "https://api.agristack.gov.in/errors/invalid-payload" in body
    assert "Invalid Payload Structure" in body
    assert "invalid_params" in body
