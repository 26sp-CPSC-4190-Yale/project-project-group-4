'use strict';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../lib/constants';
const NOTIF_POLL_INTERVAL = 30000;

export default function Layout({ activeTab, onNavigate, children }) {
  const { user, logout, token, authFetch } = useAuth();
  const [notifCount, setNotifCount] = useState(0);
  const [pulse, setPulse] = useState(false);
  const prevCountRef = useRef(null);

  useEffect(() => {
    let pulseTimeout = null;
    async function fetchNotifications() {
      const res = await authFetch(`${BASE_URL}/api/notifications/`);
      if (res.ok) {
        const data = await res.json();
        const next = data.new_matches + data.pending_requests;
        if (prevCountRef.current !== null && next > prevCountRef.current) {
          setPulse(true);
          if (pulseTimeout) clearTimeout(pulseTimeout);
          pulseTimeout = setTimeout(() => setPulse(false), 400);
        }
        prevCountRef.current = next;
        setNotifCount(next);
      }
    }

    fetchNotifications();
    const interval = setInterval(fetchNotifications, NOTIF_POLL_INTERVAL);
    return () => {
      clearInterval(interval);
      if (pulseTimeout) clearTimeout(pulseTimeout);
    };
  }, [token]);

  function handleMessagesTab() {
    setNotifCount(0);
    prevCountRef.current = 0;
    onNavigate('messages');
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
            {notifCount > 0 && (
              <span className={`notif-badge${pulse ? ' notif-badge-pulse' : ''}`}>{notifCount}</span>
            )}
          </span>
          Messages
        </button>
      </footer>
    </>
  );
}
