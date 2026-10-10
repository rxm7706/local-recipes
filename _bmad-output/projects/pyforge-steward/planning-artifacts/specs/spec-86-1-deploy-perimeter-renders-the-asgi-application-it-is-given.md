---
title: "86.1: Deploy perimeter renders the ASGI application it is given"
type: 'fix'
created: '2026-10-10'
status: 'done'
baseline_revision: 'f05de4bab8500a64631f84d8a9a0dc6bce064295'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/tests/unit/test_deploy_perimeter.py
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `steward deploy perimeter` renders a daphne unit for one application only, a hardcoded Django
placeholder. It cannot front Herald's webhook host, which herald's Story 19.2 is re-scoped to run on this machine's local
stack.

- **The ruling.** On 2026-10-10 the operator chose the local-host path for herald Story 19.2, verbatim "go with option 1,
  local host": "Mint a small steward fix that adds `--asgi-application` to `deploy perimeter`. Then re-scope herald 19.2
  so its host and store are this machine's local stack: `pyforge-foundry-full-stack` with PostgreSQL 17. No public
  endpoint, nothing outside the repo. Herald Epic 19 then closes, and 49.11 flips to done."
- **What the code does on `6d5e84cb6b`:**
  - `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` sets
    `_ASGI_APPLICATION_PLACEHOLDER = "myproject.asgi:application"` at `:539`. The comment at `:532`-`:538` records why
    Story 9.5 added no flag: its spec's Code Map named none, so the adopter edits the rendered line by hand.
  - `render_daphne_unit` (`:564`) takes only `topology`, `base_port` and `bind_host`. It writes a comment telling the
    adopter to replace the placeholder (`:604`-`:605`) and `ExecStart=daphne --bind {bind_host} --port %i
    --proxy-headers {_ASGI_APPLICATION_PLACEHOLDER}` (`:613`).
  - `_run_perimeter` (`:833`) validates the topology, then renders the daphne unit, the nginx edge config
    (`render_edge_config`, `:724`) and the audit-grants SQL into `--output-dir`.
  - The `perimeter` parser in `cli.py` (`:870`-about `:930`) declares `--workers`, `--cache-backend`,
    `--channel-layer-backend`, `--trusted-address`, `--tls-cert`, `--tls-key`, `--output-dir`, `--app-db-role` and
    `--audit-retention-db-role`. None names the application.
- **The deferral.** Herald's DW-13-6-1 (`_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md`,
  the row titled "Steward's `deploy perimeter` cannot target an arbitrary ASGI application") records this gap, citing
  `deploy.py:484` before the module grew. Its fix candidate is this story: an `--asgi-application <module:variable>` flag
  threaded into `render_daphne_unit`. It also asks whether `render_edge_config`'s nginx assumptions (one upstream shape,
  `X-Forwarded-For` handling) hold for a non-Django ASGI app.

**Approach:** one optional flag, validated before anything renders. Without it, nothing changes.

- `render_daphne_unit` gains a keyword `asgi_application: str = _ASGI_APPLICATION_PLACEHOLDER`.
  - At the default, the output is byte-identical to today's, including the replace-the-placeholder comment.
  - Given any other value, `ExecStart` names it and the replace-the-placeholder comment is not rendered.
- `cli.py`'s `perimeter` parser gains `--asgi-application`, metavar `MODULE:ATTR`, default `None`. Its help names the
  form and says the default is the placeholder an adopter replaces by hand.
- `_run_perimeter` validates the value before any render, in validation-only mode too. It must match
  `^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$`. Anything else
  is `DutyResult(ok=False, summary="deploy perimeter: refused — --asgi-application …")`, naming the value and the form,
  and nothing is written. The success summary names the application when one is given.
- `render_edge_config` does not change. It proxies to `bind_host` and the worker ports, and never names the application;
  daphne's `--proxy-headers`, already in `ExecStart`, makes any ASGI application see the client address from
  `X-Forwarded-For`. A test shows the edge config is the same for the default and an override. That answers
  DW-13-6-1's nginx question.
- The comment at `:532`-`:538` is replaced by one that cites this story and DW-13-6-1.
- DW-13-6-1 is closed in herald's deferred-work ledger: its `status:` becomes the resolved value that ledger uses, with
  a dated line naming this story, the flag and the tests. It is the one herald file this story touches, and only that
  row.

Ledger key: `86-1-deploy-perimeter-renders-the-asgi-application-it-is-given`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour:** `spec-pyforge-steward` CAP-114, "the deployment perimeter ships with the pattern" (from
  `spec-secure-live-dashboards` CAP-6; Story 9.5 built `deploy perimeter`). An adopter receives a production-shaped
  runtime rather than assembling one. A placeholder the adopter re-edits after every render falls short of that for any
  application but steward's own dashboard. This story mints no CAP and changes no `SPEC.md` text.
- **AD-1** (wrap, never reimplement): the unit still runs `daphne`; the flag only names its target. **AD-8**: the duty
  returns a `DutyResult`, never exits.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. The new option is opt-in and its absence
  is today's behaviour.
- **Epic.** Epic 9, which built `deploy perimeter`, is `done`, so this fix opens Epic 86 (repo convention: a fix on a
  done epic gets a new epic).

## Acceptance Criteria

- **(1) The default is unchanged.** Given the fixture topology and declarations of
  `test_perimeter_with_output_dir_renders_both_manifests` When `deploy perimeter` renders without
  `--asgi-application` Then the daphne unit, the nginx edge config and the grants SQL are byte-identical to the render
  of `6d5e84cb6b`. A golden string, or a render through the default keyword, pins each file.
- **(2) The override renders.** Given `--asgi-application pyforge.herald.webhook_host:application` When it renders
  Then the unit's `ExecStart` line is `ExecStart=daphne --bind 127.0.0.1 --port %i --proxy-headers
  pyforge.herald.webhook_host:application`, the unit contains neither `myproject.asgi:application` nor the
  replace-the-placeholder comment, and the duty's summary names the application. The same holds through
  `main(["deploy", "perimeter", …, "--asgi-application", …])`, which exits `EXIT_OK`.
- **(3) Invalid values are refused.** Given each of `""`, `"app"`, `"pkg.mod:"`, `":application"`,
  `"pkg mod:application"`, `"pkg.mod:application;rm -rf /"`, `"pkg.mod:application\nExecStartPre=/bin/sh"` and
  `"pkg..mod:application"` When `deploy perimeter` runs with `--output-dir` Then the result is `ok=False`, its summary
  starts `deploy perimeter: refused` and names `--asgi-application`, and the output directory holds no file. In
  validation-only mode (no `--output-dir`) the same values are refused.
- **(4) The edge config does not depend on the application.** Given one topology and one set of declarations When the
  manifests render with the default and with an override Then the two nginx edge configs are byte-identical.
- **(5) The CLI's counts do not move.** The duty count and the deploy verb list asserted in `tests/unit/test_cli.py`
  and `tests/unit/test_restore_duty.py` are unchanged, and `steward deploy perimeter --help` lists `--asgi-application`.
- **(6) The deferral closes.** Herald's DW-13-6-1 row carries the closed status that ledger uses and a dated line naming
  Story 86.1, the flag, and the test names for (2) and (4). `pixi run -e pyforge-guild deferred-work-check` exits 0.
- **(7) Mutations fail the tests.** Hardcoding the placeholder in `ExecStart` again fails (2). Dropping the validation
  fails (3). Rendering the replace-the-placeholder comment for an override fails (2).

## Boundaries & Constraints

**Always:**
- Change only these paths:
  - `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py`;
  - `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`;
  - `src/shared/packages/pyforge-steward/tests/unit/test_deploy_perimeter.py`;
  - herald's `deferred-work-ledger.md`, the DW-13-6-1 row only;
  - `docs/reference/station-cheat-sheet.md`, through `docs-station-cli` and only if its output changes.
- Validate before rendering, and write nothing on a refusal (the I/O matrix of Story 9.5 holds).
- Co-governors: steward's `src/` is governed by `spec-pyforge-steward` and `spec-pyforge-core`. Add a memlog entry on
  every Spec `spec-surface-check` names, then `git add`. Run one scoped stamp per named Spec from a clean tree, re-run
  the check and read its exit code.

**Never:**
- Never deploy, install or start a unit, and never call the network. The duty renders files only.
- Never change the unit's file name (`pyforge-steward-dashboard@.service`), its `Description`, the nginx config or the
  grants SQL. A rename would break (1) and is not asked for.
- Never edit herald's code, specs, epics or ledger. Its re-scope of Story 19.2 is herald's chain. The DW-13-6-1 row is
  the only herald line this story writes.
- Never flip steward's 49.11 key. It flips when herald Epic 19 closes.
- Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Command | Verdict |
|---|---|
| `steward deploy perimeter --workers 1` | ok, validation only, as today |
| same `--output-dir D` with all declarations, no `--asgi-application` | ok; three files byte-identical to today's |
| same with `--asgi-application pyforge.herald.webhook_host:application` | ok; `ExecStart` names it; no placeholder comment; summary names it |
| `--asgi-application app` | refused, names the form; nothing written |
| `--asgi-application "pkg.mod:application;rm -rf /"` | refused; nothing written |
| `--asgi-application` invalid, no `--output-dir` | refused (validation-only mode validates it too) |
| `--workers 2` with in-process backends and a valid override | refused for the backends first, as today |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-114 (Story 9.5). Closes herald DW-13-6-1.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (local host) entry.
- Epic: Epic 86 (new; Epic 9 is `done`).
- Ledger key: `86-1-deploy-perimeter-renders-the-asgi-application-it-is-given`; `epic-86` and
  `epic-86-retrospective` minted with it.
- Ledger status at mint: `backlog`.
- Deps: —. Herald's re-scope of Story 19.2 waits on this story; this story waits on nothing.
- Spec: `spec-pyforge-steward/.memlog.md` records the ruling and the mint. `SPEC.md` is untouched and no CAP is minted.
- Surface: `src/shared/packages/pyforge-steward/**` is in Epic 86's `[epic_surfaces]` entry, as are herald's
  `deferred-work-ledger.md` and `docs/reference/station-cheat-sheet.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run -e pyforge-guild deferred-work-check` — expected: exit 0 with DW-13-6-1 closed.
- `pixi run -e pyforge-guild steward deploy perimeter --workers 1 --asgi-application pyforge.herald.webhook_host:application`
  — expected: ok, validation only.

## Spec Change Log

- 2026-10-10: minted from the operator's ruling "go with option 1, local host".

## Review Triage Log

### 2026-10-10 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — diff read against all seven acceptance criteria and I/O matrix rows)

## Auto Run Result

- **Summary:** Added optional `steward deploy perimeter --asgi-application MODULE:ATTR` with pre-render validation, default-preserving daphne unit rendering, and closed herald DW-13-6-1.
- **Files changed:**
  - `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` — ASGI path validation (no `re` import; deploy.py invariant), `render_daphne_unit` override, `_run_perimeter` wiring
  - `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `--asgi-application` flag
  - `src/shared/packages/pyforge-steward/tests/unit/test_deploy_perimeter.py` — AC (1)–(4) coverage and help listing
  - `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md` — DW-13-6-1 → resolved
- **Review:** 0 patches; 0 deferrals; no rejected findings.
- **followup_review_recommended:** false
- **Verification:**
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2280 passed, 2 skipped
  - `pixi run -e pyforge-guild deferred-work-check` — ok
  - `python scripts/spec_surface_reconcile.py` — exit 0 (after memlog reconcile; no `--write-baseline`)
  - `pixi run --frozen -e pyforge-guild lint-types` — see session log
- **Residual risks:** Herald Story 19.2 re-scope and ledger 49.11 flip remain herald's chain (out of scope here).
