function ListSection({ title, items, color }) {
  if (!items?.length) return null
  return (
    <div>
      <h4 className="text-xs font-semibold mb-2" style={{ color }}>{title}</h4>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-xs" style={{ color: 'var(--muted)' }}>
            <span className="flex-shrink-0 font-bold" style={{ color }}>›</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function MiniBar({ label, value, max = 10 }) {
  const pct = Math.round((value / max) * 100)
  const color = pct >= 70 ? 'var(--success)' : pct >= 50 ? '#fbbf24' : 'var(--danger)'

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs w-36 flex-shrink-0" style={{ color: 'var(--muted)' }}>{label}</span>
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-semibold tabular-nums w-10 text-right" style={{ color: 'var(--text)' }}>
        {value}/{max}
      </span>
    </div>
  )
}

export default function AIRecommendations({ aiData }) {
  if (!aiData) return null

  const {
    project_overview, tech_stack_assessment,
    strengths, weaknesses,
    security_suggestions, performance_suggestions, maintainability_suggestions,
    best_practices, beginner_friendly_score, production_readiness_score,
    documentation_quality, overall_review, recommended_next_steps,
    similar_projects_to_study, ai_available,
  } = aiData

  const DOC_COLOR = {
    poor:      'var(--danger)',
    fair:      '#fbbf24',
    good:      'var(--success)',
    excellent: 'var(--success)',
  }

  return (
    <div className="card p-6 space-y-6 animate-slide-up">
      <div className="flex items-center gap-3">
        <p className="section-title">AI Review</p>
        {ai_available === false && (
          <span className="text-xs px-2 py-0.5 rounded-full"
                style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', color: '#fbbf24' }}>
            AI unavailable — using fallback
          </span>
        )}
      </div>

      {/* Scores */}
      <div className="rounded-xl p-4 space-y-3"
           style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <MiniBar label="Beginner Friendly"    value={beginner_friendly_score}    max={10} />
        <MiniBar label="Production Readiness" value={production_readiness_score} max={10} />
        {documentation_quality && (
          <div className="flex items-center gap-3">
            <span className="text-xs w-36 flex-shrink-0" style={{ color: 'var(--muted)' }}>
              Documentation Quality
            </span>
            <span className="text-xs font-semibold capitalize"
                  style={{ color: DOC_COLOR[documentation_quality] ?? 'var(--muted)' }}>
              {documentation_quality}
            </span>
          </div>
        )}
      </div>

      {/* Overview */}
      {project_overview && (
        <div className="rounded-xl px-4 py-3"
             style={{ background: 'rgba(124,92,252,0.08)', border: '1px solid rgba(124,92,252,0.2)' }}>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--accent-lt)' }}>{project_overview}</p>
        </div>
      )}

      {/* Tech stack */}
      {tech_stack_assessment && (
        <div>
          <h4 className="text-xs font-semibold mb-1.5" style={{ color: 'var(--muted)' }}>Tech Stack Assessment</h4>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--muted)' }}>{tech_stack_assessment}</p>
        </div>
      )}

      {/* Strengths / Weaknesses */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <ListSection title="Strengths"  items={strengths}  color="var(--success)" />
        <ListSection title="Weaknesses" items={weaknesses} color="var(--danger)"  />
      </div>

      {/* Suggestions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <ListSection title="Security"        items={security_suggestions}        color="#f59e0b"   />
        <ListSection title="Performance"     items={performance_suggestions}     color="var(--accent-lt)" />
        <ListSection title="Maintainability" items={maintainability_suggestions} color="#a78bfa"  />
      </div>

      <ListSection title="Best Practices" items={best_practices} color="#22d3a5" />

      {/* Overall review */}
      {overall_review && (
        <div>
          <h4 className="text-xs font-semibold mb-1.5" style={{ color: 'var(--muted)' }}>Overall Review</h4>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--muted)' }}>{overall_review}</p>
        </div>
      )}

      <ListSection title="Recommended Next Steps"   items={recommended_next_steps}   color="var(--accent-lt)" />
      <ListSection title="Similar Projects to Study" items={similar_projects_to_study} color="var(--muted)"    />
    </div>
  )
}
