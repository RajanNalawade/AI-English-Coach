import { useRef, useState } from 'react'

const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']

export const canRecord = () =>
  typeof window !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined'

/** Records from the microphone; stop() resolves with the recording. */
export function useRecorder() {
  const [recording, setRecording] = useState(false)
  const recorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])

  async function start() {
    // Microphone access needs a secure page: localhost or HTTPS.
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      throw new Error('Microphone access was blocked or no microphone was found. Allow it in the browser and try again.')
    }
    const mimeType = MIME_TYPES.find((t) => MediaRecorder.isTypeSupported(t))
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    chunks.current = []
    rec.ondataavailable = (e) => e.data.size > 0 && chunks.current.push(e.data)
    rec.start()
    recorder.current = rec
    setRecording(true)
  }

  function stop(): Promise<Blob> {
    return new Promise((resolve) => {
      const rec = recorder.current
      if (!rec) return resolve(new Blob())
      rec.onstop = () => {
        rec.stream.getTracks().forEach((t) => t.stop())
        recorder.current = null
        setRecording(false)
        resolve(new Blob(chunks.current, { type: rec.mimeType }))
      }
      rec.stop()
    })
  }

  return { recording, start, stop }
}

export const canSpeak = () => typeof window !== 'undefined' && 'speechSynthesis' in window

/** Reads text aloud with the device's built-in voices (no server, works offline). */
export function speak(text: string) {
  if (!canSpeak()) return
  const synth = window.speechSynthesis
  synth.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  const voices = synth.getVoices().filter((v) => v.lang.toLowerCase().startsWith('en'))
  // Prefer voices installed on the device over ones streamed from the cloud.
  utterance.voice = voices.find((v) => v.localService) ?? voices[0] ?? null
  utterance.lang = utterance.voice?.lang ?? 'en-US'
  utterance.rate = 0.95
  synth.speak(utterance)
}

export function stopSpeaking() {
  if (canSpeak()) window.speechSynthesis.cancel()
}
