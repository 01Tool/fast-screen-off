#!/bin/sh
# Build in a temporary tree so repeated/parallel builds never reuse staging files.
set -eu

target=${1:-debian13}
case "$target" in
    debian13|deepin25) ;;
    *) printf 'Usage: %s [debian13|deepin25] [output-directory]\n' "$0" >&2; exit 2 ;;
esac
root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
output=${2:-"$root/assets"}
mkdir -p -- "$output"
output=$(CDPATH='' cd -- "$output" && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
mkdir "$work/source"
cp -R "$root/net.playhi.fast-screen-off/debian" "$root/net.playhi.fast-screen-off/deepin" "$work/source/"
cd "$work/source"
chmod 755 debian/rules deepin/files/bin/net.playhi.fast-screen-off.sh
version=$(dpkg-parsechangelog -S Version)
export FSO_PACKAGE_TARGET="$target"
dpkg-buildpackage --build=binary --no-sign
artifact="net.playhi.fast-screen-off_${version}_${target}_all.deb"
cp "$work/net.playhi.fast-screen-off_${version}_all.deb" "$output/$artifact"
printf 'Built %s/%s\n' "$output" "$artifact"
