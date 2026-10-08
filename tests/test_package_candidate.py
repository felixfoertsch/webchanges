"""Exercise real package metadata and reject changed provenance/bytes."""
import importlib.util
from pathlib import Path
import tempfile
import tarfile
import io
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('candidate', 'scripts/package_candidate.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CandidateTest(unittest.TestCase):
    def test_metadata_and_tampered_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected = '3.37.0+stable.2026.10.8.1'
            metadata = f'Name: webchanges\nVersion: {expected}\n'.encode()
            wheel = root / f'webchanges-{expected}-py3-none-any.whl'
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr('webchanges.dist-info/METADATA', metadata)
            sdist = root / f'webchanges-{expected}.tar.gz'
            with tarfile.open(sdist, 'w:gz') as archive:
                member = tarfile.TarInfo('webchanges/PKG-INFO'); member.size = len(metadata)
                archive.addfile(member, io.BytesIO(metadata))
            original = candidate.describe(root, expected)
            wheel.write_bytes(wheel.read_bytes() + b'tampered')
            self.assertNotEqual(candidate.describe(root, expected), original)
            with self.assertRaises(ValueError):
                candidate.describe(root, expected.replace('stable', 'nightly'))

    def test_version_is_channel_specific(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'webchanges').mkdir()
            (root / 'webchanges/__init__.py').write_text('__version__ = "3.37.0"\n')
            self.assertEqual(candidate.version(root, 'v3.37.0-2026.10.08.1'), '3.37.0+stable.2026.10.8.1')
            self.assertEqual(candidate.version(root, 'nightly-v3.37.0-2026.10.08.1'), '3.37.0+nightly.2026.10.8.1')


if __name__ == '__main__':
    unittest.main()
