---
title: '`deck-facts --refresh` rewrites stale marked literals from the ledger'
type: 'feature'
created: '2026-09-13'
status: 'done'
baseline_revision: 70f9fcbaad5ab3a58e9a9dace978c5f160538b5f
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/facts-ledger.md']
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-5 detects staleness but nothing repairs it: the moment Wave A round 1 merged, the four rebuilt posters read `mismatch` on the fleet and station counts their own landings moved (`848/878` → `852/878`, herald `69/81` → `73/81`; marshal also prints `tests_collected`, a row only `--with-tests` derives). Hand-editing dozens of marks per poster after every landing defeats the Dream (herald Story 20.14; `spec-deck-family-currency` CAP-6).

**Approach:** Add `--refresh` to `scripts/deck_facts.py`: re-derive the ledger (honouring `--with-tests`), read the poster, and rewrite the text of every `data-fact="<id>"` element whose text is neither the row's `value` nor a `shown_as` literal — choosing the replacement by the OLD literal's shape — then write `facts.yaml` and the poster. Print one line per rewrite or skip and a summary; exit 0 always (usage errors exit 2, as today).

## Boundaries & Constraints

**Always:**
- Replacement choice: if the old text (after the same normalisation `--check` uses: whitespace collapse, `/` spacing, a leading `v` before a digit stripped and remembered) equals the PREVIOUS ledger's `value` → new `value`; if it equals the previous `shown_as[k]` → new `shown_as[k]` when that index exists, else new `value`; a stripped leading `v` is restored. The previous ledger is the on-disk `facts.yaml` read before the re-derive.
- Only the text between the mark's start tag and its matching end tag is replaced, and only when that span contains no other tag; marks whose span contains tags (nested or formatted marks) are printed as `skipped  <id>  nested mark` and left alone; marks whose `id` has no row in the fresh ledger are printed as `skipped  <id>  no row` and left alone; marks whose text already resolves are not touched or printed.
- The poster is rewritten by splicing the original bytes: everything outside the rewritten spans is byte-identical (verified by the tests on a fixture with mixed content). Line endings and encoding are preserved.
- Output lines: `refreshed  <id>  "<old>" -> "<new>"`, `skipped  <id>  <reason>`, then `summary   <slug>: N refreshed, M skipped`. `--refresh` implies the derive (the ledger is written first) and may be combined with `--with-tests`; `--refresh --check` runs the check after the refresh.
- Tests in `tests/scripts/test_deck_facts.py` cover: value → value, `shown_as[k]` shape preserved (`N of M`), leading `v` restored, nested mark skipped, no-row skipped, byte-identical outside spans, idempotence (a second `--refresh` rewrites nothing), and `--check` clean afterwards.
- `docs/specs/presentation-deck.md`'s poster sub-step gains one clause naming `--refresh`.

**Never:**
- Never touch prose, unmarked tokens, attributes, SVG geometry, or any file other than the poster and its `facts.yaml`; never re-render or push.
- Never invent a literal: a mark with no row is skipped, never guessed. Never change exit-code semantics (0 always; usage errors 2).
- Never edit `facts-ledger.md`, `infographic-standard.md`, `pixi.toml`, or other decks.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Stale value mark | ledger moved `848/878` → `852/878`; poster mark `848/878` | rewritten to `852/878`; `refreshed` line; `--check` 0 mismatch | — |
| Shape preserved | poster mark `848 of 878` (old `shown_as[1]`) | rewritten to `852 of 878` | — |
| Leading v | poster mark `v0.11.1`, ledger `0.11.2` | rewritten to `v0.11.2` | — |
| Nested mark | `<b data-fact="cli_verbs"><i>52</i></b>` | `skipped  cli_verbs  nested mark`; bytes untouched | — |
| No row | mark id `tests_collected` on a plain run | `skipped  tests_collected  no row`; untouched | — |
| Idempotent | second `--refresh` | `0 refreshed`; poster bytes identical | — |
| Unknown slug | `deck-facts nope --refresh` | usage error | exit 2 |

</intent-contract>

## Code Map

- `scripts/deck_facts.py` — `_PosterText` (HTMLParser: marks + segments, `_norm`, `_LEADING_V`), `check()`, `main()` argparse; `render_yaml`/`derive` unchanged. Add `refresh(root, slug, previous, fresh, poster_text) -> (new_text, lines)` using a regex over the raw text for `<tag … data-fact="id" …>TEXT</tag>` where TEXT has no `<`; reuse `_norm` and the leading-`v` rule for matching.
- `tests/scripts/test_deck_facts.py` — fixture `root` (synthetic repo, `POSTER`), `_rows`; extend with a refresh fixture that moves a ledger value between runs (edit the synthetic `sprint-status-ledger.yaml`/manifest) and asserts bytes outside spans.
- `docs/specs/presentation-deck.md:79` — the poster sub-step line naming `deck-facts <slug> [--check]`.
- `presentations/pyforge-marshal/project/PyForge Marshal Infographic standalone.html` — a live poster with 128 marks incl. `N of M` shapes and `tests_collected`; run `--refresh --with-tests` against it as a manual check (do not commit poster changes in this story — the operator's currency sweep does).

## Tasks & Acceptance

**Execution:**
- `scripts/deck_facts.py` -- add `refresh()` + the `--refresh` flag and output lines -- CAP-6.
- `tests/scripts/test_deck_facts.py` -- the seven matrix rows + byte-identity + idempotence.
- `docs/specs/presentation-deck.md` -- one clause naming `--refresh` in the poster sub-step.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/.memlog.md` -- append an event naming `scripts/deck_facts.py` and `docs/specs/presentation-deck.md` so `spec-surface-check` reconciles.

**Acceptance Criteria:**
- Given the live marshal poster and a ledger moved by the round-1 landings, when `deck-facts pyforge-marshal --refresh --with-tests --check` runs, then every previously mismatched mark is `refreshed`, the check reports 0 `mismatch`, and a `git diff --stat` of the poster shows only the rewritten literals.
- Given a poster with no stale mark, when `--refresh` runs, then the poster's bytes are unchanged.

## Spec Change Log

## Review Triage Log

### 2026-09-13 — Review pass
- verdicts: 31 findings — high 0, medium 17, low 14, false 0, maybe-false 0 (22 patched, 9 rejected)
- findings:
  - `[low]` `[reject]` BH1 `pixi.toml` task description omits `--refresh` — the intent-contract's Never list excludes `pixi.toml` from this story; the description is corrected in the wave reconcile PR (operator), not here
  - `[low]` `[reject]` BH2 `facts-ledger.md` lacks the refresh vocabulary — the Never list excludes the companion; the parent Spec's maintainer records the refresh vocabulary and the shape rule via memlog + companion re-derive in the reconcile
  - `[low]` `[patch]` BH3 "Where to edit WHAT" row still describes only the hand path — row now names `--refresh` for an already-marked literal and hand-marking for a new one
  - `[medium]` `[patch]` BH4 `_replacement` maps by `shown_as` index before shape, so a reordered `shown_as` returns another shape — index result is checked against the old text's digit pattern and falls back to the same-shape literal; reorder case tested
  - `[medium]` `[patch]` BH5 `--refresh` (regex) rewrites marks inside comments/`<script>`/`<style>`/`<title>` and inner marks nested in a skipped outer mark that `--check` never sees — those spans are skipped with a reason; tested
  - `[low]` `[patch]` BH6 `nested mark` reason also printed for unclosed marks and void elements — `not a plain span`
  - `[medium]` `[patch]` BH7 entity-encoded edge whitespace (`&nbsp;`) dropped, bytes changed beyond the literal — marks whose raw text carries entities are skipped with reason `entities`; tested
  - `[medium]` `[patch]` BH8 non-UTF-8 poster raises `UnicodeDecodeError` (exit 1) — decode failure prints `skipped poster: not UTF-8` + summary, exit 0; tested
  - `[low]` `[reject]` BH9 memlog says "landed" while the ledger row reads `backlog` — the row flips at finalize in this same PR (operator process); memlog wording stands as the implementer's landing note
  - `[low]` `[patch]` BH10 module docstrings not extended for CAP-6 — both docstrings name `--refresh` / CAP-6 / Story 20.14
  - `[low]` `[reject]` BH11 Dream Realization log has no CAP-6 entry — outside the story surface; the operator appends the dated entry in the reconcile (Dream-first convention honoured there)
  - `[low]` `[patch]` BH12 test gaps (ledger-less refresh, single-quoted attribute, uppercase tag, reorder, multi-poster audit line) — tests added; `poster: <path>` line printed
  - `[medium]` `[patch]` EC1 a `>` inside a quoted attribute on a mark truncates the splice and corrupts markup — attribute-aware start-tag pattern; unparsable tags skipped as `unparsed tag`; tested
  - `[medium]` `[patch]` EC2 unquoted / spaced `data-fact` forms accepted by `--check` are never visited by `--refresh` — both forms accepted; parser-vs-regex cross-check prints `unvisited <id>`; tested
  - `[medium]` `[patch]` EC3 marks inside `<script>`/`<style>`/`<title>`/comments silently edited — same root cause as BH5
  - `[medium]` `[patch]` EC4 entities folded before comparing (`4&nbsp;of&nbsp;6` → `5 of 6`) — same root cause as BH7
  - `[medium]` `[patch]` EC5 previous-vs-fresh `shown_as` layout drift collapses `2 of 4` to `3/4` — same root cause as BH4
  - `[medium]` `[patch]` EC6 unparsable `facts.yaml` now crashes the plain regenerate command — previous ledger parsed only under `--check`/`--refresh`; `yaml.YAMLError` → "no previous ledger" with a note; tested
  - `[medium]` `[patch]` EC7 non-UTF-8 poster traceback after the ledger was already rewritten — same root cause as BH8, plus the read-before-write reorder (EC9)
  - `[low]` `[patch]` EC8 in-place `write_bytes` can leave a truncated tracked poster — temp file + `os.replace`
  - `[medium]` `[patch]` EC9 (claim) ledger written before the poster is read, so a poster failure leaves the ledger advanced — poster read and decoded first, then ledger and poster written
  - `[medium]` `[patch]` EC10 (claim) three uncaught raises break the 0/2 exit domain — covered by the EC6/BH8 handlers
  - `[medium]` `[patch]` EC11 (claim) regex-only discovery lets `0 skipped` hide stale marks — covered by EC2's `unvisited` cross-check
  - `[low]` `[reject]` IA(a) the shape heuristic is additive to the intent-contract's index rule — verified real and compatible with "never invent a literal" (only fresh-row literals are chosen); the rule is recorded in `facts-ledger.md` by the spec maintainer; fix would edit this build's spec
  - `[low]` `[reject]` IA(b) tests' primary surface is the stale-on-disk-ledger world — the already-re-derived world is covered end-to-end once plus at unit level, and VG1 adds the ledger-less path
  - `[medium]` `[patch]` IA(c) "mark" defined by two readers (HTMLParser vs raw regex) — same root cause as BH5/EC2; skip regions + `unvisited` cross-check align them
  - `[low]` `[reject]` IA(d) live surface verified only by the coordinator's manual run — repo convention for `tests/scripts` (synthetic root); the live marshal run is recorded in the memlog
  - `[low]` `[reject]` IA(e) `--check`-before-ledger narrowed to `--check` without `--refresh`; pixi description omission — the first is the intended composition, the second is BH1
  - `[medium]` `[patch]` VG1 ledger-less `--refresh` (poster present, no `facts.yaml`) unexercised at `main()` level — end-to-end test added (the `previous or {}` guard)
  - `[medium]` `[patch]` VG2 (other) corrupt `facts.yaml` crashes plain derive — same root cause as EC6
  - `[low]` `[reject]` VG3 (other) `pixi.toml` description stale — same as BH1

## Verification

**Commands:**
- `pixi run -e local-recipes python -m pytest tests/scripts/test_deck_facts.py -q` -- expected: all pass (≥ 33).
- `pixi run -e local-recipes deck-facts pyforge-marshal --refresh --with-tests --check; echo rc=$?` -- expected: `refreshed` lines for the fleet/herald counts, `0 mismatch`, `rc=0`; then `git checkout -- presentations/pyforge-marshal/` to leave the poster to the operator's sweep.
- `pixi run -e local-recipes deck-facts pyforge-marshal --refresh --with-tests` twice -- expected: second run `0 refreshed`.
- `pixi run -e local-recipes spec-surface-check` -- expected: ok.

## Auto Run Result

**Summary:** `deck-facts <slug> --refresh` (CAP-6) re-derives the ledger, then rewrites the text of
every stale `data-fact` mark from the fresh row, keeping the old literal's shape. Mark spans are
located by a second `HTMLParser` (`_MarkSpans` + `_mark_spans`) that mirrors `_PosterText`'s tag
bookkeeping and records raw offsets, so `--refresh` and `--check` agree on what a mark is; a loose
regex survives only as a net for `unparsed tag`. Advisory: exit 0 always.

**Files changed:**
- `scripts/deck_facts.py` — `--refresh`, `_MarkSpans`/`_mark_spans`, `_shape`/`_replacement`,
  `refresh()`; previous-ledger parse moved under `--check`/`--refresh`; poster read before the
  ledger write; atomic poster write; `poster:` / `unvisited` / five skip reasons.
- `tests/scripts/test_deck_facts.py` — 45 tests (from 33): twelve new, none replaced.
- `docs/specs/presentation-deck.md` — the "Where to edit WHAT" row splits marked vs new literals.
- `spec-deck-family-currency/.memlog.md` — the landing event; also collapsed a **double `updated:`
  key** in its frontmatter that PyYAML was silently resolving to the *earlier* timestamp, so the
  memlog read as older than it was.

**Review findings breakdown:** 31 findings from four layers — 22 patched (medium 17, low 5),
0 deferred, 9 rejected: BH1/VG3 the `pixi.toml` description (excluded by the intent-contract's Never
list; corrected in the wave reconcile, PR #1312) · BH2 the companion's refresh vocabulary (same
exclusion; landed in #1312) · BH9 the memlog "landed" wording (the ledger row flips at finalize) ·
BH11 the Dream Realization entry (outside the story surface; landed in #1312) · IA(a) the shape
heuristic being additive to the index rule (verified compatible with "never invent a literal" — it
only ever returns a fresh-row literal; now recorded in `facts-ledger.md`) · IA(b) the tests' primary
world (both worlds are covered; VG1 added the ledger-less path) · IA(d) the live surface being
verified by run rather than by suite (repo convention for `tests/scripts`) · IA(e) `--check` before a
ledger narrowed to `--check` without `--refresh` (the intended composition).

**Follow-up review recommended:** false — no `high` was patched and the medium patches converged in
one round.

**Verification:** 45 tests pass. Live on the marshal poster: `--refresh --with-tests --check` printed
the `poster:` line, refreshed 11 stale literals (fleet `848/878` → `857/884`, herald `69/81` →
`73/82`, scribe `20/20` → `25/25` — counts the other session moved while this story was in review),
0 skipped, then reported `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 0 unshown; facts 128/128`.
A second run: `0 refreshed, 0 skipped`. `presentations/` restored; no `.tmp` survived. `spec-surface`
output byte-identical with these four files reverted — no new gating finding.

**Residual risks:** two-part versions (`0.9`) remain outside the swept shapes, so a stale one is
caught only by `unshown` or a mark; `--with-tests` needs the station's own pixi env, so a refresh
that keeps a `tests_collected` row must pass that flag or the row reports `no row`.
