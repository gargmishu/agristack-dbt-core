"""External Service Abstractions package for Foundational AI Blocks and DPI Registries."""

from src.services.ai import BhashiniService, SlmExtractor
from src.services.delivery import MultichannelNotificationService
from src.services.dpi import (
    AgriRegistryService,
    IdentityVerificationService,
    PaymentRailService,
    SocialRegistryService,
)

__all__ = [
    "AgriRegistryService",
    "BhashiniService",
    "IdentityVerificationService",
    "MultichannelNotificationService",
    "PaymentRailService",
    "SlmExtractor",
    "SocialRegistryService",
]
