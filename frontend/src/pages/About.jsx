const STACK = [
  { name: 'React 18 + Vite',            role: 'Frontend SPA & build tool'               },
  { name: 'Tailwind CSS',               role: 'Utility-first styling'                   },
  { name: 'React Router DOM v6',        role: 'Client-side routing'                     },
  { name: 'Recharts',                   role: 'Language chart & score visualisations'   },
  { name: 'FastAPI',                    role: 'Backend REST API (Python 3.14)'          },
  { name: 'SQLAlchemy 2 + aiosqlite',   role: 'Async ORM + SQLite persistent storage'  },
  { name: 'httpx',                      role: 'Async GitHub REST API client'            },
  { name: 'Google Gemini (genai)',       role: 'AI-powered project review & insights'   },
  { name: 'ReportLab',                  role: '6-page PDF report generation'            },
  { name: 'GitHub REST API v3',         role: 'Repository metadata, tree & source files'},
]

const DIMENSIONS = [
  { name: 'Project Structure',  weight: '20%', color: '#7c5cfc',
    desc: '22 rules across essential files, CI/CD, testing, docs, and code organisation.' },
  { name: 'Documentation',      weight: '20%', color: '#38bdf8',
    desc: 'README completeness scored across 14 sections including badges, installation, and contributing.' },
  { name: 'Code Quality',       weight: '30%', color: '#22d3a5',
    desc: 'Static analysis across 14 languages — LOC, issues by severity, density-normalized deduction.' },
  { name: 'Security',           weight: '15%', color: '#f59e0b',
    desc: 'Keyword-matched issues: hardcoded secrets, injection, eval(), deprecated APIs, missing SRI.' },
  { name: 'AI Assessment',      weight: '15%', color: '#e879f9',
    desc: 'Google Gemini holistic score + beginner-friendly + production-readiness ratings.' },
]

const GRADES = [
  { grade: 'A+', range: '90–100', color: '#22d3a5' },
  { grade: 'A',  range: '80–89',  color: '#34d399' },
  { grade: 'B+', range: '70–79',  color: '#a3e635' },
  { grade: 'B',  range: '60–69',  color: '#fbbf24' },
  { grade: 'C+', range: '50–59',  color: '#fb923c' },
  { grade: 'C',  range: '40–49',  color: '#f97316' },
  { grade: 'D',  range: '30–39',  color: '#f87171' },
  { grade: 'F',  range: '0–29',   color: '#f4606c' },
]

export default function About() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12 space-y-12 animate-fade-in">

      {/* Header */}
      <div className="space-y-3">
        <h2 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>About</h2>
        <p className="text-sm leading-relaxed max-w-2xl" style={{ color: 'var(--muted)' }}>
          <span className="font-semibold" style={{ color: 'var(--text)' }}>AI GitHub Project Reviewer</span>{' '}
          fetches any public repository, runs multi-language static analysis across 14 languages,
          evaluates README quality, checks project structure rules, and sends the results to
          Google Gemini for a deep AI review — all in under 60 seconds.
        </p>
      </div>

      {/* Scoring dimensions */}
      <section className="space-y-4">
        <p className="section-title">Scoring Dimensions</p>
        <div className="space-y-2">
          {DIMENSIONS.map((d) => (
            <div key={d.name}
              className="card px-4 py-4 flex items-start gap-4">
              <div className="flex-shrink-0 w-12 text-center">
                <span className="text-base font-black" style={{ color: d.color }}>{d.weight}</span>
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{d.name}</p>
                <p className="text-xs mt-0.5 leading-relaxed" style={{ color: 'var(--muted)' }}>{d.desc}</p>
              </div>
              {/* Accent pip */}
              <div className="w-1 h-8 rounded-full flex-shrink-0 self-center"
                   style={{ background: d.color, opacity: 0.7 }} />
            </div>
          ))}
        </div>
      </section>

      {/* Grade scale */}
      <section className="space-y-4">
        <p className="section-title">Grade Scale</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {GRADES.map((g) => (
            <div key={g.grade}
              className="card px-3 py-4 text-center"
              style={{ borderColor: `${g.color}33` }}>
              <div className="text-2xl font-black" style={{ color: g.color }}>{g.grade}</div>
              <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{g.range}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Tech stack */}
      <section className="space-y-4">
        <p className="section-title">Tech Stack</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {STACK.map((s) => (
            <div key={s.name}
              className="card px-4 py-3 flex items-center justify-between gap-3">
              <span className="text-sm font-semibold" style={{ color: 'var(--accent-lt)' }}>{s.name}</span>
              <span className="text-xs text-right" style={{ color: 'var(--muted)' }}>{s.role}</span>
            </div>
          ))}
        </div>
      </section>

    </div>
  )
}
