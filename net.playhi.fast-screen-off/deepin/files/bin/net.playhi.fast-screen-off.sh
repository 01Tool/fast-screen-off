#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
set -u

usage() {
    cat <<'EOF'
Usage: fast-screen-off [--delay SECONDS] [--help] [--version]
Turn off the displays in the current graphical session (default delay: 0.5s).
Run as your desktop user. Move the mouse or press a key to wake the displays.
EOF
}

fail() {
    printf 'fast-screen-off: %s\n' "$1" >&2
    if command -v notify-send >/dev/null 2>&1; then
        timeout --kill-after=1 5 notify-send --app-name='Fast Screen Off' \
            --icon=net.playhi.fast-screen-off 'Could not turn off the screen' "$1" \
            >/dev/null 2>&1 || :
    fi
    exit 1
}

delay=0.5
while [ "$#" -gt 0 ]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --version) printf '%s\n' 'fast-screen-off 1.1.0.0'; exit 0 ;;
        --delay)
            if [ "$#" -lt 2 ]; then
                printf '%s\n' 'fast-screen-off: --delay needs a number of seconds' >&2
                exit 2
            fi
            delay=$2
            shift 2
            ;;
        *) usage >&2; exit 2 ;;
    esac
done
case "$delay" in
    ''|*[!0-9.]*|.*|*.|*.*.*)
        printf '%s\n' 'fast-screen-off: delay must be a non-negative number, e.g. 0.5' >&2
        exit 2
        ;;
esac

# An explicit session type takes precedence over inherited display variables.
session=${XDG_SESSION_TYPE:-}
if [ -z "$session" ]; then
    if [ -n "${WAYLAND_DISPLAY:-}" ]; then
        session=wayland
    elif [ -n "${DISPLAY:-}" ]; then
        session=x11
    fi
fi
case "$session" in
    x11) [ -n "${DISPLAY:-}" ] || fail 'No X11 display is available.' ;;
    wayland) ;;
    *) fail 'Run this application inside a supported X11 or Wayland desktop session.' ;;
esac

# Let the launching click/key release finish before powering down the displays.
sleep "$delay" || fail 'Could not wait for the requested delay.'

if [ "$session" = x11 ]; then
    command -v xset >/dev/null 2>&1 || fail 'Install x11-xserver-utils for X11 screen power control.'
    timeout --kill-after=1 10 xset dpms force off && exit 0
    fail 'X11 DPMS failed. Check that your X server and display support power management.'
fi

desktop=$(printf '%s' "${XDG_CURRENT_DESKTOP:-${DESKTOP_SESSION:-}}" | tr '[:upper:]' '[:lower:]')
case ":$desktop:" in
    *:kde:*|*:plasma:*)
        if command -v kscreen-doctor >/dev/null 2>&1; then
            # A user-wide QT_QPA_PLATFORM=xcb must not redirect this to XWayland.
            # kscreen-doctor can exit zero even when DPMS is unsupported.
            state=$(QT_QPA_PLATFORM=wayland timeout --kill-after=1 10 kscreen-doctor --dpms show) || \
                fail 'Could not query KDE display power management.'
            case "$state" in
                *'dpms mode for screen '*': on'*|*'dpms mode for screen '*': off'*) ;;
                *) fail 'KDE reports unsupported display power management.' ;;
            esac
            QT_QPA_PLATFORM=wayland timeout --kill-after=1 10 kscreen-doctor --dpms off && exit 0
        fi
        fail 'KDE Wayland screen power control failed. Install libkscreen-bin and check the KWin session.'
        ;;
    *:gnome:*|*:gnome-classic:*)
        if command -v gdbus >/dev/null 2>&1; then
            # Mutter forbids setting PowerSaveMode when its value is -1.
            mode=$(gdbus call --session --timeout 5 \
                --dest org.gnome.Mutter.DisplayConfig \
                --object-path /org/gnome/Mutter/DisplayConfig \
                --method org.freedesktop.DBus.Properties.Get \
                org.gnome.Mutter.DisplayConfig PowerSaveMode) || \
                fail 'Could not query GNOME display power management.'
            case "$mode" in
                '(<0>,)'|'(<1>,)'|'(<2>,)'|'(<3>,)') ;;
                *) fail 'GNOME reports unsupported display power management.' ;;
            esac
            gdbus call --session --timeout 5 \
                --dest org.gnome.Mutter.DisplayConfig \
                --object-path /org/gnome/Mutter/DisplayConfig \
                --method org.freedesktop.DBus.Properties.Set \
                org.gnome.Mutter.DisplayConfig PowerSaveMode '<int32 3>' >/dev/null && exit 0
        fi
        fail 'GNOME screen power control failed. Check the session bus and install libglib2.0-bin.'
        ;;
esac

# Treeland and other compositors exposing zwlr_output_power_manager_v1.
# DISPLAY can refer to XWayland, which cannot power off physical outputs.
if command -v wlopm >/dev/null 2>&1; then
    timeout --kill-after=1 10 wlopm --off '*' && exit 0
fi
fail 'This Wayland session needs wlopm and the output-power-management protocol (e.g. Treeland). Use a supported session if the compositor does not expose it.'

