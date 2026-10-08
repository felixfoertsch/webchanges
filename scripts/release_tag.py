#!/usr/bin/env python3
"""Select collision-safe dated release identities; retry exact source only."""
import argparse
from datetime import datetime
import re
import sys
from zoneinfo import ZoneInfo


def select_tag(upstream: str, channel: str, commit: str, refs: str, date: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', upstream):
        raise ValueError('unsafe upstream tag')
    prefix = f'{"nightly-" if channel == "nightly" else ""}{upstream}-{date}.'
    found = []
    for line in refs.splitlines():
        sha, ref = line.split()
        name = ref.removeprefix('refs/tags/')
        if name.startswith(prefix) and name[len(prefix):].isdigit():
            found.append((int(name[len(prefix):]), sha, name))
    for _, sha, name in sorted(found, reverse=True):
        if sha == commit:
            return name
    return prefix + str(max((number for number, _, _ in found), default=0) + 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--channel', choices=('stable', 'nightly'), required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    date = datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y.%m.%d')
    print(select_tag(args.upstream, args.channel, args.commit, sys.stdin.read(), date))
