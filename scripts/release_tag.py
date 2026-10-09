#!/usr/bin/env python3
"""Select collision-safe dated release identities; retry exact source only."""
import argparse
from datetime import datetime
import re
import sys
from zoneinfo import ZoneInfo


def select_tag(upstream: str, channel: str, commit: str, refs: str, date: str, force: bool = False) -> str:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', upstream):
        raise ValueError('unsafe upstream tag')
    stem = f'{"nightly-" if channel == "nightly" else ""}{upstream}-'
    found = []
    for line in refs.splitlines():
        sha, ref = line.split()
        name = ref.removeprefix('refs/tags/')
        match = re.fullmatch(re.escape(stem) + r'(\d{4}\.\d{2}\.\d{2})\.(\d+)', name)
        if match:
            found.append((match[1], int(match[2]), sha, name))
    if not force:
        for _, _, sha, name in sorted(found, reverse=True):
            if sha == commit:
                return name
    return stem + date + '.' + str(max((number for day, number, _, _ in found if day == date), default=0) + 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--channel', choices=('stable', 'nightly'), required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    date = datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y.%m.%d')
    print(select_tag(args.upstream, args.channel, args.commit, sys.stdin.read(), date, args.force))
