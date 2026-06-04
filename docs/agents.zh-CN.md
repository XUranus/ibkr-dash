# AI 代理 (AI Agents)

IBKR Dash 包含一套 AI 驱动的代理，自动分析你的投资组合数据并生成可操作的见解。

## 可用代理

### 每日持仓审查 (Daily Position Review)

在每个交易日结束时分析所有当前持仓。该代理：

- 审查每个持仓的盈亏、成本基础和市场表现
- 识别显著盈利或亏损的持仓
- 将当前价格与入场价格和近期趋势进行比较
- 生成包含关键观察的摘要报告
- 突出显示可能需要关注的持仓

**触发方式**：每日数据导入后自动触发，或通过 API 手动触发。

### 交易审查 (Trade Review)

分析单笔或成组交易。该代理：

- 评估交易入场和出场时机
- 将交易结果与市场走势进行比较
- 识别盈利和亏损交易的模式
- 提供交易执行质量的反馈

**触发方式**：通过 API 按需触发。

### 风险评估 (Risk Assessment)

评估投资组合层面的风险指标。该代理：

- 分析集中度风险（持仓规模相对于总权益）
- 审查行业和资产类别多元化
- 识别持仓之间的相关性风险
- 提供再平衡建议

**触发方式**：通过 API 按需触发。

## 架构

所有代理遵循一致的模式：

1. **任务创建**：在 `agent_tasks` 表中创建状态为 `pending` 的任务记录。
2. **数据收集**：代理查询 SQLite 数据库获取相关数据（快照、持仓、交易）。
3. **提示构建**：数据被格式化为结构化提示发送给 LLM。
4. **LLM 调用**：提示发送到配置的 LLM 提供商。
5. **结果存储**：LLM 响应被解析并存储在相应的表中（`daily_position_reviews`、`trade_reviews`、`risk_assessments`）。
6. **任务完成**：任务状态更新为 `completed`（出错时为 `failed`）。

## 任务状态生命周期

```
pending -> running -> completed
                   -> failed
         -> cancelled
```

- **pending**：任务已创建，等待处理。
- **running**：任务正在处理中。
- **completed**：任务成功完成并有结果。
- **failed**：任务遇到错误。
- **cancelled**：任务在完成前被取消。

## 配置

代理使用与账户助手相同的 LLM 配置：

```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_DEFAULT_MODEL=gpt-4o
```

用于从 worker 触发代理的内部令牌：

```env
DAILY_REVIEW_INTERNAL_TOKEN=your-internal-token
```

## API 端点

| 端点 | 方法 | 描述 |
|---|---|---|
| `/api/agent/tasks` | GET | 列出代理任务 |
| `/api/agent/tasks/{id}` | GET | 获取任务详情 |
| `/api/agent/daily-position-review` | GET | 列出每日审查 |
| `/api/agent/daily-position-review/{id}` | GET | 获取特定审查 |
| `/api/agent/daily-position-review/internal/latest/tasks` | POST | 触发最新审查 |
| `/api/agent/trade-reviews` | GET | 列出交易审查 |
| `/api/agent/risk-assessments` | GET | 列出风险评估 |

## 提示管理

代理提示是版本化的，存储在 `agent_prompts` 表中。这允许：

- 在不更改代码的情况下迭代提示质量
- A/B 测试不同的提示策略
- 回滚到以前的提示版本
- 激活/停用特定提示

## 扩展代理

要添加新代理：

1. 在 `agent_prompts` 表中创建新提示。
2. 实现一个收集所需数据的服务类。
3. 添加 API 路由来触发和查询代理。
4. 将结果存储在专用表中或复用现有表。
