import { useState, useEffect, useMemo } from 'react'
import { useAuth } from './AuthContext'
import { BASE_URL, FALLBACK_IMAGE } from './constants'
import { buildEraBreakdown } from './dateUtils'

const PROFILE_FETCH_LIMIT = 500

export default function Profile({ onNavigate }) {
  const { token, user } = useAuth()
  const [liked, setLiked] = useState([])
  const [totalLikes, setTotalLikes] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchProfile() {
      try {
        const res = await fetch(
          `${BASE_URL}/api/liked/?limit=${PROFILE_FETCH_LIMIT}&offset=0`,
          { headers: { Authorization: `Token ${token}` } }
        )
        if (!res.ok) throw new Error()
        const data = await res.json()
        setTotalLikes(data.count)
        setLiked(data.results)
      } catch {
        setError('Failed to load profile data.')
      } finally {
        setLoading(false)
      }
    }
    fetchProfile()
  }, [token])

  const recent = liked.slice(0, 8)
  const eras = useMemo(() => buildEraBreakdown(liked), [liked])

  const initial = user?.username?.[0]?.toUpperCase() ?? '?'

  return (
    <div className="profile-page">
      <h2 className="profile-title">Profile</h2>

      <section className="profile-account">
        <div className="profile-avatar">{initial}</div>
        <div className="profile-account-info">
          <p className="profile-username">{user?.username}</p>
          {user?.email && <p className="profile-email">{user.email}</p>}
        </div>
      </section>

      <section className="profile-stats">
        <div className="profile-stat-card">
          {loading ? (
            <div className="profile-skeleton profile-skeleton-stat" />
          ) : (
            <p className="profile-stat-value">{totalLikes ?? 0}</p>
          )}
          <p className="profile-stat-label">Total Likes</p>
        </div>
      </section>

      <section className="profile-eras">
        <div className="profile-section-header">
          <h3 className="profile-section-title">Eras You Love</h3>
        </div>

        {loading ? (
          <div className="profile-era-list">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="profile-skeleton profile-skeleton-era" />
            ))}
          </div>
        ) : eras.length === 0 ? (
          <p className="profile-empty-sub">
            Like a few artworks to see your era breakdown.
          </p>
        ) : (
          <div className="profile-era-list">
            {eras.map(({ label, count, percent }) => (
              <div key={label} className="profile-era-row">
                <span className="profile-era-label">{label}</span>
                <div className="profile-era-bar-track">
                  <div
                    className="profile-era-bar-fill"
                    style={{ width: `${Math.max(percent, 2)}%` }}
                  />
                </div>
                <span className="profile-era-count">
                  {count} · {percent}%
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="profile-recent">
        <div className="profile-section-header">
          <h3 className="profile-section-title">Recently Liked</h3>
        </div>

        {error && <p className="error-message">{error}</p>}

        {loading ? (
          <div className="profile-recent-strip">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="profile-skeleton profile-skeleton-thumb" />
            ))}
          </div>
        ) : recent.length === 0 ? (
          <p className="profile-empty">Nothing here yet — start swiping!</p>
        ) : (
          <div className="profile-recent-strip">
            {recent.map(artwork => (
              <button
                key={artwork.id}
                type="button"
                className="profile-recent-item"
                onClick={() => onNavigate?.('likes')}
                aria-label={`Open My Likes — ${artwork.label}`}
              >
                <img
                  src={`https://media.collections.yale.edu/thumbnail/yuag/obj/${artwork.id}`}
                  alt={artwork.label}
                  onError={e => { e.target.src = FALLBACK_IMAGE }}
                />
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
