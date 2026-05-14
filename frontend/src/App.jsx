import { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Common/Navbar'
import HomePage from './pages/HomePage'
import StartMeetingPage from './pages/StartMeetingPage'
import MeetingDetailsPage from './pages/MeetingDetailsPage'
import PeoplePage from './pages/PeoplePage'
import PersonProfilePage from './pages/PersonProfilePage'
import SettingsPage from './pages/SettingsPage'
import LoadingSpinner from './components/Common/LoadingSpinner'

function App() {
  const [backendReady, setBackendReady] = useState(false)
  const [statusMessage, setStatusMessage] = useState('Connecting to backend server...')

  useEffect(() => {
    let cancelled = false
    let retryTimer = null

    const checkBackendHealth = async (attempt = 1) => {
      try {
        const response = await fetch('/api/health', { cache: 'no-store' })

        // 503 means our Vite proxy error handler fired — backend not up yet
        if (response.status === 503) {
          throw new Error('starting')
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        if (!cancelled) {
          setBackendReady(true)
        }
      } catch (error) {
        if (cancelled) return

        const isStarting = error.message === 'starting' || error.message.includes('Failed to fetch')
        const message = isStarting
          ? `Backend is initializing, please wait... (attempt ${attempt})`
          : `Backend error: ${error.message}. Retrying...`

        setStatusMessage(message)

        // Exponential backoff capped at 5 s
        const delay = Math.min(1000 * Math.pow(1.5, attempt - 1), 5000)
        retryTimer = setTimeout(() => checkBackendHealth(attempt + 1), delay)
      }
    }

    checkBackendHealth()

    return () => {
      cancelled = true
      if (retryTimer) clearTimeout(retryTimer)
    }
  }, [])

  if (!backendReady) {
    return (
      <div style={{
        minHeight: '100vh',
        background: '#f9fafb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: '16px',
        fontFamily: 'Inter, system-ui, sans-serif'
      }}>
        <LoadingSpinner size="xl" text="Starting Meeting Assistant..." />
        <p style={{ color: '#6b7280', fontSize: '0.875rem', textAlign: 'center', maxWidth: '320px' }}>
          {statusMessage}
        </p>
        <p style={{ color: '#9ca3af', fontSize: '0.75rem' }}>
          Make sure the backend server is running on port 5000.
        </p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/start-meeting" element={<StartMeetingPage />} />
          <Route path="/meeting/:id" element={<MeetingDetailsPage />} />
          <Route path="/people" element={<PeoplePage />} />
          <Route path="/person/:id" element={<PersonProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
