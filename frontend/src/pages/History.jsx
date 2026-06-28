import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getHistory, getReport, deleteReport } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import LanguageBadge  from '../components/LanguageBadge'
import { useAppToast } from '../App'

function gradeColor(score) {
  if (score >= 80) return '#22d3a5'
  if (score >= 65) return '#a3e635'
  if (score >= 50) return '#fbbf24'
  if (score >= 35) return '#fb923c'
  return '#f4606c'
}

function gradeLabel(score) {
  if (score >= 90) return 'A+'
  if (score >= 80) return 'A'
  if (score >= 70) return 'B+'
  if (score >= 60) return 'B'
  if (score >= 50) return 'C+'
  if (score >= 40) return 'C'
  if (score >= 30) return 'D'
  return 'F'
}

export default function History() {
  const [history,  setHistory]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [deleting, setDeleting] = useState(null)
  const navigate  = useNavigate()
  const addToast  = useAppToast()

  useEffect(() => {
    getHistory()
      .then(setHistory)
      .catch((err) => setError(err.message ?? 'Failed to load history.'))
      .finally(() => setLoading(false))
  }, [])

  async function viewReport(id) {
    try {
      const report = await getReport(id)
      navigate('/dashboard', { state: { report } })
    } catch (err) {
      addToast?.(err.message ?? 'Could not load this report.', 'error')
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this report?')) return
    setDeleting(id)
    try {
      await deleteReport(id)
      setHistory((h) => h.filter((item) => item.id !== id))
      addToast?.('Report deleted.', 'success')
    } catch (err) {
      addToast?.(err.message ?? 'Failed to delete report.', 'error')
    } finally {
      setDeleting(null)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3 text-center px-4">
        <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"
             style={{ color: 'var(--danger)' }}>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-sm" style={{ color: 'var(--danger)' }}>{error}</p>
        <button onClick={() => window.location.reload()}
          className="text-xs underline" style={{ color: 'var(--muted)' }}>Retry</button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
          Review History
        </h2>
        <span className="text-xs px-2.5 py-1 rounded-full"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--muted)' }}>
          {history.length} report{history.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Empty state */}
      {history.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
          <svg className="w-14 h-14" fill="none" stroke="currentColor" viewBox="0 0 24 24"
               style={{ color: 'var(--border)' }}>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>No reviews yet.</p>
          <button onClick={() => navigate('/')} className="btn-primary px-5 py-2.5 text-sm">
            Analyze a Repository
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {history.map((item) => {
            const score = Math.round(item.score)
            const gc    = gradeColor(score)
            const gl    = item.grade ?? gradeLabel(score)

            return (
              <div key={item.id}
                className="card px-4 py-4 sm:px-5 sm:py-4 flex flex-col sm:flex-row sm:items-center gap-4
                           hover:border-[#3a4060] transition-colors">

                {/* Score badge */}
                <div className="flex-shrink-0 w-14 text-center">
                  <div className="text-2xl font-black tabular-nums leading-none" style={{ color: gc }}>
                    {score}
                  </div>
                  <div className="text-xs font-bold mt-0.5" style={{ color: gc }}>{gl}</div>
                </div>

                {/* Divider on sm+ */}
                <div className="hidden sm:block w-px h-10 self-center"
                     style={{ background: 'var(--border)' }} />

                {/* Repo info */}
                <div className="flex-1 min-w-0 space-y-1">
                  <p className="font-semibold text-sm truncate" style={{ color: 'var(--text)' }}>
                    {item.repo_name}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--muted)' }}>
                    {new Date(item.created_at).toLocaleString()}
                  </p>
                  {item.primary_language && (
                    <div className="pt-0.5">
                      <LanguageBadge language={item.primary_language} />
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2 flex-shrink-0">
                  <button onClick={() => viewReport(item.id)}
                    className="btn-primary px-3 py-1.5 text-xs">
                    View
                  </button>
                  <button onClick={() => handleDelete(item.id)}
                    disabled={deleting === item.id}
                    className="btn-ghost px-3 py-1.5 text-xs disabled:opacity-40"
                    style={{ borderColor: 'rgba(244,96,108,0.3)', color: '#f4606c' }}>
                    {deleting === item.id ? '…' : 'Delete'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
