---
sidebar_position: 2
title: Docker 部署
---

# Docker 部署

IBKR Dash 提供 Docker Compose 配置，用于在容器中运行所有三个服务（后端、前端、Worker）。这是在本地不安装 Python 或 Node.js 的情况下运行完整技术栈的最简单方式。

---

## 架构

```mermaid
graph TB
    subgraph Host["宿主机"]
        P8080[":8080"]
        P8000[":8000"]
    end

    subgraph DockerNetwork["Docker 网络"]
        subgraph Frontend["前端容器 (Nginx)"]
            NGINX["nginx.conf"]
            STATIC["React SPA 静态文件"]
        end
        subgraph Backend["后端容器"]
            UVICORN["uvicorn + FastAPI"]
        end
        subgraph Worker["Worker 容器"]
            SCHEDULER["APScheduler"]
        end
        VOLUME[("backend-data 卷<br/>(SQLite DB + config.json)")]
    end

    P8080 --> NGINX
    P8000 --> UVICORN
    NGINX -->|"/api/* 代理"| UVICORN
    UVICORN --> VOLUME
    SCHEDULER --> VOLUME
    SCHEDULER -->|获取 Flex 报告| IBKR["IBKR Flex API"]

    style VOLUME fill:#f9f,stroke:#333
```

- **前端** -- Nginx 提供构建好的 React 应用，并将 `/api/*` 代理到后端。
- **后端** -- FastAPI 在端口 8000 上提供 REST API。
- **Worker** -- 运行 IBKR Flex 调度器，每日导入数据。
- **共享卷** -- `backend-data` 存储 SQLite 数据库和 `config.json`，后端和 Worker 共享。

---

## 快速开始

### 1. 构建并启动

```bash
docker compose up --build -d
```

### 2. 访问应用

| 服务 | URL |
|------|-----|
| 前端 | `http://localhost:8080` |
| 管理后台设置 | `http://localhost:8080/admin/settings` |
| 后端 API | `http://localhost:8080/api/health` |
| API 文档 | `http://localhost:8000/docs`（直接访问后端） |

### 3. 配置

打开 **http://localhost:8080/admin/settings**，设置 LLM API 密钥、Flex Token 等。更改立即生效。

---

## Docker Compose 服务

```yaml
# docker-compose.yml
services:
  backend:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    volumes:
      - backend-data:/app/backend/data
    environment:
      - SQLITE_PATH=/app/backend/data/ibkr_dash.db
      - APP_ENV=${APP_ENV:-docker}
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: docker/worker.Dockerfile
    volumes:
      - backend-data:/app/backend/data
    environment:
      - SQLITE_PATH=/app/backend/data/ibkr_dash.db
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: docker/frontend.Dockerfile
    ports:
      - "${FRONTEND_PORT:-8080}:80"
    depends_on:
      - backend

volumes:
  backend-data:
```

---

## Dockerfile

### 后端 (`docker/backend.Dockerfile`)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Worker (`docker/worker.Dockerfile`)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker/ .
CMD ["python", "-m", "worker.main", "run-scheduler"]
```

### 前端 (`docker/frontend.Dockerfile`)

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
```

---

## .dockerignore

项目根目录的 `.dockerignore` 文件排除了构建上下文中不需要的文件（node_modules、.venv、docs 等），将上下文从 ~196MB 减少到 ~5MB。

---

## Nginx 配置

前端使用 Nginx 提供 SPA 并代理 API 请求：

```nginx
# docker/nginx.conf
server {
    listen 80;
    server_name _;
    client_max_body_size 100m;

    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000/api/;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 卷

| 卷 | 用途 |
|----|------|
| `backend-data` | SQLite 数据库、config.json 和 Flex CSV 导出 |

该卷在后端和 Worker 之间共享，以便它们可以读写同一个数据库和配置。

备份数据库：

```bash
docker compose exec backend cp /app/backend/data/ibkr_dash.db /tmp/backup.db
docker compose cp backend:/tmp/backup.db ./backup.db
```

---

## 配置

所有配置通过管理后台设置页面（`http://localhost:8080/admin/settings`）管理。配置存储在 `data/config.json` 中，持久化在 Docker 卷内。

Docker 特定的环境变量覆盖：

| 变量 | Docker 默认值 | 说明 |
|------|---------------|------|
| `SQLITE_PATH` | `/app/backend/data/ibkr_dash.db` | 容器内的路径 |
| `APP_ENV` | `docker` | 环境名称 |
| `BACKEND_PORT` | `8000` | 后端的宿主机端口 |
| `FRONTEND_PORT` | `8080` | 前端的宿主机端口 |

---

## 常用命令

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# 重启单个服务
docker compose restart backend

# 停止所有服务
docker compose down

# 代码更改后重新构建
docker compose up --build -d

# 在 Worker 内运行一次性导入
docker compose exec worker python -m worker.main import /path/to/file.csv

# 在后端容器中打开 shell
docker compose exec backend bash
```

---

## 故障排除

### 容器持续重启

查看日志：`docker compose logs backend`。常见原因：
- 宿主机端口冲突（使用 `BACKEND_PORT` / `FRONTEND_PORT` 更改）
- 配置值无效

### 数据库未持久化

验证卷是否存在：`docker volume ls`。如果卷丢失，数据库会在每次重启时重置。

### 前端显示 502 Bad Gateway

后端容器可能尚未就绪。等待几秒后刷新。检查：`docker compose ps` 确认所有容器正在运行。

### Worker 未导入数据

查看 Worker 日志：`docker compose logs worker`。确保在管理后台设置 → IBKR Flex 中正确配置了 Flex Token 和 Query ID。
