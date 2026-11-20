import ast
import hashlib
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bundle_release', ROOT / 'bundle_release.py')
bundler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundler)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        source = self.root / 'ExternalFileManager'
        source.mkdir()
        for name in bundler.RUNTIME:
            shutil.copyfile(ROOT / 'ExternalFileManager' / name, source / name)
        shutil.copyfile(ROOT / 'CHANGELOG.md', self.root / 'CHANGELOG.md')
        for name in ('selftest.py', 'extended_selftest.py', 'private.log', 'live-selftest.json'):
            (source / name).write_text('DO NOT PACKAGE')

    def tearDown(self): self.tmp.cleanup()

    def test_clean_contents_and_unchanged_development_source(self):
        before = (self.root / 'ExternalFileManager' / 'plugin.py').read_bytes()
        target, digest = bundler.bundle(self.root)
        self.assertEqual(target.parent.name, '.releases')
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), digest)
        with zipfile.ZipFile(target) as archive:
            expected = {'ExternalFileManager/' + n for n in bundler.RUNTIME} | {'README.md', 'CHANGELOG.md'}
            self.assertEqual(set(archive.namelist()), expected)
            plugin = archive.read('ExternalFileManager/plugin.py').decode()
            self.assertNotIn('selftest', plugin)
            self.assertNotIn('CRISPY_EFM_SELFTEST', plugin)
            for name in bundler.RUNTIME:
                ast.parse(archive.read('ExternalFileManager/' + name).decode())
            self.assertIsNone(archive.testzip())
        self.assertEqual((self.root / 'ExternalFileManager' / 'plugin.py').read_bytes(), before)

    def test_reproducible_and_refuses_accidental_overwrite(self):
        target, first = bundler.bundle(self.root)
        with self.assertRaises(FileExistsError): bundler.bundle(self.root)
        _, second = bundler.bundle(self.root, force=True)
        self.assertEqual(first, second)

    def test_missing_runtime_dependency_rejected(self):
        path = self.root / 'ExternalFileManager' / 'controller.py'
        path.write_text(path.read_text() + '\nfrom .unpackaged import helper\n')
        with self.assertRaisesRegex(ValueError, 'Unpackaged relative dependency'):
            bundler.bundle(self.root)


if __name__ == '__main__': unittest.main()
