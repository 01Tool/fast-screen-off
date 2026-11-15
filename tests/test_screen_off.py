"""Exercise the real launcher with isolated, non-destructive command doubles."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "net.playhi.fast-screen-off/deepin/files/bin/net.playhi.fast-screen-off.sh"
SHELL = os.environ.get("FSO_TEST_SHELL") or shutil.which("sh")

STUB = r'''#!/bin/sh
name=${0##*/}
{
    printf '%s' "$name"
    for arg in "$@"; do printf '|%s' "$arg"; done
    printf '\n'
} >> "$FSO_TEST_LOG"
case "$name" in
    sleep) exit "${SLEEP_STATUS:-0}" ;;
    timeout) shift 2; exec "$@" ;;
    xset) exit "${XSET_STATUS:-0}" ;;
    kscreen-doctor)
        printf 'qt-platform|%s\n' "${QT_QPA_PLATFORM:-}" >> "$FSO_TEST_LOG"
        if [ "$2" = show ]; then
            printf '%s\n' "${KSCREEN_STATE-dpms mode for screen eDP-1: on}"
        fi
        exit "${KSCREEN_STATUS:-0}" ;;
    gdbus)
        case "$*" in
            *Properties.Get*)
                printf '(<%s>,)\n' "${GNOME_MODE:-0}"
                exit "${GNOME_GET_STATUS:-0}" ;;
            *Properties.Set*) exit "${GNOME_SET_STATUS:-0}" ;;
        esac
        exit 1 ;;
    wlopm) exit "${WLOPM_STATUS:-0}" ;;
    notify-send) exit "${NOTIFY_STATUS:-0}" ;;
esac
exit 1
'''


class ScreenOffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.log = self.directory / "calls.log"
        for name in ("sleep", "timeout", "xset", "kscreen-doctor", "gdbus", "wlopm", "notify-send"):
            path = self.directory / name
            path.write_text(STUB, encoding="utf-8", newline="\n")
            path.chmod(0o755)

    def run_app(self, *args, **overrides):
        self.log.write_text("", encoding="utf-8")
        env = os.environ.copy()
        for key in ("XDG_SESSION_TYPE", "DISPLAY", "WAYLAND_DISPLAY", "XDG_CURRENT_DESKTOP",
                    "DESKTOP_SESSION", "QT_QPA_PLATFORM", "DBUS_SESSION_BUS_ADDRESS"):
            env.pop(key, None)
        env.update(PATH=str(self.directory) + os.pathsep + env["PATH"],
                   FSO_TEST_LOG=self.log.as_posix(), LC_ALL="C")
        env.update(overrides)
        # Git for Windows' bin/sh wrapper prepends its own tools to PATH.
        # Set the mock path inside the shell before sourcing the launcher.
        mock_path = self.directory.as_posix()
        if os.name == "nt":
            mock_path = "/" + mock_path[0].lower() + mock_path[2:]
        command = 'PATH="$1:$PATH"; export PATH; shift; script=$1; shift; . "$script"'
        result = subprocess.run([SHELL, "-c", command, "test", mock_path, APP.as_posix(), *args], env=env,
                                text=True, capture_output=True, timeout=15)
        self.calls = self.log.read_text(encoding="utf-8")
        return result

    def wayland(self, desktop="Deepin", *args, **overrides):
        env = dict(XDG_SESSION_TYPE="wayland", WAYLAND_DISPLAY="wayland-0",
                   DISPLAY=":0", XDG_CURRENT_DESKTOP=desktop)
        env.update(overrides)
        return self.run_app(*args, **env)

    def test_x11_uses_dpms_after_launch_delay(self):
        result = self.run_app(XDG_SESSION_TYPE="x11", DISPLAY=":0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls, "sleep|0.5\ntimeout|--kill-after=1|10|xset|dpms|force|off\nxset|dpms|force|off\n")

    def test_x11_failure_is_reported(self):
        result = self.run_app(DISPLAY=":0", XSET_STATUS="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("X11 DPMS failed", result.stderr)
        self.assertIn("notify-send|", self.calls)

    def test_explicit_x11_overrides_stale_wayland_variable(self):
        result = self.run_app(XDG_SESSION_TYPE="x11", DISPLAY=":0", WAYLAND_DISPLAY="stale")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("wlopm", self.calls)

    def test_x11_requires_display(self):
        result = self.run_app(XDG_SESSION_TYPE="x11")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("xset|", self.calls)

    def test_no_graphical_session(self):
        result = self.run_app()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("sleep|", self.calls)

    def test_explicit_tty_does_not_use_inherited_display(self):
        result = self.run_app(XDG_SESSION_TYPE="tty", DISPLAY=":0")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("xset|", self.calls)

    def test_treeland_uses_all_output_power_control(self):
        result = self.wayland()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("wlopm|--off|*\n", self.calls)
        self.assertNotIn("xset|", self.calls)

    def test_wayland_detection_without_session_type(self):
        result = self.run_app(WAYLAND_DISPLAY="wayland-0", DISPLAY=":0")
        self.assertEqual(result.returncode, 0)
        self.assertIn("wlopm|--off|*", self.calls)
        self.assertNotIn("xset|", self.calls)

    def test_wayland_failure_never_falls_back_to_xwayland(self):
        result = self.wayland(WLOPM_STATUS="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("output-power-management", result.stderr)
        self.assertNotIn("xset|", self.calls)

    def test_wayland_timeout_is_reported(self):
        result = self.wayland(WLOPM_STATUS="124")
        self.assertEqual(result.returncode, 1)
        self.assertIn("timeout|--kill-after=1|10|wlopm", self.calls)

    def test_kde_forces_native_wayland(self):
        result = self.wayland("KDE", QT_QPA_PLATFORM="xcb")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("kscreen-doctor|--dpms|off", self.calls)
        self.assertIn("qt-platform|wayland", self.calls)
        self.assertNotIn("wlopm", self.calls)

    def test_kde_failure_is_reported(self):
        result = self.wayland("KDE", KSCREEN_STATUS="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("KDE display power", result.stderr)
        self.assertNotIn("xset|", self.calls)

    def test_kde_zero_status_without_dpms_is_not_success(self):
        result = self.wayland("KDE", KSCREEN_STATE="")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("kscreen-doctor|--dpms|off", self.calls)

    def test_gnome_queries_then_sets_typed_power_mode(self):
        result = self.wayland("ubuntu:GNOME")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(self.calls.index("Properties.Get"), self.calls.index("Properties.Set"))
        self.assertIn("PowerSaveMode|<int32 3>", self.calls)
        self.assertNotIn("wlopm", self.calls)

    def test_gnome_all_supported_modes(self):
        for mode in ("0", "1", "2", "3"):
            with self.subTest(mode=mode):
                self.assertEqual(self.wayland("GNOME", GNOME_MODE=mode).returncode, 0)

    def test_gnome_unsupported_mode_is_not_changed(self):
        result = self.wayland("GNOME", GNOME_MODE="-1")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Properties.Set", self.calls)

    def test_gnome_query_failure_is_not_ignored(self):
        result = self.wayland("GNOME", GNOME_GET_STATUS="1")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Properties.Set", self.calls)

    def test_gnome_set_failure_is_not_ignored(self):
        result = self.wayland("GNOME", GNOME_SET_STATUS="1")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("xset|", self.calls)

    def test_notification_failure_preserves_failure(self):
        result = self.wayland(WLOPM_STATUS="1", NOTIFY_STATUS="1")
        self.assertEqual(result.returncode, 1)

    def test_custom_delay(self):
        result = self.run_app("--delay", "2.25", DISPLAY=":0")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.calls.startswith("sleep|2.25\n"))

    def test_interrupted_delay_does_not_turn_off_displays(self):
        result = self.run_app(DISPLAY=":0", SLEEP_STATUS="1")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("xset|", self.calls)

    def test_invalid_arguments_never_act(self):
        for args in (("--delay",), ("--invalid",), ("--delay", "-1"), ("--delay", "nan"),
                     ("--delay", "1.2.3"), ("--delay", ""), ("--delay", "1d")):
            with self.subTest(args=args):
                self.assertEqual(self.run_app(*args, DISPLAY=":0").returncode, 2)
                self.assertEqual(self.calls, "")

    def test_help_and_version_do_not_need_a_desktop(self):
        for option in ("--help", "--version"):
            with self.subTest(option=option):
                result = self.run_app(option)
                self.assertEqual(result.returncode, 0)
                self.assertTrue(result.stdout)
                self.assertEqual(self.calls, "")


if __name__ == "__main__":
    unittest.main()
