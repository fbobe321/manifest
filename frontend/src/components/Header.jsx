import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useUser } from '../UserContext.jsx'

export default function Header() {
  const [q, setQ] = useState('')
  const [showSignIn, setShowSignIn] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const { user, signOut } = useUser()
  const navigate = useNavigate()

  function submit(e) {
    e.preventDefault()
    navigate(`/search?q=${encodeURIComponent(q)}`)
  }

  return (
    <header className="header">
      <div className="header-inner">
        <NavLink to="/" className="brand">
          <svg className="brand-logo" width="26" height="26" viewBox="0 0 32 32" aria-hidden="true">
            <rect x="2" y="2" width="28" height="28" rx="7" fill="url(#mfg)" />
            <g
              fill="none"
              stroke="#ffca4a"
              strokeWidth="2.1"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="16" cy="7.3" r="2.3" />
              <path d="M16 9.6 V25.6" />
              <path d="M11 12.7 H21" />
              <path d="M7 17.8 C7.4 22 11 25.6 16 25.6 C21 25.6 24.6 22 25 17.8" />
              <path d="M7 17.8 L5.3 19.9 M7 17.8 L9.7 18.5" />
              <path d="M25 17.8 L26.7 19.9 M25 17.8 L22.3 18.5" />
            </g>
            <defs>
              <linearGradient id="mfg" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#17395c" />
                <stop offset="1" stopColor="#0b2137" />
              </linearGradient>
            </defs>
          </svg>
          <span className="brand-name">Local&nbsp;AI&nbsp;Hub</span>
        </NavLink>

        <form className="search" onSubmit={submit}>
          <span className="search-icon">🔍</span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search models and datasets…"
            aria-label="Search"
          />
        </form>

        <nav className="nav">
          <NavLink to="/models" className={({ isActive }) => (isActive ? 'active' : '')}>
            Models
          </NavLink>
          <NavLink to="/datasets" className={({ isActive }) => (isActive ? 'active' : '')}>
            Datasets
          </NavLink>
          <NavLink to="/new" className="btn-new">
            + New
          </NavLink>

          {user ? (
            <div className="usermenu">
              <button className="avatar-btn" onClick={() => setMenuOpen((o) => !o)}>
                <span className="avatar">{user.username[0].toUpperCase()}</span>
              </button>
              {menuOpen && (
                <div className="menu" onMouseLeave={() => setMenuOpen(false)}>
                  <NavLink to={`/${user.username}`} onClick={() => setMenuOpen(false)}>
                    Your profile
                  </NavLink>
                  <NavLink to="/new" onClick={() => setMenuOpen(false)}>
                    New repository
                  </NavLink>
                  <button
                    onClick={() => {
                      signOut()
                      setMenuOpen(false)
                    }}
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button className="btn-signin" onClick={() => setShowSignIn(true)}>
              Sign in
            </button>
          )}
        </nav>
      </div>

      {showSignIn && <SignInModal onClose={() => setShowSignIn(false)} />}
    </header>
  )
}

function SignInModal({ onClose }) {
  const { signIn } = useUser()
  const [username, setUsername] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    if (!/^[A-Za-z0-9_.-]+$/.test(username)) {
      setError('Username may only contain letters, numbers, _ . -')
      return
    }
    setBusy(true)
    try {
      await signIn(username.trim(), fullName.trim())
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Sign in</h2>
        <p className="muted">
          No password needed — this is a local hub. Pick a username to publish under.
        </p>
        <form onSubmit={submit}>
          <label>
            Username
            <input
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. jane-doe"
            />
          </label>
          <label>
            Display name <span className="muted">(optional)</span>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Jane Doe"
            />
          </label>
          {error && <div className="form-error">{error}</div>}
          <div className="modal-actions">
            <button type="button" className="btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={busy || !username}>
              {busy ? 'Signing in…' : 'Continue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
