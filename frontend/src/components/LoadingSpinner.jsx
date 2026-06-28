export default function LoadingSpinner({ size = 'md' }) {
  const sz = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-10 h-10' }[size] ?? 'w-8 h-8'
  return (
    <div
      className={`${sz} rounded-full animate-spin`}
      style={{ border: '2px solid var(--border)', borderTopColor: 'var(--accent)' }}
      role="status"
      aria-label="Loading"
    />
  )
}
