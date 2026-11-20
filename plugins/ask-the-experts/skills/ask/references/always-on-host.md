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
   `claude plugin install ask-the-experts@ask-the-experts`
2. Install Python 3 from python.org and tick "Add to PATH". Install Tailscale and sign in.
3. Run the setup script once in PowerShell:
   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\plugins\cache\ask-the-experts\ask-the-experts\<version>\skills\ask\scripts\setup_windows.ps1"`
   It uses your settings (or creates them), copies `host.py` into the home folder, registers two start-at-sign-in tasks ("Ask the Experts - App" and "Ask the Experts - Moderator"), starts them, and runs `tailscale serve`. It shares the app on its own HTTPS port (8766), so anything else you already share on the tailnet address keeps working, and prints your address, for example `https://nuc.your-tailnet.ts.net:8766/`.
4. **Keep it available:** set Windows to sign in automatically: in Settings → Accounts → Sign-in options, turn off "For improved security, only allow Windows Hello sign-in" (it hides the next option), then run `netplwiz` and untick "Users must enter a user name and password to use this computer", and set Power → Sleep to **Never**. The tasks start at sign-in, because Claude Code needs your user profile.

On macOS or Linux, run the same two programs at login instead: `python3 -I <home>/host.py server` and `python3 -I <home>/host.py moderator` (launchd, systemd or a login item).

## Your phone

Open the address with Tailscale on, then Share → **Add to Home Screen**: it opens full-screen with its own icon. If you keep Tailscale off most of the time, turn it on before opening the app, or use Tailscale's on-demand (iOS) or always-on VPN (Android) setting just for your tailnet.

## Keep a copy on your laptop: git sync (private GitHub repo)

The home folder can sync through a **private** repository. The host is the only machine that commits and pushes, which the moderator does after every run. Your laptop only pulls.

1. **Where the data is now** (for example your laptop): run Setup and choose "sync through a private GitHub repo", or create the private repo yourself and run
   `python3 -I <skill>/scripts/home_sync.py init https://github.com/<you>/ask-the-experts-home.git`
2. **On the host** (signed in to GitHub, e.g. `gh auth login` and `gh auth setup-git`), before running the setup script:
   `python -I <skill>\scripts\home_sync.py clone https://github.com/<you>/ask-the-experts-home.git`
   Then set `"sync_role": "host"` in `%USERPROFILE%\.claude\ask-the-experts\config.json`.
3. **On the laptop**, set `"sync_role": "copy"` in its config. From then on, run `home_sync.py pull` whenever you want the latest. Don't run the app or moderator there while the host is the host.

What syncs: chats and their attachments, personas and avatars. What stays local: the app's inbox, the moderator's state and log, brief files, and persona source documents (`persona-sources/`).

`"sync_sources": true` would sync persona source documents too, but think twice. They're raw uploads (emails, notes, write-ups), often work material and other people's words. Your employer's rules may not allow them in personal cloud storage, a private repo is one setting away from public, and anything in git history is hard to remove. The built personas already carry what matters from them.

## Keep a copy on your laptop (Syncthing, no cloud)

1. Install Syncthing on both machines and pair them.
2. Share the home folder from the host as **Send Only**, and add it on the laptop as **Receive Only**, so only the host writes.
3. Ignore `chats/.ask-the-experts-inbox.jsonl`, `chats/.moderator-state.json`, `chats/.moderator.log` and `chats/.briefs` (an `.stignore` file in the folder).

If you use git history in the home folder, commit on the host only. Use Syncthing or git sync, not both.

## Updates and troubleshooting

- **Plugin update:** run `claude plugin update ask-the-experts@ask-the-experts`, then restart both tasks (Task Scheduler, or sign out and in). `host.py` always starts the newest installed version.
- **Logs:** `chats\.moderator.log` shows each run and how it ended. If a chat seems stuck, look there first.
- **Nothing answers on the phone:** check Tailscale is on, then `tailscale serve status` on the host, then open `http://127.0.0.1:8766/` on the host itself.
- **Undo:** `Unregister-ScheduledTask -TaskName "Ask the Experts - App","Ask the Experts - Moderator" -Confirm:$false` and `tailscale serve reset`.
