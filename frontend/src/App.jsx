import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [artwork, setArtwork] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Reaching out to the Django API
    fetch('http://127.0.0.1:8000/api/artwork/')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => setArtwork(data))
      .catch(error => {
        console.error("Error fetching art:", error);
        setError("Failed to load artwork. Is Django running?");
      })
  }, [])

  return (
    <div className="gallery-container">
      <h1>YArt Match</h1>
      
      {error && <p style={{ color: 'red' }}>{error}</p>}
      
      {artwork ? (
        <div className="artwork-card" style={{ border: '1px solid #ccc', padding: '20px', borderRadius: '8px', maxWidth: '400px', margin: '0 auto' }}>
          <h2>{artwork.label}</h2>
          <p><strong>Accession Number:</strong> {artwork.accession_no}</p>
          <p><strong>Date:</strong> {artwork.date}</p>
          
          {/* The dynamic image tag */}
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

export default App