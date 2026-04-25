import { useEffect, useMemo, useState } from 'react'
import { useAuth } from './AuthContext'
import { BASE_URL } from './constants'

export default function TasteProfile() {
  const { token } = useAuth()
  const [signals, setSignals] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Art of the Day state
  const [candidates, setCandidates] = useState([])
  const [explanation, setExplanation] = useState([])
  const [candidateIndex, setCandidateIndex] = useState(0)
  const [isPopular, setIsPopular] = useState(false)
  const [aotdLoading, setAotdLoading] = useState(true)
  const [imageReady, setImageReady] = useState(false)

  useEffect(() => {
    async function fetchTaste() {
      try {
        const headers = { Authorization: `Token ${token}` }
        const tasteRes = await fetch(`${BASE_URL}/api/taste/me/`, { headers })
        if (!tasteRes.ok) throw new Error()
        const tasteData = await tasteRes.json()
        setSignals(tasteData.signals || [])

        // Stats fetch is optional — endpoint may not be deployed yet
        try {
          const statsRes = await fetch(`${BASE_URL}/api/profile/stats/`, { headers })
          if (statsRes.ok) setStats(await statsRes.json())
        } catch { /* stats unavailable */ }
      } catch {
        setError('Failed to load taste profile.')
      } finally {
        setLoading(false)
      }
    }

    async function fetchDaily() {
      try {
        const res = await fetch(`${BASE_URL}/api/art-of-the-day/`, {
          headers: { Authorization: `Token ${token}` },
        })
        if (!res.ok) throw new Error()
        const data = await res.json()
        setCandidates(data.candidates || [])
        setExplanation(data.explanation || [])
        setIsPopular(data.is_popular || false)
      } catch {
        // silent fail — taste profile still shows
      } finally {
        setAotdLoading(false)
      }
    }

    fetchTaste()
    fetchDaily()
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

  const dailyArt = candidates[candidateIndex] || null
  const allCandidatesFailed = candidateIndex >= candidates.length && candidates.length > 0

  const [usedFallback, setUsedFallback] = useState(false)

  function handleImageError() {
    setImageReady(false)
    setCandidateIndex(i => i + 1)
  }

  useEffect(() => {
    if (!usedFallback && candidateIndex >= candidates.length && candidates.length > 0) {
      setUsedFallback(true)
      fetch(`${BASE_URL}/api/art-of-the-day/?fallback=true`, {
        headers: { Authorization: `Token ${token}` },
      })
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.candidates?.length) {
            setCandidates(data.candidates)
            setCandidateIndex(0)
            setExplanation([])
            setIsPopular(true)
          }
        })
        .catch(() => {})
    }
  }, [candidateIndex, candidates.length, usedFallback, token])

  function formatCentury(value) {
    const n = parseInt(value, 10)
    const abs = Math.abs(n)
    const suffix = abs % 10 === 1 && abs !== 11 ? 'st'
      : abs % 10 === 2 && abs !== 12 ? 'nd'
      : abs % 10 === 3 && abs !== 13 ? 'rd' : 'th'
    return `${abs}${suffix} century${n < 0 ? ' BC' : ''}`
  }

  function formatAgent(agent) {
    let str = agent.name
    if (agent.role && agent.role !== 'Artist') {
      str += ` (${agent.role})`
    }
    if (agent.nationalities?.length) {
      str += `, ${agent.nationalities.join(', ')}`
    }
    if (agent.begin_date) {
      const birth = agent.begin_date.slice(0, 4)
      const death = agent.end_date ? agent.end_date.slice(0, 4) : 'present'
      str += ` (${birth}\u2013${death})`
    }
    return str
  }

  if (loading) return <p className="status-message">Analyzing your taste...</p>
  if (error) return <p className="error-message">{error}</p>

  return (
    <div className="profile-page">
      <h2 className="profile-title">Your Taste Profile</h2>

      {/* Art of the Day */}
      {aotdLoading ? (
        <div className="aotd-card">
          <div className="aotd-skeleton-image" />
          <div className="aotd-body">
            <div className="aotd-skeleton-line aotd-skeleton-title" />
            <div className="aotd-skeleton-line" />
            <div className="aotd-skeleton-line aotd-skeleton-short" />
          </div>
        </div>
      ) : dailyArt && !allCandidatesFailed ? (
        <div className="aotd-card">
          <div className="aotd-header">
            <span className="aotd-label">Art of the Day</span>
          </div>

          <div className="aotd-image-wrap">
            <img
              className="aotd-image"
              src={`https://media.collections.yale.edu/thumbnail/yuag/obj/${dailyArt.id}`}
              alt={dailyArt.label}
              onLoad={() => setImageReady(true)}
              onError={handleImageError}
              style={{ opacity: imageReady ? 1 : 0, transition: 'opacity 0.4s ease' }}
              draggable={false}
            />
          </div>

          <div className="aotd-body">
            <h3 className="aotd-title">{dailyArt.label}</h3>

            {dailyArt.agents?.length > 0 && (
              <p className="aotd-artist">
                {dailyArt.agents.map(formatAgent).join('; ')}
              </p>
            )}

            <div className="aotd-meta">
              {dailyArt.date && (
                <div className="aotd-meta-row">
                  <span className="aotd-meta-label">Date</span>
                  <span className="aotd-meta-value">{dailyArt.date}</span>
                </div>
              )}
              {dailyArt.medium && (
                <div className="aotd-meta-row">
                  <span className="aotd-meta-label">Medium</span>
                  <span className="aotd-meta-value">{dailyArt.medium}</span>
                </div>
              )}
              {dailyArt.dimensions && (
                <div className="aotd-meta-row">
                  <span className="aotd-meta-label">Dimensions</span>
                  <span className="aotd-meta-value">{dailyArt.dimensions}</span>
                </div>
              )}
              {dailyArt.period && (
                <div className="aotd-meta-row">
                  <span className="aotd-meta-label">Period</span>
                  <span className="aotd-meta-value">{dailyArt.period}</span>
                </div>
              )}
              {dailyArt.culture && (
                <div className="aotd-meta-row">
                  <span className="aotd-meta-label">Culture</span>
                  <span className="aotd-meta-value">{dailyArt.culture}</span>
                </div>
              )}
              {dailyArt.classifiers?.length > 0 && (
                <div className="aotd-meta-row">
                  <span className="aotd-meta-label">Classification</span>
                  <span className="aotd-meta-value">{dailyArt.classifiers.join(', ')}</span>
                </div>
              )}
              {dailyArt.departments?.length > 0 && (
                <div className="aotd-meta-row">
                  <span className="aotd-meta-label">Department</span>
                  <span className="aotd-meta-value">{dailyArt.departments.join(', ')}</span>
                </div>
              )}
              {dailyArt.places?.length > 0 && (
                <div className="aotd-meta-row">
                  <span className="aotd-meta-label">Place</span>
                  <span className="aotd-meta-value">{dailyArt.places.join(', ')}</span>
                </div>
              )}
            </div>

            {dailyArt.credit_line && (
              <p className="aotd-credit">{dailyArt.credit_line}</p>
            )}

            <div className="aotd-explanation">
              {explanation.length > 0 ? (
                <>
                  <span className="aotd-explanation-label">Chosen for you because you love</span>
                  <div className="aotd-explanation-tags">
                    {explanation.map(e => (
                      <span key={`${e.facet}-${e.value}`} className="taste-tag">
                        {e.facet === 'century' ? formatCentury(e.value) : e.value}
                      </span>
                    ))}
                  </div>
                </>
              ) : isPopular ? (
                <span className="aotd-explanation-label">Popular among YArt users — keep swiping to get personalized picks</span>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {/* Stats */}
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

      {/* Taste signal tags */}
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
