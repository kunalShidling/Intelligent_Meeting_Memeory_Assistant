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
import api from './services/api'

function App() {
  const [backendReady, setBackendReady] = useState(false)
  const [backendError, setBackendError] = useState(false)

  useEffect(() => {
    checkBackendHealth()
  }, [])

  const checkBackendHealth = async () => {
    try {
      // Try to connect to backend health endpoint
      await api.get('/health')
      setBackendReady(true)
    } catch (error) {
      console.warn('Backend not ready yet, will retry...')
      setBackendError(true)
      // Even if health check fails, allow the app to load
      // The retry logic in api.js will handle subsequent requests
      setTimeout(() => {
        setBackendReady(true)
      }, 2000)
    }
  }

  if (!backendReady) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="xl" text="Connecting to backend server..." />
          {backendError && (
            <p className="mt-4 text-sm text-gray-600">
              Backend is initializing. This may take a moment...
            </p>
          )}
        </div>
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
