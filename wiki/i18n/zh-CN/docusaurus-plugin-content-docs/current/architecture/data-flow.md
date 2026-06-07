---
sidebar_position: 4
title: 数据流
---

# 数据流

本文档追踪数据在 IBKR Dash 中的流转 -- 从 IBKR 的服务器到您的屏幕。每个主要流都用序列图说明，以便您了解每一步发生了什么。

---

## 概览

IBKR Dash 中有两个主要数据流：

1. **金融数据流** -- IBKR Flex API -> Worker -> SQLite -> 后端 -> 前端
2. **AI 代理流** -- 用户 -> 前端 -> 后端 -> LLM -> 响应

```mermaid
graph LR
    subgraph Flow1 ["金融数据流"]
        IBKR["IBKR Flex API"] --> Worker["Worker"]
        Worker --> SQLite["SQLite"]
        SQLite --> Backend["后端 API"]
        Backend --> Frontend["前端"]
        Frontend --> User["用户"]
    end

    subgraph Flow2 ["AI 代理流"]
        User2["用户"] --> FE["前端"]
        FE --> BE["后端"]
        BE --> LLM["LLM 提供商"]
        LLM --> BE
        BE --> FE
        FE --> User2
    end
```

---

## 金融数据流

这是将您的 IBKR 投资组合数据带入仪表盘的核心数据管道。

### 步骤 1：从 IBKR 提取数据

有两种方式从 IBKR 获取数据：

#### 选项 A：手动 Flex CSV 导出

您手动从 IBKR 的 Web 界面导出 CSV：

1. 登录 IBKR Account Management
2. 导航到 Reports > Flex Queries
3. 运行 Flex Query（每日快照）
4. 下载 CSV 文件
5. 放入 `data/flex_exports/`

#### 选项 B：自动 Flex Web Service 拉取

Worker 使用 IBKR 的 Flex Web Service API 自动拉取数据：

```mermaid
sequenceDiagram
    participant Scheduler as Worker 调度器
    participant FlexClient as Flex 客户端
    participant IBKR as IBKR Flex API
    participant Disk as 文件系统

    Scheduler->>Scheduler: Cron 触发（每日 12:30）
    Scheduler->>FlexClient: run_daily_incremental_job()
    FlexClient->>IBKR: SendRequest (query_id, token)
    IBKR-->>FlexClient: ReferenceCode

    loop 轮询直到就绪
        FlexClient->>IBKR: GetStatement (reference_code)
        IBKR-->>FlexClient: "未就绪" (code 1018/1019)
        FlexClient->>FlexClient: Sleep(poll_interval)
    end

    FlexClient->>IBKR: GetStatement (reference_code)
    IBKR-->>FlexClient: FlexQueryResponse (XML)
    FlexClient->>Disk: 保存报表文件
```

Flex 客户端 (`worker/clients/flex_client.py`) 处理：

- **发送**查询请求，包含您的令牌和查询 ID
- **轮询**直到报表就绪（IBKR 异步生成报表）
- **下载**最终报表（XML 或 CSV 格式）
- **重试**最多 60 次，间隔 10 秒

:::info
IBKR Flex 查询不是即时的。提交查询后，IBKR 需要 10-60 秒来生成报表。Worker 每 10 秒轮询一次，直到报表就绪。
:::

---

### 步骤 2：CSV 解析

IBKR Flex CSV 格式是一种带有记录类型标记的多段格式。解析器 (`worker/parsers/flex_csv_parser.py`) 读取每一行并分类：

```mermaid
flowchart TD
    Input["原始 CSV 文件"] --> ReadLine["读取行"]
    ReadLine --> CheckType{"记录类型？"}

    CheckType -->|"BOF"| ExtractMeta["提取文件元数据<br/>(AccountId, QueryName, Dates)"]
    CheckType -->|"BOA"| ExtractAccount["提取账户元数据<br/>(键值对)"]
    CheckType -->|"BOS"| StartSection["开始新段<br/>(ACCT, POST, TRNT 等)"]
    CheckType -->|"HEADER"| SetHeaders["设置当前段的<br/>列头"]
    CheckType -->|"DATA"| AddRow["添加数据行<br/>到当前段"]
    CheckType -->|"EOS"| EndSection["结束当前段"]
    CheckType -->|"EOF"| Done["解析完成"]

    ExtractMeta --> ReadLine
    ExtractAccount --> ReadLine
    StartSection --> ReadLine
    SetHeaders --> ReadLine
    AddRow --> ReadLine
    EndSection --> ReadLine

    Done --> Output["FlexStatement 对象"]
```

CSV 包含多个段：

| 段 | 描述 | 映射到 |
|----|------|--------|
| `ACCT` | 账户信息 | `account_snapshots` |
| `POST` | 持仓数据 | `position_snapshots` |
| `TRNT` | 交易记录 | `trade_records` |
| `CTRN` | 现金交易 | `cash_flows` |
| `FIFO` | FIFO 盈亏数据 | 合并到持仓 |
| `SECU` | 证券详情 | 合并到持仓 |
| `PPPO` | 价格数据 | `price_history` |

原始 CSV 结构示例：

```csv
BOF,DU123456,Daily_Snapshot,2024-01-01,2024-01-15
BOA,AccountId,DU123456,AccountType,Individual
BOS,ACCT
HEADER,AccountId,Currency,TotalEquity,Cash
DATA,DU123456,USD,150000.00,25000.00
EOS
BOS,POST
HEADER,Symbol,Quantity,MarkPrice,PositionValue
DATA,AAPL,100,185.50,18550.00
DATA,MSFT,50,375.00,18750.00
EOS
```

---

### 步骤 3：数据转换

转换器 (`worker/parsers/transformers.py`) 将解析的段转换为 SQLite 就绪的字典：

```mermaid
flowchart LR
    subgraph Input ["FlexStatement"]
        Sections["段<br/>(ACCT, POST, TRNT 等)"]
        Meta["元数据<br/>(账户 ID, 日期)"]
    end

    subgraph Transform ["转换逻辑"]
        AccountTF["账户转换器"]
        PositionTF["持仓转换器"]
        TradeTF["交易转换器"]
        CashFlowTF["现金流转换器"]
        PriceTF["价格转换器"]
    end

    subgraph Output ["TransformResult"]
        Accounts["account_documents[]"]
        Positions["position_documents[]"]
        Trades["trade_documents[]"]
        CashFlows["cash_flow_documents[]"]
        Prices["price_history_documents[]"]
    end

    Sections --> AccountTF
    Sections --> PositionTF
    Sections --> TradeTF
    Sections --> CashFlowTF
    Sections --> PriceTF
    Meta --> AccountTF

    AccountTF --> Accounts
    PositionTF --> Positions
    TradeTF --> Trades
    CashFlowTF --> CashFlows
    PriceTF --> Prices
```

关键转换步骤：

- **日期标准化** -- 将 IBKR 日期格式转换为 ISO 8601 (`YYYY-MM-DD`)
- **数字清理** -- 从数字字段中移除逗号、货币符号和空白
- **字段映射** -- 将 IBKR 列名映射到数据库列名
- **去重** -- 使用唯一约束防止重复记录

---

### 步骤 4：数据库写入

SQLite 写入器 (`worker/writers/sqlite_writer.py`) 执行批量 upsert：

```mermaid
sequenceDiagram
    participant Writer as SQLite 写入器
    participant DB as SQLite 数据库

    Writer->>DB: BEGIN TRANSACTION
    Writer->>DB: INSERT OR REPLACE INTO account_snapshots
    Writer->>DB: INSERT OR REPLACE INTO position_snapshots
    Writer->>DB: INSERT OR REPLACE INTO trade_records
    Writer->>DB: INSERT OR REPLACE INTO cash_flows
    Writer->>DB: INSERT OR REPLACE INTO price_history
    Writer->>DB: COMMIT

    DB-->>Writer: 每张表的写入计数
```

Upsert 模式 (`INSERT ... ON CONFLICT DO UPDATE`) 确保：

- 重新导入同一天的数据会更新现有记录而不是创建重复项
- 唯一约束 (`account_id + report_date + symbol`) 防止数据重复
- 每次导入都是幂等的（可安全多次运行）

:::tip
Worker 使用 SQLite 的 `PRAGMA journal_mode=WAL` 进行并发访问。这允许后端在 Worker 写入的同时继续提供读取请求。
:::

---

### 步骤 5：API 读取

当前端请求数据时，后端从 SQLite 读取：

```mermaid
sequenceDiagram
    participant Frontend as 前端
    participant Router as FastAPI 路由
    participant Service as 持仓服务
    participant DB as SQLite

    Frontend->>Router: GET /api/positions
    Router->>Service: get_positions(account_id, date)
    Service->>DB: SELECT * FROM position_snapshots<br/>WHERE account_id=? AND report_date=?
    DB-->>Service: 原始行
    Service->>Service: 转换为 Pydantic 模型
    Service-->>Router: List[PositionSnapshot]
    Router-->>Frontend: JSON 响应
```

---

### 步骤 6：前端显示

前端使用 React 组件和 ECharts 渲染数据：

```mermaid
flowchart TD
    API["API 响应 (JSON)"] --> Hook["useAccountOverview() Hook"]
    Hook --> State["React 状态"]
    State --> Components

    subgraph Components ["UI 组件"]
        StatCard["StatCard<br/>(总权益, 盈亏)"]
        PositionTable["PositionTable<br/>(所有持仓)"]
        EquityCurve["EquityCurveSimple<br/>(折线图)"]
        PieChart["PieDistributionCard<br/>(配置)"]
        Calendar["PerformanceCalendar<br/>(每日盈亏)"]
    end

    Components --> DOM["浏览器 DOM"]
```

---

## AI 代理数据流

AI 代理是 IBKR Dash 中最复杂的数据流。有两种不同的模式：

### 模式 1：结构化输出代理

使用者：每日持仓审查、交易决策、交易回顾、风险评估

这些代理遵循固定管道：收集数据 -> 调用 LLM -> 解析结构化 JSON -> 存储结果。

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant API as 后端 API
    participant Service as 代理服务
    participant Tools as IBKR 工具
    participant Runtime as ReAct 运行时
    participant LLM as LLM 提供商
    participant DB as SQLite

    User->>Frontend: 点击"生成审查"
    Frontend->>API: POST /api/daily-position-review/generate
    API->>Service: 创建代理任务
    API-->>Frontend: 任务 ID (202 Accepted)

    Service->>Tools: 收集投资组合数据
    Tools->>DB: 读取持仓、交易、现金流
    DB-->>Tools: 金融数据
    Tools-->>Service: 工具结果

    Service->>Runtime: 运行 ReAct 循环
    loop ReAct 轮次（最多 6 轮）
        Runtime->>LLM: 使用工具和上下文聊天
        LLM-->>Runtime: 工具调用或最终答案
        alt 请求工具调用
            Runtime->>Tools: 并行执行工具
            Tools-->>Runtime: 工具观察
        else 最终答案
            Runtime-->>Service: 结构化 JSON 输出
        end
    end

    Service->>Service: 解析 + 验证 JSON
    Service->>DB: 存储审查结果
    Service->>DB: 更新代理任务状态

    Frontend->>API: GET /api/agent-tasks/{id}
    API->>DB: 读取任务结果
    DB-->>API: 结果 JSON
    API-->>Frontend: 带结果的任务
    Frontend-->>User: 显示审查
```

---

### 模式 2：Copilot（对话代理）

使用者：账户 Copilot

Copilot 是一个具有记忆、技能和工具调度的对话代理：

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant API as 后端 API
    participant Copilot as Copilot 运行时
    participant Planner as LLM 规划器
    participant Tools as IBKR 工具
    participant Skills as 技能注册表
    participant DB as SQLite

    User->>Frontend: "我的 AAPL 持仓值多少钱？"
    Frontend->>API: POST /api/copilot/chat<br/>{session_id, message}
    API->>Copilot: 运行 copilot(state)

    loop ReAct 轮次（最多 8 轮）
        Copilot->>Planner: 规划下一步行动
        Note over Planner: 使用结构化输出<br/>决定：tool_call,<br/>skill_request 或 final_answer
        Planner-->>Copilot: PlannerAction

        alt action_type = "tool_call"
            Copilot->>Tools: 执行工具(name, args)
            Tools->>DB: 查询投资组合数据
            DB-->>Tools: 数据
            Tools-->>Copilot: 观察
        else action_type = "request_skill_approval"
            Copilot-->>Frontend: "应该运行 X 吗？"
            Frontend-->>User: 审批提示
            User->>Frontend: 批准
            Frontend->>API: 批准技能
            Copilot->>Skills: 执行技能
        else action_type = "final_answer"
            Copilot-->>API: 最终答案文本
        end
    end

    API->>DB: 存储消息 + 记忆
    API-->>Frontend: Copilot 响应
    Frontend-->>User: 显示答案
```

---

## 结构化输出管道

所有 AI 代理使用结构化输出管道确保从 LLM 获得可靠的 JSON 输出。这很重要，因为 LLM 可能产生格式错误的 JSON。

```mermaid
flowchart TD
    LLM["LLM 响应<br/>(原始文本)"] --> Parse["步骤 1: 提取 JSON<br/>extract_json_object()"]
    Parse -->|成功| Validate["步骤 2: 验证<br/>Pydantic model_validate()"]
    Parse -->|失败| Repair

    Validate -->|成功| Result["StructuredOutputResult<br/>(ok=True)"]
    Validate -->|失败| Repair["步骤 3: 修复<br/>发送给 LLM 并附带错误"]

    Repair --> RepairLLM["LLM 修复调用<br/>(temperature=0)"]
    RepairLLM --> Parse2["再次解析 + 验证"]
    Parse2 -->|成功| Result
    Parse2 -->|失败| Fallback["步骤 4: 回退<br/>使用默认值"]

    Fallback --> Result

    Result --> Store["存储到 SQLite"]
```

管道有四个阶段：

1. **解析** -- 从原始 LLM 文本中提取 JSON 对象（处理 markdown 代码块、额外文本等）
2. **验证** -- 根据 Pydantic 模型模式验证 JSON
3. **修复** -- 如果验证失败，将原始输出和错误消息发回 LLM 要求修复格式
4. **回退** -- 如果修复失败，使用默认/回退值

:::info
结构化输出管道定义在 `app/agents/structured_output/` 中。每个代理定义一个 `StructuredOutputContract`，指定预期模式、修复行为和回退逻辑。
:::

---

## Copilot 工具系统

账户 Copilot 可以访问一个只读工具注册表来查询数据库：

```mermaid
graph TD
    subgraph Tools ["Copilot 工具"]
        T1["get_account_overview"]
        T2["get_positions"]
        T3["get_trades"]
        T4["get_cash_flows"]
        T5["get_dividends"]
        T6["get_price_history"]
        T7["get_daily_pnl"]
        T8["search_symbol"]
    end

    subgraph Skills ["Copilot 技能"]
        S1["daily_position_review"]
        S2["trade_decision"]
        S3["trade_review"]
        S4["risk_assessment"]
    end

    Copilot["Copilot 运行时"] --> Tools
    Copilot --> Skills
    Tools --> DB["SQLite 数据库"]
    Skills --> AgentRuntime["代理运行时"]
    AgentRuntime --> LLM["LLM 提供商"]
    AgentRuntime --> DB
```

**工具**是只读数据库查询。Copilot 可以自由调用它们来收集数据。

**技能**是更复杂的操作，触发完整的代理运行。它们在执行前需要用户批准，可能多次调用 LLM。

---

## 代理任务生命周期

每次代理执行都会创建一个跟踪其进度的任务记录：

```mermaid
stateDiagram-v2
    [*] --> pending: 任务创建
    pending --> running: 代理开始
    running --> completed: 代理完成
    running --> failed: 发生错误
    running --> cancelled: 用户取消

    completed --> [*]
    failed --> [*]
    cancelled --> [*]
```

任务记录存储：

- **进度** -- 执行期间的 JSON 更新
- **结果** -- 最终输出（审查、决策等）
- **错误** -- 失败时的错误消息
- **计时** -- 创建、开始和完成时间戳
- **运行追踪** -- 完整的执行追踪用于调试

```mermaid
sequenceDiagram
    participant Frontend as 前端
    participant API as API
    participant DB as SQLite

    Note over Frontend,API: 步骤 1: 创建任务
    Frontend->>API: POST /api/daily-position-review/generate
    API->>DB: INSERT INTO agent_tasks (status=pending)
    API-->>Frontend: {task_id: "abc123"}

    Note over Frontend,API: 步骤 2: 轮询结果
    loop 每 2 秒
        Frontend->>API: GET /api/agent-tasks/abc123
        API->>DB: SELECT * FROM agent_tasks WHERE id='abc123'
        DB-->>API: {status: "running", progress: {...}}
        API-->>Frontend: 任务仍在运行
    end

    Note over Frontend,API: 步骤 3: 获取最终结果
    Frontend->>API: GET /api/agent-tasks/abc123
    API->>DB: SELECT * FROM agent_tasks WHERE id='abc123'
    DB-->>API: {status: "completed", result: {...}}
    API-->>Frontend: 最终结果
    Frontend-->>User: 显示审查
```

---

## Copilot 记忆流

Copilot 在对话中维护记忆：

```mermaid
flowchart TD
    UserMsg["用户消息"] --> Planner["规划器 LLM 调用"]

    subgraph Memory ["记忆系统"]
        Rolling["滚动摘要<br/>(浓缩历史)"]
        Pinned["固定事实<br/>(关键洞察)"]
        Session["会话消息<br/>(完整对话)"]
    end

    Memory --> Planner
    Planner --> Action{"操作类型？"}

    Action -->|"tool_call"| Tool["执行工具"]
    Tool --> Observation["观察"]
    Observation --> Planner

    Action -->|"final_answer"| Answer["最终答案"]
    Answer --> UpdateMemory["更新记忆"]
    UpdateMemory --> Rolling
    UpdateMemory --> Pinned
```

记忆类型：

- **滚动摘要** -- 对话历史的浓缩版本，每次交流后更新
- **固定事实** -- 从对话中提取的关键事实（例如"用户对科技股感兴趣"）
- **会话消息** -- 当前会话的完整消息历史

---

## 数据新鲜度

了解数据何时更新有助于您理解仪表盘：

```mermaid
gantt
    title 每日数据时间线
    dateFormat HH:mm
    axisFormat %H:%M

    section Worker
    Flex 查询提交   :done, 12:30, 1m
    轮询报表        :done, 12:31, 5m
    解析 + 转换     :done, 12:36, 1m
    写入 SQLite     :done, 12:37, 1m

    section 后端
    提供 API 请求   :active, 00:00, 24h

    section 前端
    页面加载时获取   :crit, 12:38, 1m
```

- **金融数据**每天更新一次（当 Worker 运行时）
- **API 响应**是从 SQLite 的实时读取（默认无缓存，但可配置 `CACHE_TTL_SECONDS`）
- **AI 代理输出**按需生成并永久存储

:::warning
仪表盘显示最新的快照日期。如果 Worker 今天没有运行，您将看到昨天的数据。检查仪表盘头部的报告日期以确认数据新鲜度。
:::

---

## 错误处理

每一层都有自己的错误处理策略：

```mermaid
flowchart TD
    subgraph Worker ["Worker 错误"]
        W1["Flex API 超时"] --> W1R["重试最多 60 次"]
        W2["无效 CSV 格式"] --> W2R["记录错误，跳过文件"]
        W3["SQLite 写入失败"] --> W3R["回滚事务"]
    end

    subgraph Backend ["后端错误"]
        B1["LLM 超时"] --> B1R["抛出 LLMClientError"]
        B2["LLM 返回无效 JSON"] --> B2R["结构化输出修复"]
        B3["工具执行失败"] --> B3R["返回错误观察"]
        B4["超过最大轮次"] --> B4R["强制最终合成"]
    end

    subgraph Frontend ["前端错误"]
        F1["API 请求失败"] --> F1R["ErrorBoundary 捕获"]
        F2["无效响应"] --> F2R["ErrorBlock 组件"]
        F3["网络错误"] --> F3R["重试 + 错误消息"]
    end
```

---

## 总结

| 流 | 方向 | 协议 | 频率 |
|----|------|------|------|
| IBKR -> Worker | 拉取 | Flex Web Service API | 每日（定时） |
| Worker -> SQLite | 写入 | 直接 SQL (upsert) | 导入时 |
| SQLite -> 后端 | 读取 | 直接 SQL 查询 | API 请求时 |
| 后端 -> 前端 | 提供 | HTTP REST (JSON) | 页面加载时 |
| 前端 -> 用户 | 显示 | 浏览器 DOM | 实时 |
| 用户 -> Copilot | 聊天 | HTTP REST (JSON) | 按需 |
| Copilot -> LLM | 查询 | HTTP (chat/completions) | 每个代理轮次 |
| LLM -> Copilot | 响应 | HTTP (JSON) | 每个代理轮次 |
| Copilot -> SQLite | 存储 | 直接 SQL | 完成后 |
