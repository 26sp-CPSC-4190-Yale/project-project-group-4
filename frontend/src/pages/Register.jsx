import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function Register({ onSwitch }) {
  const { register } = useAuth()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await register(username, email, password)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-wrapper">
        <div className="auth-branding">
          <h1>YArt Match</h1>
          <p>Discover art, one swipe at a time</p>
        </div>

        <div className="auth-card">
          <h2>Create account</h2>
          <form onSubmit={handleSubmit} className="auth-form">
            <input
              className="auth-input"
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
            />
            <input
              className="auth-input"
              type="email"
              placeholder="Email (optional)"
              value={email}
              onChange={e => setEmail(e.target.value)}
            />
            <input
              className="auth-input"
              type="password"
              placeholder="Password (min 8 characters)"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={8}
            />
            {error && <p className="auth-error">{error}</p>}
            <button className="auth-submit" type="submit" disabled={loading}>
              {loading ? 'Creating account...' : 'Register'}
            </button>
          </form>
        </div>

        <p className="auth-switch">
          Already have an account?{' '}
          <button onClick={onSwitch}>Log in</button>
        </p>
      </div>
    </div>
  )
}
