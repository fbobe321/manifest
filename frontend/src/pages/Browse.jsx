import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import RepoCard from '../components/RepoCard.jsx'
import FacetSidebar from '../components/FacetSidebar.jsx'

const SORTS = [
  ['trending', 'Trending'],
  ['recent', 'Recently updated'],
  ['downloads', 'Most downloads'],
  ['likes', 'Most likes'],
  ['created', 'Newly created'],
  ['name', 'Name (A–Z)'],
]

export default function Browse({ type }) {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') || ''

  const [facets, setFacets] = useState(null)
  const [filters, setFilters] = useState({ task: null, library: null, license: null, tag: null })
  const [sort, setSort] = useState('trending')
  const [data, setData] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(true)

  const title = type === 'model' ? 'Models' : type === 'dataset' ? 'Datasets' : 'Search'

  // Reset filters when switching between models/datasets/search.
  useEffect(() => {
    setFilters({ task: null, library: null, license: null, tag: null })
  }, [type])

  useEffect(() => {
    api.facets(type).then(setFacets).catch(() => setFacets(null))
  }, [type])

  useEffect(() => {
    setLoading(true)
    api
      .repos({ repo_type: type || undefined, q: q || undefined, sort, limit: 60, ...filters })
      .then((r) => setData(r))
      .catch(() => setData({ items: [], total: 0 }))
      .finally(() => setLoading(false))
  }, [type, q, sort, filters])

  function toggle(key, value) {
    setFilters((f) => ({ ...f, [key]: f[key] === value ? null : value }))
  }

  const activeFilters = Object.entries(filters).filter(([, v]) => v)

  return (
    <div className="browse">
      <FacetSidebar facets={facets} active={filters} onToggle={toggle} />

      <div className="browse-main">
        <div className="browse-head">
          <h1>
            {title}
            {q && <span className="muted"> · “{q}”</span>}
            <span className="count">{data.total}</span>
          </h1>
          <label className="sort">
            Sort:
            <select value={sort} onChange={(e) => setSort(e.target.value)}>
              {SORTS.map(([v, label]) => (
                <option key={v} value={v}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {(activeFilters.length > 0 || q) && (
          <div className="active-filters">
            {q && (
              <button className="chip" onClick={() => setParams({})}>
                “{q}” ✕
              </button>
            )}
            {activeFilters.map(([k, v]) => (
              <button key={k} className="chip" onClick={() => toggle(k, v)}>
                {k}: {v} ✕
              </button>
            ))}
          </div>
        )}

        {loading ? (
          <p className="muted">Loading…</p>
        ) : data.items.length ? (
          <div className="list">
            {data.items.map((r) => (
              <RepoCard key={r.id} repo={r} />
            ))}
          </div>
        ) : (
          <div className="empty">No repositories match these filters.</div>
        )}
      </div>
    </div>
  )
}
