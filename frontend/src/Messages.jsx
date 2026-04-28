import { useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import { BASE_URL } from './constants'
import Conversation from './Conversation'
import MatchProfile from './MatchProfile'



export default function Messages() {
  const { token } = useAuth()
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeConversation, setActiveConversation] = useState(null)
  const [activeProfile, setActiveProfile] = useState(null)


  async function fetchMatches() {
    const res = await fetch(`${BASE_URL}/api/matches/`, {
      headers: { Authorization: `Token ${token}` },
    })
    if (res.ok) setMatches(await res.json())
    setLoading(false)
  }

  useEffect(() => { fetchMatches() }, [token])

  async function performAction(userId, action) {
    const res = await fetch(`${BASE_URL}/api/matches/${userId}/action/`, {
      method: 'POST',
      headers: { Authorization: `Token ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    })
    if (res.ok) fetchMatches()
  }

  if (activeProfile) {
    return (
      <MatchProfile
        match={activeProfile}
        onBack={() => setActiveProfile(null)}
        onMessage={user => {
          setActiveProfile(null)
          setActiveConversation(user)
        }}
      />
    )
  }

  if (activeConversation) {
    return (
      <Conversation
        otherUser={activeConversation}
        onBack={() => { setActiveConversation(null); fetchMatches() }}
        onUnmatch={() => { setActiveConversation(null); fetchMatches() }}
      />
    )
  }

  const newMatches = matches.filter(m => m.status === 'pending')
  const incoming = matches.filter(m => m.status === 'requested' && !m.requested_by_me)
  const sent = matches.filter(m => m.status === 'requested' && m.requested_by_me)
  const conversations = matches.filter(m => m.status === 'accepted')

  function FacetTags({ facets }) {
    if (!facets || facets.length === 0) return null
    return (
      <div className="match-facets">
        {facets.map((f, i) => <span key={i} className="match-facet-tag">{f.value}</span>)}
      </div>
    )
  }

  function MatchCard({ m, actions }) {
    return (
      <div className="match-card">
        <span className="messages-user-avatar">{m.user.username[0].toUpperCase()}</span>
        <div className="match-card-info">
          <span className="messages-user-name">{m.user.username}</span>
          <span className="match-similarity">{Math.round(m.similarity * 100)}% taste match</span>
          <FacetTags facets={m.top_facets} />
        </div>
        <div className="match-actions">{actions}</div>
      </div>
    )
  }

  return (
    <div className="messages-page">
      <h2 className="messages-title">Messages</h2>
      {loading && <p className="status-message">Loading…</p>}

      {newMatches.length > 0 && (
        <section className="match-section">
          <h3 className="match-section-title">New Matches</h3>
          {newMatches.map(m => (
            <MatchCard key={m.user.id} m={m} actions={
              <>
                <button className="match-action-btn secondary" onClick={() => setActiveProfile(m)}>View Profile</button>
                <button className="match-action-btn primary" onClick={() => performAction(m.user.id, 'request')}>Send Request</button>
              </>
            } />
          ))}
        </section>
      )}

      {incoming.length > 0 && (
        <section className="match-section">
          <h3 className="match-section-title">Incoming Requests</h3>
          {incoming.map(m => (
            <MatchCard key={m.user.id} m={m} actions={
              <>
                <button className="match-action-btn secondary" onClick={() => setActiveProfile(m)}>View Profile</button>
                <button className="match-action-btn primary" onClick={() => performAction(m.user.id, 'accept')}>Accept</button>
                <button className="match-action-btn secondary" onClick={() => performAction(m.user.id, 'decline')}>Decline</button>
              </>
            } />
          ))}
        </section>
      )}

      {sent.length > 0 && (
        <section className="match-section">
          <h3 className="match-section-title">Pending</h3>
          {sent.map(m => (
            <MatchCard key={m.user.id} m={m} actions={
              <>
                <button className="match-action-btn secondary" onClick={() => setActiveProfile(m)}>View Profile</button>
                <span className="match-status-label">Waiting…</span>
              </>
            } />
          ))}
        </section>
      )}

      {conversations.length > 0 && (
        <section className="match-section">
          <h3 className="match-section-title">Conversations</h3>
          <ul className="messages-user-list">
            {conversations.map(m => (
              <li key={m.user.id}>
                <div className="match-card">
                  <span className="messages-user-avatar">{m.user.username[0].toUpperCase()}</span>
                  <div className="match-card-info">
                    <span className="messages-user-name">{m.user.username}</span>
                    <span className="match-similarity">{Math.round(m.similarity * 100)}% taste match</span>
                    <FacetTags facets={m.top_facets} />
                  </div>
                  <div className="match-actions">
                    <button className="match-action-btn secondary" onClick={() => setActiveProfile(m)}>View Profile</button>
                    <button className="match-action-btn primary" onClick={() => setActiveConversation(m.user)}>Open Chat</button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!loading && matches.length === 0 && (
        <p className="messages-empty">No matches yet. Keep swiping!</p>
      )}
    </div>
  )
}
