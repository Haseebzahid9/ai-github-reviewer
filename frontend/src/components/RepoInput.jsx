import { useState } from 'react'

const EXAMPLES = [
  { label: 'fastapi',  url: 'https://github.com/tiangolo/fastapi' },
  { label: 'react',    url: 'https://github.com/facebook/react' },
  { label: 'vscode',   url: 'https://github.com/microsoft/vscode' },
]

export default function RepoInput({ onSubmit, loading }) {
  const [url, setUrl] = useState('')

  const submit = (e) => {
    e.preventDefault()
    const trimmed = url.trim()
    if (trimmed) onSubmit(trimmed)
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={submit}>
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repository"
            disabled={loading}
            className="flex-1 px-4 py-3 rounded-xl text-sm outline-none transition-all disabled:opacity-40"
            style={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              boxShadow: 'none',
            }}
            onFocus={(e) => {
              e.target.style.borderColor = 'var(--accent)'
              e.target.style.boxShadow   = '0 0 0 3px rgba(124,92,252,0.2)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = 'var(--border)'
              e.target.style.boxShadow   = 'none'
            }}
          />
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="btn-primary px-5 py-3 text-sm flex items-center gap-2 whitespace-nowrap"
          >
            {loading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Analyzing&hellip;
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Analyze
              </>
            )}
          </button>
        </div>
      </form>

      {/* Quick-pick chips */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-xs" style={{ color: 'var(--muted)' }}>Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.url}
            onClick={() => setUrl(ex.url)}
            disabled={loading}
            className="text-xs px-3 py-1 rounded-full transition-all disabled:opacity-40"
            style={{
              background: 'rgba(124,92,252,0.1)',
              border: '1px solid rgba(124,92,252,0.25)',
              color: 'var(--accent-lt)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(124,92,252,0.2)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(124,92,252,0.1)'
            }}
          >
            {ex.label}
          </button>
        ))}
      </div>
    </div>
  )
}
