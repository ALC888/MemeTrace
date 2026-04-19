# Task 2: Text Normalization Pipeline

## 目标
将多平台原始文本清洗成可分析语料，输出稳定、可复跑的标准化结果。

## 覆盖范围
- 去链接
- 去@提及
- 处理转发前缀
- 话题标签提取与归一
- 重复标点压缩
- 空白标准化
- 基础分词 + 停用词过滤

## 运行方式
```bash
python ai/normalize/normalize_pipeline.py \
  --input sample_data/processed/raw-posts.task2.input.json \
  --output sample_data/processed/raw-posts.task2.normalized.json \
  --config ai/config/normalization.json \
  --stopwords ai/config/stopwords_zh.txt
```

## 输出说明
输出为 JSON，包含：
- `run_stage`: 固定为 `normalize`
- `config_version`: 清洗规则版本
- `input_count` / `output_count`: 输入输出条数
- `posts`: 清洗后的帖子列表，每条新增：
  - `normalized_content`
  - `tokens`
  - `normalization_meta`

## 说明
本基线优先保证可解释和可复现，不依赖外部在线服务。
