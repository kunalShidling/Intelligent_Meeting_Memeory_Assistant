import { defineConfig, createLogger } from 'vite'
import react from '@vitejs/plugin-react'

// Custom logger: suppress the 'http proxy error: ECONNREFUSED' spam that
// appears while the backend is still starting up. All other messages pass through.
const logger = createLogger()
const originalWarn = logger.warn.bind(logger)
logger.warn = (msg, opts) => {
  if (msg.includes('http proxy error') && msg.includes('ECONNREFUSED')) return
  originalWarn(msg, opts)
}
const originalError = logger.error.bind(logger)
logger.error = (msg, opts) => {
  if (msg.includes('http proxy error') && msg.includes('ECONNREFUSED')) return
  originalError(msg, opts)
}

export default defineConfig({
  plugins: [react()],
  customLogger: logger,
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, req, res) => {
            // Backend not yet available – return a clean 503 instead of crashing
            if (!res.headersSent) {
              res.writeHead(503, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({
                error: 'Backend server is starting up. Please wait...',
                code: err.code
              }))
            }
          })
        }
      }
    }
  }
})
