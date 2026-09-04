"""FastAPI exception handler for Pydantic ValidationError instances.

Translates internal schema validation errors into standard RFC 7807 problem details payloads.

See: decisions/step2.0_canonical_domain_schemas.md (Section 5)
"""

import logging
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)

__all__ = ["validation_exception_handler"]


async def validation_exception_handler(
    incoming_request: Request, validation_error: ValidationError
) -> JSONResponse:
    """FastAPI exception handler for Pydantic ValidationError.

    See: decisions/step2.0_canonical_domain_schemas.md#5-api-exception-handling--security-defense

    Converts validation errors into RFC 7807 problem details payloads while
    sanitizing internal stack traces.
    """
    invalid_params = [
        {
            "field": ".".join(str(segment) for segment in error_detail["loc"]),
            "reason": error_detail["msg"],
        }
        for error_detail in validation_error.errors()
    ]

    request_path = incoming_request.scope.get("path", "<unknown>")
    logger.warning(
        "Request validation failed for path=%s: %d invalid parameters",
        request_path,
        len(invalid_params),
    )

    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={
            "type": "https://api.agristack.gov.in/errors/invalid-payload",
            "title": "Invalid Payload Structure",
            "status": HTTPStatus.UNPROCESSABLE_ENTITY,
            "detail": "The submitted payload violated inter-layer schema validation constraints.",
            "invalid_params": invalid_params,
        },
    )
