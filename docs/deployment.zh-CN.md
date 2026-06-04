# 部署指南

本指南介绍如何使用 Docker 或直接在服务器上部署 IBKR Dash。

## 快速启动（本地开发）

### 前置条件

- Python 3.11+
- Node.js 18+
- IBKR Flex Query Token（用于数据导入）
- （可选）OpenAI 兼容的 API Key（用于 AI 功能）

### 步骤 1：克隆并配置

```bash
cd /path/to/ibkr-dash

# 后端配置
cp ibkr_dash_backend/.env.example ibkr_dash_backend/.env
# 编辑 ibkr_dash_backend/.env，填入 LLM API Key 和登录密码

# Worker 配置
cp ibkr_dash_worker/.env.example ibkr_dash_worker/.env
# 编辑 ibkr_dash_worker/.env，填入 IBKR Flex Token
```

### 步骤 2：启动后端

```bash
cd ibkr_dash_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 步骤 3：启动前端

```bash
cd ibkr_dash_frontend
npm install
npm run dev
```

### 步骤 4：导入数据

```bash
cd ibkr_dash_worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 导入 Flex CSV 文件
python -m worker.main import ../data/flex_exports/your_file.csv

# 或导入示例数据用于测试
python -m worker.main import worker/fixtures/daily_sample.csv
```

### 步骤 5：访问

- 前端：http://localhost:5173
- API 文档：http://localhost:8000/docs
- 登录：`admin` / 你设置的密码

## 配置参考

### 后端 (`ibkr_dash_backend/.env`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SQLITE_PATH` | `data/ibkr_dash.db` | SQLite 数据库路径 |
| `LLM_API_KEY` | (空) | OpenAI 兼容的 API Key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM 端点 |
| `LLM_DEFAULT_MODEL` | `gpt-4o` | 模型名称 |
| `AUTH_PASSWORD` | (空) | 登录密码（空 = 无认证） |

### Worker (`ibkr_dash_worker/.env`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FLEX_TOKEN` | (空) | IBKR Flex Web Service Token |
| `FLEX_QUERY_ID_DAILY` | (空) | 每日快照查询 ID |
| `DATA_DIR` | `data/flex_exports` | CSV 导入目录 |

### 支持的 LLM 提供商

| 提供商 | Base URL | 模型示例 |
|--------|----------|----------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` |
| 小米 MiMo | `https://token-plan-cn.xiaomimimo.com/v1` | `mimo-v2.5`, `mimo-v2.5-pro` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat`, `deepseek-reasoner` |

## 数据导入

### 手动 CSV 导入

从 IBKR Flex Query 导出 CSV 并导入：

```bash
cd ibkr_dash_worker
python -m worker.main import /path/to/your/flex_export.csv
```

### 自动导入

在 worker `.env` 中配置调度器：

```env
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=12
SCHEDULER_MINUTE=30
FLEX_TOKEN=your-token
FLEX_QUERY_ID_DAILY=your-query-id
```

## 故障排除

### 仪表盘没有数据

先导入数据：`python -m worker.main import worker/fixtures/daily_sample.csv`

### LLM 未配置

在 `ibkr_dash_backend/.env` 中设置 `LLM_API_KEY` 并重启后端。

### 登录不工作

检查 `ibkr_dash_backend/.env` 中是否设置了 `AUTH_PASSWORD`。
