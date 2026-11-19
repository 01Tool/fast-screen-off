#!/bin/sh
# Run on Debian 12 amd64, the oldest supported portable build baseline.
set -eu
[ "$(uname -m)" = x86_64 ] || { echo 'This recipe currently targets x86_64.' >&2; exit 2; }
# shellcheck source=/dev/null
. /etc/os-release
if [ "$ID" != debian ] || [ "${VERSION_ID%%.*}" != 12 ]; then
    echo 'Build the AppImage on Debian 12 to preserve its glibc baseline.' >&2
    exit 2
fi
root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
output=${1:-"$root/assets"}
mkdir -p "$output"
output=$(CDPATH='' cd -- "$output" && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
version=$(python3 "$root/scripts/prepare-portable.py" appimage "$work")
cd "$work/source"
sh install.sh "$work/AppDir/usr"
cd "$work"
# Debian 12 predates the wlopm package; build against this baseline's libraries.
curl -fL --retry 3 -o wlopm.tar.gz \
    https://deb.debian.org/debian/pool/main/w/wlopm/wlopm_0.1.0.orig.tar.gz
printf '%s\n' '1f3d7d3ff5d43de634b87e6ca951238ad8bef9ef6bdea5b904b8293f7f000fb1  wlopm.tar.gz' | sha256sum -c -
tar -xf wlopm.tar.gz
make -C wlopm-0.1.0 -j2
install -Dm644 wlopm-0.1.0/LICENSE AppDir/usr/share/licenses/wlopm/LICENSE
curl -fL --retry 3 -o linuxdeploy-x86_64.AppImage \
    https://github.com/linuxdeploy/linuxdeploy/releases/download/1-alpha-20251107-1/linuxdeploy-x86_64.AppImage
curl -fL --retry 3 -o linuxdeploy-plugin-qt-x86_64.AppImage \
    https://github.com/linuxdeploy/linuxdeploy-plugin-qt/releases/download/1-alpha-20250213-1/linuxdeploy-plugin-qt-x86_64.AppImage
printf '%s\n' \
    'c20cd71e3a4e3b80c3483cef793cda3f4e990aca14014d23c544ca3ce1270b4d  linuxdeploy-x86_64.AppImage' \
    '15106be885c1c48a021198e7e1e9a48ce9d02a86dd0a1848f00bdbf3c1c92724  linuxdeploy-plugin-qt-x86_64.AppImage' | sha256sum -c -
chmod 755 ./*.AppImage
export APPIMAGE_EXTRACT_AND_RUN=1
export QMAKE=/usr/bin/qmake
export EXTRA_PLATFORM_PLUGINS='libqwayland-egl.so;libqwayland-generic.so;libqoffscreen.so'
export OUTPUT="$output/fast-screen-off_${version}_x86_64.AppImage"
./linuxdeploy-x86_64.AppImage --appdir AppDir \
    --executable /usr/bin/xset --executable /usr/bin/gdbus \
    --executable "$work/wlopm-0.1.0/wlopm" --executable /usr/bin/kscreen-doctor \
    --executable /usr/bin/notify-send \
    --desktop-file AppDir/usr/share/applications/net.playhi.fast-screen-off.desktop \
    --icon-file AppDir/usr/share/icons/hicolor/scalable/apps/net.playhi.fast-screen-off.svg \
    --plugin qt
# Keep Debian's dependency copyright/license notices and an exact package list.
for copyright in /usr/share/doc/*/copyright; do
    package=$(basename "$(dirname "$copyright")")
    install -Dm644 "$copyright" "AppDir/usr/share/doc/$package/copyright"
done
dpkg-query -W > AppDir/usr/share/doc/build-packages.txt
./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage
"$OUTPUT" --version
PATH="$work/AppDir/usr/bin:$PATH" \
LD_LIBRARY_PATH="$work/AppDir/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
QT_PLUGIN_PATH="$work/AppDir/usr/plugins" \
    sh AppDir/usr/libexec/fast-screen-off/check-runtime.sh
