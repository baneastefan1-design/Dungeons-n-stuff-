#!/usr/bin/env bash
# Build locally, then transfer and run Dungeon Escape on the Laptop Server.
set -euo pipefail

remote_host="${1:-laptop-server}"
remote_directory="${DUNGEON_ESCAPE_REMOTE_DIR:-/home/rares/docker/dungeon-escape}"
host_port="${DUNGEON_ESCAPE_PORT:-8082}"
image_name="dungeon-escape:latest"
archive_name="dungeon-escape-image.tar.gz"
local_archive="$(mktemp -t dungeon-escape-image.XXXXXX.tar.gz)"

cleanup() {
    rm -f "$local_archive"
}
trap cleanup EXIT

remote_architecture="$(ssh "$remote_host" uname -m)"
case "$remote_architecture" in
    x86_64) image_platform="linux/amd64" ;;
    aarch64|arm64) image_platform="linux/arm64" ;;
    *)
        echo "Unsupported Laptop Server architecture: $remote_architecture"
        exit 1
        ;;
esac

if ssh "$remote_host" "ss -ltn 'sport = :$host_port' | grep -q LISTEN" && ! ssh "$remote_host" "docker ps --format '{{.Names}}' | grep -qx dungeon-escape"; then
    echo "Port $host_port is already in use on $remote_host. Choose another DUNGEON_ESCAPE_PORT."
    exit 1
fi

docker build --platform "$image_platform" --tag "$image_name" .
docker image save "$image_name" | gzip > "$local_archive"

ssh "$remote_host" "mkdir -p '$remote_directory'"
scp "$local_archive" "$remote_host:$remote_directory/$archive_name"
scp compose.laptop-server.yaml "$remote_host:$remote_directory/"

ssh "$remote_host" "cd '$remote_directory'
gunzip -c '$archive_name' | docker image load
DUNGEON_ESCAPE_PORT='$host_port' docker compose -f compose.laptop-server.yaml up -d
rm -f '$archive_name'
docker compose -f compose.laptop-server.yaml ps"

echo "Dungeon Escape is deployed at http://$(ssh "$remote_host" "hostname -I | awk '{print \$1}'"):$host_port"
