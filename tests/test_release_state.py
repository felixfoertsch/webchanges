import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class ReleaseStateTest(unittest.TestCase):
    def test_complete_release_requires_expected_assets(self):
        release = {
            'target_commitish': 'abc', 'draft': False,
            'assets': [
                {'name': 'webchanges-3.tar.gz', 'digest': 'sha256:' + 'a' * 64},
                {'name': 'webchanges-3-py3-none-any.whl', 'digest': 'sha256:' + 'b' * 64},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'release.json'; path.write_text(json.dumps(release))
            result = subprocess.run(['python3', 'scripts/release_state.py', str(path), '--commit', 'abc', '--asset', 'webchanges-3.tar.gz', '--asset', 'webchanges-3-py3-none-any.whl'], text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), 'complete')

    def test_draft_is_partial(self):
        release = {'target_commitish': 'abc', 'draft': True, 'assets': []}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'release.json'; path.write_text(json.dumps(release))
            result = subprocess.run(['python3', 'scripts/release_state.py', str(path), '--commit', 'abc', '--asset', 'wheel'], text=True, capture_output=True, check=True)
            strict = subprocess.run(['python3', 'scripts/release_state.py', str(path), '--commit', 'abc', '--asset', 'wheel', '--require-complete'], text=True, capture_output=True)
        self.assertEqual(result.stdout.strip(), 'partial')
        self.assertNotEqual(strict.returncode, 0)


if __name__ == '__main__':
    unittest.main()
