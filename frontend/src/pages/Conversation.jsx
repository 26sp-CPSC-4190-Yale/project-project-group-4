'use strict';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../lib/constants';
const POLL_INTERVAL = 4000;

function formatDateSeparator(date) {
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  const sameDay = (a, b) => a.toDateString() === b.toDateString();
  if (sameDay(date, today)) return 'Today';
  if (sameDay(date, yesterday)) return 'Yesterday';
  const daysAgo = (today - date) / (1000 * 60 * 60 * 24);
  if (daysAgo < 7) return date.toLocaleDateString([], { weekday: 'long' });
  const sameYear = date.getFullYear() === today.getFullYear();
  return date.toLocaleDateString([], sameYear
    ? { month: 'short', day: 'numeric' }
    : { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function Conversation({ otherUser, onBack, onUnmatch }) {
  const { user, authFetch } = useAuth();
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [unmatched, setUnmatched] = useState(false);
  const bottomRef = useRef(null);

  async function fetchMessages() {
    try {
      const res = await authFetch(`${BASE_URL}/api/messages/${otherUser.id}/`);
      if (res.status === 403) {
        setUnmatched(true);
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch { /* network error, will retry next poll */ }
  }

  useEffect(() => {
    if (unmatched) return;
    let interval = null;
    function start() {
      if (interval) return;
      fetchMessages();
      interval = setInterval(fetchMessages, POLL_INTERVAL);
    }
    function stop() {
      if (!interval) return;
      clearInterval(interval);
      interval = null;
    }
    function onVisibility() {
      if (document.hidden) stop(); else start();
    }
    if (!document.hidden) start();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [otherUser.id, unmatched]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;

    const pendingId = `pending-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const pendingMsg = {
      id: pendingId,
      sender: user.id,
      text: trimmed,
      timestamp: new Date().toISOString(),
      pending: true,
    };

    setMessages(prev => [...prev, pendingMsg]);
    setText('');
    setSending(true);

    let succeeded = false;
    try {
      const res = await authFetch(`${BASE_URL}/api/messages/${otherUser.id}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed }),
      });
      if (res.ok) {
        succeeded = true;
        await fetchMessages();
      }
    } catch { /* fall through to rollback */ }
    finally {
      if (!succeeded) {
        setMessages(prev => prev.filter(m => m.id !== pendingId));
        setText(trimmed);
      }
      setSending(false);
    }
  }

  async function handleUnmatch() {
    if (!confirm(`Unmatch with ${otherUser.username}? This will delete all messages.`)) return;
    const res = await authFetch(`${BASE_URL}/api/matches/${otherUser.id}/`, {
      method: 'DELETE',
    });
    if (res.ok) onUnmatch();
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
        {messages.map((msg, i) => {
          const mine = msg.sender === user.id;
          const ts = new Date(msg.timestamp);
          const prevTs = i > 0 ? new Date(messages[i - 1].timestamp) : null;
          const showSeparator = !prevTs || prevTs.toDateString() !== ts.toDateString();
          return (
            <div key={msg.id} className="message-row">
              {showSeparator && (
                <div className="conversation-date-separator">{formatDateSeparator(ts)}</div>
              )}
              <div className={`message-bubble ${mine ? 'mine' : 'theirs'}${msg.pending ? ' message-bubble-pending' : ''}`}>
                <p className="message-text">{msg.text}</p>
                <span className="message-time">
                  {ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {unmatched ? (
        <div className="conversation-ended">
          <p>This conversation is no longer available.</p>
          <button onClick={onBack}>Back to Messages</button>
        </div>
      ) : (
        <form className="conversation-input-row" onSubmit={handleSend}>
          <div className="conversation-input-wrapper">
            <input
              className="conversation-input"
              type="text"
              placeholder="Type a message…"
              value={text}
              onChange={(e) => setText(e.target.value.slice(0, 5000))}
              maxLength={5000}
              disabled={sending}
            />
            {text.length > 4500 && (
              <span className={`char-counter${text.length > 4900 ? ' char-counter-danger' : ''}`}>
                {text.length}/5000
              </span>
            )}
          </div>
          <button className="conversation-send" type="submit" disabled={sending || !text.trim()}>
            Send
          </button>
        </form>
      )}
    </div>
  );
}
