import { useState, useCallback } from 'react'

let _id = 0

/**
 * Minimal toast manager.
 * Returns { toasts, addToast, removeToast }.
 *
 * addToast(message, type?, autoClose?)
 *   type: 'error' | 'warning' | 'success' | 'info'  (default 'info')
 */
export function useToasts() {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback((message, type = 'info', autoClose = 6000) => {
    const id = ++_id
    setToasts((prev) => [...prev, { id, message, type, autoClose }])
    return id
  }, [])

  return { toasts, addToast, removeToast }
}
