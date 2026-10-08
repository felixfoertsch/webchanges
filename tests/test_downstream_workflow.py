from pathlib import Path
import subprocess
import unittest


class DownstreamWorkflowTest(unittest.TestCase):
    def test_only_automation_and_main_branches(self):
        workflow = Path('.github/workflows/downstream.yml').read_text()
        self.assertIn('branches: [patch-queue]', workflow)
        self.assertIn('$NIGHTLY_COMMIT:refs/heads/main', workflow)
        self.assertNotIn('generated/', workflow)
        self.assertNotIn('--clobber', workflow)

    def test_trusted_publisher_boundary(self):
        workflow = Path('.github/workflows/downstream.yml').read_text()
        prepare, build, publish = workflow.split('  build:', 1)[0], *workflow.split('  build:', 1)[1].split('  publish:', 1)
        self.assertIn('contents: read', prepare)
        self.assertNotIn('contents: write', build)
        self.assertIn('needs: [prepare, build]', publish)
        self.assertIn('contents: write', publish)
        self.assertNotIn('python -m build', publish)
        self.assertNotIn('pip install', publish)
        self.assertEqual(workflow.count('persist-credentials: false'), 3)
        self.assertEqual(workflow.count("ref: '${{ github.sha }}'"), 3)
        self.assertEqual(workflow.count("github.repository == 'felixfoertsch/webchanges' && github.ref == 'refs/heads/patch-queue'"), 3)
        self.assertIn('--manifest "$candidate/provenance.json" --verify', publish)
        self.assertIn('--force-with-lease="refs/heads/main:$MAIN_LEASE"', publish)
        self.assertIn('--force-with-lease="refs/tags/$tag:"', publish)
        self.assertIn('--prerelease --latest=false', publish)
        self.assertNotIn('--clobber', workflow)
        self.assertIn('gh api --method POST "repos/$GITHUB_REPOSITORY/releases"', publish)
        self.assertIn('gh api "repos/$GITHUB_REPOSITORY/releases/$release_id"', publish)
        self.assertLess(publish.index('Reconstruct and validate both candidates'), publish.index('push origin'))

    def test_no_inherited_publication(self):
        for path in Path('.github/workflows').iterdir():
            if path.name == 'downstream.yml':
                continue
            workflow = path.read_text()
            self.assertNotIn('pypi-publish', workflow)
            self.assertNotIn('coveralls', workflow.lower())
            self.assertNotIn('action-gh-release', workflow)
        self.assertFalse(Path('.github/workflows/ci-cd.yaml').exists())

    def test_exact_absorption_and_conflict(self):
        import importlib.util
        import os
        import tempfile
        spec = importlib.util.spec_from_file_location('replay', 'scripts/replay_patches.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env = {**os.environ, **module.IDENTITY}
            def git(*args):
                return subprocess.check_output(['git', '-c', 'commit.gpgSign=false', *args], cwd=root, env=env, text=True).strip()
            git('init', '-q')
            (root / 'README.rst').write_text('Upstream README\n')
            (root / 'pyproject.toml').write_text("readme = { file = 'README.rst', content-type = 'text/x-rst' }\n")
            (root / 'docs').mkdir()
            (root / 'docs/index.rst').write_text('.. include:: ../README.rst\n')
            (root / 'value').write_text('before\n')
            git('add', '.')
            git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            (root / 'value').write_text('after\n')
            git('commit', '-qam', 'patch')
            patch = git('format-patch', '-1', '--stdout') + '\n'
            (root / 'patches').mkdir()
            (root / 'patches/0001.patch').write_text(patch)
            (root / 'patches/series').write_text('0001.patch\n')
            git('add', '.')
            git('commit', '-qm', 'control')
            module.ROOT = root
            absorbed = module.replay('HEAD', None)
            self.assertEqual(git('show', f'{absorbed}:value'), 'after')
            git('checkout', '-q', base)
            (root / 'patches').mkdir()
            (root / 'patches/0001.patch').write_text(patch)
            (root / 'patches/series').write_text('0001.patch\n')
            (root / 'value').write_text('conflict\n')
            git('commit', '-qam', 'conflict')
            with self.assertRaises(RuntimeError):
                module.replay('HEAD', None)

    def test_release_identity(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('release_tag', 'scripts/release_tag.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        refs = 'aaa refs/tags/v3.37.0-2026.10.08.1\nbbb refs/tags/v3.37.0-2026.10.08.2'
        self.assertEqual(module.select_tag('v3.37.0', 'stable', 'aaa', refs, '2026.10.08'), 'v3.37.0-2026.10.08.1')
        self.assertEqual(module.select_tag('v3.37.0', 'stable', 'ccc', refs, '2026.10.08'), 'v3.37.0-2026.10.08.3')
        self.assertEqual(module.select_tag('v3.37.0', 'nightly', 'aaa', refs, '2026.10.08'), 'nightly-v3.37.0-2026.10.08.1')

    def test_replay_is_deterministic_and_has_patch_list(self):
        command = ['python3', 'scripts/replay_patches.py', '--base', 'upstream/main']
        first = subprocess.check_output(command, text=True).strip()
        second = subprocess.check_output(command, text=True).strip()
        self.assertEqual(first, second)
        files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', first], text=True).splitlines()
        self.assertFalse(any(name.startswith(('.github/workflows/', 'patches/')) for name in files))
        readme = subprocess.check_output(['git', 'show', f'{first}:README.md'], text=True)
        self.assertTrue(readme.startswith('This fork follows upstream [webchanges'))
        self.assertEqual([name for name in files if '/' not in name and name.startswith('README')], ['README.md'])
        self.assertIn('Patched webchanges', readme)
        self.assertIn('https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/', readme)
        upstream_readme = subprocess.check_output(['git', 'show', 'upstream/main:README.rst'], text=True)
        converted = subprocess.check_output(['pandoc', '-f', 'rst', '-t', 'gfm', '--wrap=none'], input=upstream_readme, text=True)
        self.assertEqual(readme.split('\n' + '-' * 72 + '\n\n', 1)[1], converted)
        self.assertEqual(subprocess.check_output(['git', 'show', f'{first}:docs/upstream-readme.rst'], text=True), upstream_readme)
        names = Path('patches/series').read_text().splitlines()
        for index, name in enumerate(names, 1):
            self.assertIn(f'{index}.  [{name}](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/{name})', readme)


if __name__ == '__main__':
    unittest.main()
