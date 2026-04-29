import { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Layout from './components/Layout'
import Gallery from './pages/Gallery'
import Messages from './pages/Messages'
import TasteProfile from './pages/TasteProfile'
import Profile from './pages/Profile'
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
    if (view === 'taste') return <TasteProfile />
    if (view === 'messages') return <Messages />
    if (view === 'profile') return <Profile />
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
