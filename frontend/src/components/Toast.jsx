import { useEffect, useRef } from 'react'

const ICON_SVG = {
  error: (
    <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
    </svg>
  ),
  warning: (
    <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
    </svg>
  ),
  success: (
    <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
    </svg>
  ),
  info: (
    <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
    </svg>
  ),
}

const TYPE_STYLE = {
  error:   { bg: 'rgba(244,96,108,0.12)', border: 'rgba(244,96,108,0.3)',  color: '#f4606c' },
  warning: { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)',  color: '#fbbf24' },
  success: { bg: 'rgba(34,211,165,0.12)', border: 'rgba(34,211,165,0.3)',  color: '#22d3a5' },
  info:    { bg: 'rgba(124,92,252,0.12)', border: 'rgba(124,92,252,0.3)',  color: 'var(--accent-lt)' },
}

export function Toast({ message, type = 'info', onClose, autoClose = 6000 }) {
  const timer = useRef(null)
  const s = TYPE_STYLE[type] ?? TYPE_STYLE.info

  useEffect(() => {
    if (autoClose > 0) {
      timer.current = setTimeout(onClose, autoClose)
    }
    return () => clearTimeout(timer.current)
  }, [autoClose, onClose])

  return (
    <div role="alert"
         className="flex items-start gap-3 px-4 py-3 rounded-xl max-w-sm w-full animate-slide-up"
         style={{
           background:   s.bg,
           border:       `1px solid ${s.border}`,
           boxShadow:    '0 8px 32px rgba(0,0,0,0.4)',
           backdropFilter: 'blur(8px)',
         }}>
      <span style={{ color: s.color }}>{ICON_SVG[type] ?? ICON_SVG.info}</span>
      <p className="flex-1 text-sm leading-snug" style={{ color: 'var(--text)' }}>{message}</p>
      <button onClick={onClose} className="flex-shrink-0 transition-opacity hover:opacity-70 ml-1"
              style={{ color: 'var(--muted)' }} aria-label="Dismiss">
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
  )
}

export function ToastContainer({ toasts, onClose }) {
  if (!toasts?.length) return null
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 items-end pointer-events-none">
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <Toast message={t.message} type={t.type}
                 autoClose={t.autoClose ?? 6000} onClose={() => onClose(t.id)} />
        </div>
      ))}
    </div>
  )
}
