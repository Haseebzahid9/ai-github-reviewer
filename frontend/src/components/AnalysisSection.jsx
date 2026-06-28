function IssueItem({ issue }) {
  const colors = {
    error:   { bg: 'rgba(244,96,108,0.1)',  border: 'rgba(244,96,108,0.25)', text: '#f4606c',   dot: '#f4606c'   },
    warning: { bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.25)', text: '#fbbf24',   dot: '#f59e0b'   },
    info:    { bg: 'rgba(56,189,248,0.08)', border: 'rgba(56,189,248,0.2)',  text: 'var(--muted)', dot: '#38bdf8' },
  }
  const c = colors[issue.severity] ?? colors.info

  return (
    <div className="flex items-start gap-2 px-2.5 py-2 rounded-lg text-xs"
         style={{ background: c.bg, border: `1px solid ${c.border}` }}>
      <span className="w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0" style={{ background: c.dot }} />
      <div style={{ color: c.text }}>
        {issue.file && <span className="font-mono font-semibold mr-1">{issue.file}:</span>}
        {issue.line && <span style={{ opacity: 0.7 }} className="mr-1">L{issue.line}</span>}
        {issue.message}
      </div>
    </div>
  )
}

function LangCard({ lang, data }) {
  const issues   = data.issues ?? []
  const errors   = issues.filter((i) => i.severity === 'error').length
  const warnings = issues.filter((i) => i.severity === 'warning').length

  return (
    <div className="rounded-xl p-4 space-y-3" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between">
        <span className="font-semibold text-sm" style={{ color: 'var(--text)' }}>{lang}</span>
        <div className="flex items-center gap-3 text-xs">
          <span style={{ color: 'var(--muted)' }}>{data.total_loc ?? 0} LOC</span>
          {errors   > 0 && <span style={{ color: '#f4606c' }}>{errors}E</span>}
          {warnings > 0 && <span style={{ color: '#fbbf24' }}>{warnings}W</span>}
        </div>
      </div>

      {issues.length > 0 ? (
        <div className="space-y-1.5 max-h-40 overflow-y-auto pr-0.5">
          {issues.slice(0, 10).map((iss, i) => <IssueItem key={i} issue={iss} />)}
          {issues.length > 10 && (
            <p className="text-xs italic pl-1" style={{ color: 'var(--muted)', opacity: 0.6 }}>
              +{issues.length - 10} more issues
            </p>
          )}
        </div>
      ) : (
        <p className="text-xs" style={{ color: 'var(--success)' }}>No issues detected</p>
      )}
    </div>
  )
}

export default function AnalysisSection({ codeAnalysis }) {
  if (!codeAnalysis) return null
  const byLang  = codeAnalysis.by_language ?? {}
  const entries = Object.entries(byLang)

  return (
    <div className="card p-6 space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <p className="section-title">Code Quality</p>
        <span className="text-xs" style={{ color: 'var(--muted)' }}>
          {codeAnalysis.total_files ?? 0} files &middot; {codeAnalysis.total_loc ?? 0} LOC
        </span>
      </div>

      {entries.length === 0 ? (
        <p className="text-sm italic" style={{ color: 'var(--muted)' }}>No source files analyzed.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {entries.map(([lang, data]) => <LangCard key={lang} lang={lang} data={data} />)}
        </div>
      )}
    </div>
  )
}
