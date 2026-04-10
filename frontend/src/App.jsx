import { useState } from 'react'
import { AuthProvider, useAuth } from './AuthContext'
import Login from './Login'
import Register from './Register'
import Layout from './Layout'
import Gallery from './Gallery'
import LikedArt from './LikedArt'
import Messages from './Messages'
import TasteProfile from './TasteProfile'
import './App.css'

function AuthGate() {
  const { token } = useAuth()
  const [showRegister, setShowRegister] = useState(false)
  const [view, setView] = useState('explore')

  if (!token) {
    if (showRegister) return <Register onSwitch={() => setShowRegister(false)} />
    return <Login onSwitch={() => setShowRegister(true)} />
  }

  function renderView() {
    if (view === 'likes') return <LikedArt />
    if (view === 'taste') return <TasteProfile />
    if (view === 'messages') return <Messages />
    return <Gallery />
  }

  return (
    <Layout activeTab={view} onNavigate={setView}>
      {renderView()}
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
