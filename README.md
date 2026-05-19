# MemeTrace

基于网络热点实时更新的梗，搜集、分析、使用与溯源。

当前仓库已包含两部分可直接运行的内容：

- `ai/`
  - 离线热点梗分析链路
- `backend/`
  - FastAPI 后端 Demo

前端展示层当前不在这个仓库内，所以仓库内可直接演示的是：

- AI 全链路样例分析
- 后端接口与 Swagger

## 目录结构

```text
MemeTrace-main/
  ai/
  backend/
  sample_data/
  scripts/
  tests/
```

## 环境要求

- Python 3.10+
- Windows PowerShell 或任意能运行 Python 的终端

## 快速开始

### 1. 跑 AI 样例

```powershell
cd D:\360Downloads\MemeTrace-main
python ai\pipeline\run_full_pipeline.py `
  --input sample_data\raw-posts.public-sample.json `
  --out-dir sample_data\out\fullrun `
  --final-output sample_data\out\analysis-run.public-sample.json
```

或者直接运行：

```powershell
.\scripts\run-ai-public-sample.ps1
```

### 2. 启动后端

```powershell
cd D:\360Downloads\MemeTrace-main\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

或者直接运行：

```powershell
.\scripts\start-backend.ps1
```

启动后访问：

- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- Hot Events: [http://127.0.0.1:8000/api/hot-events](http://127.0.0.1:8000/api/hot-events)

## 常用演示路径

### AI 全链路

- 输入样例：`sample_data/raw-posts.public-sample.json`
- 中间输出：`sample_data/out/fullrun/`
- 最终导出：`sample_data/out/analysis-run.public-sample.json`

### 后端内置演示

- 默认会自动写入 SQLite 演示库：`backend/data/memetrace.db`
- 内置结构化输出样例：`backend/sample_data/analysis-run.public-sample.json`

## 后端与 AI 联动

后端 `POST /api/admin/reanalyze` 会执行：

```text
REPO_ROOT/ai/pipeline/run_full_pipeline.py
```

当前默认仓库结构就是：

```text
REPO_ROOT/
  ai/
  backend/
```

如果你的 AI 不在默认路径，可以启动前设置：

```powershell
$env:MEMETRACE_REPO_ROOT="D:\path\to\your\project"
```

然后保证下面这个文件真实存在：

```text
$env:MEMETRACE_REPO_ROOT\ai\pipeline\run_full_pipeline.py
```

## 测试

运行全部测试：

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

或者：

```powershell
.\scripts\run-tests.ps1
```

## 当前边界

- 仓库内没有前端页面代码
- 仓库内没有真实抓取器，只提供离线样例输入
- 后端默认使用 SQLite 做本地演示，便于答辩和联调
