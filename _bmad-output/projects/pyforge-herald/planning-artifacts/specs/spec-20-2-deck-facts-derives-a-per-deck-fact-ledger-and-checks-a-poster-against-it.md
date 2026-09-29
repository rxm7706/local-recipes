---
title: '`deck-facts` derives a per-deck fact ledger and checks a poster against it'
type: 'feature'
created: '2026-09-13'
status: 'done'
baseline_revision: ac3761abc550fdf25374618235a07793e6a719b3
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/facts-ledger.md']
warnings: ['oversized']
deferred:
  - summary: >-
      Real `pytest --collect-only -q` output is never parsed under test; only the plumbing around the stubbed `tests_collected` seam is verified.
    evidence: |-
      The suite stubs `tests_collected` wholesale, so the regex `(\d+)(?:/\d+)? tests? collected` and the reversed-line scan run only against synthetic strings. The row is opt-in (`--with-tests`) and present in none of the ten committed ledgers. Settle with a stubbed-`subprocess.run` test over captured real tails (plural, singular `1 test collected`, rc≠0 "N errors") when the first `--with-tests` ledger is committed (Wave A).
    location: >-
      scripts/deck_facts.py:tests_collected
    severity: medium (unverified)
declared_low_risk: false
---
<intent-contract>

## Intent

**Problem:** No infographic poster cites a source for any number it shows and nothing detects poster staleness — the Marshal poster still prints `bmad-method 6.10.0`, `bmad-loop 0.9.0`, `128/333`, `4/27` against a live 6.12.0 / 0.11.1 / 846/865 / 67/68 (herald Story 20.2; `spec-deck-family-currency` CAP-2, CAP-5).

**Approach:** One repo script, `scripts/deck_facts.py`, behind pixi task `deck-facts <slug> [--check] [--with-tests]` (the `scripts/deck_export.py` precedent). It derives `presentations/<slug>/facts.yaml` from tracked live sources only, deterministically; `--check` reads the deck's `project/<Persona> Infographic standalone.html` and reports fact tokens with no row, rows whose fresh derivation differs, and rows no longer shown — advisory, exit 0.

## Boundaries & Constraints

**Always:**
- Ledgers via `scripts/fleet_scan.py::parse_sprint_status` (`sys.path` insert); stories = `development_status` keys not starting `epic-`; epics = `epic-N` keys without `-retrospective`; `done` is the literal.
- Deterministic: facts sorted by `id`; `tree` = HEAD sha; `derived_at` = HEAD commit date (`git log -1 --format=%cI`); a re-run on an unchanged tree writes identical bytes.
- Row = `id`, `value` (string as shown), `source` (tracked path or pixi task), `method`, `shown_as` (literals the poster may print; default `[value]`). Unsourceable facts are omitted and named on stderr, never guessed.
- Sources per `facts-ledger.md`: `pyforge-<station>` → own ledger, `spec-pyforge-<station>/SPEC.md` (status, distinct `CAP-N`), `docs/dreams/pyforge-<station>.md` status, `pyproject.toml` version + console entry, argparse `add_parser("…")` verbs from the station package (omit row when none); `pyforge-genesis` → guild roster station count, Dream counts by status; `pyforge-unifying-strategy` → steward ledger + `spec-pyforge-unifying-strategy/SPEC.md`. Every deck: fleet totals over all eight ledgers, BMAD core version (`_bmad/_config/manifest.yaml` `installation.version`), installed `bmad-loop` (`pixi.lock`), CFE skill version (`SKILL.md` frontmatter), `bmad-groundtruth` keys, `recipes/` count.
- `--check`: visible text via `html.parser` skipping `<style>`/`<script>`; `data-fact="<id>"` elements must equal `value` or a `shown_as` literal, else `mismatch`; visible `n/n`, `x.y.z`, `YYYY-MM-DD` tokens matching no row → `unmarked`; rows whose fresh derivation differs → `drifted`; rows neither marked nor shown → `unshown`. One line per finding plus a summary; exit 0.
- Test counts only under `--with-tests` (`pixi run -e pyforge-<station> pytest --collect-only -q`); the default run is offline, seconds.
- `pixi.toml` gains only `[feature.local-recipes.tasks.deck-facts]` (`cmd = "python scripts/deck_facts.py"`); `environment.yaml` re-exported, byte-identical.
- `docs/specs/presentation-deck.md`'s poster sub-step names the task in one line; the ten `facts.yaml` files come from running the task.

**Never:**
- No `DETECTOR` marker; never in `detectors`/`detectors-ci`; non-zero exit only for usage errors.
- Never read `implementation-artifacts/`, another poster, or memory as a source; never regex the ledger.
- Never edit a poster, a deck README, `deck_export.py`, or `.claude/skills/conda-forge-expert/**`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Derive twice, unchanged tree | `deck-facts pyforge-marshal` ×2 | second run leaves `git diff` empty | — |
| Check today's marshal poster | `--check` | `unmarked` lines for `6.10.0` `0.9.0` `128/333` `4/27`; summary; exit 0 | — |
| Planted stale mark | fixture with `data-fact="bmad_core_version">6.10.0` | one `mismatch` line naming the row; exit 0 | — |
| Unknown slug | `deck-facts nope` | usage error naming `presentations/nope` | exit 2 |
| Deck without a poster | `--check` on a slug with no `* Infographic standalone.html` | "no poster" line; exit 0 | — |
| `--with-tests` | `deck-facts pyforge-warden --with-tests` | adds `tests_collected` row | pytest failure → row omitted, named on stderr |

</intent-contract>

## Code Map

- `scripts/deck_export.py` -- shape to mirror (argparse, `ROOT` from `__file__`, `sys.exit` on usage errors, one pixi task).
- `scripts/fleet_scan.py:301` `parse_sprint_status`; `PROJECT_SOURCES` keys = the eight bare station names (import 0.01 s).
- `_bmad-output/projects/pyforge-<s>/planning-artifacts/sprint-status-ledger.yaml` -- tracked twin with `development_status:` (herald today 68/81 stories, 18/20 epics).
- `_bmad/_config/manifest.yaml` (`installation.version: 6.12.0`); `pixi.lock` (`bmad-loop-0.11.1`); `.claude/skills/conda-forge-expert/SKILL.md` (`version: 8.90.5`); `pixi run -e local-recipes bmad-groundtruth` → JSON `{atlas_phases, gotcha_max, mcp_tools, pixi_envs, schema_version, skill_version}`.
- `src/shared/packages/pyforge-<s>/pyproject.toml` (`version`, `[project.scripts]`); argparse verbs in `pyforge/<s>/cli.py` (herald, mason, steward, warden), `__main__.py` (doctor), `cli/*.py` (marshal); atlas, scribe expose none.
- `docs/governance/guild-roster.json` `stations` (8 strings); `docs/dreams/*.md` `status:` (144 files); `recipes/*/` (7,874).
- `pixi.toml:1130` `deck-export` task (add `deck-facts` after it); `docs/specs/presentation-deck.md:74-78` poster sub-step; `tests/scripts/` -- repo-script pytest home (`pixi.toml:770` runs it).
- `presentations/<slug>/project/* Infographic standalone.html` -- persona = filename prefix; ten Wave A/B slugs per `spec-deck-family-currency/deck-inventory.md`.

## Tasks & Acceptance

**Execution:**
- `scripts/deck_facts.py` -- new: derive, `--check`, `--with-tests`.
- `tests/scripts/test_deck_facts.py` -- new: determinism, fixture-ledger counts, planted `mismatch`, `unmarked` sweep, exit codes.
- `pixi.toml` -- `deck-facts` task after `deck-export`; `environment.yaml` -- re-export, expect no diff.
- `docs/specs/presentation-deck.md` -- one line naming `deck-facts <slug> [--check]`.
- `presentations/pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden,genesis,unifying-strategy}/facts.yaml` -- first derivations by running the task.
- `spec-deck-family-currency/.memlog.md` -- append an event naming `scripts/deck_facts.py`, `pixi.toml`, the ten `facts.yaml` so `spec-surface-check` reconciles.

**Acceptance Criteria:**
- Given the ten decks, when `deck-facts <slug>` runs for each, then ten `facts.yaml` exist, every row has the five fields, and a second run changes no bytes.
- Given `detectors -- --list`, when it runs, then `deck_facts` is absent.

## Spec Change Log

## Review Triage Log

### 2026-09-13 — Review pass
- verdicts: 45 findings — high 1, medium 20, low 22, false 1, maybe-false 1
- findings:
  - `[low]` `[reject]` IA: tests run in-process on a synthetic root while the matrix is phrased at the live pixi-task surface — live surface verified by the operator's own runs (derive ×2 unchanged, --check rc=0, env export identical); synthetic-root tests are the repo's `tests/scripts` convention and a live-surface suite would be slow and nondeterministic
  - `[low]` `[reject]` IA: `tests/scripts` runs under `pyforge-ci`, where PyYAML is only transitive — pre-existing pattern (two existing tests import yaml there); 9/9 pass in both envs; adding the dep is a pixi-deps change outside this story
  - `[low]` `[reject]` IA: the Problem paragraph's `846/865 · 67/68` are `fleet-picture` figures the tool cannot reproduce — fix would edit this build's intent-contract; the memlog now records the definitional difference (tracked twins vs Tier-3 report; literal epic key vs inferred)
  - `[medium]` `[patch]` IA: other stations' counts and cited dates can never resolve under the shipped derivation — per-station rows on every deck and generic date rows (poster last-commit, tree commit date, Dream Realization-log entries) added per the companion's catalog
  - `[low]` `[reject]` IA: after merge HEAD differs, so the first re-run rewrites all ten headers with 0 drifted — property of the chosen determinism rule (documented in facts-ledger.md), not a defect
  - `[false]` `[reject]` IA: beyond-contract items (foreign baseline stamps, genesis omitted notes, the test file) — none is a bad outcome; stamps follow the repo precedent `228e589a03`, omissions are the contract's own rule
  - `[medium]` `[patch]` EC1 `_shown` rejects `v0.11.1` while `_TOKEN` accepts it → contradictory unshown — one boundary rule with optional `v` in both
  - `[medium]` `[patch]` EC2 mark text `v0.11.1` mismatches literal `0.11.1` — leading `v` before a digit stripped before comparing (same root cause as EC1)
  - `[medium]` `[patch]` EC3 `<b>847</b>/878` never tokenizes (text nodes joined with a space) — block boundaries separate; an inline boundary joins without a separator only when both neighbours are token characters (a blanket join fused sibling chips like `Proclaimer4/27`); whitespace around `/` normalized in marks and sweep text
  - `[low]` `[reject]` EC4 integer literals matched standalone elsewhere ("Act 8") count as shown — bare integers rely on `data-fact` marks by the intent-contract's sweep definition; requiring marks for integers adds a branch for a rare miss
  - `[low]` `[reject]` EC5 nested `data-fact` elements: inner never checked — authors do not nest marks; reporting nesting adds a branch for a state not shown reachable
  - `[low]` `[patch]` EC6 `<title>` text swept as visible — `title` added to the skip set (direct correction)
  - `[medium]` `[patch]` EC7 rows not derived this run (plain run vs `--with-tests`, groundtruth failure) reported as `drifted … fresh absent` — reported as `unsourced` with the omit reason; summary gains the count
  - `[low]` `[patch]` EC8 null groundtruth value written as `"None"` — null keys omitted with a note
  - `[medium]` `[patch]` EC9 dirty working tree attributed to HEAD sha — `tree` gets a `-dirty` suffix when tracked files are uncommitted
  - `[low]` `[reject]` EC10 traceback outside a git checkout / missing roster — the pixi task runs inside this repo; a loud failure on an unreachable state is correct
  - `[low]` `[patch]` EC11 two-component manifest version parsed as float — `yaml.BaseLoader`
  - `[low]` `[patch]` EC12 multiple poster matches resolved silently — stderr note names all matches and the one used
  - `[low]` `[reject]` EC13 unclosed frontmatter returns a body `status:` — no such file exists in the tree; guard adds a branch for a malformed input never shown reachable
  - `[low]` `[patch]` EC14 `45/50 tests collected` misread — regex accepts `/M`, returns N
  - `[low]` `[patch]` EC15 "not a station" `--with-tests` branch unexercised (beta is in the roster) — test now uses a deck outside the roster
  - `[low]` `[reject]` EC16 (claim) ledgers do not print the intent's `846/865 · 67/68` — same as IA row 3; fix is a spec edit
  - `[low]` `[reject]` EC17 (claim) plain integers never reported unmarked — the intent-contract's sweep set; `unshown` covers unmarked integer rows
  - `[high]` `[patch]` BH1 `spec_capabilities` counts prose mentions (herald 3, doctor 10 vs 8, scribe 6 vs 4) — definition lines only (bold `- **CAP-N`/`- **HER-N` bullets and `### HER-a..HER-b` heading ranges), never prose or frontmatter; live herald 13, scribe 4, doctor 9 (its ninth is a bold titled `- **CAP-N — …**` bullet of the same shape as unifying-strategy's 19), unifying-strategy 19
  - `[medium]` `[patch]` BH2 `_TOKEN`/`_shown` leading-`v` disagreement — same root cause as EC1
  - `[medium]` `[patch]` BH3 HEAD sha on working-tree values, no dirty marker — same root cause as EC9; `derived_at` documented as the HEAD commit date in facts-ledger.md
  - `[medium]` `[patch]` BH4 own spec's spec-surface baseline left unstamped, masking future drift — scoped `--write-baseline --spec pyforge-herald/spec-deck-family-currency` at finalize after `git add`
  - `[medium]` `[patch]` BH5 dates swept but never derivable — same root cause as IA row 4; generic date rows derived
  - `[medium]` `[reject]` BH6 sweep misses two-part versions (`0.9`), status words, bare integers — the intent-contract fixes the swept shapes (`n/n`, `x.y.z`, `YYYY-MM-DD`); marks + `unshown` cover the rest; two-part versions recorded as a residual risk, fix is a spec edit
  - `[low]` `[patch]` BH7 `recipes_count` includes `recipes/example` and `recipes/examples` — excluded, method text says so
  - `[medium]` `[patch]` BH8 facts-ledger.md and SPEC.md CAP-2 drifted from the implementation (shape, fleet-picture as source, pixi.toml pins, cli.py-only verbs, row-level derived_at) — reconciled through the parent Spec's memlog (three decisions) and the derived files
  - `[medium]` `[patch]` BH9 untested branches (proxy, genesis, sub-package scan, `__main__` entry, spec_hits≠1, zero facts, `v` prefix, quoted frontmatter; `is` identity assert) — tests added; `frontmatter_scalar` strips quotes; `==`
  - `[medium]` `[patch]` BH10 ledger row still `backlog` and parent SPEC `ready` — SPEC `in-progress` (memlog event); Tier-3 row flipped and promoted at finalize
  - `[low]` `[patch]` BH11 `presentation-deck.md` edit-surface table lacks a `facts.yaml` row — row added
  - `[medium]` `[patch]` BH12 whitespace-brittle marks/tokens — same root cause as EC3
  - `[low]` `[patch]` BH13 "eight" hard-coded in the task description; unquoted `tree:` — description derives from the roster; `tree` quoted (the `head_info` raise is EC10, rejected)
  - `[medium]` `[patch]` VG1 groundtruth argv never checked against the `bmad-groundtruth` task; `None` branches untested — argv-equality test against `pixi.toml` and three stubbed-failure tests
  - `[medium]` `[patch]` VG2 one-sided `--check` branches unexecuted — unknown-id mismatch and `unsourced`/`ledger absent` cases tested
  - `[medium]` `[patch]` VG3 sub-package `cli_verbs` scan has no fixture — gamma station fixture, `cli_verbs == "2"`, source ends `/cli`
  - `[medium]` `[patch]` VG4 `LEDGER_PROXY` untested — proxy test with prefixed rows and no package rows
  - `[medium]` `[patch]` VG5 ambiguous bmad-loop lock untested — two-version fixture lock, row omitted, stderr names both
  - `[maybe-false]` `[defer]` VG6 real `pytest --collect-only` output never parsed under test — opt-in row present in no committed ledger; would be `medium` if the regex misses real output; settle by a stubbed-subprocess test when the first `--with-tests` ledger lands (Wave A)
  - `[low]` `[patch]` VG7 epics-done rule differs from `fleet-picture` (literal key vs inferred) and the memlog misattributed the delta — memlog decision records both rules and the by-design divergence
  - `[low]` `[patch]` VG8 `test_deck_facts_is_not_a_detector` second assertion vacuous — comment states what the AST assertion proves
  - `[low]` `[patch]` VG9 groundtruth `source` names the pixi task while the code runs `python -m` directly — guarded by VG1's argv-equality test

## Verification

**Commands:**
- `pixi run -e local-recipes deck-facts pyforge-marshal && pixi run -e local-recipes deck-facts pyforge-marshal && git status --short presentations/pyforge-marshal/` -- expected: `facts.yaml` listed once, unchanged by the second run.
- `pixi run -e local-recipes deck-facts pyforge-marshal --check; echo rc=$?` -- expected: `unmarked` lines for `6.10.0` `0.9.0` `128/333` `4/27`; `rc=0`.
- `pixi run -e local-recipes python -m pytest tests/scripts/test_deck_facts.py -q` -- expected: pass.
- `pixi project export conda-environment -e build | diff - environment.yaml` -- expected: empty.
- `pixi run -e local-recipes detectors -- --list | grep -c deck_facts` -- expected: `0`.
- `pixi run -e local-recipes spec-surface-check` -- expected: `ok`.

## Auto Run Result

**Summary:** `scripts/deck_facts.py` behind the pixi task `deck-facts <slug> [--check] [--with-tests]` derives `presentations/<slug>/facts.yaml` from tracked sources only (36–47 rows per deck: fleet + per-station ledger pairs via `parse_sprint_status`, BMAD core and bmad-loop versions, CFE skill version, `bmad-groundtruth` keys, recipe count, spec status + capability-definition count, Dream status, package version, console entry, CLI verbs, tree/poster/Dream-log dates) deterministically (sorted rows; `tree` = HEAD sha, `-dirty` when uncommitted; `derived_at` = HEAD commit date), and `--check` reads the poster's visible text and reports `unmarked` / `mismatch` / `drifted` / `unsourced` / `unshown`, advisory exit 0. Ten ledgers derived; 24 tests; one doc line plus a `facts.yaml` edit-surface row.

**Files changed:**
- `scripts/deck_facts.py` — new: derive, `--check`, `--with-tests` (the `deck_export.py` shape; no DETECTOR marker).
- `tests/scripts/test_deck_facts.py` — new: 24 tests on a synthetic root (determinism, parser counts, proxy, genesis, sub-package CLI scan, ambiguous lock, groundtruth argv + failure branches, check kinds, exit codes, not-a-detector).
- `pixi.toml` — `[feature.local-recipes.tasks.deck-facts]`; `environment.yaml` re-export byte-identical (untouched).
- `docs/specs/presentation-deck.md` — poster sub-step names the task; "Where to edit WHAT" gains the `facts.yaml` row.
- `presentations/pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden,genesis,unifying-strategy}/facts.yaml` — first derivations.
- `spec-deck-family-currency/{SPEC.md,facts-ledger.md,.memlog.md}` — CAP-2 shape text and the source catalog reconciled with the implementation (memlog decisions); status `ready → in-progress`.
- `spec-pyforge-herald/{SPEC.md,.memlog.md}` — `surface-drift-exclude` gains the four deck-family surfaces the narrower Spec owns.
- `scripts/.spec-surface-baseline.json` — scoped stamps (eight `pixi.toml` co-owners per precedent `228e589a03`, `spec-pyforge-herald`, `spec-deck-family-currency`).

**Review findings breakdown:** 45 findings from four layers — 32 patched (high 1, medium 19, low 12), 1 deferred (VG6, `maybe-false`, medium if true), 12 rejected: IA1 synthetic-root tests (repo convention; live surface verified by the coordinator's runs) · IA2 transitive PyYAML in `pyforge-ci` (pre-existing pattern) · IA3 / EC16 the Problem's `846/865 · 67/68` are `fleet-picture` figures (fix is a spec edit) · IA5 headers move after every commit (property of `tree` = HEAD) · IA6 beyond-contract items are not defects · EC4 standalone integers count as shown (intent-contract sweep set; `unshown` covers rows) · EC5 nested marks (state not shown reachable) · EC10 traceback outside a git checkout (unreachable via the pixi task) · EC13 unclosed frontmatter (no such file) · EC17 plain integers not swept (intent-contract) · BH6 two-part versions / status words not swept (intent-contract fixes the shapes; residual risk below).

**Follow-up review recommended:** true — one `high` entry was patched (BH1). Unverified risk: the capability-definition heuristic (bold `- **CAP-N`/`- **HER-N` bullets plus `### HER-a..HER-b` heading ranges) was tuned against the ten decks' own specs; a spec written in another shape could over- or under-count silently. The follow-up should read each `spec_capabilities` value against its SPEC.md by eye before Wave A cites it.

**Verification:** `deck-facts pyforge-marshal` ×2 → `unchanged` (47 facts) · `--check` → `unmarked` for `128/333`, `4/27`, `6.10.0`, `0.9.0`; `0 drifted, 0 unsourced`; `2026-07-23`/`2026-07-31` resolve to `dream_log_*` rows; rc=0 · `pytest tests/scripts/test_deck_facts.py -q` → 24 passed · `pixi project export conda-environment -e build | diff - environment.yaml` → empty · `detectors -- --list | grep -c deck_facts` → 0 · `spec-surface-check` → ok · matrix audit: every I/O row has a passing covering test.

**Residual risks:** two-part versions (`0.9`) are outside the swept shapes — a stale `bmad-loop 0.9` passes unless marked or caught as `unshown`; `tree` headers change on every re-derive after a commit (expected; the kernel spec excludes the ledgers from its own drift tracking, the owning Spec's memlog moves per story); the committed ledgers are re-derived on the clean tree before commit so no `-dirty` header ships; `--with-tests` runs `pytest --collect-only -q src/shared/packages/pyforge-<station>/tests` (the literal repo-root command in the intent-contract collects `build_artifacts/` and exits 3 — the only functional reading; the row's `source` records the exact command).
