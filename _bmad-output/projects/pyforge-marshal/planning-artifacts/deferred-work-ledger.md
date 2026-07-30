---
doc_type: deferred-work-ledger
project: pyforge-marshal
date: 2026-07-29
status: promoted-verbatim
---

# pyforge-marshal — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-29 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown, and this repo has already lost data that way
(pyforge-atlas's live ledger is still truncated to 11 of 64 entries, collateral of the
2026-07-19 copy failure). Until today this project had **no tracked ledger at all**, so
its entire deferred-work record — 4 KB — existed only in
scratch space. Found by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current. The one intentional edit is
id renaming, below.

Durability first; curation is owned follow-up work.

## Ids renamed on promotion

- `DW-1` → **`DW-FU-1-1`** (story `1-1-package-spine-verdict-lattice-findings-registry…`) — bmad-loop emits a bare
  `DW-<n>` per run, which collides with the next damped story; renamed on promotion.

---

# Deferred Work

> **Re-reconciled 2026-07-29 against conda-forge-expert v8.81.0** (Round-4 code-audit
> remediation). Each entry re-checked against the live tree; **1 of 5 is resolved, 4 stand**:
>
> - **`pixi build --manifest-path` (entry 1) — RESOLVED, and not by this pass.** The root
>   `pixi.toml` tasks already target the member package by `cwd` rather than the missing
>   flag (`pyforge-{mason,steward}-build-conda`, with the reason in an inline comment), so
>   the tasks the entry describes as failing do not fail. Re-verified against the newly
>   floored pixi **0.74.0**: `pixi build --help` still exposes only `--path`, no
>   `--manifest-path`, so the `cwd` workaround remains the correct shape rather than
>   something to revert. The entry described already-fixed code.
> - **Inline `.gitignore` comments (entry 2) — STILL OPEN, confirmed live.**
>   `pyforge-doctor/.gitignore` and `pyforge-warden/.gitignore` both still read
>   `/dist/          # pypi: wheel + sdist (...)`; gitignore has no trailing-comment
>   syntax, so both patterns remain dead and those directories are not ignored.
> - **Missing package LICENSE files (entry 3) — STILL OPEN.** `ls src/shared/packages/*/LICENSE*`
>   returns nothing while every sibling `pyproject.toml` declares MIT.
> - **DW-1 / DW-FU-1-1 follow-up review — STILL OPEN.** Unchanged.
>
> Nothing was re-severitied and nothing was closed in place: the one resolved entry is
> recorded as resolved-by-prior-work, not claimed by this pass.

> **Promotion pass 2026-07-30** — the Epic-1 continuation run (stories 1.2 / 1.3 / 1.10,
> bmad-loop run 20260730-001132-58f6) left 12 entries in the gitignored Tier-3 file that
> `deferred-work-check` flagged as `tier3-only-deferral`. Promoted here verbatim: bodies are
> unedited and nothing was re-severitied, per this ledger's standing copy-not-curation rule.
> The one change is the id — bare `DW-2` became `DW-FU-1-3`, because bmad-loop emits a generic
> per-run id that the next damped story would collide with.
>
> **Two entries were RESOLVED by the work in the same commit range, and are recorded as
> resolved rather than edited in place:**
>
> - *"No project-policy source anywhere in the repo currently supplies `gate_mode="none"` or
>   `max_followup_reviews=2`"* (Story 1.10 review) — **RESOLVED.** Nine tracked
>   `planning-artifacts/marshal-policy.toml` station layers now supply `gate_mode = "none"` and
>   per-station `verify_commands`, and `marshal config --write-harness-policy` plus convention
>   lookup give them a caller. Verified live: all nine render `gate=none`, `fu=2`.
> - *"restoring `max_followup_reviews = 2` via pyforge-marshal's project-policy layer alone
>   under-scopes the fix … the only homes for a repo-wide seed value are Marshal's
>   `DEFAULT_POLICY` or the global custom layer"* (Story 1.10 follow-up review) — **RESOLVED,
>   and it corrected this session's first attempt.** The nine layers each restated
>   `max_followup_reviews = 2`; that is nine copies of one repo-wide decision, exactly what the
>   finding warned against. The key was moved to `DEFAULT_POLICY` and dropped from every layer.
>   Composition provenance now reports `max_followup_reviews: 2 (layer=default)`, and a new
>   station inherits it instead of having to remember it.

## DW-1-1-1 — The `pyforge-mason`, `pyforge-steward`, and `pyforge-warden` `*-build-conda` pixi tasks (root `p…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: The `pyforge-mason`, `pyforge-steward`, and `pyforge-warden` `*-build-conda` pixi tasks (root `pixi.toml`) invoke `pixi build --manifest-path ...`, a flag the installed pixi (0.73.0) does not have (`pixi build --help` only exposes `--path`), so all three tasks fail when run.
  evidence: Confirmed live against the installed `pixi build --help` output while implementing Story 1.1's own `pyforge-marshal-build-conda` task, which mirrors the same block but was written with `--path` instead to avoid propagating the bug. Pre-existing in already-merged code; outside this story's declared surface (`src/shared/packages/pyforge-marshal/**` + root `pixi.toml` additions only).

  status: done 2026-07-30

  verified: 2026-07-30 — ALREADY RESOLVED, confirming the 2026-07-29 header note by measurement: `--manifest-path` appears exactly 3 times in the root `pixi.toml` and ALL THREE are inside comments (`:142`, `:171`, `:206`) — zero occurrences in any `cmd =`. mason (`:141-142`) and steward (`:170-171`) target the member by `cwd`; marshal (`:210`) uses `--path`. SIDE FINDING, worth its own cleanup: the surviving comments are now factually wrong. `:206-209` still asserts 'the pyforge-steward block this mirrors uses `--manifest-path` … steward's own build-conda task fails identically' — steward was fixed at `:170-171`, so that NOTE now libels working code. `:142`/`:171` also still cite pixi '0.73.0' against a repo floor of 0.75.0.

## DW-1-1-2 — `pyforge-doctor` and `pyforge-warden`'s package `.gitignore` files put comments inline after the…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: `pyforge-doctor` and `pyforge-warden`'s package `.gitignore` files put comments inline after the `/dist/` and `/dist-conda/` patterns; gitignore has no trailing-comment syntax, so both patterns are dead and those directories are not ignored (steward/mason use bare lines and are fine; marshal's copy of the same defect was fixed in this story's review pass).
  evidence: Reproduced live during the Story 1.1 review — probe files created under `pyforge-marshal/dist/` appeared as untracked until the comments were moved to their own lines; doctor's and warden's `.gitignore` are byte-identical to the pre-fix marshal file. Pre-existing in already-merged sibling packages, outside this story's surface.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN and WIDER than recorded — the entry named doctor and warden; it is now FOUR packages. `pyforge-warden/.gitignore:2-3`, `pyforge-doctor/.gitignore:2-3`, `pyforge-scribe/.gitignore:2-3` and `pyforge-herald/.gitignore:2-3` all carry the trailing-comment form `/dist/          # pypi: wheel + sdist (python -m build)`. gitignore has no trailing-comment syntax, so all eight patterns are dead. marshal (`:6-7`) and atlas (`:6`) use bare lines and are clean — the defect spread to scribe and herald by the same clone-the-sibling route that created it.

## DW-1-1-3 — Every pyforge sibling package (doctor, warden, steward, mason, and now marshal) declares `licens…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: Every pyforge sibling package (doctor, warden, steward, mason, and now marshal) declares `license = { text = "MIT" }` in `pyproject.toml` but ships no LICENSE file in the package directory, so built wheels/sdists/conda artifacts carry no license text.
  evidence: `ls src/shared/packages/*/LICENSE*` returns nothing while every sibling `pyproject.toml` declares MIT. Repo-wide sibling convention predating this story; fixing marshal alone would diverge from the mirror-the-siblings mandate, so it needs a one-sweep fix across all five packages.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and the sweep is now bigger: `ls src/shared/packages/*/LICENSE*` still returns nothing, across all EIGHT sibling packages (atlas, doctor, herald, marshal, mason, scribe, steward, warden) — the entry counted five. Every sibling `pyproject.toml` still declares `license = { text = "MIT" }` with no LICENSE file to ship.

## DW-1-1-4 — The `pyforge-mason-build-dist` and `pyforge-steward-build-dist` pixi tasks (root `pixi.toml`) ru…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: The `pyforge-mason-build-dist` and `pyforge-steward-build-dist` pixi tasks (root `pixi.toml`) run `python -m build` without `--no-isolation`, so `python -m build` creates an isolated venv and pip-fetches `hatchling` from PyPI — the `hatchling` deliberately provisioned in each feature block is dead weight, and the tasks hard-fail in the air-gapped/offline environments this repo explicitly supports (warden and doctor's equivalent tasks pass `--no-isolation`; marshal's copy of the same defect was fixed in this story's third review pass).
  evidence: Root `pixi.toml` shows warden/doctor build-dist cmds with `--no-isolation` and steward/mason without it; marshal's task mirrored steward/mason and was confirmed fixed live in this pass (wheel + sdist built successfully against the in-env hatchling with `--no-isolation` added). Pre-existing in already-merged sibling blocks, outside this story's surface.

  status: done 2026-07-30

  verified: 2026-07-30 — ALREADY RESOLVED. Every `*-build-dist` task in the root `pixi.toml` now passes `--no-isolation` — filtering the build-dist commands for ones lacking the flag returns nothing. mason (`:146`) and steward (`:175`), the two the entry named, both read `python -m build --no-isolation --outdir dist`. The air-gapped failure mode is closed.
### DW-FU-1-1: Follow-up review still recommended for 1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 1) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260725-234618-4c9d; this entry preserves the lingering recommendation for a deliberate later review.
status: open

verified: 2026-07-30 — CONFIRMED STILL OPEN — the recommended independent follow-up never happened. Grepping the whole of `planning-artifacts/` (32 files) for `1-1-package-spine` matches only `sprint-status-ledger.yaml` and this ledger; no review artifact exists for the story.

## DW-1-2-1 — `architecture.md`'s AD-23 rule text still says the story key is "purely numeric on both parts", contradicting AD-38

<!-- id assigned 2026-07-30 during the verification campaign: this entry was promoted
     with no heading and no status, so neither `normalize_deferred_ledgers.py` nor any
     id-based count could see it. Nothing cited it (it had no id), so assigning one
     breaks no references. -->

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-2-story-identity-merge-subject-rendering-and-feed-completeness.md`
  summary: `architecture-pyforge-marshal-2026-07-25/architecture.md`'s AD-23 rule text still literally says the canonical story key is "purely numeric on both parts," directly contradicting AD-38 (added the same day), which requires an optional ordered suffix to be preserved on read.
  evidence: Confirmed live by reading the architecture file during Story 1.2's implementation: AD-23's rule sentence is unamended even though the 2026-07-25 adversarial review (`architecture-pyforge-marshal-2026-07-25/reviews/review-ad25-39-adversarial-2026-07-25.md`, finding F-12) already flagged this exact contradiction as HIGH and noted the harness's own `bmad-loop run --story` documents accepting a split suffix (`2-6a`). Story 1.2's `core/identity.py` implements the epics.md-and-AD-38-correct behavior (suffix preserved, lowercased) per its own Design Notes, but the architecture document itself was left self-contradictory for the next reader who trusts AD-23's rule text without also reading identity.py's docstring. Pre-existing in already-final planning artifacts, outside this story's declared surface (`core/identity.py`, `core/findings.py`, `core/verdict.py`, their tests).

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and the contradiction is now visible inside a
  single document rather than across two. `architecture.md:221` still reads "the canonical story
  key is `<epic>.<seq>`, purely numeric on both parts", while the same file's summary table at
  `:382` reads "story key `<epic>.<seq>` with an optional ordered suffix, normalized on read
  (AD-23, AD-38)" — citing AD-23 as authority for the very rule AD-23's own text denies. AD-38
  is present at `:361`. Unamended since 2026-07-25.

## DW-1-3-1 — `core/policy.py`'s `content_hash` (and therefore `materialize()`'s content-addressed filename) i…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-3-layered-policy-composition-with-provenance-and-validation.md`
  summary: `core/policy.py`'s `content_hash` (and therefore `materialize()`'s content-addressed filename) is computed over each policy field's raw, UNREDACTED value — so once a real policy key ever becomes secret-shaped (none of the 9 shipped in Story 1.3 are), the materialized artifact's filename would be a deterministic fingerprint of that secret, even though the file's own body correctly redacts it via `policy.redact()`.
  evidence: Found during Story 1.3's adversarial + edge-case review passes (both reviewers independently flagged it). Reproduced by inspection: `EffectivePolicy.content_hash` and `cli/config.py::_policy_fields_payload()` both read `field.value` directly; only the payload path calls `redact()` before serializing for the file BODY, while the hash used for the FILENAME does not. Currently inert (no real secret-shaped key exists — the spec's own Never bullet says "do not invent a real secret key today"), but the tension is real: hashing the redacted value instead would make two different secrets that redact identically collide (defeating write-once correctness), so the fix is a genuine threat-model decision, not a mechanical patch. Needs a human call before any future story introduces a real secret-shaped policy key.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — and the behaviour is now deliberately documented, which does not close the concern. `core/policy.py:569-582`'s own `content_hash` docstring states it hashes 'over the RAW (unredacted) values … (redaction is a display/persistence concern, not an identity one)', while `cli/config.py:211` and `:213` still apply `policy.redact()` to the file BODY only. Note the docstring's stated rationale answers a DIFFERENT question than this entry asks — it justifies not hashing redacted values (collision avoidance), and says nothing about the filename becoming a fingerprint of a secret. Still inert: no secret-shaped key exists among the 9 shipped.

## DW-1-3-2 — `schemas/policy.json`'s `policyField` `$defs` entry does not constrain the TYPE of `value`/`raw_…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-3-layered-policy-composition-with-provenance-and-validation.md`
  summary: `schemas/policy.json`'s `policyField` `$defs` entry does not constrain the TYPE of `value`/`raw_source` (only the key set and the `layer` enum are checked), so a materialized document with a wrong-typed value (e.g. a string where `max_dev_attempts` expects an int) still validates against the schema.
  evidence: Found during Story 1.3's adversarial review pass. Confirmed by reading `schemas/policy.json`: the reused `policyField` shape gives `value`/`raw_source` a `description` but no `type` constraint, because the same `$defs` entry is shared across all 9 policy keys whose value types differ (str/int/tuple-as-array/dict). A precise fix needs per-field-name conditional typing (mirroring `pyforge-doctor/src/pyforge/doctor/data/report-schema.json`'s `if/then/else` pattern) — real schema-authoring effort, not a one-line change. Outside this story's `Effort: M` budget.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, verified by loading the schema rather than reading it. Parsing `schemas/policy.json` and inspecting `$defs.policyField.properties` gives exactly: `value: ['description']`, `layer: ['enum', 'description']`, `raw_source: ['description']` — so `value` and `raw_source` still carry NO `type` keyword and a wrong-typed materialized document still validates. No `if/then/else` per-field conditional typing was added.

## DW-1-3-3 — `cli/config.py::materialize()` can leave an orphaned `.policy-*.tmp` file in the target director…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-3-layered-policy-composition-with-provenance-and-validation.md`
  summary: `cli/config.py::materialize()` can leave an orphaned `.policy-*.tmp` file in the target directory if the process is killed unhandleably (e.g. `SIGKILL`, host crash) between `tempfile.mkstemp()` and `os.replace()` — no sweep/cleanup mechanism exists anywhere in this package to reclaim it later.
  evidence: Found during Story 1.3's edge-case review pass. Confirmed by reading `materialize()`: its `except BaseException: tmp_path.unlink(...); raise` cleanup only runs for exceptions the interpreter gets to handle, which a `SIGKILL` or crash bypasses entirely. Low-probability (requires an unhandleable interrupt at a narrow window) and no loop-home/cleanup story exists yet to own a general tmp-file sweep (Story 1.4+/`[cleanup]` policy territory) — outside this story's surface.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — no sweep mechanism exists. `cli/config.py:317` still names the temp file `.pid{os.getpid()}.t{threading.get_native_id()}.tmp`, and grepping the whole `pyforge/marshal/` package for a sweep/orphan/tmp-glob reclaimer returns only the unrelated `[sweep]` stanza in the harness template. A SIGKILL between `mkstemp` and `os.replace` still strands the file permanently.
### DW-FU-1-3: Follow-up review still recommended for 1-3-layered-policy-composition-with-provenance-and-validation after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-1-3-layered-policy-composition-with-provenance-and-validation.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260730-001132-58f6; this entry preserves the lingering recommendation for a deliberate later review.
status: open

verified: 2026-07-30 — CONFIRMED STILL OPEN — same measurement as its 1-1 twin. `1-3-layered-policy` matches only `sprint-status-ledger.yaml` and this ledger across all of `planning-artifacts/`; no review artifact was ever produced.

## DW-1-10-7 — No project-policy source supplies `gate_mode="none"` / `max_followup_reviews=2`, so the first real `write_policy_toml` caller would silently regress both

<!-- id assigned 2026-07-30 during the verification campaign: promoted with no heading and
     no status, so it was invisible to every id-based count. Nothing cited it. -->

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: No project-policy source anywhere in the repo currently supplies `gate_mode="none"` or `max_followup_reviews=2` for `pyforge-marshal`, so the first real invocation of `write_policy_toml` (once a later story wires it up) will render `gates.mode="per-story-spec-approval"` and `limits.max_followup_reviews=1` — Marshal's own `DEFAULT_POLICY` values — silently reintroducing the exact gate-pause and follow-up-review-damping regressions the live hand-edited `.bmad-loop/policy.toml` currently guards against (the latter already caused a documented incident, DW-AD23-3, across atlas/marshal/warden).
  evidence: Found during Story 1.10's adversarial review. Confirmed by grepping every `.bmad-config.toml`/`.bmad-config.user.toml` under `_bmad-output/projects/pyforge-marshal/` for `gate_mode`/`max_followup_reviews` — no match anywhere. `core/policy.py`'s `DEFAULT_POLICY` pins `gate_mode="per-story-spec-approval"` and `max_followup_reviews=1`, both weaker than the live tracked file's `mode="none"`/`max_followup_reviews=2`. Not this story's problem (Story 1.10 only renders a given `EffectivePolicy`; establishing pyforge-marshal's own project-policy layer is Story 1.4/1.7's concern), but whichever story first wires a real caller to `write_policy_toml` must supply that project layer or this regression ships silently.

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED, and by both halves independently, confirming the header's
  claim by measurement. `gate_mode`: NINE tracked `planning-artifacts/marshal-policy.toml`
  station layers now declare `gate_mode = "none"` (9 files matched, all 9 identical).
  `max_followup_reviews`: seeded once in `core/policy.py:150` as `"max_followup_reviews": 2`,
  with ten lines of inline reasoning at `:141-150` naming the repo-wide framing and the five
  damped stories. The real caller the entry anticipated also exists now
  (`cli/config.py:128` `--write-harness-policy`), so the regression window it describes is
  closed rather than merely unreached.

## DW-1-10-1 — `adapters/harness_bmadloop.py`'s vendored `_POLICY_TEMPLATE` is a hand-copied snapshot of `bmad_…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: `adapters/harness_bmadloop.py`'s vendored `_POLICY_TEMPLATE` is a hand-copied snapshot of `bmad_loop` 0.9.0's schema with no drift detector; root `pixi.toml` pins `bmad-loop = ">=0.9.0"` with no upper bound, so a routine re-solve installing a newer harness version with a renamed/added/changed-default key would silently go unnoticed by every existing test.
  evidence: Found during Story 1.10's adversarial review. Confirmed by reading `pixi.toml`'s `bmad-loop = ">=0.9.0"` pin (no ceiling) and `_POLICY_TEMPLATE`'s own docstring, which states the template was "verified once ... rather than imported at runtime." This repo already has an equivalent-purpose mechanism for a structurally similar problem (`scripts/bmad_drift_check.py`, `llms-full-check`) but nothing analogous protects this new vendored artifact. Deliberately out of this story's `Effort: M` scope (the spec explicitly chose vendoring over an `import bmad_loop` dependency to avoid a root pixi.lock re-solve); a lightweight version-pinned drift check is a reasonable follow-up for whichever story next touches this file.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN on both halves. The pin still has no ceiling: `pixi.toml:926` reads `bmad-loop = ">=0.9.0"`. And no drift detector guards the vendored snapshot — grepping `scripts/*.py` and the package's own `tests/` for `_POLICY_TEMPLATE` returns nothing, so the template at `adapters/harness_bmadloop.py:81` is still unprotected against a renamed or re-defaulted harness key.

## DW-1-10-2 — `write_policy_toml`'s unconditional whole-file overwrite will silently discard harness-native st…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: `write_policy_toml`'s unconditional whole-file overwrite will silently discard harness-native state that legitimately lives in the same file outside Marshal's control — `bmad-loop mux set <name>` persists `[mux].backend`, and the TUI persists resized pane geometry (`[tui].left_width`/`.runs_height`/`.deferred_height`/`.tasks_height`) — the moment this rendering path runs against a live loop home more than once.
  evidence: Found during Story 1.10's adversarial review. Confirmed in the installed `bmad_loop` 0.9.0 source: `policy.py::write_mux_backend()` rewrites `[mux].backend` in place, and `TuiPolicy`'s pane-dimension fields are documented as written by the TUI on resize. This is a direct consequence of AD-12/AD-35's own "written whole -- never patched, never merged" invariant (epics.md's Story 1.10 AC text, not a choice this story's spec introduced) — resolving it would need an architecture-level carve-out (e.g. round-tripping `[mux]`/`[tui]` from the pre-existing file before overwriting everything else), which is a product decision, not a mechanical patch.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — now stated outright in the code. `write_policy_toml`'s docstring (`adapters/harness_bmadloop.py:281-282`) says: 'Never reads an existing file at that path first: every call fully replaces any prior content, including hand-edited or unrelated bytes.' The harness-owned sections are in the vendored template (`[tui]` at `:184`, `[mux]` at `:187`), so a second render does not merely drop live pane geometry and the `mux set` backend — it resets them to template values.

## DW-1-10-3 — This story's untrack (`git rm --cached .bmad-loop/policy.toml`) only closes the F-1 cross-projec…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: This story's untrack (`git rm --cached .bmad-loop/policy.toml`) only closes the F-1 cross-project bleed going forward from this merge; any loop-home branch that diverged BEFORE this fix landed (the motivating example, `loop-pyforge-herald`, held 17+/27− of herald-specific policy on the shared tracked file at review time) still carries those tracked commits and needs a manual rebase/re-merge to actually stop bleeding.
  evidence: Found during Story 1.10's adversarial review. `loop-pyforge-herald`'s divergent state is already documented in this project's own memory (`project_open_items_2026-07-26.md`'s "Marshal (station owner)" section) as of the review date; nothing in this story's diff or ACs names a remediation step for already-diverged branches. Operational/rollout concern (a manual git operation per affected home), not a code defect this story's surface can fix.

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED — the divergence this entry worried about is gone. Checked ALL NINE `loop/pyforge-*` branches (atlas, doctor, genesis, herald, marshal, mason, scribe, steward, warden): `git show <branch>:.bmad-loop/policy.toml` fails on every one, so no branch still carries a tracked copy — including `loop/pyforge-herald`, the motivating example that held 17+/27− of herald-specific policy at review time. The untrack propagated to every home; no manual rebase is outstanding.

## DW-1-10-4 — Between this story's merge (which untracks `.bmad-loop/policy.toml`) and the later story that wi…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: Between this story's merge (which untracks `.bmad-loop/policy.toml`) and the later story that wires a real caller to `write_policy_toml`, any FRESH loop home/clone — and any existing home whose unmodified tracked copy git deletes on pull — has no `.bmad-loop/policy.toml` at all, so bmad-loop runs on its stock defaults: `scm.isolation="none"` (dev sessions edit the live checkout in place), `verify.commands=[]` (no deterministic verify gate), `review.trigger="recommended"`, `session_timeout_min=90`; rollout needs a per-home restore/render step until the renderer is wired.
  evidence: Found during Story 1.10's follow-up review (second pass). The diff deletes the tracked file while the module docstring itself states "no CLI wires this module's functions yet"; bmad_loop 0.9.0's stock defaults were confirmed against its installed `policy.py` dataclasses. Distinct from the two existing entries (the first-caller DEFAULT_POLICY regression, and pre-diverged branches needing rebase): this is the no-file-at-all window, a direct consequence of the epic's own mandated sequencing (untrack last, wiring in Story 1.4/1.7), so it is an operational rollout concern outside this story's authority, not a code defect.

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED — both ends of the window are closed. A real caller now exists: `cli/config.py:128` declares `--write-harness-policy`, wired at `:447` and dispatching to the renderer at `:455`. And no home is currently bare: all nine `~/.bmad-loops/pyforge-*` homes have a live `.bmad-loop/policy.toml` present. The stock-defaults exposure the entry describes (`scm.isolation="none"`, `verify.commands=[]`) is therefore not live anywhere today.

## DW-1-10-5 — The `max_followup_reviews = 2` value in the (now untracked) live policy.toml was explicitly bran…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: The `max_followup_reviews = 2` value in the (now untracked) live policy.toml was explicitly branded a REPO-WIDE policy decision ("a repo-wide policy decision that has nothing to do with marshal", restored 2026-07-30 after five stories across three projects were damped by the default of 1), so restoring it via pyforge-marshal's project-policy layer alone (the existing ledger entry's Story 1.4/1.7 remedy) under-scopes the fix — in the new rendering model the only homes for a repo-wide seed value are Marshal's `DEFAULT_POLICY` (core/policy.py) or the global custom policy layer, and a template hardcode cannot work because `render_policy_toml` unconditionally overwrites `[limits].max_followup_reviews` from the composed `EffectivePolicy`.
  evidence: Found during Story 1.10's follow-up review (second pass). The deleted file's own 2026-07-30 comment (this diff, `.bmad-loop/policy.toml` lines 49-68) documents the repo-wide framing and the five damped stories (atlas 10.5/10.6, marshal 1.1, warden 6.3/5.1, yielding DW-AD23-3); `core/policy.py::DEFAULT_POLICY` pins 1. This is a resolution-shaping constraint for whichever story supplies the policy source — recorded as a NEW entry (the orchestrator owns the existing marshal-values entry; this does not modify or re-open it).

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED exactly as the entry prescribed — the value was seeded in Marshal's `DEFAULT_POLICY`, not in a project layer. `core/policy.py:150` now declares `"max_followup_reviews": 2`, and `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` restates it ZERO times — confirming the nine-copies shape the review warned against was avoided. The entry named exactly two acceptable homes (DEFAULT_POLICY or the global custom layer); the first was used.

## DW-1-10-6 — The tracked `.bmad-loop/policy.toml` this story deletes carried curated operational commentary w…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: The tracked `.bmad-loop/policy.toml` this story deletes carried curated operational commentary with no other tracked home — the A4/A6 authoring conventions from the pyforge-atlas retro, the hard-story model-escalation batch procedure, the atlas-gates restore instructions, the `--frozen` verify rationale, and the full max_followup_reviews=2 argument — which now survives only in git history (`git show 99ba90ea4e:.bmad-loop/policy.toml`) and in untracked per-home working copies; the still-relevant parts should be relocated to a tracked home (template comments, the future project-policy source, or project docs) when Story 1.4/1.7 establishes where policy values live.
  evidence: Found during Story 1.10's follow-up review (second pass). Directly visible in this story's diff (250 deleted lines, of which ~120 are curated commentary, not config); the A4/A6 block explicitly says "recorded here because this is where a loop operator looks." Not permanent loss (git history retains the blob), but a real discoverability regression; placement of each fragment depends on the policy-source design owned by later stories, so it is not mechanically patchable inside this story's declared surface (adapter + tests + .gitignore).
  status: open

  verified: 2026-07-30 — PARTIALLY RESOLVED, so held open for the remainder. Two fragments now DO have tracked homes: the `max_followup_reviews = 2` argument was relocated in full to `core/policy.py:141-150` (ten comment lines naming the repo-wide framing, the five damped stories and DW-AD23-3), and the A4/A6 authoring conventions live in the tracked `pyforge-atlas/planning-artifacts/retros/SYNTHESIS.md`. Not verified as relocated: the hard-story model-escalation batch procedure, the atlas-gates restore instructions, and the `--frozen` verify rationale. Those still survive only in `git show 99ba90ea4e:.bmad-loop/policy.toml` and untracked per-home copies.
