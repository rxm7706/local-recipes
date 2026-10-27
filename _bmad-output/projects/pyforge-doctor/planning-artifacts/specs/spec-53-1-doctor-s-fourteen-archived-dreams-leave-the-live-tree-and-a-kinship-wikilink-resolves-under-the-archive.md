---
title: "53.1: Doctor's fourteen archived Dreams leave the live tree, and a Kinship wikilink resolves under the archive"
type: 'chore'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
baseline_revision: '97c8211773'
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/dreams/one-chain-per-station.md
  - docs/dreams/pyforge-doctor.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pixi_currency.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** `spec-one-chain-per-station:CAP-11` (operator ruling 2026-09-29; CHAIN-STANDARD §11) says a Dream is live in
`docs/dreams/` or archived under `archive/docs/dreams/`, never both, and that a folded satellite leaves the live tree only
once its whole body sits verbatim in a dated section of its station Dream. The readers landed on 2026-09-29/30 (doctor
36.1 and 36.2, marshal 75.1, herald 33.1) and no fold PR followed: at `97c8211773` (2026-10-26) 14 doctor Dreams under
`docs/dreams/` still read `status: archived` (`bmad-drift-new-artifact-shape`, `bmad-method-version-drift`, `capability-effect-check`, `chain-currency-sweep`, `deferred-work-audit-completeness`, `deferred-work-resolution-sweep`, `deferred-work-visibility`, `docs-shelf-alignment`, `fleet-hygiene-verification-exemplar-program`, `general-docs-consistency`, `pixi-candidate-currency`, `pyforge-doctor-dependency-health`, `sibling-dreams-drift`, `status-body-consistency`), each behind the `Consolidated into` banner the 2026-09-16/17 fold
left, and doctor's `fold-complete` named them in its one WARN.

**Approach:**
- **Fold first, verbatim.** For each of the 14 satellites whose long paragraphs were not all in `docs/dreams/pyforge-doctor.md`
  (measured with `fold-complete`'s own `long_paragraphs`: whitespace collapsed, headings dropped, paragraphs over 80
  characters), the whole body goes in as a dated `## 2026-10-26 — <title> (folded from <slug>)` section: verbatim, headings
  demoted one level, the one-chain banner left out, never trimmed (a body already partly there is pasted whole — the
  standard asks for the body, not the difference).
- **Then the move.** Every one of the 14 loses its one-chain banner (an older `Superseded` or `Absorbed` note is body and
  stays) and moves with `git mv` to `archive/docs/dreams/<same name>`, frontmatter unchanged (`status: archived` stays:
  location is the archive signal, CHAIN-STANDARD §11 as amended 2026-09-30).
- **Pointers follow; records do not.** The README's 14 interim rows leave with their files; `spec-pyforge-doctor/SPEC.md`'s
  `surface:` and `covers-dreams:` entries and the 15 absorbed pointer Specs whose `owner-dream:` named a moved file name the
  archive path (script render under the memlog, anchors asserted once, both self-validate passes logged). Memlogs, story
  specs, epic bodies, PRD prose, ledgers and the Dreams' own logs keep the path they were written with: a dated record
  names what was true when it was written.
- **A reader follows the move (CHAIN-STANDARD §11).** `dreams-hygiene`'s `kinship-wikilink-dead` resolved a `[[slug]]` against `docs/dreams/` alone; after the move, 605 wikilinks in live Dreams name a moved slug (126 distinct), and `chain.py` now reads `archive/docs/dreams/` as well (`_archived_dream_slugs`, the wikilink check only: the README-row and roster checks still walk `docs/dreams/`, so a moved Dream needs no row and its frontmatter is not judged). `pixi_currency.py` reads its four ledger sections from `archive/docs/dreams/pixi-candidate-currency.md` — the ledger it dates through `git log -L`, whose section clocks restart at the move commit (a known, named consequence; the alternative, reading the demoted copy inside `pyforge-doctor.md`, would change the section grammar).

Ledger key: `53-1-doctor-s-fourteen-archived-dreams-leave-the-live-tree-and-a-kinship-wikilink-resolves-under-the-archive`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-one-chain-per-station:CAP-11` (the Guild's; Doctor mints no CAP and no FR, the relay shape of doctor Epic 36, marshal
  Epic 75 and herald Epic 33); CHAIN-STANDARD §11.
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.
- Siblings: the other seven station stories of the 2026-10-26 one-PR move (atlas 44.1, doctor 53.1, herald 48.1, marshal
  111.1, mason 35.1, scribe 28.1, steward 115.1, warden 23.1).

## Acceptance Criteria

- Given the 14 doctor Dreams named above When `pixi run -e pyforge-guild fold-complete-check` runs Then each reads `fold-complete-ok` from `archive/docs/dreams/`, and `fold-complete-archived-in-live-tree` names no doctor Dream
- Given `docs/dreams/` after the move When `ls docs/dreams/*.md` is read Then no file carries `owner: doctor` with `status: archived`, and `docs/dreams/README.md` has no row for a moved file (`readme-table-orphan` is silent)
- Given a moved file When it is diffed against its pre-move content Then only the one-chain banner paragraph is gone; the frontmatter and every other line are unchanged
- Given every live pointer that named `docs/dreams/<moved>.md` When the repo is grepped Then it names `archive/docs/dreams/<moved>.md`, and `governance-currency`, `dreams-hygiene`, `dream-chain`, `chain-sprawl`, `spec-surface` and `detectors-ci` are green
- Given `docs/dreams/pyforge-doctor.md` When its 2026-10-26 sections are read Then each names the satellite it folds, its banner date, and the archive path

## Tasks

1. Measure: `long_paragraphs` of each archived doctor Dream against the station Dream's collapsed text.
2. Fold the incomplete bodies (dated sections, verbatim, headings demoted, banner left out); re-measure to zero missing.
3. Strip each banner and `git mv` the 14 files; run `fold-complete-check` and read its exit code.
4. Drop the README rows; re-point every live pointer; prune `docs/governance/chain-sprawl-baseline.json`.
5. Memlog event on `spec-pyforge-doctor` naming every surface path that moved or changed; script-render the Spec's `surface:` / `covers-dreams:` lines and the absorbed pointers' `owner-dream:`; scoped `--write-baseline --spec`.
6. Run the planning detectors and the station suite; read every verdict from the exit code.

## Boundaries & Constraints

**Always:**
- Paste a body whole and verbatim; demote headings; name the fold's source, banner date and archive path in the section's opening line.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not trim, rewrite or re-flow a satellite's text; do not reset or un-archive a moved Dream.
- Do not rewrite a dated record (memlog, story spec, epic body, PRD prose, ledger, research) to name the archive path.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| incomplete fold | satellite with paragraphs missing from the station Dream | dated section carries the whole body verbatim; `fold-complete-ok` after the move | — |
| complete fold | every paragraph already in the station Dream (banner aside) | no section added; banner stripped; `git mv` | — |
| older banner | `Superseded` / `Absorbed` blockquote from 2026-08 | kept as body; pasted with the body | — |
| wikilink to a moved slug | `[[slug]]` in a live Dream | resolves under the archive (`dreams-hygiene`) | — |
| dated record naming the old path | memlog, story spec, PRD prose | left as written | — |

</intent-contract>

## Binding

Parent capability: `spec-one-chain-per-station:CAP-11` (Guild relay; no doctor CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-10-26 — The archived Dreams leave the live tree*.
Ledger key: `53-1-doctor-s-fourteen-archived-dreams-leave-the-live-tree-and-a-kinship-wikilink-resolves-under-the-archive`.
Ledger status at mint: `done` (built in the same PR, the #2322 shape).
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run -e pyforge-guild fold-complete-check` — expected: exit 0; `fold-complete-archived-in-live-tree` absent.
- `pixi run -e pyforge-guild dreams-hygiene-check` — expected: exit 0; no `readme-table-orphan`, no `kinship-wikilink-dead`.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `grep -rl 'status: archived' docs/dreams/` — expected: no output.
- `ls archive/docs/dreams | wc -l` — expected: 165 (158 moved + the 7 already there).

## Review Triage Log

### 2026-10-26 — Independent review (fresh reviewer, diff `97c8211773..5e7549297e`, every check scripted over the whole set)
- verdicts: 8 findings — high 0, medium 3, low 5
- findings:
  - `[medium]` `[patch]` 13 archived marshal Dreams kept a second `Consolidated into` blockquote (the 2026-08-08 and 2026-09-16 sub-fold banners that sat after the H1) and their pasted sections carried it — stripped from the 13 files and from the 13 fold sections; `fold-complete` still reads 159/159.
  - `[medium]` `[patch]` two README prose links (`unity-data-stack.md`, `regenerable-factory.md`) pointed at moved files — re-pointed to `../../archive/docs/dreams/`.
  - `[medium]` `[patch]` 25 live pointers the first pass missed (three deck READMEs, `docs/MAP.md`, `docs/reference/README.md`, `docs/reference/container-base-layer-convention.md`, `docs/tutorials/local-platform-development.md`, `docs/foundry/guards/README.md`, doctor's `CHAIN-CURRENCY-RUNBOOK.md`, six `scripts/*.py` docstrings and one runtime message, herald's and steward's `marshal-policy.toml` path lists, Kinship lines in four live Dreams) — re-pointed. Two docstrings under `.claude/skills/conda-forge-expert/tests/meta/` are left for the next CFE retro: a commit touching the skill tree needs the `retro(cfe):` form and a CHANGELOG move.
  - `[low]` `[reject]` relative `[x.md](x.md)` links inside the 2026-09-16 fold sections of `pyforge-marshal.md` — a dated record, left as written.
  - `[low]` `[patch]` spec-surface not yet reconciled at review time — the memlog-first render and the scoped stamps follow in the same PR.
  - `[low]` `[reject]` the satellite's H1 demotes to an H2 beside the dated heading — the 2026-10-11 precedent's shape; literal §11.
  - `[low]` `[reject]` epic numbers skip two in five stations — deliberate, for two sibling sessions cut from the same main (the Guild memlog's correction of 2026-10-26).
  - `[low]` `[patch]` a historical docstring in `test_sources_status_body_promissory.py` had been re-pointed against the diff's own rule — reverted; the vacuous live assertion in `test_sources_status_body_status_comment.py` is annotated.
- **2026-10-26, after the first push — `docs-site-validate-links` (the docs link gate) read 77 dead links: every relative `[slug.md](slug.md)` link to a moved sibling inside the station Dreams' fold sections (steward 43, marshal 29), the README's four `../../archive/` links (the validator counts any target outside `docs/` as dead) and one in `docs/dreams/archive/`. Fixed: 139 such links name the repository URL `https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/<slug>.md` — in the pasted sections and, identically, in the 158 archived files (62 links), so `fold-complete` still reads every fold verbatim-equal; the README's own precedent for an out-of-`docs/` target is that URL form, written as a CommonMark angle-bracket destination `](<https://…/slug.md>)` because the vendored validator (kept byte-identical to upstream, herald 41.1) reads a bare URL ending in `.md` as a relative path.
- clean passes the reviewer measured: 158/158 moved files with byte-identical frontmatter, 148 differing by the one banner only; all 113 folds verbatim, every heading demoted by exactly one level, none inside a code fence; 605 wikilinks to moved slugs in live Dreams, 0 dead; chain artifacts consistent (headings, keys, Status lines, spec paths); fold-complete, dreams-hygiene, chain-sprawl, chain-completeness, story-status, governance-currency and dream-chain exit 0.

## Auto Run Result

Status: done

Summary: doctor's 14 archived satellite Dreams moved to `archive/docs/dreams/`, 14 of them folded verbatim into `docs/dreams/pyforge-doctor.md` first; `fold-complete` reads 14 complete folds and 0 archived Dreams in the live tree for this station.
