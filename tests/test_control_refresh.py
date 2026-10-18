"""Control refresh uses real Git; only external API boundaries are doubled."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path('scripts').resolve()))
import replay_patches as replay
import refresh_control as refresh

SOURCE = Path.cwd()
ENV = {**os.environ, **replay.IDENTITY, 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1'}


class ControlRefreshTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.previous = replay.ROOT
        replay.ROOT = self.root
        self.addCleanup(setattr, replay, 'ROOT', self.previous)
        self.git('init', '-q')
        (self.root / 'README.rst').write_text('Upstream README\n===============\n\nComplete upstream text.\n')
        (self.root / 'pyproject.toml').write_text("readme = { file = 'README.rst', content-type = 'text/x-rst' }\n")
        (self.root / 'docs').mkdir()
        (self.root / 'docs/index.rst').write_text('.. include:: ../README.rst\n')
        (self.root / '.github/workflows').mkdir(parents=True)
        (self.root / '.github/workflows/upstream.yml').write_text('untrusted publisher\n')
        (self.root / 'value').write_text('before\n')
        self.commit('base')
        self.base = self.git('rev-parse', 'HEAD')
        self.upstream_remote = Path(self.temp.name) / 'upstream.git'
        self.git('init', '--bare', '-q', str(self.upstream_remote))
        self.git('push', '-q', str(self.upstream_remote), 'HEAD:refs/heads/main')
        self.git('--git-dir=' + str(self.upstream_remote), 'symbolic-ref', 'HEAD', 'refs/heads/main')
        actual_git = refresh.git
        def local_upstream(*args, **kwargs):
            if args[:3] == ('ls-remote', '--symref', refresh.UPSTREAM):
                return actual_git('ls-remote', '--symref', str(self.upstream_remote), 'HEAD', **kwargs)
            return actual_git(*args, **kwargs)
        self.git_patch = patch.object(refresh, 'git', side_effect=local_upstream)
        self.git_patch.start()
        self.addCleanup(self.git_patch.stop)
        (self.root / 'value').write_text('after\n')
        self.commit('feature')
        queue = self.git('format-patch', '-1', '--stdout') + '\n'
        self.git('checkout', '-q', self.base)
        (self.root / 'patches').mkdir()
        (self.root / 'patches/0001.patch').write_text(queue)
        (self.root / 'patches/series').write_text('0001.patch\n')
        for name in replay.CONTROL_PATHS:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / name, target)
        self.commit('seed overlay')
        self.old = replay.replay(self.base, None, True)
        self.git('checkout', '-q', '-B', 'patch-queue', self.old)

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'commit.gpgSign=false', '-c', 'core.hooksPath=/dev/null', *args], cwd=self.root, env=ENV, text=True, stderr=subprocess.PIPE).strip()

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-qm', message)

    def upstream(self, path='new', content='upstream\n'):
        self.git('checkout', '-q', self.base)
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        self.commit('upstream advancement')
        result = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-q', 'patch-queue')
        return result

    def test_noop_then_new_upstream_and_workflow_identity(self):
        self.assertEqual(refresh.candidate(self.base), self.old)
        new = self.upstream()
        result = refresh.candidate(new)
        self.assertEqual(result, refresh.candidate(new))
        self.git('merge-base', '--is-ancestor', new, result)
        self.assertEqual(self.git('show', f'{result}:value'), 'after')
        self.assertEqual(self.git('show', f'{result}:new'), 'upstream')
        self.assertEqual(self.git('rev-parse', f'{result}:.github/workflows'), self.git('rev-parse', f'{self.old}:.github/workflows'))
        self.assertEqual(self.git('show', f'{result}:patches/series'), '0001.patch')
        self.assertEqual(self.git('show', f'{result}:docs/upstream-readme.rst'), self.git('show', f'{new}:README.rst'))
        self.assertNotIn('downstream-source.json', self.git('ls-tree', '-r', '--name-only', result))
        self.git('checkout', '-q', '-B', 'patch-queue', result)
        self.assertEqual(refresh.candidate(new), result)

    def test_absorption_conflict_unknown_customization_collision(self):
        adopted = self.upstream('value', 'after\n')
        result = refresh.candidate(adopted)
        self.assertEqual(self.git('show', f'{result}:value'), 'after')
        conflict = self.upstream('value', 'conflict\n')
        with self.assertRaises(RuntimeError):
            refresh.candidate(conflict)
        collision = self.upstream('scripts/refresh_control.py', 'upstream owns this\n')
        with self.assertRaisesRegex(RuntimeError, 'ownership collision'):
            refresh.candidate(collision)
        (self.root / 'unknown').write_text('unrecorded customization\n')
        self.commit('unknown')
        with self.assertRaisesRegex(RuntimeError, 'unknown control/source'):
            refresh.candidate(self.base)

    def test_backup_restore_hash_and_archive_atomic_dispatch(self):
        directory = Path(self.temp.name) / 'backup'
        refresh.backup(directory, self.old)
        refresh.verify_bundle(directory, self.old)
        result = refresh.candidate(self.upstream())
        calls = []
        original = refresh.git
        def actuator(*args, **kwargs):
            if args[:2] == ('ls-remote', '--symref'):
                return original(*args, **kwargs)
            if args[0] == 'ls-remote':
                if len(args) == 5:
                    return result + '\trefs/heads/patch-queue\n' + self.old + '\trefs/tags/archive/patch-queue/' + self.old
                return ''
            if 'push' in args:
                calls.append(args)
                return ''
            return original(*args, **kwargs)
        with patch.object(refresh, 'git', side_effect=actuator), patch.object(refresh, 'freshness') as fresh, patch.object(refresh, 'api') as api:
            refresh.promote(self.old, self.git('rev-parse', f'{result}~2'), result, directory, True)
            fresh.assert_called_once()
            self.assertIn('--atomic', calls[0])
            self.assertIn(f'--force-with-lease=refs/heads/patch-queue:{self.old}', calls[0])
            self.assertIn(f'--force-with-lease=refs/tags/archive/patch-queue/{self.old}:', calls[0])
            self.assertIn(f'inputs[expected_control]={result}', api.call_args.args)
            self.assertIn('inputs[rebuild]=true', api.call_args.args)
        (directory / 'control.bundle').write_bytes(b'corrupt')
        with self.assertRaisesRegex(RuntimeError, 'backup hash/head'):
            refresh.verify_bundle(directory, self.old)

    def test_archive_wrong_target_and_race_stop_before_push(self):
        directory = Path(self.temp.name) / 'backup'
        refresh.backup(directory, self.old)
        upstream = self.upstream()
        result = refresh.candidate(upstream)
        original = refresh.git
        def wrong_archive(*args, **kwargs):
            if args[:2] == ('ls-remote', '--symref'):
                return original(*args, **kwargs)
            if args[0] == 'ls-remote':
                return 'f' * 40 + '\trefs/tags/archive/patch-queue/' + self.old
            if 'push' in args:
                self.fail('must not push')
            return original(*args, **kwargs)
        with patch.object(refresh, 'git', side_effect=wrong_archive):
            with self.assertRaisesRegex(RuntimeError, 'directly'):
                refresh.promote(self.old, upstream, result, directory, False)

    def test_real_atomic_push_lease_race_and_dispatch_recovery(self):
        remote = Path(self.temp.name) / 'remote.git'
        self.git('init', '--bare', '-q', str(remote))
        self.git('remote', 'add', 'origin', str(remote))
        self.git('push', '-q', 'origin', 'patch-queue')
        directory = Path(self.temp.name) / 'backup'
        refresh.backup(directory, self.old)
        upstream = self.upstream()
        result = refresh.candidate(upstream)
        with patch.object(refresh, 'freshness'), patch.object(refresh, 'api', side_effect=RuntimeError('dispatch failed')):
            with self.assertRaisesRegex(RuntimeError, 'dispatch failed'):
                refresh.promote(self.old, upstream, result, directory, False)
        self.assertEqual(self.git('ls-remote', 'origin', 'refs/heads/patch-queue').split()[0], result)
        archive = 'refs/tags/archive/patch-queue/' + self.old
        self.assertEqual(self.git('ls-remote', '--refs', 'origin', archive).split()[0], self.old)
        # Concurrent different head loses exact branch lease; archive remains unchanged.
        self.git('push', '-q', 'origin', f'{upstream}:refs/heads/patch-queue', '--force')
        with patch.object(refresh, 'freshness'), patch.object(refresh, 'api') as api:
            with self.assertRaises(RuntimeError):
                refresh.promote(self.old, upstream, result, directory, False)
            api.assert_not_called()
        self.git('checkout', '-q', '-B', 'patch-queue', result)
        self.assertEqual(refresh.candidate(upstream), result)
        # Missing archive plus stale branch must fail atomically, without ghost archive.
        self.base = upstream
        next_upstream = self.upstream('second', 'advance again\n')
        next_result = refresh.candidate(next_upstream)
        next_backup = Path(self.temp.name) / 'next-backup'
        refresh.backup(next_backup, result)
        self.git('push', '-q', 'origin', f'{self.old}:refs/heads/patch-queue', '--force')
        with patch.object(refresh, 'freshness'), patch.object(refresh, 'api') as api:
            with self.assertRaises(RuntimeError):
                refresh.promote(result, next_upstream, next_result, next_backup, False)
            api.assert_not_called()
        self.assertEqual(self.git('ls-remote', '--refs', 'origin', 'refs/tags/archive/patch-queue/' + result), '')

    def test_candidate_has_no_write_credentials_and_freshness_stops(self):
        upstream = self.upstream()
        result = refresh.candidate(upstream)
        directory = Path(self.temp.name) / 'backup'
        refresh.backup(directory, self.old)
        def reconstruct(base):
            self.assertNotIn('GH_TOKEN', os.environ)
            self.assertNotIn('GITHUB_TOKEN', os.environ)
            return result
        original = refresh.git
        def no_network(*args, **kwargs):
            if args[0] == 'ls-remote':
                return ''
            if 'push' in args:
                self.fail('freshness failure must prevent push')
            return original(*args, **kwargs)
        with patch.dict(os.environ, {'GH_TOKEN': 'test-only-sentinel', 'GITHUB_TOKEN': 'test-only-sentinel'}), patch.object(refresh, 'candidate', side_effect=reconstruct), patch.object(refresh, 'git', side_effect=no_network), patch.object(refresh, 'freshness', side_effect=RuntimeError('control advanced')):
            with self.assertRaisesRegex(RuntimeError, 'control advanced'):
                refresh.promote(self.old, upstream, result, directory, False)
            self.assertEqual(os.environ['GH_TOKEN'], 'test-only-sentinel')

    def test_detached_snapshot_backup_without_local_branches(self):
        self.git('checkout', '--detach', '-q', self.old)
        self.git('branch', '-D', 'patch-queue')
        self.git('branch', '-D', 'master')
        self.assertEqual(self.git('for-each-ref', 'refs/heads'), '')
        directory = Path(self.temp.name) / 'detached-backup'
        refresh.backup(directory, self.old)
        refresh.verify_bundle(directory, self.old)
        self.assertEqual(self.git('for-each-ref', 'refs/backup'), '')

    def test_changed_default_stops_noop(self):
        self.git('push', '-q', str(self.upstream_remote), self.base + ':refs/heads/develop')
        self.git('--git-dir=' + str(self.upstream_remote), 'symbolic-ref', 'HEAD', 'refs/heads/develop')
        with self.assertRaisesRegex(RuntimeError, 'default branch changed'):
            refresh.candidate(self.base)

    def test_bad_readback_never_dispatches(self):
        upstream = self.upstream()
        result = refresh.candidate(upstream)
        directory = Path(self.temp.name) / 'backup'
        refresh.backup(directory, self.old)
        original = refresh.git
        for response in ('', 'f' * 40 + '\trefs/heads/patch-queue', RuntimeError('read failed')):
            def actuator(*args, **kwargs):
                if args[:2] == ('ls-remote', '--symref'):
                    return original(*args, **kwargs)
                if args[0] == 'ls-remote':
                    if len(args) == 5:
                        if isinstance(response, Exception):
                            raise response
                        return response
                    return ''
                if 'push' in args:
                    return ''
                return original(*args, **kwargs)
            with patch.object(refresh, 'git', side_effect=actuator), patch.object(refresh, 'freshness'), patch.object(refresh, 'api') as api:
                with self.assertRaises(RuntimeError):
                    refresh.promote(self.old, upstream, result, directory, False)
                api.assert_not_called()

    def test_empty_upstream_commit_refreshes_once(self):
        self.git('checkout', '-q', self.base)
        self.git('commit', '--allow-empty', '-qm', 'empty upstream advance')
        upstream = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-q', 'patch-queue')
        result = refresh.candidate(upstream)
        self.assertNotEqual(result, self.old)
        self.git('merge-base', '--is-ancestor', upstream, result)
        self.git('checkout', '-q', '-B', 'patch-queue', result)
        self.assertEqual(refresh.candidate(upstream), result)

    def test_incremental_bundle_cannot_restore(self):
        directory = Path(self.temp.name) / 'incremental'
        directory.mkdir()
        bundle = directory / 'control.bundle'
        self.git('bundle', 'create', str(bundle), 'patch-queue', '^' + self.base)
        (directory / 'manifest.json').write_text(json.dumps({'old': self.old, 'sha256': hashlib.sha256(bundle.read_bytes()).hexdigest()}))
        with self.assertRaises(RuntimeError):
            refresh.verify_bundle(directory, self.old)

    def test_archive_tags_are_not_versions(self):
        spec = importlib.util.spec_from_file_location('release_tag', SOURCE / 'scripts/release_tag.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        refs = 'abc refs/tags/archive/patch-queue/' + 'a' * 40
        self.assertEqual(module.select_tag('v3.37.0', 'stable', 'abc', refs, '2026.10.18'), 'v3.37.0-2026.10.18.1')


if __name__ == '__main__':
    unittest.main()
