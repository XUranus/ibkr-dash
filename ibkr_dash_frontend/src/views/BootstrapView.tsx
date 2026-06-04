import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function BootstrapView() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    const trimmedUsername = username.trim()
    if (!trimmedUsername) { setError('Username cannot be empty'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    if (password !== confirmPassword) { setError('Passwords do not match'); return }

    setLoading(true)
    try {
      const response = await fetch('/api/bootstrap/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: trimmedUsername, password }),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || 'Initialization failed')
      }
      navigate('/admin/llm')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Initialization failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', padding: '2rem',
      background: 'var(--color-bg)',
    }}>
      <section style={{
        width: '100%', maxWidth: 400,
        background: 'linear-gradient(180deg, rgba(25, 50, 80, 0.95), rgba(16, 34, 57, 0.98))',
        borderRadius: 12, border: '1px solid var(--color-border)',
        boxShadow: '0 24px 80px rgba(0, 0, 0, 0.3)',
        padding: '2rem',
      }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <p className="eyebrow">WELCOME</p>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.25rem' }}>Welcome to IBKR Dashboard</h1>
          <p style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', margin: 0 }}>Create an admin account to get started</p>
        </div>

        <form style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }} onSubmit={handleSubmit}>
          <label className="field-stack">
            <span className="field-stack__label">Username</span>
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} type="text" autoComplete="username" />
          </label>
          <label className="field-stack">
            <span className="field-stack__label">Password</span>
            <input className="input" value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="new-password" placeholder="At least 8 characters" />
          </label>
          <label className="field-stack">
            <span className="field-stack__label">Confirm Password</span>
            <input className="input" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} type="password" autoComplete="new-password" />
          </label>
          {error && <p style={{ margin: 0, color: 'var(--color-negative)', fontSize: '0.85rem' }}>{error}</p>}
          <button type="submit" className="btn btn--accent" style={{ width: '100%', marginTop: '0.5rem' }} disabled={loading}>
            {loading ? 'Creating...' : 'Create and Enter System'}
          </button>
        </form>
      </section>
    </div>
  )
}
