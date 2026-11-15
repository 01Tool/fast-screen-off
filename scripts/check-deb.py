"""Check the actual binary payload, metadata, permissions and desktop entry."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def check(target, package):
    assert target in ("debian13", "deepin25"), target
    appid = "net.playhi.fast-screen-off"
    fields = subprocess.check_output(
        ["dpkg-deb", "--field", package], text=True
    )
    metadata = dict(line.split(": ", 1) for line in fields.splitlines()
                    if line and not line.startswith(" ") and ": " in line)
    assert metadata["Package"] == appid
    assert metadata["Architecture"] == "all"
    version = metadata["Version"]
    for dependency in ("coreutils", "x11-xserver-utils", "libglib2.0-bin"):
        assert dependency in metadata["Depends"], dependency

    data = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", package])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        files = {item.name.removeprefix("./"): item for item in archive if item.isfile()}
        assert all(item.uid == item.gid == 0 for item in archive.getmembers())
        assert not any(item.issym() or item.islnk() for item in archive.getmembers())
        if target == "deepin25":
            prefix = f"opt/apps/{appid}/"
            assert all(name.startswith(prefix) for name in files), sorted(files)
            binary = prefix + f"files/bin/{appid}.sh"
            desktop = prefix + f"entries/applications/{appid}.desktop"
            icon = prefix + f"entries/icons/hicolor/scalable/apps/{appid}.svg"
            info = json.load(archive.extractfile(files[prefix + "info"]))
            assert info["appid"] == appid
            assert info["version"] == version
            assert info["permissions"]["notification"] is True
            assert prefix + "files/copyright" in files
            assert prefix + "files/changelog" in files
            expected_exec = f'Exec="/{binary}"'
        else:
            assert all(name.startswith("usr/") for name in files), sorted(files)
            binary = "usr/bin/fast-screen-off"
            desktop = f"usr/share/applications/{appid}.desktop"
            icon = f"usr/share/icons/hicolor/scalable/apps/{appid}.svg"
            assert f"usr/share/doc/{appid}/copyright" in files
            assert f"usr/share/doc/{appid}/changelog.gz" in files
            expected_exec = "Exec=fast-screen-off"
        assert icon in files
        assert files[binary].mode == 0o755
        assert files[desktop].mode == 0o644
        script = archive.extractfile(files[binary]).read()
        assert b"\r" not in script
        assert f"fast-screen-off {version}".encode() in script
        entry = archive.extractfile(files[desktop]).read().decode()
        assert expected_exec in entry.splitlines()
        assert "Name[zh_CN]=快速熄屏" in entry.splitlines()
        assert len([name for name in files if name.endswith(".desktop")]) == 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"{appid}.desktop"
            path.write_text(entry, encoding="utf-8")
            subprocess.run(["desktop-file-validate", str(path)], check=True)

    # Deepin's store layout must not introduce maintainer hooks or system triggers.
    if target == "deepin25":
        control = subprocess.check_output(["dpkg-deb", "--ctrl-tarfile", package])
        with tarfile.open(fileobj=io.BytesIO(control)) as archive:
            names = {Path(item.name).name for item in archive if item.isfile()}
            assert not names.intersection({"preinst", "postinst", "prerm", "postrm", "triggers"}), names
    print(f"Validated {target}: {package}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: check-deb.py {debian13|deepin25} PACKAGE.deb")
    check(*sys.argv[1:])
