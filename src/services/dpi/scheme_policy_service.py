"""Authoritative DPI Registry: Scheme Policy & Calamity Notification Service (Data DHARA MCP).

Connects to harmonized NMDS 2.0 scheme policy catalogues via Model Context Protocol (MCP)
Streamable HTTP endpoints (`POST /mcp`) to verify whether a district and crop variety are
covered under active calamity relief and subsidy rules.

In production environments, LiveSchemePolicyService enforces live HTTPS communication with
strict fail-fast configuration and fail-closed error handling (no mock fallback).
In non-production, MockSchemePolicyService provides deterministic simulation for offline testing.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: decisions/step2.3_governance_flows_and_state_transitions.md
See: decisions/step3.7_live_service_integration.md
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import json
import logging
from typing import Any, Final, Protocol, Self

from httpx import AsyncClient

from src.config.service_settings import (
    get_scheme_policy_api_key,
    get_scheme_policy_endpoint,
    is_production,
)
from src.errors.service_errors import ServiceResponsePayloadError
from src.services.dpi.dpi_mock_fixtures import EXCLUDED_POLICY_PREFIX
from src.services.http_transport import (
    ServiceHttpTransport,
    ServiceTransportConfig,
    get_shared_http_client,
)

logger = logging.getLogger(__name__)

__all__ = [
    "LiveSchemePolicyService",
    "MockSchemePolicyService",
    "SchemePolicyService",
    "create_scheme_policy_service",
]

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0
_MCP_ENDPOINT_PATH: Final[str] = "/mcp"
_JSONRPC_VERSION: Final[str] = "2.0"
_MCP_TOOLS_CALL_METHOD: Final[str] = "tools/call"
_MCP_TOOL_SEARCH_DATASETS: Final[str] = "search_datasets"
_MCP_TOOL_GET_METADATA: Final[str] = "get_metadata"
_MCP_TOOL_GET_TABLE: Final[str] = "get_table"


class SchemePolicyService(Protocol):
    """Protocol contract for machine-readable scheme policy and calamity coverage verification."""

    async def verify_scheme_policy_coverage(
        self,
        district: str,
        crop_name: str,
        active_season: str = "KHARIF-2026",
    ) -> bool:
        """Queries harmonized scheme policy metadata to verify district and crop coverage."""
        ...


class LiveSchemePolicyService:
    """Production live client executing MCP JSON-RPC 2.0 calls to Data DHARA (`/mcp`).

    Strictly requires endpoint URL, API key, and pooled HTTP client. Communicates with
    Data DHARA's Stateless Streamable HTTP MCP server (`POST /mcp`) using tools
    `search_datasets`, `get_metadata`, and `get_table`. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote outages, raises
    ServiceRequestPayloadError on malformed policy queries (400/422),
    and raises ServiceResponsePayloadError on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live scheme policy MCP client with mandatory credentials and transport."""
        self._transport = ServiceHttpTransport(
            http_client=http_client,
            api_key=api_key,
            config=ServiceTransportConfig(
                service_name="scheme_policy",
                service_title="Scheme Policy Metadata",
                timeout_seconds=timeout_seconds,
            ),
            base_url=endpoint_url,
        )

    @classmethod
    def from_env(
        cls,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> Self:
        """Factory constructor building live instance from environment settings or overrides."""
        return cls(
            endpoint_url=endpoint_url or get_scheme_policy_endpoint() or "",
            api_key=api_key or get_scheme_policy_api_key() or "",
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def verify_scheme_policy_coverage(
        self,
        district: str,
        crop_name: str,
        active_season: str = "KHARIF-2026",
    ) -> bool:
        """Verifies whether a district and crop are covered under active scheme policy rules.

        Invokes Data DHARA's `get_table` MCP tool (`POST /mcp`) filtered by administrative
        district on the active seasonal dataset to confirm that the claimed crop variety is
        eligible for relief under the notified government resolution.

        Args:
            district: Administrative district name or Local Government Directory (LGD) code.
            crop_name: Claimed agricultural crop variety.
            active_season: Active agricultural season dataset identifier (e.g., 'KHARIF-2026').

        Returns:
            True if the district and crop are covered by the active scheme policy, False otherwise.

        Raises:
            ServiceRequestPayloadError: If policy query payload is rejected (400/422).
            ServiceResponsePayloadError: If MCP endpoint returns invalid response schema.
            ServiceUnavailableError: If MCP endpoint fails, times out, or returns 5xx.
            ServiceAuthenticationError: If MCP endpoint returns 401/403.
        """
        logger.info(
            "Live querying Data DHARA MCP scheme policy coverage for district=%s crop=%s season=%s",
            district,
            crop_name,
            active_season,
        )

        table_payload = await self.get_table(
            dataset_id=active_season,
            column="district",
            equals=district,
        )
        return self._evaluate_policy_coverage(table_payload, crop_name=crop_name)

    async def search_datasets(
        self,
        q: str = "",
        metadata_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Searches published NMDS 2.0 datasets via Data DHARA's `search_datasets` MCP tool."""
        return await self._call_mcp_tool(
            tool_name=_MCP_TOOL_SEARCH_DATASETS,
            arguments={
                "q": q,
                "metadata_id": metadata_id,
                "limit": limit,
                "offset": offset,
            },
            context_label=q or metadata_id or "all_datasets",
        )

    async def get_metadata(self, dataset_id: str) -> dict[str, Any]:
        """Retrieves NMDS 2.0 metadata and classifications via Data DHARA's `get_metadata` tool."""
        return await self._call_mcp_tool(
            tool_name=_MCP_TOOL_GET_METADATA,
            arguments={"dataset_id": dataset_id},
            context_label=dataset_id,
        )

    async def get_table(
        self,
        dataset_id: str,
        column: str = "",
        equals: str = "",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Queries harmonized dataset rows via Data DHARA's `get_table` MCP tool."""
        return await self._call_mcp_tool(
            tool_name=_MCP_TOOL_GET_TABLE,
            arguments={
                "dataset_id": dataset_id,
                "limit": limit,
                "offset": 0,
                "column": column,
                "equals": equals,
                "contains": "",
            },
            context_label=f"{dataset_id}:{column}={equals}",
        )

    # -------------------------------------------------------------------------
    # Private Helper Routines
    # -------------------------------------------------------------------------

    async def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context_label: str,
    ) -> dict[str, Any]:
        """Executes a JSON-RPC 2.0 `tools/call` POST against the `/mcp` Streamable HTTP endpoint."""
        rpc_payload: dict[str, Any] = {
            "jsonrpc": _JSONRPC_VERSION,
            "id": f"dhara-{tool_name}",
            "method": _MCP_TOOLS_CALL_METHOD,
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        response_data = await self._transport.post_json(
            _MCP_ENDPOINT_PATH,
            payload=rpc_payload,
            context_label=context_label,
        )
        return self._unwrap_mcp_response(response_data)

    def _unwrap_mcp_response(self, response_data: dict[str, Any]) -> dict[str, Any]:
        """Unwraps FastMCP JSON-RPC 2.0 `result.content[0].text` or direct result dictionaries."""
        target_url = self._transport.resolve_url(_MCP_ENDPOINT_PATH)
        if "error" in response_data:
            raise ServiceResponsePayloadError(
                f"Live scheme policy MCP check returned error payload from {target_url}.",
                service_name="scheme_policy",
            )

        result = response_data.get("result", response_data)
        if not isinstance(result, dict):
            raise ServiceResponsePayloadError(
                f"Live scheme policy check returned invalid schema from {target_url}.",
                service_name="scheme_policy",
            )

        if result.get("isError") is True:
            raise ServiceResponsePayloadError(
                f"Live scheme policy MCP tool execution failed from {target_url}.",
                service_name="scheme_policy",
            )

        content = result.get("content")
        if isinstance(content, list) and content:
            first_block = content[0]
            if isinstance(first_block, dict) and isinstance(first_block.get("text"), str):
                try:
                    parsed = json.loads(first_block["text"])
                except json.JSONDecodeError as err:
                    raise ServiceResponsePayloadError(
                        f"Live scheme policy MCP text block is not valid JSON from {target_url}.",
                        service_name="scheme_policy",
                    ) from err
                if isinstance(parsed, dict) and "error" not in parsed:
                    return parsed
                raise ServiceResponsePayloadError(
                    f"Live scheme policy check returned invalid schema from {target_url}.",
                    service_name="scheme_policy",
                )

        return result

    def _evaluate_policy_coverage(self, table_payload: dict[str, Any], crop_name: str) -> bool:
        """Evaluates whether the returned Data DHARA table rows cover the claimed crop variety."""
        if "is_policy_covered" in table_payload:
            return bool(table_payload["is_policy_covered"])

        rows = table_payload.get("rows")
        if isinstance(rows, list):
            normalized_target_crop = crop_name.strip().upper()
            for row in rows:
                if not isinstance(row, dict):
                    continue
                row_data = row.get("data", row)
                if not isinstance(row_data, dict):
                    continue
                row_crop = (
                    str(row_data.get("crop_name") or row_data.get("crop") or "").strip().upper()
                )
                if row_crop == normalized_target_crop:
                    if "is_policy_covered" in row_data:
                        return bool(row_data["is_policy_covered"])
                    if "eligible" in row_data:
                        return bool(row_data["eligible"])
                    return True
            return False

        target_url = self._transport.resolve_url(_MCP_ENDPOINT_PATH)
        raise ServiceResponsePayloadError(
            f"Live scheme policy check returned invalid schema from {target_url}.",
            service_name="scheme_policy",
        )


class MockSchemePolicyService:
    """Deterministic local simulation of harmonized Data DHARA scheme policy coverage rules."""

    async def verify_scheme_policy_coverage(
        self,
        district: str,
        crop_name: str,
        active_season: str = "KHARIF-2026",
    ) -> bool:
        """Simulates harmonized scheme policy table coverage rules for offline testing."""
        normalized_district = district.strip().upper()
        normalized_crop = crop_name.strip().upper()
        return bool(
            normalized_district
            and normalized_crop
            and active_season.strip()
            and not normalized_district.startswith(EXCLUDED_POLICY_PREFIX)
            and not normalized_crop.startswith(EXCLUDED_POLICY_PREFIX)
        )


def create_scheme_policy_service(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> SchemePolicyService:
    """Factory creating appropriate scheme policy service implementation based on environment.

    Resolution follows a 3-tier precedence model:
    1. Mandatory Production: If require_live=True (or ENVIRONMENT='production' is set),
       constructs LiveSchemePolicyService via environment settings, failing fast if credentials
       are missing.
    2. Explicit Parameters: If endpoint_url and api_key are provided directly as arguments,
       constructs LiveSchemePolicyService targeting those coordinates.
    3. Offline Simulation: If require_live is False and explicit credentials are not passed,
       returns MockSchemePolicyService to guarantee offline test isolation.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        return LiveSchemePolicyService.from_env(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    if endpoint_url and api_key:
        return LiveSchemePolicyService(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    return MockSchemePolicyService()
