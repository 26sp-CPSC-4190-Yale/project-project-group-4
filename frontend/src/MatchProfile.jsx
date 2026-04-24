export default function MatchProfile({ match, onBack, onMessage }) {
  return (
    <div className="profile-page">
      <button className="conversation-back" onClick={onBack}>←</button>

      <section className="profile-account">
        <div className="profile-avatar">{match.user.username[0].toUpperCase()}</div>
        <div className="profile-account-info">
          <p className="profile-username">{match.user.username}</p>
          <p className="profile-since">
            Matched on {new Date(match.matched_at).toLocaleDateString()}
          </p>
        </div>
      </section>

      <section className="profile-stats">
        <div className="profile-stat-card">
          <p className="profile-stat-value">{Math.round(match.similarity * 100)}%</p>
          <p className="profile-stat-label">Taste Match</p>
        </div>
        <div className="profile-stat-card">
          <p className="profile-stat-value">{match.top_facets?.length ?? 0}</p>
          <p className="profile-stat-label">Shared Signals</p>
        </div>
      </section>

      <section className="taste-section">
        <h3 className="taste-section-title">Shared Taste</h3>
        <div className="taste-tags">
          {(match.top_facets || []).map((facet, i) => (
            <span key={i} className="taste-tag">{facet.value}</span>
          ))}
        </div>
      </section>

      {match.status === 'accepted' && (
        <button className="match-action-btn primary" onClick={() => onMessage(match.user)}>
          Open Chat
        </button>
      )}
    </div>
  )
}