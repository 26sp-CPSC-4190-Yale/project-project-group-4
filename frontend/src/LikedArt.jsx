import { useState, useEffect } from 'react'
import { useAuth } from './AuthContext'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function LikedArt({ onBack }) {
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
    <div style={styles.container}>
      <div style={styles.header}>
        <button onClick={onBack} style={styles.backButton}>← Back</button>
        <h1 style={styles.title}>Liked Art</h1>
      </div>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {loading ? (
        <p>Loading your liked artworks...</p>
      ) : artworks.length === 0 ? (
        <p style={{ textAlign: 'center', marginTop: 40 }}>
          You haven't liked any artworks yet.
        </p>
      ) : (
        <div style={styles.grid}>
          {artworks.map(artwork => (
            <div key={artwork.id} style={styles.card}>
              <img
                src={`https://media.collections.yale.edu/thumbnail/yuag/obj/${artwork.id}`}
                alt={artwork.label}
                style={styles.image}
              />
              <div style={styles.cardBody}>
                <p style={styles.label}>{artwork.label}</p>
                {artwork.date && <p style={styles.date}>{artwork.date}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const styles = {
  container: { maxWidth: 900, margin: '0 auto', padding: 20 },
  header: { display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 },
  backButton: {
    background: 'none', border: '1px solid #ccc', borderRadius: 4,
    padding: '6px 14px', cursor: 'pointer', color: 'inherit', fontSize: 14,
  },
  title: { margin: 0, fontSize: '1.8em' },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
    gap: 16,
  },
  card: {
    border: '1px solid #ccc', borderRadius: 8,
    overflow: 'hidden', background: '#1a1a1a',
  },
  image: { width: '100%', height: 180, objectFit: 'cover', display: 'block' },
  cardBody: { padding: '8px 10px' },
  label: { margin: 0, fontSize: 13, fontWeight: 'bold' },
  date: { margin: '4px 0 0', fontSize: 12, opacity: 0.7 },
}
