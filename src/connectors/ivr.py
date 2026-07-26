"""Layer 1 IVR Telephony Edge Connector skeleton."""

from src.models.raw_ingress import IVRIngressPayload


class IVRConnector:
    """Processes IVR voice SIP gateway streams and passes canonical ingress payload."""

    async def process_call_session(self, payload: IVRIngressPayload) -> IVRIngressPayload:
        return payload
