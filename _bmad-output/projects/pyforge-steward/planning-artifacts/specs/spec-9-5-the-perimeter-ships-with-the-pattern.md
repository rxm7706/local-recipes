---
title: 'The perimeter ships with the pattern (Epic 9 Story 9.5, pyforge-steward)'
type: 'feature'
created: '2026-08-12'
status: 'done'
baseline_revision: 'f6b3e8f2b32efdedb498c47fa2352f5e17bb4594'
final_revision: 'e97c81a887b0d72ab360722b32ad81842313cf67'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-secure-live-dashboards-2026-08-09/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** CAP-6's deployment perimeter has no owner yet. The `[dashboard]` extra
installs Django only (no Channels/Daphne/asgiref/channels_redis, though the architecture
Stack table names all four); `cache.py`'s AD-5 refusal half — "refusing a backend that
cannot be shared once the deployment runs more than one worker" — is explicitly
unimplemented and deferred here by its own module docstring; and no edge (TLS
termination + network policy) config exists anywhere in this repo.

**Approach:** Extend the `[dashboard]` extra with `channels`/`daphne`/`asgiref`/
`channels_redis` (pixi.toml + pyproject.toml, byte-identical, mirroring Story 9.1's django
pin-sync precedent). Add a `DeploymentTopology` declaration + `check_shareable_state()`
refusal function to `deploy.py` (an out-of-process/AD-1 concern — never inside `dashboard/`,
which the import-boundary invariant forbids `deploy.py` from touching). Add a new
`steward deploy perimeter` verb — distinct from the pre-existing, unrelated `dashboard`
verb (docs/dashboard-gen) — that runs the refusal check and, on success, renders a daphne
systemd-template unit plus an nginx edge config (TLS termination, `allow`/`deny` network
policy scoped to the declared trusted addresses) into an output directory.

## Boundaries & Constraints

**Always:**
- New topology/manifest code lives in `deploy.py` (or a sibling base-package module), never
  under `dashboard/` — `test_no_module_outside_dashboard_imports_dashboard_django_or_channels`
  forbids `deploy.py` from importing anything under `pyforge.steward.dashboard`, and AD-1
  itself classifies "ASGI topology" and "edge policy" as out-of-process concerns.
- `check_shareable_state()` is allowlist-based (fail-closed): only backends this story can
  cite as genuinely cross-process-shared are accepted once `worker_count > 1` — Redis-backed
  cache classes and `channels_redis.core.RedisChannelLayer` (the architecture's own "sanctioned
  layer backend"). `worker_count == 1` accepts any backend (AD-5's own text).
- The new `channels`/`daphne`/`asgiref`/`channels_redis` pins in `pyforge-steward`'s
  `pyproject.toml` `[dashboard]` extra and pixi.toml's `[feature.pyforge-steward.dependencies]`
  stay byte-identical, enforced by tests mirroring `test_django_pin_matches_the_dashboard_extra`.
- `pixi.toml` changed → regenerate `environment.yaml` (`pixi project export conda-environment -e
  build > environment.yaml`), per this repo's CLAUDE.md gate.
- The rendered nginx edge config's network-policy block is derived only from caller-supplied
  trusted addresses (plain strings/CLI input) — this module never imports `TrustedIngress`
  from `dashboard/declarations.py` (same import-boundary rule as above).

**Block If:** none identified — CAP-6 has no undecided cross-cutting question this story's own
scope depends on; naming/allowlist/templating choices are recorded below as Design Notes, not
blockers.

**Never:**
- Build Story 9.6's non-vacuous proof suite or Story 9.7's static-publish path — both are
  separate CAP-7/CAP-8 stories with their own deps.
- Reuse the existing `dashboard` verb name for this new surface — it already means the
  docs/dashboard-gen GitHub-Pages console (`deploy.py`'s own header) and reusing it was flagged
  as a live naming collision on Story 9.1's deferred-work ledger.
- Actually provision, deploy, or reach a live daphne/nginx process — this story renders static
  manifest text to disk; running them is the adopter's/CI's job.
- Add a nested/second `[dashboard-*]` extra — one `[dashboard]` extra ships the whole runtime;
  a single-worker adopter simply never configures the Redis-backed settings, consistent with
  "the same artifact runs on a laptop and in production by config change only."

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Single worker, in-process backends | `worker_count=1`, LocMem cache + in-memory channel layer | `check_shareable_state` passes — no refusal | No error expected |
| Multi-worker, Redis-backed both | `worker_count=4`, Redis cache class + `RedisChannelLayer` | passes | No error expected |
| Multi-worker, in-process cache | `worker_count=4`, LocMemCache | raises naming the unshareable backend | Refusal names `cache_backend` |
| Multi-worker, in-process channel layer | `worker_count=4`, `InMemoryChannelLayer` | raises naming the unshareable backend | Refusal names `channel_layer_backend` |
| `DeploymentTopology.worker_count` invalid | `0`, negative, non-int | raises at construction | `ValueError`/`TypeError` naming the field |
| `perimeter` verb, refusal | topology fails the check | `DutyResult(ok=False, ...)` naming the missing/incompatible declaration; no manifest written | No exception escapes the duty |
| `perimeter` verb, `--output-dir` on success | topology passes | daphne unit + nginx config rendered to the directory | No error expected |
| `perimeter` verb, no `--output-dir` | topology passes | validation-only `DutyResult(ok=True, ...)`; nothing written | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` -- MODIFY: add `DeploymentTopology` (frozen dataclass: `worker_count`, `cache_backend`, `channel_layer_backend`), `UnshareableStateError`, `check_shareable_state()`, `render_daphne_unit()`, `render_edge_config()`, a `perimeter` verb added to `_DEPLOY_VERBS`, and `_run_perimeter(ns) -> DutyResult`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- MODIFY: `_add_deploy_subparsers` gains the `perimeter` subparser (`--workers`, `--cache-backend`, `--channel-layer-backend`, repeatable `--trusted-address`, `--tls-cert`, `--tls-key`, `--output-dir`).
- `src/shared/packages/pyforge-steward/pyproject.toml` -- MODIFY: `[dashboard]` extra gains `channels`, `daphne`, `asgiref`, `channels_redis` pins.
- `pixi.toml` -- MODIFY: `[feature.pyforge-steward.dependencies]` gains the same four pins, byte-identical to the extra.
- `environment.yaml` -- MODIFY: regenerated after the pixi.toml change.
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` -- MODIFY: pin-sync tests for the three new packages (mirroring `test_django_pin_matches_the_dashboard_extra`).
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_perimeter.py` -- NEW: exercises every I/O-matrix row plus the CLI verb wiring (mirrors `test_deploy_status.py`'s conformance-tier shape — all existing `deploy` verb tests live in `tests/conformance/`, not `tests/unit/`).

## Tasks & Acceptance

**Execution:**
- [x] `pyproject.toml` / `pixi.toml` -- add `channels`/`daphne`/`asgiref`/`channels_redis` pins to the `[dashboard]` extra and the matching pixi feature; confirm the combo solves (`pixi install` or equivalent) before finalizing exact floors -- CAP-6's "Django+Channels+Daphne via the optional extra"
- [x] `environment.yaml` -- regenerate via `pixi project export conda-environment -e build > environment.yaml`
- [x] `deploy.py` -- add `DeploymentTopology` + `check_shareable_state()` implementing AD-5's refusal, allowlisting Redis-backed cache classes and `channels_redis.core.RedisChannelLayer` only when `worker_count > 1` -- closes `cache.py`'s explicitly-deferred AD-5 gap
- [x] `deploy.py` -- add `render_daphne_unit()` (systemd template, parameterized by worker count/bind port) and `render_edge_config()` (nginx: TLS termination + `allow`/`deny` restricted to caller-supplied trusted addresses, proxying to the daphne workers) -- CAP-6's "edge that terminates TLS and enforces network policy"
- [x] `deploy.py` / `cli.py` -- wire the `perimeter` verb: validate via `check_shareable_state`, return a named refusal on failure, else render manifests to `--output-dir` if given
- [x] `tests/meta/test_invariants.py` -- pin-sync assertions for the three new dependencies
- [x] `tests/conformance/test_deploy_perimeter.py` -- every I/O-matrix row plus verb dispatch through `DeployDuty.run`

**Acceptance Criteria:**
- Given `worker_count=1` and any cache/channel-layer backend, when `check_shareable_state` runs, then it passes without raising.
- Given `worker_count>1` and a backend not on the Redis-backed allowlist, when `check_shareable_state` runs, then it raises `UnshareableStateError` naming the offending field.
- Given a topology that fails the check, when `steward deploy perimeter` runs, then it returns `DutyResult(ok=False, ...)` naming the refusal and writes no files.
- Given a topology that passes and `--output-dir` is supplied, when `steward deploy perimeter` runs, then a daphne unit file and an nginx edge config are written there, the nginx config sets TLS directives and restricts access to the supplied trusted addresses.
- Given the whole `pyforge-steward` package, when `tests/meta/test_invariants.py` runs, then the `[dashboard]` extra and pixi.toml's feature pins for `channels`/`daphne`/`asgiref`/`channels_redis` are confirmed byte-identical, and `deploy.py` still imports nothing from `pyforge.steward.dashboard`.

## Spec Change Log

## Review Triage Log

### 2026-08-12 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 1, medium 5, low 6)
- defer: 0
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[high]` `[patch]` `render_edge_config` validated only emptiness on `trusted_addresses`/`tls_cert`/`tls_key`/`server_name`, so a crafted value (embedded `;`, `{`, `}`, or any whitespace) could inject an arbitrary extra directive into the rendered security-perimeter config — fixed with a shared `_validate_nginx_value` guard (reject empty, whitespace-anywhere, or unsafe-character values) applied to every interpolated field; pinned by 6 new parametrized cases.
  - `[medium]` `[patch]` `_SHAREABLE_CACHE_BACKENDS` allowlisted `django_redis.cache.RedisCache` with no corresponding dependency (`django-redis`) declared anywhere in the extra or pixi.toml, so a passing `check_shareable_state` gave false confidence about an unsatisfiable backend — narrowed to only Django's built-in `RedisCache` (whose `redis` client is already transitively satisfied via `channels_redis`); the existing "also passes" test converted to assert refusal instead.
  - `[medium]` `[patch]` the rendered nginx config hardcoded `Connection: upgrade` on every request, not only real WebSocket upgrades — fixed with the standard `map $http_upgrade $connection_upgrade` idiom; pinned by a new test.
  - `[medium]` `[patch]` the rendered nginx config had no `proxy_read_timeout`/`proxy_send_timeout` override, so nginx's ~60s default would silently drop the long-lived Channels WebSocket connections this pattern exists to carry — fixed with an explicit 24h override; pinned by a new test.
  - `[medium]` `[patch]` `DeploymentTopology.worker_count` only checked `> 0`, so a large value could push `base_port + worker_count` past the valid port range with no error — fixed with a range check in `_worker_ports` (the single source both render functions already read); pinned by a new test.
  - `[medium]` `[patch]` `_run_perimeter` wrote the daphne unit and nginx config directly to their final filenames, so a second-file write failure left the first file on disk despite reporting `ok=False` — fixed by writing both to temp names and renaming both only after both writes succeed (atomic on POSIX), with best-effort cleanup on failure.
  - `[low]` `[patch]` `DeploymentTopology.cache_backend`/`channel_layer_backend` only rejected emptiness, not padding, so a padded-but-otherwise-valid dotted path silently mismatched `check_shareable_state`'s exact-match allowlist — fixed by rejecting leading/trailing whitespace, mirroring `declarations.py`'s established convention; pinned by 2 new parametrized cases.
  - `[low]` `[patch]` `_run_perimeter`'s documented `OSError` path (an unwritable `--output-dir`) had zero test coverage — added a test exercising it.
  - `[low]` `[patch]` `ns.workers`/`.cache_backend`/`.channel_layer_backend` were accessed directly (unlike the `getattr`-guarded optional fields), so an incomplete `Namespace` raised an uncaught `AttributeError`, contradicting the function's own "never an uncaught crash" docstring — fixed by widening the except clause; pinned by a new test. The same widened handling also now covers a `ValueError` raised by the render functions themselves (the new port-range and nginx-value checks above), which the original code path left uncaught.
  - `[low]` `[patch]` the generalized pin-sync test's `pixi_deps[pkg_name]` lookup would raise a raw `KeyError` (instead of a clear assertion) if a package were ever present in the extra but missing from pixi.toml — fixed with an explicit membership assertion first.
  - `[low]` `[patch]` the top-level `deploy` duty's help string ("dashboard build/reconcile/status, dashboard-app deployment perimeter") read as an awkward run-on — reworded for clarity.

Rejected as noise (all low/non-issues, verified independently): claimed missing `environment.yaml` regeneration (false — the `build` env doesn't include the `pyforge-steward` feature, so no diff was ever expected; regeneration was in fact run) and missing `pixi.lock` update (false — `pixi.lock` WAS modified; it was deliberately excluded from the reviewed diff as a generated file); comments asserting unmechanized cross-file facts about recipe/architecture versions (matches this codebase's pervasive existing convention of comment-only claims, not a defect unique to this story); the allowlist's exact-string match refusing a project-specific subclass of an allowlisted backend (an already-documented, deliberate design choice with its own rationale in code); single-worker-safe default backend strings duplicated between `cli.py` and the test file (normal same-package/same-PR practice, not the cross-file drift class the pin-sync mechanism exists for); the package-name regex not normalizing PEP 503 hyphen/underscore/dot spelling variants (hypothetical — the five names are author-controlled literals within one file, not external input); an unconfirmed claim that `Sequence` might be unimported in `deploy.py` (false — already imported, verified independently). One additional Blind Hunter finding (an "extra blank line" before `_add_provision_subparsers`) was also verified false: the file's own established convention is 2 blank lines between top-level `def`s, and the diff already matched it.

### 2026-08-12 — Review pass 2 (follow-up, requested by pass 1)
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 3, low 1)
- defer: 4: (high 0, medium 0, low 4)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` `_run_perimeter`'s final `unit_tmp.rename(unit_path)`/`edge_tmp.rename(edge_path)` calls sat OUTSIDE the `try/except OSError` guard, contradicting the function's own documented "a filesystem failure ... is caught as OSError and reported the same way, never propagated as an internal crash" — independently found by both Blind Hunter and Edge Case Hunter. Fixed by widening the guard to cover both renames, with best-effort cleanup of any still-temp file; pinned by a new test that makes the second rename target an existing directory.
  - `[medium]` `[patch]` `_UNSAFE_NGINX_VALUE_CHARS` (`;{}`  ) omitted `#` (starts a same-line nginx comment, truncating the directive it lands in) and `$` (triggers nginx variable interpolation in most directive contexts, including modern `ssl_certificate`/`ssl_certificate_key`) — independently found by both reviewers for `#`. Widened to `;{}#$`; pinned by 2 new parametrized cases.
  - `[medium]` `[patch]` `test_dashboard_extra_pins_match_pixi_feature_pins` looped over a hardcoded 5-name tuple with no assertion that the `[dashboard]` extra actually contains only those 5 entries, so a 6th dependency added to the extra in a later story would drift out of this SPEC's own byte-identical-pin constraint completely undetected — fixed with a `len(extra) == len(checked_names)` completeness assertion before the per-name loop.
  - `[low]` `[patch]` `_run_perimeter`'s validation-only branch (no `--output-dir`) reported `ok=True` "topology valid" without ever calling `_worker_ports`, so an extreme `--workers` value past the port-range bound reported a "valid" verdict that would then fail once `--output-dir` was added later — fixed by validating the same port range in the shared try block so both branches agree on what "valid" means; pinned by a new test.
  - defer: `DW-FU-9-5` (no `--base-port`/`--bind-host` CLI flags, so `_worker_ports`'s lower-bound and `_validate_nginx_value`'s injection guard are both unreachable for those two parameters from the shipped CLI — 3 combined findings: 1 from Blind Hunter, 2 from Edge Case Hunter) and `DW-FU-9-5-2` (hardcoded systemd unit / nginx upstream names assume one deployment per host, from Blind Hunter) appended to the Tier-3 deferred-work ledger — both are scope additions beyond this story's frozen Code Map, not defects in what it promises.

Rejected as noise (all low/non-issues, verified independently): concurrent `--output-dir` invocations to the same directory racing on deterministic temp filenames (this is a human/CI-invoked one-shot rendering tool with no stated concurrency requirement anywhere in this story's scope; two overlapping invocations against the same directory is operator error, not a defect in the reasonable usage envelope); `render_daphne_unit`/`render_edge_config` not internally re-calling `check_shareable_state` (deliberate separation of concerns — the render functions are pure string builders, `_run_perimeter` is the one orchestration point responsible for validation ordering, matching this package's established Duty pattern); `--trusted-address` accepting non-IP/CIDR strings and TLS cert/key paths never checked for existence (both explicitly out of scope — this story renders static manifest text only, and the tool may run on a machine other than the eventual production target where those files/addresses will actually resolve); the unfilled `_ASGI_APPLICATION_PLACEHOLDER` not being validated as replaced (an explicit, documented judgment call in the Design Notes — the adopter hand-edits it like any systemd unit before enabling); the `except (TypeError, ValueError, AttributeError)` around both `DeploymentTopology` construction and `check_shareable_state` being "too broad" (already a deliberate, reviewed widening from pass 1's own `AttributeError` fix; the hypothetical it guards against — a future typo inside `check_shareable_state` — does not exist today); `trusted_addresses: Sequence[str]` being iterated twice (a one-shot generator would exhaust on the first pass, but `Sequence` is not `Iterator` — passing a generator already violates the function's own type contract, and every real caller in this codebase passes a tuple); a non-string `tls_cert`/`tls_key` passed directly to `render_edge_config` raising `AttributeError` instead of the documented `ValueError` (same type-contract-violation class, and unreachable via `_run_perimeter`'s own CLI path since emptiness is already guarded before that call).

## Design Notes

**Why the topology/manifest logic lives in `deploy.py`, not a new `dashboard/` module.**
AD-1 classifies "runtime scaffold, edge policy, ASGI topology... wiring verification" as
out-of-process concerns that ship as the `steward deploy` subcommand, and the existing
import-boundary invariant already forbids `deploy.py` from importing anything under
`dashboard/` — even a django-free submodule, as Story 9.4's Design Notes established for the
same reason. Keeping this story's code in `deploy.py` avoids inventing a second boundary rule
and mirrors `deploy.py`'s own "Epic 2's single file, one module per duty" precedent.

**Why an allowlist, not a denylist, for shareable backends.** `cache.py`'s own docstring is
explicit that `FileBasedCache` and `DatabaseCache` have real but subtle failure modes under
contention (unlocked check-then-set; silent `add()` failures), and only a Redis-backed store
and `LocMemCache`(single-process only) have documented, unambiguous behavior. Rather than
adjudicate every Django cache backend's cross-process semantics, this story allowlists the one
backend the architecture itself names as sanctioned (`channels_redis`) and its cache
counterpart, refusing everything else under `worker_count > 1` — consistent with this
package's established "fail loudly on anything not explicitly known-good" style
(`declarations.py`, `middleware.py`).

**Manifests are rendered as strings, not template files.** No package-data/asset-packaging
precedent exists in this repo for `pyforge-steward`; `render_daphne_unit()`/`render_edge_config()`
return plain strings built from the topology's fields, avoiding new packaging plumbing for a
story of this size. The CLI verb writes them to `--output-dir` when given.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary.** Resumed an `in-progress` spec whose implementation (commit `a691c547265ccf9636c7fd1dd5a01fd4f360da87`) was already complete and had already been through Review pass 1, but failed bmad-loop's own deterministic S-13.2 spec-surface drift gate (`scripts/spec_surface_reconcile.py`): 5 files under `spec-pyforge-steward`'s governed package-path surface had changed without that Spec's own `.memlog.md` naming them. Repaired by appending a `(change) RECONCILES ...` bullet to `spec-pyforge-steward/.memlog.md` (matching the established Story 9.1 precedent for the same mechanism), then ran the follow-up review pass this spec's frontmatter had already flagged as recommended.

**Files changed this session:**
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` -- new reconciliation entry naming this story's 5 governed-surface files, per S-13.2 (commit `86849d17dc`).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` -- Review pass 2: widened the `--output-dir` write guard to also cover the two final `rename()` calls; widened `_UNSAFE_NGINX_VALUE_CHARS` to include `#`/`$`; validation-only mode now also validates the port range via `_worker_ports`.
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_perimeter.py` -- Review pass 2: 2 new parametrized injection cases (`#`, `$`), a rename-failure refusal test, a validation-only port-overflow refusal test.
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` -- Review pass 2: added a completeness assertion (`len(extra) == len(checked_names)`) to the generalized pin-sync test.
- `_bmad-output/projects/pyforge-steward/implementation-artifacts/deferred-work.md` -- 2 new Tier-3 entries, `DW-FU-9-5` and `DW-FU-9-5-2`.

**Review findings breakdown (pass 2, follow-up):** 4 patches applied (0 high / 3 medium / 1 low), 4 findings deferred to 2 ledger entries (all low), 8 findings rejected as noise (all low; see Review Triage Log for the per-finding rationale). No intent_gap, no bad_spec.

**Follow-up review recommendation:** `false`. Pass 2's patches were narrowly scoped, mechanical fixes (widen an existing exception guard, widen an existing character denylist, add one validation call, add one completeness assertion) with no new capability, no API/behavior change beyond making documented guarantees actually hold, and no security-relevant scope expansion — not significant enough in volume or consequence to warrant another independent pass.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- exit 0, `OK: every tracked file governed or allowlisted; no drift.`
- `pixi run -e pyforge-steward pyforge-steward-test` -- 443 passed (439 baseline + 4 new tests from pass 2).
- `pixi run -e pyforge-steward steward --version` -- `steward 0.1.0`, exit 0.
- `pixi install -e pyforge-steward` -- environment installs cleanly with the four new pins.
- `ruff check` on all 3 touched Python files -- identical pre-existing 8-finding baseline (verified via `git stash`), zero findings introduced by this session's changes.

**Residual risks:** `DW-FU-9-5`/`DW-FU-9-5-2` (deferred, see ledger) — no CLI override for the daphne/nginx base port or bind host, and hardcoded manifest/upstream names that would collide across two perimeter deployments to the same host. Both are scope additions beyond this story's frozen Code Map, not defects in what it currently promises. The two-file rename in `_run_perimeter` still cannot be made fully atomic across both files (if the second rename fails after the first succeeds, the newly cleaned-up temp file is removed but the first file's rename is not rolled back) — the fix in this pass converts an uncaught crash into a named refusal but does not add multi-file transactional rollback, which would require backing up any pre-existing content at the target paths and was judged out of this pass's scope.
