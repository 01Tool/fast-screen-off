# Portable packaging

All recipes install the same launcher from `net.playhi.fast-screen-off/deepin`.
`scripts/prepare-portable.py` checks its version against the Debian changelog
and Deepin metadata, then copies only the required inputs to a fresh temporary
directory. Build scripts write artifacts to `assets/`, or a directory supplied
as their first argument. The initial portable target is x86_64.

## AppImage

Build on Debian 12 amd64 to keep the glibc baseline at 2.36:

```sh
sudo apt install ca-certificates curl git python3 file patchelf desktop-file-utils \
  x11-xserver-utils libglib2.0-bin libnotify-bin libkf5screen-bin \
  build-essential libwayland-dev pkg-config \
  qt5-qmake qtbase5-dev qtwayland5 libqt5svg5
sh scripts/build-appimage.sh
```

The recipe builds pinned wlopm sources because Debian 12 does not package it.
It uses checksum-pinned linuxdeploy and its Qt plugin, packages the
display helpers and their shared libraries, and includes the Qt Wayland and
offscreen plugins. It keeps Debian dependency copyright files and a package
version inventory under `usr/share/doc` inside the AppImage. Host graphics
drivers and standard system facilities still come from the desktop system.

## Flatpak

```sh
sudo apt install flatpak flatpak-builder python3 dbus-x11
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.kde.Sdk//6.10 org.kde.Platform//6.10
dbus-run-session -- sh scripts/build-flatpak.sh
```

The source manifest is `flatpak/net.playhi.fast-screen-off.json`. The script
stages it alongside the application source, builds pinned libXt/libXmu, xset, wlopm and
KScreen sources, and copies the SDK's gdbus tool for use with its matching
runtime libraries. KDE supplies Qt and its platform plugins, avoiding host Qt
dependencies. The generated bundle records Flathub as the runtime repository.
The wlopm module uses C17 because its pinned release predates the C23 change
to empty function parameter lists in newer SDK compilers.

CI uses Flathub's official KDE 6.10 container, pinned by digest, with both the
SDK and runtime preinstalled. Its documented privileged container setting
allows Flatpak's nested namespaces on the disposable GitHub runner; the
application's own sandbox permissions remain those in the manifest.
The optional rofiles-fuse build-cache optimization is disabled so builds also
work in containers without its host-spawn integration.

The build script installs the app into the invoking user's Flatpak installation
to test its helpers in the actual sandbox. Use a disposable build user if you
already have the same app installed. Remove the test installation with
`flatpak uninstall --user net.playhi.fast-screen-off`.

The manifest explicitly grants Mutter D-Bus access for GNOME. Wayland socket
access does not guarantee that a compositor exposes power-management protocols.
No host-spawn permission or broad session-bus permission is requested.

## Linglong / Linyaps

Install `linglong-builder`, `linglong-bin` and `linglong-box` following the official Linyaps
instructions, then run:

```sh
dbus-run-session -- sh scripts/build-linglong.sh
```

The recipe targets the 1.14 builder and `org.deepin.base/25.2.2`. It uses the
builder's APT extension to include the display helpers and Qt 6 platform plugins,
with `qt.conf` pointing at their relocated directory. It includes Wayland support
and builds wlopm from a pinned source archive because it is not available in
every Deepin APT repository. The build runs headless helper checks in the
generated runtime before exporting a distribution `.uab`.

Install distribution UABs using `ll-cli install`. They resolve their declared
base through Linyaps; they are not standalone executables. This workflow does
not export the deprecated `.layer` format or the distinct `.uabx` format.

CI installs the builder from the official HTTPS release APT repository. As
documented by upstream, that repository currently has no APT signing metadata
and uses `trusted=yes`; it is used only on the disposable GitHub runner.

## Validation and releases

The shared `common/check-runtime.sh` checks command availability and starts the
helpers with help/version flags. KDE runs with the offscreen Qt plugin, without
changing screen power. Backend behavior remains covered by the mock tests.
These checks do not replace testing on real desktop sessions and hardware.

All five package builds must pass before a tag release publishes. One release
job downloads the five artifacts, checks their expected names, and generates
one `SHA256SUMS` covering `.deb`, `.AppImage`, `.flatpak` and `.uab` files.
Build failures cannot silently produce a partial release.

## Sources and maintenance

- [linuxdeploy](https://github.com/linuxdeploy/linuxdeploy/releases/tag/1-alpha-20251107-1)
- [linuxdeploy Qt plugin](https://github.com/linuxdeploy/linuxdeploy-plugin-qt/releases/tag/1-alpha-20250213-1)
- [xset 1.2.5](https://xorg.freedesktop.org/archive/individual/app/xset-1.2.5.tar.xz)
- [libXt 1.3.1](https://xorg.freedesktop.org/archive/individual/lib/libXt-1.3.1.tar.xz)
- [libXmu 1.2.1](https://xorg.freedesktop.org/archive/individual/lib/libXmu-1.2.1.tar.xz)
- [wlopm 0.1.0 source](https://deb.debian.org/debian/pool/main/w/wlopm/wlopm_0.1.0.orig.tar.gz)
- [Plasma Wayland protocols 1.16.0](https://download.kde.org/stable/plasma-wayland-protocols/plasma-wayland-protocols-1.16.0.tar.xz)
- [KScreen 6.3.6 source](https://download.kde.org/stable/plasma/6.3.6/libkscreen-6.3.6.tar.xz)
- [KDE runtime sources, including GLib/gdbus](https://invent.kde.org/packaging/flatpak-kde-runtime/-/tree/qt6.10)
- [Flatpak permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html)
- [Official Flatpak CI images](https://github.com/flathub-infra/actions-images)
- [Linyaps manifest and APT extension](https://linglong.dev/en/guide/building/manifests.html)
- [Linyaps installation repositories](https://linglong.dev/en/guide/start/install.html)

Archive checksums live in the manifests and AppImage script. Runtime/base and
CI image updates, and new architectures, require rebuilding and repeating the checks.
Publishing to Flathub or the Linyaps store needs its own metadata/review process;
these recipes produce downloadable GitHub assets.
