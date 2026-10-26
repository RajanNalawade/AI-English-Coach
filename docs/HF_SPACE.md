# Put the coach online for free (Hugging Face Spaces)

This runs the whole coach (Ollama model, backend and app) in one free Hugging Face **Docker Space** on the "CPU basic" hardware (2 vCPU, 16 GB RAM). No card is needed. You get a fixed HTTPS address that works on your phone even when your PC is off, protected by a username and password.

Things to know:

- **Speed:** 2 CPU cores are slower than your PC. Replies take roughly 10 to 40 seconds. For faster replies, use the smaller `qwen3:1.7b` model (see the end of this guide).
- **Sleep:** a free Space sleeps after about 48 hours without visitors. The next visit wakes it in a minute or two.
- **Progress tab:** the mistake log is stored inside the Space, so it resets when the Space restarts or is updated.
- **Public page:** the Space page is public, but the app itself asks for your password before it shows anything or uses the model.

GitHub sends the app to the Space automatically on every change to `main`, using `.github/workflows/hf-space.yml`.

## 1. Create a Hugging Face account

Sign up at https://huggingface.co/join and confirm your email. Your username appears in your Space's address.

## 2. Create the Space

1. Go to https://huggingface.co/new-space.
2. **Space name**: `ai-english-coach`.
3. **Select the Space SDK**: **Docker**, then the **Blank** template.
4. **Space hardware**: **CPU basic · 2 vCPU · 16 GB · FREE**.
5. **Visibility**: **Public**. A private Space can't be opened from the phone app without a Hugging Face login. Your password protects the app either way.
6. Click **Create Space**. It shows an empty page; that's expected.

## 3. Set the app password

In the Space, open **Settings**, scroll to **Variables and secrets**, and click **New secret**:

- Name `COACH_PASSWORD`, value: a password you choose for the app.

Optionally, add a **New variable** named `COACH_USER` with the username you want (the default is `coach`).

## 4. Create a token for GitHub

1. Go to https://huggingface.co/settings/tokens and click **Create new token**.
2. Choose **Write** (or a fine-grained token with write access to just this Space).
3. Name it `github-deploy`, create it, and copy it. Hugging Face shows it only once.

Paste it only in the next step, never in a chat.

## 5. Connect GitHub to the Space

In your GitHub repository, go to **Settings > Secrets and variables > Actions**:

1. **Secrets** tab, **New repository secret**: name `HF_TOKEN`, value: the token from step 4.
2. **Variables** tab, **New repository variable**: name `HF_SPACE`, value: `your-hf-username/ai-english-coach`.

## 6. Deploy

1. In GitHub, open **Actions > Deploy to Hugging Face > Run workflow** (on `main`).
2. When it turns green, open your Space. It shows **Building**. The first build downloads the model into the image and takes about 10 to 20 minutes.
3. When it shows **Running**, open `https://your-hf-username-ai-english-coach.hf.space` and sign in with `coach` (or your `COACH_USER`) and your password.

From now on, every merge to `main` redeploys the Space automatically.

## 7. Install it on your phone

Open the address above in Chrome (Android) or Safari (iPhone) and sign in. Then use **Install app** (Android) or **Share > Add to Home Screen** (iPhone). The mic works because the address is HTTPS.

## Use the faster, smaller model

In the Space, go to **Settings > Variables and secrets** and add a variable `COACH_MODEL` = `qwen3:1.7b`. Then click **Factory rebuild** (in Settings) so the image is rebuilt with that model.

## If something goes wrong

- **Build error:** open the Space's **Logs > Build** and send the last lines.
- **App won't start:** check **Logs > Container**. "Set the COACH_PASSWORD secret" means step 3 is missing.
- **GitHub action skipped:** the `HF_TOKEN` secret or the `HF_SPACE` variable isn't set (step 5).
