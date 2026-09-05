#!/usr/bin/env bash
# Install Dungeon Escape for the current user, then launch it.
set -euo pipefail

REPOSITORY="https://raw.githubusercontent.com/baneastefan1-design/Dungeons-n-stuff-/main"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/dungeon-escape"
BIN_DIR="$HOME/.local/bin"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required. Install it, then run this command again." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR/backend" "$INSTALL_DIR/frontend/assets" "$BIN_DIR"
for module in dungeon_improved.py game.py pathfinding.py rendering.py asset_manager.py __init__.py; do
    curl -fsSL "$REPOSITORY/backend/$module" -o "$INSTALL_DIR/backend/$module"
done
curl -fsSL "$REPOSITORY/frontend/assets/start_screen.png" -o "$INSTALL_DIR/frontend/assets/start_screen.png"
for asset in \
    hero/idle.png hero/walk.png \
    dragon/sleeping.png dragon/awake.png dragon/phantom.png \
    tiles/floor_1.png tiles/floor_2.png \
    tiles/wall_horizontal.png tiles/wall_vertical.png \
    portal.png treasure_open.png scorch.png fog.png; do
    mkdir -p "$INSTALL_DIR/frontend/assets/illustrated/$(dirname "$asset")"
    curl -fsSL "$REPOSITORY/frontend/assets/illustrated/$asset" -o "$INSTALL_DIR/frontend/assets/illustrated/$asset"
done
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/python" -m pip install --quiet --disable-pip-version-check pygame-ce

cat > "$BIN_DIR/dungeon-escape" <<EOF
#!/usr/bin/env bash
cd "$INSTALL_DIR"
exec "$INSTALL_DIR/.venv/bin/python" -m backend.dungeon_improved "\$@"
EOF
chmod +x "$BIN_DIR/dungeon-escape"

echo "Dungeon Escape installed. Run it anytime with: dungeon-escape"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Add $BIN_DIR to your PATH to use that command in new terminals."
fi
exec "$BIN_DIR/dungeon-escape"
