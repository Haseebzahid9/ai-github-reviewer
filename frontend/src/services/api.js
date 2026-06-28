import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 75000,           // 75 s — pipeline timeout is 60 s + headroom
  headers: { 'Content-Type': 'application/json' },
})

// ---------------------------------------------------------------------------
// Response error interceptor — normalise every error into a plain Error
// with a human-readable .message and optional .code / .status fields.
// ---------------------------------------------------------------------------

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.code === 'ECONNABORTED' || err.message?.toLowerCase().includes('timeout')) {
      const e = new Error(
        'The request timed out. The repository may be very large — please try again.'
      )
      e.code   = 'TIMEOUT'
      e.status = 504
      return Promise.reject(e)
    }

    if (!err.response) {
      const e = new Error(
        'Cannot reach the server. Check your internet connection or try again later.'
      )
      e.code   = 'NETWORK_ERROR'
      e.status = 0
      return Promise.reject(e)
    }

    const { status, data } = err.response

    // GitHub rate-limit surface
    if (status === 429) {
      const reset = data?.reset_at
      const mins  = reset
        ? `Try again at ${new Date(reset).toLocaleTimeString()}.`
        : 'Please wait a few minutes before retrying.'
      const e = new Error(`GitHub API rate limit reached. ${mins}`)
      e.code   = 'RATE_LIMIT'
      e.status = 429
      return Promise.reject(e)
    }

    // Extract the most descriptive message from FastAPI's error shape
    const message =
      data?.detail ||
      data?.error  ||
      data?.message ||
      `Request failed with status ${status}.`

    const e = new Error(message)
    e.code   = data?.code  || `HTTP_${status}`
    e.status = status
    e.data   = data
    return Promise.reject(e)
  }
)

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * Run the full review pipeline for a GitHub repository URL.
 * @param {string} url  — full https://github.com/owner/repo URL
 * @returns {Promise<object>}  full report dict from the backend
 */
export const analyzeRepo = (url) =>
  api.post('/api/review', { repo_url: url }).then((r) => r.data)

/** Backward-compat alias */
export const reviewRepo = analyzeRepo

/**
 * Fetch the last 20 review summaries.
 * @returns {Promise<Array>}
 */
export const getHistory = () =>
  api.get('/api/history').then((r) => r.data)

/**
 * Load the full saved report by database ID.
 * @param {number} id
 * @returns {Promise<object>}
 */
export const getReport = (id) =>
  api.get(`/api/report/${id}`).then((r) => r.data)

/**
 * Delete a saved report.
 * @param {number} id
 * @returns {Promise<{deleted: boolean, id: number}>}
 */
export const deleteReport = (id) =>
  api.delete(`/api/history/${id}`).then((r) => r.data)

/**
 * Trigger a PDF download for the given report ID.
 * Uses native fetch so we can handle the binary blob directly.
 * @param {number} id
 * @param {string} filename  — suggested download filename
 */
export async function downloadReport(id, filename = 'report.pdf') {
  const url = `${BASE_URL}/api/report/${id}/download`
  const res = await fetch(url)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const msg  = body?.detail || body?.error || `Download failed (${res.status})`
    const e    = new Error(msg)
    e.status   = res.status
    throw e
  }
  const blob  = await res.blob()
  const href  = URL.createObjectURL(blob)
  const a     = document.createElement('a')
  a.href      = href
  a.download  = filename
  a.click()
  URL.revokeObjectURL(href)
}

export default api
