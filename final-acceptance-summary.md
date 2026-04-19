# 任务1到任务7总验收总结与答辩提纲

日期：2026-04-18
范围：AI职责任务1-7
结论：整体通过，已形成可复跑、可解释、可演示的离线分析流水线

## 1. 项目目标回顾

本阶段目标是为“热点梗实时抓取与溯源插件”建立一条离线可复现的 AI 分析链路，覆盖输入契约、文本清洗、热词发现、相似表达聚类、来源归因、解释生成和自动化回归验证。

最终要求不是单点效果，而是：
- 输出结构稳定
- 每一步可解释
- 同一输入重复运行结果稳定
- 低证据场景可降级
- 能为后端和前端联调提供固定契约

## 2. 任务1到任务7完成情况

### Task 1. 输入输出契约
- 交付：`harness/ai-schema-contract.md`
- 核心内容：`RawPost`、`MemeEvent`、`Evidence`、`TrendSnapshot` 契约与降级规则
- 验证结果：通过

### Task 2. 文本标准化
- 交付：`ai/normalize/normalize_pipeline.py`
- 配置：`ai/config/normalization.json`、`ai/config/stopwords_zh.txt`
- 样例：`sample_data/processed/raw-posts.task2.input.json`、`sample_data/processed/raw-posts.task2.normalized.json`
- 验证结果：链接、@、转发前缀、重复标点处理有效；重复运行一致

### Task 3. 热词发现
- 交付：`ai/detect/hotword_detection.py`
- 配置：`ai/config/hotword_detection.json`
- 样例：`sample_data/processed/hotwords.task3.output.json`
- 验证结果：目标词“某梗”进入候选第1；得分与窗口信息可解释；重复运行一致

### Task 4. 相似表达聚类
- 交付：`ai/cluster/similar_expression_cluster.py`
- 配置：`ai/config/cluster_rules.json`
- 样例：`sample_data/processed/clusters.task4.output.json`
- 验证结果：`某梗` 与 `某梗变体` 成功归并；无关表达未误合并；重复运行一致

### Task 5. 来源归因
- 交付：`ai/attribute/source_attribution.py`
- 配置：`ai/config/source_attribution.json`
- 样例：`sample_data/processed/source-attribution.task5.output.json`
- 验证结果：来源候选排序与评分明细完整；`某梗` 判定为 probable 且平台为 weibo；低证据事件自动降级

### Task 6. 解释生成与完整闭环
- 交付：`ai/summarize/explanation_generation.py`、`ai/config/explanation_templates.json`
- 闭环：`ai/pipeline/run_full_pipeline.py`、`ai/pipeline/export_analysis_run.py`
- 样例：`sample_data/processed/summaries.task6.output.json`、`sample_data/processed/analysis-run.task6.output.json`
- 验证结果：解释文案可生成；低证据自动降级；`normalize -> detect -> cluster -> attribute -> summarize -> export` 全链路跑通

### Task 7. 自动化回归
- 交付：`tests/test_regression.py`、`tests/README.md`
- 报告：`harness/task7-regression-report-20260418.md`
- 验证结果：`python -m unittest discover -s tests -p "test_*.py"` 通过，`5 tests OK`

## 3. 关键验收证据

- Task 2+Task 3 阶段验收通过：`harness/stage-acceptance-task2-task3-20260418.md`
- Task 4 阶段验收通过：`harness/task-progress-check.md` 中 Check E
- Task 5 阶段验收通过：`harness/task5-source-attribution-report-20260418.md`
- Task 6 阶段验收通过：`harness/task6-explanation-and-closure-report-20260418.md`
- Task 7 阶段验收通过：`harness/task7-regression-report-20260418.md`

### 稳定性结论
- Task 2、Task 3、Task 4、Task 5 的双次复跑哈希一致
- Task 6 的最终导出包含 `generated_at` 动态时间戳，直接哈希不同属于预期
- 忽略 `generated_at` 后，Task 6 两次完整闭环输出结构一致，`equal_without_generated_at = true`
- Task 7 自动化回归已通过，可作为后续变更的必跑基线

## 4. 对外可讲的结果

你可以把这套成果概括为三句话：

1. 这不是一个单点模型，而是一条离线可复跑的完整分析流水线。
2. 每个阶段都有固定输入、固定输出和可解释中间证据。
3. 即使在证据不足时，系统也会保守降级，而不是编造结论。

## 5. 答辩用提纲

### 5.1 开场
- 说明目标：把多平台文本变成可解释的热点梗事件结果。
- 说明约束：离线复现、字段稳定、证据可追溯、低证据降级。

### 5.2 方案结构
- 输入契约：RawPost / MemeEvent / Evidence / TrendSnapshot。
- 处理链路：normalize -> detect -> cluster -> attribute -> summarize -> export。
- 质量保障：固定样例回归测试。

### 5.3 阶段亮点
- Task 2：把脏文本清洗成可分析语料。
- Task 3：把候选热词排序做成可解释结果。
- Task 4：把同义变体归并成单一事件。
- Task 5：把来源判断拆成评分构成。
- Task 6：把解释生成做成模板化、可降级输出。
- Task 7：把前面所有阶段固化成自动回归。

### 5.4 结果展示顺序
- 先展示契约和样例文件。
- 再展示 Task 2 到 Task 5 的中间结果。
- 然后展示 Task 6 的最终 analysis-run 输出。
- 最后展示 Task 7 的自动化回归结果。

### 5.5 可能被问到的问题
- 为什么要保留中间结果：为了可解释和可回归。
- 为什么有些事件是 `needs_review`：因为证据不足，系统按规则保守降级。
- 为什么最终文件哈希可能变化：因为 `generated_at` 是动态字段。
- 如何判断稳定：忽略动态字段后比对结构一致，并通过自动化回归。

## 6. 风险与边界

- 当前分词与相似度仍是 baseline 规则，适合 Demo 和答辩，不代表最终上线形态。
- 当前时间窗口和来源权重较简化，后续可按真实数据继续校准。
- 仍需扩充更多负样本和边界样本，以提升回归覆盖面。

## 7. 最终结论

任务1到任务7已形成完整交付闭环，满足“可复跑、可解释、可演示”的目标。当前最适合的下一步是把这份总结作为答辩主材料，再按需要拆成 3 分钟、5 分钟或 10 分钟版本。