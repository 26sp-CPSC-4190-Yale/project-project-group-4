import { useState, useEffect, useRef } from 'react'
import { useAuth } from './AuthContext'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const POLL_INTERVAL = 4000

export default function Conversation({ otherUser, onBack, onUnmatch }) {
  const { token, user } = useAuth()
  const [messages, setMessages] = useState([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef(null)

  async function fetchMessages() {
    const res = await fetch(`${BASE_URL}/api/messages/${otherUser.id}/`, {
      headers: { Authorization: `Token ${token}` },
    })
    if (res.ok) {
      const data = await res.json()
      setMessages(data)
    }
  }

  useEffect(() => {
    fetchMessages()
    const interval = setInterval(fetchMessages, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [otherUser.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(e) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    setSending(true)
    try {
      const res = await fetch(`${BASE_URL}/api/messages/${otherUser.id}/`, {
        method: 'POST',
        headers: {
          Authorization: `Token ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: trimmed }),
      })
      if (res.ok) {
        setText('')
        await fetchMessages()
      }
    } finally {
      setSending(false)
    }
  }

  async function handleUnmatch() {
    if (!confirm(`Unmatch with ${otherUser.username}? This will delete all messages.`)) return
    const res = await fetch(`${BASE_URL}/api/matches/${otherUser.id}/`, {
      method: 'DELETE',
      headers: { Authorization: `Token ${token}` },
    })
    if (res.ok) onUnmatch()
  }

  return (
    <div className="conversation">
      <div className="conversation-header">
        <button className="conversation-back" onClick={onBack}>←</button>
        <span className="conversation-title">{otherUser.username}</span>
        <button className="conversation-unmatch" onClick={handleUnmatch}>Unmatch</button>
      </div>

      <div className="conversation-messages">
        {messages.length === 0 && (
          <p className="conversation-empty">No messages yet. Say hello!</p>
        )}
        {messages.map((msg) => {
          const mine = msg.sender === user.id
          return (
            <div key={msg.id} className={`message-bubble ${mine ? 'mine' : 'theirs'}`}>
              <p className="message-text">{msg.text}</p>
              <span className="message-time">
                {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      <form className="conversation-input-row" onSubmit={handleSend}>
        <input
          className="conversation-input"
          type="text"
          placeholder="Type a message…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={sending}
        />
        <button className="conversation-send" type="submit" disabled={sending || !text.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
