import { useEffect, useRef, useState } from 'react'
import { api, type Change, type ChatMessage, type Level } from '../api'
import ChangeList from './ChangeList'
import { SLOW_HINT, useAsync } from './useAsync'

const TOPICS = [
  'everyday small talk',
  'a job interview for a software developer role',
  'ordering food at a restaurant',
  'travel and holidays',
  'talking about your hobbies',
  'a phone call with customer support',
]

interface Turn extends ChatMessage {
  corrections?: Change[]
}

export default function ChatTab({ level }: { level: Level }) {
  const [topic, setTopic] = useState(TOPICS[0])
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const { loading, error, run } = useAsync()
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, loading])

  async function send() {
    const content = draft.trim()
    if (!content) return
    const next: Turn[] = [...turns, { role: 'user', content }]
    setTurns(next)
    setDraft('')
    const res = await run(() =>
      api.chat(
        next.map(({ role, content }) => ({ role, content })),
        topic,
        level,
      ),
    )
    if (!res) return
    setTurns((t) => {
      const copy = [...t]
      copy[copy.length - 1] = { ...copy[copy.length - 1], corrections: res.corrections }
      return [...copy, { role: 'assistant', content: res.reply }]
    })
  }

  function restart(nextTopic: string) {
    setTopic(nextTopic)
    setTurns([])
  }

  return (
    <section className="chat">
      <label className="topic">
        Topic
        <select value={topic} onChange={(e) => restart(e.target.value)}>
          {TOPICS.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </label>

      <div className="messages">
        {turns.length === 0 && <p className="hint">Say hello to start practising. Mistakes appear under your messages.</p>}
        {turns.map((t, i) => (
          <div key={i} className={`bubble ${t.role}`}>
            <p>{t.content}</p>
            {t.corrections && t.corrections.length > 0 && (
              <details className="fixes">
                <summary>
                  {t.corrections.length} correction{t.corrections.length > 1 ? 's' : ''}
                </summary>
                <ChangeList changes={t.corrections} />
              </details>
            )}
          </div>
        ))}
        {loading && <p className="hint">{SLOW_HINT}</p>}
        {error && <p className="banner error">{error}</p>}
        <div ref={endRef} />
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault()
          send()
        }}
      >
        <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Type your message in English…" />
        <button className="primary" disabled={loading || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
