#!/usr/bin/env python3
"""Validate immutable GitHub Release metadata and asset digests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def assets(release: dict, expected: set[str]) -> dict[str, str]:
    found = {asset["name"]: asset.get("digest", "").removeprefix("sha256:") for asset in release["assets"]}
    unknown = set(found) - expected
    if unknown or any(len(found.get(name, "")) != 64 for name in found):
        raise ValueError("unexpected or unhashed release asset")
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("release", type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--asset", action="append", required=True)
    parser.add_argument("--dist", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    release = json.loads(args.release.read_text())
    if release["target_commitish"] != args.commit:
        raise SystemExit("release target differs")
    found = assets(release, set(args.asset))
    if args.dist:
        local = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in args.dist.iterdir()}
        if any(local.get(name) != digest for name, digest in found.items()):
            raise SystemExit("release asset digest differs")
    if release["draft"] and not args.require_complete:
        print("partial")
        return 0
    if set(found) != set(args.asset):
        raise SystemExit("published release lacks expected assets")
    if args.dist and local != found:
        raise SystemExit("release asset digest differs")
    print("complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
