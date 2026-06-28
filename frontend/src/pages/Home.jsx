import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import RepoInput from '../components/RepoInput'
import { analyzeRepo } from '../services/api'

const STEPS = [
  { icon: '⬡', label: 'Validating repository',     ms: 2000,  pct: 8  },
  { icon: '⬡', label: 'Fetching repository data',  ms: 5000,  pct: 25 },
  { icon: '⬡', label: 'Analyzing source code',     ms: 10000, pct: 55 },
  { icon: '⬡', label: 'Running AI review',         ms: 8000,  pct: 78 },
  { icon: '⬡', label: 'Calculating scores',        ms: 2000,  pct: 92 },
  { icon: '⬡', label: 'Report ready',              ms: 1000,  pct: 100 },
]

const FEATURES = [
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    title: '5-Dimension Scoring',
    desc: 'Structure, Documentation, Code Quality, Security, and AI Assessment weighted into a single grade.',
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
          d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
    title: '14+ Languages',
    desc: 'Python, JS/TS, Java, C/C++, Go, Rust, PHP, Swift, Kotlin, SQL, HTML, CSS and more.',
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    title: 'Gemini AI Insights',
    desc: 'Deep project overview, tech-stack assessment, strengths, weaknesses, and actionable next steps.',
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
    title: 'Security Detection',
    desc: 'Identifies hardcoded secrets, injection risks, deprecated APIs, missing integrity checks, and more.',
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    title: 'README Analysis',
    desc: 'Scores 14 README sections including installation, usage, contributing guide, and badges.',
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
    ),
    title: 'PDF Export',
    desc: 'Download the full 6-page analysis report as a formatted PDF.',
  },
]

function ProgressLoader({ stepIdx }) {
  const step = STEPS[Math.min(stepIdx, STEPS.length - 1)]

  return (
    <div className="w-full max-w-md mx-auto py-6 space-y-5 animate-fade-in">
      <div className="space-y-1.5">
        {STEPS.map((s, i) => {
          const done    = i < stepIdx
          const current = i === stepIdx
          return (
            <div key={i}
              className="flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200"
              style={{
                background: current ? 'rgba(124,92,252,0.12)' : 'transparent',
                opacity: done ? 0.45 : current ? 1 : 0.3,
              }}
            >
              {/* Status dot */}
              <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                {done ? (
                  <svg className="w-4 h-4" fill="none" stroke="#22d3a5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7"/>
                  </svg>
                ) : current ? (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"
                       style={{ color: 'var(--accent)' }}>
                    <circle className="opacity-25" cx="12" cy="12" r="10"
                            stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                ) : (
                  <span className="w-2 h-2 rounded-full" style={{ background: 'var(--border)' }} />
                )}
              </span>

              <span className="text-sm font-medium"
                    style={{ color: current ? 'var(--accent-lt)' : done ? 'var(--muted)' : 'var(--muted)' }}>
                {s.label}
              </span>
              {done && (
                <span className="ml-auto text-xs" style={{ color: 'var(--success)' }}>done</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Progress track */}
      <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${step.pct}%`, background: 'var(--accent)' }}
        />
      </div>
      <p className="text-center text-xs tabular-nums" style={{ color: 'var(--muted)' }}>
        {step.pct}%
      </p>
    </div>
  )
}

export default function Home() {
  const [loading, setLoading] = useState(false)
  const [stepIdx, setStepIdx] = useState(0)
  const [error,   setError]   = useState(null)
  const navigate  = useNavigate()
  const timerRef  = useRef(null)

  useEffect(() => () => clearTimeout(timerRef.current), [])

  function scheduleStep(idx) {
    if (idx >= STEPS.length) return
    timerRef.current = setTimeout(() => {
      setStepIdx(idx + 1)
      scheduleStep(idx + 1)
    }, STEPS[idx].ms)
  }

  async function handleSubmit(url) {
    setError(null)
    setLoading(true)
    setStepIdx(0)
    scheduleStep(0)

    try {
      const report = await analyzeRepo(url)
      clearTimeout(timerRef.current)
      setStepIdx(STEPS.length - 1)
      await new Promise((r) => setTimeout(r, 500))
      navigate('/dashboard', { state: { report } })
    } catch (err) {
      clearTimeout(timerRef.current)
      setError(err.message ?? 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center px-4 py-14 sm:py-20 space-y-20">

      {/* Hero */}
      <section className="max-w-2xl w-full text-center space-y-7 animate-fade-in">
        {/* Eyebrow */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold"
             style={{ background: 'rgba(124,92,252,0.15)', color: 'var(--accent-lt)', border: '1px solid rgba(124,92,252,0.3)' }}>
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          Powered by Google Gemini &amp; FastAPI
        </div>

        <h1 className="text-4xl sm:text-5xl font-black leading-tight tracking-tight" style={{ color: 'var(--text)' }}>
          Instant code review for<br />
          <span style={{ color: 'var(--accent-lt)' }}>any GitHub repository</span>
        </h1>

        <p className="text-base sm:text-lg leading-relaxed" style={{ color: 'var(--muted)' }}>
          Paste a public repository URL and get a comprehensive quality score,
          multi-language static analysis, and AI-generated insights — all in under 60 seconds.
        </p>

        <RepoInput onSubmit={handleSubmit} loading={loading} />

        {loading && <ProgressLoader stepIdx={stepIdx} />}

        {!loading && error && (
          <div className="flex items-start gap-3 rounded-xl px-4 py-3 text-sm text-left animate-fade-in"
               style={{ background: 'rgba(244,96,108,0.1)', border: '1px solid rgba(244,96,108,0.3)', color: '#f4606c' }}>
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="font-semibold mb-0.5">Analysis failed</p>
              <p style={{ color: '#f4606c', opacity: 0.85 }}>{error}</p>
            </div>
          </div>
        )}
      </section>

      {/* Feature grid */}
      {!loading && (
        <section className="max-w-5xl w-full animate-slide-up">
          <p className="section-title text-center mb-6">What we analyze</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f) => (
              <div key={f.title}
                className="card p-5 flex flex-col gap-3 hover:border-[#3a4060] transition-colors">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                     style={{ background: 'rgba(124,92,252,0.15)', color: 'var(--accent-lt)' }}>
                  {f.icon}
                </div>
                <div>
                  <h3 className="font-semibold text-sm mb-1" style={{ color: 'var(--text)' }}>{f.title}</h3>
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--muted)' }}>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
