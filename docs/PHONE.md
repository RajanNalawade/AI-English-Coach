# Use the coach on your phone (free, through your own PC)

Your PC keeps running the coach, and your phone reaches it privately through [Tailscale](https://tailscale.com) (free for personal use). Tailscale gives your PC an HTTPS address, so the microphone and "install as app" work on the phone. Only devices signed in to your Tailscale account can open it.

It works anywhere your phone has internet (mobile data too), as long as your PC is on and awake.

## One-time setup

1. **On your PC**, install Tailscale and sign in (Google sign-in is fine):
   ```powershell
   winget install --id Tailscale.Tailscale -e
   ```
   Then open Tailscale from the Start menu and log in.
2. **On your phone**, install the Tailscale app (Play Store or App Store) and log in with the **same account**.
3. **Turn on HTTPS** in the Tailscale admin console (https://login.tailscale.com/admin/dns): make sure **MagicDNS** is on, then click **Enable HTTPS** under HTTPS Certificates.

## Each time you want to use it

1. Start the backend as usual (in `backend`, activate the venv, then `uvicorn app.main:app --port 8000`).
2. In `frontend`, build and serve the app:
   ```powershell
   npm run phone
   ```
3. In another PowerShell window, share it over Tailscale (only needed once; it keeps running in the background):
   ```powershell
   tailscale serve --bg 4173
   ```
   It prints your address, for example `https://my-pc.tail1234.ts.net`.
4. On your phone, with Tailscale switched on, open that address.
   - **Android**: Chrome menu > **Install app**.
   - **iPhone**: Safari > Share > **Add to Home Screen**.

To stop sharing: `tailscale serve reset`.

## If something goes wrong

- **The page doesn't load on the phone:** check that Tailscale is connected on both devices and that your PC isn't asleep.
- **"Blocked request. This host is not allowed":** you opened the address of a different machine name. Use the exact `*.ts.net` address that `tailscale serve` printed.
- **Mic doesn't work:** make sure you opened the `https://` address and allowed microphone access.

For an always-on option that doesn't need your PC, see [DEPLOY.md](DEPLOY.md).
