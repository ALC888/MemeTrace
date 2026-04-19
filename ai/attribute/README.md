# Task 5: Source Attribution Scoring Baseline

## 目标
对每个聚类事件输出疑似来源排序、评分构成和证据明细。

## 输入
- Task 2 输出：标准化帖子
- Task 4 输出：聚类结果与帖子映射

## 评分组成
- 时间得分：越早发布时间得分越高
- 平台权重：按配置给不同平台基础权重
- 证据相关度：帖子是否包含事件核心词
- 文本代表性：按互动指标归一化估算代表性

最终分数为四项加权和，权重在配置中可调。

## 运行方式
```bash
python ai/attribute/source_attribution.py \
  --normalized sample_data/processed/raw-posts.task2.normalized.json \
  --clusters sample_data/processed/clusters.task4.output.json \
  --output sample_data/processed/source-attribution.task5.output.json \
  --config ai/config/source_attribution.json
```

## 输出说明
- events：每个事件的来源判断（probable / uncertain / insufficient_evidence）
- evidence：来源证据条目及 source_score
- stats：来源状态计数

## 降级规则
- 候选证据条数不足时强制降级为 insufficient_evidence
- 最高分低于阈值时降级为 uncertain 或 insufficient_evidence
