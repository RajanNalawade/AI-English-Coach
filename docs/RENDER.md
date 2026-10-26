# Put the coach online for free (Render + Groq)

This runs the coach as one free **Render** web service, with **Groq's** free API doing the AI work (chat replies and speech-to-text). Neither needs a card. You get a fixed HTTPS address that works on your phone even when your PC is off, protected by a username and password.

Things to know:

- **Privacy:** your text and voice recordings go to Groq to be processed. Your PC setup (Ollama) stays fully private; this one doesn't.
- **Daily limits:** Groq's free plan allows about 1,000 AI requests a day. A chat message uses two (reply and corrections), so that's roughly 500 messages a day. More than enough for one person.
- **Sleep:** a free Render service sleeps after 15 minutes without visits. The first visit after that takes about a minute to wake up.
- **Progress tab:** free Render services have no permanent disk, so the mistake log resets whenever the service restarts or sleeps.

Every change merged into `main` redeploys automatically.

## 1. Get a free Groq API key

1. Sign up at https://console.groq.com (Google or email; no card).
2. Open **API Keys** and click **Create API Key**. Name it `ai-english-coach`.
3. Copy the key (it starts with `gsk_`). It's shown only once. Paste it only into Render in step 3, never in a chat.

## 2. Create a free Render account

Sign up at https://dashboard.render.com/register. Choosing **GitHub** is easiest, because Render needs access to your repository anyway. No card is needed for free services.

## 3. Deploy with the Blueprint

1. Open https://dashboard.render.com/blueprint/new (or **New > Blueprint** in the dashboard).
2. Connect your GitHub account if asked, and pick the **AI-English-Coach** repository. Render reads `render.yaml` from it.
3. **Blueprint name**: `ai-english-coach`.
4. Render asks for the two secret values:
   - `COACH_PASSWORD`: a password you make up for signing in to the app.
   - `COACH_REMOTE_API_KEY`: the Groq key from step 1.
5. Click **Deploy Blueprint**. The first build takes about 5 minutes.

## 4. Open it

1. In the Render dashboard, open the **ai-english-coach** service. Its address is at the top, like `https://ai-english-coach-xxxx.onrender.com`.
2. Open it and sign in with username `coach` and your `COACH_PASSWORD`.
3. On your phone: **Install app** (Android Chrome) or **Share > Add to Home Screen** (iPhone Safari). The mic works because the address is HTTPS.

## Change the model

The Blueprint uses `openai/gpt-oss-20b` on Groq. To try another free Groq model, edit `COACH_REMOTE_MODEL` under the service's **Environment** tab in Render (for example `qwen/qwen3.6-27b`, which Groq marks as a preview), then save. Render restarts the service.

## If something goes wrong

- **Deploy failed:** open the service's **Logs** and send the last lines (without any keys).
- **"The hosted model failed: ... 401":** the Groq key is wrong. Paste it again under **Environment > COACH_REMOTE_API_KEY**.
- **"... 429":** you've reached Groq's per-minute or daily limit. Wait a minute, or until tomorrow.
