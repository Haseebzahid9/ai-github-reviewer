import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import AnalysisSection   from '../components/AnalysisSection'
import AIRecommendations from '../components/AIRecommendations'
import FileStructureTree from '../components/FileStructureTree'
import LanguageBadge     from '../components/LanguageBadge'
import { useAppToast }   from '../App'
import { downloadReport } from '../services/api'

const LANG_COLORS = [
  '#7c5cfc','#22d3a5','#f59e0b','#f4606c','#38bdf8',
  '#a78bfa','#34d399','#fb923c','#e879f9','#60a5fa',
]

function barColor(score) {
  if (score >= 80) return '#22d3a5'
  if (score >= 65) return '#a3e635'
  if (score >= 50) return '#fbbf24'
  if (score >= 35) return '#fb923c'
  return '#f4606c'
}

function gradeInfo(score) {
  if (score >= 90) return { grade: 'A+', color: '#22d3a5' }
  if (score >= 80) return { grade: 'A',  color: '#34d399' }
  if (score >= 70) return { grade: 'B+', color: '#a3e635' }
  if (score >= 60) return { grade: 'B',  color: '#fbbf24' }
  if (score >= 50) return { grade: 'C+', color: '#fb923c' }
  if (score >= 40) return { grade: 'C',  color: '#f97316' }
  if (score >= 30) return { grade: 'D',  color: '#f87171' }
  return             { grade: 'F',  color: '#f4606c' }
}

/* ── Stat card ── */
function StatCard({ label, value, icon }) {
  return (
    <div className="card px-4 py-4 flex items-center gap-3">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
           style={{ background: 'rgba(124,92,252,0.15)', color: 'var(--accent-lt)' }}>
        {icon}
      </div>
      <div className="min-w-0">
        <div className="font-bold text-xl leading-none tabular-nums" style={{ color: 'var(--text)' }}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--muted)' }}>{label}</div>
      </div>
    </div>
  )
}

/* ── SVG score ring ── */
function ScoreRing({ score, grade, gradeColor }) {
  const r    = 50
  const circ = 2 * Math.PI * r
  const dash = circ * (Math.min(score, 100) / 100)

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="124" height="124" className="-rotate-90">
        <circle cx="62" cy="62" r={r} fill="none" stroke="var(--border)" strokeWidth="8" />
        <circle cx="62" cy="62" r={r} fill="none"
          stroke={gradeColor} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(0.25,0.46,0.45,0.94)' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center leading-none gap-0.5">
        <span className="text-3xl font-black tabular-nums" style={{ color: 'var(--text)' }}>
          {Math.round(score)}
        </span>
        <span className="text-xs font-bold" style={{ color: gradeColor }}>{grade}</span>
      </div>
    </div>
  )
}

/* ── Dimension bar ── */
function DimBar({ label, score, weight }) {
  const pct = Math.round(score)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span style={{ color: 'var(--muted)' }}>{label}</span>
        <span className="font-semibold tabular-nums" style={{ color: 'var(--text)' }}>{pct}</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <div className="h-full rounded-full animate-bar"
             style={{ '--bar-width': `${pct}%`, background: barColor(pct) }} />
      </div>
      <p className="text-right" style={{ fontSize: 10, color: 'var(--muted)', opacity: 0.55 }}>
        weight {Math.round(weight * 100)}%
      </p>
    </div>
  )
}

/* ── Score card ── */
function ScoreCard({ finalScore }) {
  if (!finalScore) return null
  const { total_score, grade, badge, breakdown } = finalScore
  const { grade: g, color: gc } = gradeInfo(Math.round(total_score))
  const actualGrade = grade ?? g

  const LABELS = {
    structure:     'Project Structure',
    documentation: 'Documentation',
    code_quality:  'Code Quality',
    security:      'Security',
    ai_assessment: 'AI Assessment',
  }

  return (
    <div className="card p-6 animate-slide-up">
      <p className="section-title mb-5">Overall Score</p>
      <div className="flex flex-col sm:flex-row items-center gap-6">
        <div className="flex flex-col items-center gap-2 flex-shrink-0">
          <ScoreRing score={total_score} grade={actualGrade} gradeColor={gc} />
          {badge && (
            <span className="text-xs font-medium px-2.5 py-0.5 rounded-full"
                  style={{ background: 'rgba(124,92,252,0.15)', color: 'var(--accent-lt)' }}>
              {badge}
            </span>
          )}
        </div>
        {breakdown && (
          <div className="flex-1 w-full space-y-3">
            {Object.entries(breakdown).map(([dim, data]) => (
              <DimBar key={dim} label={LABELS[dim] ?? dim} score={data.score} weight={data.weight} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Language chart ── */
function LanguageChart({ languages }) {
  if (!languages || Object.keys(languages).length === 0) return null
  const total = Object.values(languages).reduce((a, b) => a + b, 0)
  const data  = Object.entries(languages)
    .sort(([, a], [, b]) => b - a).slice(0, 8)
    .map(([name, bytes]) => ({ name, value: bytes, pct: ((bytes / total) * 100).toFixed(1) }))

  return (
    <div className="card p-6 animate-slide-up">
      <p className="section-title mb-5">Language Breakdown</p>
      <div className="flex flex-col sm:flex-row items-center gap-5">
        <div className="w-40 h-40 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} cx="50%" cy="50%" innerRadius={38} outerRadius={62}
                   dataKey="value" paddingAngle={3} stroke="none">
                {data.map((_, i) => <Cell key={i} fill={LANG_COLORS[i % LANG_COLORS.length]} />)}
              </Pie>
              <Tooltip
                formatter={(v, name, props) => [`${props.payload.pct}%`, name]}
                contentStyle={{
                  background: 'var(--card)', border: '1px solid var(--border)',
                  borderRadius: 8, fontSize: 12, color: 'var(--text)',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex-1 w-full space-y-2">
          {data.map((d, i) => (
            <div key={d.name} className="flex items-center gap-2 text-xs">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ background: LANG_COLORS[i % LANG_COLORS.length] }} />
              <span className="w-20 truncate font-medium" style={{ color: 'var(--text)' }}>{d.name}</span>
              <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                <div className="h-full rounded-full"
                     style={{ width: `${d.pct}%`, background: LANG_COLORS[i % LANG_COLORS.length] }} />
              </div>
              <span className="w-8 text-right tabular-nums" style={{ color: 'var(--muted)' }}>{d.pct}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ── README card ── */
function ReadmeCard({ readmeAnalysis }) {
  if (!readmeAnalysis) return null
  const { score, sections_found, sections_missing, suggestions } = readmeAnalysis
  const pct = Math.round(score)

  return (
    <div className="card p-6 space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <p className="section-title">README Quality</p>
        <span className="font-bold text-lg tabular-nums" style={{ color: barColor(pct) }}>{pct}</span>
      </div>
      <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: barColor(pct), transition: 'width 1s ease' }} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <p className="text-xs font-semibold mb-2" style={{ color: 'var(--success)' }}>
            Found ({sections_found?.length ?? 0})
          </p>
          <ul className="space-y-1">
            {(sections_found ?? []).map((s) => (
              <li key={s} className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--muted)' }}>
                <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                     style={{ color: 'var(--success)' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold mb-2" style={{ color: 'var(--warning)' }}>
            Missing ({sections_missing?.length ?? 0})
          </p>
          <ul className="space-y-1">
            {(sections_missing ?? []).map((s) => (
              <li key={s} className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--muted)', opacity: 0.7 }}>
                <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                     style={{ color: 'var(--warning)' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
                {s}
              </li>
            ))}
          </ul>
          {suggestions?.length > 0 && (
            <div className="mt-2 space-y-1">
              <p className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Suggestions</p>
              {suggestions.map((sg, i) => (
                <p key={i} className="text-xs" style={{ color: 'var(--muted)', opacity: 0.7 }}>· {sg}</p>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── SVG icons ── */
const ICONS = {
  star: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
    </svg>
  ),
  fork: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4M7 16h10" />
    </svg>
  ),
  issue: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  eye: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  ),
}

/* ── Page ── */
export default function Dashboard() {
  const { state }   = useLocation()
  const navigate    = useNavigate()
  const addToast    = useAppToast()
  const [pdfLoading, setPdfLoading] = useState(false)
  const report = state?.report

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-4 text-center animate-fade-in">
        <svg className="w-14 h-14" fill="none" stroke="currentColor" viewBox="0 0 24 24"
             style={{ color: 'var(--border)' }}>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="text-sm" style={{ color: 'var(--muted)' }}>No report loaded.</p>
        <button onClick={() => navigate('/')} className="btn-primary px-5 py-2.5 text-sm">
          Analyze a Repository
        </button>
      </div>
    )
  }

  const { id: reportId, languages = {}, file_presence, final_score, code_analysis, readme_analysis } = report
  const repo      = report.repo_info ?? report.repo ?? {}
  const ai_review = report.ai_review ?? report.ai  ?? null

  async function handleDownloadPDF() {
    if (!reportId) {
      addToast?.('Report ID not available — try re-analyzing.', 'warning')
      return
    }
    setPdfLoading(true)
    try {
      const name = (repo?.full_name || 'report').replace('/', '_')
      await downloadReport(reportId, `${name}_review.pdf`)
      addToast?.('PDF downloaded successfully.', 'success')
    } catch (err) {
      addToast?.(err.message ?? 'PDF download failed.', 'error')
    } finally {
      setPdfLoading(false)
    }
  }

  const stars    = repo?.stargazers_count ?? repo?.stars ?? 0
  const forks    = repo?.forks_count      ?? repo?.forks ?? 0
  const issues   = repo?.open_issues_count ?? repo?.open_issues ?? 0
  const watchers = repo?.watchers_count   ?? repo?.watchers ?? 0
  const langList = Object.keys(languages)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-5 animate-fade-in">

      {/* 1 — Repo header */}
      <div className="card p-5 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-start gap-4">
          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
                {repo?.full_name ?? 'Repository'}
              </h2>
              {repo?.private && (
                <span className="text-xs px-2 py-0.5 rounded-full"
                      style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--muted)' }}>
                  Private
                </span>
              )}
            </div>
            {repo?.description && (
              <p className="text-sm leading-relaxed" style={{ color: 'var(--muted)' }}>
                {repo.description}
              </p>
            )}
            <div className="flex flex-wrap gap-1.5">
              {langList.map((lang) => <LanguageBadge key={lang} language={lang} />)}
            </div>
            <div className="flex flex-wrap gap-4 text-xs" style={{ color: 'var(--muted)' }}>
              {repo?.license        && <span>License: {repo.license}</span>}
              {repo?.default_branch && <span>Branch: {repo.default_branch}</span>}
              {repo?.created_at     && <span>Created: {new Date(repo.created_at).getFullYear()}</span>}
            </div>
          </div>

          <div className="flex gap-2 flex-shrink-0">
            {repo?.html_url && (
              <a href={repo.html_url} target="_blank" rel="noreferrer"
                 className="btn-ghost px-4 py-2 text-xs flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                </svg>
                GitHub
              </a>
            )}
            <button onClick={handleDownloadPDF} disabled={pdfLoading}
                    className="btn-primary px-4 py-2 text-xs flex items-center gap-1.5">
              {pdfLoading ? (
                <>
                  <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  Generating&hellip;
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                  </svg>
                  PDF Report
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 2 — Stat row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Stars"       value={stars}    icon={ICONS.star}  />
        <StatCard label="Forks"       value={forks}    icon={ICONS.fork}  />
        <StatCard label="Open Issues" value={issues}   icon={ICONS.issue} />
        <StatCard label="Watchers"    value={watchers} icon={ICONS.eye}   />
      </div>

      {/* 3 — Score + Languages */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ScoreCard finalScore={final_score} />
        <LanguageChart languages={languages} />
      </div>

      {/* 4 — File structure + README */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <FileStructureTree filePresence={file_presence} />
        <ReadmeCard readmeAnalysis={readme_analysis} />
      </div>

      {/* 5 — Code analysis */}
      <AnalysisSection codeAnalysis={code_analysis} />

      {/* 6 — AI review */}
      <AIRecommendations aiData={ai_review} />

    </div>
  )
}
