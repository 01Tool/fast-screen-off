"""Stage only package inputs, never the checkout, caches or prior artifacts."""
import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def version():
    text = (ROOT / 'net.playhi.fast-screen-off/debian/changelog').read_text()
    result = re.match(r'net\.playhi\.fast-screen-off \((\d+\.\d+\.\d+\.\d+)\)', text)
    if not result:
        raise ValueError('Expected a four-part numeric package version')
    value = result.group(1)
    info = json.loads((ROOT / 'net.playhi.fast-screen-off/deepin/info').read_text(encoding='utf-8'))
    script = (ROOT / 'net.playhi.fast-screen-off/deepin/files/bin/net.playhi.fast-screen-off.sh').read_text()
    if info['version'] != value or f'fast-screen-off {value}' not in script:
        raise ValueError('Changelog, Deepin metadata and launcher versions disagree')
    return value


def prepare(output, package_format):
    value = version()
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'source').exists():
        raise ValueError('Use a fresh staging directory')
    shutil.copytree(ROOT / 'net.playhi.fast-screen-off/deepin', output / 'source/deepin')
    for item in (ROOT / 'packaging/common').iterdir():
        shutil.copy2(item, output / 'source' / item.name)
    if package_format == 'flatpak':
        shutil.copy2(ROOT / 'packaging/flatpak/net.playhi.fast-screen-off.json', output)
    elif package_format == 'linglong':
        template = (ROOT / 'packaging/linglong/linglong.yaml.in').read_text()
        (output / 'linglong.yaml').write_text(template.replace('@VERSION@', value), encoding='utf-8', newline='\n')
    print(value)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('format', choices=['appimage', 'flatpak', 'linglong', 'version'])
    parser.add_argument('output', type=Path, nargs='?')
    args = parser.parse_args()
    if args.format == 'version':
        print(version())
    elif args.output is None:
        parser.error('output directory is required')
    else:
        prepare(args.output, args.format)
