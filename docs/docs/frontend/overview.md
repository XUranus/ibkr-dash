---
sidebar_position: 1
title: Frontend Overview
description: Introduction to the React frontend architecture
---

# Frontend Overview

The IBKR Dashboard frontend is a single-page application built with **React 18**, **TypeScript**, and **Vite**. It provides a terminal-luxury themed interface for viewing portfolio data and interacting with AI agents.

## Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| React | 18.3 | UI framework |
| TypeScript | 5.5 | Type safety |
| Vite | 5.4 | Build tool and dev server |
| React Router | 6.23 | Client-side routing |
| react-i18next | 17.0 | Internationalization |
| ECharts | 5.5 | Charts and data visualization |
| react-markdown | 10.1 | Markdown rendering (Copilot) |
| Vitest | 4.1 | Unit testing |

## Application Architecture Diagram

```mermaid
graph TB
    subgraph Browser
        User["User"]
    end

    subgraph Frontend["React SPA (Vite)"]
        Router["React Router v6"]
        Views["Views (Lazy Loaded)"]
        Components["Reusable Components"]
        Hooks["Custom Hooks"]
        API["API Client Layer"]
        I18N["react-i18next"]
        Charts["ECharts"]
    end

    subgraph Backend["FastAPI Backend"]
        REST["REST API"]
        Auth["Auth Service"]
        Agents["AI Agents"]
    end

    subgraph Data["SQLite Database"]
        DB[(ibkr_dash.db)]
    end

    User -->|"interacts with"| Router
    Router -->|"renders"| Views
    Views -->|"compose"| Components
    Views -->|"use"| Hooks
    Components -->|"fetch data via"| API
    API -->|"HTTP + JWT"| REST
    REST -->|"reads/writes"| DB
    Agents -->|"reads"| DB
    Views -->|"translate text"| I18N
    Views -->|"render charts"| Charts
```

## Module Structure

The source code lives in `frontend/src/` and is organized by concern:

```
frontend/src/
├── api/              # API client functions (one file per domain)
│   ├── http.ts       # Shared Axios instance with JWT interceptor
│   ├── account.ts    # Account overview & snapshots
│   ├── positions.ts  # Position data
│   ├── trades.ts     # Trade records
│   ├── charts.ts     # Equity curve, calendar data
│   ├── auth.ts       # Login / logout
│   └── ...           # 18 more domain-specific files
├── auth/             # Authentication utilities (token storage, refresh)
├── components/       # Reusable UI components (StatCard, tables, charts, etc.)
│   ├── AppHeader.tsx
│   ├── StatCard.tsx
│   ├── PositionTable.tsx
│   ├── ErrorBoundary.tsx
│   └── ...
├── composables/      # Shared composition logic
├── hooks/            # Custom React hooks
│   ├── useAuth.ts         # Authentication state management
│   ├── useAccountOverview.ts  # Account metrics fetching
│   └── ...
├── i18n/             # Internationalization setup and locale files
│   ├── index.ts      # i18next initialization
│   └── locales/      # en.json, zh-CN.json
├── router/           # React Router configuration
│   └── index.tsx     # All route definitions with lazy loading
├── styles/           # CSS files
│   ├── theme.css     # Design tokens (CSS variables)
│   ├── base.css      # Base styles and component classes
│   └── primevue-overrides.css
├── test/             # Test utilities
├── types/            # TypeScript type definitions (one file per domain)
│   ├── account.ts    # AccountOverview, AccountSnapshot
│   ├── positions.ts  # PositionItem, PositionDetail
│   ├── common.ts     # PaginatedResponse, ApiResponse
│   └── ...
├── utils/            # Utility functions (format, metrics)
├── views/            # Page-level components (one per route)
│   ├── DashboardView.tsx
│   ├── PositionsView.tsx
│   ├── TradesView.tsx
│   ├── AccountCopilotView.tsx
│   ├── TradeDecisionAgentView.tsx
│   └── ...
├── App.tsx           # Root component (layout + header + outlet)
├── main.tsx          # Entry point (renders App, imports styles)
└── vite-env.d.ts     # Vite type declarations
```

## Component Hierarchy

```mermaid
graph TB
    Main["main.tsx"] --> App["App.tsx"]
    App --> AppHeader["AppHeader"]
    App --> ErrorBoundary["ErrorBoundary"]
    App --> Outlet["Route Outlet"]

    Outlet --> Dashboard["DashboardView"]
    Outlet --> Positions["PositionsView"]
    Outlet --> Trades["TradesView"]
    Outlet --> Copilot["AccountCopilotView"]
    Outlet --> Decision["TradeDecisionAgentView"]
    Outlet --> Review["TradeReviewAgentView"]
    Outlet --> Daily["DailyPositionReviewView"]
    Outlet --> Admin["Admin Views"]
    Outlet --> Bootstrap["BootstrapView"]
    Outlet --> Research["StockResearchView"]

    Dashboard --> StatCard["StatCard"]
    Dashboard --> EquityCurve["EquityCurveSimple"]
    Dashboard --> Calendar["PerformanceCalendar"]
    Dashboard --> Pie["PieDistributionCard"]

    Positions --> PosTable["PositionTable"]
    Positions --> Pie

    Trades --> TradeTable["TradeTable"]

    Copilot --> Markdown["react-markdown"]
    Copilot --> JsonBlock["JsonBlock"]
    Decision --> AgentPanel["AgentEvidencePanel"]
    Decision --> AgentGraph["AgentTaskGraph"]
```

## Key Dependencies

### UI and Routing

- **react-router-dom**: Client-side routing with `createBrowserRouter`. Supports lazy loading, nested routes, and protected routes.
- **react-markdown**: Renders Markdown in the Copilot chat interface. Supports GitHub Flavored Markdown via `remark-gfm`.

### Data Visualization

- **echarts**: Full-featured charting library used for equity curves, P&L calendars, pie charts, and performance visualizations. Charts are wrapped in React components that manage the ECharts instance lifecycle.

### Internationalization

- **i18next**: Core i18n framework
- **react-i18next**: React bindings for i18next
- **i18next-browser-languagedetector**: Auto-detects user language from localStorage and browser settings

### Testing

- **vitest**: Fast unit test runner compatible with Vite
- **@testing-library/react**: React testing utilities
- **@testing-library/jest-dom**: Custom Jest matchers for DOM assertions
- **jsdom**: DOM implementation for Node.js testing

## Build Configuration

The Vite config (`vite.config.ts`) sets up:

- React plugin for JSX transformation
- Path alias `@` pointing to `src/`
- Dev server with API proxy to the backend
- Production build with code splitting

### vite.config.ts

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          charts: ['echarts'],
        },
      },
    },
  },
})
```

### Development

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173` and proxies API requests to the backend.

### Production Build

```bash
npm run build
```

This produces optimized static files in `dist/` with:
- Code splitting by route (lazy-loaded views)
- CSS extraction and minification
- Asset hashing for cache busting

## API Layer

Each backend domain has a corresponding API client file in `src/api/`:

| File | Domain |
|---|---|
| `account.ts` | Account overview and snapshots |
| `positions.ts` | Position data |
| `trades.ts` | Trade records |
| `cashFlows.ts` | Cash flow records |
| `dividends.ts` | Dividend records |
| `charts.ts` | Chart data (equity curve, calendar) |
| `tradeDecision.ts` | Trade decision agent |
| `tradeReview.ts` | Trade review agent |
| `dailyPositionReview.ts` | Daily position review agent |
| `accountCopilot.ts` | Account copilot chat |
| `symbolAnalysis.ts` | Stock research |
| `auth.ts` | Authentication |
| `adminSystem.ts` | System status |
| `adminLlm.ts` | LLM configuration |
| `adminIbkr.ts` | IBKR settings |
| `adminEmail.ts` | Email configuration |
| `adminPrompts.ts` | Prompt management |
| `adminHarness.ts` | Eval harness |
| `adminLongbridgeMcp.ts` | Longbridge MCP settings |
| `agentTasks.ts` | Agent task history |

### HTTP Client

All API calls go through a shared HTTP client (`src/api/http.ts`) that handles authentication headers, error responses, and base URL configuration.

```typescript
// frontend/src/api/http.ts
import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token from localStorage
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors (redirect to login)
http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/'
    }
    return Promise.reject(error)
  },
)

export default http
```

### Example API Call

```typescript
// frontend/src/api/account.ts
import http from './http'
import type { AccountOverview } from '@/types/account'

export async function fetchAccountOverview(): Promise<AccountOverview> {
  const { data } = await http.get('/account/overview')
  return data
}
```

## Type Definitions

TypeScript types are defined in `src/types/`, one file per domain:

| File | Types |
|---|---|
| `account.ts` | AccountOverview, AccountSnapshot |
| `positions.ts` | PositionItem, PositionDetail |
| `trades.ts` | TradeRecord, TradeSummary |
| `cashFlows.ts` | CashFlowRecord, CashFlowSummary |
| `dividends.ts` | DividendRecord |
| `charts.ts` | EquityCurvePoint, CalendarData |
| `tradeDecision.ts` | TradeDecision, ScoreDetail |
| `tradeReview.ts` | TradeReview, MistakeTag |
| `dailyPositionReview.ts` | DailyReview, SymbolAnalysis |
| `accountCopilot.ts` | CopilotSession, CopilotMessage |
| `agentTasks.ts` | AgentTask, AgentTaskStatus |
| `common.ts` | PaginatedResponse, ApiResponse |
| `auth.ts` | AuthState, LoginCredentials |

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant View as DashboardView
    participant Hook as useAccountOverview
    participant API as api/account.ts
    participant HTTP as api/http.ts
    participant Backend as FastAPI Backend
    participant DB as SQLite

    User->>View: Navigate to /
    View->>Hook: useAccountOverview()
    Hook->>API: fetchAccountOverview()
    API->>HTTP: http.get('/account/overview')
    HTTP->>Backend: GET /api/account/overview (JWT)
    Backend->>DB: SELECT * FROM account_snapshots
    DB-->>Backend: Rows
    Backend-->>HTTP: JSON response
    HTTP-->>API: AxiosResponse
    API-->>Hook: AccountOverview
    Hook-->>View: { data, loading, error }
    View->>User: Render StatCards + Charts
```

## Design Philosophy

The frontend follows these principles:

- **Terminal luxury theme**: Dark obsidian base with amber/gold accents, monospace typography, Bloomberg Terminal-inspired layout
- **Responsive**: Works on desktop and tablet; gracefully degrades on mobile
- **Accessible**: Semantic HTML, keyboard navigation, color contrast
- **Performant**: Lazy-loaded routes, memoized computations, efficient re-renders
- **Type-safe**: Full TypeScript coverage with strict mode
