import { useNavigate, useLocation } from 'react-router-dom'

interface TabLink {
  path: string
  label: string
}

const adminTabs: TabLink[] = [
  { path: '/admin/llm', label: 'LLM Config' },
  { path: '/admin/ibkr', label: 'IBKR Data' },
  { path: '/admin/email', label: 'Email Config' },
  { path: '/admin/longbridge-mcp', label: 'Longbridge MCP' },
  { path: '/admin/system', label: 'System Status' },
  { path: '/admin/agent-monitoring', label: 'Agent Monitor' },
  { path: '/admin/prompts', label: 'Prompt Mgmt' },
  { path: '/admin/harness', label: 'Harness Console' },
]

export default function AdminTabs() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <nav className="admin-tabs">
      {adminTabs.map((tab) => (
        <button
          key={tab.path}
          className={`btn terminal-nav__button${location.pathname === tab.path ? ' is-active' : ''}`}
          onClick={() => navigate(tab.path)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  )
}
