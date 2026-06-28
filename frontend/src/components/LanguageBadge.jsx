const PALETTE = {
  JavaScript: { bg: 'rgba(251,191,36,0.12)',  color: '#fbbf24' },
  TypeScript: { bg: 'rgba(96,165,250,0.12)',  color: '#60a5fa' },
  Python:     { bg: 'rgba(52,211,153,0.12)',  color: '#34d399' },
  Rust:       { bg: 'rgba(251,146,60,0.12)',  color: '#fb923c' },
  Go:         { bg: 'rgba(56,189,248,0.12)',  color: '#38bdf8' },
  Java:       { bg: 'rgba(244,96,108,0.12)',  color: '#f4606c' },
  'C++':      { bg: 'rgba(167,139,250,0.12)', color: '#a78bfa' },
  C:          { bg: 'rgba(148,163,184,0.12)', color: '#94a3b8' },
  'C#':       { bg: 'rgba(139,92,246,0.12)',  color: '#8b5cf6' },
  Ruby:       { bg: 'rgba(244,96,108,0.12)',  color: '#f472b6' },
  PHP:        { bg: 'rgba(124,92,252,0.12)',  color: '#a78bfa' },
  Swift:      { bg: 'rgba(251,146,60,0.12)',  color: '#fb923c' },
  Kotlin:     { bg: 'rgba(232,121,249,0.12)', color: '#e879f9' },
  HTML:       { bg: 'rgba(251,113,133,0.12)', color: '#fb7185' },
  CSS:        { bg: 'rgba(56,189,248,0.12)',  color: '#7dd3fc' },
  SCSS:       { bg: 'rgba(244,114,182,0.12)', color: '#f472b6' },
  SQL:        { bg: 'rgba(34,211,165,0.12)',  color: '#2dd4bf' },
}

const DEFAULT = { bg: 'rgba(136,146,164,0.12)', color: '#8892a4' }

export default function LanguageBadge({ language, className = '' }) {
  const { bg, color } = PALETTE[language] ?? DEFAULT
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${className}`}
      style={{ background: bg, color, border: `1px solid ${color}33` }}
    >
      {language}
    </span>
  )
}
