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
          <span className="brand-logo">🤗</span>
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
