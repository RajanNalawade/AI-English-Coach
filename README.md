# AI English Coach

A self-hosted AI language coach. It fixes grammar with short explanations, rephrases sentences in different styles, and holds practice conversations while correcting your mistakes. Every AI call goes to an open-weight model running on your own machine through [Ollama](https://ollama.com), so nothing is sent to a third-party AI service and it costs nothing to run.

The app is a Progressive Web App (PWA): one web app that can be installed on Android, iOS, Windows, macOS and Linux from the browser.

```
PWA (React + Vite)  --HTTP-->  Backend (Python FastAPI)  --HTTP-->  Ollama (local model, CPU is fine)
                                     |
                                  SQLite (mistake log)
```

## Features (phase 1)

- **Grammar**: corrected text plus each change with a category (tense, article, preposition...) and a one-line reason.
- **Rephrase**: the same sentence as simpler, formal, casual, natural or concise.
- **Chat**: role-play on a topic; corrections for each of your messages appear under it without interrupting the conversation.
- **Progress**: your most common mistake categories and recent corrections.
- **Level**: CEFR A2 to C1 changes how the coach explains things.

## Requirements

- 8 GB RAM minimum, 16 GB recommended. No graphics card needed.
- [Ollama](https://ollama.com/download)
- Python 3.11 or newer
- Node.js 20 or newer

## Run it locally (Windows)

Open three terminals (PowerShell). Commands for macOS/Linux differ only where noted.

**1. Start the model**

Install Ollama, then download a model (about 2.5 GB):

```powershell
ollama pull qwen3:4b
```

Ollama runs in the background after install. If replies are too slow on your laptop, use a smaller model: `ollama pull qwen3:1.7b`, then set `$env:COACH_MODEL="qwen3:1.7b"` before step 2. `gemma3:4b` is another good choice.

**2. Start the backend**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**3. Start the app**

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. A red banner tells you if the backend, Ollama or the model is missing.

To try it on your phone, connect it to the same Wi-Fi and open the `Network:` address that `npm run dev` prints. Installing it as an app (Add to Home Screen) needs HTTPS, so that comes with deployment.

## Configuration

Backend environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `COACH_MODEL` | `qwen3:4b` | Any Ollama model name |
| `OLLAMA_URL` | `http://localhost:11434` | Where Ollama is running |
| `COACH_DB` | `coach.db` | SQLite file for the mistake log |
| `COACH_LLM_TIMEOUT` | `180` | Seconds to wait for the model |
| `COACH_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated origins allowed to call the API |

Frontend: set `VITE_API_URL` when the backend is on a different host from the app.

## Tests

```powershell
cd backend
pip install -r requirements-dev.txt
pytest
```

The tests use a fake model, so they run without Ollama.

## Roadmap

1. Text coach for English (this version)
2. Voice: speak and listen with whisper.cpp and Piper, both on CPU
3. More languages, explanations in your native language, accounts, and hosting on a free cloud VM
