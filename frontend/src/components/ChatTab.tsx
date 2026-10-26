import { useEffect, useRef, useState } from 'react'
import { api, type Change, type ChatMessage, type ExplainIn, type Level } from '../api'
import ChangeList from './ChangeList'
import { SLOW_HINT, useAsync } from './useAsync'
import { canRecord, canSpeak, speak, stopSpeaking, useRecorder } from './voice'

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

function loadSpeakReplies(): boolean {
  try {
    return localStorage.getItem('speakReplies') !== 'false'
  } catch {
    return true
  }
}

export default function ChatTab({ level, explainIn }: { level: Level; explainIn: ExplainIn }) {
  const [topic, setTopic] = useState(TOPICS[0])
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [speakReplies, setSpeakReplies] = useState(loadSpeakReplies)
  const [transcribing, setTranscribing] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const { loading, error, run } = useAsync()
  const recorder = useRecorder()
  const endRef = useRef<HTMLDivElement>(null)
  const busy = loading || transcribing

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, busy])

  useEffect(() => stopSpeaking, [])

  async function send(text: string) {
    const content = text.trim()
    if (!content) return
    const next: Turn[] = [...turns, { role: 'user', content }]
    // An empty assistant turn is a placeholder that fills in as the reply streams.
    setTurns([...next, { role: 'assistant', content: '' }])
    setDraft('')
    let streamed = ''
    const updateLast = (patch: Partial<Turn>) => setTurns((t) => [...t.slice(0, -1), { ...t[t.length - 1], ...patch }])
    const res = await run(() =>
      api.chatStream(
        next.map(({ role, content }) => ({ role, content })),
        topic,
        level,
        explainIn,
        (text) => {
          streamed += text
          updateLast({ content: streamed })
        },
      ),
    )
    if (!res) {
      setTurns((t) => t.slice(0, -1))
      return
    }
    // Corrections belong to the learner's message, just before the reply.
    setTurns((t) => [
      ...t.slice(0, -2),
      { ...t[t.length - 2], corrections: res.corrections },
      { role: 'assistant', content: res.reply },
    ])
    if (speakReplies) speak(res.reply)
  }

  async function toggleMic() {
    if (recorder.recording) {
      const audio = await recorder.stop()
      setTranscribing(true)
      const text = await run(() => api.transcribe(audio))
      setTranscribing(false)
      if (text?.trim()) await send(text)
      else if (text !== undefined) setNotice("I didn't catch that. Tap the mic and try again.")
      return
    }
    setNotice(null)
    stopSpeaking()
    await run(() => recorder.start()).catch(() => undefined)
  }

  function toggleSpeakReplies() {
    const next = !speakReplies
    setSpeakReplies(next)
    if (!next) stopSpeaking()
    try {
      localStorage.setItem('speakReplies', String(next))
    } catch {
      // Ignore; the setting still applies for this visit.
    }
  }

  function restart(nextTopic: string) {
    stopSpeaking()
    setTopic(nextTopic)
    setTurns([])
  }

  return (
    <section className="chat">
      <div className="chat-bar">
        <label className="topic">
          Topic
          <select value={topic} onChange={(e) => restart(e.target.value)}>
            {TOPICS.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        {canSpeak() && (
          <label className="toggle">
            <input type="checkbox" checked={speakReplies} onChange={toggleSpeakReplies} />
            Speak replies
          </label>
        )}
      </div>

      <div className="messages">
        {turns.length === 0 && (
          <p className="hint">
            Say hello to start practising{canRecord() ? ': type, or tap the mic and speak' : ''}. Mistakes appear under
            your messages.
          </p>
        )}
        {turns.map((t, i) =>
          t.content === '' ? null : (
            <div key={i} className={`bubble ${t.role}`}>
              <p>{t.content}</p>
              {t.role === 'assistant' && canSpeak() && (
                <button className="link replay" onClick={() => speak(t.content)} aria-label="Play this reply">
                  Play
                </button>
              )}
              {t.corrections && t.corrections.length > 0 && (
                <details className="fixes">
                  <summary>
                    {t.corrections.length} correction{t.corrections.length > 1 ? 's' : ''}
                  </summary>
                  <ChangeList changes={t.corrections} />
                </details>
              )}
            </div>
          ),
        )}
        {recorder.recording && <p className="hint recording-hint">Listening… tap Stop when you finish speaking.</p>}
        {transcribing && <p className="hint">Turning your speech into text…</p>}
        {loading && !transcribing && turns.at(-1)?.content === '' && <p className="hint">{SLOW_HINT}</p>}
        {notice && <p className="hint">{notice}</p>}
        {error && <p className="banner error">{error}</p>}
        <div ref={endRef} />
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault()
          send(draft)
        }}
      >
        {canRecord() && (
          <button
            type="button"
            className={recorder.recording ? 'mic on' : 'mic'}
            onClick={toggleMic}
            disabled={busy}
            aria-label={recorder.recording ? 'Stop recording' : 'Speak'}
          >
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              {recorder.recording ? (
                <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
              ) : (
                <path
                  fill="currentColor"
                  d="M12 14a3 3 0 0 0 3-3V5a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z"
                />
              )}
            </svg>
          </button>
        )}
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type your message in English…"
          disabled={recorder.recording}
        />
        <button className="primary" disabled={busy || recorder.recording || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
