import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { BASE_URL } from '../lib/constants'

export default function Profile() {
  const { token, user, login, changePassword, authFetch } = useAuth()
  const [stats, setStats] = useState(null)
  const [bio, setBio] = useState('')
  const [hasPhoto, setHasPhoto] = useState(false)
  const [photoUrl, setPhotoUrl] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const fileInputRef = useRef(null)

  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [pwError, setPwError] = useState(null)
  const [pwSuccess, setPwSuccess] = useState(null)

  useEffect(() => {
    async function fetchProfile() {
      try {
        const [statsRes, profileRes] = await Promise.all([
          authFetch(`${BASE_URL}/api/profile/stats/`),
          authFetch(`${BASE_URL}/api/profile/me/`),
        ])
        if (!statsRes.ok || !profileRes.ok) throw new Error()
        const [statsData, profileData] = await Promise.all([
          statsRes.json(),
          profileRes.json(),
        ])
        setStats(statsData)
        setBio(profileData.bio || '')
        setHasPhoto(profileData.has_photo)
        if (profileData.has_photo) {
          setPhotoUrl(`${BASE_URL}/api/profile/photo/${user.id}/?t=${Date.now()}`)
        }
      } catch {
        setError('Failed to load profile data.')
      } finally {
        setLoading(false)
      }
    }
    fetchProfile()
  }, [token, user.id])

  async function handleSave() {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const formData = new FormData()
      formData.append('bio', bio)
      const res = await authFetch(`${BASE_URL}/api/profile/me/`, {
        method: 'PATCH',
        body: formData,
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error || 'Save failed')
      }
      setSuccess('Profile saved!')
      setTimeout(() => setSuccess(null), 2000)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handlePhotoChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setSaving(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('photo', file)
      const res = await authFetch(`${BASE_URL}/api/profile/me/`, {
        method: 'PATCH',
        body: formData,
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error || 'Upload failed')
      }
      setHasPhoto(true)
      setPhotoUrl(`${BASE_URL}/api/profile/photo/${user.id}/?t=${Date.now()}`)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const initial = user?.username?.[0]?.toUpperCase() ?? '?'

  const memberSince = stats?.date_joined
    ? new Date(stats.date_joined).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
      })
    : null

  const likeRatePercent =
    stats && (stats.total_likes + stats.total_passes) > 0
      ? Math.round(stats.like_rate * 100)
      : null

  return (
    <div className="profile-page">
      <h2 className="profile-title">Profile</h2>

      <section className="profile-account">
        <button
          type="button"
          className="profile-avatar-btn"
          onClick={() => fileInputRef.current?.click()}
          aria-label="Upload profile photo"
        >
          {photoUrl ? (
            <img
              className="profile-avatar-img"
              src={photoUrl}
              alt="Profile"
              onError={() => setPhotoUrl(null)}
            />
          ) : (
            <div className="profile-avatar">{initial}</div>
          )}
          <span className="profile-avatar-overlay">Edit</span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handlePhotoChange}
          hidden
        />
        <div className="profile-account-info">
          <p className="profile-username">{user?.username}</p>
          {user?.email && <p className="profile-email">{user.email}</p>}
          {memberSince && (
            <p className="profile-since">Member since {memberSince}</p>
          )}
        </div>
      </section>

      <section className="profile-stats">
        <div className="profile-stat-card">
          {loading ? (
            <div className="profile-skeleton profile-skeleton-stat" />
          ) : (
            <p className="profile-stat-value">{stats?.total_likes ?? 0}</p>
          )}
          <p className="profile-stat-label">Total Likes</p>
        </div>
        <div className="profile-stat-card">
          {loading ? (
            <div className="profile-skeleton profile-skeleton-stat" />
          ) : (
            <p className="profile-stat-value">{stats?.total_passes ?? 0}</p>
          )}
          <p className="profile-stat-label">Total Passes</p>
        </div>
        <div className="profile-stat-card">
          {loading ? (
            <div className="profile-skeleton profile-skeleton-stat" />
          ) : (
            <p className="profile-stat-value">
              {likeRatePercent == null ? '—' : `${likeRatePercent}%`}
            </p>
          )}
          <p className="profile-stat-label">Like Rate</p>
        </div>
      </section>

      <section className="profile-bio-section">
        <h3 className="profile-section-title">About You</h3>
        <textarea
          className="profile-bio-input"
          value={bio}
          onChange={e => setBio(e.target.value)}
          placeholder="Tell others about yourself..."
          maxLength={500}
          rows={4}
        />
        <div className="profile-bio-footer">
          <span className="profile-bio-count">{bio.length}/500</span>
          <button
            className="profile-save-btn"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </section>

      {error && <p className="error-message">{error}</p>}
      {success && <p className="success-message">{success}</p>}

      <section className="profile-password-section">
        <h3 className="profile-section-title">Change Password</h3>
        <input
          className="profile-pw-input"
          type="password"
          placeholder="Current password"
          value={currentPw}
          onChange={e => setCurrentPw(e.target.value)}
        />
        <input
          className="profile-pw-input"
          type="password"
          placeholder="New password (min 8 characters)"
          value={newPw}
          onChange={e => setNewPw(e.target.value)}
        />
        <input
          className="profile-pw-input"
          type="password"
          placeholder="Confirm new password"
          value={confirmPw}
          onChange={e => setConfirmPw(e.target.value)}
        />
        {pwError && <p className="error-message">{pwError}</p>}
        {pwSuccess && <p className="success-message">{pwSuccess}</p>}
        <button
          className="profile-save-btn"
          disabled={pwSaving}
          onClick={async () => {
            setPwError(null)
            setPwSuccess(null)
            if (newPw !== confirmPw) { setPwError('Passwords do not match'); return }
            if (newPw.length < 8) { setPwError('New password must be at least 8 characters'); return }
            setPwSaving(true)
            try {
              await changePassword(currentPw, newPw)
              setCurrentPw('')
              setNewPw('')
              setConfirmPw('')
              setPwSuccess('Password changed!')
              setTimeout(() => setPwSuccess(null), 3000)
            } catch (e) {
              setPwError(e.message)
            } finally {
              setPwSaving(false)
            }
          }}
        >
          {pwSaving ? 'Changing...' : 'Change Password'}
        </button>
      </section>
    </div>
  )
}
