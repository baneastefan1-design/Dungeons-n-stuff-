# Install Dungeon Escape for the current user, then launch it.
$ErrorActionPreference = "Stop"
$repository = "https://raw.githubusercontent.com/baneastefan1-design/Dungeons-n-stuff-/main"
$installDir = Join-Path $env:LOCALAPPDATA "Dungeon Escape"
$launcher = Join-Path $installDir "DungeonEscape.cmd"

$python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { throw "Python 3 is required. Install it, then run this command again." }
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
Invoke-WebRequest "$repository/dungeon_improved.py" -OutFile (Join-Path $installDir "dungeon_improved.py")
& $python -m venv (Join-Path $installDir ".venv")
& (Join-Path $installDir ".venv\Scripts\python.exe") -m pip install --quiet --disable-pip-version-check pygame-ce

@"
@echo off
"$installDir\.venv\Scripts\python.exe" "$installDir\dungeon_improved.py" %*
"@ | Set-Content -Encoding Ascii $launcher

Write-Host "Dungeon Escape installed. Run it anytime with: $launcher"
& $launcher
