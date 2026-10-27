"""Hard-fork release identity and build trust boundary regression checks."""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'publish_release', Path(__file__).parents[1] / 'scripts/publish_release.py'
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTest(unittest.TestCase):
    def test_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'webchanges').mkdir()
            (root / 'webchanges/__init__.py').write_text("__version__ = '3.39.0'\n")
            self.assertEqual(release.identity(root, 'refs/tags/v3.39.0', '4'), ('v3.39.0', '3.39.0', False))
            with self.assertRaises(ValueError):
                release.identity(root, 'refs/tags/v3.38.0', '4')
            with patch.dict(os.environ, {'GITHUB_SHA': 'a' * 40}):
                self.assertEqual(
                    release.identity(root, 'refs/heads/main', '4'),
                    ('nightly-' + 'a' * 40, '3.39.0+nightly.' + 'a' * 40, True),
                )
            with self.assertRaises(ValueError):
                release.identity(root, 'refs/heads/patch-queue', '4')

    def test_build_and_publisher_separation(self):
        workflow = (Path(__file__).parents[1] / '.github/workflows/downstream.yml').read_text()
        build, publish = workflow.split('  publish:', 1)
        self.assertIn('branches: [main]', build)
        self.assertIn("tags: ['v*']", build)
        self.assertNotIn('schedule:', workflow)
        self.assertNotIn('contents: write', build)
        self.assertNotIn('GH_TOKEN', build)
        self.assertNotIn('pip install', publish)
        self.assertNotIn('python -m build', publish)
        self.assertEqual(workflow.count('persist-credentials: false'), 2)


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.files = {}
        for name in ('one.whl', 'two.tar.gz'):
            path = Path(self.directory.name) / name
            path.write_bytes(name.encode())
            self.files[name] = path
        self.sha = 'a' * 40
        self.tag = 'nightly-' + self.sha
        self.refs = []
        self.releases = []
        self.release = {'id': 123, 'tag_name': self.tag, 'prerelease': True, 'draft': True, 'assets': []}
        self.calls = []
        self.head = self.sha
        self.tag_sha = self.sha
        self.download_bytes = {}

    def gh(self, *args):
        self.calls.append(args)
        if args[:2] == ('api', '--paginate'):
            return json.dumps([self.refs] if args[-1].endswith('/git/refs/tags') else [self.releases])
        if args[:1] == ('api',):
            endpoint = args[-1]
            if endpoint.endswith('/git/ref/heads/main'):
                return json.dumps({'object': {'type': 'commit', 'sha': self.head}})
            if endpoint.endswith('/git/ref/tags/' + self.tag):
                return json.dumps({'object': {'type': 'commit', 'sha': self.tag_sha}})
            if endpoint.endswith('/releases/123'):
                return json.dumps(self.release)
        if args[:2] == ('release', 'upload'):
            for path in args[5:]:
                name = Path(path).name
                self.release['assets'].append({'name': name, 'id': name})
                self.download_bytes[name] = Path(path).read_bytes()
            return ''
        if args[:2] == ('release', 'create'):
            self.releases = [self.release]
            return ''
        if args[:2] == ('release', 'edit'):
            return ''
        raise AssertionError(args)

    def publish(self):
        with (
            patch.object(release, 'gh', side_effect=self.gh),
            patch.object(release, 'download', side_effect=lambda repo, asset: self.download_bytes[asset['id']]),
        ):
            release.publish('owner/repo', self.tag, self.sha, True, self.files)

    def asset(self, name, data=None):
        self.release['assets'].append({'name': name, 'id': name})
        self.download_bytes[name] = self.files[name].read_bytes() if data is None else data

    def test_resolve_lightweight_and_nested_annotated(self):
        responses = [
            {'object': {'type': 'tag', 'sha': 'tag1'}},
            {'object': {'type': 'tag', 'sha': 'tag2'}},
            {'object': {'type': 'commit', 'sha': self.sha}},
        ]
        with patch.object(release, 'gh', side_effect=[json.dumps(r) for r in responses]) as gh:
            self.assertEqual(release.resolve('owner/repo', 'tags/v1'), self.sha)
            self.assertEqual(gh.call_args_list[1].args, ('api', 'repos/owner/repo/git/tags/tag1'))
        with patch.object(release, 'gh', return_value=json.dumps(responses[-1])):
            self.assertEqual(release.resolve('owner/repo', 'heads/main'), self.sha)
        with patch.object(release, 'gh', return_value=json.dumps(responses[0])) as gh:
            with self.assertRaises(ValueError):
                release.resolve('owner/repo', 'tags/v1')
            self.assertLessEqual(gh.call_count, 12)

    def test_stale_ref_and_wrong_existing_tag(self):
        self.head = 'b' * 40
        with self.assertRaises(ValueError):
            self.publish()
        self.head = self.sha
        self.refs = [{'ref': 'refs/tags/' + self.tag}]
        self.tag_sha = 'b' * 40
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(any(c[:2] == ('release', 'create') for c in self.calls))

    def test_duplicate_and_classification_rejected(self):
        self.releases = [self.release]
        self.release['prerelease'] = False
        with self.assertRaises(ValueError):
            self.publish()
        self.release['prerelease'] = True
        self.asset('one.whl')
        self.asset('one.whl')
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(any(c[:2] == ('release', 'upload') for c in self.calls))

    def test_create_draft_and_retry_upload_missing(self):
        self.publish()
        self.assertTrue(any(c[:2] == ('release', 'create') and '--draft' in c for c in self.calls))
        self.assertTrue(any(c[:2] == ('release', 'edit') for c in self.calls))
        self.calls.clear()
        self.releases = [self.release]
        self.release['assets'].pop()
        self.publish()
        upload = next(c for c in self.calls if c[:2] == ('release', 'upload'))
        self.assertIn(str(self.files['two.tar.gz']), upload)
        self.assertNotIn(str(self.files['one.whl']), upload)
        self.assertFalse(any(c[:2] == ('release', 'create') for c in self.calls))

    def test_mismatch_and_published_incomplete_or_matching(self):
        self.releases = [self.release]
        self.asset('one.whl', b'wrong')
        with self.assertRaises(ValueError):
            self.publish()
        self.download_bytes['one.whl'] = self.files['one.whl'].read_bytes()
        self.release['draft'] = False
        with self.assertRaises(ValueError):
            self.publish()
        self.asset('two.tar.gz')
        self.calls.clear()
        self.publish()
        self.assertFalse(any(c[:2] in (('release', 'edit'), ('release', 'upload')) for c in self.calls))

    def test_uploaded_bytes_mismatch_blocks_visibility(self):
        with (
            patch.object(release, 'gh', side_effect=self.gh),
            patch.object(release, 'download', return_value=b'corrupt'),
        ):
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                release.publish('owner/repo', self.tag, self.sha, True, self.files)
        self.assertFalse(any(c[:2] == ('release', 'edit') for c in self.calls))

    def test_api_failure_propagates_without_create(self):
        with patch.object(release, 'gh', side_effect=subprocess.CalledProcessError(1, 'gh')) as gh:
            with self.assertRaises(subprocess.CalledProcessError):
                release.publish('owner/repo', self.tag, self.sha, True, self.files)
            self.assertEqual(gh.call_count, 1)
