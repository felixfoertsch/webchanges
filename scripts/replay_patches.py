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
        ["git", *args], cwd=cwd or ROOT, text=True, stdout=subprocess.PIPE if capture else None, check=False,
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


def replay(base: str, output: Path | None) -> str:
    temporary = output is None
    directory = Path(tempfile.mkdtemp(prefix="webchanges-replay-")) if temporary else output
    if directory.exists() and not temporary:
        raise RuntimeError(f"output already exists: {directory}")
    try:
        timestamp = git("show", "-s", "--format=%aI", base, capture=True)
        env = {**os.environ, **IDENTITY, "GIT_AUTHOR_DATE": timestamp, "GIT_COMMITTER_DATE": timestamp}
        git("worktree", "add", "--quiet", "--detach", str(directory), base)
        for patch in series():
            applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=directory, capture_output=True).returncode == 0
            if not applied:
                git("-c", "commit.gpgSign=false", "am", "--quiet", "--committer-date-is-author-date", str(patch), cwd=directory, env=env)
        (directory / "downstream-source.json").write_text(json.dumps({
            "upstream": git("rev-parse", f"{base}^{{commit}}", capture=True),
            "control": git("rev-parse", "HEAD", capture=True),
            "patches": [patch.name for patch in series()],
        }, sort_keys=True) + "\n")
        shutil.rmtree(directory / ".github" / "workflows", ignore_errors=True)
        shutil.rmtree(directory / "patches", ignore_errors=True)
        readme = directory / "README.rst"
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
        git("add", "-A", cwd=directory)
        changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=directory).returncode != 0
        if changed:
            git("-c", "commit.gpgSign=false", "commit", "--quiet", "-m", "Apply downstream metadata", cwd=directory, env=env)
        return git("rev-parse", "HEAD", cwd=directory, capture=True)
    finally:
        if temporary:
            git("worktree", "remove", "--force", str(directory))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="upstream/main")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        print(replay(args.base, args.output))
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
