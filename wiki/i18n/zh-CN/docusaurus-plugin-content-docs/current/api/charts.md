---
sidebar_position: 4
title: 图表 API
---

# 图表 API

图表 API 提供用于可视化投资组合绩效的数据。包括权益曲线（投资组合价值随时间变化）和绩效日历（按月/季/年的盈亏）。

---

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/charts/equity-curve` | 投资组合权益曲线时间序列 |
| GET | `/api/charts/performance-calendar` | 按周期的盈亏日历 |

所有端点在 `AUTH_PASSWORD` 非空时需要身份验证。

---

## 权益曲线

返回投资组合的总权益价值随时间的变化。数据来源于每日账户快照，适用于折线图。

### 请求

```
GET /api/charts/equity-curve
```

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `start_date` | string | 最早 | 开始日期（`YYYY-MM-DD`） |
| `end_date` | string | 最新 | 结束日期（`YYYY-MM-DD`） |

### 示例

```bash
# 完整权益曲线
curl "http://localhost:8000/api/charts/equity-curve"

# 最近 30 天
curl "http://localhost:8000/api/charts/equity-curve?start_date=2024-01-01&end_date=2024-01-31"

# 年初至今
curl "http://localhost:8000/api/charts/equity-curve?start_date=2024-01-01"
```

### 响应

```json
{
  "items": [
    {
      "report_date": "2024-01-15",
      "total_equity": 250000.00,
      "total_pnl": 50000.00,
      "net_cost": 200000.00,
      "realized_pnl": 15000.00,
      "daily_mtm": 2500.00,
      "daily_twr": 1.01
    },
    {
      "report_date": "2024-01-16",
      "total_equity": 252500.00,
      "total_pnl": 52500.00,
      "net_cost": 200000.00,
      "realized_pnl": 15000.00,
      "daily_mtm": 2500.00,
      "daily_twr": 1.00
    }
  ]
}
```

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `report_date` | string | 快照日期 |
| `total_equity` | float | 投资组合总价值 |
| `total_pnl` | float | 总盈亏 |
| `net_cost` | float | 净成本基础 |
| `realized_pnl` | float | 累计已实现盈亏 |
| `daily_mtm` | float | 每日按市值计价变化 |
| `daily_twr` | float | 每日时间加权收益率（百分比） |

### 图表数据格式

权益曲线响应的结构可直接用于图表库：

```typescript
// ECharts 折线图示例
const res = await fetch('/api/charts/equity-curve');
const { items } = await res.json();

const option = {
  xAxis: {
    type: 'category',
    data: items.map(i => i.report_date),  // ["2024-01-15", "2024-01-16", ...]
  },
  yAxis: {
    type: 'value',
    name: '权益 ($)',
  },
  series: [{
    type: 'line',
    data: items.map(i => i.total_equity),  // [250000, 252500, ...]
    smooth: true,
  }],
};
```

:::tip
权益曲线非常适合在仪表盘上渲染折线图。Y 轴使用 `total_equity`，X 轴使用 `report_date`。
:::

---

## 绩效日历

返回按时间段（月、季或年）组织的盈亏数据。适用于构建热力图样式的日历视图。

### 请求

```
GET /api/charts/performance-calendar
```

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `view` | string | `month` | 周期粒度：`month`、`quarter` 或 `year` |
| `anchor` | string | 最新 | 将视图定位到此周期键（如月视图的 `2024-01`） |

### 各视图的锚点格式

| 视图 | 锚点格式 | 示例 |
|------|----------|------|
| `month` | `YYYY-MM` | `2024-01` |
| `quarter` | `YYYY-QN` | `2024-Q1` |
| `year` | `YYYY` | `2024` |

### 示例

```bash
# 月度绩效日历
curl "http://localhost:8000/api/charts/performance-calendar?view=month"

# 以 2024 年 Q1 为中心的季度视图
curl "http://localhost:8000/api/charts/performance-calendar?view=quarter&anchor=2024-Q1"

# 年度视图
curl "http://localhost:8000/api/charts/performance-calendar?view=year"
```

### 响应

```json
{
  "view": "month",
  "anchor": "2024-01",
  "latest_anchor": "2024-03",
  "earliest_anchor": "2023-01",
  "previous_anchor": "2023-12",
  "next_anchor": "2024-02",
  "items": [
    {
      "period_key": "2024-01",
      "label": "Jan 2024",
      "period_start": "2024-01-01",
      "period_end": "2024-01-31",
      "pnl": 5000.00,
      "twr": 2.05,
      "has_data": true
    },
    {
      "period_key": "2024-02",
      "label": "Feb 2024",
      "period_start": "2024-02-01",
      "period_end": "2024-02-29",
      "pnl": -1200.00,
      "twr": -0.47,
      "has_data": true
    }
  ],
  "summary": {
    "positive_periods": 8,
    "negative_periods": 4,
    "total_pnl": 25000.00,
    "periods_with_data": 12
  }
}
```

### 响应字段

**导航字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `view` | string | 当前周期粒度 |
| `anchor` | string | 当前中心周期 |
| `latest_anchor` | string | 有数据的最新周期 |
| `earliest_anchor` | string | 有数据的最早周期 |
| `previous_anchor` | string | 上一页锚点（用于分页） |
| `next_anchor` | string | 下一页锚点（用于分页） |

**items[] 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `period_key` | string | 周期的唯一键 |
| `label` | string | 人类可读的标签 |
| `period_start` | string | 周期开始日期 |
| `period_end` | string | 周期结束日期 |
| `pnl` | float | 该周期的盈亏 |
| `twr` | float | 该周期的时间加权收益率 |
| `has_data` | bool | 该周期是否有数据 |

**summary 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `positive_periods` | int | 盈利周期数 |
| `negative_periods` | int | 亏损周期数 |
| `total_pnl` | float | 所有周期的总盈亏 |
| `periods_with_data` | int | 有数据的周期数 |

### 日历热力图示例

```typescript
// 从日历响应构建热力图数据数组
const res = await fetch('/api/charts/performance-calendar?view=month');
const { items } = await res.json();

const heatmapData = items.map(item => ({
  date: item.period_key,       // "2024-01"
  value: item.pnl,             // 5000.00 或 -1200.00
  label: item.label,           // "Jan 2024"
}));

// 颜色映射：正值为绿色，负值为红色
const getColor = (pnl: number) => pnl >= 0 ? '#22c55e' : '#ef4444';
```

:::tip
使用 `previous_anchor` 和 `next_anchor` 字段在日历视图中实现分页。将锚点值传回 API 即可在页面之间导航。
:::

---

## 错误处理

| 状态码 | 响应体 | 原因 |
|--------|--------|------|
| `401` | `{"detail":"Not authenticated"}` | 会话缺失或已过期 |
| `422` | `{"detail":"Invalid view: ..."}` | view 必须是 `month`、`quarter` 或 `year` |
| `500` | `{"detail":"Internal server error"}` | 服务器内部错误 |
