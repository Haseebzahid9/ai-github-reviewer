import { useState, createContext, useContext } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Home      from './pages/Home'
import Dashboard from './pages/Dashboard'
import History   from './pages/History'
import About     from './pages/About'
import { ToastContainer } from './components/Toast'
import { useToasts }      from './hooks/useToasts'

export const ToastCtx    = createContext(null)
export const useAppToast = () => useContext(ToastCtx)

const GH_MARK = (
  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
  </svg>
)

function NavLink({ to, children, onClick }) {
  const { pathname } = useLocation()
  const active = pathname === to
  return (
    <Link
      to={to}
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
        active
          ? 'bg-white/10 text-white'
          : 'text-[#8892a4] hover:text-white hover:bg-white/5'
      }`}
    >
      {children}
    </Link>
  )
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  const { toasts, addToast, removeToast } = useToasts()
  const close = () => setMenuOpen(false)

  return (
    <ToastCtx.Provider value={addToast}>
      <div className="min-h-screen flex flex-col" style={{ background: 'var(--bg)' }}>

        {/* Navbar */}
        <nav style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}
             className="sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">

              {/* Logo */}
              <Link to="/" onClick={close}
                className="flex items-center gap-2.5 text-white font-bold text-sm">
                <span className="flex items-center justify-center w-8 h-8 rounded-lg"
                      style={{ background: 'var(--accent)' }}>
                  {GH_MARK}
                </span>
                <span className="hidden sm:block tracking-tight">AI GitHub Reviewer</span>
              </Link>

              {/* Desktop links */}
              <div className="hidden md:flex items-center gap-0.5">
                <NavLink to="/">Home</NavLink>
                <NavLink to="/history">History</NavLink>
                <NavLink to="/about">About</NavLink>
              </div>

              {/* Mobile hamburger */}
              <button
                className="md:hidden p-2 rounded-lg transition-colors"
                style={{ color: 'var(--muted)' }}
                onClick={() => setMenuOpen((o) => !o)}
                aria-label="Toggle menu"
              >
                {menuOpen ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                )}
              </button>
            </div>

            {/* Mobile menu */}
            {menuOpen && (
              <div className="md:hidden pb-3 flex flex-col gap-0.5 animate-fade-in">
                <NavLink to="/"        onClick={close}>Home</NavLink>
                <NavLink to="/history" onClick={close}>History</NavLink>
                <NavLink to="/about"   onClick={close}>About</NavLink>
              </div>
            )}
          </div>
        </nav>

        {/* Pages */}
        <main className="flex-1">
          <Routes>
            <Route path="/"          element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/history"   element={<History />} />
            <Route path="/about"     element={<About />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer style={{ background: 'var(--surface)', borderTop: '1px solid var(--border)', color: 'var(--muted)' }}
                className="py-4 text-center text-xs">
          <p>
            Built by{' '}
            <a href="https://github.com/Haseebzahid9" target="_blank" rel="noreferrer"
               style={{ color: 'var(--accent-lt)' }}
               className="hover:underline font-medium">
              Haseeb Raza
            </a>
            {' '}&mdash; AI GitHub Reviewer &middot; Gemini &amp; FastAPI
          </p>
        </footer>

        <ToastContainer toasts={toasts} onClose={removeToast} />
      </div>
    </ToastCtx.Provider>
  )
}
