---
title: '121.4: A chain write off the writer is refused in session'
type: 'feature'
created: '2026-11-10'
status: 'done'
flag-exempt: detector-or-gate
difficulty: medium
story: 121.4
spec: python-foundry-cutover
surface:
  - docs/governance/guild-roster.json
  - .claude/hooks/pre-shell.py
  - tests/scripts/test_pre_shell_hook.py
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md
  - docs/governance/guild-roster.json
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Ruling 2: `pyforge.cutover_root` means the writer lock and the root of record, and nothing reads it as such. This is the guard the ruling names (Story 44.12 stays done). The session denial is the session half; doctor Story 56.5 is the branch half, a detectors-ci source that reads the flag at the merge base (fnd:AD-24). The hook also hard-codes this root's slug three times.

**Approach:** Roster: `roots: {this: local-recipes}` with a `$comment_roots` (the hook needs this checkout's identity without pyforge; the slug table stays core's `FORGE_SLUGS`, never a second copy). One `session_denials` entry in the existing shape; its reason names the root of record and the sanctioned path (write on the root of record, then bump the pin). Hook: `match_chain_write_off_the_writer` checks the path first, then loads `pyforge.core.cutover_root` (installed, or from the in-repo core source by path, the `_commit_msg_hook` precedent) and calls `root_of_record()`; writer when `.root == roots.this` and `.source == 'flag-tree'`; a `default` source denies with its own reason; a `CutoverRootError` exits 2. `_LOCAL_RECIPES_SLUG` and the two `--repo` comparisons read `FORGE_SLUGS[roots.this]`. The module docstring's rule count follows. Any test pinning 19 session denials follows to 20 in this story's files.

Ledger key: `121-4-a-chain-write-off-the-writer-is-refused-in-session`. Type / Effort / Deps: feature / M / S-120.1.

### Living CAP citations

- **`spec-python-foundry-cutover`** — fnd:CAP-2, fnd:CAP-8 (the writer lock), fnd:CAP-9 (the ledger generator) and fnd:CAP-11, amended 2026-11-10 by memlog and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Adding the denial is a governance act the operator authorised (the second addendum's ruling 3).
- Cursor has no before-edit deny, so the rule warns there.

**Never:**
- Never match a Bash write (memlog.py, sed): doctor Story 56.5 judges the branch for every harness.
- Never keep a slug literal in the hook.
- Never edit AGENTS.md here: its denial count and wording are scribe's.

## Acceptance Criteria

- **AC1 — the hook's tests.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-guild python -m pytest tests/scripts/test_pre_shell_hook.py -q -p no:cacheprovider
  ```
- **AC2 — the roster declares the denial and this root only.** Expected: exit 0.
  ```bash
  python3 -c "import json;d=json.load(open('docs/governance/guild-roster.json'));r={x['id']:x for x in d['session_denials']};e=r['chain-write-off-the-writer'];assert e['applies_to']=='edit_write' and e['trigger'] and e['reason'];assert len(r)==20;assert d['roots']=={'this':'local-recipes'}"
  ```
- **AC3 — the hook holds no slug literal (lines 671, 674 and 1140 today).** Expected: 0.
  ```bash
  grep -c 'rxm7706/' .claude/hooks/pre-shell.py
  ```
- **AC4 — the denial fires off the writer and is silent on it.** Expected: exit 0, at least 6 tests selected (flipped fixture denies on Claude and warns on Cursor; writer allowed; non-chain path allowed under either flag; source default denies; unreadable tree exits 2).
  ```bash
  pixi run -e pyforge-guild python -m pytest tests/scripts/test_pre_shell_hook.py -q -p no:cacheprovider -k chain_write
  ```
- **AC5 — removing the matcher is loud.** Expected: exit 0, 1 test selected (a copy of MATCHERS without the id makes the roster load raise RuntimeError).
  ```bash
  pixi run -e pyforge-guild python -m pytest tests/scripts/test_pre_shell_hook.py -q -p no:cacheprovider -k chain_write_matcher_removal_is_loud
  ```
- **AC6 — the slug comes from core's table.** Expected: exit 0, 1 test selected (hook slug == FORGE_SLUGS[roots.this]).
  ```bash
  pixi run -e pyforge-guild python -m pytest tests/scripts/test_pre_shell_hook.py -q -p no:cacheprovider -k slug_parity
  ```
- **AC7 — stdlib lane still collects the file.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-ci pyforge-doctor-scripts-test
  ```
- **AC8 — the denial's reason passes the forms test.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-guild scripts-lib-test
  ```

</intent-contract>

## Binding

Parent: `spec-python-foundry-cutover` fnd:CAP-8

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 121.
- Ledger key: `121-4-a-chain-write-off-the-writer-is-refused-in-session` (`backlog` at mint).
- Deps: S-120.1.
- Surface: `docs/governance/guild-roster.json`, `.claude/hooks/pre-shell.py`, `tests/scripts/test_pre_shell_hook.py`.
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_pre_shell_hook.py -q -p no:cacheprovider` — expected: exit 0.

## Notes

- Cross-station: marshal:S-117.2 (`root_of_record()` and `FORGE_SLUGS`) must land first; doctor:S-56.5 is the branch half; scribe:S-32.1 carries AGENTS.md's count (`Sixteen`, twice).
