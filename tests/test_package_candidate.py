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

    @unittest.skipUnless(importlib.util.find_spec('build'), 'requires scripts/build-requirements.txt')
    def test_pinned_backend_rebuild_is_byte_identical(self):
        import os
        import subprocess
        import sys
        from scripts.normalize_sdist import normalize
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'webchanges.py').write_text('__version__ = "1.0"\n')
            (root / 'pyproject.toml').write_text(
                '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n'
                '[project]\nname = "webchanges"\nversion = "1.0"\n')
            results = []
            for mtime in (1700000000, 1800000000):
                os.utime(root / 'webchanges.py', (mtime, mtime))
                subprocess.run([sys.executable, '-m', 'build', '--no-isolation', str(root)],
                               env={**os.environ, 'SOURCE_DATE_EPOCH': '1600000000'},
                               capture_output=True, check=True)
                normalize(root / 'dist/webchanges-1.0.tar.gz', 1600000000)
                results.append(candidate.describe(root / 'dist', '1.0'))
            self.assertEqual(results[0], results[1])

    def test_version_is_channel_specific(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'webchanges').mkdir()
            (root / 'webchanges/__init__.py').write_text('__version__ = "3.37.0"\n')
            self.assertEqual(candidate.version(root, 'v3.37.0-2026.10.08.1'), '3.37.0+stable.2026.10.8.1')
            self.assertEqual(candidate.version(root, 'nightly-v3.37.0-2026.10.08.1'), '3.37.0+nightly.2026.10.8.1')


if __name__ == '__main__':
    unittest.main()
