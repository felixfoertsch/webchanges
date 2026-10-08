import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.normalize_sdist import normalize


class NormalizeSdistTest(unittest.TestCase):
    def test_rebuild_metadata_does_not_change_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f'{index}.tar.gz' for index in range(2)]
            for index, path in enumerate(paths):
                with tarfile.open(path, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
                    member = tarfile.TarInfo('package/source.py')
                    member.size = 4
                    member.mtime = 100.5 + index
                    member.uid = index
                    member.uname = str(index)
                    archive.addfile(member, io.BytesIO(b'code'))
                normalize(path, 100)
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            with tarfile.open(paths[0]) as archive:
                self.assertEqual(archive.extractfile('package/source.py').read(), b'code')


if __name__ == '__main__':
    unittest.main()
