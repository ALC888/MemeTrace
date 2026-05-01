# MemeTrace Backend

热点梗实时抓取与溯源插件的后端 Demo，实现参赛计划中的最小接口闭环：

- `GET /api/hot-events`
- `GET /api/hot-events/{id}`
- `GET /api/hot-events/{id}/timeline`
- `GET /api/search?q=`
- `POST /api/admin/reanalyze`

## 运行

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

接口文档：

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/api/health

如果使用 Codex 工作区 Python 并把依赖安装到 `backend/.deps`，可在 PowerShell 中这样启动：

```powershell
$env:PYTHONPATH="D:\360Downloads\MemeTrace-main\backend\.deps;D:\360Downloads\MemeTrace-main\backend"
C:\Users\29569\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m uvicorn app.main:app --reload
```

## 数据说明

当前版本默认使用 `backend/data/memetrace.db` 作为本地演示数据库，并在首次启动时写入内置样例数据。这样答辩现场即使没有 MySQL 和外网，也可以稳定演示。

`POST /api/admin/reanalyze` 支持两种模式：

1. 不传参数：重置为内置样例分析结果。
2. 传入 `input_path`：调用仓库已有 AI 流水线 `ai/pipeline/run_full_pipeline.py`，再把生成的 `analysis-run` 结果导入数据库。

示例：

```json
{
  "input_path": "sample_data/processed/raw-posts.task2.input.json"
}
```
