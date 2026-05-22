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
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="w-full max-w-md rounded-2xl border border-amber-100 bg-white/85 backdrop-blur p-8 text-center shadow-xl">
          <LoadingSpinner size="xl" text="Starting Meeting Assistant..." />
          <p className="mt-4 text-sm text-slate-600">
            {statusMessage}
          </p>
          <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-400">
            Ensure the backend runs on port 5000.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen text-slate-900 relative overflow-hidden">
      <div className="pointer-events-none absolute -top-32 right-0 h-80 w-80 rounded-full bg-teal-200/40 blur-3xl" />
      <div className="pointer-events-none absolute top-1/3 -left-24 h-72 w-72 rounded-full bg-amber-200/40 blur-3xl" />
      <Navbar />
      <main className="relative z-10 mx-auto w-full max-w-6xl px-6 py-10">
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
