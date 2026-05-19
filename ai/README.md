# AI Pipeline

`ai/` 目录提供离线可复跑的热点梗分析链路：

`normalize -> detect -> cluster -> attribute -> summarize -> export`

## 快速运行

在仓库根目录执行：

```bash
python ai/pipeline/run_full_pipeline.py \
  --input sample_data/raw-posts.public-sample.json \
  --out-dir sample_data/out/fullrun \
  --final-output sample_data/out/analysis-run.public-sample.json
```

## 目录说明

- `normalize/`
  - 文本清洗、分词、停用词过滤
- `detect/`
  - 热词候选发现
- `cluster/`
  - 相似表达归并
- `attribute/`
  - 来源归因与候选排序
- `summarize/`
  - 解释文案和趋势快照生成
- `pipeline/`
  - 全链路执行与最终导出
- `config/`
  - 各阶段配置

## 输入契约

原始输入为 JSON 数组，每条记录至少建议包含：

- `id`
- `platform`
- `content`
- `publish_time`
- `url`
- `metrics`

可选字段：

- `title`
- `author`
- `crawl_time`
- `extra.topic_tags`

## 输出契约

最终 `analysis-run` 结构至少包含：

- `run_id`
- `generated_at`
- `source_batch`
- `events`
- `evidence`
- `trend_snapshots`
- `stats`

其中 `source_batch.source_type` 统一使用：

- `mock`
- `public_sample`
- `captured_excerpt`

## 配置说明

- [normalization.json](/D:/360Downloads/MemeTrace-main/ai/config/normalization.json)
  - 文本清洗规则、token pattern、最短 token 长度
- [hotword_detection.json](/D:/360Downloads/MemeTrace-main/ai/config/hotword_detection.json)
  - 热词频次、跨帖数、突增分数阈值
- [cluster_rules.json](/D:/360Downloads/MemeTrace-main/ai/config/cluster_rules.json)
  - 别名字典、相似度阈值
- [source_attribution.json](/D:/360Downloads/MemeTrace-main/ai/config/source_attribution.json)
  - 平台权重、来源阈值、候选数量
- [explanation_templates.json](/D:/360Downloads/MemeTrace-main/ai/config/explanation_templates.json)
  - 来源解释模板

## 回归建议

- 修改配置后，先单独运行变更阶段，再跑全链路。
- 回归时忽略最终导出里的 `generated_at` 动态字段。
