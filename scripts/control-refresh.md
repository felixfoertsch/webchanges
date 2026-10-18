# Control refresh ownership

`patches/series` owns application changes. Explicit `CONTROL_PATHS` in
`replay_patches.py` owns fork automation. `control-upstream.json` records the
selected upstream repository, ref and commit; refresh rejects rewritten upstream
ancestry, unknown source changes and reserved-path collisions.

Migration preserves the offline SMTP test repair introduced by infrastructure
commit `36428af2885b825d78c67c5e3b205919ce6d43eb`. Parent review assigned this existing
email-testing follow-up to accepted patch `0001`, keeping eight accepted ideas.
The patch retains original authorship and subject; this control change owns the
additional diff, not the historical patch author's original commit. Other seven
patches remain byte-identical. Published tags and assets retain original source.
New reconstructed source needs new release identities.

Refresh builds candidates without write credentials. Old-control code separately
reconstructs before promotion, restores the downloaded self-contained backup into
an empty repository, checks workflow tree identity, rechecks remote selection and
heads, then atomically archives the old head and replaces control using explicit
leases. No atomic support means failure. Remote branch and direct archive targets
are read back before dispatch; missing/wrong targets or read failures stop without
dispatch, retagging or rollback. Existing archive tags rely on immutability policy:
Git skips up-to-date tags, so leases cannot lock them against concurrent admin
mutation. Readback detects persistent changes, not mutations after that check.
Archive tags are permanent lightweight tags, not release versions. Dispatch binds the new exact control SHA and preserves
manual rebuild intent. Dispatch failure fails the run; the next schedule at the
new control head reaches ordinary publication through a no-op refresh.

GitHub-hosted jobs separate build from trusted promotion. No candidate setup,
hooks or application code runs with repository-write credentials. Initial local
migration and actual job-token atomic/dispatch capability require separate review.
