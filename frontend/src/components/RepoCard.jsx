import { Link } from 'react-router-dom'
import { formatBytes, timeAgo, compact } from '../utils.js'

export default function RepoCard({ repo }) {
  const [owner, name] = repo.repo_id.split('/')
  const icon = repo.repo_type === 'dataset' ? '📊' : '🧠'
  return (
    <Link to={`/${owner}/${name}`} className="repo-card">
      <div className="repo-card-head">
        <span className="repo-icon">{icon}</span>
        <span className="repo-id">
          <span className="repo-owner">{owner}</span>
          <span className="repo-slash">/</span>
          <span className="repo-name">{name}</span>
        </span>
      </div>

      {repo.description && <p className="repo-desc">{repo.description}</p>}

      <div className="repo-meta">
        {repo.task && <span className="pill pill-task">{repo.task}</span>}
        {repo.library && <span className="pill">{repo.library}</span>}
        <span className="repo-meta-spacer" />
        <span className="stat" title="Updated">
          🕑 {timeAgo(repo.updated_at)}
        </span>
        <span className="stat" title="Files size">
          💾 {formatBytes(repo.total_size_bytes)}
        </span>
        <span className="stat" title="Downloads">
          ⬇ {compact(repo.downloads)}
        </span>
        <span className="stat" title="Likes">
          ❤ {compact(repo.likes)}
        </span>
      </div>
    </Link>
  )
}
