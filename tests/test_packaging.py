"""Guard staging boundaries, metadata and Flatpak's explicit permission scope."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_portable', ROOT / 'scripts/prepare-portable.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class PackagingTests(unittest.TestCase):
    def test_staging_contains_current_launcher_without_checkout_or_caches(self):
        for package_format in ('appimage', 'flatpak', 'linglong'):
            with self.subTest(format=package_format), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                prepare.prepare(output, package_format)
                app = output / 'source/deepin/files/bin/net.playhi.fast-screen-off.sh'
                self.assertIn(f'fast-screen-off {prepare.version()}', app.read_text())
                self.assertEqual({p.name for p in (output / 'source').iterdir()},
                                 {'deepin', 'install.sh', 'check-runtime.sh',
                                  'net.playhi.fast-screen-off.metainfo.xml'})
                if package_format == 'linglong':
                    self.assertIn(f'version: {prepare.version()}', (output / 'linglong.yaml').read_text())
                    self.assertNotIn('@VERSION@', (output / 'linglong.yaml').read_text())

    def test_staging_refuses_to_mix_with_an_existing_build(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'source').mkdir()
            marker = output / 'source/keep'
            marker.write_text('existing input')
            with self.assertRaises(ValueError):
                prepare.prepare(output, 'flatpak')
            self.assertEqual(marker.read_text(), 'existing input')

    def test_flatpak_permissions_target_display_services(self):
        manifest = json.loads((ROOT / 'packaging/flatpak/net.playhi.fast-screen-off.json').read_text())
        self.assertEqual(set(manifest['finish-args']), {
            '--socket=wayland', '--socket=fallback-x11', '--share=ipc',
            '--talk-name=org.gnome.Mutter.DisplayConfig', '--talk-name=org.freedesktop.Notifications'
        })
        for module in manifest['modules']:
            for source in module['sources']:
                if source['type'] == 'archive':
                    self.assertRegex(source['sha256'], r'^[a-f0-9]{64}$')
                    self.assertTrue(source['url'].startswith('https://'))

    def test_desktop_and_appstream_identity_agree(self):
        appstream = ET.parse(ROOT / 'packaging/common/net.playhi.fast-screen-off.metainfo.xml').getroot()
        self.assertEqual(appstream.findtext('id'), 'net.playhi.fast-screen-off')
        self.assertEqual(appstream.findtext('launchable'), 'net.playhi.fast-screen-off.desktop')


if __name__ == '__main__':
    unittest.main()
