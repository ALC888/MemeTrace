# Sample Data

本目录存放仓库内可直接运行的演示数据。

- `raw-posts.public-sample.json`
  - AI 全链路的原始输入样例
  - 可直接传给 `ai/pipeline/run_full_pipeline.py --input`
  - 包含微博、B 站、抖音 3 个平台共 6 条帖子

说明：

- 该样例使用公开演示字段结构，不依赖外部抓取服务。
- AI 输出文件默认不要提交到仓库，建议写到临时目录或 `backend/data/pipeline_runs/`。
