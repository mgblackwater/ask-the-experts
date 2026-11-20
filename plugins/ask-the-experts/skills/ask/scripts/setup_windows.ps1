<#
Ask the Experts: set up an always-on Windows host (an Intel NUC, a home PC).

Run once in PowerShell, as the Windows user who is signed in to Claude Code:
  powershell -ExecutionPolicy Bypass -File "<plugin>\skills\ask\scripts\setup_windows.ps1"

What it does (safe to run again):
  1. Checks Python 3, Claude Code and (optionally) Tailscale.
  2. Uses your Ask the Experts settings, or creates them with a home folder of
     %USERPROFILE%\Documents\ask-the-experts (chats\, personas\, persona-sources\, avatars\).
  3. Copies host.py into the home folder, so start-up never depends on a plugin version folder.
  4. Registers two tasks that start when you sign in and restart if they stop:
     "Ask the Experts - App" (the web app) and "Ask the Experts - Moderator" (the always-on moderator).
  5. Starts both, and shares the app on your tailnet with `tailscale serve` (private to your devices).

To undo: Unregister-ScheduledTask -TaskName "Ask the Experts - App","Ask the Experts - Moderator" -Confirm:$false
          tailscale serve reset
#>
param(
  [string]$HomeDir = "$env:USERPROFILE\Documents\ask-the-experts",
  [int]$Port = 8766
)
$ErrorActionPreference = "Stop"
function Say($m) { Write-Host "  $m" }
function Ok($m) { Write-Host "  [ok] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  [!] $m" -ForegroundColor Yellow }

Write-Host "`nAsk the Experts: always-on host setup`n"

# 1. Tools -------------------------------------------------------------------
$py = $null
foreach ($c in @("py", "python", "python3")) {
  $cmd = Get-Command $c -ErrorAction SilentlyContinue
  if ($cmd) {
    $pyArgs = if ($c -eq "py") { @("-3", "-c") } else { @("-c") }
    try { $exe = & $cmd.Source @pyArgs "import sys; print(sys.executable)" 2>$null } catch { $exe = $null }
    if ($exe -and (Test-Path $exe)) { $py = $exe.Trim(); break }
  }
}
if (-not $py) { throw "Python 3 isn't installed. Install it from python.org (tick 'Add to PATH'), then run this again." }
$pyw = Join-Path (Split-Path $py) "pythonw.exe"
if (-not (Test-Path $pyw)) { $pyw = $py }
Ok "Python: $py"

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) { throw "Claude Code isn't on PATH. Install it and sign in, then run this again." }
Ok "Claude Code: $($claude.Source)"

$plugins = Join-Path $env:USERPROFILE ".claude\plugins\cache\blackwater-skills\ask-the-experts"
$latest = Get-ChildItem $plugins -Directory -ErrorAction SilentlyContinue |
  Sort-Object { [version]($_.Name -replace '[^0-9.]', '') } | Select-Object -Last 1
if (-not $latest) { throw "The ask-the-experts plugin isn't installed. Run: claude plugin install ask-the-experts@blackwater-skills" }
$scripts = Join-Path $latest.FullName "skills\ask\scripts"
Ok "Plugin: ask-the-experts $($latest.Name)"

# 2. Settings and home folder ---------------------------------------------------
$cfgDir = Join-Path $env:USERPROFILE ".claude\ask-the-experts"
$cfgPath = Join-Path $cfgDir "config.json"
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
if (Test-Path $cfgPath) {
  $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
  Ok "Using existing settings: $cfgPath"
  if ($cfg.home_dir) { $HomeDir = $cfg.home_dir } elseif ($cfg.logs_dir) { $HomeDir = Split-Path $cfg.logs_dir }
} else {
  $cfg = [ordered]@{
    user_name = "You"; home_dir = $HomeDir; logs_dir = (Join-Path $HomeDir "chats"); private_personas_dir = (Join-Path $HomeDir "personas")
    port = $Port; refresh_after_days = 90; remind_every_days = 30; last_freshness_check = (Get-Date -Format "yyyy-MM-dd")
    host_name = "Claude"; chat_history = "none"
  }
  ($cfg | ConvertTo-Json) | Set-Content -Encoding UTF8 $cfgPath
  Ok "Created settings: $cfgPath (run /ask-the-experts:ask setup in Claude Code later to change your name)"
}
foreach ($d in @("chats", "personas", "persona-sources", "avatars")) { New-Item -ItemType Directory -Force -Path (Join-Path $HomeDir $d) | Out-Null }
Ok "Home folder: $HomeDir"

# 3. Launcher --------------------------------------------------------------------
$hostPy = Join-Path $HomeDir "host.py"
Copy-Item (Join-Path $scripts "host.py") $hostPy -Force
Ok "Launcher: $hostPy"

# 4. Start-at-sign-in tasks ------------------------------------------------------
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
  -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
foreach ($t in @(@{Name = "Ask the Experts - App"; Arg = "server"}, @{Name = "Ask the Experts - Moderator"; Arg = "moderator"})) {
  $action = New-ScheduledTaskAction -Execute $pyw -Argument "-I `"$hostPy`" $($t.Arg)" -WorkingDirectory $HomeDir
  Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Ask the Experts ($($t.Arg)). Starts at sign-in." -Force | Out-Null
  Stop-ScheduledTask -TaskName $t.Name -ErrorAction SilentlyContinue
  Start-ScheduledTask -TaskName $t.Name
  Ok "Task registered and started: $($t.Name)"
}

# 5. Check, then share on the tailnet ---------------------------------------------
Start-Sleep -Seconds 3
try {
  $ping = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/ping" -TimeoutSec 5
  Ok "App is up: version $($ping.version) on http://127.0.0.1:$Port/"
} catch { Warn "The app didn't answer on port $Port yet. Check Task Scheduler, or run: & `"$py`" -I `"$hostPy`" server" }

$ts = Get-Command tailscale -ErrorAction SilentlyContinue
if ($ts) {
  try {
    & $ts.Source serve --bg $Port | Out-Null
    $dns = (& $ts.Source status --json | ConvertFrom-Json).Self.DNSName.TrimEnd(".")
    Ok "Shared on your tailnet: https://$dns/"
    Say "On your phone: turn Tailscale on, open that address, then Share > Add to Home Screen."
  } catch { Warn "tailscale serve failed: $($_.Exception.Message). Try: tailscale serve --bg $Port" }
} else { Warn "Tailscale isn't installed; the app is only reachable on this PC." }

Write-Host "`nDone. Keep this PC awake and signed in (see the NUC guide). Moderator log: $(Join-Path $HomeDir 'chats\.moderator.log')`n"
