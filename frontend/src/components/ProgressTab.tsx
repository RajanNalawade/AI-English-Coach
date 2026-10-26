import { useEffect, useState } from 'react'
import { api, type MistakeSummary } from '../api'
import { useAsync } from './useAsync'

export default function ProgressTab() {
  const [data, setData] = useState<MistakeSummary | null>(null)
  const { loading, error, run } = useAsync()

  useEffect(() => {
    run(api.mistakes).then((res) => res && setData(res))
  }, [])

  if (loading) return <p className="hint">Loading…</p>
  if (error) return <p className="banner error">{error}</p>
  if (!data) return null
  if (data.total === 0) return <p className="hint">No mistakes logged yet. Use Grammar or Chat and they will show up here.</p>

  const max = Math.max(...data.top_categories.map((c) => c.count))
  return (
    <section>
      <div className="card">
        <h2>Your most common mistakes</h2>
        <p className="why">{data.total} corrections so far</p>
        {data.top_categories.map((c) => (
          <div key={c.category} className="bar-row">
            <span className="bar-label">{c.category.replace('_', ' ')}</span>
            <span className="bar" style={{ width: `${(c.count / max) * 100}%` }} />
            <span className="bar-count">{c.count}</span>
          </div>
        ))}
      </div>
      <div className="card">
        <h2>Recent corrections</h2>
        <ul className="changes">
          {data.recent.map((m, i) => (
            <li key={i}>
              <span className="from">{m.original}</span> → <span className="to">{m.correction}</span>
              <span className="badge">{m.category.replace('_', ' ')}</span>
              <div className="why">{m.explanation}</div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
