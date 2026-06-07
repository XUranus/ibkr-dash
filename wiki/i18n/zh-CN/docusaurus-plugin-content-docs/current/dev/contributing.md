---
sidebar_position: 1
title: 贡献指南
---

# 贡献指南

欢迎来到 IBKR Dash 项目！本指南涵盖代码风格、Git 工作流、Pull Request 流程和架构决策，帮助您高效地做出贡献。

---

## 项目架构

IBKR Dash 是一个包含三个模块的 monorepo：

```
ibkr-dash/
  ibkr_dash_backend/     # FastAPI REST API (Python)
  ibkr_dash_frontend/    # React SPA (TypeScript)
  ibkr_dash_worker/      # ETL 调度器 (Python)
  data/                  # SQLite 数据库 + Flex CSV 导出
  docker/                # Dockerfile + nginx 配置
  wiki/                  # Docusaurus 文档
```

### 后端 (`ibkr_dash_backend/`)

- **框架**：FastAPI + Pydantic v2 schemas
- **数据库**：SQLite（无 Redis、无 Elasticsearch）
- **结构**：路由 -> 服务 -> 数据库
- **AI 代理**：使用 LLM 函数调用的 ReAct 风格代理

关键目录：

```
app/
  api/routes/     # FastAPI 路由处理器
  schemas/        # Pydantic 请求/响应模型
  services/       # 业务逻辑层
  agents/         # AI 代理实现
  core/           # 配置、数据库、身份验证、日志
```

### 前端 (`ibkr_dash_frontend/`)

- **框架**：React 18 + TypeScript（严格模式）
- **构建工具**：Vite
- **图表**：ECharts
- **路由**：React Router v6
- **国际化**：i18next

关键目录：

```
src/
  api/            # HTTP 客户端函数
  components/     # 可复用 UI 组件
  views/          # 页面级组件
  hooks/          # 自定义 React hooks
  types/          # TypeScript 类型定义
  utils/          # 工具函数
```

### Worker (`ibkr_dash_worker/`)

- **用途**：从 IBKR Flex CSV 到 SQLite 的 ETL 管道
- **调度器**：APScheduler（基于 cron）
- **CLI**：基于 argparse 的命令

关键目录：

```
worker/
  clients/        # 外部服务客户端（Flex、SQLite、邮件）
  core/           # 配置、调度器、日志
  importers/      # 数据导入编排
  jobs/           # 定时任务定义
  parsers/        # CSV/XML 解析
  writers/        # 数据库写操作
```

---

## 代码风格

### Python（后端 + Worker）

- 所有函数签名和返回类型**必须有类型注解**。
- **仅限英文注释** -- 源代码中不得使用中文。
- **文档字符串**：公共函数和类使用 Google 风格文档字符串。
- **导入**：按 stdlib、第三方、本地分组（用空行分隔）。
- **命名**：函数/变量用 `snake_case`，类用 `PascalCase`，常量用 `UPPER_SNAKE`。

```python
# 正确
def get_positions(
    db: Database,
    symbol: str | None = None,
    page: int = 1,
) -> PositionListResponse:
    """返回分页的持仓列表。

    Args:
        db: 数据库实例。
        symbol: 可选的标的筛选。
        page: 页码（从 1 开始）。

    Returns:
        分页的持仓列表。
    """
    ...

# 错误 -- 缺少类型注解
def get_positions(db, symbol=None, page=1):
    ...
```

**导入排序示例：**

```python
# stdlib
import os
from datetime import datetime
from typing import Optional

# third-party
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# local
from app.core.database import Database
from app.core.config import get_settings
from app.schemas.positions import PositionListResponse
```

### TypeScript（前端）

- `tsconfig.json` 中启用**严格模式**。
- **仅限英文注释**。
- **命名**：函数/变量用 `camelCase`，组件/类型用 `PascalCase`，常量用 `UPPER_SNAKE`。
- **组件**：每个文件一个组件，使用具名导出。
- **类型**：在 `src/types/` 目录中定义。

```typescript
// 正确
interface Position {
  symbol: string;
  quantity: number;
  markPrice: number;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}

// 正确 -- React 组件使用具名导出
export function PositionCard({ position }: { position: Position }) {
  return (
    <div className="position-card">
      <span>{position.symbol}</span>
      <span>{formatCurrency(position.markPrice)}</span>
    </div>
  );
}
```

---

## Git 工作流

### 分支策略

```
main            # 稳定发布分支
  ├── feature/* # 新功能
  ├── fix/*     # Bug 修复
  └── docs/*    # 文档变更
```

### 分支命名

使用带前缀的描述性名称：

```
feature/add-dividend-charts
fix/position-sort-order
docs/update-api-reference
```

### 提交信息

遵循约定式提交：

```
feat: add dividend history API endpoint
fix: correct P&L calculation for options
docs: update deployment guide for Docker
refactor: extract position service from route handler
test: add unit tests for trade service
```

前缀：`feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`perf`。

### 典型工作流

```bash
# 1. 创建功能分支
git checkout main
git pull origin main
git checkout -b feature/my-feature

# 2. 修改并提交
git add .
git commit -m "feat: add my new feature"

# 3. 推送并创建 PR
git push origin feature/my-feature

# 4. 审核后通过 GitHub 合并
```

---

## Pull Request 流程

### 提交前

1. **运行测试** -- 确保所有测试通过。
2. **检查代码风格** -- 无 lint 错误。
3. **更新文档** -- 如果更改了 API，请更新相关文档。
4. **写清楚描述** -- 解释改了什么以及为什么。

### PR 模板

```markdown
## 改了什么

简要描述变更。

## 为什么

变更的动机。

## 如何测试

验证变更生效的步骤。

## 检查清单

- [ ] 测试通过
- [ ] 文档已更新
- [ ] 无破坏性变更（或已记录）
```

### 审核指南

- 保持 PR 小而专注（每个 PR 一个功能或修复）。
- 及时回复审核评论。
- 如果分支有很多小提交，合并时使用 squash。

---

## 架构决策

以下是塑造项目的关键设计选择：

### 1. SQLite 而非 Elasticsearch

IBKR Dash 是单用户应用。所有财务数据完全可以放在 SQLite 中，它无需任何设置，也没有外部依赖。WAL 模式为后端和 worker 共享同一数据库文件提供了足够的并发性。

### 2. 无 Redis

内存 TTL 缓存（带时间戳的 Python 字典）替代了 Redis 进行缓存。这消除了另一个外部依赖。缓存 TTL 默认为 24 小时（`CACHE_TTL_SECONDS=86400`）。

### 3. 无 LangGraph

AI 代理使用简单的 Python 函数配合 `asyncio.gather()` 实现并行，而非 LangGraph 的图编排。每个代理是一个独立函数，接收数据库和 LLM 服务，收集上下文，提示 LLM，并返回结构化输出。

### 4. React 而非 Vue

前端使用 React + TypeScript 重建，以获得更好的类型安全和生态系统支持。Vite 处理构建工具。

### 5. FastAPI 而非 Django

选择 FastAPI 是因为它的自动 OpenAPI 文档、Pydantic 集成和异步支持。API 足够简单，Django 的 ORM 和管理面板是不必要的。

---

## 添加新的 API 端点

以下是分步流程：

### 1. 定义 schema

在 `app/schemas/` 中创建或编辑文件：

```python
# app/schemas/my_feature.py
from pydantic import BaseModel

class MyFeatureResponse(BaseModel):
    id: str
    name: str
    value: float
```

### 2. 创建服务

在 `app/services/` 中添加业务逻辑：

```python
# app/services/my_feature_service.py
from app.core.database import Database
from app.schemas.my_feature import MyFeatureResponse

class MyFeatureService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_feature(self, feature_id: str) -> MyFeatureResponse:
        row = self.db.execute_one(
            "SELECT * FROM my_features WHERE id = ?", (feature_id,)
        )
        if not row:
            raise ValueError(f"Feature not found: {feature_id}")
        return MyFeatureResponse(**row)
```

### 3. 创建路由

在 `app/api/routes/` 中添加端点：

```python
# app/api/routes/my_feature.py
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.schemas.my_feature import MyFeatureResponse
from app.services.my_feature_service import MyFeatureService

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

@router.get("/{feature_id}", response_model=MyFeatureResponse)
def get_feature(
    feature_id: str,
    db: Database = Depends(get_db),
    _user: str | None = Depends(get_current_user),
) -> MyFeatureResponse:
    service = MyFeatureService(db)
    return service.get_feature(feature_id)
```

### 4. 注册路由

添加到 `app/main.py`：

```python
from app.api.routes.my_feature import router as my_feature_router
app.include_router(my_feature_router, prefix="/api")
```

### 5. 编写测试

在 `tests/` 中添加测试：

```python
# tests/test_my_feature_service.py
from app.core.database import Database
from app.services.my_feature_service import MyFeatureService

def test_get_feature():
    db = Database(":memory:")
    db.init_schema()
    # ... 插入测试数据并断言
```

---

## 获取帮助

- 查看 GitHub 上的现有 issues 和 PR。
- 阅读源代码 -- 注释很详细。
- 在项目的讨论论坛中提问。
