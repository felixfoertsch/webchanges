#!/usr/bin/env python3
"""Normalize setuptools sdist metadata for byte-identical draft retries."""
import gzip
import io
import sys
import tarfile
from pathlib import Path


def normalize(path: Path, epoch: int) -> None:
    output = io.BytesIO()
    with tarfile.open(path, 'r:gz') as source, tarfile.open(fileobj=output, mode='w', format=tarfile.PAX_FORMAT) as target:
        for member in source:
            member.mtime = epoch
            member.uid = member.gid = 0
            member.uname = member.gname = ''
            member.pax_headers = {key: value for key, value in member.pax_headers.items() if key not in ('mtime', 'atime', 'ctime')}
            target.addfile(member, source.extractfile(member) if member.isfile() else None)
    with path.open('wb') as file, gzip.GzipFile(filename='', mode='wb', fileobj=file, mtime=epoch) as compressed:
        compressed.write(output.getvalue())


if __name__ == '__main__':
    normalize(Path(sys.argv[1]), int(sys.argv[2]))
