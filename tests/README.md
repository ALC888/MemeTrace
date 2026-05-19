# Tests

运行全部测试：

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

测试覆盖：

- `test_ai_pipeline.py`
  - 公共样例全链路回归
  - 最终输出结构校验
- `test_backend_api.py`
  - 健康检查
  - 热点列表、详情、时间线、搜索
  - `reanalyze` 默认重置路径
  - `reanalyze` 自定义输入路径
