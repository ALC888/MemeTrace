# Task 3: Hotword Detection Baseline

## 目标
从 Task 2 标准化语料中产出可解释的热词候选 Top-N 列表。

## 方法（baseline）
- 候选抽取：来自 `tokens`、`topic_tags`，并额外从文本中抽取“*梗*”片段
- 频次统计：统计候选词总出现次数
- 时间窗口涨幅：按发布时间排序后切分为前后两个窗口，计算增长比
- 跨帖子覆盖：统计候选词出现于多少条帖子
- 综合打分：`frequency + burst + cross_post` 加权
- 噪声过滤：denylist、最小频次、最小帖子覆盖、最小分数阈值

## 运行方式
```bash
python ai/detect/hotword_detection.py \
  --input sample_data/processed/raw-posts.task2.normalized.json \
  --output sample_data/processed/hotwords.task3.output.json \
  --config ai/config/hotword_detection.json
```

## 输出字段
- `run_stage`: 固定为 `detect`
- `hotwords`: 候选词列表（已按分数排序）
- `stats`: 候选总量与入选数量

## 说明
该版本强调可解释和可调参，后续可在 Task 4 结合聚类进一步去重与归并。
