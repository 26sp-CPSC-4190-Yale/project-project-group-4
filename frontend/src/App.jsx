import { useState, useEffect, useRef } from 'react'
import { AuthProvider, useAuth } from './AuthContext'
import Login from './Login'
import Register from './Register'
import './App.css'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const SWIPE_THRESHOLD = 80

function Gallery() {
  const { user, token, logout } = useAuth()
  const [artworks, setArtworks] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [error, setError] = useState(null)
  const [dragX, setDragX] = useState(0)
  const [dragging, setDragging] = useState(false)
  const startXRef = useRef(null)
  const isFetchingRef = useRef(false)
  const seenIdsRef = useRef(new Set())
  const noMoreRef = useRef(false)

  async function fetchMore() {
    if (isFetchingRef.current || noMoreRef.current) return
    isFetchingRef.current = true
    try {
      const exclude = [...seenIdsRef.current].join(',')
      const params = `limit=20${exclude ? `&exclude=${exclude}` : ''}`
      const r = await fetch(`${BASE_URL}/api/artworks/?${params}`, {
        headers: { Authorization: `Token ${token}` },
      })
      if (!r.ok) throw new Error()
      const data = await r.json()
      if (data.results.length === 0) {
        noMoreRef.current = true
      } else {
        data.results.forEach(a => seenIdsRef.current.add(a.id))
        setArtworks(prev => [...prev, ...data.results])
      }
    } catch {
      setError('Failed to load artworks. Is Django running?')
    } finally {
      isFetchingRef.current = false
    }
  }

  useEffect(() => { fetchMore() }, [])

  useEffect(() => {
    if (artworks.length > 0 && currentIndex >= artworks.length - 5) {
      fetchMore()
    }
  }, [currentIndex, artworks.length])

  async function recordInteraction(artworkId, action) {
    try {
      await fetch(`${BASE_URL}/api/interactions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Token ${token}` },
        body: JSON.stringify({ artwork_id: artworkId, action }),
      })
    } catch (_) {}
  }

  function handleSwipe(direction) {
    const artwork = artworks[currentIndex]
    recordInteraction(artwork.id, direction === 'right' ? 'like' : 'pass')
    setDragX(0)
    setCurrentIndex(i => i + 1)
  }

  function onTouchStart(e) {
    startXRef.current = e.touches[0].clientX
    setDragging(true)
  }

  function onTouchMove(e) {
    if (startXRef.current === null) return
    setDragX(e.touches[0].clientX - startXRef.current)
  }

  function onTouchEnd() {
    if (Math.abs(dragX) >= SWIPE_THRESHOLD) {
      handleSwipe(dragX > 0 ? 'right' : 'left')
    } else {
      setDragX(0)
    }
    startXRef.current = null
    setDragging(false)
  }

  function onMouseDown(e) {
    startXRef.current = e.clientX
    setDragging(true)
  }

  function onMouseMove(e) {
    if (!dragging || startXRef.current === null) return
    setDragX(e.clientX - startXRef.current)
  }

  function onMouseUp() {
    if (Math.abs(dragX) >= SWIPE_THRESHOLD) {
      handleSwipe(dragX > 0 ? 'right' : 'left')
    } else {
      setDragX(0)
    }
    startXRef.current = null
    setDragging(false)
  }

  const artwork = artworks[currentIndex]
  const rotation = dragX / 20
  const likeOpacity = Math.max(0, Math.min(dragX / SWIPE_THRESHOLD, 1))
  const passOpacity = Math.max(0, Math.min(-dragX / SWIPE_THRESHOLD, 1))

  return (
    <div className="gallery-container">
      <div style={{ position: 'fixed', top: 12, right: 16, display: 'flex', alignItems: 'center', gap: 12, zIndex: 100 }}>
        <span>{user.username}</span>
        <button onClick={logout} style={{ cursor: 'pointer' }}>Logout</button>
      </div>

      <h1>YArt Match</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {artwork ? (
        <>
          <div
            className="artwork-card"
            style={{
              border: '1px solid #ccc',
              padding: '20px',
              borderRadius: '8px',
              maxWidth: '400px',
              margin: '0 auto',
              cursor: dragging ? 'grabbing' : 'grab',
              userSelect: 'none',
              position: 'relative',
              transform: `translateX(${dragX}px) rotate(${rotation}deg)`,
              transition: dragging ? 'none' : 'transform 0.3s ease',
            }}
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={onMouseUp}
          >
            <div style={{
              position: 'absolute', top: 16, left: 16,
              border: '3px solid green', color: 'green',
              padding: '4px 12px', borderRadius: 4, fontWeight: 'bold', fontSize: 22,
              opacity: likeOpacity, pointerEvents: 'none',
            }}>LIKE</div>

            <div style={{
              position: 'absolute', top: 16, right: 16,
              border: '3px solid red', color: 'red',
              padding: '4px 12px', borderRadius: 4, fontWeight: 'bold', fontSize: 22,
              opacity: passOpacity, pointerEvents: 'none',
            }}>PASS</div>

            <h2>{artwork.label}</h2>
            <p><strong>Accession Number:</strong> {artwork.accession_no}</p>
            <p><strong>Date:</strong> {artwork.date}</p>
            <img
              src={`https://media.collections.yale.edu/thumbnail/yuag/obj/${artwork.id}`}
              alt={artwork.label}
              style={{ width: '100%', height: 'auto', marginTop: '15px', borderRadius: '4px' }}
              draggable={false}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginTop: 24 }}>
            <button
              onClick={() => handleSwipe('left')}
              style={{ padding: '12px 32px', fontSize: 20, background: '#e74c3c', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
            >✗ Pass</button>
            <button
              onClick={() => handleSwipe('right')}
              style={{ padding: '12px 32px', fontSize: 20, background: '#2ecc71', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
            >♥ Like</button>
          </div>
        </>
      ) : !error && artworks.length === 0 ? (
        <p>Loading museum vault...</p>
      ) : (
        <p style={{ textAlign: 'center', marginTop: 40 }}>No more artworks!</p>
      )}
    </div>
  )
}

function AuthGate() {
  const { token } = useAuth()
  const [showRegister, setShowRegister] = useState(false)

  if (token) return <Gallery />
  if (showRegister) return <Register onSwitch={() => setShowRegister(false)} />
  return <Login onSwitch={() => setShowRegister(true)} />
}

export default function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  )
}
