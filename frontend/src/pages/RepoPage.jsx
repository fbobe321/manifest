import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { useUser } from '../UserContext.jsx'
import Markdown from '../components/Markdown.jsx'
import { formatBytes, compact, timeAgo } from '../utils.js'

export default function RepoPage() {
  const { owner, name } = useParams()
  const { user } = useUser()
  const navigate = useNavigate()
  const [repo, setRepo] = useState(null)
  const [tab, setTab] = useState('card')
  const [error, setError] = useState('')

  const isOwner = user && repo && user.username === repo.owner_username

  function load() {
    api
      .repo(owner, name)
      .then(setRepo)
      .catch((e) => setError(e.message))
  }
  useEffect(load, [owner, name])

  async function like() {
    const updated = await api.like(owner, name)
    setRepo((r) => ({ ...r, likes: updated.likes }))
  }

  async function remove() {
    if (!confirm(`Delete ${owner}/${name}? This cannot be undone.`)) return
    await api.deleteRepo(owner, name)
    navigate(`/${owner}`)
  }

  if (error) return <div className="empty">{error}</div>
  if (!repo) return <p className="muted">Loading…</p>

  const icon = repo.repo_type === 'dataset' ? '📊' : '🧠'

  return (
    <div className="repo-page">
      <div className="repo-header">
        <div className="repo-title">
          <span className="repo-icon-lg">{icon}</span>
          <h1>
            <Link to={`/${owner}`} className="owner-link">
              {owner}
            </Link>
            <span className="repo-slash">/</span>
            <span className="repo-name">{name}</span>
          </h1>
          <span className={`type-badge type-${repo.repo_type}`}>{repo.repo_type}</span>
        </div>

        <div className="repo-actions">
          <button className="like-btn" onClick={like}>
            ❤ Like <span className="like-count">{compact(repo.likes)}</span>
          </button>
          {isOwner && (
            <>
              <Link className="btn-ghost" to={`/${owner}/${name}/edit`}>
                Edit
              </Link>
              <button className="btn-danger" onClick={remove}>
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      {repo.description && <p className="repo-tagline">{repo.description}</p>}

      <div className="repo-badges">
        {repo.task && <span className="pill pill-task">{repo.task}</span>}
        {repo.library && <span className="pill">{repo.library}</span>}
        {repo.license && <span className="pill">🔖 {repo.license}</span>}
        {repo.tags.map((t) => (
          <Link key={t} to={`/search?q=${encodeURIComponent(t)}`} className="pill pill-tag">
            {t}
          </Link>
        ))}
      </div>

      <div className="repo-substats">
        <span>⬇ {compact(repo.downloads)} downloads</span>
        <span>❤ {compact(repo.likes)} likes</span>
        <span>💾 {formatBytes(repo.total_size_bytes)}</span>
        <span>📄 {repo.num_files} files</span>
        <span>🕑 updated {timeAgo(repo.updated_at)}</span>
      </div>

      <div className="tabs">
        <button className={tab === 'card' ? 'tab active' : 'tab'} onClick={() => setTab('card')}>
          {repo.repo_type === 'dataset' ? 'Dataset card' : 'Model card'}
        </button>
        <button className={tab === 'files' ? 'tab active' : 'tab'} onClick={() => setTab('files')}>
          Files and versions <span className="tab-count">{repo.num_files}</span>
        </button>
      </div>

      {tab === 'card' ? (
        <div className="card-body">
          <Markdown source={repo.readme} />
        </div>
      ) : (
        <FilesTab repo={repo} owner={owner} name={name} isOwner={isOwner} onChange={load} />
      )}
    </div>
  )
}

function FilesTab({ repo, owner, name, isOwner, onChange }) {
  async function download(file) {
    try {
      await api.registerDownload(owner, name)
    } catch {}
    window.open(file.url, '_blank', 'noopener,noreferrer')
  }

  async function del(file) {
    if (!confirm(`Remove ${file.filename}?`)) return
    await api.deleteFile(owner, name, file.id)
    onChange()
  }

  return (
    <div className="files">
      {isOwner && <AddFileForm owner={owner} name={name} onAdded={onChange} />}

      {repo.files.length === 0 ? (
        <p className="muted">No files listed yet.</p>
      ) : (
        <table className="files-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Size</th>
              <th>Location</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {repo.files.map((f) => (
              <tr key={f.id}>
                <td className="file-name">📄 {f.filename}</td>
                <td className="file-size">{f.size_bytes ? formatBytes(f.size_bytes) : '—'}</td>
                <td className="file-host">
                  <span className="host">{hostOf(f.url)}</span>
                </td>
                <td className="file-actions">
                  <button className="btn-download" onClick={() => download(f)}>
                    ⬇ Download
                  </button>
                  {isOwner && (
                    <button className="btn-x" title="Remove file" onClick={() => del(f)}>
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function AddFileForm({ owner, name, onAdded }) {
  const [filename, setFilename] = useState('')
  const [url, setUrl] = useState('')
  const [sizeMB, setSizeMB] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.addFile(owner, name, {
        filename: filename.trim(),
        url: url.trim(),
        size_bytes: sizeMB ? Math.round(parseFloat(sizeMB) * 1024 * 1024) : 0,
      })
      setFilename('')
      setUrl('')
      setSizeMB('')
      onAdded()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="add-file" onSubmit={submit}>
      <h4>Add a file</h4>
      <p className="muted">Link to where the file is actually hosted — the bytes stay there.</p>
      <div className="add-file-row">
        <input
          placeholder="filename (e.g. model.safetensors)"
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
          required
        />
        <input
          placeholder="https://host/path/to/file"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          type="url"
          required
        />
        <input
          placeholder="size MB"
          value={sizeMB}
          onChange={(e) => setSizeMB(e.target.value)}
          type="number"
          min="0"
          step="any"
          className="size-input"
        />
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy ? 'Adding…' : 'Add'}
        </button>
      </div>
      {error && <div className="form-error">{error}</div>}
    </form>
  )
}

function hostOf(url) {
  try {
    return new URL(url).host
  } catch {
    return 'external'
  }
}
