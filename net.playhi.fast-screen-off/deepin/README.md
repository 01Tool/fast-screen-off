# net.playhi.fast-screen-off

Turn off the displays with one click. Run as your normal desktop user.
The default delay is 0.5 seconds; mouse or keyboard input wakes the displays.
Desktop lock policies still apply. This app does not suspend the computer.

Supports X11 DPMS, GNOME Wayland, KDE Plasma Wayland, and compositors with the
Wayland output-power-management protocol. KDE needs libkscreen-bin; Treeland
and other compatible compositors need wlopm. Helper availability and compositor
support vary; use X11 if a required Wayland backend is unavailable.

Command options: --help, --version, --delay SECONDS.

Source and full instructions: https://github.com/01Tool/fast-screen-off

