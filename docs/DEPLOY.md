# Put the coach online for free (Oracle Cloud)

This runs the whole coach (model, backend and app) on an Oracle Cloud **Always Free** server, with HTTPS and a login, so you can install it on your phone. It costs nothing as long as you stay within the Always Free limits. Oracle asks for a card at sign-up to verify you; Always Free resources are not charged.

What you get: `https://<your-server-ip>.sslip.io`, protected by a username and password, with a free Let's Encrypt certificate that Caddy renews automatically.

Oracle's console changes from time to time, so button names below may differ slightly.

## 1. Create the account

1. Sign up at https://www.oracle.com/cloud/free/.
2. Pick a **home region** close to you (for India: Mumbai or Hyderabad). You can't change it later, and Always Free servers can only be created there.

## 2. Create the server

1. In the console, go to **Compute > Instances > Create instance**.
2. **Image**: Canonical Ubuntu 24.04 (the aarch64 build is chosen automatically for the shape below).
3. **Shape**: Ampere, `VM.Standard.A1.Flex`, **4 OCPUs and 24 GB memory** if your account allows it. Check your free Arm limit under **Governance & Administration > Limits, Quotas and Usage** first; some accounts now get 2 OCPUs and 12 GB, which is still enough for a 4B model (replies are just slower).
4. **Networking**: keep the default new VCN and public subnet, with "Assign a public IPv4 address" on.
5. **SSH keys**: choose "Generate a key pair" and download the private key.
6. **Boot volume**: 50 GB is enough (Always Free covers up to 200 GB in total).
7. Click **Create**. If you see "Out of capacity", try another availability domain or try again later; free Ampere capacity comes and goes.

Copy the **Public IP address** from the instance page.

## 3. Open ports 80 and 443

1. On the instance page, click the subnet, then its **Default Security List**.
2. **Add Ingress Rules** twice, both with source CIDR `0.0.0.0/0`, IP protocol TCP:
   - destination port `80`
   - destination port `443`

(The setup script opens the same ports in the server's own firewall.)

## 4. Install and start the coach

From your PC (PowerShell), connect to the server. Use the key file you downloaded and your server's IP:

```powershell
ssh -i C:\path\to\ssh-key.key ubuntu@YOUR_SERVER_IP
```

If Windows complains that the key's permissions are too open, run this once first:
`icacls C:\path\to\ssh-key.key /inheritance:r /grant:r "$($env:USERNAME):R"`

Then, on the server:

```bash
git clone https://github.com/RajanNalawade/AI-English-Coach.git
cd AI-English-Coach
bash deploy/setup.sh
```

The script installs Docker, opens the firewall, asks you for a username and password for the app, builds everything and downloads the model. The first run takes about 10 to 15 minutes.

When it finishes it prints your address, for example `https://140.238.12.34.sslip.io`.

## 5. Use it on your phone

1. Open the address in Chrome (Android) or Safari (iPhone) and sign in.
2. **Android**: menu > **Install app** (or Add to Home screen). **iPhone**: Share > **Add to Home Screen**.
3. The mic works here because the site is HTTPS. The first voice message downloads the speech model, so it is slow once.

## Updating later

```bash
cd AI-English-Coach
git pull
cd deploy
sudo docker compose up -d --build
```

## Useful commands (on the server, in `AI-English-Coach/deploy`)

| What | Command |
| --- | --- |
| See logs | `sudo docker compose logs -f backend` |
| Restart | `sudo docker compose restart` |
| Stop | `sudo docker compose down` |
| Try another model | `sudo docker compose exec ollama ollama pull gemma3:4b`, set `COACH_MODEL=gemma3:4b` in `.env`, then `sudo docker compose up -d` |
| Change the password | `rm .env`, then `bash setup.sh` again |

## Optional: faster replies from a hosted open model

By default every answer comes from the Ollama model on your server, which is free and private. If replies feel slow, you can point the coach at a hosted open model with an OpenAI-compatible API (DeepInfra, Groq, OpenRouter). The local model stays as the fallback, so the app keeps working if the provider is down or your credit runs out.

In `deploy/.env`, set:

```
COACH_LLM_PROVIDER=openai
COACH_REMOTE_URL=https://api.deepinfra.com/v1/openai
COACH_REMOTE_API_KEY=your-key
COACH_REMOTE_MODEL=the-model-name-from-the-provider
```

then run `sudo docker compose up -d`. Your text goes to that provider while this is on. Use prepaid credits with auto top-up off, and never paste the key into a chat. Set `COACH_LLM_PROVIDER=ollama` to switch back.

Your mistake log and downloaded models are kept in Docker volumes, so they survive restarts and updates.
