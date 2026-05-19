# Full Pipeline Runner

## 目标
一键执行离线演示全流程：
`normalize -> detect -> cluster -> attribute -> summarize -> export`

## 运行方式
```bash
python ai/pipeline/run_full_pipeline.py \
  --input sample_data/raw-posts.public-sample.json \
  --out-dir sample_data/out/fullrun \
  --final-output sample_data/out/analysis-run.public-sample.json
```

## 产物
- `out-dir` 下保留各阶段中间结果
- `final-output` 为最终 analysis-run 结构

## 说明
最终输出包含 `generated_at` 动态时间戳；做稳定性比较时应忽略该字段。
