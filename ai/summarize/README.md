# Task 6: Explanation Generation Baseline

## 目标
基于聚类与来源归因结果生成事件解释文案，并对低证据场景进行降级输出。

## 输入
- Task 3 热词输出
- Task 4 聚类输出
- Task 5 来源归因输出

## 输出
- 事件解释（MemeEvent字段对齐）
- 证据列表透传
- 趋势快照（基于证据平台分布生成）

## 运行方式
```bash
python ai/summarize/explanation_generation.py \
  --hotwords sample_data/processed/hotwords.task3.output.json \
  --clusters sample_data/processed/clusters.task4.output.json \
  --attribute sample_data/processed/source-attribution.task5.output.json \
  --output sample_data/processed/summaries.task6.output.json \
  --config ai/config/explanation_templates.json
```

## 降级规则
- source_status = probable: 生成完整解释
- source_status = uncertain: 生成保守解释并提示人工复核
- source_status = insufficient_evidence: 输出证据不足模板并标记 explanation_status 为 insufficient_context

## 全流程闭环
可通过 `ai/pipeline/run_full_pipeline.py` 一键跑通到导出结果。
