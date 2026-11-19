#!/bin/sh
# Headless dependency checks: none of these commands changes display power.
set -eu
for helper in fast-screen-off xset gdbus wlopm kscreen-doctor; do
    command -v "$helper"
done
fast-screen-off --version
xset -version
gdbus help >/dev/null
wlopm --help >/dev/null
QT_QPA_PLATFORM=offscreen kscreen-doctor --help >/dev/null
