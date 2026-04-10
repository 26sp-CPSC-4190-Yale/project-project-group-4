import { useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import Conversation from './Conversation'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function Messages() {
  const { token } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeConversation, setActiveConversation] = useState(null)

  useEffect(() => {
    async function fetchUsers() {
      const res = await fetch(`${BASE_URL}/api/users/`, {
        headers: { Authorization: `Token ${token}` },
      })
      if (res.ok) {
        setUsers(await res.json())
      }
      setLoading(false)
    }
    fetchUsers()
  }, [token])

  if (activeConversation) {
    return (
      <Conversation
        otherUser={activeConversation}
        onBack={() => setActiveConversation(null)}
      />
    )
  }

  return (
    <div className="messages-page">
      <h2 className="messages-title">Messages</h2>
      {loading && <p className="status-message">Loading…</p>}
      {!loading && users.length === 0 && (
        <p className="messages-empty">No other users yet.</p>
      )}
      <ul className="messages-user-list">
        {users.map((u) => (
          <li key={u.id}>
            <button
              className="messages-user-item"
              onClick={() => setActiveConversation(u)}
            >
              <span className="messages-user-avatar">{u.username[0].toUpperCase()}</span>
              <span className="messages-user-name">{u.username}</span>
              <span className="messages-user-chevron">›</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
