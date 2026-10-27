#!/usr/bin/env python3
"""Validate package identity and immutable release bytes without importing application code."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True).strip()


def identity(source, ref, run):
    version = re.search(r'^__version__ = [\'\"]([^\'\"]+)', (source / 'webchanges/__init__.py').read_text(), re.M)[1]
    version = version.split('+')[0]
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('source version must be numeric major.minor.patch')
    if ref.startswith('refs/tags/'):
        if ref != 'refs/tags/v' + version:
            raise ValueError('tag and source version differ')
        return ref.removeprefix('refs/tags/'), version, False
    if ref != 'refs/heads/main' or not str(run).isdigit():
        raise ValueError('unsupported build ref')
    return 'nightly-' + os.environ['GITHUB_SHA'], version + '+nightly.' + os.environ['GITHUB_SHA'], True


def describe(dist: Path, expected: str) -> dict:
    names = {f'webchanges-{expected}.tar.gz', f'webchanges-{expected}-py3-none-any.whl'}
    if {p.name for p in dist.iterdir()} != names:
        raise ValueError('unexpected package files')
    hashes = {}
    for name in sorted(names):
        path = dist / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('package must be regular file')
        if name.endswith('.whl'):
            with zipfile.ZipFile(path) as archive:
                metadata = [n for n in archive.namelist() if n.endswith('/METADATA')]
                if len(metadata) != 1:
                    raise ValueError('ambiguous wheel metadata')
                data = archive.read(metadata[0])
        else:
            with tarfile.open(path) as archive:
                metadata = [n for n in archive.getmembers() if n.name.count('/') == 1 and n.name.endswith('/PKG-INFO')]
                if len(metadata) != 1 or not metadata[0].isfile():
                    raise ValueError('ambiguous sdist metadata')
                data = archive.extractfile(metadata[0]).read()
        parsed = BytesParser().parsebytes(data)
        if parsed['Name'] != 'webchanges' or parsed['Version'] != expected:
            raise ValueError('package identity differs')
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def resolve(repo, ref):
    obj = json.loads(gh('api', f'repos/{repo}/git/ref/{ref}'))['object']
    for _ in range(10):
        if obj['type'] == 'commit':
            return obj['sha']
        if obj['type'] != 'tag':
            break
        obj = json.loads(gh('api', f'repos/{repo}/git/tags/{obj["sha"]}'))['object']
    raise ValueError('tag does not resolve to commit')


def download(repo, asset):
    return subprocess.check_output(
        ['gh', 'api', '-H', 'Accept: application/octet-stream', f'repos/{repo}/releases/assets/{asset["id"]}']
    )


def publish(repo, tag, sha, nightly, files):
    def fresh():
        if resolve(repo, 'heads/main' if nightly else 'tags/' + tag) != sha:
            raise ValueError('stale source ref')
        # Listing permits absent nightly tags without treating API failures as absence.
        pages = json.loads(gh('api', '--paginate', '--slurp', f'repos/{repo}/git/refs/tags'))
        found = [r for page in pages for r in page if r['ref'] == 'refs/tags/' + tag]
        if len(found) > 1 or found and resolve(repo, 'tags/' + tag) != sha:
            raise ValueError('existing tag differs from source')

    def verify(release, complete=False):
        if release['prerelease'] != nightly or release['tag_name'] != tag:
            raise ValueError('release classification differs')
        names = [a['name'] for a in release['assets']]
        if len(names) != len(set(names)) or not set(names) <= set(files):
            raise ValueError('duplicate or unexpected release assets')
        if complete and set(names) != set(files):
            raise ValueError('uploaded asset set differs')
        for asset in release['assets']:
            if download(repo, asset) != files[asset['name']].read_bytes():
                raise ValueError('immutable asset bytes differ')
        return set(names)

    fresh()
    pages = json.loads(gh('api', '--paginate', '--slurp', f'repos/{repo}/releases'))
    matches = [r for page in pages for r in page if r['tag_name'] == tag]
    if len(matches) > 1:
        raise ValueError('duplicate release')
    if not matches:
        created = json.loads(gh(
            'api', '--method', 'POST', f'repos/{repo}/releases',
            '-f', f'tag_name={tag}', '-f', f'target_commitish={sha}',
            '-f', f'name={tag}', '-f', f'body=Source: {sha}',
            '-F', 'draft=true', '-F', f'prerelease={str(nightly).lower()}',
            '-f', 'make_latest=false' if nightly else 'make_latest=true',
        ))
        matches = [created]
    if len(matches) != 1:
        raise ValueError('expected one release after creation')
    endpoint = f'repos/{repo}/releases/{matches[0]["id"]}'
    release = json.loads(gh('api', endpoint))
    present = verify(release)
    missing = [str(p) for name, p in files.items() if name not in present]
    if not release['draft']:
        if missing:
            raise ValueError('published release incomplete')
        fresh()
        return
    if missing:
        fresh()
        gh('release', 'upload', tag, '--repo', repo, *missing)
    verify(json.loads(gh('api', endpoint)), complete=True)
    fresh()
    gh('release', 'edit', tag, '--repo', repo, '--draft=false')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'manifest', 'publish'])
    args = parser.parse_args()
    root = Path.cwd()
    tag, version, nightly = identity(root, os.environ['GITHUB_REF'], os.environ['GITHUB_RUN_NUMBER'])
    sha = os.environ['GITHUB_SHA']
    if args.mode == 'prepare':
        p = root / 'webchanges/__init__.py'
        p.write_text(re.sub(r'(__version__ = [\'\"])[^\'\"]+', lambda m: m[1] + version, p.read_text()))
        return
    manifest = root / 'candidate/provenance.json'
    dist = root / 'candidate/dist'
    data = {'commit': sha, 'tag': tag, 'version': version, 'assets': describe(dist, version)}
    if args.mode == 'manifest':
        manifest.write_text(json.dumps(data, sort_keys=True) + '\n')
        return
    if json.loads(manifest.read_text()) != data:
        raise ValueError('provenance or artifact hash mismatch')
    repo = os.environ['GITHUB_REPOSITORY']
    publish(repo, tag, sha, nightly, {p.name: p for p in [*dist.iterdir(), manifest]})


if __name__ == '__main__':
    main()
