import { useState } from 'react'

/** Runs one request at a time and tracks its loading and error state. */
export function useAsync() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setLoading(true)
    setError(null)
    try {
      return await fn()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      return undefined
    } finally {
      setLoading(false)
    }
  }

  return { loading, error, run }
}

export const SLOW_HINT = 'Thinking… a model on a laptop CPU can take 10 to 30 seconds.'
