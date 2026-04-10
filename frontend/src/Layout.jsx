import { useAuth } from './AuthContext'

/**
 * Shared page layout: top nav + content + bottom tab bar.
 * Used by both Gallery and LikedArt views.
 */
export default function Layout({ activeTab, onNavigate, children }) {
  const { user, logout } = useAuth()

  return (
    <>
      <nav className="top-nav">
        <h1 className="top-nav-brand">YArt Match</h1>
        <div className="top-nav-right">
          <span className="top-nav-user">{user.username}</span>
          <button className="top-nav-logout" onClick={logout}>Log out</button>
        </div>
      </nav>

      {children}

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
          className={`tab-bar-item ${activeTab === 'messages' ? 'active' : ''}`}
          onClick={() => onNavigate('messages')}
        >
          <span className="tab-bar-icon">✉</span>
          Messages
        </button>
      </footer>
    </>
  )
}
