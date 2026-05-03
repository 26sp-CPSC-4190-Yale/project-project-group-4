import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import useSwipe from '../hooks/useSwipe'
import { BASE_URL } from '../lib/constants'

export default function Gallery() {
  const { token } = useAuth()
  const [artworks, setArtworks] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [error, setError] = useState(null)

  const [imageReady, setImageReady] = useState(false)
  const [lastSwiped, setLastSwiped] = useState(null)
  const isFetchingRef = useRef(false)
  const noMoreRef = useRef(false)

  // Swipe callback: runs after the exit animation completes
  const { flipped, likeOpacity, passOpacity, exiting, cardProps, handleSwipe } = useSwipe(
    direction => {
      const artwork = artworks[currentIndex]
      const action = direction === 'right' ? 'like' : 'pass'
      recordInteraction(artwork.id, action)
      setLastSwiped({ artwork, action })
      setCurrentIndex(i => i + 1)
    }
  )

  async function fetchMore() {
    if (isFetchingRef.current || noMoreRef.current) return
    isFetchingRef.current = true
    try {
      const res = await fetch(`${BASE_URL}/api/artworks/?limit=20`, {
        headers: { Authorization: `Token ${token}` },
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      if (data.results.length === 0) {
        noMoreRef.current = true
      } else {
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

  // Track load state for the current artwork. Using a separate Image() instance
  // is more reliable than the JSX img's onLoad: when the displayed <img>'s src
  // swaps to a URL that's already cached, the load event may not re-fire on the
  // existing element, leaving imageReady stuck at false.
  useEffect(() => {
    const artwork = artworks[currentIndex]
    if (!artwork) return
    setImageReady(false)
    let cancelled = false
    const img = new Image()
    img.onload = () => { if (!cancelled) setImageReady(true) }
    img.onerror = () => { if (!cancelled) skipCurrentArtwork() }
    img.src = `https://media.collections.yale.edu/thumbnail/yuag/obj/${artwork.id}`
    if (img.complete && img.naturalWidth > 0) setImageReady(true)
    return () => { cancelled = true }
  }, [currentIndex, artworks])

  // Preload the next 3 artwork images so they're cached by the browser
  useEffect(() => {
    const preloaded = []
    for (let i = 1; i <= 3; i++) {
      const next = artworks[currentIndex + i]
      if (next) {
        const img = new Image()
        img.src = `https://media.collections.yale.edu/thumbnail/yuag/obj/${next.id}`
        preloaded.push(img)
      }
    }
    return () => { preloaded.length = 0 }
  }, [currentIndex, artworks])

  // Keyboard shortcuts: Arrow keys and A/D for swiping
  useEffect(() => {
    function onKeyDown(e) {
      if (exiting || !artworks[currentIndex]) return
      if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {
        e.preventDefault()
        handleSwipe('right')
      } else if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {
        e.preventDefault()
        handleSwipe('left')
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [exiting, currentIndex, artworks, handleSwipe])

  async function handleUndo() {
    if (!lastSwiped) return
    try {
      await fetch(`${BASE_URL}/api/interactions/${lastSwiped.artwork.id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Token ${token}` },
      })
    } catch { /* best-effort */ }
    setCurrentIndex(i => i - 1)
    setLastSwiped(null)
  }

  function skipCurrentArtwork() {
    setCurrentIndex(i => i + 1)
  }

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
                    onError={skipCurrentArtwork}
                    style={{ opacity: imageReady ? 1 : 0, transition: 'opacity 0.3s ease' }}
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
            <button
              className="action-btn action-btn-undo"
              onClick={handleUndo}
              disabled={!lastSwiped || exiting}
            >
              ↩
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
