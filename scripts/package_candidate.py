#!/usr/bin/env python3
"""Describe and validate package bytes without importing generated source."""
import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
import tarfile
import zipfile


def version(source: Path, tag: str) -> str:
    upstream = re.search(r'^__version__ = [\'\"]([^\'\"]+)', (source / 'webchanges/__init__.py').read_text(), re.M)[1]
    suffix = re.search(r'-(\d{4})\.(\d{2})\.(\d{2})\.(\d+)$', tag)
    if not suffix:
        raise ValueError('invalid release identity')
    return upstream.split('+')[0] + '+' + ('nightly' if tag.startswith('nightly-') else 'stable') + '.' + '.'.join(str(int(n)) for n in suffix.groups())


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--dist', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    expected = version(args.source, args.tag)
    result = {'tag': args.tag, 'commit': args.commit, 'version': expected,
              'source': json.loads((args.source / 'downstream-source.json').read_text()),
              'assets': describe(args.dist, expected)}
    if args.verify:
        if json.loads(args.manifest.read_text()) != result:
            raise SystemExit('candidate provenance or digest differs')
    else:
        args.manifest.write_text(json.dumps(result, sort_keys=True) + '\n')
