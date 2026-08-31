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

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
curl -fsSL "$REPOSITORY/dungeon_improved.py" -o "$INSTALL_DIR/dungeon_improved.py"
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/python" -m pip install --quiet --disable-pip-version-check pygame-ce

cat > "$BIN_DIR/dungeon-escape" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/dungeon_improved.py" "\$@"
EOF
chmod +x "$BIN_DIR/dungeon-escape"

echo "Dungeon Escape installed. Run it anytime with: dungeon-escape"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Add $BIN_DIR to your PATH to use that command in new terminals."
fi
exec "$BIN_DIR/dungeon-escape"
