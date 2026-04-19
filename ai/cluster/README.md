# Task 4: Similar-Expression Clustering Baseline

## 目标
将不同写法的同一热梗归并为单一事件候选，为 Task 5 溯源与 Task 6 解释生成提供稳定输入。

## 输入
- Task 2 输出：标准化文本结果
- Task 3 输出：热词候选结果

## 基线策略
- 词形归一：去空白、小写化
- 别名词典映射：优先使用 `alias_map`
- 关键词重合度：基于中文片段集合的 Jaccard
- 向量相似度辅助：基于字符计数余弦相似度（离线可复现代理）
- 兜底：未命中规则/阈值的词保留为 singleton

## 运行方式
```bash
python ai/cluster/similar_expression_cluster.py \
  --normalized sample_data/processed/raw-posts.task2.normalized.json \
  --hotwords sample_data/processed/hotwords.task3.output.json \
  --output sample_data/processed/clusters.task4.output.json \
  --config ai/config/cluster_rules.json
```

## 输出说明
- `clusters`: 聚类结果（canonical + member_terms）
- `term_mappings`: 词项到聚类中心映射及证据
- `post_cluster_links`: 帖子到聚类词映射
- `stats`: 聚类统计

## 说明
该版本先保证可解释与可复跑，后续可替换为真实向量模型相似度并保持字段不变。
