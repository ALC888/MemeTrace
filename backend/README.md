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

运行产物只放在 `backend/data/` 下，并已加入 `.gitignore`；仓库内保留的结构化演示样例是 `backend/sample_data/analysis-run.public-sample.json`。

## 后端与 AI 目录约定

后端以后统一以“同时包含 `backend/` 与 `ai/` 的项目根目录”为仓库根目录。默认情况下，后端会把 `backend/..` 识别为 `REPO_ROOT`，并要求下面这个脚本真实存在：

```text
REPO_ROOT/
  backend/
  ai/
    pipeline/
      run_full_pipeline.py
```

也就是说，`POST /api/admin/reanalyze` 会执行：

```text
REPO_ROOT/ai/pipeline/run_full_pipeline.py
```

如果本地联调阶段 AI 目录不在默认位置，例如实际在 `外包 梗/ai`，需要先把后端放到同一个项目根下，或启动前显式指定：

```powershell
$env:MEMETRACE_REPO_ROOT="D:\path\to\外包 梗"
```

此时也必须保证：

```text
$env:MEMETRACE_REPO_ROOT\ai\pipeline\run_full_pipeline.py
```

存在。若脚本不存在，`reanalyze` 会直接返回错误，不会静默写入旧数据。

## source_type 枚举

后端与 AI 契约统一使用以下 `source_type` 枚举：

- `mock`
- `public_sample`
- `captured_excerpt`

内置演示数据使用 `public_sample`，不再使用 `local_sample`。

`POST /api/admin/reanalyze` 支持两种模式：

1. 不传参数：重置为内置样例分析结果。
2. 传入 `input_path`：调用仓库已有 AI 流水线 `ai/pipeline/run_full_pipeline.py`，再把生成的 `analysis-run` 结果导入数据库。

示例：

```json
{
  "input_path": "sample_data/processed/raw-posts.task2.input.json"
}
```
