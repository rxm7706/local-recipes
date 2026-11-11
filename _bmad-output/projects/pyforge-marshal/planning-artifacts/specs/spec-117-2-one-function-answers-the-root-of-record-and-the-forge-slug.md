---
title: "117.2: One function answers the root of record and the forge slug"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: flag-infrastructure   # the module holds the flag tree's one resolver (resolve_flags_path) and the reader of pyforge.cutover_root; this story adds no consumer, and each consumer story is a fix with no kill switch (operator ruling 2026-11-10)
difficulty: easy
story: '117.2'
spec: pyforge-core
surface:
  - src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py
  - src/shared/packages/pyforge-core/tests/unit/test_cutover_root.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py
  - src/shared/packages/pyforge-core/src/pyforge/core/roster.py
  - src/shared/packages/pyforge-core/tests/unit/test_cutover_root.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D3 of the 2026-11-10 design pass and operator ruling 2 of 2026-11-10: `pyforge.cutover_root` means the writer lock and the root of record, and its consumers need one answer. At `82a2b18828` nothing but its own reader reads the value, and the repository slug is a literal in marshal (four sites), herald, steward and atlas.

**Approach:** Realizes spec-pyforge-core:CAP-13 (memlog 2026-11-10, rendered by Story 117.5). New code in the leaf, no consumer in this story. API: `FORGE_SLUGS: Mapping[str, str]`, a read-only mapping `{'local-recipes': 'rxm7706/local-recipes', 'foundry': 'rxm7706/python-foundry'}`; `@dataclass(frozen=True) class RootOfRecord: root: str; forge_slug: str; source: str` with `source` in `{'flag-tree', 'default'}`; `def forge_slug_for(root: str) -> str` (pure; `CutoverRootError` for a root outside `CUTOVER_VARIANTS`); `def root_of_record(path: Path | str | None = None) -> RootOfRecord`. An explicit `path` is read with `read_cutover_root(path)`, so one that is not a file raises `CutoverRootError` (answering `default` would hide a mistyped path); with no path, `resolve_flags_path()` finds the tree (`PYFORGE_FLAGS_PATH`, then the walk-up, unchanged) and `read_cutover_root` reads it, so the overlay composition and every `CutoverRootError` hold; only when no tree is in reach does it answer `DEFAULT_CUTOVER_ROOT` with source `default` (ruling 5 of the second addendum). Kept out of the seam: `is_writer` (the caller compares its own root name), the clone URL (`https://github.com/<slug>.git`, composed by the caller) and the station-packages directory (B's to settle, DW-marshal-115-4-1). Test names carry `root_of_record` or `forge_slug`.

Ledger key: `117-2-one-function-answers-the-root-of-record-and-the-forge-slug`. Type / Effort / Deps: feature / S / S-117.5.

## Boundaries & Constraints

**Always:**
- The slug table is a constant in `pyforge.core.cutover_root`; the leaf reads no repository file (operator ruling of 2026-11-10: constant, not a governance read).
- `read_cutover_root`, its constants and the four case-list tests stay as they are.

**Never:**
- No new exception class, environment variable or override.
- No consumer is wired here: marshal Story 115.4, steward:S-121.4 and doctor:S-56.5 call the function in their own stories.
- Never append a `Surface reconcile` line to any Spec's memlog and never run `spec_surface_check.py --write-baseline`: the governed paths go in this spec's `surface:`, Story 117.8 reconciles core and the testing charter, and doctor:S-58.4 stamps once.

## Acceptance Criteria

- **AC1 — Unit tests for the seam.**

  ```bash
  pixi run --frozen -e pyforge-core python -c "import re,subprocess,sys; r=subprocess.run(['pytest','src/shared/packages/pyforge-core/tests/unit/test_cutover_root.py','-q','-p','no:cacheprovider','-k','root_of_record or forge_slug'],capture_output=True,text=True); m=re.search(r'(\d+) passed',r.stdout); print(r.returncode, m and m.group(1)); sys.exit(r.returncode or not m or int(m.group(1))<8)"
  ```

  Expected: exit 0, at least 8 passed (the cases spec-pyforge-core:CAP-13's success names).

- **AC2 — The checked-in tree answers A, and a mistyped path refuses.**

  ```bash
  pixi run --frozen -e pyforge-core env PYTHONPATH=src/shared/packages/pyforge-core/src python -c "import pytest; from pyforge.core.cutover_root import root_of_record, forge_slug_for, FORGE_SLUGS, CUTOVER_VARIANTS, CutoverRootError; r=root_of_record('src/platform/config/flags.json'); assert (r.root, r.forge_slug, r.source)==('local-recipes','rxm7706/local-recipes','flag-tree'), r; assert forge_slug_for('foundry')=='rxm7706/python-foundry'; assert set(FORGE_SLUGS)==set(CUTOVER_VARIANTS); pytest.raises(CutoverRootError, root_of_record, 'src/platform/config/no-such.json')"
  ```

  Expected: exit 0 (a missing explicit path raises `CutoverRootError`; `pytest.raises` fails the command when it does not).

- **AC3 — The four case-list tests are unchanged.**

  ```bash
  python3 -c "import ast,subprocess,sys,pathlib; b=subprocess.run(['git','merge-base','origin/main','HEAD'],capture_output=True,text=True,check=True).stdout.strip(); p='src/shared/packages/pyforge-core/tests/unit/test_cutover_root.py'; f=lambda t:{n.name:ast.dump(n) for n in ast.parse(t).body if isinstance(n,ast.FunctionDef)}; o=f(subprocess.run(['git','show',b+':'+p],capture_output=True,text=True,check=True).stdout); n=f(pathlib.Path(p).read_text(encoding='utf-8')); k=['test_default_is_local_recipes','test_foundry_variant','test_unknown_variant_fails','test_missing_flag_fails']; bad=[x for x in k if o.get(x) is None or o.get(x)!=n.get(x)]; print(bad); sys.exit(bool(bad))"
  ```

  Expected: exit 0, prints `[]`.

- **AC4 — The slug has one home in the leaf.**

  ```bash
  git grep -l 'rxm7706/local-recipes\|rxm7706/python-foundry' -- src/shared/packages/pyforge-core/src
  ```

  Expected: prints exactly `src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py`.

- **AC5 — Still a leaf.**

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py -q -p no:cacheprovider
  ```

  Expected: exit 0.

- **AC6 — The whole core suite still passes as wired.**

  ```bash
  pixi run --frozen -e pyforge-core pyforge-core-test
  ```

  Expected: exit 0.

- **AC7 — Lint and types.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-core` (spec-pyforge-core:CAP-13; memlog 2026-11-10, rendered by Story 117.5); FR-251 <- spec-pyforge-core:CAP-13, written by Story 114.1 after Story 117.5's render; AD-66; fnd:AD-11, fnd:AD-17. Kinship: fnd:CAP-8 (the flag's own capability).

- Epic: Epic 117 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 117.2: One function answers the root of record and the forge slug`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Same-project dependency: Story 117.5. Needed by Story 115.4 (marshal's forge repository) and Story 117.4 (the contract lists the new names).
- Cross-station consumers: steward:S-121.4 and doctor:S-56.5 read `root_of_record()`; herald:S-52.2 reads `forge_slug_for()`.
- Deferred row (written by Story 116.5): DW-marshal-117-2-1 (atlas and warden still hold the repository slug as a literal).
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (core and the testing charter: Story 117.8; marshal: Story 116.5; steward and the host: steward:S-122.5), and doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). Its open Deps (S-117.5, later in this epic) name no later epic of this station, so the one forward-dependency policy of this PR's mints (a story is minted `blocked` only when its Deps name a later epic) leaves it `backlog`; the integration branch's wave order and marshal's Deps-aware drain hold them. The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-core` came first; `SPEC.md` is rendered by Story 117.5.
