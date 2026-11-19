#!/bin/sh
# Install the shared launcher and desktop metadata into a portable prefix.
set -eu
prefix=${1:?Usage: install.sh PREFIX}
appid=net.playhi.fast-screen-off
install -Dm755 "deepin/files/bin/$appid.sh" "$prefix/bin/fast-screen-off"
install -Dm644 "deepin/entries/icons/hicolor/scalable/apps/$appid.svg" "$prefix/share/icons/hicolor/scalable/apps/$appid.svg"
install -d "$prefix/share/applications"
sed 's|^Exec=.*|Exec=fast-screen-off|' "deepin/entries/applications/$appid.desktop" > "$prefix/share/applications/$appid.desktop"
chmod 644 "$prefix/share/applications/$appid.desktop"
install -Dm644 "$appid.metainfo.xml" "$prefix/share/metainfo/$appid.metainfo.xml"
install -Dm644 deepin/LICENSE "$prefix/share/licenses/$appid/LICENSE"
install -Dm755 check-runtime.sh "$prefix/libexec/fast-screen-off/check-runtime.sh"
