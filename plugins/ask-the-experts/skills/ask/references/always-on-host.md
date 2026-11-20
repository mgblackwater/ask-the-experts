# Always-on host (use the app from your phone)

Run Ask the Experts on a PC that stays on, such as an Intel NUC or a home server, and open it from your phone or laptop anywhere over your own Tailscale network. Nothing is exposed to the internet.

```
 phone / laptop ──(Tailscale, private)──► always-on PC
                                          ├─ the app (roundtable_server.py, port 8766)
                                          ├─ the moderator (headless_moderator.py → claude -p per event)
                                          └─ your home folder (chats, personas)  ──Syncthing──► your laptop (copy)
```

## What runs where

- **The app** serves the chat list and chats on `127.0.0.1:8766`. `tailscale serve` shares it on your tailnet over HTTPS, so only your own devices can reach it.
- **The moderator** watches the app's inbox. For each batch of events about one chat, it runs Claude Code headless with this skill: it briefs the thinkers, posts turns, and carries on until the chat needs you. Each chat keeps its own Claude session (`--resume`), recorded in `chats/.moderator-state.json`, so context survives restarts and reboots. Persona builds get a fresh session each.
- **Only one machine runs the app and moderator.** Your laptop opens the host's address too. If two machines ran it on synced folders, their moderators would write the same chats.

## Set up (Windows)

1. On the PC, sign in to Claude Code as you, and install the plugin:
   `claude plugin install ask-the-experts@blackwater-skills`
2. Install Python 3 from python.org and tick "Add to PATH". Install Tailscale and sign in.
3. Run the setup script once in PowerShell:
   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\plugins\cache\blackwater-skills\ask-the-experts\<version>\skills\ask\scripts\setup_windows.ps1"`
   It uses your settings (or creates them), copies `host.py` into the home folder, registers two start-at-sign-in tasks ("Ask the Experts - App" and "Ask the Experts - Moderator"), starts them, and runs `tailscale serve`. It prints your address, for example `https://nuc.your-tailnet.ts.net/`.
4. **Keep it available:** set Windows to sign in automatically (`netplwiz`, or Settings → Accounts → Sign-in options), and set Power → Sleep to **Never**. The tasks start at sign-in, because Claude Code needs your user profile.

On macOS or Linux, run the same two programs at login instead: `python3 -I <home>/host.py server` and `python3 -I <home>/host.py moderator` (launchd, systemd or a login item).

## Your phone

Open the address with Tailscale on, then Share → **Add to Home Screen**: it opens full-screen with its own icon. If you keep Tailscale off most of the time, turn it on before opening the app, or use Tailscale's on-demand (iOS) or always-on VPN (Android) setting just for your tailnet.

## Keep a copy on your laptop (Syncthing)

1. Install Syncthing on both machines and pair them.
2. Share the home folder from the host as **Send Only**, and add it on the laptop as **Receive Only**, so only the host writes.
3. Ignore `chats/.ask-the-experts-inbox.jsonl`, `chats/.moderator-state.json`, `chats/.moderator.log` and `chats/.briefs` (an `.stignore` file in the folder).

If you use git history in the home folder, commit on the host only.

## Updates and troubleshooting

- **Plugin update:** run `claude plugin update ask-the-experts@blackwater-skills`, then restart both tasks (Task Scheduler, or sign out and in). `host.py` always starts the newest installed version.
- **Logs:** `chats\.moderator.log` shows each run and how it ended. If a chat seems stuck, look there first.
- **Nothing answers on the phone:** check Tailscale is on, then `tailscale serve status` on the host, then open `http://127.0.0.1:8766/` on the host itself.
- **Undo:** `Unregister-ScheduledTask -TaskName "Ask the Experts - App","Ask the Experts - Moderator" -Confirm:$false` and `tailscale serve reset`.
