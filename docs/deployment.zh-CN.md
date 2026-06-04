# 部署指南

本指南介绍如何使用 Docker 部署 IBKR Dash 或直接在服务器上运行。

## Docker 快速开始

推荐使用 Docker Compose 部署 IBKR Dash。

### 前提条件

- Docker Engine 20.10+
- Docker Compose v2+
- IBKR Flex 查询令牌（用于数据导入）
- （可选）兼容 OpenAI 的 API 密钥（用于 AI 功能）

### 步骤

1. **克隆仓库**：

   ```bash
   git clone https://github.com/your-org/ibkr-dash.git
   cd ibkr-dash
   ```

2. **创建环境文件**：

   ```bash
   cp ibkr_dash_worker/.env.example .env
   ```

   编辑 `.env` 并填入你的值：

   ```env
   # 数据导入必需
   FLEX_TOKEN=your-ibkr-flex-token
   FLEX_QUERY_ID_DAILY=your-query-id

   # AI 功能必需（可选）
   LLM_API_KEY=your-openai-api-key

   # 认证
   AUTH_PASSWORD=your-secure-password

   # worker 与后端通信的内部令牌
   DAILY_REVIEW_INTERNAL_TOKEN=a-random-secret-string
   ```

3. **构建并启动**：

   ```bash
   docker compose up -d --build
   ```

4. **验证**：

   ```bash
   curl http://localhost:8080/health
   ```

5. **访问仪表盘**：在浏览器中打开 `http://localhost:8080`。

### Docker 架构

```
                    +------------------+
                    |   nginx (前端)    |
                    |   端口 8080      |
                    +--------+---------+
                             |
                    +--------+---------+
                    |   后端           |
                    |   端口 8000      |
                    |   (FastAPI)      |
                    +--------+---------+
                             |
                    +--------+---------+
                    |   SQLite         |
                    |   (数据卷)       |
                    +------------------+
```

- **frontend**：由 nginx 提供的 React SPA，将 `/api/` 代理到后端。
- **backend**：使用 SQLite 存储的 FastAPI 应用。
- **worker-init**：运行初始数据导入的一次性容器。

### 数据卷

SQLite 数据库存储在 Docker 卷中。要在容器重建时持久化数据：

```yaml
volumes:
  ibkr-data:
    driver: local
```

### 反向代理配置

如果在反向代理（nginx、Caddy 等）后面部署，请确保：

- 支持 WebSocket（如果适用）
- 足够的 `client_max_body_size`（建议 100MB，用于大型导入）
- 正确的 `X-Forwarded-For` 和 `X-Forwarded-Proto` 头
- 健康检查端点 `/health`

## 手动部署

### 前提条件

- Python 3.11+
- Node.js 18+（用于前端构建）
- SQLite 3.35+

### 后端

```bash
cd ibkr_dash_backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Worker

```bash
cd ibkr_dash_worker
pip install -r requirements.txt
# 运行一次性导入
python -m worker.cli import-latest
# 运行调度器
python -m worker.cli scheduler
```

### 前端

```bash
cd ibkr_dash_frontend
npm install
npm run build
# 使用任何静态文件服务器提供 dist/ 目录
```

## 环境变量

### 后端

| 变量 | 默认值 | 描述 |
|---|---|---|
| `APP_ENV` | `development` | 环境名称 |
| `SQLITE_PATH` | `data/ibkr_dash.db` | SQLite 数据库路径 |
| `AUTH_USERNAME` | `admin` | 登录用户名 |
| `AUTH_PASSWORD` | （空） | 登录密码 |
| `AUTH_SESSION_SECRET` | （随机） | 会话签名密钥 |
| `LLM_API_KEY` | （空） | 兼容 OpenAI 的 API 密钥 |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM 端点 |
| `LLM_DEFAULT_MODEL` | `gpt-4o` | 默认模型 |
| `CORS_ORIGINS` | `http://localhost:5173` | 允许的 CORS 来源 |

### Worker

| 变量 | 默认值 | 描述 |
|---|---|---|
| `FLEX_TOKEN` | （空） | IBKR Flex Web Service 令牌 |
| `FLEX_QUERY_ID_DAILY` | （空） | 每日快照查询 ID |
| `FLEX_BASE_URL` | IBKR Flex URL | Flex API 基础 URL |
| `SCHEDULER_ENABLED` | `true` | 启用自动调度 |
| `SCHEDULER_HOUR` | `12` | 每日导入的小时 |
| `SCHEDULER_MINUTE` | `30` | 每日导入的分钟 |
| `SCHEDULER_TIMEZONE` | `Asia/Shanghai` | 调度时区 |
| `BACKEND_BASE_URL` | `http://localhost:8000` | 后端 API URL |

## 备份

可以通过复制数据库文件来备份 SQLite 数据库：

```bash
# 先停止后端以确保一致性
cp data/ibkr_dash.db data/ibkr_dash_backup_$(date +%Y%m%d).db
```

对于实时备份，使用 SQLite 的备份 API：

```bash
sqlite3 data/ibkr_dash.db ".backup 'data/backup.db'"
```

## 监控

健康检查端点：`GET /api/health`

返回包含服务状态的 JSON：

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

## 故障排除

### Worker 无法连接到 IBKR

- 验证 `FLEX_TOKEN` 设置正确
- 检查 `FLEX_QUERY_ID_DAILY` 是否匹配你的 IBKR Flex 查询配置
- 确保服务器可以访问 `interactivebrokers.com`

### 前端没有显示数据

- 检查 worker 是否至少运行过一次导入
- 验证后端正在运行且可访问
- 检查浏览器控制台的 API 错误

### AI 功能不工作

- 验证 `LLM_API_KEY` 已设置
- 检查 `LLM_BASE_URL` 是否可达
- 查看后端日志中的 LLM 提供商错误
