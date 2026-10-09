"""Unchanged release reuse requires complete matching bytes, including provenance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
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

    def test_complete_missing_mismatch_and_draft_repair(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dist = root / 'dist'
            dist.mkdir()
            for name in ('webchanges.whl', 'webchanges.tar.gz'):
                (dist / name).write_bytes(name.encode())
            provenance = root / 'provenance.json'
            provenance.write_text('{"commit": "source"}\n')
            files = [*dist.iterdir(), provenance]
            release = {'target_commitish': 'source', 'draft': False, 'assets': [
                {'name': path.name, 'digest': 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in files
            ]}
            path = root / 'release.json'
            command = [sys.executable, 'scripts/release_state.py', str(path), '--commit', 'source',
                       '--dist', str(dist), '--provenance', str(provenance)]
            for asset in files:
                command.extend(['--asset', asset.name])

            def check():
                path.write_text(json.dumps(release))
                return subprocess.run(command, capture_output=True, text=True)

            self.assertEqual(check().stdout.strip(), 'complete')
            removed = release['assets'].pop()
            self.assertNotEqual(check().returncode, 0)
            release['draft'] = True
            self.assertEqual(check().stdout.strip(), 'partial')
            release['assets'].append(removed)
            release['assets'][0]['digest'] = 'sha256:' + '0' * 64
            self.assertNotEqual(check().returncode, 0)
            release['assets'][0]['digest'] = 'sha256:' + hashlib.sha256(files[0].read_bytes()).hexdigest()
            provenance.write_text('{"commit": "tampered"}\n')
            self.assertNotEqual(check().returncode, 0)
            provenance.write_text('{"commit": "source"}\n')
            release['assets'].append(removed)
            self.assertNotEqual(check().returncode, 0)
            release['assets'].pop()
            release['target_commitish'] = 'changed'
            self.assertNotEqual(check().returncode, 0)


if __name__ == '__main__':
    unittest.main()
