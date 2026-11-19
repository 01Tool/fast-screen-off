#!/bin/sh
set -eu
[ "$(uname -m)" = x86_64 ] || { echo 'This recipe currently targets x86_64.' >&2; exit 2; }
root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
output=${1:-"$root/assets"}
mkdir -p "$output"
output=$(CDPATH='' cd -- "$output" && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
version=$(python3 "$root/scripts/prepare-portable.py" flatpak "$work")
cd "$work"
flatpak-builder --disable-rofiles-fuse --user --install --force-clean --repo=repo build net.playhi.fast-screen-off.json
flatpak build-bundle --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo \
    repo "$output/fast-screen-off_${version}_x86_64.flatpak" net.playhi.fast-screen-off
flatpak run --command=sh net.playhi.fast-screen-off /app/libexec/fast-screen-off/check-runtime.sh
flatpak info --show-permissions net.playhi.fast-screen-off
