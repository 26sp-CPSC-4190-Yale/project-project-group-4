import { useEffect, useState } from 'react'
import { useAuth } from './AuthContext'
import { BASE_URL } from './constants'

export default function TasteProfile() {
    const { token } = useAuth()
    const [signals, setSignals] = useState([])
    const[loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        async function fetchTaste() {
            try {
                const res = await fetch(`${BASE_URL}/api/taste/me/`, {
                    headers: {
                        Authorization: `Token ${token}`,
                    },
                })

                if (!res.ok) throw new Error()
                
                const data = await res.json()
                setSignals(data.signals || [])
            } catch {
                setError('Failed to load taste profile.')
            } finally {
                setLoading(false)
            }
        }

        fetchTaste()
    }, [token])

    if (loading) return <p className="status-message">Analyzing your taste...</p>
    if (error) return <p className="error-message">{error}</p>

    const grouped = {}
    signals.forEach(s => {
        if (!grouped[s.facet]) grouped[s.facet] = []
        grouped[s.facet].push(s)
    })

    return (
        <div className="likes-page">
            <h2 className="likes-title">Your Taste Profile</h2>

            {Object.keys(grouped).length === 0 ? (
                <p className="likes-empty">Like more art to build your profile.</p>
            ) : (
                Object.entries(grouped).map(([facet, values]) =>(
                    <div key={facet} className="taste-section">
                        <h3 className="taste-section-title">
                            {facet.charAt(0).toUpperCase() + facet.slice(1)}
                        </h3>

                        <div className="taste-tags">
                            {values.map(v => (
                                <span key={v.value} className="taste-tag">
                                    {v.value}
                                </span>
                            ))}
                        </div>
                    </div>
                ))  
            )}
        </div>
    )
}
