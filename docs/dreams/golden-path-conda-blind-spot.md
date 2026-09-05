---
title: A promotion gate that has never seen what it ships
type: dream
owner: warden
status: specified
---

# A promotion gate that has never seen what it ships

## The Dream

`golden-path-promotion` (Story 43.4) ran for the first time on 2026-09-04. It
recorded a Warden verdict of **`indeterminate`** over 329 components, zero of
them assessed for vulnerabilities. That is not a fluke result waiting on a
rerun — the verdict is structurally incapable of ever saying `clean`, because
of what it is actually scanning.

Read `scripts/platform-golden-path-promotion.sh`'s own comment: *"Warden has
no per-environment selector and its lock reader does not accept this
workspace's pixi.lock yet, so the honest target is the workspace manifest
alone, staged in a scratch dir."* The gate does not scan the resolved,
pinned closure that ships inside the platform image. It scans a bare
`pixi.toml` — no locked versions, no per-environment scoping — because
Warden's `PixiLockExtractor` was built (Story 2.2) to flatten *every*
environment and platform the lockfile ever resolved into one undifferentiated
set. That is a reasonable default for a manifest with one environment; it is
the wrong answer for this repo's `pixi.lock`, which resolves dozens of
environments — recipe tooling, docs, dev, five station test envs, and the one
that actually matters here, `python-agent-platform` — and unioning them all
would misrepresent what the deployed image contains far worse than scanning
nothing does.

Even where Warden *can* name a conda package's PyPI identity — Epic 2's
`spec-2-1-conda-pypi-map` already shipped a verified-confidence conda→pypi
map — a bare `pixi.toml` carries no locked version for anything but an exact
pin, so `classify_conda_specifier` degrades most of the inventory to
`NO_VERSION` before OSV ever gets a chance to match it. And even a perfectly
identified, perfectly versioned inventory would still come back
`indeterminate`: no CI job anywhere in this repo provisions the offline OSV
database. `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` is unset everywhere, and
Story 1.4's own decision record says a missing DB must route to
`indeterminate` rather than a false `clean` — which is correct, and exactly
what's happening, just for a reason nobody has gone back to fix.

One more piece completes the picture, and it isn't Warden's: `platform-deploy`
gates on the promotion *record existing*, not on `warden_status == "clean"`.
So today, a genuinely compromised image would promote exactly as freely as a
clean one, provided the script ran and wrote something. The record was meant
to be read, and nothing reads it yet.

Three structural gaps, one gate that has never been able to tell anyone
anything: it has never seen the image it's promoting, never had a database to
check against, and its one consumer never asked what it said.

## What it looks like when real

- `golden-path-promotion` scans the *actual* resolved `python-agent-platform`
  environment out of the root `pixi.lock` — real pinned versions, the thing
  that is actually built into the image — not a bare, unresolved `pixi.toml`.
- Warden's lockfile reader can be told which environment (and platform) to
  extract, instead of flattening every environment in the file into one set.
  A deploy gate needs to answer "what is IN this image", not "what exists
  anywhere in this monorepo's dev tooling."
- CI provisions the offline OSV database through the mechanism Story 1.4
  already designed and accepted — a conda-packaged DB, an explicit
  `--download-offline-databases` run on a connected machine, or a mirror — so
  `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` points at something real instead of
  nothing.
- `platform-deploy`'s verifier refuses any digest whose recorded verdict is
  not `clean` — not merely one whose record is missing.
- The verdict finally says something true: `clean` when the shipped
  environment's conda+pypi closure is actually scanned end to end,
  `indeterminate`/`warn` only for a real, specific, nameable gap — never a
  permanent architectural `indeterminate` that no amount of correct behavior
  could ever clear.

## What is real (measured 2026-09-04, `retro-pyforge-steward-2026-09-04.md`)

- `golden-path-promotion`'s first-ever run: `warden_status: indeterminate`,
  329 components, vulnerability axis 0 assessed.
- `scripts/platform-golden-path-promotion.sh` stages a bare `pixi.toml` (no
  lock) in a scratch dir as its scan target, by explicit, commented design —
  not an oversight, a documented workaround for the two gaps above.
- `pyforge-warden/extract/lockfiles.py::PixiLockExtractor`'s own docstring:
  "every package the file ever resolved, across all environments/platforms —
  no per-environment/per-platform selection" (Story 2.2-era decision).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-2-1-conda-pypi-map-the-ecosystem-identity-predicate.md`
  — verified-confidence conda→pypi identity mapping, already shipped (Epic 2).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/osv-db-offline-provisioning-decision.md`
  — Story 1.4 spike, **accepted** 2026-07-14: the offline-DB mechanism,
  staleness rule, cold-start disposition, and trust model are all already
  specified in detail. Nobody has wired the CI-side provisioning step it
  describes.
- `scripts/platform-deploy-verify-promotion.py` refuses a digest only when the
  promotion record is absent; it does not inspect `warden_status`.

## Constraints

- **Never promote to `clean` by loosening what counts as scanned.** An
  environment selector that still can't resolve a component's identity must
  keep withholding it (`UNMAPPED_ECOSYSTEM`), never quietly drop it from the
  denominator to make the percentage look better.
- **Reuse the two already-accepted designs.** `spec-2-1`'s conda→pypi map and
  the Story 1.4 OSV-DB decision record are correct and already gate other
  stories (1.5, 2.4) — this Dream wires them into the golden-path, it does not
  re-derive matching or staleness semantics from scratch.
- **Stay offline-first (NFR-S2).** Provisioning the database is an explicit,
  non-default CI step; the scan itself never egresses silently.
- **The two halves of the gate land together.** Warden producing a real
  verdict and `platform-deploy` actually reading it (steward's flip, record-
  exists → status-is-clean) are one effort, not two — a real verdict nobody
  gates on is exactly as useless as no verdict at all.

## Non-goals

- **Not** a general-purpose multi-environment/multi-platform selector for
  every future Warden caller. Build only what the golden-path use case needs
  — one named environment, the current platform — and widen it later if a
  second caller actually needs more.
- **Not** a new conda-native vulnerability data source. OSV via the verified
  conda→pypi identity is the v1 answer the accepted decision record already
  chose; revisit only if that proves insufficient in practice.
- **Not** touching the CFE atlas's own separate `pixi.lock` parser
  (`scan_project`) — a different, already-working subsystem. This Dream is
  scoped to `pyforge-warden/extract/lockfiles.py` and the golden-path script.

## Realization log

- **2026-09-04** — Captured, from `retro-pyforge-steward-2026-09-04.md` action
  item 8. Root cause traced to two comments already sitting in the code
  rather than assumed: `scripts/platform-golden-path-promotion.sh`'s own note
  on why it scans a bare `pixi.toml`, and `PixiLockExtractor`'s docstring
  naming the flattening as a deliberate Story-2.2 scope decision that has
  since become the actual blocker. The two designs this Dream leans on
  (`spec-2-1-conda-pypi-map`, the Story 1.4 OSV-DB decision record) were both
  already accepted before this Dream existed — verified by reading them, not
  assumed from their titles.
- **2026-09-05** — Spec distilled (`bmad-spec`, express mode) at
  `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-golden-path-conda-blind-spot/`
  — five capabilities, four constraints, five open questions for the operator;
  status `draft`. **Correction to § What is real:**
  `scripts/platform-deploy-verify-promotion.py` has refused any verdict that is
  not `clean` since `1016f4e763` (2026-09-04, after this Dream's measurement),
  so the third gap is closed and the gate is fail-closed today — nothing
  promotes until the verdict is real. Preserved in the Spec as CAP-5.
