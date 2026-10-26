import { useState } from 'react'
import { api, type Style, type Variant } from '../api'
import { SLOW_HINT, useAsync } from './useAsync'

const STYLES: Style[] = ['simpler', 'formal', 'casual', 'natural', 'concise']

export default function RephraseTab() {
  const [text, setText] = useState('')
  const [styles, setStyles] = useState<Style[]>(['simpler', 'formal', 'natural'])
  const [variants, setVariants] = useState<Variant[]>([])
  const { loading, error, run } = useAsync()

  function toggle(style: Style) {
    setStyles((s) => (s.includes(style) ? s.filter((x) => x !== style) : [...s, style]))
  }

  async function rephrase() {
    const res = await run(() => api.rephrase(text, STYLES.filter((s) => styles.includes(s))))
    if (res) setVariants(res.variants)
  }

  return (
    <section>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Write a sentence to rephrase, e.g. “I want leave early today because I am not feeling good.”"
        rows={4}
      />
      <div className="chips">
        {STYLES.map((s) => (
          <label key={s} className={styles.includes(s) ? 'chip on' : 'chip'}>
            <input type="checkbox" checked={styles.includes(s)} onChange={() => toggle(s)} />
            {s}
          </label>
        ))}
      </div>
      <button className="primary" onClick={rephrase} disabled={loading || !text.trim() || styles.length === 0}>
        {loading ? 'Rephrasing…' : 'Rephrase'}
      </button>
      {loading && <p className="hint">{SLOW_HINT}</p>}
      {error && <p className="banner error">{error}</p>}
      {!loading &&
        variants.map((v, i) => (
          <div key={i} className="card">
            <span className="badge">{v.style}</span>
            <p className="corrected">{v.text}</p>
            <p className="why">{v.note}</p>
            <button className="link" onClick={() => navigator.clipboard?.writeText(v.text)}>
              Copy
            </button>
          </div>
        ))}
    </section>
  )
}
