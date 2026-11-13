---
title: "50.3: Herald's public contract is one companion, and a meta-test holds the code to it"
type: 'feature'
created: '2026-11-10'
status: 'done'
flag-exempt: detector-or-gate   # a companion document and the test that judges it (a gated gate reports a silent green); the cli.py edit is citation and help text, no behaviour
difficulty: heavy
story: '50.3'
spec: pyforge-herald
surface:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/contract.md
  - src/shared/packages/pyforge-herald/tests/meta/test_public_contract.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py
  - src/shared/packages/django-herald/src/django_herald_portal/mcp_asgi.py
  - docs-site/src/lib/flags.ts
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-52.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).
>
> **Unblocked 2026-11-13.** Every story its Deps name is `done` on branch `cutover-readiness-2026-11-10`. The operator's "Start build" consent covered the unblock; CLOSE-LEDGERS moved the key to `done`.

<intent-contract>

## Intent

**Problem:** Herald's Spec names no CLI flag, MCP tool, flag key, environment variable or exit code, so a second
root rebuilding herald from its Spec cannot reproduce the surface a caller touches (audit cross-cutting fault 3;
SHOULD: code with no CAP). Separately, `cli.py`'s 22 capability citations (help strings, docstrings, one error
message) use the numbers from before the 2026-09-17 remint, so operator-facing text points at the wrong capability
(audit MUST 8).

**Approach:** spec-pyforge-herald CAP-62 (minted 2026-11-10; FR-14.1) is realized by one companion and one test. No
CLI verb or generator is added.

- **`contract.md`**, beside `SPEC.md`, is written by hand from the code. It has one table per kind:
  - CLI verb paths with their flags, and a CAP column naming the capability each verb realizes. The verb table is
    where `deck qa` (CAP-26..CAP-28), `scheduler run` (CAP-39), `deck pptx-spec` and `deck pptx-fill` (CAP-41),
    `deck pptx-native` (CAP-57) and the MCP face (`spec-pyforge-unifying-strategy:CAP-20`, steward Epic 119) get
    their capability.
  - The two MCP tools of `POST /stations/herald/mcp` (`start_notice`, `get_notice`).
  - Feature-flag keys, whatever their prefix: herald's own `*_FLAG` constants (five today), and each flag reader of
    `docs-site/src/lib/flags.ts`. A flag reader is an exported function whose doc comment opens with a backticked key
    matching `pyforge\.[a-z_]+\.[a-z_]+` (three today: `statusPages`, `ciSurfacesTile` and `marketplacePages`, among
    them `pyforge.steward.marketplace_pages`). `envFlagOn`, the generic helper whose doc comment opens with its
    parameter `name`, is exempt by name; any other exported function with no such key fails the test.
  - Environment variables, from every read form the tree uses. In the package: a string literal read through
    `os.environ.get(…)`, `os.environ[…]` or `os.getenv(…)`, and every string constant, annotated or not, whose name
    ends in `_ENV` or `_ENV_VAR` (`CREDENTIALS_PATH_ENV`, `TOKEN_ENV_VAR`, `SECRET_ENV_VAR`, `REPO_ROOT_ENV_VAR`, deck_store's five
    `*_ENV`), however it is read (`os.environ.get(CONST)`, an injected `source.get(CONST)` whose default is
    `os.environ`, or `deck_store._env(CONST)`). Under `docs-site/src`, `docs-site/scripts` and
    `docs-site/astro.config.mjs`: `process.env.X`; `process.env[CONST]`, resolved through the constant's
    `export const CONST = '…'` (`INPUTS_DIR_ENV` is `PAGES_BUILD_INPUTS_DIR`); `env.X` on an injected env record (a
    parameter or local named `env` whose default is `process.env`, as in `built-from.ts`, `pages.mts` and
    `marketplace.ts`); and the string argument of `envFlagOn('X', …)` (the three `PYFORGE_*` keys in `flags.ts` and
    `pages.mts`). `envFlagOn`'s own `env[name]` is the generic read and names no key. `import.meta.env.X` is Astro's
    build constant, not an environment read, and is not scanned.
  - `HeraldError` classes with their exit codes, and the closed exit-code set (0, 1, 2, 3, 4).
- **Repository keys.** Herald reads no flag key through a core seam. When herald's source imports
  `pyforge.core.cutover_root`, which Story 52.2 adds, the contract names the roster key it resolves, `roots.this`.
  Story 52.2 writes that row in the same change as the import, so this story's `contract.md` lists no such row. The
  test carries the check from birth: a herald source that imports `pyforge.core.cutover_root` while `contract.md`
  has no repository-key row naming the roster key it resolves fails, naming the module (CAP-62's success).
- **`tests/meta/test_public_contract.py`** carries `pytestmark = pytest.mark.live_tree` from birth (it reads the
  Spec folder, docs-site and django-herald as data); Story 52.1 registers the marker. It builds the parser through
  `pyforge.herald.cli._build_parser()` and walks the subparser actions. It reads tool names from `mcp_asgi.py` by
  regex, with no Django import. It does not use a bare `pyforge\.herald\.` regex, which would catch module paths. It
  fails in both directions: on code the contract lacks and on contract rows the code lacks. Its own `planted` cases
  run over in-memory fixtures.
- **`cli.py`.** All 22 citations are re-keyed to the folded Spec's ids (CHAIN-STANDARD § 6), and the deck group's
  help lists its verbs from the parser. Nothing else in the module changes.
- Known surface on 2026-11-10: 5 top-level commands, 12 deck verbs, 30 `add_parser` calls, 82 `add_argument` calls,
  exit codes 0, 1, 2, 3, 4.

Ledger key: `50-3-herald-s-public-contract-is-one-companion-and-a-meta-test-holds-the-code-to-it`.
Type / Effort / Deps: feature (`flag-exempt: detector-or-gate`) / L / S-52.1.

## Boundaries & Constraints

**Always:**
- Write the companion by hand from the code, and let the test judge it in both directions.
- Use a `cli_cites` check: for each handler the parser reaches, the `CAP-n` tokens in its help, docstring and body
  are a subset of its contract row's capabilities; module-level tokens are a subset of the union.
- Read every verdict from the exit code.

**Never:**
- Never write a generator or a CLI verb that emits the contract.
- Never change `cli.py` behaviour; only citation and help text move.
- Never write `SPEC.md`, `.memlog.md` or the PRD. The mint wrote CAP-62 and FR-14.1, and Story 50.2 adds
  `contract.md` to `companions:` and writes herald's reconcile line. The co-governor spec-pyforge-core takes its line
  from its own closer (marshal:S-117.8).

## Acceptance Criteria

Each verdict is read from the exit code, never through a pipe.

- **AC1 — The contract test passes on the tree.**
  `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_public_contract.py -q`.
  Expected: exit 0.
- **AC2 — The test fails in both directions on planted differences.**
  `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_public_contract.py -q -k planted`.
  Expected: exit 0, with at least 10 tests selected. The failure text names each of these: an extra verb, an extra
  option, an extra MCP tool, an extra `*_FLAG` constant, an exported `flags.ts` function other than `envFlagOn` with
  no documented `pyforge.<station>.<name>` key, an extra environment variable read as `process.env.X`, an extra
  environment variable read as `env.X` on an injected env record, an extra error class, a contract row the code
  lacks, and an in-memory herald source that imports `pyforge.core.cutover_root` against a contract with no
  `roots.this` repository-key row.
- **AC3 — The contract carries the measured surface.** Run `grep -c` on `contract.md` for each of
  `'^| \`herald deck '`, `'start_notice\|get_notice'`, `'pyforge\.herald\.[a-z_]*'` and
  `'pyforge\.steward\.marketplace_pages'`. Expected: the first count is at least 12 (the twelve deck verbs). The
  second is at least 2. The third is at least 5 (`ci_surfaces_tile`, `deck_export_native`, `deck_publish`,
  `deck_viewer`, `status_pages`). The fourth is at least 1 (the key `docs-site/src/lib/flags.ts` reads as
  `PYFORGE_MARKETPLACE_PAGES`). Then run `grep -c` for each of `'PAGES_BUILD_INPUTS_DIR'` (a `process.env[CONST]`
  read), `'GITHUB_RUN_ID'` (an `env.X` read), `'PYFORGE_STATUS_PAGES'` (an `envFlagOn` argument), `'TOKEN_ENV_VAR\|HERALD_TOKEN'`
  (a `*_ENV_VAR` constant) and `'HERALD_LIVE_SYNC_PROOF'` (a literal `os.environ.get`). Expected: each prints at least
  `1`, and `grep -cE '(^|[^_A-Z])BASE_URL'` prints `0` (`import.meta.env.BASE_URL` is not an environment read;
  `PAGES_HOST_BASE_URL` is, and that pattern does not match it).
- **AC4 — `cli.py` cites only what its contract rows name.**
  `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_public_contract.py -q -k cli_cites`.
  Expected: exit 0.
- **AC5 — The pre-fold number pairs are gone.**
  `git grep -nE 'Story 15\.1, CAP-1\b|Story 23\.[146], CAP-[168]\b|\(seed/pull/status/watch\)' -- src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py`.
  Expected: exit 1 (no match). Today `:229`, `:380`, `:426`, `:446`, `:945`, `:1051`, `:1159` and `:1255` match;
  `:1236` breaks the pair across two lines and is caught by AC4.
- **AC6 — Herald's suite and the lint gate hold.**
  `pixi run -e pyforge-herald pyforge-herald-test && pixi run -e pyforge-guild lint-types`. Expected: exit 0.
- **AC7 — The touched-module coverage floor holds for `cli.py`.**
  `pixi run -e pyforge-herald pyforge-herald-coverage-gate`. Expected: exit 0. A text-only edit moves no line of
  coverage. If `cli.py` is under the 80 % floor today, the story adds the missing unit cases; it does not skip the
  gate.
- **AC8 — Post-condition, run by steward:S-124.2.**
  `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q`.
  Expected: exit 0 once steward-station has added the spec-pyforge-herald Spec folder to herald's trigger paths.
  Before that it fails by design, naming exactly the difference this story introduced.

</intent-contract>

## Binding

- Capability: spec-pyforge-herald CAP-62 (minted 2026-11-10, `(ready 2026-11-10)` until this story lands). FR-14.1
  ← CAP-62 (PRD Feature Group 14). No AD; the spine's 2026-11-10 currency section records why.
- Dream: `docs/dreams/pyforge-herald.md`, the 2026-11-10 (cutover readiness) entry.
- Epic 50. Ledger key `50-3-herald-s-public-contract-is-one-companion-and-a-meta-test-holds-the-code-to-it`.
- Cross-station: steward:S-124.2 (herald's trigger paths gain the Spec folder). It is a post-condition, not a gate.
- Findings closed: MUST 8 (cli.py's 22 citations); SHOULD: code with no CAP.
- The plan's `DW-herald-50-3-1` (93 citations in 23 other modules) is not minted, because Story 50.4 carries that
  work. `DW-herald-50-3-2` is this story's planned deferral, and Story 50.2 writes it.

## Spec Change Log

- 2026-11-10: minted (backlog) with CAP-62 and FR-14.1. Following the integration ruling on Story 52.2 (operator
  ruling 5 of the second addendum: only ruling 2's three consumers follow the root of record), the contract lists
  `roots.this` as a repository key, not `pyforge.cutover_root` as a flag key.
- 2026-11-10: status set to blocked (forward dependency on a later epic; unblocked only with operator confirmation).
- 2026-11-11: the mint's review found that the environment scan (`process.env.X` only) missed most of the docs-site
  build's reads and that `flags.ts` exports a fourth function, the generic helper `envFlagOn`. The scan now covers
  every read form the tree uses, a planted case covers an `env.X` read, AC3 counts one row of each form, and a
  `flags.ts` flag reader is defined by its `pyforge.<station>.<name>` key, with `envFlagOn` exempt by name.

## Planned deferral (written at build)

The row below is not in the deferred-work ledger yet. Story 50.2 writes it to
`planning-artifacts/deferred-work-ledger.md` and adds it to this spec's `deferred:` frontmatter in the same change,
because `deferred-work-check` refuses a frontmatter deferral with no tracked twin. Station deferred-work rows are
written at build, never at mint.

- **`DW-herald-50-3-2`** (low, open; location `docs/how-to/presentation-deck.md`): docs/how-to/presentation-deck.md documents 8 of herald's 12 deck verbs. The four missing verbs are listed in contract.md once this story lands. Fix: add them to the how-to, with a reconcile line on spec-pyforge-doctor, which governs docs/how-to/**.
