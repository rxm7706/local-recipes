---
title: "28.1: The rebuild guard reads a SHA field whatever type YAML gives it"
type: 'fix'
created: '2026-10-09'
status: 'done'
baseline_revision: 'f7ce163b6991281695ea93a121b5c96fad299cf9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - scripts/cfe_rebuild_guard_check.py
  - tests/scripts/test_cfe_rebuild_guard_check.py
  - src/shared/packages/pyforge-mason/tests/unit/test_cfe_rebuild_guard_merges.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-27-1-mason-s-package-and-the-repo-tooling-it-owns-close-their-open-deferrals.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-09 the `scripts-suite` job of PR #2031 (Detectors run 37990293221) failed
`tests/scripts/test_cfe_rebuild_guard_check.py::test_brief_must_name_every_retro_at_or_older_than_the_pointer`. The
guard reported a `brief-defect` for a brief that does name its retro: `has no retro-mirror amendment naming
4139357790`. The cause is in `scripts/cfe_rebuild_guard_check.py`:

- `_amendment_sha_tokens` (`:279-290`) keeps a field value only when it is a `str` (`:286`), and a list item only when
  it is a `str` (`:289`).
- The guard loads the brief with PyYAML's `safe_load` (`:369`). PyYAML resolves an unquoted all-digit token such as
  `commit: 4139357790` to an `int`, so that SHA field is dropped and the retro it names counts as unmirrored.

The test makes two real commits and writes the older retro's 10-character prefix unquoted
(`_write_brief`, test file `:95`; the test at `:761-777`). It fails whenever that prefix is all digits and loads as an
int. All-digit prefixes come up in (10/16)^10 of runs, about 0.9%. A brief written by hand hits the same false
finding.

**Audit of every SHA the guard reads from YAML** (checked 2026-10-09 against PyYAML 6.0.3):

- The guard reads SHAs from YAML in two places only:
  - a `retro-mirror` amendment's fields and list items, in the brief (clause (b'));
  - a slice's `brief_mirrored_through`, in `campaign-state.yaml` (`campaign_state`, `:204-220`), which clauses (b)
    and (b') both read.
- `DEFAULT_SINCE` and `--since` are not YAML. `id`, `order`, `status`, `equivalence`, `brief_path`, `callers` and
  `re_scope_gate` are not SHAs.
- **`brief_mirrored_through` as an int is wrong in both clauses.** Clause (b') skips the slice (`:397-399` requires a
  `str`), so the brief's mirror check never runs. Clause (b) compares with `==` (`:500`), so an int pointer that names
  the newest retro is still reported `unmirrored-retro`.
- **Clause (b)'s remedy contradicts its check.** The check requires `brief_mirrored_through` to equal the newest
  retro's full 40-character SHA (`:500`). The remedy tells the reader to set it to the 10-character prefix
  (`:511-512`), and clause (b') already accepts a prefix pointer (`_required_mirror_shas`, `:308-316`). Following the
  remedy keeps the finding.
- **A prefix pointer outside the scanned range is matched one way only.** When `brief_mirrored_through` is not a
  qualifying retro in range, the brief owes the pointer itself (`:316`). `_sha_matches(token, pointer)` then requires
  the amendment token to be a prefix of the pointer, so a brief that names the pointer's full SHA does not cover a
  10-character pointer.

**The brief's leading-zero premise is half right.** PyYAML keeps `0123456789` a string: it is not a valid decimal int
(leading zero), and `8` and `9` are not octal digits. But a token with a leading `0` and only the digits 0 to 7
(`0123456701`) resolves as a YAML 1.1 octal int, `21913025`, and `0b` followed by 0s and 1s (`0b10110101`) resolves as
a binary int, `181`. A hex SHA can take both shapes: `b` is a hex digit. The decimal string of those values is not the
SHA, so reading the value's decimal string does not cover them. The scalar's text as written does. For a decimal int
the two are identical: a hex token can carry no sign, underscore or leading zero. No float, bool, null or timestamp
arises from a hex token: those forms need a `.`, a `-`, a `:` or a letter outside `a`-`f`. Probe:
`yaml.safe_load("commit: 0123456701")` returns `{'commit': 21913025}`.

**Approach:** read a SHA from a loaded YAML value in one place, and compare two SHAs with one rule.

- **Read.** A `str` is a SHA candidate as it is today. An `int` that is not a `bool` is a candidate, read as its
  scalar text. Anything else is never a SHA.
- **Compare.** Two candidates name the same commit when, stripped and lower-cased, both are hex tokens of 10 to 40
  characters and one is a prefix of the other.
- Route amendment fields, amendment list items and `brief_mirrored_through` (in both clauses) through the reader. Route
  every SHA comparison through the comparison rule.
- `MIN_SHA_PREFIX` stays 10. A SHA quoted inside free text still never matches.
- Clauses (a), (c) and (d), and their inputs, are unchanged.

One way to keep the scalar text: a `yaml.SafeLoader` subclass whose int constructor returns an `int` subclass that
carries `node.value`, so `order` stays an `int` for clause (d). The implementer may choose another mechanism that meets
the ACs.

Ledger key: `28-1-the-rebuild-guard-reads-a-sha-field-whatever-type-yaml-gives-it`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-16 (← `spec-conda-forge-expert-rebuild` CAP-3): the anti-atlas guard, parallel-run form.
  Divergence and the endgame are enforced by a detector. Clause (b) (Story 6.2) and clause (b') (Story 27.1, under
  CAP-16) are the divergence half this story repairs.
- Not bound: CAP-17 (← rebuild CAP-4, campaign state). Story 12.4's re-scope gate is clause (d), which this story does
  not change, and `campaign-state.yaml`'s schema does not move.
- No new CAP, so no FR moves (decision recorded on the `spec-pyforge-mason` memlog, 2026-10-09).
- `spec-feature-flag-governance` CAP-1, Q1: a `fix` carries no flag.
- AD-1: no Mason code changes. AD-15: no CFE-surface path changes, so there is no `retro(cfe):` commit.

## Acceptance Criteria

The new tests use fixed SHA strings and scan a brief file under `tmp_path`. They make no commits, so their verdict
never depends on a generated SHA.

1. **An int-loaded SHA field reads like a string one.** Given a `retro-mirror` amendment whose field YAML loaded as an
   `int` (a `bool` never counts), When the guard reads its SHA candidates, Then the value is read as its decimal
   string and matched exactly like a string field. That covers the field as a whole value and as a list item:
   - `commit: 4139357790` covers retro `4139357790` followed by 30 more hex characters;
   - `commits: [4139357790]` covers the same retro.
2. **An octal- or binary-shaped SHA reads as written.** Given an unquoted amendment value that PyYAML resolves as an
   octal or binary `int`, When the guard reads it, Then it matches by the scalar's text as written:
   - `commit: 0123456701` covers retro `0123456701…`;
   - `commit: 0b10110101` covers retro `0b10110101…`;
   - `commit: 0123456789`, which PyYAML keeps a string, still covers `0123456789…`.
   This extends AC 1's decimal-string reading, since the brief's premise left these two forms out (Intent, *half
   right*).
3. **Nothing else is ever a SHA.** Given an amendment field of `true`, `false`, `1.5`, `null` or a 9-digit int
   (`413935779`), When the guard reads it, Then it names no retro. A brief with only that field still gets a
   `brief-defect` for its retro. A SHA inside free text, such as `reason: mirrored 4139357790 into …`, still names
   nothing.
4. **`brief_mirrored_through` gets the same reading in both clauses.** Given a `campaign-state.yaml`, loaded through
   `campaign_state()`, with `brief_mirrored_through: 4139357790` unquoted, When `scan` runs:
   - and `4139357790…` is the newest retro, Then clause (b) raises no `unmirrored-retro`;
   - and the brief names no retro, Then clause (b') raises a `brief-defect`, not a skip.
   The octal-shaped pointer `0123456701` behaves the same way. A `bool` or `float` pointer is never a SHA: clause (b')
   skips it, and clause (b) reports it, as they do today.
5. **One comparison rule for every pair.** Given two hex tokens of 10 to 40 characters, Then they name the same
   commit when one is a prefix of the other, case-insensitively. This applies to amendment token and retro, pointer and
   retro, and amendment token and pointer. So:
   - `brief_mirrored_through: "4139357790"`, a string prefix of the newest retro, raises no `unmirrored-retro`;
   - the value clause (b)'s remedy prints clears that finding, and a test asserts the remedy names that value;
   - a 10-character pointer outside the scanned range is covered by an amendment naming its full SHA, and by one
     naming the same prefix.
6. **The existing test holds for any SHA.** `test_brief_must_name_every_retro_at_or_older_than_the_pointer` passes
   unchanged, and `_write_brief` still writes SHAs unquoted. A deterministic test replays its two assertions over fixed
   `(newer, older)` pairs, with no commits:
   - the brief naming only `newer` reds with `older[:10]` in its refs;
   - the brief naming `newer` and `older[:10]` is clean.
   The pairs give `older[:10]` five shapes: decimal-int (`4139357790`), octal (`0123456701`), binary (`0b10110101`),
   leading-zero string (`0123456789`) and plain hex.
7. **Red first.** Each test added for ACs 1, 2, 4, 5 and 6 fails against `origin/main`'s
   `scripts/cfe_rebuild_guard_check.py` and passes with the fix. AC 3's tests may pass on both, since they pin
   behaviour that already holds. The story records the red run.
8. **Docs match behaviour.** The module docstring's clause (b) and (b') text names the reading and comparison rules.
   Clause (b)'s remedy names a value the check accepts.
9. **Nothing else moves.** Every existing test in `tests/scripts/test_cfe_rebuild_guard_check.py` and
   `src/shared/packages/pyforge-mason/tests/unit/test_cfe_rebuild_guard_merges.py` passes unchanged.
   `pixi run -e pyforge-guild cfe-rebuild-guard-check` exits 0 on the live repo.

## Tasks

1. Read the guard's module docstring, `_amendment_sha_tokens`, `_brief_covers_retro_sha`, `_required_mirror_shas`,
   `_brief_defect_findings` and clause (b) in `scan()`. Read Story 27.1's spec for why clause (b') matches only a
   field's whole value.
2. Re-run the probe in the Intent (`yaml.safe_load` over `4139357790`, `0123456701`, `0123456789`, `0b10110101`) in
   the `pyforge-ci` environment, and record the result here if it differs.
3. Write the tests from the Acceptance Criteria first. Run them against `origin/main`'s script and record which fail
   (AC 7).
4. Implement the reader and the comparison rule, and route the three read sites and every comparison through them.
   Update the module docstring and clause (b)'s remedy text.
5. Run every Verification command, and read each verdict from its exit code.
6. Run `pixi run -e pyforge-guild spec-surface-check`. No Spec's surface lists either file today. If the detector
   names a Spec anyway, append its memlog entry first, then `git add`, then run a scoped `--write-baseline --spec`
   for that Spec only (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**

- Read every verdict from the exit code, never through a pipe.
- Keep `MIN_SHA_PREFIX = 10`, `--no-merges`, the whole-value rule for SHA fields, and the exit-code contract
  (0 clean, 1 findings, 2 could not run).
- Keep `order` an `int` for clause (d), and keep `_slice_ref`'s handling of an integer `id`.

**Never:**

- Touch any file other than `scripts/cfe_rebuild_guard_check.py` and `tests/scripts/test_cfe_rebuild_guard_check.py`.
  The story spec's own status and record are the only planning edits.
- Fix the flake by quoting SHAs in the test helpers. That hides the defect a hand-written brief still hits.
- Add a dependency. The guard runs in the lean `pyforge-ci` environment on PyYAML alone, so no `ruamel.yaml`.
- Edit `campaign-state.yaml`, `pixi.toml` or any CFE-surface path (`.claude/skills/conda-forge-expert/**`,
  `.claude/scripts/conda-forge-expert/**`, `.claude/tools/conda_forge_server.py`). The guard is repo tooling for the
  closed CFE-rebuild campaign, not the CFE surface. So AGENTS.md's conda-forge retro rule, a CFE `CHANGELOG.md` semver
  entry, does not apply, and there is no `retro(cfe):` commit. Story 27.1 changed this same script with no CFE path.
  A commit that touched the CFE surface and its `CHANGELOG.md` together would also count as a retro for clause (b).
- Change clause (a), (c) or (d), or read `re_scope_gate.note`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| decimal-int field | `commit: 4139357790` | covers retro `4139357790…` | — |
| decimal-int list item | `commits: [4139357790]` | covers retro `4139357790…` | — |
| octal-shaped field | `commit: 0123456701` (loads as `21913025`) | covers retro `0123456701…` | scalar text, not value |
| binary-shaped field | `commit: 0b10110101` (loads as `181`) | covers retro `0b10110101…` | scalar text, not value |
| leading zero with 8 or 9 | `commit: 0123456789` (stays `str`) | covers retro `0123456789…` | unchanged |
| bool, float, null | `commit: true` / `1.5` / `null` | names nothing | `brief-defect` stands |
| short int | `commit: 413935779` | names nothing (< 10) | `brief-defect` stands |
| free text | `reason: mirrored 4139357790 …` | names nothing | unchanged |
| int pointer, newest | `brief_mirrored_through: 4139357790` | no `unmirrored-retro` | — |
| int pointer, empty brief | same pointer, no amendment | `brief-defect`, not a skip | — |
| prefix pointer, newest | `brief_mirrored_through: "4139357790"` | no `unmirrored-retro` | remedy value clears it |
| prefix pointer, out of range | pointer older than `--since`; brief names the full SHA | covered | symmetric prefix rule |
| bool or float pointer | `brief_mirrored_through: true` | (b') skips; (b) reports | as today |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-16 (← `spec-conda-forge-expert-rebuild` CAP-3). No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 — Ruled: the CFE-rebuild guard reads a SHA field
whatever type YAML gives it*.
Ledger key: `28-1-the-rebuild-guard-reads-a-sha-field-whatever-type-yaml-gives-it`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1).
Epic: a new Epic 28, because Epic 6 (the guard's own epic) and Epic 12 (Story 12.4's re-scope gate) are done, and a
fix story on a done epic breaks the ledger detectors.
Minted 2026-10-09 on the operator's ruling of that day ("yes mint both stories and keep going").

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test`. Expected: pass. This is the station's `verify_commands`,
  and it runs `test_cfe_rebuild_guard_merges.py`, which loads the guard.

**Manual checks:**

- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`, the `scripts-suite` job's command. Expected: pass.
- `pixi run -e pyforge-guild cfe-rebuild-guard-check`. Expected: exit 0 on the live repo.
- The red-first run (AC 7): the new tests against `git show origin/main:scripts/cfe_rebuild_guard_check.py` fail, and
  pass on the branch.
- `pixi run -e pyforge-guild spec-surface-check`. Expected: exit 0.
- `pixi run -e pyforge-guild pr-preflight`. Expected: exit 0.

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — adversarial self-review against diff and AC matrix; no patch/defer routes)

## Auto Run Result

Status: done

Summary: `cfe_rebuild_guard_check.py` now reads SHA candidates from YAML strings and ints (scalar text preserved via a SafeLoader int map for octal/binary tokens), compares SHAs with one symmetric prefix rule, and applies the same reading to `brief_mirrored_through` in clauses (b) and (b'). Clause (b)'s remedy names an accepted prefix value.

Files changed:
- `scripts/cfe_rebuild_guard_check.py` — SHA reader, loader int scalars, comparison rule, docstring/remedy
- `tests/scripts/test_cfe_rebuild_guard_check.py` — Story 28.1 AC coverage (fixed SHAs, no commits)
- `_bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml` — ledger sync for 28.1 done

Red-first (AC 7): new parametrized/unit tests fail against `origin/main`'s guard (int commit fields dropped); pass on this branch.

Verification:
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — exit 0
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — exit 0 (1419 passed)
- `pixi run -e pyforge-guild cfe-rebuild-guard-check` — exit 0
- `python scripts/spec_surface_reconcile.py` — exit 0 (no governed-path memlog entries required; script on allowlist)

Follow-up review recommended: false

Residual risk: two distinct YAML int scalars that parse to the same integer in one document would share one map entry (unlikely for SHA/order fields in practice).
