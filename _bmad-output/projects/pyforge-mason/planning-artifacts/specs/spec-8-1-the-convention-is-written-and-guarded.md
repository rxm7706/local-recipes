---
title: 'The convention is written and guarded'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: 'cb6e587411f94a6073409fc3c44189b0d846ff12'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/Containerfile'
  - '{project-root}/src/platform/Containerfile'
  - '{project-root}/src/platform/compose/dbgpt/Containerfile'
  - '{project-root}/tests/packaging/test_containerfile_checkout_path.py'
  - '{project-root}/scripts/pixi_version_registry.py'
  - '{project-root}/docs/reference/README.md'
  - '{project-root}/docs/dreams/pixi-container-image.md'
  - '{project-root}/_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pixi-container-image/SPEC.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The repo ships three Containerfiles (root, `src/platform/`, `src/platform/compose/dbgpt/`) that already converge on the same base-layer pattern by accident of independent authorship, but nothing documents that convention as policy or catches a future drift from it (an unpinned base image, or a credential leaked via `ENV`/a baked layer instead of `--mount=type=secret`).

**Approach:** Write one convention doc naming the three pillars (registry-pinned base tags on every stage, the multi-stage pixi-materialization shape, the `--mount=type=secret`-only credential rule) and one guard test that statically greps all three Containerfiles for the two anti-patterns, proven to actually fire via synthetic-regression cases. Correct the owning Dream's now-stale "nothing exists yet" premise in place.

## Boundaries & Constraints

**Always:**
- Cover all three Containerfiles in both the doc and the guard test — no partial coverage.
- Write the guard test as pure stdlib (`re` + `pathlib` + `pytest`), mirroring `tests/packaging/test_containerfile_checkout_path.py`'s own stated rationale: it must run in the lean `pyforge-ci` env, which has zero runtime libraries installed.
- Include synthetic-regression test cases that prove each anti-pattern check actually fails when tripped — not just that the always-correct real files pass. `test_containerfile_checkout_path.py`'s own docstring records this repo's precedent for a guard whose failure branch was never exercised and shipped a broken assertion unnoticed; do not repeat that.
- State three things explicitly in the convention doc: (1) every `FROM` in every stage of every Containerfile must carry an explicit, non-floating tag — never bare/untagged (Docker defaults that to `:latest`), never `:latest` literally; (2) the multi-stage pixi-materialization shape — a pixi builder stage (`pixi install --frozen -e <env>` + `pixi shell-hook -e <env> -s bash`) followed by a minimal runtime stage that copies only the materialized env + activation hook, never the pixi binary itself; (3) the credential rule — build-time secrets cross the build boundary only via `--mount=type=secret`, read inline, never baked into a layer, `ENV`, or `COPY`.
- Correct `docs/dreams/pixi-container-image.md`'s stale premise in place: its "## What is real" section currently says no Dockerfile/Containerfile exists anywhere, and "## Constraints" says the base image is "not to be built until a real containerized artifact exists" — both predate the three Containerfiles that now ship. Append a dated Realization log entry recording the correction; never delete or rewrite prior log entries.
- Add the new doc to `docs/reference/README.md`'s bullet index, matching that file's existing entry style.

**Block If:**
- A fourth Containerfile-like file is found anywhere in the repo's tracked source beyond the three named ones — HALT; scope is fixed at exactly these three per the owning spec, and a 4th needs scope confirmation before the guard test's "all Containerfiles" claim can be trusted.
- The `ENV`-credential deny-list pattern cannot be written without a plausible false-positive against the three real Containerfiles' actual non-secret `ENV` lines (e.g. `HOME`, `DJANGO_SETTINGS_MODULE`) without narrowing the pattern in a way that reopens a real gap — HALT rather than silently weakening the check.

**Never:**
- Do not add a new base image build or publish step — the upstream `ghcr.io/prefix-dev/pixi` image stays the base.
- Do not modify `scripts/pixi_version_registry.py`'s site list or behavior — it already enforces the pixi-builder-stage tag staying in sync with `pixi.toml`'s `requires-pixi` floor; this story's guard test is additive (it also checks runtime-stage bases and the credential rule), not a replacement.
- Do not touch Mason's own `docker`-mode recipe-build isolation path (`cfe.py`'s `build_docker`) — an explicitly different concern per the Dream's own text (recipe cross-compilation, not a shipped application container).
- Do not add multi-arch support.
- Do not modify `.dockerignore`, `pixi.toml`, or any `.github/workflows/*.yml` — the new test file is auto-discovered by the existing `python -m pytest tests/packaging -q` command (pixi task `pyforge-deps-test` in `[feature.pyforge-ci.tasks]`); no wiring change is needed.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real repo state | The three real Containerfiles as committed today | Guard test passes — every `FROM` pinned to an explicit non-`latest` tag, no `ENV` line matches the credential deny-list | No error expected |
| Planted unpinned base | A synthetic `FROM` line with no tag, or `:latest` | Guard logic fails, identifying the offending line/value | Assertion names the offending file/line/value |
| Planted ENV credential | A synthetic `ENV` line whose key matches a credential-shaped name (e.g. `API_KEY`, `PASSWORD`, `SECRET`, `TOKEN`) | Guard logic fails, identifying the offending line/value | Assertion names the offending file/line/value |
| Guard vacuity | The parsing regex stops matching anything (e.g. a future malformed edit) | A dedicated "discovery is not vacuous" test fails rather than the suite passing having checked nothing | Assertion names the expected minimum match count |

</intent-contract>

## Code Map

- `Containerfile` -- root Containerfile; builder stage `FROM --platform=linux/amd64 ghcr.io/prefix-dev/pixi:0.77.0 AS builder`, runtime `FROM --platform=linux/amd64 ubuntu:24.04`; no `ENV` directives present today.
- `src/platform/Containerfile` -- same pixi-builder pattern; runtime `FROM --platform=linux/amd64 registry.access.redhat.com/ubi9/ubi-minimal:9.6 AS runtime`; has `ENV HOME=/app/.home` and `ENV DJANGO_SETTINGS_MODULE=config.settings.production` (both non-credential; the deny-list must not flag these).
- `src/platform/compose/dbgpt/Containerfile` -- same pixi-builder pattern; runtime `FROM --platform=linux/amd64 registry.access.redhat.com/ubi9/ubi-minimal:9.6 AS runtime`; has `ENV HOME=/app/.home` (non-credential).
- `scripts/pixi_version_registry.py` -- existing, separate mechanism: `SITES` tuple already includes all three Containerfiles' builder-stage `ghcr.io/prefix-dev/pixi:<version> AS builder` lines, checked against `pixi.toml`'s `requires-pixi` floor by `pixi-version-check`. This story's guard test is complementary (covers ALL `FROM` lines including runtime-stage bases, plus the `ENV`-credential rule); it must not duplicate or replace this file.
- `tests/packaging/test_containerfile_checkout_path.py` -- the pattern to mirror exactly: module docstring explaining rationale, `REPO_ROOT`/`CONTAINERFILE` constants, a compiled line-regex, a "discovery is not vacuous" test, positive assertions against the real file, and a `@pytest.mark.parametrize`d synthetic-regression test that drives the same regex/logic against strings never written to disk.
- `tests/packaging/` -- directory; `pixi.toml`'s `[feature.pyforge-ci.tasks.pyforge-deps-test]` runs `python -m pytest tests/packaging -q`; a new `test_*.py` file here is auto-discovered, no task/CI change required.
- `docs/reference/README.md` -- curated bullet-list index of `docs/reference/*.md`; add one bullet for the new file, same style as existing entries.
- `docs/dreams/pixi-container-image.md` -- owning Dream. "## What is real" (currently: "Nothing. No Dockerfile exists anywhere in this repo's own tracked source...") and "## Constraints" (currently: "Not to be built until a real containerized artifact exists") are stale; "## Realization log" is the append-only section to extend with a dated correction entry, matching its existing entries' style (bold date, em-dash, prose).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pixi-container-image/SPEC.md` -- the owning spec (CAP-1, Constraints, Non-goals, Success signal) this story implements; read-only reference, do not edit.

## Tasks & Acceptance

**Execution:**
- `docs/reference/container-base-layer-convention.md` -- CREATE -- document the one convention (base-tag pinning on every stage of every Containerfile, the multi-stage pixi-materialization shape, the `--mount=type=secret`-only credential rule), naming all three Containerfiles by relative path and stating that `scripts/pixi_version_registry.py` (builder-tag/floor sync) and the new `tests/packaging` guard test (full `FROM`/`ENV` sweep) together enforce it.
- `docs/reference/README.md` -- EDIT -- add one bullet for the new doc.
- `tests/packaging/test_containerfile_base_layer_convention.py` -- CREATE -- pure-stdlib pytest module mirroring `test_containerfile_checkout_path.py`'s structure: parse all three Containerfiles' `FROM` lines (image ref + tag, tolerating a leading `--platform=...` flag and a trailing `AS <name>`) and `ENV` lines (key only); assert every `FROM` carries an explicit non-`latest` tag; assert no `ENV` key matches a credential-shaped deny-list (case-insensitive substrings: `PASSWORD`, `SECRET`, `TOKEN`, `API_KEY`, `APIKEY`, `PRIVATE_KEY`, `ACCESS_KEY`, `CREDENTIAL`); include a "discovery is not vacuous" test; include parametrized synthetic-regression tests proving both the unpinned-base and the ENV-credential checks fire on inputs never written to disk.
- `docs/dreams/pixi-container-image.md` -- EDIT -- correct "## What is real" and "## Constraints" to state the trigger fired (three Containerfiles ship today) and point at the new convention doc + guard test; append one dated Realization log entry recording the correction; leave all prior entries untouched.

**Acceptance Criteria:**
- Given the three real Containerfiles as committed today, when `python -m pytest tests/packaging -q` runs, then it passes, including every case in the new file, with no existing test regressed.
- Given a synthetic Containerfile-shaped `FROM` line with no tag or with `:latest`, when the new test's guard logic runs against it directly, then it fails, naming the offending value.
- Given a synthetic Containerfile-shaped `ENV` line with a credential-shaped key, when the new test's guard logic runs against it directly, then it fails, naming the offending value.
- Given `docs/reference/container-base-layer-convention.md`, when read, then it names all three Containerfiles by path and states all three convention pillars explicitly.
- Given `docs/dreams/pixi-container-image.md` after the edit, when read, then "## What is real" no longer states that no Dockerfile/Containerfile exists, and a new dated Realization log entry records the correction alongside (not replacing) the prior entries.

## Spec Change Log

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 3, low 2)
- defer: 0
- reject: 11: (high 0, medium 0, low 11)
- addressed_findings:
  - `[medium]` `[patch]` docs/dreams/pixi-container-image.md: "## The Dream" and "## What it looks like when real" sections still asserted the pre-correction premise ("no PyForge artifact currently ships as a container" / describing containerization as purely hypothetical), contradicting the corrected "## What is real"/"## Constraints" sections in the same file. Extend the correction to those two sections for internal consistency.
  - `[medium]` `[patch]` tests/packaging/test_containerfile_base_layer_convention.py: `ENV_LINE_RE` only captures the first key on a Docker multi-variable `ENV key1=val1 key2=val2` directive (confirmed live by the verification-gap reviewer), so a credential-shaped key placed after the first on such a line would evade `test_no_env_key_is_credential_shaped` undetected. Extend `_env_directives()` to extract every key on an `ENV` line.
  - `[medium]` `[patch]` tests/packaging/test_containerfile_base_layer_convention.py: `_is_unpinned` does not flag an empty-string tag (e.g. a malformed `FROM ubuntu:` with a trailing bare colon) as unpinned -- `tag is None or tag.lower() == "latest"` is `False` for `tag == ""`. Treat a falsy tag the same as `None`.
  - `[low]` `[patch]` tests/packaging/test_containerfile_base_layer_convention.py: `FROM <previous-stage-name> AS <new-stage>` (Docker's valid stage-reuse pattern) has no `:tag` and would be false-positived as unpinned by `test_every_from_has_an_explicit_non_latest_tag`. Not exercised by any of the three real Containerfiles today, but cheap to close now: collect every `AS <name>` declared earlier in the same file and exclude a `FROM <name>` that references one.
  - `[low]` `[patch]` docs/reference/container-base-layer-convention.md: pillar 3's "the two non-secret `ENV` lines that do exist" phrasing is ambiguous against the test file's `MIN_EXPECTED_ENV_LINES = 3` comment (2 distinct variable names across 3 total directive occurrences, not 2 lines). Reword for clarity.

## Design Notes

The guard test is a static text scan over the Containerfiles as committed — it is not a build-time or runtime check. `scripts/container-gates secrets-scan` (already wired into all three Containerfiles as a `RUN` step) proves no credential-shaped content ships in a built layer; this story's test is a different, complementary layer that catches an `ENV`-declared credential (or an unpinned base) at review time, before any `docker build` runs. Do not conflate the two or try to unify them — they check different things at different times, and `scripts/pixi_version_registry.py` already documents itself as a third, single-purpose mechanism (pixi-tag/floor sync only). Three separate, narrow checks are the existing pattern in this repo; keep it that way rather than merging them into one.

`ARG` is out of scope for the credential deny-list: none of the three Containerfiles use `ARG` for anything credential-shaped today (the one `ARG`-adjacent thing, `--platform=linux/amd64`, is a `FROM` flag, not a separate directive), and the spec's own credential rule names `ENV`/layers specifically, mirroring `docs/dreams/pixi-container-image.md`'s own Realization log wording ("never ENV, never COPY, never persisted in any layer").

## Verification

**Commands:**
- `python -m pytest tests/packaging -q` -- expected: all tests pass, including every new test in `test_containerfile_base_layer_convention.py`, with the same or greater total test count as before this change.
- `python -m pytest tests/packaging/test_containerfile_base_layer_convention.py -v` -- expected: all tests pass, including the parametrized synthetic-regression cases (visible individually with `-v`).

**Manual checks (if no CLI):**
- Read `docs/reference/container-base-layer-convention.md` and confirm it names all three Containerfiles by relative path and states the base-tag-pinning, multi-stage-materialization, and `--mount=type=secret`-only rules explicitly.
- Read `docs/reference/README.md` and confirm the new file is listed in the bullet index.
- Read `docs/dreams/pixi-container-image.md` and confirm "## What is real" and "## Constraints" reflect the three shipped Containerfiles, with a new dated Realization log entry appended after the existing ones.

## Auto Run Result

**Summary:** Documented the base-layer convention shared by this repo's three Containerfiles
(registry-pinned base tags on every stage, the multi-stage pixi-materialization shape, and the
`--mount=type=secret`-only credential rule) and added a static guard test that reds on a planted
ENV-credential or unpinned base across all three files. Corrected the owning Dream's stale
"nothing exists yet" premise in place.

**Files changed:**
- `docs/reference/container-base-layer-convention.md` (new) -- the convention doc; three pillars,
  an Enforcement section, a Scope note.
- `tests/packaging/test_containerfile_base_layer_convention.py` (new) -- pure-stdlib pytest guard
  mirroring `test_containerfile_checkout_path.py`'s pattern; 21 tests incl. synthetic-regression
  coverage for every failure branch (unpinned base, empty tag, stage-name-reuse exemption, ENV
  credential incl. multi-key lines).
- `docs/reference/README.md` -- added the new doc to the bullet index.
- `docs/dreams/pixi-container-image.md` -- corrected "What is real"/"Constraints"/"The Dream"/"What
  it looks like when real"/the feature-audit table row to state the trigger fired (three
  Containerfiles ship); appended a dated Realization log entry; all prior entries and every other
  section left untouched.

**Review findings breakdown:** 4 review layers ran (Blind Hunter, Edge Case Hunter,
Verification-Gap, Intent-Alignment). 16 total findings after dedup: 5 patched (3 medium: Dream
internal-consistency gap, ENV multi-key parsing gap, empty-tag pin-check bug; 2 low: FROM
stage-name-reuse false positive, ambiguous ENV-count wording), 0 deferred, 11 rejected (deliberate
scope choices already justified in the spec's own Design Notes / Block-If clauses, or matching an
established sibling-file precedent, or explicitly out of this dispatch's scope per the dispatching
session's own instructions -- see Review Triage Log for the full breakdown). One additional
inconsistency found during this HALT's own independent re-verification (not from the 4 review
layers): the Dream's "Full feature audit" table row 1 still read "No PyForge artifact ships as a
container," contradicting the corrected "What is real" section three paragraphs above -- fixed
directly.

**Follow-up review recommendation:** `true` (3 medium x 3 + 2 low x 1 = 11 >= 5). All 5 patches
have already been applied and re-verified in this same pass, so a follow-up pass is a
belt-and-suspenders check, not a known-outstanding gap.

**Verification performed:**
- `pixi run -e pyforge-ci python -m pytest tests/packaging/test_containerfile_base_layer_convention.py -v`
  -- 21/21 pass, independently re-run after all patches (was 18/21 before; 3 new cases added by
  the patches).
- `pixi run -e pyforge-ci python -m pytest tests/packaging -q` -- 103 passed, 2 failed
  (`pyforge-herald`/`python-pptx` dependency-completeness gap), independently re-run and confirmed
  via the pre-existing baseline (same 2 failures present before this story's changes) -- no
  regression.
- Manually read `docs/reference/container-base-layer-convention.md`, `docs/reference/README.md`,
  and the full `docs/dreams/pixi-container-image.md` diff end-to-end (twice: once after the
  original implementation, once after the patch round) to confirm content accuracy and internal
  consistency.

**Residual risks:** None blocking. Two narrow, explicitly-scoped gaps remain by design (documented
in the convention doc and test docstrings, not hidden): (1) the multi-stage-materialization pillar
(pillar 2) is not mechanically checked, only documented -- a structural property, not a grep; (2)
the ENV-credential deny-list only inspects `ENV` directives, not `ARG`/`COPY`/other layer content --
matches the AC's literal "reds on a planted ENV-credential" wording. The sprint-status ledger and
the SPEC's own status field are intentionally not touched here, per this dispatch's explicit
instructions (a separate coordinating-session step).
