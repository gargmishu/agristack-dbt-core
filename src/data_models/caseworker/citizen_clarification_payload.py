"""Citizen clarification payload schema."""

from pydantic import Field

from src.data_models.common import StrictBaseModel, UtcTimestamp


class CitizenClarificationPayload(StrictBaseModel):
    """A citizen clarification appended to an open case review ticket."""

    text: str = Field(min_length=3, max_length=5000)
    received_at: UtcTimestamp