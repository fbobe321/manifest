const BASE = '/api'

async function req(path, opts) {
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail || detail
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

function jsonBody(method, body) {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

const enc = encodeURIComponent

export const api = {
  stats: () => req('/stats'),
  facets: (type) => req(`/facets${type ? `?repo_type=${type}` : ''}`),

  // Users
  createUser: (body) => req('/users', jsonBody('POST', body)),
  user: (username) => req(`/users/${enc(username)}`),

  // Repositories
  repos: (params = {}) => {
    const clean = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    )
    return req(`/repos?${new URLSearchParams(clean)}`)
  },
  repo: (owner, name) => req(`/repos/${enc(owner)}/${enc(name)}`),
  createRepo: (body) => req('/repos', jsonBody('POST', body)),
  updateRepo: (owner, name, body) => req(`/repos/${enc(owner)}/${enc(name)}`, jsonBody('PUT', body)),
  deleteRepo: (owner, name) => req(`/repos/${enc(owner)}/${enc(name)}`, { method: 'DELETE' }),
  like: (owner, name) => req(`/repos/${enc(owner)}/${enc(name)}/like`, { method: 'POST' }),
  registerDownload: (owner, name) =>
    req(`/repos/${enc(owner)}/${enc(name)}/download`, { method: 'POST' }),

  // Files
  addFile: (owner, name, body) =>
    req(`/repos/${enc(owner)}/${enc(name)}/files`, jsonBody('POST', body)),
  deleteFile: (owner, name, fileId) =>
    req(`/repos/${enc(owner)}/${enc(name)}/files/${fileId}`, { method: 'DELETE' }),
}
