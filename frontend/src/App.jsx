import { useState, useEffect } from 'react'
import { AuthProvider, useAuth } from './AuthContext'
import Login from './Login'
import Register from './Register'
import './App.css'

function Gallery() {
  const { user, token, logout } = useAuth()
  const [artwork, setArtwork] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
    fetch(`${baseUrl}/api/artwork/`, {
      headers: { Authorization: `Token ${token}` },
    })
      .then(response => {
        if (!response.ok) throw new Error('Network response was not ok')
        return response.json()
      })
      .then(data => setArtwork(data))
      .catch(err => {
        console.error('Error fetching art:', err)
        setError('Failed to load artwork. Is Django running?')
      })
  }, [token])

  return (
    <div className="gallery-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>YArt Match</h1>
        <div>
          <span style={{ marginRight: 12 }}>Hello, {user.username}</span>
          <button onClick={logout} style={{ cursor: 'pointer' }}>Logout</button>
        </div>
      </div>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {artwork ? (
        <div className="artwork-card" style={{ border: '1px solid #ccc', padding: '20px', borderRadius: '8px', maxWidth: '400px', margin: '0 auto' }}>
          <h2>{artwork.label}</h2>
          <p><strong>Accession Number:</strong> {artwork.accession_no}</p>
          <p><strong>Date:</strong> {artwork.date}</p>
          <img
            src={`https://media.collections.yale.edu/thumbnail/yuag/obj/${artwork.id}`}
            alt={artwork.label}
            style={{ width: '100%', height: 'auto', marginTop: '15px', borderRadius: '4px' }}
          />
        </div>
      ) : (
        !error && <p>Loading museum vault...</p>
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
