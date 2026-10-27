# webchanges hard fork

This repository is an independently maintained hard fork of mborsetti/webchanges. This child policy supersedes parent-folder upstream-plus-patches instructions for webchanges.

- `main` owns ordinary application source, tests, documentation and release automation. Edit source directly. Keep history linear; preserve existing remote `main` ancestry.
- Upstream v3.39.0 and all eight historical fork features are integrated. Future upstream updates are deliberate source integrations, not scheduled synchronization or patch replay.
- Preserve historical `patch-queue` branch and published tags. It is an archive, not active source of truth. Do not delete or rewrite it.
- Pushes to `main` build nightly wheel and sdist GitHub releases. Version tags `v<application version>` build stable GitHub releases. Preserve existing application version scheme; never publish to PyPI.
- Keep nightly identities separate from stable versions. Existing release records and immutable assets remain intact.
- Build/test candidate code without write credentials or production secrets. Separate trusted publisher verifies exact source revision, provenance and artifact hashes, then uses built-in GitHub tokens. Never execute downloaded application code with write credentials.
- Stable assets are immutable. Draft retries may fill missing assets only after matching existing bytes. Stop on mismatches or stale source refs.
- Run application regressions, release automation tests and real wheel/sdist builds for release changes.
