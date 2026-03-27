import { useState, useEffect, useRef } from 'react'
import { useAuth } from './AuthContext'
import useSwipe from './useSwipe'
import { BASE_URL, FALLBACK_IMAGE } from './constants'

export default function Gallery() {
  const { token } = useAuth()
  const [artworks, setArtworks] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [error, setError] = useState(null)

  const isFetchingRef = useRef(false)
  const seenIdsRef = useRef(new Set())
  const noMoreRef = useRef(false)

  // Swipe handler: record the interaction, then advance to next card
  const { flipped, likeOpacity, passOpacity, cardProps, handleSwipe } = useSwipe(
    direction => {
      const artwork = artworks[currentIndex]
      const action = direction === 'right' ? 'like' : 'pass'
      recordInteraction(artwork.id, action)
      setTimeout(() => setCurrentIndex(i => i + 1), 0)
    }
  )

  async function fetchMore() {
    if (isFetchingRef.current || noMoreRef.current) return
    isFetchingRef.current = true
    try {
      const exclude = [...seenIdsRef.current].join(',')
      const params = `limit=20${exclude ? `&exclude=${exclude}` : ''}`
      const res = await fetch(`${BASE_URL}/api/artworks/?${params}`, {
        headers: { Authorization: `Token ${token}` },
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      if (data.results.length === 0) {
        noMoreRef.current = true
      } else {
        data.results.forEach(a => seenIdsRef.current.add(a.id))
        setArtworks(prev => [...prev, ...data.results])
      }
    } catch {
      setError('Failed to load artworks. Is the server running?')
    } finally {
      isFetchingRef.current = false
    }
  }

  async function recordInteraction(artworkId, action) {
    try {
      await fetch(`${BASE_URL}/api/interactions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Token ${token}` },
        body: JSON.stringify({ artwork_id: artworkId, action }),
      })
    } catch { /* fire and forget */ }
  }

  useEffect(() => { fetchMore() }, [])

  useEffect(() => {
    if (artworks.length > 0 && currentIndex >= artworks.length - 5) fetchMore()
  }, [currentIndex, artworks.length])

  const artwork = artworks[currentIndex]

  return (
    <main className="gallery">
      {error && <p className="error-message">{error}</p>}

      {artwork ? (
        <>
          <div className="card-container">
            <div className="card" {...cardProps}>
              <div className="swipe-label swipe-label-like" style={{ opacity: likeOpacity }}>
                LIKE
              </div>
              <div className="swipe-label swipe-label-pass" style={{ opacity: passOpacity }}>
                NOPE
              </div>

              <div
                className="card-flipper"
                style={{ transform: flipped ? 'rotateY(180deg)' : 'none' }}
              >
                {/* Front: artwork image with gradient overlay */}
                <div className="card-face card-front">
                  <img
                    className="card-image"
                    src={`https://media.collections.yale.edu/thumbnail/yuag/obj/${artwork.id}`}
                    alt={artwork.label}
                    onError={e => { e.target.src = FALLBACK_IMAGE }}
                    draggable={false}
                  />
                  <div className="card-gradient">
                    <h2 className="card-title">{artwork.label}</h2>
                    {artwork.date && <p className="card-date">{artwork.date}</p>}
                  </div>
                  <p className="card-hint">Tap for details</p>
                </div>

                {/* Back: artwork metadata */}
                <div className="card-face card-back">
                  <h2 className="card-back-title">{artwork.label}</h2>
                  {artwork.date && (
                    <div className="card-back-field">
                      <span className="card-back-label">Date</span>
                      {artwork.date}
                    </div>
                  )}
                  {artwork.accession_no && (
                    <div className="card-back-field">
                      <span className="card-back-label">Accession No.</span>
                      {artwork.accession_no}
                    </div>
                  )}
                  <div className="card-back-source">Yale University Art Gallery</div>
                  <p className="card-hint">Tap to see artwork</p>
                </div>
              </div>
            </div>
          </div>

          <div className="action-buttons">
            <button className="action-btn action-btn-pass" onClick={() => handleSwipe('left')}>
              ✕
            </button>
            <button className="action-btn action-btn-like" onClick={() => handleSwipe('right')}>
              ♥
            </button>
          </div>

          <p className="gallery-counter">
            {currentIndex + 1} viewed
          </p>
        </>
      ) : !error && artworks.length === 0 ? (
        <p className="status-message">Loading artworks...</p>
      ) : (
        <p className="status-message">No more artworks to discover!</p>
      )}
    </main>
  )
}
