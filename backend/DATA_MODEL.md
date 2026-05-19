# Backend Data Model

后端当前围绕 4 类核心对象组织：

## RawPost

原始平台内容，主要由 AI 输入样例和外部导入数据承载。建议字段：

- `id`
- `platform`
- `title`
- `content`
- `author`
- `publish_time`
- `crawl_time`
- `url`
- `metrics`

## MemeEvent

热点梗事件的聚合结果，对应数据库 `meme_events` 表。

- `id`
- `name`
- `aliases`
- `summary`
- `heat_score`
- `confidence`
- `first_seen_time`
- `source_platform`
- `status`
- `source_confidence`
- `source_status`

## Evidence

事件的来源证据和传播证据，对应数据库 `evidence` 表。

- `id`
- `event_id`
- `raw_post_id`
- `platform`
- `snippet`
- `post_time`
- `url`
- `relevance_score`
- `source_score`
- `is_source_candidate`
- `evidence_type`

## TrendSnapshot

事件热度快照，对应数据库 `trend_snapshots` 表。

- `id`
- `event_id`
- `snapshot_time`
- `heat_value`
- `platform_breakdown`
- `sample_count`
