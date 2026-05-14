from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    HealthResponse,
    HotEventDetail,
    HotEventListResponse,
    ReanalyzeRequest,
    ReanalyzeResponse,
    SearchResponse,
    TimelineResponse,
)
from .services import (
    bootstrap_data,
    get_hot_event,
    get_timeline,
    list_hot_events,
    reset_demo_data,
    run_ai_pipeline,
    search_events,
)


app = FastAPI(
    title="MemeTrace Backend",
    description="热点梗实时抓取与溯源插件后端 Demo",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    bootstrap_data()


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="memetrace-backend")


@app.get("/api/hot-events", response_model=HotEventListResponse)
def hot_events(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> HotEventListResponse:
    items, total = list_hot_events(limit=limit, offset=offset)
    return HotEventListResponse(items=items, total=total)


@app.get("/api/hot-events/{event_id}", response_model=HotEventDetail)
def hot_event_detail(event_id: str) -> HotEventDetail:
    return get_hot_event(event_id)


@app.get("/api/hot-events/{event_id}/timeline", response_model=TimelineResponse)
def hot_event_timeline(event_id: str) -> TimelineResponse:
    nodes, snapshots = get_timeline(event_id)
    return TimelineResponse(event_id=event_id, nodes=nodes, snapshots=snapshots)


@app.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query(default="", description="关键词，匹配梗名、别名和解释"),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    items = search_events(q=q, limit=limit)
    return SearchResponse(q=q, items=items, total=len(items))


@app.post("/api/admin/reanalyze", response_model=ReanalyzeResponse)
def reanalyze(payload: ReanalyzeRequest | None = None) -> ReanalyzeResponse:
    request = payload or ReanalyzeRequest()
    if not request.input_path:
        count = reset_demo_data()
        return ReanalyzeResponse(
            ok=True,
            mode="demo_seed",
            message="已重置为内置样例分析结果",
            event_count=count,
            output_path=None,
        )

    count, output = run_ai_pipeline(
        input_path=request.input_path,
        final_output_path=request.final_output_path,
    )
    return ReanalyzeResponse(
        ok=True,
        mode="ai_pipeline",
        message="AI 流水线已执行并导入最新分析结果",
        event_count=count,
        output_path=str(output),
    )
