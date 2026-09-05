# Install Dungeon Escape for the current user, then launch it.
$ErrorActionPreference = "Stop"
$repository = "https://raw.githubusercontent.com/baneastefan1-design/Dungeons-n-stuff-/main"
$installDir = Join-Path $env:LOCALAPPDATA "Dungeon Escape"
$launcher = Join-Path $installDir "DungeonEscape.cmd"

$python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { throw "Python 3 is required. Install it, then run this command again." }
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $installDir "backend"), (Join-Path $installDir "frontend\assets") | Out-Null
foreach ($module in @("dungeon_improved.py", "game.py", "pathfinding.py", "rendering.py", "asset_manager.py", "__init__.py")) {
    Invoke-WebRequest "$repository/backend/$module" -OutFile (Join-Path $installDir "backend\$module")
}
Invoke-WebRequest "$repository/frontend/assets/start_screen.png" -OutFile (Join-Path $installDir "frontend\assets\start_screen.png")
$illustratedAssets = @(
    "hero/idle.png", "hero/walk.png",
    "dragon/sleeping.png", "dragon/awake.png", "dragon/phantom.png",
    "tiles/floor_1.png", "tiles/floor_2.png",
    "tiles/wall_horizontal.png", "tiles/wall_vertical.png",
    "portal.png", "treasure_open.png", "scorch.png", "fog.png"
)
foreach ($asset in $illustratedAssets) {
    $destination = Join-Path $installDir "frontend\assets\illustrated\$asset"
    New-Item -ItemType Directory -Force -Path (Split-Path $destination) | Out-Null
    Invoke-WebRequest "$repository/frontend/assets/illustrated/$asset" -OutFile $destination
}
& $python -m venv (Join-Path $installDir ".venv")
& (Join-Path $installDir ".venv\Scripts\python.exe") -m pip install --quiet --disable-pip-version-check pygame-ce

@"
@echo off
Set-Location $installDir
& "$installDir\.venv\Scripts\python.exe" -m backend.dungeon_improved @args
"@ | Set-Content -Encoding Ascii $launcher

Write-Host "Dungeon Escape installed. Run it anytime with: $launcher"
& $launcher
