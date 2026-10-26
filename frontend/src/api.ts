export type Level = 'A2' | 'B1' | 'B2' | 'C1'
export type Style = 'simpler' | 'formal' | 'casual' | 'natural' | 'concise'

export interface Change {
  original: string
  correction: string
  category: string
  explanation: string
}

export interface GrammarResult {
  corrected: string
  changes: Change[]
}

export interface Variant {
  style: Style
  text: string
  note: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResult {
  reply: string
  corrections: Change[]
}

export interface MistakeSummary {
  total: number
  top_categories: { category: string; count: number }[]
  recent: (Change & { created_at: string; source: string })[]
}

export interface Health {
  ok: boolean
  ollama: boolean
  model?: string
  model_installed?: boolean
}

// Empty means "same origin": the Vite dev server proxies /api to the backend.
const BASE = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new Error('Cannot reach the coach server. Is the backend running?')
  }
  if (!res.ok) {
    const detail = await res.json().then((d) => d.detail, () => null)
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<Health>('/api/health'),
  grammar: (text: string, level: Level) => request<GrammarResult>('/api/grammar', { text, level }),
  rephrase: (text: string, styles: Style[]) => request<{ variants: Variant[] }>('/api/rephrase', { text, styles }),
  chat: (messages: ChatMessage[], topic: string, level: Level) =>
    request<ChatResult>('/api/chat', { messages, topic, level }),
  mistakes: () => request<MistakeSummary>('/api/mistakes'),
  transcribe: async (audio: Blob): Promise<string> => {
    const form = new FormData()
    const ext = audio.type.includes('mp4') ? 'mp4' : audio.type.includes('ogg') ? 'ogg' : 'webm'
    form.append('audio', audio, `recording.${ext}`)
    let res: Response
    try {
      res = await fetch(`${BASE}/api/transcribe`, { method: 'POST', body: form })
    } catch {
      throw new Error('Cannot reach the coach server. Is the backend running?')
    }
    if (!res.ok) {
      const detail = await res.json().then((d) => d.detail, () => null)
      throw new Error(typeof detail === 'string' ? detail : `Transcription failed (${res.status})`)
    }
    return ((await res.json()) as { text: string }).text
  },
}
