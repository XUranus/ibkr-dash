# 架构

## 概述

IBKR Dash 是一个个人投资组合仪表盘，将 Interactive Brokers 账户数据与 AI 分析代理相结合。

## 模块

```
ibkr-dash/
├── ibkr_dash_backend/    # FastAPI 服务器 + AI 代理
├── ibkr_dash_worker/     # 数据 ETL（IBKR Flex CSV → SQLite）
├── ibkr_dash_frontend/   # React + TypeScript 仪表盘
├── docker/               # Dockerfile 和 nginx 配置
├── scripts/              # 实用脚本
└── docs/                 # 文档
```

## 数据流

```
IBKR Flex CSV → Worker（解析/转换） → SQLite ← Backend（API）← Frontend
                                                    ↓
                                              AI Agents（LLM）
```

## 存储

| 组件 | 存储 | 原因 |
|------|------|------|
| 财务数据 | SQLite | 单用户，最多约 30 万行，仅需结构化查询 |
| 代理输出 | SQLite | 同一数据库，无需单独存储 |
| 缓存 | 内存字典 | 单进程，基于 TTL 过期 |

## 代理架构

代理遵循通用模式：
1. **构建证据** — 从 SQLite 查询账户/持仓/交易数据
2. **调用 LLM** — 使用结构化输出合约
3. **验证** — Pydantic 模型验证
4. **修复** — 如果 JSON 格式错误，使用修复提示重试
5. **回退** — 如果仍然失败，生成安全默认值
6. **保存** — 持久化到 SQLite
