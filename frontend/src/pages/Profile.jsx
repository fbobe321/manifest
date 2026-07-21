import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { useUser } from '../UserContext.jsx'
import RepoCard from '../components/RepoCard.jsx'

export default function Profile() {
  const { owner } = useParams()
  const { user } = useUser()
  const [profile, setProfile] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setProfile(null)
    setError('')
    api.user(owner).then(setProfile).catch((e) => setError(e.message))
  }, [owner])

  if (error) return <div className="empty">{error}</div>
  if (!profile) return <p className="muted">Loading…</p>

  const isSelf = user && user.username === profile.username
  const models = profile.repositories.filter((r) => r.repo_type === 'model')
  const datasets = profile.repositories.filter((r) => r.repo_type === 'dataset')

  return (
    <div className="profile">
      <div className="profile-head">
        <span className="profile-avatar">{profile.username[0].toUpperCase()}</span>
        <div>
          <h1>{profile.full_name || profile.username}</h1>
          <p className="muted">@{profile.username}</p>
          {profile.bio && <p className="bio">{profile.bio}</p>}
        </div>
        {isSelf && (
          <Link to="/new" className="btn-primary profile-new">
            + New repository
          </Link>
        )}
      </div>

      <Section title={`🧠 Models`} repos={models} />
      <Section title={`📊 Datasets`} repos={datasets} />

      {profile.repositories.length === 0 && (
        <div className="empty">
          {isSelf ? 'You have' : `${profile.username} has`} no repositories yet.
        </div>
      )}
    </div>
  )
}

function Section({ title, repos }) {
  if (!repos.length) return null
  return (
    <section className="section">
      <div className="section-head">
        <h2>
          {title} <span className="count">{repos.length}</span>
        </h2>
      </div>
      <div className="list">
        {repos.map((r) => (
          <RepoCard key={r.id} repo={r} />
        ))}
      </div>
    </section>
  )
}
