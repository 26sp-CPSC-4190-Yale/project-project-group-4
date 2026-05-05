'use strict';

import { createContext, useContext, useState, useCallback } from 'react';
import { BASE_URL } from '../lib/constants';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });

  // Clears all local auth state — called on explicit logout and on token expiry.
  const _clearAuth = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  }, []);

  async function login(username, password) {
    const res = await fetch(`${BASE_URL}/api/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Login failed');
    }
    const data = await res.json();
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
  }

  async function register(username, email, password) {
    const res = await fetch(`${BASE_URL}/api/auth/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      const msg = Object.values(err).flat().join(' ');
      throw new Error(msg || 'Registration failed');
    }
    const data = await res.json();
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
  }

  async function logout() {
    try {
      await fetch(`${BASE_URL}/api/auth/logout/`, {
        method: 'POST',
        headers: { Authorization: `Token ${token}` },
      });
    } catch { /* server logout is best-effort */ }
    _clearAuth();
  }

  /**
   * Change the current user's password.
   * On success the old token is invalidated server-side; the new token
   * returned by the server is stored so the user stays logged in.
   *
   * Throws an Error with a human-readable message on failure.
   */
  async function changePassword(currentPassword, newPassword) {
    const res = await fetch(`${BASE_URL}/api/auth/change-password/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Token ${token}`,
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      const msg = Array.isArray(err.error) ? err.error.join(' ') : (err.error || 'Password change failed');
      throw new Error(msg);
    }
    const data = await res.json();
    // Store the fresh token so the user stays authenticated
    localStorage.setItem('token', data.token);
    setToken(data.token);
  }

  /**
   * Convenience wrapper for authenticated API calls.
   * Automatically attaches the Authorization header and, when the server
   * returns 401 (expired or revoked token), clears auth state so the app
   * redirects to login.
   */
  async function authFetch(url, options = {}) {
    const res = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: `Token ${token}`,
      },
    });
    if (res.status === 401) {
      _clearAuth();
    }
    return res;
  }

  return (
    <AuthContext.Provider value={{ token, user, login, register, logout, changePassword, authFetch }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
