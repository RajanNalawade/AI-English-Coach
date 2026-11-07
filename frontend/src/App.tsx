import { useEffect, useState } from 'react'
import { api, type ExplainIn, type Health, type Level } from './api'
import GrammarTab from './components/GrammarTab'
import RephraseTab from './components/RephraseTab'
import ChatTab from './components/ChatTab'
import ProgressTab from './components/ProgressTab'

const TABS = ['Grammar', 'Rephrase', 'Chat', 'Progress'] as const
type Tab = (typeof TABS)[number]

function loadLevel(): Level {
  try {
    const saved = localStorage.getItem('level')
    if (saved === 'A2' || saved === 'B1' || saved === 'B2' || saved === 'C1') return saved
  } catch {
    // Storage can be unavailable (private mode); fall back to the default.
  }
  return 'B1'
}

// Give up after this long and show the "cannot reach" message instead.
const WAKE_TIMEOUT_MS = 3 * 60 * 1000

const EXPLAIN_LANGUAGES: { value: ExplainIn; label: string }[] = [
  { value: 'English', label: 'English' },
  { value: 'Hindi', label: 'हिन्दी Hindi' },
  { value: 'Marathi', label: 'मराठी Marathi' },
]

function loadExplainIn(): ExplainIn {
  try {
    const saved = localStorage.getItem('explainIn')
    if (EXPLAIN_LANGUAGES.some((l) => l.value === saved)) return saved as ExplainIn
  } catch {
    // Storage can be unavailable (private mode); fall back to the default.
  }
  return 'English'
}

export default function App() {
  const [tab, setTab] = useState<Tab>('Grammar')
  const [level, setLevel] = useState<Level>(loadLevel)
  const [explainIn, setExplainIn] = useState<ExplainIn>(loadExplainIn)
  const [health, setHealth] = useState<Health | null>(null)
  const [waking, setWaking] = useState(false)

  useEffect(() => {
    // A free Render server sleeps when nobody uses it, and takes about a minute to wake up.
    // While it wakes, its requests hang or fail, so keep asking and show a friendly screen.
    let stopped = false
    const started = Date.now()
    const slow = setTimeout(() => setWaking(true), 2500)
    async function check() {
      while (!stopped) {
        try {
          const res = await api.health()
          if (res.ok) {
            if (!stopped) setHealth(res)
            break
          }
        } catch {
          // Not awake yet; try again below.
        }
        if (Date.now() - started > WAKE_TIMEOUT_MS) {
          if (!stopped) setHealth({ ok: false, ollama: false })
          break
        }
        await new Promise((r) => setTimeout(r, 3000))
      }
      clearTimeout(slow)
      if (!stopped) setWaking(false)
    }
    check()
    return () => {
      stopped = true
      clearTimeout(slow)
    }
  }, [])

  function changeLevel(next: Level) {
    setLevel(next)
    try {
      localStorage.setItem('level', next)
    } catch {
      // Ignore; the level still applies for this visit.
    }
  }

  function changeExplainIn(next: ExplainIn) {
    setExplainIn(next)
    try {
      localStorage.setItem('explainIn', next)
    } catch {
      // Ignore; the choice still applies for this visit.
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>AI English Coach</h1>
        <label className="level">
          Level
          <select value={level} onChange={(e) => changeLevel(e.target.value as Level)}>
            <option value="A2">A2 beginner</option>
            <option value="B1">B1 intermediate</option>
            <option value="B2">B2 upper-intermediate</option>
            <option value="C1">C1 advanced</option>
          </select>
        </label>
        <label className="level">
          Explain in
          <select value={explainIn} onChange={(e) => changeExplainIn(e.target.value as ExplainIn)}>
            {EXPLAIN_LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
      </header>

      {waking ? <WakingScreen /> : <HealthBanner health={health} />}

      <nav className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </nav>

      <main>
        {tab === 'Grammar' && <GrammarTab level={level} explainIn={explainIn} />}
        {tab === 'Rephrase' && <RephraseTab explainIn={explainIn} />}
        {tab === 'Chat' && <ChatTab level={level} explainIn={explainIn} />}
        {tab === 'Progress' && <ProgressTab />}
      </main>
    </div>
  )
}

function WakingScreen() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [])
  return (
    <div className="card waking" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <div>
        <h2>Waking up the coach…</h2>
        <p className="why">
          The coach takes a short nap when nobody is using it. It usually wakes up in under a minute. You can start
          typing now; your first answer will come once it is awake.
        </p>
        <p className="why">Waiting {seconds}s</p>
      </div>
    </div>
  )
}

function HealthBanner({ health }: { health: Health | null }) {
  if (!health) return null
  if (!health.ok) return <p className="banner error">Cannot reach the coach server. Start the backend (see README).</p>
  if (health.remote) return null
  if (!health.ollama) return <p className="banner error">The backend is up but Ollama is not running. Start Ollama.</p>
  if (health.model_installed === false)
    return (
      <p className="banner error">
        Model <code>{health.model}</code> is not downloaded yet. Run <code>ollama pull {health.model}</code>.
      </p>
    )
  return null
}
