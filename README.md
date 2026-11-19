# Fast Screen Off / 快速熄屏

Turn off the displays with one click. The launcher waits 0.5 seconds for the
launching input to finish, then requests display power-off. Run it as your normal
desktop user. Mouse or keyboard input wakes the displays; desktop lock policies
still apply. This application does not suspend the computer or change idle timers.

## Desktop compatibility

| System/session | Backend | Requirements |
| --- | --- | --- |
| Deepin 25 or Debian 13, X11 | `xset dpms force off` | `x11-xserver-utils` (installed as a dependency), X server/driver DPMS support |
| Debian 13, GNOME Wayland | Mutter `PowerSaveMode` | `libglib2.0-bin` (installed as a dependency), an active GNOME session bus |
| Debian 13, KDE Plasma Wayland | `kscreen-doctor --dpms off` | `libkscreen-bin`, normally supplied with Plasma |
| Deepin 25, Treeland Wayland; other compatible Wayland compositors | `wlopm --off '*'` | `wlopm` and compositor support for `zwlr_output_power_manager_v1` |

Wayland support depends on the running compositor and its version. For Treeland,
`wlopm` is a recommended dependency, installed by APT when available from your
distribution's repositories. It is not mandatory because availability differs
across Deepin builds; install it explicitly if recommendations were disabled.
If it is unavailable or the compositor does not expose output-power management,
use an X11 session. No XWayland fallback is attempted. Unknown sessions, missing
helpers and backend failures return a nonzero exit status, print an explanation,
and show a notification when `notify-send` is installed.

These backends follow the upstream interfaces linked below. Automated tests check
dispatch and failure behavior with mock commands. Container CI checks packaging,
installation and removal; actual screen power-off and input wake-up still need
testing on each target desktop and GPU.

## Install

Download the matching `.deb` from [Releases](https://github.com/01Tool/fast-screen-off/releases).
Both variants use the existing package ID `net.playhi.fast-screen-off`, so they
upgrade earlier releases. Install **one** variant matching your system:

```sh
# Debian 13
sudo apt install ./net.playhi.fast-screen-off_2.0.0.0_debian13_all.deb

# Deepin 25
sudo apt install ./net.playhi.fast-screen-off_2.0.0.0_deepin25_all.deb
```

The Debian package installs `/usr/bin/fast-screen-off` and the standard desktop
entry/icon in `/usr/share`. The Deepin package keeps its payload under
`/opt/apps/net.playhi.fast-screen-off`, including `info`, `entries` and `files`.
Deepin's application integration discovers the entries. It contains no maintainer
scripts or system-directory copies. On immutable Deepin installations, use the
system's supported package installer/update mechanism; do not disable protection
for this app. Store submission and approval are separate from building a package.

Open **Fast Screen Off / 快速熄屏** in the application launcher, or run:

```sh
fast-screen-off --delay 1          # Debian command
/opt/apps/net.playhi.fast-screen-off/files/bin/net.playhi.fast-screen-off.sh --delay 1
```

Both commands accept `--help`, `--version` and `--delay SECONDS`. Remove with
`sudo apt remove net.playhi.fast-screen-off` or your system's software manager.

## AppImage, Flatpak and Linglong

The latest workflow builds these additional **x86_64** artifacts. They will be
included in future tagged releases; the previously published v2.0.0.0 release
contains only the two `.deb` packages. Branch builds are available under the
workflow run's **Artifacts** section.

| Format | Artifact | Requirements |
| --- | --- | --- |
| AppImage | `fast-screen-off_<version>_x86_64.AppImage` | Desktop Linux with glibc 2.36 or newer; FUSE, or extraction mode |
| Flatpak | `fast-screen-off_<version>_x86_64.flatpak` | Flatpak and the KDE 6.10 runtime from Flathub |
| Linglong / Linyaps | `fast-screen-off_<version>_x86_64.uab` | Linyaps 1.14 or newer and access to its base repository |

These packages include `xset`, `gdbus`, `wlopm` and `kscreen-doctor` through
bundled dependencies or their declared runtime. Desktop/compositor power-control
support is still required. Flatpak grants the X11/Wayland sockets, shared IPC,
and access to the Mutter display and notification D-Bus services. Linglong uses
its desktop runtime integration; custom runtime policies can restrict access to
the session bus or display sockets.

```sh
# Set VERSION to match your downloaded workflow/release artifact.
VERSION=2.0.0.0
# AppImage
chmod +x "fast-screen-off_${VERSION}_x86_64.AppImage"
./fast-screen-off_${VERSION}_x86_64.AppImage
# If FUSE is unavailable:
APPIMAGE_EXTRACT_AND_RUN=1 ./fast-screen-off_${VERSION}_x86_64.AppImage

# Flatpak
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user ./fast-screen-off_${VERSION}_x86_64.flatpak
flatpak run net.playhi.fast-screen-off

# Linglong: install distribution UABs instead of executing them directly
ll-cli install ./fast-screen-off_${VERSION}_x86_64.uab
ll-cli run net.playhi.fast-screen-off
```

CI runs headless helper checks inside Flatpak and the Linglong build runtime,
and checks the AppImage launcher and bundled helper programs. These checks do
not switch off a monitor. Real display-off/wake-up testing on GNOME, Plasma and
Deepin/Treeland is still needed before claiming verified desktop compatibility
for these formats. Store submission and Snap packaging are separate work.

See [packaging instructions and dependency sources](packaging/README.md) for
local builds, runtime choices and troubleshooting.

## Build `.deb` assets locally

On Debian 13 or Deepin 25, install the build tools and run from the repository root:

```sh
sudo apt install build-essential debhelper python3 desktop-file-utils shellcheck
python3 -m unittest discover -s tests -v
sh scripts/build-deb.sh debian13
sh scripts/build-deb.sh deepin25
python3 scripts/check-deb.py debian13 assets/*_debian13_all.deb
python3 scripts/check-deb.py deepin25 assets/*_deepin25_all.deb
```

The build uses debhelper compatibility level 13 and isolated temporary source
trees. Output goes to the ignored `assets/` directory, or an optional second
argument to `build-deb.sh`. Both packages are `Architecture: all`: their payload
is shell scripts and data, and runtime helpers come from the target distribution.
CI currently exercises amd64 containers, not every architecture listed in Deepin
metadata. Generated package staging trees must not be committed.

## GitHub Actions and releases

[The package workflow](.github/workflows/packages.yml) runs for pull requests,
pushes to `master`/`main`, version tags, and manual dispatch. It builds in
`debian:13` and `linuxdeepin/deepin:25` containers, runs ShellCheck and backend
tests, validates the actual package contents and desktop entry, and installs and
purges each package in its target container. Each job uploads a downloadable
workflow artifact. Separate jobs build AppImage, Flatpak and Linglong packages
and check their helper commands.

To release:

1. Update the version together in `debian/changelog`, `deepin/info`, and the
   launcher's `--version` string, all under `net.playhi.fast-screen-off/`.
2. Add release notes under `docs/releases/<tag>.md`, then commit and push the
   changes. Wait for all package jobs to pass before pushing a new matching tag.
   Published tags must not be moved or reused for the added formats.
3. After all tag package jobs pass, the workflow creates a draft GitHub release
   (or uses the existing one), uploads all five package files and `SHA256SUMS`, and
   publishes the release. If no notes file exists, GitHub generates the notes.

Tags must exactly match the package version: use `v2.0.0.0` for package version
`2.0.0.0`. Adding a suffix such as `-nightly-1` without changing the package
version will fail the version check; this workflow publishes stable releases.
Only the tag release job receives
`contents: write`; pull requests never publish releases. Rerunning a tag workflow
replaces assets with the same filenames. The `.deb` filenames include the target;
the internal package name and version are the same for both variants.

## Interface and packaging references

- [Deepin application store packaging specification](https://docs.deepin.org/info/开发进阶/应用商店/应用打包规范/相关规范/商店打包规范)
- [Deepin 25 release notes](https://www.deepin.org/en/deepin-25-release/)
- [Debian 13 release notes](https://www.debian.org/releases/trixie/release-notes/)
- [GNOME 48 display-power interface](https://github.com/GNOME/mutter/blob/gnome-48/data/dbus-interfaces/org.gnome.Mutter.DisplayConfig.xml)
- [KDE Plasma 6.3 KScreen doctor](https://github.com/KDE/libkscreen/blob/Plasma/6.3/src/doctor/doctor.cpp)
- [Treeland output power handling](https://github.com/linuxdeepin/treeland/blob/master/src/output/outputmanager.cpp)
- [wlopm manual](https://manpages.debian.org/trixie/wlopm/wlopm.1.en.html)

![Cover](Cover/net.playhi.fast-screen-off_cover.png)

