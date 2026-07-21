export default function FacetSidebar({ facets, active, onToggle }) {
  if (!facets) return <aside className="facets" />

  const groups = [
    { key: 'task', label: 'Tasks', values: facets.tasks },
    { key: 'library', label: 'Libraries', values: facets.libraries },
    { key: 'license', label: 'Licenses', values: facets.licenses },
    { key: 'tag', label: 'Tags', values: facets.tags },
  ]

  return (
    <aside className="facets">
      {groups
        .filter((g) => g.values && g.values.length)
        .map((g) => (
          <div key={g.key} className="facet-group">
            <h4>{g.label}</h4>
            <ul>
              {g.values.map((v) => {
                const isActive = active[g.key] === v.value
                return (
                  <li key={v.value}>
                    <button
                      className={isActive ? 'facet active' : 'facet'}
                      onClick={() => onToggle(g.key, v.value)}
                    >
                      <span className="facet-label">{v.value}</span>
                      <span className="facet-count">{v.count}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
    </aside>
  )
}
