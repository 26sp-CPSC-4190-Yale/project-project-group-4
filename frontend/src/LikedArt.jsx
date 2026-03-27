import { useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import { BASE_URL, FALLBACK_IMAGE } from './constants'

export default function LikedArt() {
  const { token } = useAuth()
  const [artworks, setArtworks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchLiked() {
      try {
        const res = await fetch(`${BASE_URL}/api/liked/?limit=50&offset=0`, {
          headers: { Authorization: `Token ${token}` },
        })
        if (!res.ok) throw new Error()
        const data = await res.json()
        setArtworks(data.results)
      } catch {
        setError('Failed to load liked artworks.')
      } finally {
        setLoading(false)
      }
    }
    fetchLiked()
  }, [token])

  return (
    <div className="likes-page">
      <h2 className="likes-title">My Likes</h2>

      {error && <p className="error-message">{error}</p>}

      {loading ? (
        <p className="status-message">Loading your liked artworks...</p>
      ) : artworks.length === 0 ? (
        <p className="likes-empty">You haven't liked any artworks yet.</p>
      ) : (
        <div className="likes-grid">
          {artworks.map(artwork => (
            <div key={artwork.id} className="likes-card">
              <img
                src={`https://media.collections.yale.edu/thumbnail/yuag/obj/${artwork.id}`}
                alt={artwork.label}
                onError={e => { e.target.src = FALLBACK_IMAGE }}
              />
              <div className="likes-card-body">
                <p className="likes-card-title">{artwork.label}</p>
                {artwork.date && <p className="likes-card-date">{artwork.date}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
