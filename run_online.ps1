# Start the latest game directly from GitHub on Windows PowerShell.
$ErrorActionPreference = "Stop"
$repository = "https://raw.githubusercontent.com/baneastefan1-design/Dungeons-n-stuff-/main"
$workDir = Join-Path ([System.IO.Path]::GetTempPath()) ("dungeon-escape-" + [guid]::NewGuid())

try {
    New-Item -ItemType Directory -Path $workDir | Out-Null
    $python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { throw "Python 3 is required. Install it, then run this command again." }
    $env:DUNGEON_STATS_FILE = Join-Path $env:APPDATA "Dungeon Escape\dungeon_stats.json"
    Invoke-WebRequest "$repository/dungeon_improved.py" -OutFile (Join-Path $workDir "dungeon_improved.py")
    & $python -m venv (Join-Path $workDir ".venv")
    & (Join-Path $workDir ".venv\Scripts\python.exe") -m pip install --quiet --disable-pip-version-check pygame-ce
    & (Join-Path $workDir ".venv\Scripts\python.exe") (Join-Path $workDir "dungeon_improved.py")
}
finally {
    Remove-Item -Recurse -Force $workDir -ErrorAction SilentlyContinue
}
