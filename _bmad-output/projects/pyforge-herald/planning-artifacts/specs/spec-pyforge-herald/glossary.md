# Glossary — Herald (pointers only)

Companion to `SPEC.md`, added 2026-11-01 (EGM fleet audit, marshal Story 113.7; finding HER-M-C6). It names the
station terms the audit's fresh-context reviewers met undefined in CAP-58..CAP-61, one line each, and points at the
place that defines each; it restates nothing defined elsewhere. Fleet terms (station, `CAP-n`, `FR-n`, `AD-n` and its
prefixes, Lane 1, Twin, Tier, the rebase, Path B) are defined in
`docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` § 0; a qualified `spec-<x>:CAP-n` cite follows its § 2.

Spine below means `_bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md`.

## The Pages site

- **herald:AD-21** — one Pages artifact, one owner per path prefix, one deploy caller: spine § *AD-21*, with its 2026-10-14 amendment.
- **The placement rule** — which surfaces live on Pages and which on Lane 1: spine § *AD-21*, amendment of 2026-10-14.
- **AD-21 rule 5 (vendored)** — upstream files kept byte-identical and exempt from the origin check: spine § *AD-21* rule 5; the files are `docs-site/scripts/pages.mts`'s `VENDORED`.
- **herald:AD-23** — one generator renders every prefix; another station's output is data it reads: spine § *AD-23*.
- **One registry** — `docs/map.yaml` `sections:`, the source of every menu: `spec-pyforge-doctor:CAP-90`; CAP-58.
- **Section, menu entry** (older text: *nav tile*) — one `docs/map.yaml` `sections:` row and the menu links it yields: CAP-58.
- **Mount** — a static tree copied into the artifact unbuilt (Kedro-Viz, Vizro, marketplace): CAP-60; `NOT_PAGES` in `docs-site/src/lib/artifact.ts`.
- **`kedro-viz-export` artifact** — atlas's Actions artifact that fills the Kedro-Viz mount: `spec-pyforge-atlas:CAP-62`; CAP-60.
- **Guild step** — a step of steward's `.github/workflows/pages.yml` run in the Guild env: `spec-pyforge-steward:CAP-168`; CAP-60.
- **Build input** — a gitignored file a Guild step writes before the build (`fleet-status.json` and the `/changes/` and `/status/runs/` inputs): CAP-60, CAP-61; `PAGES_BUILD_INPUTS_DIR` in `docs-site/src/lib/agent-surface.ts`; the unwritten ones are `DW-steward-43-6-1`.
- **Snapshot** — `docs-site/src/content/ci-status.json`, the committed CI status the tile and `/status/ci/` read: CAP-59.
- **Built-from line** — the footer naming the build: CAP-61; `docs-site/src/lib/built-from.ts`.
- **The URL set** (older text: *every URL the 2026-10-13 artifact held*) — the list `test_one_generator.py`'s AC7 test enumerates: CAP-61.

## The dossier

- **The artifact build** — `herald/artifact/dossier.html`, the body-only dossier for the Claude Artifact tool: CAP-47; `docs-site/README.md` § *The artifact build*.
- **Block type** — the `type:` of a dossier block, drawn by `renderBlock`: CAP-61; `docs-site/src/lib/dossier-blocks.ts`.
- **The measurer** — `docs-site/scripts/verify_claims.py`: CAP-46.
- **`check:` stat** (as `check: src_lines`) — a dossier stat the measurer computes at build: CAP-46, CAP-61; `docs-site/src/content/dossier/dossier.yml`.

## The decks

- **The ten families** — the deck families the gallery shows, one per `site.yml` `infographics` include: CAP-35, CAP-61.
- **HTML twin** — a deck's self-contained browser copy: CAP-55. **Local twin** — a presentation's copy of its Design project: CAP-30. Neither is CHAIN-STANDARD § 0's *Twin*.
- **Poster, fact ledger** — `infographic-standard.md` and `facts-ledger.md` beside this file; **the trio**, CAP-20; the six acts, `six-act-framework.md`; the Design bridge and etags, `bridge-protocol.md`.

## The record

- **This memlog** — `.memlog.md` beside this file, the canonical record `SPEC.md` is derived from.
- **Design-thinking § *Target information architecture*** — `_bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md`.
- **The reconcile, the scoped stamp** — `AGENTS.md` § *Pre-PR Pre-flight Checklist* item 5.
