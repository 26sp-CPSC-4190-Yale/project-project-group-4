import { useEffect, useMemo, useState } from 'react'
import { useAuth } from './AuthContext'
import { BASE_URL } from './constants'

export default function TasteProfile() {
  const { token } = useAuth()
  const [signals, setSignals] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchTaste() {
      try {
        const headers = { Authorization: `Token ${token}` }
        const [tasteRes, statsRes] = await Promise.all([
          fetch(`${BASE_URL}/api/taste/me/`, { headers }),
          fetch(`${BASE_URL}/api/profile/stats/`, { headers }),
        ])

        if (!tasteRes.ok || !statsRes.ok) throw new Error()

        const [tasteData, statsData] = await Promise.all([
          tasteRes.json(),
          statsRes.json(),
        ])

        setSignals(tasteData.signals || [])
        setStats(statsData)
      } catch {
        setError('Failed to load taste profile.')
      } finally {
        setLoading(false)
      }
    }

    fetchTaste()
  }, [token])

  const grouped = useMemo(() => {
    const result = {}
    signals.forEach(signal => {
      if (!result[signal.facet]) result[signal.facet] = []
      result[signal.facet].push(signal)
    })
    return result
  }, [signals])

  const likeRate =
    stats && stats.total_likes + stats.total_passes > 0
      ? `${Math.round(stats.like_rate * 100)}%`
      : '--'

  if (loading) return <p className="status-message">Analyzing your taste...</p>
  if (error) return <p className="error-message">{error}</p>

  return (
    <div className="profile-page">
      <h2 className="profile-title">Your Taste Profile</h2>

      <section className="profile-stats">
        <div className="profile-stat-card">
          <p className="profile-stat-value">{stats?.total_likes ?? 0}</p>
          <p className="profile-stat-label">Total Likes</p>
        </div>
        <div className="profile-stat-card">
          <p className="profile-stat-value">{stats?.total_passes ?? 0}</p>
          <p className="profile-stat-label">Total Passes</p>
        </div>
        <div className="profile-stat-card">
          <p className="profile-stat-value">{likeRate}</p>
          <p className="profile-stat-label">Like Rate</p>
        </div>
        <div className="profile-stat-card">
          <p className="profile-stat-value">{signals.length}</p>
          <p className="profile-stat-label">Top Signals</p>
        </div>
      </section>

      {Object.keys(grouped).length === 0 ? (
        <p className="likes-empty">Like more art to build your profile.</p>
      ) : (
        Object.entries(grouped).map(([facet, values]) => (
          <section key={facet} className="taste-section">
            <h3 className="taste-section-title">
              {facet.charAt(0).toUpperCase() + facet.slice(1)}
            </h3>

            <div className="taste-tags">
              {values.map(value => (
                <span key={value.value} className="taste-tag">
                  {value.value} · {value.likes} likes
                </span>
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  )
}
