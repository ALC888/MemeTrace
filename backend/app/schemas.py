from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class HotEventListItem(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    summary: str | None = None
    heat_score: float = 0.0
    confidence: float | None = None
    first_seen_time: str | None = None
    source_platform: str | None = None
    status: str = "needs_review"
    evidence_count: int = 0


class EvidenceItem(BaseModel):
    id: str
    event_id: str
    raw_post_id: str | None = None
    platform: str | None = None
    snippet: str | None = None
    post_time: str | None = None
    url: str | None = None
    relevance_score: float = 0.0
    source_score: float = 0.0
    is_source_candidate: bool = False
    evidence_type: str | None = None


class TrendSnapshotItem(BaseModel):
    id: str
    event_id: str
    snapshot_time: str | None = None
    heat_value: float = 0.0
    platform_breakdown: dict[str, float] = Field(default_factory=dict)
    sample_count: int = 0


class TimelineNode(BaseModel):
    id: str
    event_id: str
    platform: str | None = None
    time: str | None = None
    title: str
    snippet: str | None = None
    url: str | None = None
    source_score: float = 0.0
    node_type: str = "evidence"


class HotEventDetail(HotEventListItem):
    source_confidence: float | None = None
    source_status: str | None = None
    representative_evidence_id: str | None = None
    keyword_signals: list[dict[str, Any]] = Field(default_factory=list)
    explanation_status: str | None = None
    notes: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    latest_snapshot: TrendSnapshotItem | None = None


class HotEventListResponse(BaseModel):
    items: list[HotEventListItem]
    total: int


class TimelineResponse(BaseModel):
    event_id: str
    nodes: list[TimelineNode]
    snapshots: list[TrendSnapshotItem]


class SearchResponse(BaseModel):
    q: str
    items: list[HotEventListItem]
    total: int


class ReanalyzeRequest(BaseModel):
    input_path: str | None = None
    final_output_path: str | None = None


class ReanalyzeResponse(BaseModel):
    ok: bool
    mode: str
    message: str
    event_count: int
    output_path: str | None = None
