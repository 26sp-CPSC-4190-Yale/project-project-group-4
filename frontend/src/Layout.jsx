import { useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import { BASE_URL } from './constants'
const NOTIF_POLL_INTERVAL = 30000

export default function Layout({ activeTab, onNavigate, children }) {
  const { user, logout, token } = useAuth()
  const [notifCount, setNotifCount] = useState(0)

  useEffect(() => {
    async function fetchNotifications() {
      const res = await fetch(`${BASE_URL}/api/notifications/`, {
        headers: { Authorization: `Token ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setNotifCount(data.new_matches + data.pending_requests)
      }
    }

    fetchNotifications()
    const interval = setInterval(fetchNotifications, NOTIF_POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [token])

  function handleMessagesTab() {
    setNotifCount(0)
    onNavigate('messages')
  }

  return (
    <>
      <nav className="top-nav">
        <h1 className="top-nav-brand">YArt Match</h1>
        <div className="top-nav-right">
          <button
            type="button"
            className={`top-nav-user ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => onNavigate('profile')}
          >
            {user.username}
          </button>
          <button className="top-nav-logout" onClick={logout}>Log out</button>
        </div>
      </nav>

      <main className="page-content">
        {children}
      </main>

      <footer className="tab-bar">
        <button
          className={`tab-bar-item ${activeTab === 'explore' ? 'active' : ''}`}
          onClick={() => onNavigate('explore')}
        >
          <span className="tab-bar-icon">◆</span>
          Explore
        </button>
        <button
          className={`tab-bar-item ${activeTab === 'likes' ? 'active' : ''}`}
          onClick={() => onNavigate('likes')}
        >
          <span className="tab-bar-icon">♥</span>
          My Likes
        </button>
        <button
          className={`tab-bar-item ${activeTab === 'taste' ? 'active' : ''}`}
          onClick={() => onNavigate('taste')}
        >
          <span className="tab-bar-icon">★</span>
          Taste
        </button>
        <button
          className={`tab-bar-item ${activeTab === 'messages' ? 'active' : ''}`}
          onClick={handleMessagesTab}
        >
          <span className="tab-bar-icon tab-bar-icon-notif">
            ✉
            {notifCount > 0 && <span className="notif-badge">{notifCount}</span>}
          </span>
          Messages
        </button>
      </footer>
    </>
  )
}
