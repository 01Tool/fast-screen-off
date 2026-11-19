#!/bin/sh
set -eu
[ "$(uname -m)" = x86_64 ] || { echo 'This recipe currently targets x86_64.' >&2; exit 2; }
root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
output=${1:-"$root/assets"}
mkdir -p "$output"
output=$(CDPATH='' cd -- "$output" && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
version=$(python3 "$root/scripts/prepare-portable.py" linglong "$work")
cd "$work"
ll-builder build
ll-builder run /bin/sh /opt/apps/net.playhi.fast-screen-off/files/libexec/fast-screen-off/check-runtime.sh
ll-builder export --output "$output/fast-screen-off_${version}_x86_64.uab"
test -s "$output/fast-screen-off_${version}_x86_64.uab"
