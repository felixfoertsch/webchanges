#!/usr/bin/env python3
"""Trusted old-control refresh checks and narrowly scoped Git/API actuators."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import replay_patches
from replay_patches import git, replay


def root() -> Path:
    return replay_patches.ROOT

UPSTREAM = 'https://github.com/mborsetti/webchanges.git'
REPO = 'felixfoertsch/webchanges'


def sha(value: str) -> str:
    if not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('expected full commit SHA')
    return value


def candidate(base: str) -> str:
    sha(base)
    old = git('rev-parse', 'HEAD', capture=True)
    metadata = json.loads((root() / 'control-upstream.json').read_text())
    if metadata.get('repository') != UPSTREAM or metadata.get('ref') != 'refs/heads/main':
        raise RuntimeError('upstream repository/ref changed')
    selection = git('ls-remote', '--symref', UPSTREAM, 'HEAD', capture=True)
    if selection.splitlines()[0] != 'ref: ' + metadata['ref'] + '\tHEAD':
        raise RuntimeError('upstream default branch changed')
    previous = sha(metadata['commit'])
    if subprocess.run(['git', 'merge-base', '--is-ancestor', previous, base], cwd=root()).returncode:
        raise RuntimeError('upstream ancestry changed')
    reconstructed = replay(previous, None, True)
    if git('rev-parse', f'{old}^{{tree}}', capture=True) != git('rev-parse', f'{reconstructed}^{{tree}}', capture=True):
        raise RuntimeError('unknown control/source customizations; reconstruct old control before refresh')
    result = replay(base, None, True)
    if git('rev-parse', f'{old}:.github/workflows', capture=True) != git('rev-parse', f'{result}:.github/workflows', capture=True):
        raise RuntimeError('workflow tree changed during refresh')
    return result


def verify_bundle(directory: Path, old: str) -> None:
    manifest = json.loads((directory / 'manifest.json').read_text())
    bundle = directory / 'control.bundle'
    if manifest != {'old': sha(old), 'sha256': hashlib.sha256(bundle.read_bytes()).hexdigest()}:
        raise RuntimeError('backup hash/head mismatch')
    with tempfile.TemporaryDirectory(prefix='webchanges-restore-') as temp:
        restored = Path(temp)
        git('init', '--bare', '--quiet', str(restored))
        git('bundle', 'verify', str(bundle.resolve()), cwd=restored)
        git('fetch', '--quiet', str(bundle.resolve()), 'refs/backup/control-' + old + ':refs/heads/patch-queue', cwd=restored)
        if git('rev-parse', 'refs/heads/patch-queue', cwd=restored, capture=True) != old:
            raise RuntimeError('backup restore head mismatch')
        git('fsck', '--full', '--no-dangling', cwd=restored)


def backup(directory: Path, old: str) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    if git('rev-parse', 'HEAD', capture=True) != sha(old):
        raise RuntimeError('backup HEAD changed')
    bundle = directory / 'control.bundle'
    ref = 'refs/backup/control-' + old
    git('update-ref', ref, old, '0' * 40)
    try:
        git('bundle', 'create', str(bundle.resolve()), ref)
    finally:
        git('update-ref', '-d', ref, old)
    (directory / 'manifest.json').write_text(json.dumps({'old': old, 'sha256': hashlib.sha256(bundle.read_bytes()).hexdigest()}, sort_keys=True) + '\n')
    verify_bundle(directory, old)


def api(endpoint: str, *args: str) -> str:
    return subprocess.check_output(['gh', 'api', endpoint, *args], text=True).strip()


def freshness(old: str, upstream: str) -> None:
    if api(f'repos/{REPO}', '--jq', '.default_branch') != 'patch-queue':
        raise RuntimeError('fork default branch changed')
    default = api('repos/mborsetti/webchanges', '--jq', '.default_branch')
    if default != 'main':
        raise RuntimeError('upstream default branch changed')
    if git('ls-remote', UPSTREAM, 'refs/heads/' + default, capture=True).split()[0] != upstream:
        raise RuntimeError('upstream advanced')
    if git('ls-remote', 'origin', 'refs/heads/patch-queue', capture=True).split()[0] != old:
        raise RuntimeError('control advanced')


def promote(old: str, upstream: str, expected: str, directory: Path, rebuild: bool) -> None:
    for value in (old, upstream, expected):
        sha(value)
    if git('rev-parse', 'HEAD', capture=True) != old:
        raise RuntimeError('not trusted old control checkout')
    tokens = {key: os.environ.pop(key) for key in ('GH_TOKEN', 'GITHUB_TOKEN') if key in os.environ}
    try:
        result = candidate(upstream)
    finally:
        os.environ.update(tokens)
    if result != expected:
        raise RuntimeError('candidate mismatch')
    verify_bundle(directory, old)
    archive = 'refs/tags/archive/patch-queue/' + old
    found = git('ls-remote', '--refs', 'origin', archive, capture=True)
    if found and found.split()[0] != old:
        raise RuntimeError('archive tag must point directly to old control')
    freshness(old, upstream)
    if result == old:
        return
    args = ['-c', 'credential.helper=!gh auth git-credential', 'push', '--atomic', 'origin',
            f'--force-with-lease=refs/heads/patch-queue:{old}', f'{result}:refs/heads/patch-queue']
    if not found:
        args += [f'--force-with-lease={archive}:', f'{old}:{archive}']
    git(*args)
    if git('ls-remote', '--refs', 'origin', 'refs/heads/patch-queue', archive, capture=True).splitlines() != sorted([
        result + '\trefs/heads/patch-queue', old + '\t' + archive,
    ], key=lambda line: line.split('\t')[1]):
        raise RuntimeError('promoted branch/archive readback mismatch; no dispatch')
    # GITHUB_TOKEN pushes do not trigger push workflows. Exact-SHA binding rejects stale dispatches.
    api(f'repos/{REPO}/actions/workflows/downstream.yml/dispatches', '--method', 'POST',
        '-f', 'ref=patch-queue', '-f', f'inputs[expected_control]={result}',
        '-f', f'inputs[rebuild]={str(rebuild).lower()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('candidate', 'backup', 'verify', 'promote'))
    parser.add_argument('--upstream')
    parser.add_argument('--old')
    parser.add_argument('--expected')
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()
    if args.action == 'candidate':
        print(candidate(args.upstream))
    elif args.action == 'backup':
        backup(args.directory, args.old)
    elif args.action == 'verify':
        verify_bundle(args.directory, args.old)
    else:
        promote(args.old, args.upstream, args.expected, args.directory, args.rebuild)
