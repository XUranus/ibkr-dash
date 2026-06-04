# 账户助手 (Account Copilot)

账户助手是集成在 IBKR Dash 中的 AI 对话助手。它允许你用自然语言查询投资组合、交易和账户表现。

## 功能

- **自然语言查询**：提问如"本月总盈亏多少？"或"哪些持仓未实现亏损最大？"
- **上下文感知**：助手理解你的账户数据、持仓、交易和现金流。
- **会话记忆**：对话在会话内持久化，支持追问。
- **结构化响应**：返回基于数据的答案，并引用具体记录。

## 工作原理

1. 你在助手聊天面板输入问题。
2. 后端检索相关账户数据（快照、持仓、交易、现金流）。
3. 数据被格式化为上下文提示并发送到配置的 LLM。
4. LLM 基于你的实际投资组合数据生成回答。
5. 回答显示在聊天中，可选带数据引用。

## 配置

助手需要在后端配置 LLM 提供商：

```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_DEFAULT_MODEL=gpt-4o
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
```

任何兼容 OpenAI 的 API 端点都可以使用（OpenAI、Azure OpenAI、通过 Ollama 的本地模型等）。

## API 端点

| 端点 | 方法 | 描述 |
|---|---|---|
| `/api/copilot/sessions` | POST | 创建新的对话会话 |
| `/api/copilot/sessions/{id}/messages` | POST | 发送消息并获取回复 |
| `/api/copilot/sessions/{id}/messages` | GET | 获取对话历史 |
| `/api/copilot/sessions` | GET | 列出所有会话 |

## 数据隐私

- 所有数据保存在本地 SQLite 数据库中。
- 只有回答问题所需的上下文才会发送给 LLM 提供商。
- LLM 提供商不存储任何投资组合数据。
- 会话和消息存储在本地，可随时删除。

## 限制

- 助手只能访问已导入系统的数据。
- 复杂的分析查询可能需要多轮对话。
- 回答质量取决于配置的 LLM 模型。
- 实时市场数据不可用，除非单独配置。
