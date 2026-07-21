import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { useUser } from '../UserContext.jsx'

const LICENSES = [
  '', 'apache-2.0', 'mit', 'cc-by-4.0', 'cc-by-sa-4.0', 'cc-by-nc-4.0', 'openrail',
  'openrail++', 'llama3.1', 'gpl-3.0', 'bsd-3-clause', 'other',
]

const TEMPLATE = `# {name}

## Model description

Describe what this is, how it was trained, and what it is good at.

## Intended uses & limitations

...

## How to use

\`\`\`python
# example code
\`\`\`
`

export default function RepoForm({ mode }) {
  const { user } = useUser()
  const { owner, name: routeName } = useParams()
  const navigate = useNavigate()
  const isEdit = mode === 'edit'

  const [form, setForm] = useState({
    repo_type: 'model',
    name: '',
    description: '',
    license: '',
    task: '',
    library: '',
    tags: '',
    readme: '',
  })
  const [loaded, setLoaded] = useState(!isEdit)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!isEdit) return
    api
      .repo(owner, routeName)
      .then((r) =>
        setForm({
          repo_type: r.repo_type,
          name: r.name,
          description: r.description || '',
          license: r.license || '',
          task: r.task || '',
          library: r.library || '',
          tags: r.tags.join(', '),
          readme: r.readme || '',
        }),
      )
      .then(() => setLoaded(true))
      .catch((e) => setError(e.message))
  }, [isEdit, owner, routeName])

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  if (!user) {
    return (
      <div className="empty">
        You need to sign in first to {isEdit ? 'edit' : 'create'} a repository.
      </div>
    )
  }
  if (isEdit && user.username !== owner) {
    return <div className="empty">Only {owner} can edit this repository.</div>
  }
  if (!loaded) return <p className="muted">Loading…</p>

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    const tags = form.tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)
    try {
      if (isEdit) {
        await api.updateRepo(owner, routeName, {
          description: form.description,
          readme: form.readme,
          license: form.license || null,
          task: form.task || null,
          library: form.library || null,
          tags,
        })
        navigate(`/${owner}/${routeName}`)
      } else {
        const repo = await api.createRepo({
          owner: user.username,
          name: form.name.trim(),
          repo_type: form.repo_type,
          description: form.description,
          readme: form.readme || TEMPLATE.replace('{name}', form.name.trim()),
          license: form.license || null,
          task: form.task || null,
          library: form.library || null,
          tags,
        })
        navigate(`/${repo.owner_username}/${repo.name}`)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="repo-form-wrap">
      <h1>{isEdit ? `Edit ${owner}/${routeName}` : 'Create a new repository'}</h1>

      <form className="repo-form" onSubmit={submit}>
        {!isEdit && (
          <>
            <div className="type-toggle">
              {['model', 'dataset'].map((t) => (
                <button
                  key={t}
                  type="button"
                  className={form.repo_type === t ? 'active' : ''}
                  onClick={() => set('repo_type', t)}
                >
                  {t === 'model' ? '🧠 Model' : '📊 Dataset'}
                </button>
              ))}
            </div>

            <label>
              Repository name
              <div className="name-row">
                <span className="owner-prefix">{user.username} /</span>
                <input
                  value={form.name}
                  onChange={(e) => set('name', e.target.value)}
                  placeholder="my-awesome-model"
                  pattern="[A-Za-z0-9_.\-]+"
                  required
                />
              </div>
            </label>
          </>
        )}

        <label>
          Short description
          <input
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            placeholder="One line describing this repository"
            maxLength={280}
          />
        </label>

        <div className="form-grid">
          <label>
            {form.repo_type === 'dataset' ? 'Task category' : 'Pipeline task'}
            <input
              value={form.task}
              onChange={(e) => set('task', e.target.value)}
              placeholder="e.g. text-generation"
            />
          </label>
          <label>
            Library
            <input
              value={form.library}
              onChange={(e) => set('library', e.target.value)}
              placeholder="e.g. transformers"
            />
          </label>
          <label>
            License
            <select value={form.license} onChange={(e) => set('license', e.target.value)}>
              {LICENSES.map((l) => (
                <option key={l} value={l}>
                  {l || '—'}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label>
          Tags <span className="muted">(comma-separated)</span>
          <input
            value={form.tags}
            onChange={(e) => set('tags', e.target.value)}
            placeholder="text-generation, chat, english"
          />
        </label>

        <label>
          {form.repo_type === 'dataset' ? 'Dataset card' : 'Model card'}{' '}
          <span className="muted">(Markdown)</span>
          <textarea
            className="readme-input"
            value={form.readme}
            onChange={(e) => set('readme', e.target.value)}
            rows={16}
            placeholder="Leave blank to start from a template"
          />
        </label>

        {error && <div className="form-error">{error}</div>}

        <div className="form-actions">
          <button type="button" className="btn-ghost" onClick={() => navigate(-1)}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? 'Saving…' : isEdit ? 'Save changes' : 'Create repository'}
          </button>
        </div>
      </form>
    </div>
  )
}
