import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import RepoCard from '../components/RepoCard.jsx'
import { compact } from '../utils.js'

export default function Home() {
  const [stats, setStats] = useState(null)
  const [models, setModels] = useState([])
  const [datasets, setDatasets] = useState([])
  const [q, setQ] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
    api.repos({ repo_type: 'model', sort: 'trending', limit: 6 }).then((r) => setModels(r.items))
    api.repos({ repo_type: 'dataset', sort: 'trending', limit: 4 }).then((r) => setDatasets(r.items))
  }, [])

  return (
    <div className="home">
      <section className="hero">
        <h1>
          The <span className="hi">local</span> home of machine learning
        </h1>
        <p>Catalog your models and datasets. Files stay wherever they live — we keep the links.</p>
        <form
          className="hero-search"
          onSubmit={(e) => {
            e.preventDefault()
            navigate(`/search?q=${encodeURIComponent(q)}`)
          }}
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search models, datasets, tasks…"
          />
          <button type="submit">Search</button>
        </form>
        {stats && (
          <div className="hero-stats">
            <span>
              <strong>{compact(stats.models)}</strong> models
            </span>
            <span>
              <strong>{compact(stats.datasets)}</strong> datasets
            </span>
            <span>
              <strong>{compact(stats.users)}</strong> users
            </span>
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-head">
          <h2>🧠 Trending models</h2>
          <Link to="/models">Browse all →</Link>
        </div>
        <div className="grid">
          {models.map((r) => (
            <RepoCard key={r.id} repo={r} />
          ))}
          {!models.length && <p className="muted">No models yet.</p>}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>📊 Trending datasets</h2>
          <Link to="/datasets">Browse all →</Link>
        </div>
        <div className="grid">
          {datasets.map((r) => (
            <RepoCard key={r.id} repo={r} />
          ))}
          {!datasets.length && <p className="muted">No datasets yet.</p>}
        </div>
      </section>
    </div>
  )
}
