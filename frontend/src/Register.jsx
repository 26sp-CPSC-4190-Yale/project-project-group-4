import { useState } from 'react'
import { useAuth } from './AuthContext'

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
    <div style={styles.container}>
      <h2>Create Account</h2>
      <form onSubmit={handleSubmit} style={styles.form}>
        <input
          style={styles.input}
          type="text"
          placeholder="Username"
          value={username}
          onChange={e => setUsername(e.target.value)}
          required
        />
        <input
          style={styles.input}
          type="email"
          placeholder="Email (optional)"
          value={email}
          onChange={e => setEmail(e.target.value)}
        />
        <input
          style={styles.input}
          type="password"
          placeholder="Password (min 8 characters)"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          minLength={8}
        />
        {error && <p style={styles.error}>{error}</p>}
        <button style={styles.button} type="submit" disabled={loading}>
          {loading ? 'Creating account…' : 'Register'}
        </button>
      </form>
      <p>
        Already have an account?{' '}
        <button style={styles.link} onClick={onSwitch}>Login</button>
      </p>
    </div>
  )
}

const styles = {
  container: { maxWidth: 360, margin: '80px auto', padding: 24, border: '1px solid #ccc', borderRadius: 8 },
  form: { display: 'flex', flexDirection: 'column', gap: 12 },
  input: { padding: '8px 12px', fontSize: 14, borderRadius: 4, border: '1px solid #ccc' },
  button: { padding: '10px 0', fontSize: 14, background: '#333', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' },
  error: { color: 'red', margin: 0, fontSize: 13 },
  link: { background: 'none', border: 'none', color: '#0066cc', cursor: 'pointer', textDecoration: 'underline', padding: 0, fontSize: 'inherit' },
}
