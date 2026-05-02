import { useState, useEffect, useMemo } from 'react'
import { useAuth } from './AuthContext'
import { BASE_URL, FALLBACK_IMAGE } from './constants'

export default function MatchProfile({ match, onBack, onMessage }) {
  const { token } = useAuth()
  const [facets, setFacets] = useState(null)
  const [commonArt, setCommonArt] = useState([])
  const [commonTotal, setCommonTotal] = useState(0)

  useEffect(() => {
    const headers = { Authorization: `Token ${token}` }
    async function fetchFacets() {
      try {
        const res = await fetch(`${BASE_URL}/api/matches/${match.user.id}/facets/`, { headers })
        if (res.ok) setFacets(await res.json())
      } catch { /* fall back to match.top_facets */ }
    }
    async function fetchCommonLikes() {
      try {
        const res = await fetch(`${BASE_URL}/api/matches/${match.user.id}/common-likes/`, { headers })
        if (res.ok) {
          const data = await res.json()
          setCommonArt(data.results)
          setCommonTotal(data.count)
        }
      } catch { /* silent */ }
    }
    fetchFacets()
    fetchCommonLikes()
  }, [match.user.id, token])

  const allFacets = facets ?? match.top_facets ?? []

  const grouped = useMemo(() => {
    const result = {}
    allFacets.forEach(f => {
      if (!result[f.facet]) result[f.facet] = []
      result[f.facet].push(f)
    })
    return result
  }, [allFacets])

  function strengthClass(score) {
    if (score > 0.7) return 'taste-tag taste-tag-strong'
    if (score < 0.5) return 'taste-tag taste-tag-muted'
    return 'taste-tag'
  }

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
          <p className="profile-stat-value">{allFacets.length}</p>
          <p className="profile-stat-label">Shared Signals</p>
        </div>
      </section>

      {Object.keys(grouped).length > 0 ? (
        Object.entries(grouped).map(([facet, values]) => (
          <section key={facet} className="taste-section">
            <h3 className="taste-section-title">
              {facet.charAt(0).toUpperCase() + facet.slice(1)}
            </h3>
            <div className="taste-tags">
              {values.map(f => (
                <span key={f.value} className={strengthClass(f.score)}>
                  {f.value}
                </span>
              ))}
            </div>
          </section>
        ))
      ) : (
        <section className="taste-section">
          <h3 className="taste-section-title">Shared Taste</h3>
          <p className="likes-empty">No shared taste signals yet.</p>
        </section>
      )}

      <section className="taste-section">
        <h3 className="taste-section-title">
          Artworks You Both Love{commonTotal > 0 && ` (${commonTotal})`}
        </h3>
        {commonArt.length > 0 ? (
          <div className="common-likes-grid">
            {commonArt.map(artwork => (
              <div key={artwork.id} className="common-likes-item">
                <img
                  src={`https://media.collections.yale.edu/thumbnail/yuag/obj/${artwork.id}`}
                  alt={artwork.label}
                  onError={e => { e.target.src = FALLBACK_IMAGE }}
                />
              </div>
            ))}
          </div>
        ) : (
          <p className="likes-empty">No common likes yet — you both have unique taste!</p>
        )}
      </section>

      {match.status === 'accepted' && (
        <button className="match-action-btn primary" onClick={() => onMessage(match.user)}>
          Open Chat
        </button>
      )}
    </div>
  )
}
