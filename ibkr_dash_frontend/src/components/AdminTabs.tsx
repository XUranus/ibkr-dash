import { useTranslation } from 'react-i18next'
import { useNavigate, useLocation } from 'react-router-dom'

export default function AdminTabs() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()

  const adminTabs = [
    { path: '/admin/settings', label: t('admin.settings') },
    { path: '/admin/llm', label: t('admin.llm') },
    { path: '/admin/ibkr', label: t('admin.ibkr') },
    { path: '/admin/email', label: t('admin.email') },
    { path: '/admin/longbridge-mcp', label: t('admin.longbridge') },
    { path: '/admin/system', label: t('admin.system') },
    { path: '/admin/agent-monitoring', label: t('admin.monitoring') },
    { path: '/admin/prompts', label: t('admin.prompts') },
    { path: '/admin/harness', label: t('admin.harness') },
  ]

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
