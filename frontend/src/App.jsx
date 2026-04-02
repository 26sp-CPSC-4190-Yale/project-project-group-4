import { useState } from 'react'
import { AuthProvider, useAuth } from './AuthContext'
import Login from './Login'
import Register from './Register'
import Layout from './Layout'
import Gallery from './Gallery'
import LikedArt from './LikedArt'
import './App.css'

function AuthGate() {
  const { token } = useAuth()
  const [showRegister, setShowRegister] = useState(false)
  const [view, setView] = useState('explore')

  if (!token) {
    if (showRegister) return <Register onSwitch={() => setShowRegister(false)} />
    return <Login onSwitch={() => setShowRegister(true)} />
  }

  return (
    <Layout activeTab={view} onNavigate={setView}>
      {view === 'likes' ? <LikedArt /> : <Gallery />}
    </Layout>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  )
}
