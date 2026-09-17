from __future__ import annotations

from typing import Any, Literal, get_args

from pydantic import Field, model_validator

from backend.api.schemas.common import ApiSchema
from backend.api.schemas.market import MarketMetric

AUTHORIZED_MARKET_METRICS = frozenset(get_args(MarketMetric))

MARKET_PERIODS = {
    '90d': '90 days', '90 dias': '90 days', '90 days': '90 days',
    '180d': '180 days', '180 dias': '180 days', '180 days': '180 days',
    '12m': '12 months', '12 meses': '12 months', '12 months': '12 months',
    'all': 'All available', 'all available': 'All available',
}


class ReportScopeHint(ApiSchema):
    """Untrusted geography hint for the server-owned report tool only."""

    city: str | None = Field(default=None, max_length=160)
    area: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def area_has_city(self) -> "ReportScopeHint":
        if self.area is not None and self.city is None:
            raise ValueError("A report area requires an explicit city.")
        return self


class AgentContextRequest(ApiSchema):
    """Untrusted UI selection hints, never authorization or analytical input.

    Only bounded identifiers and display filters are used to choose already
    authorized backend tools. Organization/user identity always comes from the
    authenticated server-side session.
    """

    metric: str | None = None
    region: str | None = None
    comparison_region: str | None = None
    period: str | None = None
    estate_id: str | None = Field(default=None, min_length=1, max_length=128)
    portfolio_id: str | None = Field(default=None, min_length=1, max_length=128)
    comparison_radius_meters: int | None = Field(default=None, ge=100, le=25_000)
    comparison_limit: int | None = Field(default=None, ge=1, le=20)
    selected_region: dict[str, Any] | str | None = None
    selected_property: dict[str, Any] | None = None
    market_filters: dict[str, Any] = Field(default_factory=dict)
    report_scope: ReportScopeHint | None = None

    def resolved_market_metric(self) -> str | None:
        """Return only a catalogued metric key supplied as a UI hint."""
        return self.metric if self.metric in AUTHORIZED_MARKET_METRICS else None

    def resolved_market_period(self) -> str:
        raw = (self.period or '').strip().lower()
        return MARKET_PERIODS.get(raw, 'All available')
    def resolved_estate_id(self) -> str | None:
        """Retain compatibility with the desktop's existing selected_property."""
        if self.estate_id:
            return self.estate_id
        candidate = (self.selected_property or {}).get("id")
        return candidate if isinstance(candidate, str) and 0 < len(candidate) <= 128 else None

    def resolved_report_scope(self) -> ReportScopeHint | None:
        return self.report_scope

    def resolved_heatmap(self) -> dict[str, Any] | None:
        """Whitelist UI map filters; arbitrary client fields never reach a tool."""
        raw = self.market_filters
        requested = {
            key: raw[key]
            for key in ("h3_resolution", "city", "area", "period_start", "period_end", "max_cells")
            if key in raw
        }
        if not requested and not self.region:
            return None
        if self.region and "city" not in requested:
            requested["city"] = self.region
        return requested


class AgentMessageRequest(ApiSchema):
    session_id: str | None = Field(default=None, max_length=200)
    message: str = Field(min_length=1, max_length=20_000)
    context: AgentContextRequest = Field(default_factory=AgentContextRequest)


class AgentMessage(ApiSchema):
    role: Literal["agent"] = "agent"
    content: str


class AgentSource(ApiSchema):
    label: str
    detail: str


class AgentAction(ApiSchema):
    label: str
    tool: str


class AgentInsight(ApiSchema):
    statement: str
    evidence_keys: list[str] = Field(default_factory=list)
    caveat: str | None = None


class AgentInterpretation(ApiSchema):
    answer: str
    answer_evidence_keys: list[str] = Field(default_factory=list)
    insights: list[AgentInsight] = Field(default_factory=list)
    follow_up: str | None = None


class AgentMessageResponse(ApiSchema):
    session_id: str
    message: AgentMessage
    sources: list[AgentSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    interpretation: AgentInterpretation | None = None


class AgentTraceEventResponse(ApiSchema):
    event_type: str
    status: str
    summary: str
    created_at: str | None = None
    tool: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentTraceResponse(ApiSchema):
    session_id: str
    events: list[AgentTraceEventResponse]
