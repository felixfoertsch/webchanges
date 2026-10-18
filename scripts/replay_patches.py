#!/usr/bin/env python3
"""Replay fork patches onto an exact upstream commit in an isolated Git worktree."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = {
    "GIT_AUTHOR_NAME": "webchanges downstream bot",
    "GIT_AUTHOR_EMAIL": "webchanges-downstream@users.noreply.github.com",
    "GIT_COMMITTER_NAME": "webchanges downstream bot",
    "GIT_COMMITTER_EMAIL": "webchanges-downstream@users.noreply.github.com",
}


def git(*args: str, cwd: Path | None = None, capture: bool = False, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd or ROOT, text=True, stdout=subprocess.PIPE if capture else None, check=False,
        env=env,
    )
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed ({result.returncode})")
    return result.stdout.strip() if capture else ""


def series() -> list[Path]:
    names = [line.strip() for line in (ROOT / "patches" / "series").read_text().splitlines() if line.strip()]
    patches = [ROOT / "patches" / name for name in names]
    if not patches or any(not patch.is_file() for patch in patches):
        raise RuntimeError("patches/series must name existing patches")
    return patches


CONTROL_PATHS = (
    '.github/workflows/downstream.yml', '.mise.toml',
    'scripts/replay_patches.py', 'scripts/refresh_control.py', 'scripts/control-refresh.md',
    'scripts/normalize_sdist.py', 'scripts/package_candidate.py',
    'scripts/release_state.py', 'scripts/release_tag.py',
    'tests/test_downstream_workflow.py', 'tests/test_control_refresh.py',
    'tests/test_normalize_sdist.py', 'tests/test_package_candidate.py', 'tests/test_release_state.py',
)


def replay(base: str, output: Path | None, control: bool = False) -> str:
    temporary = output is None
    directory = Path(tempfile.mkdtemp(prefix="webchanges-replay-")) if temporary else output
    if directory.exists() and not temporary:
        raise RuntimeError(f"output already exists: {directory}")
    try:
        timestamp = git("show", "-s", "--format=%aI", base, capture=True)
        env = {**{k: v for k, v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN')}, **IDENTITY, "GIT_AUTHOR_DATE": timestamp, "GIT_COMMITTER_DATE": timestamp}
        git("worktree", "add", "--quiet", "--detach", str(directory), base)
        for patch in series():
            applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=directory, capture_output=True).returncode == 0
            if not applied:
                git("-c", "commit.gpgSign=false", "am", "--quiet", "--committer-date-is-author-date", str(patch), cwd=directory, env=env)
        if not control:
            (directory / "downstream-source.json").write_text(json.dumps({
                "upstream": git("rev-parse", f"{base}^{{commit}}", capture=True),
                "control": git("rev-parse", "HEAD", capture=True),
                "patches": [patch.name for patch in series()],
            }, sort_keys=True) + "\n")
        shutil.rmtree(directory / ".github" / "workflows", ignore_errors=True)
        shutil.rmtree(directory / "patches", ignore_errors=True)
        readme = directory / "README.rst"
        upstream_readme = readme.read_text()
        readme.write_text(
            "This fork follows upstream `webchanges <https://github.com/mborsetti/webchanges>`__ with ordered patches "
            + ", ".join(f"`{patch.name[:4]} <https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/{patch.name}>`__" for patch in series())
            + ". ``patch-queue`` owns workflows and patches; generated ``main`` contains upstream source plus all patches. Stable builds follow upstream releases; nightly builds follow upstream default branch.\n\n"
            "Patched webchanges\n==================\n\n"
            "Applied patches, oldest first:\n\n"
            + "\n".join(f"{index}. `{patch.name} <https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/{patch.name}>`__" for index, patch in enumerate(series(), 1))
            + "\n\n----\n\n"
            + readme.read_text()
        )
        header = readme.read_text().split("\n----\n\n", 1)[0]
        def markdown(text: str) -> str:
            return subprocess.check_output(["pandoc", "-f", "rst", "-t", "gfm", "--wrap=none"], input=text, text=True)
        (directory / "README.md").write_text(markdown(header) + "\n" + "-" * 72 + "\n\n" + markdown(upstream_readme))
        readme.unlink()
        metadata = directory / "pyproject.toml"
        metadata.write_text(metadata.read_text().replace("file = 'README.rst', content-type = 'text/x-rst'", "file = 'README.md', content-type = 'text/markdown'"))
        # Sphinx still consumes the exact upstream RST, outside the root README namespace.
        (directory / "docs" / "upstream-readme.rst").write_text(upstream_readme)
        index = directory / "docs" / "index.rst"
        index.write_text(index.read_text().replace("../README.rst", "upstream-readme.rst"))
        if control:
            for reserved in ('control-upstream.json', 'patches'):
                if git('ls-tree', base, '--', reserved, capture=True):
                    raise RuntimeError(f'upstream control ownership collision: {reserved}')
            (directory / 'control-upstream.json').write_text(json.dumps({
                'repository': 'https://github.com/mborsetti/webchanges.git',
                'ref': 'refs/heads/main',
                'commit': git('rev-parse', f'{base}^{{commit}}', capture=True),
            }, sort_keys=True) + '\n')
            for path in CONTROL_PATHS + tuple('patches/' + patch.name for patch in series()) + ('patches/series',):
                if git('ls-tree', base, '--', path, capture=True):
                    raise RuntimeError(f'upstream control ownership collision: {path}')
                source = ROOT / path
                target = directory / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        git("add", "-A", cwd=directory)
        changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=directory).returncode != 0
        if changed:
            git("-c", "commit.gpgSign=false", "commit", "--quiet", "-m", "Apply downstream metadata", cwd=directory, env=env)
        result = git("rev-parse", "HEAD", cwd=directory, capture=True)
        if control and git('rev-parse', f'{result}^{{tree}}', capture=True) == git('rev-parse', 'HEAD^{tree}', capture=True):
            if subprocess.run(['git', 'merge-base', '--is-ancestor', base, 'HEAD'], cwd=ROOT).returncode == 0:
                return git('rev-parse', 'HEAD', capture=True)
        return result
    finally:
        if temporary:
            git("worktree", "remove", "--force", str(directory))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="upstream/main")
    parser.add_argument("--output", type=Path)
    parser.add_argument('--control', action='store_true')
    args = parser.parse_args()
    try:
        print(replay(args.base, args.output, args.control))
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
