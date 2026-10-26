import { useState } from 'react'
import { api, type GrammarResult, type Level } from '../api'
import ChangeList from './ChangeList'
import { SLOW_HINT, useAsync } from './useAsync'

export default function GrammarTab({ level }: { level: Level }) {
  const [text, setText] = useState('')
  const [result, setResult] = useState<GrammarResult | null>(null)
  const { loading, error, run } = useAsync()

  async function check() {
    const res = await run(() => api.grammar(text, level))
    if (res) setResult(res)
  }

  return (
    <section>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Write or paste English text to check, e.g. “She go to school every days.”"
        rows={6}
      />
      <button className="primary" onClick={check} disabled={loading || !text.trim()}>
        {loading ? 'Checking…' : 'Check grammar'}
      </button>
      {loading && <p className="hint">{SLOW_HINT}</p>}
      {error && <p className="banner error">{error}</p>}
      {result && !loading && (
        <div className="card">
          <h2>Corrected</h2>
          <p className="corrected">{result.corrected}</p>
          <h2>What changed</h2>
          <ChangeList changes={result.changes} />
        </div>
      )}
    </section>
  )
}
