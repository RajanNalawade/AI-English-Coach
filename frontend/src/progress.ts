import type { Change, MistakeSummary } from './api'

// Progress is kept in this browser, so it survives the server sleeping or restarting,
// and each visitor sees only their own mistakes.
const KEY = 'mistakes'
// Enough for months of practice while staying far below the browser's storage limit.
const MAX_SAVED = 1000

interface SavedMistake extends Change {
  created_at: string
  source: string
}

function load(): SavedMistake[] {
  try {
    const raw = localStorage.getItem(KEY)
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list : []
  } catch {
    // Storage can be unavailable (private mode) or hold broken data; start empty.
    return []
  }
}

/** Saves the corrections from one Grammar check or Chat message. */
export function saveMistakes(source: 'grammar' | 'chat', changes: Change[]): void {
  if (changes.length === 0) return
  const now = new Date().toISOString()
  const added = changes.map(({ original, correction, category, explanation }) => ({
    original,
    correction,
    category,
    explanation,
    created_at: now,
    source,
  }))
  try {
    localStorage.setItem(KEY, JSON.stringify([...load(), ...added].slice(-MAX_SAVED)))
  } catch {
    // Ignore; the corrections still show on screen for this visit.
  }
}

export function clearMistakes(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // Nothing to clear.
  }
}

export function mistakeSummary(recentLimit = 20): MistakeSummary {
  const all = load()
  const counts = new Map<string, number>()
  for (const m of all) counts.set(m.category, (counts.get(m.category) ?? 0) + 1)
  const top_categories = [...counts]
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count || a.category.localeCompare(b.category))
    .slice(0, 5)
  return { total: all.length, top_categories, recent: all.slice(-recentLimit).reverse() }
}
