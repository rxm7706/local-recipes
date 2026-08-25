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

> **Promotion pass 2026-07-31 (Stories 1.7-1.9 audit)** — nine entries from the
> gitignored Tier-3 ledger had no ids and therefore escaped `deferred-work-check`'s
> id-set comparison. They are copied below without editing their `source_spec`,
> `summary`, or `evidence` bodies. Stable story-scoped ids and current status/verification
> fields are the only additions. One entry was resolved by Story 1.9; eight remain open.

## DW-1-7-1 — The supported harness range had three unsynchronized declarations

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-7-preflight-adapter-config-seeding-and-first-run-acknowledgement.md`
  summary: The declared supported harness range (`>=0.9.0,<0.10`) is now hardcoded independently in THREE places — `pyproject.toml`'s `dependencies` entry, `pixi.toml`'s `bmad-loop` line, and `cli/init.py`'s own `_HARNESS_MIN_VERSION`/`_HARNESS_MAX_MINOR_EXCLUSIVE`/`_HARNESS_VERSION_RANGE_TEXT` constants that `run_preflight` validates the LIVE `bmad-loop --version` output against — with nothing keeping the third copy in sync with the first two.
  evidence: Found during Story 1.7's adversarial review pass. Confirmed by grep: all three literals exist independently, and unlike the pyproject.toml/pixi.toml pair (which `tests/meta/test_manifest_sync.py` already cross-checks), no test compares `cli/init.py`'s parsed tuple bounds against either manifest string. A future pin bump (e.g. Story 1.9's planned range change, or a routine `bmad-loop` upgrade) can update the two manifests and silently leave `_harness_version_in_range` validating against a stale range, so `marshal preflight` would wrongly pass (or wrongly block) once the two drift. Low severity today (all three still agree, and this repo's own installed `bmad-loop` is pinned at exactly 0.9.0), but real: fixing it needs either deriving the tuple bounds from `_HARNESS_VERSION_RANGE_TEXT` at import time (cuts three sources to two) or a `test_manifest_sync.py`-style meta-test extended to also parse `cli/init.py`'s constants — a deliberate design choice about where the ONE source of truth should live, not a one-line patch.

  status: done 2026-07-31

  verified: Story 1.9 moved the range constants into `adapters/harness_bmadloop.py`, the FR-52 seam that declares the supported range, and added `tests/meta/test_manifest_sync.py::test_harness_range_constants_match_pyproject_dependency_pin`; the existing manifest cross-check covers `pixi.toml` transitively.

## DW-1-8-1 — Preflight lacks init and teardown's Git-ref-shape slug guard

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `run_preflight` (Story 1.7) does not apply the same git-ref-shape guard (`.`/`..`/`.lock` component rejection) that `run_init` and now `run_teardown` both apply on top of `core.policy._is_valid_project_slug` — a slug shape git itself would refuse as a branch-name component reaches real I/O in `run_preflight` and surfaces as an opaque `MRS-PREFLIGHT-004`-class error instead of a crisp pre-I/O rejection.
  evidence: Found during Story 1.8's adversarial review pass, while verifying an inline comment in the new `run_teardown` code that (incorrectly, now corrected) claimed `run_preflight` already shared this guard. Confirmed by code inspection: `run_preflight`'s slug gate (`cli/init.py`, its `MRS-PREFLIGHT-010` check) calls only `policy._is_valid_project_slug(slug)`, with no `.`/`..`/`.lock` check anywhere in that function. Pre-existing gap, not introduced by this story; fixing it is a one-line addition to `run_preflight` but is Story 1.7's surface, not this story's.

  status: open

  verified: 2026-07-31 — CONFIRMED STILL OPEN. `run_preflight` calls only `policy._is_valid_project_slug(slug)`; `run_teardown` still carries an inline comment explicitly recording the missing companion guard.

## DW-1-8-2 — Teardown hardcodes the integration branch as `main`

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `run_teardown` always calls `is_branch_merged(repo_root, branch, into="main")` with no way to point teardown at a repo whose default integration branch is not literally `main` (`master`, `trunk`, etc.) — such a repo would hard-fail every teardown invocation with an opaque `MRS-TEARDOWN-002` from git failing to resolve `refs/heads/main`.
  evidence: Found during Story 1.8's adversarial review pass. This mirrors an already-adjudicated hardcoding: Story 1.4's `add_worktree` calls already hardcode `base="main"` when minting a loop-home branch, and `EffectivePolicy` (Story 1.3) deliberately owns only 9 fixed keys, none naming a base/integration branch. `is_branch_merged`'s new `into` parameter makes the assumption more visible than before, but does not introduce it. Needs a product decision (add a tenth policy key, or accept `main`-only as a permanent constraint of this factory) before it can be fixed — out of scope for an Effort:S story.

  status: open

## DW-1-8-3 — Teardown has a branch-deletion TOCTOU window

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `run_teardown` always calls `delete_branch(repo_root, branch, force=True)` once removal is authorized (both on the clean/merged path and the forced-refusal path) — if new commits land on the branch ref between `is_branch_merged`'s read and this call (a concurrent process writing to the same worktree via some path other than the worktree teardown just removed), they are force-deleted with `-D` and never re-verified, without the operator's own `--force` ever having been the reason.
  evidence: Found during Story 1.8's adversarial review pass. The window is narrow (the worktree itself is removed before `delete_branch` runs, and git worktrees are exclusive to one branch, so only an out-of-band `git update-ref`/push from a separate process could land new commits in it) and no architecture doc in this repo describes protecting against concurrent multi-process mutation of the same loop-home branch — AD-11's isolation model assumes one operator, one loop home. Real but requires a broader concurrency-control design (e.g. re-verifying `is_branch_merged` immediately before `delete_branch`, or locking) that is out of scope for an Effort:S story.

  status: open

## DW-1-8-4 — Teardown cannot see valuable gitignored content

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `marshal teardown`'s refusal model cannot see gitignored content -- `git status --porcelain` omits ignored files and a plain unforced `git worktree remove` deletes them, so a loop home whose most valuable content sits in gitignored paths (`.bmad-loop/runs/` state, drafted-but-unpromoted Tier-3 story specs, logs) reads as clean and is destroyed with exit 0.
  evidence: Found by Story 1.8's follow-up adversarial review, live-verified two ways -- unforced `git worktree remove` exits 0 and recursively deletes ignored files in a scratch repo, and the real `~/.bmad-loops/pyforge-marshal` home read `git status --porcelain`-clean at review time while hosting an active run with unpromoted work (the precise artifact class the pyforge-warden incident lost). Not patchable naively -- EVERY loop home carries gitignored content (`run_init`'s own marker/symlink, `.bmad-loop/runs/`), so refusing on any ignored content would refuse every ordinary teardown and train the gate away (the exact F-14 failure mode AD-29's amendment warns about). Distinguishing disposable from precious gitignored content is what AD-29's promotion-reachability predicate exists for; this entry is concrete evidence for Epic 4's wiring of `_unreachable_promotions` (a hardcoded no-op today by the spec's own Never-clause).

  status: open

## DW-1-8-5 — Teardown can destroy nested registered worktrees

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: Tearing down a loop home silently destroys nested REGISTERED run worktrees inside it (`<home>/.bmad-loop/runs/<run>/worktrees/<story>`, this repo's own bmad-loop layout) including any uncommitted story work, and leaves orphaned prunable registrations behind -- `run_teardown` interrogates only `loop/<slug>` and never consults the port's existing `list_worktrees` for worktrees nested under the removal target.
  evidence: Found by Story 1.8's follow-up adversarial review, live-verified -- unforced `git worktree remove <home>` on a home containing a nested registered worktree succeeds, recursively deletes it including uncommitted files, and leaves a prunable orphan block in `git worktree list --porcelain`; six of the eight fleet homes at `~/.bmad-loops/` contained such nested worktrees at review time. Committed nested work survives as `bmad-loop/...` branch refs in the common git dir; uncommitted work is lost. A naive any-nested-worktree refusal would fire on every fleet home (universal refusal, gate trained away), so the fix needs a designed policy -- per-nested-worktree dirty/merged checks and a post-removal `git worktree prune` -- a scope decision beyond this Effort:S story's contract, adjacent to Epic 4's AD-29 wiring.

  status: open

## DW-1-8-6 — Teardown has no active-run liveness guard

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `marshal teardown` has no liveness guard -- nothing checks whether a bmad-loop run is actively executing in the home (tmux session, fresh run state, lock), so an operator teardown mid-run destroys the run's in-flight state without refusal, since an active run's entire footprint lives in gitignored `.bmad-loop/runs/` paths the dirty check cannot see.
  evidence: Found by Story 1.8's follow-up adversarial review. The 8-home fleet at `~/.bmad-loops/` runs unattended, and a live run's worktrees/logs/state are all inside gitignored paths (see the companion gitignored-blindness entry), so both refusal probes pass while a story is mid-implementation; the check-then-remove sequence is also unsynchronized with any concurrent writer (same class as the already-deferred delete-branch TOCTOU entry). No liveness mechanism exists anywhere in Marshal's architecture yet to consult -- introducing one (probe choice, staleness thresholds, lock protocol) is a design decision interacting with the same Epic 4 refusal-extension seam, not a patch.

  status: open

## DW-1-9-1 — Marshal's README still describes a Story 1.1 skeleton

- source_spec: `_bmad-output/implementation-artifacts/spec-1-9-packaging-distribution-and-version-reporting.md`
  summary: `src/shared/packages/pyforge-marshal/README.md`'s top "Status" blurb still says "build skeleton (Story 1.1) ... No real command exists yet -- `marshal --version` / `marshal --help` are the only working invocations," which has been false since Story 1.4 shipped `init`/`homes`/`preflight`/`teardown`.
  evidence: Found during Story 1.9's adversarial review pass. Confirmed by reading the README's opening paragraph against the shipped command set in `cli/main.py`'s own docstring (five real subcommands, not zero). Pre-existing across five prior stories, not introduced by this one; Story 1.9's own diff only appended a "Platforms" section and a new command line beneath the stale blurb without correcting it, since a full README rewrite was explicitly out of this Effort:M story's declared surface (`pyproject.toml`/`pixi.toml`, packaging/version-reporting behavior) -- fixing it is a documentation-only patch some future story (or a direct edit) should pick up.

  status: open

  verified: 2026-07-31 — CONFIRMED STILL OPEN. The README's opening Status block still says no real command exists, while `cli/main.py` documents and wires five subcommands.

## DW-1-9-2 — The future run journal must record Marshal and harness versions

- source_spec: `_bmad-output/implementation-artifacts/spec-1-9-packaging-distribution-and-version-reporting.md`
  summary: Epic 3's run-journal writer (`core/journal.py`, Stories 3.1/3.2) must record BOTH `marshal_version` and `harness_version` per run to complete FR-57's "both versions appear in the journal for every run" clause -- Story 1.9 deliberately implemented only the `--version`/preflight halves of FR-57 (its spec's own Never boundary: no journal write path two epics early).
  evidence: FR-57's journal clause is explicit in the PRD; `core/journal.py` does not exist yet (`supervisor/__init__.py` is a reserved stub), so the write cannot land now. Story 1.9's spec's Design Notes promised exactly this ledger entry ("log a deferred-work entry that Story 3.1's journal writer must record {marshal_version, harness_version} per run once it exists") but no such entry had ever been appended -- its absence was itself a Story 1.9 follow-up-review finding.

  status: open

## DW-AUD-2026-07-31-1 — Stories 1.7-1.9 shipped without canonical memlog reconciliation

- source: `scripts/spec_surface_check.py`, Story 1.7-1.9 implementation specs, and PR #175
  summary: The detector's 23 governed-file findings were the implementation surface of completed Marshal Stories 1.7-1.9, not 23 unexplained defects. PR #175 merged the reviewed and verified preflight/config-seeding, safe-teardown, and packaging/version-reporting work, but `spec-pyforge-marshal/.memlog.md` stopped at Story 1.6 and omitted the delivery decisions and residual risks.
  evidence: Merge `b70f7591f29` changed 25 Marshal files (+5160/-93), including the 23 governed source/test files reported by `spec-surface-check`. All three Tier-3 story specs have `status: done`, review-triage logs, verification records, and final revisions. The canonical memlog had no Story 1.7, 1.8, or 1.9 delivery event before this audit.
  action: Append substantive Story 1.7-1.9 delivery entries to the canonical memlog, including the nine promoted deferrals; do not treat a movement-only audit line or a rewritten detector baseline as reconciliation.
  status: done 2026-07-31

  verified: The staged memlog now records each story's shipped behavior, verification, and durable residual-risk disposition. `spec-surface-check` is rerun as part of this audit's verification.

## DW-AUD-2026-07-31-2 — Four Marshal-owned Dreams still have no Tier-2 Spec

- source: `scripts/dream_chain_check.py`
  summary: The repository-wide artifact audit ran `pixi run -e local-recipes dream-chain-check` and found four Dreams owned by Marshal without a corresponding Spec: `durable-runs`, `fidelity-enforcement`, `one-front-door`, and `pr-lifecycle`.
  evidence: The detector reported `INV-1 — 4 finding(s)` on 2026-07-31, with `owner=marshal`. Related discussion exists in Marshal and Genesis memlogs, but no complete four-Spec chain exists under `_bmad-output/projects/`.
  action: For each Dream, either run `bmad-spec` and place the resulting Spec under the owning project, or record an explicit retirement/absorption decision in the Dream and its owning project memlog so the chain checker has a durable disposition.
  status: open

## DW-AUD-2026-07-31-3 — Deferred-work detector ignores anonymous Tier-3 entries

- source: `scripts/deferred_work_check.py`
  summary: `deferred-work-check` compares only `DW-*` ids between Tier 3 and the tracked ledger, so nine real Story 1.7-1.9 deferrals with no ids produced a false-green result and remained vulnerable to teardown loss.
  evidence: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/deferred-work.md` contained nine consecutive id-less entries for Stories 1.7-1.9. Before this promotion, none appeared in the tracked ledger, yet `pixi run -e local-recipes deferred-work-check` passed. The detector's anonymous-entry validation applies to tracked ledgers, not Tier-3 inputs.
  action: Extend `deferred_work_check.py` to report anonymous Tier-3 entries (or compare normalized entry fingerprints in addition to ids), with a regression fixture proving an id-less Tier-3 deferral cannot pass merely because there is no id to compare.
  status: open

> **Promotion pass 2026-07-31 (Stories 1.4-1.6 audit)** — entries from the gitignored Tier-3 ledger that were missed previously.

## DW-1-4-1 — `cli/init.py`'s project-existence check (`MRS-INIT-002`) reads `_bmad-output/pro…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `cli/init.py`'s project-existence check (`MRS-INIT-002`) reads `_bmad-output/projects/<slug>/planning-artifacts` from whatever is checked out in the resolved repo root's LIVE working tree, not from the `main` ref specifically — while `add_worktree` bases the new branch on the literal `main` ref regardless. If the primary checkout is ever not actually on `main`, the two checks are validated against different git states (a project could be wrongly rejected, or a stale project could be wrongly accepted).
  evidence: Found during Story 1.4's adversarial review. Confirmed by code inspection: `fs.is_dir(planning_dir)` calls `Path.is_dir()` on the live filesystem, with no `git show main:...`/branch check anywhere in the path. Low real-world risk given this exact story's own AD-11 invariant (main is never checked out into a second worktree, so the primary checkout has no code path that moves it off main) — but that is an operating discipline, not an enforced guarantee, so a manual `git checkout <other-branch>` in the primary checkout during unrelated work would open the window. Needs a product decision (accept the AD-11-backed low-probability risk, or add a ref-based existence check) before treating it as a mechanical patch.

  status: open

## DW-1-4-2 — The `MRS-INIT-003` marker/symlink desync guard has two blind spots: (1) `_slug_f…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: The `MRS-INIT-003` marker/symlink desync guard has two blind spots: (1) `_slug_from_symlink_target` only recognizes the exact shape `projects/<slug>/planning-artifacts` — any other shape (a target written by a different tool, an absolute path) parses to `None`, so a real desync hiding behind an unrecognized shape evades the check; (2) the guard only compares the marker and symlink to EACH OTHER, never to the actually-requested slug, so a home whose marker and symlink consistently agree on a DIFFERENT project than the one just requested is treated as "not a desync" and gets silently reconciled onto the new slug with no warning that it was repurposed.
  evidence: Found during Story 1.4's adversarial review (two related findings merged). Confirmed by code inspection of `cli/init.py::_slug_from_symlink_target` and the `MRS-INIT-003` condition (`marker_slug is not None and link_slug is not None and marker_slug != link_slug`). Given each loop home's path is keyed by its own slug (`<root>/<slug>`), (2) can only arise from external tooling repointing a home's own marker/symlink to a different project — an anomalous, unlikely-but-real operator scenario. Needs a product decision on whether a third cross-check (against the directory's own slug) belongs to this story or to Story 1.6 (isolation verification, FR-4), which is explicitly the "prove homes are genuinely isolated" surface.

  status: closed

  closed_by: Story 20.7 (spec-20-7-both-guards-hard-fail-on-drift)
  closed_note: Both guards now consume the sole `verify_scope` primitive; `bmad-switch --current` hard-fails on drift; `marshal init` refuses homes whose marker/planning agree on a different project than requested (DW-1-4-2 blind spots (1) and (2)).

## DW-1-4-3 — `adapters/fs_local.py`'s two atomic-write helpers disagree on stale-temp-file ha…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `adapters/fs_local.py`'s two atomic-write helpers disagree on stale-temp-file handling for the identical crash-orphan scenario: `write_text_atomic` opens its temp path with `O_EXCL` and hard-fails (`FsWriteError`) if a leftover temp file exists, while `repoint_symlink_atomic` silently `unlink()`s any pre-existing temp path first before proceeding.
  evidence: Found during Story 1.4's adversarial review. Confirmed by code inspection: both docstrings cite the same "pid+thread-id collision-safety" rationale, but implement opposite policies. Low-impact given the pid+thread-id-suffixed temp names already make a real collision extremely unlikely, but the inconsistency itself is a maintainability/correctness smell worth a follow-up cleanup pass to pick one policy.

  status: open

## DW-1-4-4 — `marshal init <slug>` has no protection against two concurrent invocations for t…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `marshal init <slug>` has no protection against two concurrent invocations for the same slug: there is an unguarded TOCTOU window both between `worktree_path_for_branch` (read) and `add_worktree` (write) in `cli/init.py::run_init`, and between `branch_exists` and the actual `git worktree add -b` inside `GitVcs.add_worktree`. Two concurrent runs can both observe "not yet provisioned," race, and one surfaces an opaque `MRS-INIT-004` rather than a clean "already in progress" outcome.
  evidence: Found during Story 1.4's adversarial + edge-case review passes (both reviewers independently flagged it). This repo's own documented history includes parallel-agent races over shared git/BMAD state (see `feedback_parallel_bmad_physical_paths.md`), so the scenario is realistic, not purely theoretical. A real fix (a lock file, or accepting git's own worktree-add race semantics as "good enough" with a clearer error) is a design decision spanning this story and possibly Story 1.6's isolation-verification surface — not a mechanical patch.

  status: open

  scope note (2026-07-31): this entry is the concrete, in-code instance of a wider question — nothing serializes concurrent writes to the SHARED Tier-2 artifacts (`epics.md`, this ledger, `sprint-status-ledger.yaml`) that every loop line writes. That question was raised against the Spec and PRD rather than this ledger, and was RESOLVED the same day by decomposition (PRD Q-10 / the Spec memlog decision): merge append-only inputs and re-derive regenerated outputs on main after landing; advisory append lock on the shared canonical Tier-3 store; the journal's two-writer case stays with F-6. Fixing this entry does not answer that question, and its resolution does not close this entry — the init TOCTOU remains its own open deferral.

## DW-1-4-5 — `cli/init.py::_loop_home_root()`'s real default fallback (`Path.home() / ".bmad-…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `cli/init.py::_loop_home_root()`'s real default fallback (`Path.home() / ".bmad-loops"`, used whenever `BMAD_LOOP_HOME_ROOT` is unset) has zero test coverage — every test in `tests/unit/test_init.py` and the integration test override the env var via an autouse/explicit fixture, so what an actual operator gets by default is never exercised.
  evidence: Found during Story 1.4's adversarial review. Confirmed by grep: `BMAD_LOOP_HOME_ROOT` is set in every test file that imports `run_init`/`main`. The code itself is a one-line `Path` join with low risk, but the coverage gap is real and mechanically closeable (a single test with `monkeypatch.delenv`) — recorded rather than patched now to keep this pass's diff scoped to the findings that change behavior, not just coverage.

  status: open

## DW-1-4-6 — `tests/unit/test_vcs_git.py` and `tests/integration/test_init_worktree.py` each …

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `tests/unit/test_vcs_git.py` and `tests/integration/test_init_worktree.py` each define an identical `_git(repo, *args)` subprocess-wrapping test helper instead of sharing one via `tests/conftest.py`, so a future fix to one copy can silently drift from the other.
  evidence: Found during Story 1.4's adversarial review. Confirmed by diff: both helpers are byte-identical (`subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)` plus the same returncode assertion). Minor test-hygiene issue with no runtime consequence.

  status: open

## DW-1-4-7 — `cli/init.py`'s printed `launch_line` (`cd <home> && export BMAD_ACTIVE_PROJECT=…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `cli/init.py`'s printed `launch_line` (`cd <home> && export BMAD_ACTIVE_PROJECT=<slug>`) is not shell-quoted; a `BMAD_LOOP_HOME_ROOT` override containing a space would produce a line that does not paste-and-run correctly (the slug itself cannot contain a space — `core.policy._is_valid_project_slug`'s charset already excludes it).
  evidence: Found during Story 1.4's edge-case review. Confirmed by code inspection of `run_init`'s `data["launch_line"] = f"cd {home} && export BMAD_ACTIVE_PROJECT={slug}"` — no `shlex.quote()` anywhere in the f-string. Low real-world likelihood (the loop-home root is normally under `~/.bmad-loops`, which has no spaces) but a real robustness gap for a deliberately overridable path.

  status: open

## DW-1-4-8 — `marshal init` has no guard against the total loop-home path length, despite thi…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `marshal init` has no guard against the total loop-home path length, despite this repo's own documented history of `pixi-build-python` panicking (byte-index underflow) on worktree paths beyond roughly 173 bytes — a sufficiently long project slug (up to the existing 255-char shape cap) plus a long `BMAD_LOOP_HOME_ROOT` override could still reproduce that failure class.
  evidence: Found during Story 1.4's edge-case review, corroborated by this project's own memory (`project_bmad_loop_worktree_path_length_limit.md`) and by `scripts/bmad-loop-worktree`'s own comment documenting the exact panic and the `~/.bmad-loops` short-root mitigation it already applies. Pre-existing risk, not newly introduced by this diff (the reference script has the identical gap) — the existing 255-char `_is_valid_project_slug` cap is a POSIX single-segment bound, not a total-path bound. Needs a product decision on whether Marshal should add a total-length check now or continue relying on the short default root as sufficient mitigation.

  status: open

## DW-1-4-9 — `cli/main.py::main` catches only `SystemExit` and `KeyboardInterrupt` — it has n…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `cli/main.py::main` catches only `SystemExit` and `KeyboardInterrupt` — it has no last-resort `except Exception` clamp, so any unanticipated exception escaping a subcommand handler still surfaces as a raw traceback with interpreter exit 1, outside Marshal's frozen `{0,1,2,3,4,130}` exit-code domain (AD-7).
  evidence: Found during Story 1.4's follow-up review (both reviewers flagged escape paths; the specific known escapes — `Path.cwd()` OSError, `Path.home()` RuntimeError, `UnicodeDecodeError` from marker reads and git output, pathlib `PermissionError` on the 3.12 floor — were all patched at their sources in that pass). The residual clamp is a pre-existing Story 1.1/1.3 design decision on the CLI spine (silently converting unknown bugs to `EXIT_USAGE` trades a loud traceback for domain purity), not a mechanical patch; it spans every current and future subcommand, so it deserves its own deliberate change rather than a review-pass side edit.

  status: open

## DW-1-4-10 — `tests/integration/test_init_worktree.py` — the only end-to-end proof of both wo…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `tests/integration/test_init_worktree.py` — the only end-to-end proof of both worktree acceptance criteria with the real `GitVcs`/`LocalFs` adapters — is executed by no automated gate: the default `pyforge-marshal-test` task excludes `@pytest.mark.slow`, the loop's verify command runs exactly that task, and no `.github/workflows/*` file invokes either marshal task, so `pyforge-marshal-test-slow` only runs when an operator remembers the spec's manual verification step.
  evidence: Found independently by both reviewers in Story 1.4's second follow-up review. Confirmed by grep: `pyforge-marshal-test-slow` appears only in `pixi.toml` and the spec; no CI workflow references either marshal task. Wiring it in is a decision about WHERE (a CI workflow vs. the loop's verify gate vs. a `depends-on` aggregate task) — the loop verify command is orchestrator-owned policy, so this needs a deliberate placement decision, not a review-pass side edit.

  status: open

## DW-1-5-11 — `cli/init.py`'s `tier3_backlink` step gives a real, non-empty DIRECTORY at the l…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-5-single-sourced-tier-3-store-via-backlink.md`
  summary: `cli/init.py`'s `tier3_backlink` step gives a real, non-empty DIRECTORY at the local Tier-3 path a dedicated `MRS-INIT-005` refusal, but a non-directory node (a stray plain FILE) at either the local path or the main checkout's canonical path falls through to the generic `MRS-INIT-004` via `repoint_symlink_atomic`'s/`ensure_dir`'s own internal clobber guards instead.
  evidence: Found independently by both reviewers in Story 1.5's review pass. Confirmed by code inspection: `fs.is_dir(local)` is False for a plain file, so the `remove_empty_dir`/`MRS-INIT-005` branch is never reached; `repoint_symlink_atomic`/`ensure_dir` still safely refuse (no data is destroyed), just under the less-specific code. Low real-world likelihood (why would a plain file occupy exactly this path?) and current behavior is already safe, so not patched now — a dedicated check would need a general `exists()`-style `FsPort` primitive this story's narrow surface doesn't otherwise need.

  status: open

## DW-1-5-13 — `tier3_backlink`'s convergence check compares the raw (unresolved) symlink target…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-5-single-sourced-tier-3-store-via-backlink.md`
  summary: `tier3_backlink`'s convergence check compares the raw (unresolved) symlink target string against `canonical` (`tier3_link_target == canonical`), whereas the ported reference `scripts/bmad-switch::ensure_tier3_backlink` uses `local.resolve() == canonical.resolve()`.
  evidence: Found during Story 1.5's adversarial review. Both `local`'s stored target and `canonical` are always computed identically via the same deterministic `repo_common_root()`/path-join logic on every invocation (Marshal never hand-configures this symlink, unlike the more varied historical states `bmad-switch` has to tolerate), so a divergence causing spurious non-convergence is unlikely in practice — but the inconsistency with the reference script's own comparison method is real and worth revisiting for full fidelity.

  status: open

  verified: 2026-07-31 — promoted in the second pass of this audit. Missed by the first pass, which swept the id-less Tier-3 block without reconciling its entry count against the tracked ledger — the same anonymous-entry blind spot recorded as `DW-AUD-2026-07-31-3`, reproduced by the audit that reported it.

## DW-1-5-14 — A failed `ensure_dir`/`repoint_symlink_atomic` after `remove_empty_dir` leaves the…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-5-single-sourced-tier-3-store-via-backlink.md`
  summary: If `fs.remove_empty_dir(local)` succeeds (clearing a stale empty local Tier-3 directory) but the immediately-following `fs.ensure_dir(canonical)` or `fs.repoint_symlink_atomic(local, canonical)` then fails, `local` is left with NOTHING (no directory, no symlink) — a worse state than before the removal — with no rollback.
  evidence: Found during Story 1.5's edge-case review. Confirmed by code inspection: no compensating write restores the removed directory in the `except FsError` branches after `remove_empty_dir`. Low practical impact since the removed directory was necessarily EMPTY (no data loss) and a subsequent successful re-run self-heals via the same "fresh backlink" path, but a true rollback would be more robust.

  status: open

  verified: 2026-07-31 — promoted in the second pass of this audit, alongside `DW-1-5-13`. Same miss, same cause.

## DW-1-5-12 — A home provisioned by `marshal init` alone still lacks the TOP-LEVEL `_bmad-outp…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-5-single-sourced-tier-3-store-via-backlink.md`
  summary: A home provisioned by `marshal init` alone still lacks the TOP-LEVEL `_bmad-output/implementation-artifacts` symlink, yet `_bmad/bmm/config.yaml` hard-codes `implementation_artifacts: "{project-root}/_bmad-output/implementation-artifacts"` — so every config-resolving BMAD consumer inside such a home sees a dangling path and would materialize a real top-level directory on first write, forking Tier-3 state one level above the nested backlink this story creates, and `bmad-switch --current`'s desync warning fires on every marshal-provisioned home.
  evidence: Found during Story 1.5's follow-up adversarial review. Confirmed by inspection of `_bmad/bmm/config.yaml:8` (top-level path hard-coded), `scripts/bmad-switch::_ARTIFACT_LINKS`/`desync_warning` (requires BOTH top-level links to agree with the marker), and the epics: no later story creates the link — Story 1.6 only VERIFIES Tier-3 realpaths, Story 1.7 seeds adapter configs. The spec deliberately scoped the top-level compatibility link out of Story 1.5 (its Never section + Design Notes: it belongs to `bmad-switch::repoint_links`, shared with `planning-artifacts`), and today's operational mitigation is running `bmad-switch` inside the home (auto-memory `feedback_bmad_loop_worktree_needs_switch_and_backlink.md`). Needs a product decision: either a later Marshal story ports `repoint_links`' implementation-artifacts half (e.g. into 1.6/1.7's surface), or the FR-3 claim "every consumer sees the same path" is formally narrowed to nested-path consumers.

  status: open

## DW-4-2-1 — `marshal teardown` reports every landed story as an unreachable promotion for …

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-4-2-teardown-reachability-and-spec-recovery-assistance.md`
  summary: `marshal teardown <slug>` for a project whose planning tree no longer exists refuses with `MRS-TEARDOWN-003` naming **every** story that has ever landed on `main` as an unreachable promotion — none of which is at risk. `cli/deploy.py::_scan_promotions` derives the durable-story set from `main`'s merge subjects (repo-wide, not project-scoped, since the composed policy falls back to the default `merge_subject_template` when the project has no policy file) but resolves each story's spec at `_bmad-output/projects/<slug>/planning-artifacts/specs/`. When that directory is absent, every durable key lands in `plan.missing_spec_keys` and is reported as unreachable.
  evidence: Reproduced live 2026-08-08 while retiring the dissolved `pyforge-genesis` loop home. `unreachable_promotions_for_slug(root, "pyforge-genesis")` returns **26** keys — `1.3, 1.4, 2.1, 2.3, 2.7, 3.8, 4.1-4.10, 5.2-5.6, 6.1-6.5` — while the identical call for `"pyforge-marshal"` returns **0**. Same git history, same merge subjects, same spec files: all 50 of Marshal's story specs are tracked under `pyforge-marshal/planning-artifacts/specs/` and every one resolves. The 26 are Marshal's own landed stories being looked up under a slug whose tree was archived. Confirmed by inspection of `cli/deploy.py:602-603` (`specs_dir` is built by string-joining `project_slug`) and `:699-705` (`missing_spec_keys` folded into the unreachable set).
  impact: A safety refusal that cries wolf on 26 provably-safe stories is worse than no refusal — the documented override (`--force --abandon <26 keys>`) trains the operator to abandon a list they cannot practically verify, which is exactly the trust erosion AD-27's "every widening is recorded" discipline exists to prevent. It also makes tearing down any retired project impossible without that override.
  candidate fix: scope the durable-story scan to the project (or treat "project planning tree absent" as a distinct, non-blocking state — a project with no specs directory has no promotions to lose, which is a different fact from "26 promotions are missing their specs"). Worth deciding alongside the `--abandon` UX: it currently accepts a space-separated list but silently rejects the comma-separated form the refusal message's own rendering suggests.

  status: open

  verified: 2026-08-08 — found and reproduced during the genesis retirement; the teardown was completed with `--force --abandon` only after proving the 0-vs-26 asymmetry above. Supersedes the read recorded in auto-memory `project_genesis_teardown_deferred_2026-08-08.md`, which concluded the 26 keys were "stale artifacts of an already-completed retirement (pre-split planning-phase epics)" — they are not; they are Marshal's current, shipped stories.

## DW-SYNC-2026-08-08-1 — `sprint-ledger-sync` silently DOWNGRADES the tracked ledger when …

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-4-5-feed-refresh-with-truth-partitioned-by-domain.md`
  summary: `scripts/promote_sprint_status.py` (`sprint-ledger-sync`) copies the gitignored Tier-3 `implementation-artifacts/sprint-status.yaml` over the tracked `planning-artifacts/sprint-status-ledger.yaml` wholesale. It does not merge, and it has no downgrade guard — so when the Tier-3 feed is *behind* the tracked twin, running the sync **destroys** the more-accurate tracked state and reports success.
  evidence: Hit live 2026-08-08. The tracked ledger correctly recorded Epic 6 as `done` with all 9 stories done; the Tier-3 feed still read `epic-6: in-progress` with `6-5`..`6-9` as `backlog`. One `sprint-ledger-sync` run rewrote the tracked ledger to the stale values, dropping **6 `done` keys** (`6-5-conformance-smoke-in-an-ephemeral-home`, `6-6-the-conformance-matrix`, `6-7-entry-file-family-drift-check-detect-only`, `6-8-upstream-contribution-register`, `6-9-tool-surface-rendering-and-preflight-probe`, `epic-6`) and printing only `wrote marshal (110)`. Caught by a before/after diff of the `done` key set that happened to be in place for an unrelated reason (CAP-8 story-identity verification); nothing in the tool itself flagged it.
  impact: This inverts the tracked twin's entire purpose. The ledger's own header explains it exists because Tier-3 "does not survive a clone or a bmad-loop worktree teardown" and because "the dashboard's deploy-time render reads THIS file" — so a silent downgrade regresses the public board to a stale state, and the tracked file is exactly the artifact that was supposed to be immune. It is also the same class as the incident the header cites (Epic 10's merge subjects becoming unreachable after a squash merge): durable state losing to ephemeral state.
  candidate fix: make the sync monotonic for terminal states, or refuse-and-report on any transition that moves a key backwards (`done` → anything) unless explicitly forced, naming every affected key. A per-key transition check is cheap; a wholesale overwrite of a durability artifact by a non-durable one should not be the default. Relates to auto-memory `feedback_feed_reports_intent_run_reports_fact` — the feed is *already* known to be a statement of intent rather than fact, which is precisely why it must not be allowed to overwrite the record of fact.
  workaround applied: the Tier-3 feed was corrected to match reality (Epic 6 done) before re-running, and the `done` key set was diffed before and after to prove all 59 survived. That verification was manual and is not part of the tool.

  status: open

  verified: 2026-08-08 — reproduced and recovered in the same session; the tracked ledger was restored via `git checkout` before the bad state was committed.

## DW-LEDGER-2026-08-08-1 — RETRACTED. Herald's "34 orphan story specs" was damage I caus…

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-sprint-status-auto-promote/SPEC.md`
  summary: **Retracted.** This entry reported Herald rendering 4/17 for a complete station, with 34 tracked story specs having no ledger key, and framed it as a pre-existing fleet condition. It was not pre-existing. It was **caused by commit `cfaa9a01ed` earlier in the same session** — my own — which ran `sprint-ledger-sync` after editing marshal's Tier-3 feed. The sync writes **every** project, and four stations' stale Tier-3 feeds overwrote their good tracked twins.
  measured damage: herald 71 keys/59 done -> 27/4 (**55 done destroyed**) · doctor 24/20 -> 18/6 (**14**) · scribe 13/11 -> 13/3 (**8**) · steward 26/22 -> 26/3 (**19**). **96 `done` markers total across 4 stations.** marshal, atlas, warden and mason were untouched.
  how it was missed: CAP-8 was verified for **marshal only** — the project being worked on — while the command mutates all eight. The before/after `done`-key diff that caught nothing wrong was scoped to one project out of the eight it wrote.
  how it was found: tracing Herald's "missing" keys through `git log` on its ledger, which showed 47 stories/59 done at `14a43c2544` (05:16 the same day) and 17/4 immediately after `cfaa9a01ed`.
  resolution: all four ledgers restored byte-identical to their pre-session state from `a3b5fefae8^`. Verified: seven of eight now diff clean against pre-session, and marshal differs only by the five intended story-key renames.
  the entry that stands: DW-LEDGER-2026-08-08-4's table was measured **after** the damage and is likewise void; the real pre-existing orphan counts are zero for every station.

  status: retracted

  verified: 2026-08-08 — self-inflicted, found and fully restored the same session. This is the second retraction in this ledger today (see also -3); both came from measuring an artifact without first establishing that the measurement's baseline was sound.

## DW-LEDGER-2026-08-08-2 — VOID (measured after the DW-LEDGER-1 damage; doctor's real orpha…

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-sprint-status-auto-promote/SPEC.md`
  summary: `pyforge-doctor` carries **16 tracked story specs** against **12 ledger story keys** — at least 4 landed stories have a durable spec but no ledger entry, so the board under-reports Doctor too.
  evidence: Measured 2026-08-08 alongside DW-LEDGER-2026-08-08-1. Same shape, smaller magnitude; same absent detector.
  remedy: same as above — the reconciliation should be one check covering every station, not a per-station fix.

  status: open

  verified: 2026-08-08.

## DW-LEDGER-2026-08-08-3 — RETRACTED. Atlas's feed and twin agree exactly; there is no …

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-sprint-status-auto-promote/SPEC.md`
  summary: **This entry was wrong and is retracted the same day it was filed.** It claimed `pyforge-atlas`'s Tier-3 feed held 14 stories / 3 done against a tracked twin of 38/38, and that one `sprint-ledger-sync` run would destroy 35 `done` keys. Re-measured with the real parser (`generate.py::parse_sprint_status`, the same function the sync itself uses): **feed 57 keys / 57 done, twin 57 keys / 57 done, byte-identical.** A live `sprint-ledger-sync` run reports atlas `unchanged`. There is no landmine and there never was.
  root cause: the original measurement used an ad-hoc grep, `^  [0-9]+-[0-9]+`, which silently under-counted atlas's key shapes — atlas uses `a1-scaffold-…`, `b2-…` and `0-1-…` alongside `10-1-…`, and the pattern matched only some of them. The artifact was fine; **the detector I reached for was wrong**, which is precisely the failure mode `spec-dream-to-code-model-self-verification` exists to prevent, reproduced by hand while cataloguing it.
  what survives: nothing of the Atlas claim. The sibling entries DW-LEDGER-2026-08-08-1 (herald) and -2 (doctor) were re-verified with the correct parser and **both stand** — see the corrected fleet-wide table in -1.
  note on the fix: `scripts/promote_sprint_status.py`'s new monotonic guard was written while this entry was believed true. It stays, and is still correct — it defends against DW-SYNC-2026-08-08-1, which was a **real, reproduced** loss of 6 `done` keys on marshal earlier the same session. Only the urgency framing came from this retracted entry.

  status: retracted

  verified: 2026-08-08 — retracted within hours of filing, on re-measurement with the parser rather than a regex.

## DW-LEDGER-2026-08-08-4 — VOID. Its table was measured after the damage, not before it.

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fleet-chain-completeness/SPEC.md`
  summary: Six of eight stations carry tracked story specs that have **no corresponding key in their sprint ledger**, so the board under-reports them. Measured 2026-08-08 with `generate.py::parse_sprint_status` (not a regex — see DW-LEDGER-2026-08-08-3 for why that distinction is on the record).
  evidence:

  | station | ledger keys | story keys | done | story specs | **specs with no key** |
  |---|---|---|---|---|---|
  | herald  |  27 | 17 |  4 | 47 | **34** |
  | marshal | 110 | 86 | 50 | 50 |   0 |
  | atlas   |  57 | 38 | 38 |  8 | **3** |
  | warden  |  43 | 31 | 31 | 31 |   0 |
  | mason   |  48 | 38 |  4 |  4 |   0 |
  | doctor  |  18 | 12 |  6 | 16 | **4** |
  | scribe  |  13 |  9 |  3 |  9 | **1** |
  | steward |  26 | 18 |  3 | 18 | **1** |

  Marshal, warden and mason are exactly consistent. Herald is the outlier by an order of magnitude: its `epics.md` is titled "Herald Moments 2-4" and covers only that epic set, so ~34 deck-bridge story specs were never fed into the sprint feed at all.
  impact: the Guildhall renders a station's progress from the ledger, so every one of these under-reports. Herald renders 4-of-17 for a station whose 47 story specs say otherwise.
  remedy: a reconciliation check — every tracked story spec must resolve to a ledger key, and every ledger key to an epics entry. This is `spec-fleet-chain-completeness`'s CAP-3/CAP-4 territory (chain-completeness audit + orphan detection) and belongs there rather than as eight per-station fixes. FR-137's standalone staleness check is the adjacent half.

  status: open

  verified: 2026-08-08 — re-measured with the parser after the DW-LEDGER-2026-08-08-3 retraction; these numbers supersede every earlier count in this session.

## DW-DOCTOR-2026-08-08-1 — `doctor check` is 7.04s against its documented 5.0s budget

- source_spec: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md`
  summary: `test_doctor_check_completes_within_the_five_second_budget` fails on `main`. Measured 2026-08-08 against the monorepo root: **6.92s / 7.04s / 6.73s** across three iterations, versus the 5.0s budget the Doctor PRD documents as **SM-C1**. This is a real NFR violation, not a flaky or environment-coupled test — the run does the full work and reports the full finding count, it is simply ~40% over budget.
  why it was NOT fixed alongside the two tests found with it: the other two failures in the same suite were hermeticity bugs in the tests (an uninjected `cli_runner` falling through to the real on-disk script), contained and correct to fix in place. This one is different in kind. The only two changes available without profiling are a blind performance edit or relaxing the budget, and the second is precisely the "weaken the threshold rather than meet it" move that Charter §6 forbids a station from making about its own gate. It needs a profile first: whether the cost is warden's `--version` subprocesses, the atlas MCP/CLI fallbacks, or the env-hygiene walk is unknown.
  discovered by: running Doctor's full suite while adding `sources/marshal.py`; confirmed pre-existing by stashing the change and re-running.

  status: done 2026-08-08 — Story 6.1.

  resolution: the profile ran and the cost was ATTRIBUTED, not estimated. Of the three suspects this entry named, two are cleared: warden's `--version` subprocesses are **0.18s**, and the atlas MCP/CLI fallbacks are not in `check`'s path at all (they belong to `monitor`). The env-hygiene walk is **97%** of it — re-measured worse than this entry recorded, at 7.98s / 8.13s / 8.45s. Splitting that gather again: discovery **0.21s**, per-file parse **7.73s** over 3,721 files / 33.2MB of source. **6.43s of the 7.73s — 3,216 of the 3,721 files — was the gitignored 590MB `build_artifacts/`**, i.e. extracted THIRD-PARTY conda sources and test envs (idna, typing-extensions, anyio, websockets, fastmcp).
  the fix was NOT a speed trade: `build_artifacts` sorts before `docs`/`recipes`/`scripts`/`src`, so the walk burned its whole `_DISCOVERY_ENTRY_CAP` inside it (74,340 entries walked against the 50,000 cap, first crossed under `.../test_env/include/openssl`) and reached **zero** first-party files — all **609** under `src/` and `scripts/` went unscanned, including this scanner's own module. Pruning build-output/tool-cache dir names therefore **raised** coverage (first-party 0 → 602 files) while cutting the gather to ~3.2s, and surfaced a **third real finding** that had been invisible (`pyforge-steward/tests/conformance/fixtures/ungated_jfrog_auth.py:21`). The 5.0s budget is untouched — no re-thresholding.
  guarded by: `test_discovery_walk_reaches_this_packages_own_source` (asserts the walk reaches `env_hygiene.py` itself and excludes `build_artifacts`) plus a parametrized prune test. Both mutation-tested: removing `build_artifacts` from the prune set fails the coverage test AND the budget test (7.01s).
  residual, split out: the walk is still `incomplete` — see `DW-DOCTOR-2026-08-08-2`.

  verified: 2026-08-08 — three timed iterations, all over budget; re-verified green after the fix (411 → 418 tests pass).

## DW-DOCTOR-2026-08-08-2 — Doctor's discovery walk borrowed warden's entry cap, where hitting it means the opposite thing

- source_spec: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md`
  summary: `env_hygiene._DISCOVERY_ENTRY_CAP = 50_000` is documented as "mirroring `pyforge.warden.hygiene._ADJACENT_PYTHON_SOURCE_ENTRY_CAP`", but the two caps bound **opposite-shaped** walks. Warden's walk EARLY-EXITS on the first `*.py` it sees and returns `True` at the cap — hitting it is harmless. Doctor's walk is an EXHAUSTIVE collection, so hitting the same cap silently **drops source files** from a security scan. The number was borrowed; the semantics were not.
  evidence: measured 2026-08-08 on `main` after Story 6.1's prune landed. The pruned tree is **52,968** entries against the 50,000 cap, so the walk still reports `incomplete=True`. **`SDKs/` alone is 39,379 of those entries (74%)** — the 81MB gitignored macOS cross-compilation SDK, which contains **zero** `*.py` files — and `SDKs` sorts before `src` in ASCII (uppercase < lowercase), so it starves the first-party tree it precedes: `src/` is truncated at 545 of ~588 files (cap first crossed inside `src/shared/packages/pyforge-warden/tests/fixtures/corpus/recipes`) and the top-level `tests/` tree is never reached at all.
  why it was NOT fixed in Story 6.1: 6.1's ACs (attribute the cost, meet the budget, do not re-threshold) are all met, and this needs a design decision rather than a bigger magic number — cap entries walked, cap files collected (the walk is 0.24s for the whole tree; parsing is the real cost), or make the scanner gitignore-aware so it never descends into build/vendor output in the first place. Picking a new constant to make the symptom go away is the same "blind performance edit" the parent entry refused.
  not silent: the walk does emit its `env-hygiene` INCOMPLETE sentinel finding, so the truncation is self-reported rather than a false all-clear — consistent with this scanner's documented WARN-only v1 posture and its other logged coverage gaps.

  status: open

  verified: 2026-08-08 — entry census by top-level directory; `SDKs` confirmed 0 `*.py` and gitignored.

## DW-BOARD-2026-08-08-1 — Herald's build line and Herald's ledger describe DIFFERENT sto…

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-project-path-derivation/SPEC.md`
  summary: The Guildhall renders Herald as **12/19, "paused 0.1"** while Herald's tracked ledger holds **47 story keys, 47 done**. Neither is wrong about its own source; they are describing **two different bodies of work** under one station, and only one of them reaches the board.
  evidence: Measured 2026-08-08. `data.js`'s `projects.herald.epics` is a hand-curated array whose story ids run `0.1`/`0.2`/`0.3` (E0 "Foundation & Infrastructure" — *"Set up Modernist-Identity design system"*, *"Design-Code-Bridge etagged pull protocol"*) and `1.1`..`1.4` (E1 "Design Authoring & Seeding" — *"Create 9 Design projects"*, *"six-act framework"*). Herald's `sprint-status-ledger.yaml` holds an entirely disjoint set: `1-1-package-scaffold-for-pyforge-herald` … `12-4-automation-troubleshooting-guide`. No id in one set appears in the other.
  why it persists: `scan_projects` only ever UPGRADES a hand-authored line (the deliberate guard that stops a parse failure blanking curated state), so the seeded `epics` array is never reconciled against the ledger and cannot self-heal. The same "only upgrades" property that protects curated in-flight state also freezes a divergence.
  impact: a station whose ledger says 47/47 renders as 63% and "paused". This is the visible half of the story-set question; the invisible half is that no detector compares a build line's story ids against the ledger's, so the divergence is silent.
  NOT the earlier claim: `DW-LEDGER-2026-08-08-1` alleged 34 orphan story specs and was retracted as self-inflicted damage. This is a different, genuinely pre-existing thing — the ledger is correct and complete; the BOARD's story set is the one that diverges.
  remedy: belongs with `spec-dashboard-project-path-derivation` (FR-140..FR-143) — derive the build line's story set from the ledger, or declare explicitly that a station may carry two and render both.

  status: open

  verified: 2026-08-08 — both story sets read directly and compared; zero id overlap.

## DW-SURFACE-2026-08-08-1 — memlog movement is surface-wide, so one entry launders every pending drift finding

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-regenerable-factory/SPEC.md`
  summary: `spec_surface_check`'s drift pass short-circuits **per SPEC, not per file** — `if b["memlog"] != cur["memlog"]: continue  # spec moved — code changes are presumed reconciled`. So appending ANY memlog entry marks every governed file in that surface as reconciled, including files the author never touched.
  evidence: Observed live 2026-08-08. Appending an allowlist-split note to `spec-regenerable-factory/.memlog.md` cleared two pre-existing findings — `scripts/bmad_drift_check.py` and `scripts/dream_chain_check.py` "changed but the spec's memlog did not move" — neither of which was touched by that work. Findings went 63 → 61 with no reconciliation performed. Confirmed by stash-diffing the checker's output before and after.
  impact: the drift half of this detector is defeatable by unrelated activity, and silently. The larger a surface's governed set, the more it launders: this surface governs four detectors. Worse, the disappearance is indistinguishable from a real fix in the findings count, which is what the dashboard renders.
  remedy: make the reconciliation claim per-file rather than per-spec — e.g. require the memlog entry to NAME the governed paths it reconciles, and only clear drift for those. A cheaper interim: report `[drift-presumed]` (informational) for governed files whose hash moved while the memlog also moved, so the set is at least visible rather than absent.
  note: the two unreconciled files are recorded verbatim in that memlog under a `(NOT RECONCILED …)` entry, so the information survives the finding.

  status: open

  verified: 2026-08-08 — reproduced by stash/unstash around the memlog append.

## DW-SURFACE-2026-08-08-2 — `--write-baseline` is all-or-nothing, so no spec can be reconciled in isolation

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-regenerable-factory/SPEC.md`
  summary: `spec_surface_check --write-baseline` stamps `current` for **every** spec in one write. There is no per-spec stamping, so settling one legitimately-reconciled spec necessarily accepts every other spec's pending drift as correct.
  evidence: Measured 2026-08-08 on `main`: **61 findings**, of which **24 are `[no-baseline]`** and ~35 are `[drift]`, overwhelmingly `pyforge-steward/spec-pyforge-steward` (a 20-file Epic-2/3 delivery) plus three `no-baseline` specs in steward/warden. Running `--write-baseline` to register the one spec that needed it (`spec-bmad-loop-forward-dependency-blindness`, which had no baseline entry) would have silently blessed all of them.
  impact: the sanctioned way to fix a `[no-baseline]` finding cannot be used without destroying the evidence for ~35 others — so the honest move is to leave the finding standing, which is why this detector has carried a large red for weeks. A gate nobody can safely clear stops being a gate.
  remedy: `--write-baseline [<project>/<spec-dir> ...]` stamping only the named specs and leaving other entries byte-identical.
  note: NOT run during the 2026-08-08 detector-honesty work for exactly this reason; the `[no-baseline]` finding for `spec-bmad-loop-forward-dependency-blindness` is left standing and is pre-existing.

  status: open

  verified: 2026-08-08 — finding classes counted directly from the checker's output.

### DW-FU-2-1: Follow-up review still recommended for 2-1-standalone-verify-command-runner-project-scoped after the damping cap was spent

- source_spec: `spec-2-1-standalone-verify-command-runner-project-scoped.md`
  summary: Follow-up review still recommended for 2-1-standalone-verify-command-runner-project-scoped after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260802-183704-36df; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-09 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-3` there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide with a generic `DW-3`. This promotion is the manual act Marshal FR-175 / Story 4.13 exists to make an obligation of the story itself.
  severity: low
  status: open

### DW-FU-2-6: Follow-up review still recommended for 2-6-gate-evidence-record-with-redaction-at-egress after the damping cap was spent

- source_spec: `spec-2-6-gate-evidence-record-with-redaction-at-egress.md`
  summary: Follow-up review still recommended for 2-6-gate-evidence-record-with-redaction-at-egress after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260803-023308-65b7; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-09 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-4` there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide with a generic `DW-4`. This promotion is the manual act Marshal FR-175 / Story 4.13 exists to make an obligation of the story itself.
  severity: low
  status: open

### DW-FU-3-3: Follow-up review still recommended for 3-3-detached-launch-with-scoped-story-selection after the damping cap was spent

- source_spec: `spec-3-3-detached-launch-with-scoped-story-selection.md`
  summary: Follow-up review still recommended for 3-3-detached-launch-with-scoped-story-selection after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260803-023308-65b7; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-09 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-5` there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide with a generic `DW-5`. This promotion is the manual act Marshal FR-175 / Story 4.13 exists to make an obligation of the story itself.
  severity: low
  status: open

### DW-FU-3-4: Follow-up review still recommended for 3-4-supervisor-process-lifecycle after the damping cap was spent

- source_spec: `spec-3-4-supervisor-process-lifecycle.md`
  summary: Follow-up review still recommended for 3-4-supervisor-process-lifecycle after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260803-023308-65b7; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-09 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-6` there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide with a generic `DW-6`. This promotion is the manual act Marshal FR-175 / Story 4.13 exists to make an obligation of the story itself.
  severity: low
  status: open

### DW-FU-3-5: Follow-up review still recommended for 3-5-idle-strand-detection after the damping cap was spent

- source_spec: `spec-3-5-idle-strand-detection.md`
  summary: Follow-up review still recommended for 3-5-idle-strand-detection after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260803-023308-65b7; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-09 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-7` there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide with a generic `DW-7`. This promotion is the manual act Marshal FR-175 / Story 4.13 exists to make an obligation of the story itself.
  severity: low
  status: open

### DW-FU-4-14

- source_spec: `spec-4-14-the-failed-story-safety-net-is-reported.md`
  summary: follow-up review still recommended for 4-14 after the damping cap was spent — an independent pass is owed on the failed-story safety-net reporting.
  evidence: the follow-up-review damping cap (`limits.max_followup_reviews = 2`) was spent with the story finalized (status `done`, verify green) while the review pass still recommended an independent follow-up. Committed by bmad-loop run `20260809-231524-abb9`. 4-14 also cleared on its LAST review cycle (rev 3 of 3), which is the profile where an independent pass earns its cost.
  promoted: 2026-08-10 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-8` there) under this ledger's own `DW-FU-<story>` convention (`DW-FU-2-6`, `DW-FU-3-3`, `DW-FU-3-4`, `DW-FU-3-5`). A generic `DW-8` would collide with the next damped story.
  status: open

### DW-9: Follow-up review still recommended for 7-4-manifest-schema-loader-and-model-version-ranges after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-7-4-manifest-schema-loader-and-model-version-ranges.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260810-192255-dbc6; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, mason 2-2 / marshal 7-4)



### DW-10-2-1: `pyforge-deps-test` fails on `pyforge-mason`'s five conda-only run-dependencies, reddening a verify command every story in this loop must pass
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-2-state-schema-and-the-atomic-store.md`
  summary: `pixi run --frozen -e pyforge-ci pyforge-deps-test` fails one case -- `test_conda_run_deps_add_nothing_undeclared[pyforge-mason]` -- because `conda-lock`, `gh`, `pixi`, `python-build`, and `twine` appear in `pyforge-mason`'s `pixi.toml` `[package.run-dependencies]` but in neither its `pyproject.toml` `[project.dependencies]` nor the test's `CONDA_ONLY_RUN_DEPS` allow-list, reddening a verify command every story in this loop must pass.
  evidence: Surfaced by Story 10.2's verification pass, and provably not caused by it: every input the failing assertion reads -- the root `pixi.toml`, every package `pyproject.toml`, and the whole `pyforge-mason` tree -- is byte-identical to this story's baseline `64e717d` (`git status --short` over those paths is empty), and Story 10.2's diff touches only four files, all under `pyforge-marshal`'s `seed/state/` and `tests/unit/`. The five names are deliberate conda-only engines: `pyforge-mason`'s own `pixi.toml` comment block explains they are range-pinned CLI engines consumed from feedstocks, kept byte-for-byte in sync with `engines/__init__.py`'s `PIXI_VERSION_RANGE`/`TWINE_VERSION_RANGE`/`CONDA_LOCK_VERSION_RANGE`/`PYTHON_BUILD_VERSION_RANGE`/`GH_VERSION_RANGE` constants and enforced by `tests/meta/test_engine_version_range_sync.py` -- so the fix is almost certainly to justify them in `CONDA_ONLY_RUN_DEPS` (the escape hatch the assertion message itself names) rather than to declare five CLI tools as Python dependencies. Not fixed here: the remedy edits `pyforge-mason`'s manifests or `pyforge-ci`'s test allow-list, both outside Story 10.2's Surface (`seed/state/schema.json`, `seed/state/store.py`) and inside its Never list ("never modify pyproject.toml/pixi.toml"). It belongs to whoever owns Mason's packaging gate.
  resolution: RESOLVED 2026-08-14 by Story 10.3's verification-repair pass, along exactly the line this entry predicted. Story 10.3's deterministic verifier failed the run on this gate, which made the deferral untenable -- it is a hard landing precondition, so carrying it forward blocks every remaining Epic 10 story rather than parking the debt. Fixed by adding `CONDA_ONLY_RUN_DEPS["pyforge-mason"] = {"conda-lock", "gh", "pixi", "python-build", "twine"}` to `tests/packaging/test_dependency_completeness.py` (the assertion message's own escape hatch), NOT by declaring five CLI tools in `[project.dependencies]`. Verified rather than assumed: each engine is located with `shutil.which` and driven by `subprocess.run` from `engines/*.py`, and `grep -rE "^\s*(import|from)\s+(build|twine|conda_lock|pixi|gh)\b" src/` over the whole package returns nothing, so mason never IMPORTS any of them. The precise claim matters and an earlier, sloppier version of this note got it wrong (caught by this story's second review pass): only `pixi` (Rust) and `gh` (Go) are genuinely not Python distributions — `twine`, `conda-lock`, and `python-build` (conda-forge's spelling of `build`) are real importable PyPI distributions that mason merely drives as subprocesses, which is a property of today's CODE, not of the packages. Same shape already recorded there for `pyforge-warden`'s `deptry`/`osv-scanner` and `pyforge-steward`'s `age`; version ranges remain guarded by `pyforge-mason/tests/meta/test_engine_version_range_sync.py`, which pins all five `pixi.toml` lines to their `SpecifierSet` constants (green). Because the premise is code-dependent it is now ASSERTED, not trusted: the same review pass added `test_conda_only_entries_are_still_conda_run_deps` (the ratchet this table lacked while its two sibling tables had one) and `test_conda_only_run_deps_are_never_imported`, which checks BOTH the `hard` and `deferred` import buckets — a real hole, since both pre-existing call sites discard `_scan_imports`' deferred result (`hard, _ = …`), so a lazy `import twine` inside a function would have shipped an unusable wheel with no gate firing. Both guards are mutation-verified (each fails on the mutation it exists to catch). Neither manifest was touched. Post-fix: `pyforge-deps-test` 84 passed (was 1 failed / 73 passed), `pyforge-marshal-test` 4246 passed, `pyforge-mason-test` 1409 passed.
  status: resolved
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-2` there) during the pre-shutdown deferred-work audit.

### DW-10-3-1: Writing `plan.json` to its canonical path flips the fingerprint's dirty flag, so the first apply of every freshly built plan refuses itself as stale
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `default_plan_path` is `<repo_root>/.marshal/plan.json`, which is only gitignored by the `model-ignores` region of the target's `.gitignore` -- a region a not-yet-seeded repo has not received. So `write_plan(plan, default_plan_path(repo))` on a clean repo makes `git status --porcelain --untracked-files=normal` report `?? .marshal/`, `fingerprint_drift` reports a `dirty` divergence, and `run_apply` refuses with a stale-plan `PreconditionFailure` -- blocking the plan-then-apply flow that is Genesis's entire purpose, and naming `dirty` rather than the plan file, so an operator has no way to diagnose it.
  evidence: Raised independently by BOTH of this story's review passes (Blind Hunter and Edge Case Hunter, no shared context) and reproduced by execution: on a clean git repo, `build_plan` records `dirty=False`; after `write_plan(plan, default_plan_path(d))`, `fingerprint_drift` returns `('dirty: the plan was built with dirty=False, the repo is now dirty=True',)` and `run_apply` raises. This corroborates the already-filed `DW-FU-9-6-2`, which predicted exactly this once a later story started trusting the fingerprint for a refuse decision; recorded separately per this workflow's instruction not to consolidate defer findings against existing ledger entries. Not fixed here: the remedy is a write-ORDER guarantee (materialize the `.gitignore` region before writing the plan file, or write the plan outside the target tree) owned by whichever story sequences those writes -- Story 10.6 (`adopt`) -- or a dirty-probe that excludes `.marshal/`, which is `plan/build.py`'s `_repo_is_dirty` and changes what every plan records, not just what apply checks. Both are outside this story's Surface and inside its Never list (no `plan.json` read or write, no verb sequencing).
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3` there) during the pre-shutdown deferred-work audit.

### DW-10-3-10: A failed rollback wraps an interrupt in a catchable `InternalError`, so a CLI's `except SeedError` swallows the operator's Ctrl-C
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `run_apply` catches `BaseException` and, whenever any single restore fails, re-raises as `InternalError` (exit 10) chained from the original. When the original IS a `KeyboardInterrupt` or `SystemExit`, that converts an uncatchable interrupt into an ordinary `Exception` subclass, so the CLI story that eventually does `except SeedError as e: sys.exit(e.exit_code)` will exit 10 on an operator interrupt instead of dying. This directly contradicts `_restore`'s own docstring, which argues at length that catching `Exception` rather than `BaseException` is deliberate because swallowing a Ctrl-C "would make the process unkillable at exactly the moment a human is trying to stop it".
  evidence: Raised by this story's second review pass (Blind Hunter) and verified by execution: with `commit` raising `KeyboardInterrupt` and one target inside the caller's never-write set, the caller receives `InternalError` with `__cause__` set to the interrupt. Not fixed here because it is a contract-level conflict, not a local bug: the spec's I/O & Edge-Case Matrix has a "Rollback itself fails" row mandating `InternalError` naming every unrestorable path, with no carve-out for an interrupt, and a separate "Interrupt mid-run" row promising `KeyboardInterrupt` propagates unchanged -- both rows are inside the FROZEN `<intent-contract>`, and they collide exactly when both conditions hold. Choosing which wins is an intent decision (and every mechanical alternative has a cost: re-raising the interrupt bare discards the unrestorable-path list, which is the same diagnostics loss already filed as `DW-FU-10-3-5`). This story's `_restore` docstring now states the behavior explicitly so it is not read as an oversight. Belongs with whoever amends the matrix, or with the CLI story that owns exit-code dispatch.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-10` there) during the pre-shutdown deferred-work audit.

### DW-10-3-2: Rollback restores a file's bytes but not its mode, so a failed apply leaves every executable managed artifact non-executable
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `run_apply`'s snapshot is `target.read_bytes()`, and the restore is `fs.write` -> `atomic_write_bytes(path, data)` with no mode argument, which chmods the temp file to `0o666 & ~umask` before `os.replace`. A target that was `0o755` therefore comes back `0o664`. The packaged manifest ships `scripts/bmad-switch` and `scripts/bmad-loop-worktree` as `copied-managed` executable model machinery, so a rolled-back apply silently breaks them while the runner claims to have left the repo exactly as it found it.
  evidence: Raised by this story's Blind Hunter review and independently by the Edge Case Hunter, and reproduced by execution: a `hook.sh` at `0o755`, committed by action 1, with action 2 failing, comes back with correct content at mode `0o664`. Not fixed here: `fs.write(path, data, *, repo_root, never_write)` exposes no `mode=` passthrough to the `atomic_write_bytes(path, data, mode=...)` parameter that already exists one layer down, so the fix edits `seed/fs.py` -- the never-write guard module, explicitly listed as consumed-unmodified in this story's Code Map and outside its Surface. The runner's own docstring now states the bound rather than implying it away.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-2` there) during the pre-shutdown deferred-work audit.

### DW-10-3-3: A directory target snapshots as `None` and is never removed, so a rolled-back apply leaves the whole tree it created
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `run_apply` records `None` for any target that is not a regular file, and its restore path only removes `if target.is_file()`. A manifest artifact whose path is a directory -- the packaged manifest's `deck-scaffolding` entry is `path: "presentations/{{ slug }}/"`, rationale "Genesis lays the directory" -- therefore survives rollback along with everything `commit` created under it. The same asymmetry covers empty parent directories `atomic_write_bytes` creates for a nested target, and the case where a `commit` replaces a regular-file target with a directory (`os.replace` onto a non-empty directory fails, and the file is reported unrestorable instead).
  evidence: Raised by both of this story's review passes and reproduced by execution: an action creating `adir/` plus `adir/junk.txt`, followed by a failing action, leaves both on disk after rollback. Not fixed here: `seed/fs.py` ships no directory-removal primitive (its own `remove` docstring says so explicitly, contrasting itself with `ports/fs.py`'s separate `remove_empty_dir`), and P-01 forbids reaching around `fs` with `shutil`/`os` on a target path -- so the fix adds a primitive to the guard module, outside this story's Surface and inside its Never list. The runner's docstring now enumerates this residue precisely rather than mentioning only empty parent directories.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-3` there) during the pre-shutdown deferred-work audit.

### DW-10-3-4: A symlinked target is snapshotted through the link but restored over it, leaving neither the link nor its referent as they were
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `run_apply`'s snapshot predicate is `target.is_file()`, which FOLLOWS symlinks, so a symlinked artifact captures its referent's bytes; but `fs.write` -> `atomic_write_bytes` -> `os.replace` replaces the link itself (POSIX `rename(2)` never follows a symlink at its destination -- `seed/fs.py`'s own docstring records this, confirmed by direct execution). Rollback therefore turns the symlink into a regular file holding the referent's old bytes, while the referent keeps whatever `commit` wrote through it: a state that matches neither before nor after.
  evidence: Raised by both of this story's review passes and reproduced by execution: `CLAUDE.md -> real.md` containing `"REAL\n"`, a commit writing `"mat\n"` through the link, then a later failure, leaves `CLAUDE.md` a regular file containing `"REAL\n"` and `real.md` containing `"mat\n"`. Not fixed here: a correct fix snapshots link-ness (`os.readlink`) and restores through a symlink-aware primitive `seed/fs.py` does not offer, or refuses symlinked targets outright -- a precondition, which is Story 10.4's surface. `fs.py` itself already accepts this identical bound on the stated grounds that no real V1 target artifact is expected to be a symlink; the runner now states the same bound explicitly instead of inheriting it silently.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-4` there) during the pre-shutdown deferred-work audit.

### DW-10-3-5: An interrupt raised during rollback discards the list of paths rollback already knew it could not restore
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `_restore` catches `Exception`, not `BaseException`, so a `KeyboardInterrupt` arriving while rollback is running unwinds straight past `run_apply`'s inspection of its return value. The `unrestorable` list accumulated up to that point is thrown away with it, and the caller receives a bare `KeyboardInterrupt` -- maximum partial state with zero diagnostics about which paths are known broken.
  evidence: Raised by this story's Blind Hunter review and reproduced by execution: with three modified targets where the first restore raises `PermissionError` and the second raises `KeyboardInterrupt`, the caller sees only the interrupt, no `InternalError` and no path list, while all three files sit at the committed content and the third was never attempted. Not fixed here because every available remedy is worse than the gap and the choice is a real design decision, not a mechanical fix: aggregating into an `InternalError` would downgrade an interrupt to a catchable `SeedError` (independently flagged as harmful by the Edge Case Hunter, since an `except SeedError` caller would then swallow a Ctrl-C), and writing the list to stderr would put I/O into a library module whose whole taxonomy deliberately has none (`errors.py`: no formatting beyond `__str__`, no I/O). Belongs with whichever story owns operator-facing output for the seed verbs -- `seed/cli/seed.py`, which also owns exit-code dispatch.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-5` there) during the pre-shutdown deferred-work audit.

### DW-10-3-6: The never-write guard is applied to rollback restores, so a target `commit` wrote into a never-write path can never be put back
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `run_apply` passes the caller's `never_write` to its `fs.write`/`fs.remove` restore calls. `commit` is not obligated to honor the guard (the runner's own docstring says its violations merely propagate), so a `commit` that writes a never-write target leaves bytes the runner is then structurally forbidden to restore -- even though restoring ORIGINAL content is not a new write at all. The run ends in `InternalError` (exit 10, "restore by hand"), i.e. a guaranteed partial state, where an upfront check of every `action.target_path` against `never_write` could have refused with a zero-write `NeverWriteViolation` (exit 4) before the first `commit` ran.
  evidence: Raised by this story's Blind Hunter review; the behavior is pinned by this story's own test asserting that a never-write target is left holding the committed content with an `InternalError` naming it. Verified against `seed/fs.py`: `_guard` runs before any I/O in all three primitives, with no bypass parameter, so the restore genuinely cannot proceed. Not fixed here: the proposed remedy is a PRECONDITION evaluated before the first commit, and preconditions are explicitly Story 10.4's surface -- whose own epics `Surface:` line names this same `seed/apply/run.py` file, so it lands in exactly the right place one story later. This story's Never list scopes out every precondition but the fingerprint.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-6` there) during the pre-shutdown deferred-work audit.

### DW-10-3-7: A plan's fingerprint records no repo identity, so a plan built against one non-git directory applies cleanly to a different one
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `RepoFingerprint` carries `git_head`, `dirty`, and per-artifact hashes, but nothing naming the repo the plan was built against. For a non-git target both git fields degrade identically (`git_head=None`, `dirty=True`) in every directory, so a plan built against directory A and handed to `run_apply(plan, repo_root=B)` reports zero drift whenever B's artifacts happen to hash the same -- most easily when both are empty of the actioned artifacts, which is the common greenfield case. Genesis then seeds the wrong directory.
  evidence: Raised by this story's Edge Case Hunter review. Verified by reading `plan/types.py::RepoFingerprint` (three fields, no repo identity) and `plan/build.py::_git_head`/`_repo_is_dirty` (both degrade to the same values for any non-git directory, by design). Not fixed here: the fix adds a field to `RepoFingerprint`, whose module `plan/types.py` is listed as consumed-unmodified in this story's Code Map and named in its Never list -- and it changes the serialized `plan.json` wire shape, which is a Story 9.6 surface decision with its own round-trip tests, not an apply-runner one.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-7` there) during the pre-shutdown deferred-work audit.

### DW-10-3-8: `fingerprint_drift` performs an unguarded arbitrary-path read; containment lives only in its caller, and Story 10.4 owns that same file next
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `fingerprint_drift(plan, repo_root)` reads and hashes `repo_root / action.target_path` with no containment check of its own, and `Path(repo) / "/abs/path"` discards `repo` entirely -- so a hand-edited `plan.json` handed straight to the verifier reads any host file the process can open and reports its absolute path back in a drift string. `run_apply` happens to pre-screen every target before calling it, but that guard is the CALLER's, so any second caller inherits an unguarded read.
  evidence: Raised by this story's second review pass (Blind Hunter) and verified by execution: `fingerprint_drift` called directly with `target_path="/tmp/.../secret.txt"` read that file and returned a drift tuple naming the absolute path. Not fixed here: the story's Design Notes explicitly ACCEPT this direction as fail-closed for `run_apply`'s own use ("an entry whose path escapes `repo_root` ... may find a real file there and report drift ... refuses rather than proceeds"), and the containment check was deliberately placed in `run_apply` where a `PreconditionFailure` can be raised and surfaced. The residual risk is a FUTURE second caller, and Story 10.4's own `Surface:` line names `seed/apply/run.py` while also owning the precondition ladder -- so the natural fix (hoist containment into `fingerprint_drift`, or expose a shared `_resolve_within_repo`-style helper from `detect/inventory.py` that both call) lands with the story that adds the second caller, not before it.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-8` there) during the pre-shutdown deferred-work audit.

### DW-10-3-9: `build_plan` emits Actions whose `target_path` escapes `repo_root`, so one bad manifest entry makes `run_apply` refuse the entire plan with no reachable remedy
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-3-the-apply-runner-transactional-guarded.md`
  summary: `detect/inventory.py::_resolve_within_repo` returns `None` for a manifest entry whose `path` is absolute, traverses upward, or is an in-repo symlink pointing outside, and `_classify_entry` treats `None` as `ABSENT` -- so `build_plan` emits an ordinary `Action` still carrying the raw escaping path. `run_apply` must then refuse the WHOLE plan (`escaping-target`, exit 3), because the containment check is plan-wide and correctly runs before any write. A single malformed model-manifest entry therefore blocks apply for every artifact in the repo, and re-planning reproduces the identical plan.
  evidence: Raised by this story's second review pass (Edge Case Hunter) and verified by execution for all three shapes: `entry.path` of `/etc/hostname`, `../sibling.txt`, and an in-repo symlink to an outside file each classified `ABSENT`, each produced a normal `Action`, and each made `run_apply` raise. Partially addressed here: this story corrected the refusal's REMEDY, which previously asserted such a plan "did not come from `build_plan`" and told the operator to re-plan -- provably wrong advice that sends them around a loop producing the same plan; it now names the manifest entry as the thing that must change. Not fixed here: stopping the bad `Action` from being emitted at all (skip it, or classify it into an explicit refusal state) edits `detect/inventory.py` and `plan/build.py`'s classify path, both consumed-unmodified in this story's Code Map, and changes what every plan records rather than what apply checks. Belongs with whoever owns manifest validation -- the natural home is a model-manifest schema check that rejects a non-normalized `path` at load time, before detect ever sees it.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-9` there) during the pre-shutdown deferred-work audit.

### DW-10-4-1: A symlinked ancestor directory defeats the never-write guard, because the pattern is matched against the resolved destination path rather than the repo-relative one the operator wrote
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-4-preconditions-refusals-and-skips.md`
  summary: A symlinked ancestor directory defeats the never-write guard, because the pattern is matched against the resolved destination path rather than the repo-relative one the operator wrote.
  evidence: Raised by this story's Blind Hunter review and reproduced by execution: in a repo where `docs -> real/`, with `never_write=("docs/dreams/*.md",)`, an action targeting `docs/dreams/x.md` clears all six precondition rungs, because `_relative_within` resolves parent symlinks and the matched string becomes `real/dreams/x.md`. Not fixed here: the resolution semantics are inherited deliberately from `seed/fs.py::_guard`, which resolves both `path` and `repo_root` before matching and documents the consequence as an accepted trade -- so the gap is genuinely `fs.py`'s, and `fs.py` is on this story's Never list (narrowing the precondition alone would also make the gate and the write primitive disagree, which is worse than either behavior). The scope is wider than one rung: any repo that keeps `docs/` or `_bmad-output/` on another volume via a symlink silently loses Tier-0/Tier-2 never-write protection at BOTH the precondition and the write primitive. Whoever owns `fs.py` next should decide between lexical matching before resolution, matching both strings, or refusing a symlinked ancestor outright. This story softened its own refusal text so it no longer claims a protection stronger than the one `fs.py` actually provides.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-4` there) during the pre-shutdown deferred-work audit.

### DW-10-4-2: The new never-imported packaging ratchet cannot see `python-build`, the one exempted name its own docstring says the gate exists to cover
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-4-preconditions-refusals-and-skips.md`
  summary: The new never-imported packaging ratchet cannot see `python-build`, the one exempted name its own docstring says the gate exists to cover.
  evidence: Found independently by both of this story's review passes and confirmed by execution: `test_conda_only_run_deps_are_never_imported` intersects distribution names from `_conda_only(package)` with `_candidate_distributions(module)`; for pyforge-mason the exempt set contains `python-build` while `_candidate_distributions("build")` yields `{"build"}`, so the intersection is empty and `from build import ProjectBuilder` inside a mason function would keep the gate green while shipping a wheel that raises `ModuleNotFoundError`. `twine` and `conda-lock` are covered (`conda_lock` normalizes correctly); only this one name is not. The one-line remedy is a `MODULE_ALIASES` entry mapping the `build` import module to the `python-build` distribution. Not fixed here for a merge-safety reason specific to this run: `tests/packaging/test_dependency_completeness.py` was adopted byte-identical from the sibling branch `bmad-loop/20260814-202331-bc8d/10-3-the-apply-runner-transactional-guarded` precisely so the two branches merge without a conflict, and editing it here would forfeit that property and put two divergent versions of the same fix in the tree. It belongs to whoever lands that file -- one fix, in one place, once the two branches are merged.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-4-2` there) during the pre-shutdown deferred-work audit.

### DW-10-4-3: `ManagedRecord`'s region-bearing shape has no source in the state model Story 10.2 actually landed, so rung 6 cannot be wired for hybrid artifacts
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-4-preconditions-refusals-and-skips.md`
  summary: `ManagedRecord`'s region-bearing shape has no source in the state model Story 10.2 actually landed, so rung 6 cannot be wired for hybrid artifacts.
  evidence: Raised by this story's second Blind Hunter pass and verified against `main` after Stories 10.2 and 10.3 landed (both were unmerged siblings when this story was planned, so its contract could only treat `ManagedRecord` as an abstract input). `seed/state/store.py::ManagedArtifact` on `main` carries exactly `id`, `path`, `artifact_class`, `body_sha: str` and `inserted_region_span: RegionSpanRecord | None`, and `RegionSpanRecord` is `name` plus UTF-8 byte offsets -- it holds NO per-region sha and NO region format. This story's `ManagedRecord` requires `region_shas: Mapping[str, str]` and a `region_format` whenever `region_shas` is non-empty. There is therefore no total function from the landed state model to a region-bearing `ManagedRecord`: a caller loading real state for a `hybrid-managed-region` artifact can only build a whole-file record, which sends the single `body_sha` into `check_managed_file` against the hash of the WHOLE file, refusing on any human edit outside the managed region -- the edits the hybrid class exists to permit. The consequence is that `_region_divergences` and `check_managed_region` are unreachable from real state, so the region half of SC-04 is unmitigated at runtime even though it is fully implemented and tested here. Not fixable inside this story: its frozen contract states that `ManagedRecord` is an INPUT supplied by whoever loads state and puts every state-store concern on Story 10.2's surface, and both modules involved landed after this story's baseline `64e717d`. Belongs to the verb-wiring story (10.5/10.6/10.7) that first calls `check_preconditions` with real state, which must decide whether state grows a per-region sha and a region format, or whether the adapter recomputes region shas at load time from the recorded span.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-4-3` there) during the pre-shutdown deferred-work audit.

### DW-10-4-4: `managed_after_skips` cannot protect the artifact class rung 6 actually guards, because a hand-edited managed file never carries a plan action to be skipped
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-4-preconditions-refusals-and-skips.md`
  summary: `managed_after_skips` cannot protect the artifact class rung 6 actually guards, because a hand-edited managed file never carries a plan action to be skipped.
  evidence: Raised by this story's second Blind Hunter pass. `skips.managed_after_skips(managed, plan)` filters the caller's `ManagedRecord`s by `plan.skipped`, but only an artifact carrying an `Action` can ever enter `plan.skipped` -- and this story's own Design Notes argue at length that a hand-edited managed FILE never appears in the plan at all (`classify` marks a present `copied-managed` artifact `PRESENT_CONFORMANT` regardless of its bytes, per P-07, and `build_plan` emits actions only for `ABSENT` and `PRESENT_DIVERGENT`). The two facts together make the affordance inert for exactly the case it was added to serve: an operator who hand-edits a managed file and passes the skip pattern for it gets `plan.skipped == ()`, an unfiltered `managed` sequence, and the same rung-6 refusal, whose only offered override is `--force` -- which discards that very edit. The seam test added with it (`test_rung_six_refuses_a_skipped_artifacts_hand_edit_unless_the_caller_filters`) proves the helper only against a plan that contains an action for the hand-edited artifact, a shape `build_plan` cannot produce, so the suite stays green while the operator-visible behavior does not exist. Not fixed here: the working remedy is to filter by the skip PATTERNS rather than by `plan.skipped`, which changes the helper's signature, and whether patterns or `plan.skipped` is the natural caller-side input depends on how the verb wires `state.skips[]` -- a design decision owned by the wiring story, not a local patch. There is no production caller of `check_preconditions`, `apply_skips`, `record_skip` or `managed_after_skips` anywhere in `src/` today, so the operator-facing consequence is latent rather than live. Note for whoever takes it: this story's own Review Triage Log records the affordance as delivering the fix, which is the claim this entry corrects.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-4-4` there) during the pre-shutdown deferred-work audit.

### DW-10-4-5: An action whose target is an existing DIRECTORY clears all six precondition rungs and fails later as an untyped `IsADirectoryError` instead of a refusal with a remedy
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-10-4-preconditions-refusals-and-skips.md`
  summary: An action whose target is an existing DIRECTORY clears all six precondition rungs and fails later as an untyped `IsADirectoryError` instead of a refusal with a remedy.
  evidence: Raised by this story's second Blind Hunter pass. With `docs/` an existing directory and an action whose `target_path` is `docs`, rung 3 yields the repo-relative string `docs` (not the `.`/`""` the repo-root guard catches), rung 4 matches no never-write glob, rung 5's `lstat` finds a directory rather than a symlink, and rung 6 is unrelated -- so `check_preconditions` returns `None` and the apply runner reaches `os.replace(tmp, docs)`, which raises `IsADirectoryError`. That is an untyped crash escaping the `SeedError` taxonomy, where every other refusal in this ladder is a `PreconditionFailure` with exit code 3 and a non-blank remedy. This story added a repo-root check inside rung 3 for the `.`/`""` case, which is one instance of the directory-target class while declining the class itself -- deliberately, because the six-rung ladder and its fixed evaluation order are frozen inside this story's `<intent-contract>`, so adding a seventh structural check is a contract amendment rather than an implementation choice. Belongs with whoever next amends the ladder, or with the apply runner's own owner if the cheaper answer is for the writer to raise a typed error. Latent rather than live today: nothing calls `check_preconditions` in `src/` yet, and a manifest that declares a bare directory as an artifact target is itself unusual.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-4-5` there) during the pre-shutdown deferred-work audit.

### DW-14-1-1: `pyforge-core/.gitignore`'s `/dist/` and `/dist-conda/` lines carry inline comments gitignore cannot parse, so both patterns are dead and those directories are not actually ignored
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-14-1-the-leaf-exists-and-is-provably-a-leaf.md`
  summary: `src/shared/packages/pyforge-core/.gitignore` reads `/dist/          # pypi: wheel + sdist (python -m build)` and `/dist-conda/    # conda: .conda (pixi build --output-dir dist-conda)`. `.gitignore` has no trailing-comment syntax, so the `#`-onward text is part of the literal pattern on each line, which then matches nothing — verified with a throwaway `git init` repro and directly in this worktree via `git check-ignore`/`git add -n`. Only the file-extension globs later in the same file (`*.conda`, `*.whl`, `*.tar.gz`, `*.egg-info/`) actually protect those two directories in practice; a non-extension-matching build byproduct written under `dist/` or `dist-conda/` (e.g. a wheel's loose `PKG-INFO`, a conda build's `repodata.json`) would show as untracked and could be accidentally staged.
  evidence: Surfaced by the Blind Hunter adversarial review pass over this story's diff (independent, no shared context with the Edge Case Hunter reviewer). This story's `.gitignore` was written by mirroring `pyforge-scribe/.gitignore` byte-for-byte per the spec's own instruction, which carries the identical broken pattern — and this exact defect (for `pyforge-doctor`/`pyforge-warden`) is already recorded as still-open in this same file's own 2026-07-29 reconciliation note above (Story 1.1's original entry 2). Not fixed here: this story's copy is one more instance of a fleet-wide pattern now present in most `src/shared/packages/*/.gitignore` files; fixing only `pyforge-core`'s copy would diverge it from its siblings for no benefit, and the real fix is a one-sweep correction across every package's `.gitignore` (move each comment to its own line), which is a repo-tooling change outside this story's own scaffolding-only surface.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-1` there) during the pre-shutdown deferred-work audit.

### DW-14-2-1: story deferred at the dev verify-gate — substantive work committed locally but never merged, blocked on cross-spec spec-surface reconciliation
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-14-2-atomic-write-has-one-implementation.md`
  summary: Run `20260811-190409-5c73`'s dev-2 attempt for 14-2 completed real work — committed locally in the story's own worktree (`1d60da0193 Story 14.2: consolidate atomic-write into pyforge-core (CAP-2, CAP-7)`, 20 hand-written atomic-write copies across 6 stations retired into one `pyforge-core` primitive, all test suites green per the session's own summary) — but its verify command `python scripts/spec_surface_reconcile.py` exited rc=1 with 28 findings: governed files changed under BOTH `pyforge-marshal/spec-pyforge-marshal` (`cli/config.py`, `adapters/harness_bmadloop.py`, `tests/meta/test_manifest_sync.py`, `tests/unit/test_fs_local.py`) and `pyforge-steward/spec-pyforge-steward` (`budget.py`, `keys.py`, `pixi.toml`, `pyproject.toml`) without either spec's `.memlog.md` naming the changes first. With `max_dev_attempts: 2` exhausted, the orchestrator deferred the story (`kind: story-deferred`, `action: defer`) and the run's already-pending `--graceful` stop then took effect immediately after. The commit itself was NEVER merged into `loop/pyforge-marshal` — it exists only in the story's own worktree at `~/.bmad-loops/pyforge-marshal/.bmad-loop/runs/20260811-190409-5c73/worktrees/14-2-atomic-write-has-one-implementation` (kept, per `journal.jsonl`'s `worktree-kept` entry) plus a safety-net backup at `~/.bmad-loops/pyforge-marshal/.bmad-loop/runs/20260811-190409-5c73/failed/14-2-atomic-write-has-one-implementation/changes.patch`.
  evidence: Diagnosed live 2026-08-12/13 by reading `state.json`, `journal.jsonl`, the dev-2 session log, and the story worktree's own `git log`/`git status` directly (`journal.jsonl` line: `{"kind": "dev-decision", ..., "reason": "verify command failed (rc=1): python scripts/spec_surface_reconcile.py\n... FINDINGS (28): ..."}` followed by `{"kind": "story-deferred", ...}`, `{"kind": "unit-closed", ..., "kept": true, "patch": ".../changes.patch"}`, `{"kind": "run-stop", "graceful": true, "remaining": 43}`). Not fixed here: reconciling spec-surface drift across two specs and deciding whether/how to hand-finish landing the preserved commit is a real intervention (edit both specs' `.memlog.md`, scoped-stamp both, then either resume the run or manually complete the landing pipeline) that the operator explicitly deferred pending their own decision — see the auto-memory session-close entry for the standing options.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-2` there) during the pre-shutdown deferred-work audit.

### DW-14-3-1: Doctor and Steward still carry un-reparented exception roots outside Story 14.3's CAP-5 scope
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-14-3-one-lattice-one-envelope-one-exception-root.md`
  summary: Doctor's `cli_bridge.py::CliBridgeError`/`sources/atlas.py::_FetchFailed` and seven Steward exception roots across `budget.py`/`dashboard/cache.py`/`dashboard/export.py`/`dashboard/middleware.py`/`deploy.py`/`keys.py`/`sync.py` do not inherit `pyforge.core.errors.PyforgeError`, unlike the 39 classes (herald, mason, warden, marshal, atlas) this story re-parented.
  evidence: Confirmed live while authoring this story's exception-root sole-ownership meta-test (`pyforge-core/tests/meta/test_exception_root_sole_ownership.py`): running its AST detector fleet-wide, before scoping the scan to exclude `pyforge-doctor`/`pyforge-steward`, found these 9 real, un-reparented root classes. Neither station is named in SPEC-pyforge-core CAP-5's original census (herald, mason, warden, marshal, atlas only) or this story's own Boundaries roster -- confirmed 1:1: every hit outside the two excluded stations corresponds exactly to a class in the roster, and every roster class is covered. Not fixed here: the guard's `_OUT_OF_SCOPE_STATIONS` exclusion documents this explicitly; a future story extending CAP-5 to doctor/steward should re-parent these 9 classes and remove that exclusion in the same change.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-3` there) during the pre-shutdown deferred-work audit.

### DW-14-4-1: Herald, Mason, and Scribe carry real, un-migrated subprocess implementations outside Story 14.4's CAP-6 scope
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-14-4-the-subprocess-seam-is-reconciled-and-sole-ownership-is-gated.md`
  summary: Herald's `transport/agent_sdk_transport.py` + `deck_pipeline.py`, Mason's `cfe.py` + `engines/__init__.py`, and Scribe's `compile.py` each call `subprocess` directly with no local sole-ownership guard, discovered by this story's new fleet-wide `pyforge-core` subprocess guard and excluded from it rather than migrated.
  evidence: Confirmed live while authoring `pyforge-core/tests/meta/test_process_sole_ownership.py`'s fleet-wide scan (Story 14.4): before excluding these three stations the detector fired on real, non-synthetic `subprocess.run`/`Popen` call sites in each. Unlike Doctor (its own already-working `test_cli_bridge_sole_subprocess.py`) and Warden/Steward (named in this story's own Boundaries), none of the three had a local guard filling the gap, and Mason's `test_adapter_sole_caller.py` polices CFE-path references specifically, not general subprocess ownership. Not fixed here: CAP-6's success text names only Marshal for mandatory migration; a future story extending CAP-6 to any of the three should either migrate it to `pyforge.core.process` or add a local sole-site guard, removing its entry from `_OUT_OF_SCOPE_STATIONS` in the same change.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-4` there) during the pre-shutdown deferred-work audit.

### DW-14-4-2: AD-4's import-linter contract has a verification blind spot for pyforge-core's own internal os/subprocess imports
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-14-4-the-subprocess-seam-is-reconciled-and-sole-ownership-is-gated.md`
  summary: Marshal's `core/gate.py` and `core/status.py` now import `ProcessResult` from `pyforge.core.process`, a module that itself imports `os`/`subprocess` at module scope -- but `lint-imports` (grimp-based) reports 0 broken because grimp collapses the external `pyforge.core` package to a single leaf node and never expands into `pyforge.core.process`, so AD-4's `core/**` purity contract has a verification blind spot for any external package's own internal imports.
  evidence: Confirmed live during this story's review pass: `g.find_shortest_chain('pyforge.marshal.core.gate', 'os')` returns `None` even though the transitive import genuinely exists, because `pyforge.core.process` isn't even present in the built grimp graph. The actual behavioral invariant still holds (`core/gate.py` and `core/status.py` only ever reference the pure `ProcessResult` dataclass, never instantiate or call `PosixProcess`) -- this is a verification-tooling gap, not a live purity violation, but it means a FUTURE `pyforge-core` addition that imports `os`/`subprocess` would be equally invisible to this check. Not fixed here: reconfiguring the import-linter/grimp contract to expand into external packages' own internals is a fleet-wide tooling change spanning more than this story's subprocess-guard scope.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-4-2` there) during the pre-shutdown deferred-work audit.

### DW-2-8-1: epics.md's Story 2.8 entry omits the **Surface:** line every sibling Epic-2 story carries
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-2-8-a-low-risk-storys-review-runs-lighter-never-absent-2.md`
  summary: `_bmad-output/planning-artifacts/epics.md`'s "Story 2.8: A low-risk story's review runs lighter, never absent" section has no `**Surface:**` line, even though every sibling Epic-2 story (2.1-2.7) carries one and the governing `SPEC.md` (`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-risk-tiered-review-depth/SPEC.md`) already unambiguously scopes `surface: [core/gate.py]`. That line is the one signal that would let a reader tell "CLI/envelope wiring is a deliberate follow-on story" from "wiring was simply forgotten" without cross-referencing the SPEC by hand. Pre-existing in `epics.md`, outside this story's own Code Map (`core/gate.py`, its two test files, `deferred-work.md`) -- not fixed here.
  evidence: Surfaced by the Blind Hunter adversarial review pass over this story's diff (independent, no shared context with the Edge Case Hunter). Confirmed live: `grep -n "Surface:" _bmad-output/planning-artifacts/epics.md` shows a `**Surface:**` line for Stories 2.1 through 2.7's sections but none for Story 2.8's own section between its "Why now" paragraph and its Acceptance Criteria.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-2-8` there) during the pre-shutdown deferred-work audit.

### DW-3-12-1: A resumed run's retry-escalation ceilings are read from whatever policy.toml is on disk now, not the policy that governed while a story accumulated its attempt/review_cycle count
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-3-12-a-struggling-retry-runs-under-a-stronger-model.md`
  summary: `cli/spin.py::_apply_retry_escalation` reads `max_dev_attempts`/`max_review_cycles` off `.bmad-loop/policy.toml` as it exists AT RESUME TIME, and compares them against `DeferredStory.attempt`/`.review_cycle` -- counters that accumulated under whatever policy governed the ORIGINAL launch. If an operator re-renders the loop home's policy between a story's deferral and its resume (e.g. `marshal config --write-harness-policy`, or a later `factory spin` for a different story in the same home), raising either ceiling, a story that genuinely exhausted the LOWER, original ceiling can silently stop qualifying for escalation on its next resume -- the mechanism evaluates against a ceiling the story never actually operated under.
  evidence: Confirmed via direct code reading during Story 3.12's review pass (Blind Hunter). `_apply_retry_escalation` (`cli/spin.py`) has no path back to the policy that was in effect when `run_spin` originally launched the run -- only the CURRENT on-disk file. This is a known, accepted trade-off of the story's own deliberate design choice (documented in the spec's Design Notes: "read the on-disk policy.toml rather than re-run policy.compose()... reflects exactly what THIS run was launched under, never a possibly-diverged current project policy" -- true only for the FIRST resume after any given render, not across an intervening re-render). Not fixed here: resolving this needs either persisting the launch-time ceilings alongside the run's own state (a new field on `RunState`/journal, `bmad_loop`-adjacent and out of this story's `cli/spin.py`-only surface) or accepting the drift as a documented limitation -- a design call for a follow-up story, not a mechanical patch to this one.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-3-12` there) during the pre-shutdown deferred-work audit.

### DW-3-12-2: A newly-struggling story is never named in the escalation journal once a resumed run's model is already floor-raised
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-3-12-a-struggling-retry-runs-under-a-stronger-model.md`
  summary: `cli/spin.py::_apply_retry_escalation`'s `from_model == to_model` idempotence short-circuit (the mechanism's own "bounded, never re-fires" guarantee) returns `False, [], None, None` immediately once the on-disk `[adapter].model` already equals `[adapter.review].model`, WITHOUT recomputing which deferred stories are currently crossing their ceiling. If a DIFFERENT story newly crosses its own ceiling on a resume where the model is already escalated (from an earlier trigger), that new crossing is never named in `escalated_stories`/the journal for that resume -- the correct model is already running, but the record of WHO justified it stays incomplete after the first write.
  evidence: Confirmed via direct code reading during Story 3.12's review pass (Edge Case Hunter). The mechanism's functional guarantee (a struggling story's next attempt runs under a floor-raised model) still holds -- this is a completeness gap in the journal's own "naming the trigger" AC, not a correctness defect in the escalation itself. Not fixed here: recomputing and always returning `escalated_stories` regardless of whether a NEW write occurred would change the established return-contract shape ("populate detail fields only when `escalated: true`", mirroring `story_key`/`resolution_reference`'s own precedent elsewhere in `run_resume`) -- a deliberate design call for a follow-up story rather than a rushed patch to this one.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-3-12-2` there) during the pre-shutdown deferred-work audit.

### DW-3-12-3: A model-tiering policy.toml write can land on disk before its own launch/resume intent is journaled, in both run_spin and run_resume
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-3-12-a-struggling-retry-runs-under-a-stronger-model.md`
  summary: `cli/spin.py::run_resume` calls `_apply_retry_escalation` (which durably rewrites `.bmad-loop/policy.toml` when escalation fires) BEFORE `mint_run_id`/`create_dir_exclusive`/the intent `_append_entry` for the resume itself. If run-directory creation or the intent append then fails, the floor-raise has already taken effect on disk with zero journal record of it. This is not a new pattern introduced by Story 3.12: `run_spin`'s own pre-existing `_resolve_model_tiering` (Story 6.1/3.11-adjacent) has the IDENTICAL ordering -- its `write_policy_toml` call also lands before that launch's own intent entry.
  evidence: Confirmed via direct diff comparison during Story 3.12's review pass (Blind Hunter). `_resolve_model_tiering` is called from `run_spin` before that function's own `mint_run_id`-and-intent-journal sequence, the same shape `_apply_retry_escalation` now mirrors in `run_resume`. The reviewer who raised it explicitly noted it "isn't a novel defect" but that Story 3.12 "extends the same unaudited-mutation risk to a second, more consequential write (one that changes which model the NEXT engine process uses)". Consequence is bounded in practice: a lost journal entry does not lose the escalation itself (the file is already written), only the evidentiary record of why -- and a later resume's own read-back would simply find the model already at its floor-raised value (idempotent, no re-fire). Not fixed here: reordering either call site to write-after-journal is a shared fix across BOTH `_resolve_model_tiering` (run_spin) and `_apply_retry_escalation` (run_resume), out of this story's own narrower Surface.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-3-12-3` there) during the pre-shutdown deferred-work audit.

### DW-3-12-4: A TOML serialization failure ahead of the atomic policy.toml write is never wrapped in HarnessPolicyWriteError, in both write_policy_toml and its new sibling write_policy_document
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-3-12-a-struggling-retry-runs-under-a-stronger-model.md`
  summary: `adapters/harness_bmadloop.py::write_policy_document`'s `tomlkit.dumps(doc)` call runs OUTSIDE `_atomic_write_policy_text`'s own try/except, so a serialization failure there would propagate as a raw exception rather than the `HarnessPolicyWriteError` `cli/spin.py::_apply_retry_escalation` explicitly catches to degrade to `MRS-SPIN-016` (WARN). This mirrors a PRE-EXISTING shape: `write_policy_toml`'s own `render_policy_toml(...)` call (which itself calls `tomlkit.dumps` internally) is equally unwrapped, and predates this story.
  evidence: Confirmed via direct code reading during Story 3.12's review pass (Edge Case Hunter). `write_policy_document`'s body is `text = tomlkit.dumps(doc); return _atomic_write_policy_text(text, loop_home)` -- the `dumps` call is not inside the try. `write_policy_toml`'s own body has the identical shape (`text = render_policy_toml(...)` before the same `_atomic_write_policy_text` call), confirmed unchanged by this story's diff. Practical risk is low: `tomlkit.dumps` over a document already successfully round-tripped through `tomlkit.parse` plus one scalar-string key assignment is not a realistic failure mode in normal operation. Not fixed here: widening the try/except (or moving the dumps call inside it) is a shared fix across both functions, out of this story's own narrower Surface, and belongs with DW-FU-3-12-3's write-ordering fix as one coordinated hardening pass over `_atomic_write_policy_text`'s two callers.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-3-12-4` there) during the pre-shutdown deferred-work audit.

### DW-3-13-1: Policy-vocabulary key-count literals in cli/config.py's comments and two test names were already stale before this story added an 11th seed key adjacent to them, and are not self-correcting
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-3-13-the-parallel-fan-out-clamp-is-surfaced-not-silent.md`
  summary: `cli/config.py`'s `_UNSETTABLE_KEYS` comment block ("Naming any of these 9 keys on `--set` is a usage error") and two test function names, `tests/unit/test_cli.py::test_config_prints_all_twenty_keys` and `tests/unit/test_policy.py::test_schema_file_declares_the_twenty_keys`, hardcode a key-count in prose/identifiers that does not track `core/policy.py::_ALL_KEYS`'s actual size and was already wrong before this story -- the frozenset held far more than 9 members and the real count was already 22, not 20, prior to Story 3.13's `max_parallel` addition.
  evidence: Confirmed live in this checkout: `cli/config.py:103-104`'s comment reads "Naming any of these 9 keys..." immediately above a frozenset literal (`_UNSETTABLE_KEYS`) that already held well over 9 members before this story's edit. Both test names were touched by this story's own diff (their docstrings/assertions were bumped from "22"/"now 22" to "23"/"now 23") without renaming the functions themselves, unlike the sibling `test_seed_view_returns_all_ten_seed_fields` -> `test_seed_view_returns_all_eleven_seed_fields` rename landed in the same diff -- proving the renaming convention is known in this codebase, just not applied uniformly to every touched count-named test. Surfaced by the Blind Hunter review pass over Story 3.13's diff (independent, no shared context with the Edge Case Hunter reviewer). Not fixed here: correcting the `_UNSETTABLE_KEYS` comment's stale "9" and renaming two test functions is pre-existing drift this story's own diff sits adjacent to but did not cause, out of Story 3.13's `max_parallel`-only Surface.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-3-13` there) during the pre-shutdown deferred-work audit.

### DW-5-10-1: A malformed `merge_subject_template` (missing or duplicate `{key}` placeholder) crashes `marshal land`'s full-merge path with an uncaught `ValueError`, now reachable through a higher-traffic, automated command
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-10-marshal-land-renders-a-detectable-merge-subject.md`
  summary: `cli/land.py::run_land`'s new call `identity.render_merge_subject(wave_keys[0], template)` is not wrapped in any try/except, matching `deploy.py::run_land_story`'s existing identical, unguarded call by deliberate design (this story's own Boundaries: "mirror that precedent exactly rather than giving `land` new handling `land-story` lacks"). `core/policy.py::_valid_merge_subject_template` only validates a non-empty `str` -- it never checks for the required single `{key}` placeholder -- so a project's `merge_subject_template` policy value missing (or duplicating) `{key}` passes policy composition cleanly and then raises a bare `ValueError` out of `render_merge_subject`'s `_split_template` helper, crashing the whole command with a raw traceback instead of a reported `Finding`.
  evidence: Surfaced independently by both the Blind Hunter and Edge Case Hunter review passes over this story's diff (same underlying root cause, reported from two angles). Confirmed live: `identity.render_merge_subject(StoryKey(4, 4), "Merge into main")` (a template with no `{key}` placeholder) raises `ValueError: template must contain exactly one '{key}' placeholder...`. Pre-existing gap in `core/policy.py::_valid_merge_subject_template` (out of this story's own Surface, which is `cli/land.py`/`ports/forge.py`/`adapters/forge_gh.py` only) -- `deploy.py::run_land_story` already carries the identical unguarded call site and crash risk today; this story adds a SECOND call site through `marshal land`'s own batch/automated path (higher traffic than the single-story `land-story` command), widening the blast radius of an already-latent gap rather than introducing a new one. Not fixed here: closing it means either validating the placeholder shape in `core/policy.py::_valid_merge_subject_template` (a `core/` change outside this story's Surface) or wrapping both call sites in a new caught-and-reported error path (a behavior change to `deploy.py::run_land_story` this story's own Never bullet explicitly forbids) -- either fix is a cross-cutting change touching code this story is bounded not to touch.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-10` there) during the pre-shutdown deferred-work audit.

### DW-5-10-2: A multi-key `marshal land` wave under `landing_merge_strategy: squash` or `rebase` renders its subject from the wave's primary key only, leaving the wave's other keys exactly as undetectable as before this story
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-10-marshal-land-renders-a-detectable-merge-subject.md`
  summary: `run_land` renders `subject = identity.render_merge_subject(wave_keys[0], template)` -- the wave's lowest-sorted key only, per this story's own Design Notes (`identity.render_merge_subject`/`parse_merge_subject` are AD-24's fixed single-`{key}`-placeholder pair, and this story's Surface deliberately excludes `core/identity.py`/`core/promotion.py`, so no multi-key form exists). Under the default `"merge"` strategy the non-primary keys' own already-existing bmad-loop-native commit subjects remain ancestors of `main` after the merge and are independently classified by `marshal_native_merged_keys` regardless of this commit's own subject (as the Design Notes already state) -- but under `"squash"`/`"rebase"`, `cli/land.py::_resync_home_branch`'s own docstring already documents that "the landed commits are never ancestors of `origin/<base>` ... BY CONSTRUCTION" for those two strategies, so a squash merge's non-primary wave keys have no fallback detection path at all, remaining permanently unclassified via this mechanism (though a `rebase` strategy DOES preserve each original commit's own subject verbatim on `main`, so its non-primary keys stay detectable via the pre-existing bmad-loop-native pattern independent of this gap -- only `squash` genuinely loses them).
  evidence: Surfaced by the Blind Hunter adversarial review pass over this story's diff. Confirmed via direct code reading of `_resync_home_branch`'s own docstring and `core/identity.py::_split_template`'s single-placeholder contract. Not a regression: before this story, ZERO wave keys were ever classified via the merge commit's own subject (no subject was ever rendered), so covering the primary key only is a strict improvement, never worse than the prior state, for every strategy including squash. Not fixed here: giving every wave key its own detectable trace under `squash` needs either a multi-key subject form (a `core/identity.py` change this story's Surface explicitly excludes) or a different detection mechanism entirely (e.g., an explicit per-key marker committed alongside the squash), both larger, cross-cutting changes out of this story's own bounded (Effort: S) scope; Story 5.9's own measured history shows `marshal land` waves are overwhelmingly single-key in practice, and `squash`/`rebase` are non-default `landing_merge_strategy` values.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-10-2` there) during the pre-shutdown deferred-work audit.

### DW-5-10-3: `gh pr merge --subject`'s `commitHeadline` has no merge commit to title under `landing_merge_strategy: rebase`, so a rebase-strategy landing's rendered subject is silently inert rather than actually applied anywhere
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-10-marshal-land-renders-a-detectable-merge-subject.md`
  summary: `run_land` passes the rendered `subject` to `forge.merge_pr` unconditionally, for every `landing_merge_strategy` value, per this story's own Boundaries ("`gh pr merge -t/--subject` applies uniformly across `--merge`/`--squash`/`--rebase`" -- a claim inherited from epics.md's own Story 5.10 text, "Confirmed low-risk: `gh pr merge` already supports `-t/--subject` for every strategy"). Verified live against GitHub's own GraphQL schema (`gh api graphql` introspection of `MergePullRequestInput`) that `commitHeadline`'s own description reads "Commit headline to use for **the merge commit**; if omitted, a default message will be used" -- and a `REBASE` merge, by definition, creates NO new merge commit at all (each original commit is replayed onto the base branch with its own preserved subject). `gh`'s own CLI source (`pkg/cmd/pr/merge/merge.go`/`http.go`) confirms `commitSubject` is sent unconditionally in the mutation input for all three merge methods, with no method-conditional guard -- so the flag is accepted without error for `rebase`, but has nothing to apply to: the API accepts it and silently does nothing with it. `data["subject"]` in `run_land`'s own envelope therefore reports a subject for a rebase-strategy landing that was never actually written to any real commit -- though the wave's original commits (already carrying their own preserved subjects, e.g. bmad-loop-native form) remain independently detectable via the pre-existing pattern-3 match in `marshal_native_merged_keys`, unaffected by this gap, so the story's actual detectability GOAL is still met for `rebase` by a different, already-existing mechanism; only the new `subject` parameter itself is a harmless no-op for that one strategy.
  evidence: Surfaced independently by both the Blind Hunter and Edge Case Hunter review passes over this story's diff (same underlying concern, reported from two angles: one flagging the docstring's unverified cross-strategy claim, the other flagging the unconditional pass-through with no method gate). Confirmed via live `gh api graphql` schema introspection (`MergePullRequestInput.commitHeadline`'s own description) and `gh`'s own public source (`cli/cli` `pkg/cmd/pr/merge/merge.go`'s `allowEditMsg := payload.method != PullRequestMergeMethodRebase` in the interactive path, `http.go`'s unconditional `input.CommitHeadline` assignment in the non-interactive path) during this review pass -- not a speculative concern. Not fixed here: `ports/forge.py`'s docstring wording was corrected in this same pass (a doc-only, non-behavioral patch) to describe the rebase case accurately instead of claiming uniform effect; deciding whether `land` should SKIP passing `subject` for `rebase` (to avoid a misleading `data["subject"]` value in that one case) is a small but real behavior change this bounded review pass declined to make unilaterally, since `landing_merge_strategy: rebase` is a non-default, apparently unused-in-practice value across this fleet's own projects and the actual detectability outcome is unaffected either way.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-10-3` there) during the pre-shutdown deferred-work audit.

### DW-5-8-1: `is_run_live`, which gates `marshal land`'s branch retirement off the same `FleetHomeFacts` this story extends, never consults the new `engine_alive` signal
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-8-a-dead-supervisor-sidecar-doesnt-hide-a-live-engine.md`
  summary: `core/status.py::is_run_live` (Story 4.11's own landing-safety predicate `cli/land.py` uses to refuse retiring a branch out from under a live run) still returns `not facts.finished and facts.supervisor_alive is True` -- exactly the "dead sidecar = not live" verdict `derive_home_state` used to give before this story's fix, consulting only `supervisor_alive`, never the new `facts.engine_alive`. In precisely this story's own motivating scenario (a dead supervisor sidecar behind a genuinely live, in-flight engine -- the 2026-08-11 incident), `is_run_live` returns `False`, so `marshal land` would treat the branch as safe to retire while a real run is still actively using it.
  evidence: Surfaced by the Blind Hunter adversarial review pass over this story's diff. Confirmed via direct code reading: `is_run_live`'s body (`core/status.py`) is unchanged by this story's diff and reads `facts.supervisor_alive` only; `cli/land.py` gates branch deletion on its return value. `is_run_live`'s own docstring explicitly names its purpose as preventing "a live 9-story run, avoided only because a human read the source first" -- the exact class of incident this gap reopens for the dead-sidecar-alive-engine case. Not fixed here: this story's own Boundaries explicitly scope it to `derive_home_state`'s fleet-status reporting and name `is_run_live`/`cli/land.py` as out of scope ("Its own docstring already documents why it deliberately never calls `derive_home_state`; extending it to consult engine liveness is a separate, unscoped change this story does not make") -- resolving it requires a design decision about whether `is_run_live` should consult `engine_alive` directly or via some other mechanism, which belongs to a dedicated follow-up story, not a rushed patch to this one's `derive_home_state`-focused surface.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-8` there) during the pre-shutdown deferred-work audit.

### DW-5-8-2: `ProcessPort.is_alive`'s bare pid-existence probe has no identity/start-time corroboration and admits a degenerate `pid: 0` journal entry as "alive", now consulted for a second, verdict-flipping signal
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-8-a-dead-supervisor-sidecar-doesnt-hide-a-live-engine.md`
  summary: `adapters/process_posix.py::ProcessPort.is_alive` is a bare pid-existence check (`os.kill(pid, 0)`-equivalent) with no process start-time or identity cross-check, so OS pid reuse can make a genuinely-dead process read as alive; a malformed/degenerate journaled `"pid": 0` entry passes the existing `isinstance(candidate, int) and not isinstance(candidate, bool)` validation and `is_alive(0)` reads `True` (signals the caller's own process group) rather than "unprobed". This risk pre-dates this story for `supervisor_alive`, but this story extends the same unguarded probe to `engine_alive` and gives it new leverage: a false-alive reading can now flip `derive_home_state`'s verdict from `"unsupervised"` to a healthy state outright, in tension with this story's own "narrows a false positive, never softens a real one" constraint.
  evidence: Surfaced independently by both the Blind Hunter and Edge Case Hunter review passes over this story's diff (same underlying concern, reported from two different angles: pid reuse and the pid-0 degenerate case). Confirmed via direct code reading: `adapters/process_posix.py::is_alive` performs no start-time comparison; `cli/status.py::_gather_run_journal_facts`'s payload validation for both `launch_pid` and `supervisor_pid` is identical (`isinstance(candidate, int) and not isinstance(candidate, bool)`), which lets `0` through for either. Not fixed here: hardening `is_alive` (e.g. via `/proc/<pid>/stat` start-time comparison against the journaled timestamp, or rejecting non-positive pids before probing) is a shared, cross-cutting change to a primitive already used identically for `supervisor_alive` since Story 3.4/5.1 -- out of this story's own `derive_home_state`/`FleetHomeFacts`-focused surface, and belongs to a dedicated hardening story for `ProcessPort.is_alive` itself rather than a narrow patch to this one's engine-liveness consumer.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-8-2` there) during the pre-shutdown deferred-work audit.

### DW-5-8-3: `tests/packaging/test_dependency_completeness.py`'s `BASELINE_UNDECLARED_IMPORTS` ratchet is a shared, repo-wide file with no cross-worktree land convention, unlike its `pixi.toml`/`environment.yaml` sibling
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-8-a-dead-supervisor-sidecar-doesnt-hide-a-live-engine.md`
  summary: This story's verification repair pass added a `pyforge-steward: {"django": ...}` entry to `BASELINE_UNDECLARED_IMPORTS` (a single shared dict in a repo-root test file) to close a pre-existing, unrelated `pyforge-deps-test` failure (Story 9.1's `dashboard/apps.py`/`cache.py`) blocking this story's own land -- the same class of repair `20ad57a62f` already made once for a different marshal story. Because this repo runs many concurrent bmad-loop worktrees off the same `main` (per this repo's own `CLAUDE.md` parallel-agent documentation), every other worktree forked before this lands and independently hitting the same `pyforge-deps-test` failure is likely to add its own similarly-shaped but not-identical entry for the same `pyforge-steward: django` key, producing a merge collision or, if merged blind, a duplicate/overwritten dict entry -- unlike the analogous `pixi.toml` case, which `CLAUDE.md` already instructs to "fix main directly whenever a `pixi.toml` dep change lands there" specifically to avoid this.
  evidence: Surfaced by the Blind Hunter adversarial review pass over this story's repair diff (independent, no shared context with the Edge Case Hunter reviewer, who separately confirmed the entry itself is genuine and correctly shaped). Confirmed via direct reading of `CLAUDE.md`'s "PARALLEL AGENTS" and pixi.toml-sync sections, which document this exact class of shared-global-state race for other files but do not mention `tests/packaging/test_dependency_completeness.py`. Not fixed here: deciding whether `BASELINE_UNDECLARED_IMPORTS` repairs should also land on `main` directly (mirroring the `pixi.toml` convention), or whether some other de-duplication mechanism is warranted, is a repo-tooling/process decision outside this story's `derive_home_state`/`FleetHomeFacts`-focused surface and requires its own scoped follow-up.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-8-3` there) during the pre-shutdown deferred-work audit.

### DW-5-9-1: Two distinct raw sprint-status-ledger.yaml keys that both normalize to the identical StoryKey silently collapse in reconcile-completions's raw-key index, under-rewriting the ledger while over-reporting the advance
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger.md`
  summary: `cli/deploy.py::run_reconcile_completions` builds `raw_key_by_dot: dict[str, str]` by iterating the tracked ledger's raw `(raw_key, raw_status)` pairs and keying on each raw key's normalized dot-form `StoryKey`. If the ledger ever carries two DIFFERENT raw keys that both normalize to the SAME `StoryKey` (a malformed/duplicate-keyed ledger), the dict collapses to last-write-wins: `render_ledger_advancements` rewrites only one of the two matching lines, while `data["advanced"]`/`data["advanced_count"]` still report the key as fully advanced -- an over-reporting mismatch between what the envelope claims and what the file actually reflects.
  evidence: Surfaced by the Edge Case Hunter adversarial review pass over this story's diff (independent, no shared context with the Blind Hunter reviewer). Confirmed via direct code reading: `raw_key_by_dot[dot_key] = raw_key` inside the single `for raw_key, raw_status in raw_statuses` loop has no duplicate-key detection, and `render_ledger_advancements` is handed only the SET of raw keys to advance (`raw_keys_to_advance`), which cannot distinguish "the one true raw key for this story" from "one of several colliding raw keys" once the dict has already collapsed. Not fixed here: this requires a genuinely malformed/hand-corrupted ledger to trigger (this repo's own generators -- `promote_sprint_status.py`, `bmad-quick-dev`'s `sync-sprint-status.md` -- never produce two raw keys for the same story) and reproducing it needs either a duplicate-key detection pass over `raw_statuses` (reporting a new finding) or a design decision about which of the colliding raw keys is authoritative, out of this story's own bounded patch-pass scope.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-9` there) during the pre-shutdown deferred-work audit.

### DW-5-9-2: `cli/deploy.py::run_promote` reports a story key in `data["promoted"]` even when the `commit_paths` that would make the promotion durable failed, so the envelope claims a durable promotion that exists only as an uncommitted working-tree copy
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger.md`
  summary: In `run_promote`'s promotion loop, `promoted.append(str(spec_candidate.story_key))` runs immediately after a successful `fs.copy_file`, BEFORE the batched `vcs.commit_paths` that actually makes the copy durable. When `commit_paths` raises `VcsCommandError`, the handler appends an `MRS-DEPLOY-003` ERROR finding but never removes the affected keys from `promoted`, so `data["promoted"]`/`data["promoted_count"]` still publish every key in the batch as promoted while only an uncommitted copy exists on disk. This is the same "pre-write eligibility published as post-write outcome" defect class that Story 5.9's own review pass 1 fixed for its `data["advanced"]` field, left unfixed on the sibling `promoted` field in the same envelope shape.
  evidence: Surfaced by the Edge Case Hunter adversarial review pass over Story 5.9's diff (independent, no shared context with the Blind Hunter reviewer). Confirmed pre-existing and NOT introduced by Story 5.9 via direct reading of `git show main:src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py`, where the same ordering is already present on `main` (the `promoted.append(...)` at the end of the copy loop, and the `commit_paths` failure handler that only appends a finding). Story 5.9's own code was subsequently reverted in full for an unrelated intent-contract gap, so this defect survives that revert untouched and remains live on `main` today. Not fixed here: it is a pre-existing defect in `run_promote`'s own envelope contract, surfaced only incidentally by this story's review, and correcting it means deciding whether a partially-committed batch should report an empty `promoted` list or a per-key partition -- an envelope-contract decision affecting every existing `deploy promote` consumer, out of this review pass's scope.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-9-2` there) during the pre-shutdown deferred-work audit.

### DW-5-9-3: `promote_sprint_status.py::repair_feed` matches the tracked ledger's raw key spelling against the Tier-3 feed's raw key spelling by exact string equality, so a spelling divergence inserts a duplicate row instead of reconciling
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger.md`
  summary: `cli/deploy.py::_repair_tier3_feed` calls `promote_sprint_status.repair_feed(feed_path, incoming, twin_values)` with `twin_values` keyed by the tracked ledger's own raw key spelling for each just-advanced key. `repair_feed` folds a `twin_values` key into the merged feed map only when it is absent from `incoming` (`missing = [k for k in twin_values if k not in incoming]`), an exact string-equality test. If the Tier-3 feed's own raw key for the same story is spelled differently than the ledger's (e.g. divergent hyphenation/casing introduced by a change to bmad-loop's own key-writing convention after the twin was originally promoted), the check finds no match, so the ledger's spelling is inserted as a NEW row while the feed's own differently-spelled, non-terminal row is left untouched -- two rows for one story instead of a true reconciliation.
  evidence: Surfaced by the Edge Case Hunter adversarial review pass over this story's diff (independent, no shared context with the Blind Hunter reviewer). Confirmed via direct code reading of `repair_feed`'s `missing`/merge logic (`scripts/promote_sprint_status.py`) -- the matching logic is REUSED VERBATIM from `main()`'s own pre-existing `--repair-feed` inline block (only extracted into a function by this story, never behaviorally changed), so this is a pre-existing limitation of that logic, not something Story 5.9 introduced. Not fixed here: in this story's own call path the ledger's raw keys are historically sourced FROM the feed's own spelling via a prior `promote_sprint_status.py` promotion, so the two are expected to already agree in the common case; reproducing a genuine divergence requires an out-of-band change to a DIFFERENT subsystem (bmad-loop's own key-writing convention), out of this story's own bounded scope.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-9-3` there) during the pre-shutdown deferred-work audit.

### DW-5-9-4: A failed ledger `commit_paths` after a successful `git add` leaves the git INDEX staged with pre-rollback content, even though `run_reconcile_completions`'s new rollback correctly reverts the working tree
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger.md`
  summary: `VcsPort.commit_paths` (`adapters/vcs_git.py`) stages each path with a separate `git add -- <path>` call and only THEN runs `git commit`; if the `git add` succeeds but the subsequent `git commit` fails (a plausible hook/signing rejection, not just a git-invocation crash), the path is left staged in git's index. `run_reconcile_completions`'s review-fix rollback (`fs.write_text_atomic(ledger_path, ledger_text)` on a `commit_paths` failure) restores the WORKING TREE to its pre-advance content so a later run can retry cleanly, but does not unstage the already-added index entry -- `git status`/`git diff --cached` would show the ledger as staged with the (reverted) advanced content until a later successful `commit_paths` call to the same path overwrites the stale index entry via its own `git add`, or a human runs `git reset`.
  evidence: Surfaced by the Blind Hunter adversarial review pass over this story's diff. Confirmed via direct code reading of `adapters/vcs_git.py::commit_paths` (per-path `git add --` loop, then a single `git commit -- <paths>`) and of `run_reconcile_completions`'s own rollback, which only calls `fs.write_text_atomic`, never a VCS-level unstage. Self-healing on the very next successful `commit_paths` call to the same ledger path (which re-stages the then-current, correct content), so this is a narrow, transient git-hygiene gap rather than a data-loss or false-report risk. Not fixed here: closing it cleanly needs a new `VcsPort` method (e.g. an explicit unstage/reset-path primitive) that does not exist on the port today -- extending the port's interface (plus every adapter and fake implementing it) is a larger, cross-cutting change outside this story's own bounded patch-pass scope.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-9-4` there) during the pre-shutdown deferred-work audit.

### DW-5-9-5: A literal duplicate raw key appearing twice as separate lines in the tracked ledger's own text has only its FIRST occurrence rewritten by `render_ledger_advancements`, leaving a stale duplicate line behind
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger.md`
  summary: `core/status.py::render_ledger_advancements` tracks which raw keys still need rewriting in a `remaining: set[str]`, discarding a key the moment its FIRST matching line is rewritten (`remaining.discard(key_part)`). If the ledger text contains the SAME raw key spelled identically on two separate lines (a malformed/hand-duplicated "do not hand-edit" file), only the first occurrence is rewritten to `done`; the second stays at its old status, silently. `matched_raw_keys` still reports the key as matched (once), so the caller's `data["advanced"]` reports success even though one of the two lines is stale.
  evidence: Surfaced independently by both the Blind Hunter and Edge Case Hunter review passes over this story's diff (same underlying finding, reported from two different angles). Confirmed via direct code reading of the `for i in range(0, len(parts), 2)` loop and its `remaining`/`matched` set bookkeeping -- there is no detection of a SECOND line matching an already-discarded key. Distinct from the already-recorded `DW-FU-5-9` (which is about two DIFFERENT raw keys colliding on the same normalized `StoryKey` inside `raw_key_by_dot`): this is the narrower case of the exact SAME raw key spelling appearing twice in the file's own text. Not fixed here: `render()` (`scripts/promote_sprint_status.py`) can never itself produce a duplicate key (it renders from a Python `dict`, which cannot hold two entries for the same key), so reproducing this requires a hand-edited "do not hand-edit, GENERATED" file; because the parsed READ side (`generate.py::parse_sprint_status`) already collapses a duplicate key to one value before this function ever runs, the practical consequence is a cosmetic stale duplicate LINE in the tracked file rather than a wrong STATUS being read back by any consumer -- out of this patch pass's bounded scope.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-5-9-5` there) during the pre-shutdown deferred-work audit.

### DW-8-1-1: the region-name forward-reference entry S-7.4's own ledger opened for S-8.1 is now closed in fact but still reads `status: open`
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-8-1-marker-grammar-and-the-per-format-registry.md`
  summary: Story 8.1 landed `REGION_NAME_PATTERN` (`[a-z0-9][a-z0-9-]*`) and wired it into `Region.__post_init__`, which is exactly the fix the anonymous `spec-7-4-manifest-schema-loader-and-model-version-ranges.md` entry ("A region `name` is validated only as a non-blank string...") forward-referenced to "S-8.1 (`seed/regions/markers.py`, Deps S-7.4)" -- but that entry's own `status: open` field was never updated when this story closed it, so the ledger still shows it unresolved.
  evidence: Surfaced by this repair pass's own adversarial review (Blind Hunter + Edge Case Hunter, independent) while verifying this story's Problem statement claim of "two open entries in deferred-work.md" naming S-8.1. Confirmed by direct reading: the region-name entry (`grep -n "A region \`name\` is validated only as a non-blank string" deferred-work.md`) is the one this story closes; a SECOND entry mentioning S-8.1 (`<top>` is the sole anchor...`, "the resolution is to define `<top>` in AD-56/S-8.1's grammar") is a distinct, still-genuinely-open item this story's own Never-section explicitly disclaims ("do not resolve it here even though one ledger entry loosely mentions 'S-8.1's grammar'") -- so only one of the two closes here, and even that one was never marked. Not fixed in this same edit: this repair pass's own scope is the `spec_surface_reconcile.py` gate (governed-file drift against a tracked spec's memlog), which does not read Tier-3 `deferred-work.md` at all -- editing an unrelated ledger entry's `status:` field is a distinct, mechanical follow-up for whoever next touches this ledger (or a dedicated reconciliation pass), not this gate's fix.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-1` there) during the pre-shutdown deferred-work audit.

### DW-9-1-1: `spec_surface_check.py --write-baseline --spec` stamps every file the named spec governs, not just the paths a reconciliation entry actually names, with no lock against concurrent writers
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-9-1-findings-model-severity-types-remedies.md`
  summary: This story's own deterministic-verification repair pass (reconciling `spec-pyforge-marshal`'s memlog for the two files story 9.1 added) exposed two pre-existing gaps in `scripts/spec_surface_check.py`'s `--write-baseline --spec NAME` mutation path: (1) it merges `current[name]` -- EVERY file the named spec's surface glob currently matches (~165 for this one spec's broad `src/shared/packages/pyforge-marshal/**` glob) -- into the baseline, not just the paths the accompanying memlog entry actually names, so an unrelated, un-narrated drifted file under the same broad surface would be silently absorbed as "reconciled" with no trace, not even a non-gating `drift-presumed` WARN; (2) the read-modify-write of `scripts/.spec-surface-baseline.json` carries no advisory lock, so two loop homes stamping different specs' baselines concurrently could each merge from a stale read and drop the other's just-written entry.
  evidence: Surfaced independently by both the Blind Hunter and Edge Case Hunter review passes over this repair diff (Edge Case Hunter's finding CONFIRMED after direct code reading of `spec_surface_check.py`'s `merged[name] = current[name]` line and live verification against this run's own stamp -- no unrelated file actually drifted at stamp time here, so no masking occurred in this instance, but the mechanism itself has no guard). Not fixed here: both gaps are in `scripts/spec_surface_check.py` and `pyforge.doctor.sources.chain`, entirely outside `pyforge.marshal.seed.detect.findings` (this story's own Surface) and outside the intent-contract this repair pass is bound not to touch; narrowing the stamp to named paths and/or adding a file lock (the architecture doc's own advisory-lock pattern for shared Tier-3 appends, per this project's memlog) is a `spec-surface-drift-reconciliation`-scoped fix for a future story.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-1` there) during the pre-shutdown deferred-work audit.

### DW-9-3-1: `check_managed_file`/`check_managed_region` never distinguish a shape-invalid `recorded_sha` from a genuine hand-edit
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-9-3-content-hashing-for-managed-files-and-regions.md`
  summary: Both check functions compare `recorded_sha` against the computed hash by plain string equality with no shape validation (the package's own established 8-lowercase-hex convention, `_SHA_PATTERN` in `regions/markers.py`) -- a corrupted or hand-edited state value (wrong case, whitespace, wrong length) is reported identically to a real content hand-edit (`managed-file-modified`/`managed-region-modified`, HARD), even though `FindingType.STATE_INVALID` exists in the same vocabulary specifically for a malformed state file (FR-104) and would be the more accurate, more actionable signal.
  evidence: Raised independently by this story's Blind Hunter review pass. Verified against the current codebase: `state/store.py` does not exist yet (only `seed/state/__init__.py`, empty) -- FR-104's "validated against a JSON schema on every read" is explicitly that future story's responsibility, and every real sha producer in this package today (`hash_content`, `region_sha`) only ever emits the valid shape, so a malformed `recorded_sha` can only originate from state corruption this pure comparison module has no way to distinguish from a real hand-edit without itself reading/validating state -- exactly the boundary this story's own spec draws (`recorded_sha` is always a caller-supplied parameter, never read from disk here). Not fixed here: doing so would require either importing shape-validation logic ahead of the state-store story that owns it, or duplicating `_SHA_PATTERN`'s convention into `detect/hashes.py` speculatively. Whichever story builds `state/store.py` (FR-102/FR-104) should decide whether schema validation happens before `recorded_sha` ever reaches `check_managed_file`/`check_managed_region` (making this moot) or whether these two functions should additionally special-case a shape-invalid input into `STATE_INVALID`.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3` there) during the pre-shutdown deferred-work audit.

### DW-9-4-1: Epic 9.4's AC prose names a glob (`docs/specs/*.md`) for the canonical legacy worked example that this module's presence check cannot honor
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-9-4-legacy-convention-detection.md`
  summary: `epics.md`'s Story 9.4 AC says "the canonical case is covered by test: `docs/specs/*.md` present ⇒ preserved, recorded" -- but `_classify_entry`'s presence check is a literal `Path.exists()` against `entry.path`, which never glob-expands, so an artifact entry whose `path` was literally set to a glob like `docs/specs/*.md` would report `absent` on every real repo (no file is named `*.md`). Both the shipped `templates/manifest.yaml` (`specs-dir-legacy`, `path: "docs/specs/"`) and this story's own spec/test correctly use the bare directory instead, sidestepping the AC's wording, but the AC prose itself was never reconciled to match.
  evidence: Surfaced by this story's second (fresh, post-`done`) review pass, Blind Hunter. Verified directly by reading `epics.md` line 2153 (the literal glob text) against `seed/templates/manifest.yaml`'s real `specs-dir-legacy` entry (bare directory path, no `legacy_of` set) and this story's own intent-contract (also bare directory) -- the implementation is correct and consistent with the module's pre-existing, non-globbing presence-check semantics (unchanged since S-9.2); only the epics AC's illustrative wording is imprecise. Not fixed here: this story's Surface is `inventory.py`/`findings.py`, not `epics.md`, and the AC's glob phrasing was already pre-existing before this story's dev work began -- a future editorial pass over Epic 9's AC prose (or whichever story next reads it closely) should reword this bullet to name the bare directory, so a future manifest author does not take the glob literally and hit a silent `absent` misclassification.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4` there) during the pre-shutdown deferred-work audit.

### DW-9-5-1: Manifest coverage check can never actually fire against any manifest built through normal construction
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-9-5-manifest-coverage-check.md`
  summary: `coverage_findings()`/`coverage_counts()` (S-9.5, FR-69/SC-10) re-verify `entry.artifact_class`/`entry.rationale` as a second, independent gate against `ManifestEntry.__post_init__` (S-7.4/7.5) already enforcing both unconditionally -- so no manifest built through `load_manifest` or ordinary `ManifestEntry(...)` construction can ever produce an `uncovered` finding; the failing branches are reachable only via `object.__setattr__` bypassing the frozen dataclass, a technique that appears nowhere in production code. The corresponding CI-gate test (`test_packaged_manifest_passes_coverage_findings_with_zero_findings`) can consequently only fail if `load_manifest` itself already failed to enforce its own invariants, in which case the fixture would have raised before the test body runs -- adding little regression protection beyond the pre-existing `test_packaged_manifest_class_counts_match_the_spec_exactly`. Separately, the implementation only validates that a *declared* manifest entry is internally well-formed; it never reconciles against `Inventory`/the target repo, so it cannot detect the arguably more valuable reading of SC-10's "100% manifest coverage" -- a real repo artifact with no manifest entry at all, or an entry whose declared class doesn't match what's actually on disk.
  evidence: Surfaced by this story's review pass (Blind Hunter). Verified directly: `ManifestEntry.__post_init__` (`model/manifest.py`) unconditionally coerces `artifact_class` through `ArtifactClass(...)` (raising on any invalid value) and requires a non-blank `rationale` via `_require_text` on every entry regardless of class -- both conditions `_uncovered_reason` checks are already fully closed before a `ManifestEntry` can exist. This is faithful to epics.md Story 9.5's literal AC (an explicit, planning-approved requirement predating this dev pass, mirroring AD-54's "coverage check that HARD-fails any unclassified artifact" design and `bmad_drift_check.py`'s own redundant-gate philosophy) -- not a defect introduced by this diff, so not fixed here. Worth a future architecture-level look (perhaps alongside S-9.6's plan builder or a later report-renderer story) at whether the coverage check should also reconcile against `Inventory`'s classification output to catch the file-system-divergence case, which is the reading with real teeth.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-5` there) during the pre-shutdown deferred-work audit.

### DW-9-5-2: A second, independent review pass re-confirms manifest coverage is structurally redundant with `ManifestEntry.__post_init__`
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-9-5-manifest-coverage-check.md`
  summary: This story's fresh, post-`done` review pass (run after the story's implementation was recovered from a preserved branch following an unrelated worktree reset) independently re-derived the same structural observation already filed as `DW-FU-9-5`: `coverage_findings()`/`coverage_counts()` re-verify `entry.artifact_class`/`entry.rationale`, but `ManifestEntry.__post_init__` (S-7.4/7.5, `model/manifest.py`) already coerces `artifact_class` through `ArtifactClass(...)` and requires a non-blank `rationale` unconditionally on every entry -- and the sole production construction path (`_build_entry`, `model/manifest.py`) coerces the class a second time before `ManifestEntry` even exists. So a bug that broke `__post_init__`'s coercion would also have to survive `_build_entry`'s own separate, earlier coercion of the identical value to be exploitable through this gate at all -- the "second, decoupled gate" the module docstring claims is less independent than the prose suggests, since both layers share the same `ArtifactClass(...)` call.
  evidence: Raised independently by this pass's Blind Hunter review (no shared context with the review pass that filed `DW-FU-9-5`), reading the exact same `_build_entry`/`ManifestEntry.__post_init__` code as before, corroborating rather than superseding it. Recorded per this workflow's own instruction not to consolidate or dedupe defer findings against existing ledger entries. Not fixed here -- unchanged from `DW-FU-9-5`'s own disposition: faithful to epics.md Story 9.5's literal, planning-approved AC; a future architecture-level look (see `DW-FU-9-5`) is the right venue, not this diff.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-5-2` there) during the pre-shutdown deferred-work audit.

### DW-9-5-3: Manifest coverage only sees version-filtered entries, so a staged or retired entry's corrupted class/rationale produces no signal
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-9-5-manifest-coverage-check.md`
  summary: `coverage_findings()`/`coverage_counts()` operate on `Manifest.entries`, which -- when the `Manifest` came from `load_manifest` (`model/manifest.py`) -- has already been filtered to only entries `in_range(model_version, entry.since, entry.until)` at the manifest's own declared `model_version`. An entry staged for a future version (`since` not yet reached) or already retired (`until` passed) is invisible to the coverage check entirely, so a corrupted `artifact_class`/`rationale` on such an entry produces no `uncovered` finding at the model version where the check actually runs. This is consistent with `load_manifest`'s documented version-filtering design (the manifest is an append-only historical ledger; AD-55) and with the intent contract's own explicit boundary ("coverage is intrinsic to the manifest alone"), but it sits in tension with FR-69's "every artifact [Genesis] knows about" framing, which reads as broader than "every artifact active at the manifest's own declared version."
  evidence: Raised by this pass's Blind Hunter review. Verified directly: `load_manifest`'s `filtered_entries = tuple(entry for entry in entries if in_range(model_version, entry.since, entry.until))` (`model/manifest.py`) runs before `Manifest(...)` is constructed, so `Manifest.entries` -- the only input `coverage_findings`/`coverage_counts` ever see -- never contains an out-of-range entry when built via the loader. Not this story's defect: the version-filtering behavior is S-7.4's pre-existing design, and S-9.5's intent contract explicitly scopes coverage to the manifest alone (no `Inventory`/repo-target involvement), which by construction means "the manifest at its declared version," not "every entry the YAML source ever mentions." Worth a future look (perhaps alongside a report-renderer story) at whether a coverage-style check should also run against the UNFILTERED entry list to catch corruption in staged/retired entries before they become active.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-5-3` there) during the pre-shutdown deferred-work audit.

### DW-9-6-1: `build_plan`'s git fingerprint can misreport an ancestor repository's HEAD/dirty state for a nested target
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-9-6-plan-and-action-types-repo-fingerprint-and-the-plan-builder.md`
  summary: `_git_head`/`_repo_is_dirty` run `git rev-parse HEAD`/`git status --porcelain` with `cwd=inventory.repo_root` and no `--show-toplevel`-style boundary check; if `repo_root` is a subdirectory of an ENCLOSING git checkout rather than a repo root of its own, both calls succeed and report the ANCESTOR repository's HEAD/dirty state instead of degrading to `git_head=None` the way a genuinely non-git target does -- silently mislabeling `RepoFingerprint` for a target that is not actually version-controlled on its own terms.
  evidence: Raised by this story's review pass (Blind Hunter). Verified by reading `build.py::_git_head`/`_repo_is_dirty`: both simply pass `cwd=repo_root` to `git`, and `git` itself walks upward to the nearest enclosing `.git` when the given directory is not itself a repo root -- there is no code here (or anywhere else in `seed/`) that calls `git rev-parse --show-toplevel` or otherwise confirms `repo_root` IS the repository root before trusting its answer. `errors.py`'s own `PreconditionFailure` docstring already earmarks "a target that is not a git repo" as a check a later `seed/verbs/` story performs before running any verb -- the nested-repo variant of that same boundary question belongs there (where a `PreconditionFailure` can actually be raised and surfaced to the operator), not in this story's `plan/build.py` (a later `apply` story, Epic 10, is the one that would actually trust `repo_fingerprint` for a refuse decision, per this story's own Never list). Not fixed here: this story's Boundaries/Never list explicitly excludes both CLI-level precondition checking and any fingerprint-based refusal logic. A future `seed/verbs/` (or the `apply` story itself) should add a `--show-toplevel` (or equivalent) boundary check before computing or trusting a `RepoFingerprint`.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-6` there) during the pre-shutdown deferred-work audit.

### DW-9-6-2: Writing `plan.json` before the target's `.gitignore` region is materialized can make the plan file itself flip a subsequent fingerprint's `dirty` flag
- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-9-6-plan-and-action-types-repo-fingerprint-and-the-plan-builder.md`
  summary: `write_plan` composes freely with `build_plan` -- nothing in this story sequences them -- so a future verb calling `write_plan(plan, default_plan_path(repo_root))` against a target repo whose `.gitignore` has not yet had the model's `model-ignores` region materialized into it (e.g. the very first `init`/`adopt` run, before Genesis has written anything) leaves the freshly-written `.marshal/plan.json` as an untracked file. A subsequent `build_plan` call against that same repo (e.g. to verify idempotence, AD-60) would then see that untracked file via `git status --porcelain` and report `dirty=True`, even though nothing about the repo's OWN content actually changed. (Whether `.marshal/plan.json` is covered by the packaged `.gitignore` region at all was also raised and is independently verified TRUE: `templates/files/model-ignores.gitignore.j2` lists it explicitly -- the surviving concern is purely the ORDERING between materializing that region and writing the plan file, not whether the ignore rule itself exists.)
  evidence: Raised by this story's review pass (Blind Hunter). Verified by reading `build.py`: `build_plan` and `write_plan` are two entirely independent, composable functions with no call-order relationship to each other or to whatever future code materializes a target repo's `.gitignore` -- this story never writes to a target repo at all (Never list: "No apply integration"). The self-referential fragility is real but only reachable once a LATER story (Epic 10's `apply`, or whichever `seed/verbs/` story first sequences `init`/`adopt`) starts calling `write_plan` against a real target repo; nothing in Story 9.6's own test suite triggers it, since none of `build_plan`'s tests call `write_plan` against a repo that also has a real `.gitignore` file. Not fixed here: the correct fix is a write-order guarantee ("materialize `.gitignore`'s `model-ignores` region before writing `plan.json`, or write `plan.json` outside the target repo's own tree entirely") that belongs to whichever future story actually sequences those writes -- outside this story's Surface (`plan/types.py`, `plan/build.py`) and explicitly outside its Never list's "no apply integration" boundary.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-6-2` there) during the pre-shutdown deferred-work audit.


### DW-4-14-1: Follow-up review still recommended for 4-14-the-failed-story-safety-net-is-reported after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-4-14-the-failed-story-safety-net-is-reported.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260809-231524-abb9; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-8` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

### DW-FU-8-5: Follow-up review still recommended for 8-5-marker-deletion-as-a-sanctioned-opt-out after the damping cap was spent

- source_spec: `spec-8-5-marker-deletion-as-a-sanctioned-opt-out.md`
  summary: Follow-up review still recommended for 8-5-marker-deletion-as-a-sanctioned-opt-out after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260820-140537-4cd4; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-20 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-10` there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide with a generic `DW-10`.
  severity: low
  status: open

### DW-BL011-1: loop-stall-check labels a bmad-loop 0.11 `awaiting-operator` parked run "stalled" — attention arrives, mislabeled
  origin: bmad-loop-0.11-compat-audit (2026-08-21, the BMAD 6.11.0 upgrade session)
  source_spec: `spec-bmad-loop-governance` (the detector's contract)
  severity: low
  reason: bmad-loop 0.11.0 adds an `awaiting-operator` phase (operator-parked stories, completed via `bmad-loop confirm`; park records in-commit at `.bmad-loop/operator/<key>.json`). `scripts/loop_stall_check.py`'s liveness test exempts only `finished`/`stopped`/`paused_reason`, so a parked run sitting deliberately still reads as a 15-minute stall. Benign in effect — a parked run WANTS operator attention — but the "stalled" label misdirects triage toward a wedged-session diagnosis. Fix shape: recognize the parked state in `_is_live` and report it as `awaiting-operator (run bmad-loop confirm)` instead of a stall. No live runs existed at audit time; first reproduction requires a 0.11 run that parks.
  resolved: 2026-08-22 — marshal Story 25.5 (spec-bmad-611-era-alignment CAP-5). `scripts/loop_stall_check.py` now classifies a live run's tasks off the same state.json read: a parked-only run (≥1 `awaiting-operator` task, nothing non-terminal) is reported distinctly as `awaiting-operator (run bmad-loop confirm)` with its parked story keys and exits 0; a quiet run carrying parked AND still-active tasks stays a stall with the parked keys named. The same run state is now first-class across marshal (`derive_home_state`'s sixth fleet state, terminal-set fix, `preserve_ref`/`sweeps_refused` surfacing) and `scripts/fleet_picture.py` (state column + tracked-ledger ATTENTION line); pinned against the installed package by `tests/unit/test_bmad_loop_status_vocabulary.py` and the two CFE meta tests (`test_loop_stall_check_awaiting_operator.py`, `test_fleet_picture_awaiting_operator.py`).
  status: resolved

### DW-BL011-2: the deferred-work pipeline's intake shape changes on the FIRST bmad-loop 0.11 run — Tier-3 `deferred-work.md` is no longer written; deferred findings live in spec frontmatter `deferred:` lists
  origin: bmad-loop-0.11-compat-audit (2026-08-21, the BMAD 6.11.0 upgrade session)
  source_spec: `spec-regenerable-factory` (deferred-work-check's contract)
  severity: medium
  reason: BMAD 6.11's build-auto contract (which bmad-loop 0.9.1+ dispatches via on-disk resolution, and 0.10.0 adopts as "the deferred-work contract of the 6.11 era") drops `implementation-artifacts/deferred-work.md` and `final_revision`; deferred findings are spec-frontmatter `deferred:` lists (items: summary, evidence, optional location, severity), and 0.11's own validate now FAILS (was warn) on an unreadable ledger.
  correction (2026-08-22): upstream research narrows the scope — bmad-loop's `Engine._harvest_spec_deferrals` (since the 0.9.1 hotfix, confirmed via closed issue #567) already harvests spec-frontmatter `deferred:` entries into the ledger its sweep reads, so LOOP-DRIVEN runs are bridged upstream. The remaining gap is HAND-DRIVEN build-auto runs (proven live by the 2026-08-22 canary, whose deferral needed a manual relay to doctor's tracked ledger as DW-14-1-1) plus our scripts' tracked-twin intake. Decomposed as marshal Story 25.6 (spec-bmad-611-era-alignment CAP-6); this entry closes when 25.6 lands. Consumers built on the old shape: `scripts/deferred_work_baseline.py`, `deferred_work_promote.py`, `normalize_deferred_ledgers.py`, `apply_verification_verdicts.py`, `scripts/deferred_work_check.py` (whose premise is "bmad-loop's damping refiles into gitignored deferred-work.md"), scribe's promote path, and the tracked-ledger promotion flow. Nothing is broken today (no live runs; existing ledgers remain readable); the first 0.11-era run produces findings these tools will not see. Fix shape: teach the promotion/check pipeline to ALSO read spec-frontmatter `deferred:` lists, keeping the legacy file as a still-honored source.
  resolved: 2026-08-23 — marshal Story 25.6 (CAP-6). Doctor `chain.py` discovers spec-frontmatter `deferred:` via `spec-frontmatter-only-deferral` findings; `scripts/deferred_work_intake.py --fix` promotes into tracked ledgers; `scripts/deferred_work_check.py` restored as a thin shim over `python -m pyforge.doctor.sources deferred-work`. Loop-run bridge unchanged (bmad-loop `_harvest_spec_deferrals`). Fixture-proven (DW-14-1-1 canary shape).
  status: resolved

### DW-25-4-1: `repo_defaults` compose parameter is accepted but never folded — `policy-defaults.toml` is functionally inert for all 28 keys
  origin: story-25-4 review (deferred, MATERIAL — carried in the story spec's 6.11-era frontmatter `deferred:` list; relayed here because the DW pipeline cannot yet read frontmatter, DW-BL011-2/Story 25.6)
  source_spec: `spec-bmad-611-era-alignment` (CAP-4's story)
  severity: medium
  reason: The AD-16 chain is documented as defaults -> policy-defaults.toml (repo layer) -> marshal-policy.toml (project) -> flags, and team memory teaches "repo-wide in policy-defaults.toml" — but the compose path accepts the repo_defaults parameter and never folds it, so the repo layer is a no-op for every one of the 28 keys. Harmless TODAY only because policy-defaults.toml carries zero divergences from DEFAULT_POLICY (verified during 25.4); the first operator who edits it gets silently ignored. Fix shape: fold repo_defaults between DEFAULT_POLICY and the project layer with precedence tests; alternatively retire the file + correct the docs/memory — either way, deliberately.
  status: open

### DW-25-5-1: Story 25.5's review round landed AFTER the merge — two layers' findings dispositioned here, unapplied
  origin: review-layer orphaning (the 25.5 orchestrator died at a spend limit after committing but before triage; Blind Hunter + Edge Case Hunter delivered to the parent session post-merge, 2026-08-22)
  source_spec: `spec-bmad-611-era-alignment` (CAP-5's story; followup_review_recommended stands)
  severity: medium
  reason: PR #612 merged verified-green (marshal 5223 passed) but without its review round applied. Finalize omissions were completed post-merge same day (ledger flip, owed memlog events for spec-bmad-611 + spec-bmad-loop-governance, story-spec promotion, pixi.toml stall-check description, meta-test baseline classification). The MATERIAL unapplied findings, distilled: (1) ports/harness.py RunStatusSnapshot is a frozen dataclass now carrying a MUTABLE DICT field (sweeps_refused) — hash()/set-membership raises TypeError; tuple-of-pairs or eq=False is the fix; (2) loop_stall_check.parked_tasks assumes state.json "tasks" is a dict — a list/string crashes the whole watchdog before other homes are checked; (3) a run that flips finished/stopped while still carrying awaiting-operator tasks drops its owed confirms from the watchdog (parked-outranks-finished precedence not honored at the liveness gate); (4) fleet_picture's ATTENTION chain emits BOTH "idle — needs a spin" AND the parked-confirm line for a parked station with backlog (the state column pins confirm-not-respin; ATTENTION lacks the exclusion); (5) derive_home_state precedence cell parked+escalated+dead-supervisor flips unsupervised→paused-on-escalation, hiding the dead supervisor; (6) preserve_ref values + sweeps_refused keys print verbatim (no redaction/shape-check) into terminal + dashboard JSON; (7) the installed-package drift pins degrade to silent SKIPS via importorskip when bmad_loop is absent — nothing asserts the env carries it; (8) `sweeps_refused: None` renders as a raw Python literal conflating absent-key with unreadable-state; (9) the parked state cell drops the "N left" backlog count; (10) ledger-count plumbing (counts[awaiting-operator] + the ATTENTION needs line) is untested and the feed-token spelling is unpinned; (11) doctor's marshal.py false-green source: a feed-done story whose harness phase is awaiting-operator confirms "landed" via park commit_sha though acceptance was never confirmed; (12) minor: dead preserve_ref fixture param, F541 f-string, summary-line accounting, mid-phrase wraps. Fix shape: one remediation story (or the Epic 25 retro) applies 1-6 with tests, decides 7's env-assertion posture, and polishes 8-12; nothing here invalidates the landed behavior, which is fixture-verified for the primary paths.
  status: open

### DW-FU-11-4: `_wholesale_regenerate_actions` never cross-checks `state.opted_out`/`state.skips` before regenerating, so it could silently override a previously opted-out hybrid region or a previously skipped whole-file artifact.

- source_spec: `planning-artifacts/specs/spec-11-4-marshal-seed-update-two-phase.md`
  summary: `_wholesale_regenerate_actions` never cross-checks `state.opted_out`/`state.skips` before regenerating, so it could silently override a previously opted-out hybrid region or a previously skipped whole-file artifact.
  evidence: Blind Hunter review finding. `build_plan` itself already respects `opted_out` for its own actions (`_pendency`/`_is_fully_opted_out`); the new wholesale-regenerate pass has no equivalent check. Not demonstrated as an active bug, and how `update` should treat a prior opt-out/skip on a subsequent update is a genuine, undecided product question the epics AC does not address — deserves dedicated design attention rather than an improvised same-pass fix.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py:_wholesale_regenerate_actions
  origin: spec-deferred 134693f178f9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-11-4-2: The `--include-seeded` "offered now, applicable later" story is untested across separate `update` invocations.

- source_spec: `planning-artifacts/specs/spec-11-4-marshal-seed-update-two-phase.md`
  summary: The `--include-seeded` "offered now, applicable later" story is untested across separate `update` invocations.
  evidence: Blind Hunter review finding. Once a migration's `to_version` lands in `state.migrations_applied[]`, a later `chain()` call may not re-walk that migration, so whether the `copied-seeded` offer still resurfaces on a later `--include-seeded` run is unverified. No test in this diff exercises two sequential `run_update` calls against the same evolving state.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py:run_update
  origin: spec-deferred fce9464dd645 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-11-4-3: `--force` combined with a hand-edited hybrid-managed-region (as opposed to a hand-edited whole-file artifact) is untested.

- source_spec: `planning-artifacts/specs/spec-11-4-marshal-seed-update-two-phase.md`
  summary: `--force` combined with a hand-edited hybrid-managed-region (as opposed to a hand-edited whole-file artifact) is untested.
  evidence: Blind Hunter review finding. `test_force_bypasses_the_hand_edited_managed_content_precondition` only covers the whole-file case; whether `--force` correctly bypasses rung 6 and correctly substitutes over a hand-edited region span is unverified.
  location: src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_update.py
  origin: spec-deferred c4780a609ee1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-11-4-4: The `projects-table` repo-computed region-body dispatch (Story 11.2) is never exercised through `update`'s own commit path — only through `adopt`'s.

- source_spec: `planning-artifacts/specs/spec-11-4-marshal-seed-update-two-phase.md`
  summary: The `projects-table` repo-computed region-body dispatch (Story 11.2) is never exercised through `update`'s own commit path — only through `adopt`'s.
  evidence: Verification Gap Reviewer observation. Every hybrid-region test in the new test files uses the static "tiers" fragment; `_region_body_for`'s `projects-index`/`projects-table` branch has no direct test via `update`.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py:_region_body_for
  origin: spec-deferred 0677368b6afa — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-12-1: llms-full-check reports 82 pre-existing catalog drift findings on main (floor-drift + undocumented deps unrelated to copier); exit 1 before and after this story.

- source_spec: `planning-artifacts/specs/spec-12-1-full-pixi-wiring-distribution-and-repo-gate-compliance.md`
  summary: llms-full-check reports 82 pre-existing catalog drift findings on main (floor-drift + undocumented deps unrelated to copier); exit 1 before and after this story.
  evidence: pixi run -e local-recipes llms-full-check exits 1 on origin/main and on this branch with identical 82 findings; copier is documented and absent from the drift report.
  origin: spec-deferred 2d1d053f9b12 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-12-2: K-02: local-recipes is not genesis-aligned — adopt dry-run yields 21 filtered actions (managed regions absent, no seed-state, first-claim pending). Slow oracle fails until bootstrap adopt lands.

- source_spec: `planning-artifacts/specs/spec-12-2-the-local-recipes-empty-plan-oracle.md`
  summary: K-02: local-recipes is not genesis-aligned — adopt dry-run yields 21 filtered actions (managed regions absent, no seed-state, first-claim pending). Slow oracle fails until bootstrap adopt lands.
  evidence: pixi run --frozen -e pyforge-marshal pyforge-marshal-test-slow -k test_local_recipes → AssertionError, 21 actions (claude-skills excluded).
  origin: spec-deferred 96f6f96ebc9f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-18-2: Coverage detection is filesystem path presence only; an empty stub mcp/tools.py or server.py counts as covered without proving registered tools.

- source_spec: `planning-artifacts/specs/spec-18-2-parity-and-coverage-are-gated-numbers.md`
  summary: Coverage detection is filesystem path presence only; an empty stub mcp/tools.py or server.py counts as covered without proving registered tools.
  evidence: Blind Hunter / Design Notes intentionally measure presence for FR-156. Stronger "callable FastMCP tools" checks are a future hardening pass.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/coverage.py
  origin: spec-deferred 73edfe40ad08 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-18-2-2: discover_cli_verbs walks private argparse _actions / _build_parser internals.

- source_spec: `planning-artifacts/specs/spec-18-2-parity-and-coverage-are-gated-numbers.md`
  summary: discover_cli_verbs walks private argparse _actions / _build_parser internals.
  evidence: Edge-case / Blind Hunter. Works against the live CLI today; a public inventory API would harden the gate against parser refactors.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/parity.py
  origin: spec-deferred ba68f64529fe — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-18-2-3: resolve_repo_root has no MARSHAL_REPO_ROOT override when the package is installed outside the monorepo layout.

- source_spec: `planning-artifacts/specs/spec-18-2-parity-and-coverage-are-gated-numbers.md`
  summary: resolve_repo_root has no MARSHAL_REPO_ROOT override when the package is installed outside the monorepo layout.
  evidence: Blind Hunter. python -m coverage is repo-operator oriented; installed wheel use outside the tree is out of v1 scope.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/coverage.py
  origin: spec-deferred 6672ec85a061 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-19-2: Seeded mock edge-case hardening (recreate-after-delete, negative clock advance, journal reload from disk) remains identical to archive seeds.

- source_spec: `planning-artifacts/specs/spec-19-2-the-shared-test-support-kit.md`
  summary: Seeded mock edge-case hardening (recreate-after-delete, negative clock advance, journal reload from disk) remains identical to archive seeds.
  evidence: Edge-case hunter listed lifecycle/input guards that the archived Marshal mocks also lack; Story 19.2 seeds without rewriting those behaviors.
  location: src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/
  origin: spec-deferred dbdb7dc7a6b7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-19-2-2: docs/reference/library-llms-full.md still reports broad pin/undocumented-dep drift beyond the new pyforge-testing-kit env row.

- source_spec: `planning-artifacts/specs/spec-19-2-the-shared-test-support-kit.md`
  summary: docs/reference/library-llms-full.md still reports broad pin/undocumented-dep drift beyond the new pyforge-testing-kit env row.
  evidence: llms-full-check reports dozens of pre-existing undocumented deps and pin mismatches; this story only added the testing-kit env row.
  location: docs/reference/library-llms-full.md
  origin: spec-deferred 87f14aecc755 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-19-3: Expand coverage-gates CI beyond the marshal home env (matrix / per-station pixi env) so non-marshal package touches are gated in the same workflow.

- source_spec: `planning-artifacts/specs/spec-19-3-coverage-gates-that-name-the-module.md`
  summary: Expand coverage-gates CI beyond the marshal home env (matrix / per-station pixi env) so non-marshal package touches are gated in the same workflow.
  evidence: Workflow installs only pyforge-marshal and sets COVERAGE_GATES_STATIONS=marshal; other stations rely on pixi *-test-coverage tasks / future matrix work.
  location: .github/workflows/coverage-gates.yml
  origin: spec-deferred 64e543f27d3d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-19-3-2: Add parallel pixi `pyforge-*-test-coverage` tasks for non-marshal stations.

- source_spec: `planning-artifacts/specs/spec-19-3-coverage-gates-that-name-the-module.md`
  summary: Add parallel pixi `pyforge-*-test-coverage` tasks for non-marshal stations.
  evidence: Only pyforge-marshal-test-coverage was added; comments still refer to plural tasks.
  location: pixi.toml
  origin: spec-deferred 60790d83b8fd — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-19-3-3: Upload coverage JSON / term-missing artifacts on gate failure for operators.

- source_spec: `planning-artifacts/specs/spec-19-3-coverage-gates-that-name-the-module.md`
  summary: Upload coverage JSON / term-missing artifacts on gate failure for operators.
  evidence: CI currently relies on step stdout only.
  location: .github/workflows/coverage-gates.yml
  origin: spec-deferred 521659a156b4 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-19-4: Wire `tea-playwright-check` into a CI / detectors job so the CAP-5 gate runs without an operator opt-in (intent allowed CI or CLI; this story shipped the CLI).

- source_spec: `planning-artifacts/specs/spec-19-4-test-architecture-stays-current-as-stories-land.md`
  summary: Wire `tea-playwright-check` into a CI / detectors job so the CAP-5 gate runs without an operator opt-in (intent allowed CI or CLI; this story shipped the CLI).
  evidence: pixi task exists; no .github/workflows reference in the 19.4 diff. Approach said "detectable (fail or report)"; original AC allowed CI or CLI.
  location: pixi.toml / .github/workflows
  origin: spec-deferred 63ed15e7314d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-19-4-2: Atlas-style epic headers `### Story A1 (2.1): …` are not parsed by `_STORY_HEADER`, so lettered stories never enter the --check expected set.

- source_spec: `planning-artifacts/specs/spec-19-4-test-architecture-stays-current-as-stories-land.md`
  summary: Atlas-style epic headers `### Story A1 (2.1): …` are not parsed by `_STORY_HEADER`, so lettered stories never enter the --check expected set.
  evidence: Pre-existing 19.1 generator limitation surfaced by verification-gap review; live atlas check reports only numeric ids.
  location: _bmad/scripts/bmad_tea_playwright.py
  origin: spec-deferred dcede833142d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-3: Parent Spec CAP-3 memlog/SPEC success oracle still describes the draft as unfiled; sync on a later docs pass if needed.

- source_spec: `planning-artifacts/specs/spec-20-3-the-gated-upstream-filing.md`
  summary: Parent Spec CAP-3 memlog/SPEC success oracle still describes the draft as unfiled; sync on a later docs pass if needed.
  evidence: Blind-hunter finding: spec-bmad-loop-baseline-drift CAP-3 text may still say gated/unfiled; outside this chore's Code Map surfaces.
  origin: spec-deferred 3099eeba57f5 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-3-2: If #701 closes only one half of the coordinated report, split or re-note the register entry so FR-189 is not silently retired.

- source_spec: `planning-artifacts/specs/spec-20-3-the-gated-upstream-filing.md`
  summary: If #701 closes only one half of the coordinated report, split or re-note the register entry so FR-189 is not silently retired.
  evidence: Edge-case hunter: single upstream_status on a dual-mode coordinated filing.
  origin: spec-deferred e50b56676a5b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-6: Until 20.7, cli/init.py and scripts/bmad-switch still ship divergent slug-parse / desync bodies alongside pyforge.marshal.scope.

- source_spec: `planning-artifacts/specs/spec-20-6-the-verify-scope-primitive.md`
  summary: Until 20.7, cli/init.py and scripts/bmad-switch still ship divergent slug-parse / desync bodies alongside pyforge.marshal.scope.
  evidence: CAP-1 ships the sole new primitive but intentionally leaves legacy guards in place; never-two-parallel-copies is satisfied for the new module, with body retirement deferred to CAP-2.
  location: cli/init.py:_slug_from_symlink_target; scripts/bmad-switch:desync_warning
  origin: spec-deferred 8b1ce54bdb4d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-20-6-2: MRS-INIT-003 today inspects only planning-artifacts; verify_scope requires both artifact symlinks — 20.7 must absorb the widening.

- source_spec: `planning-artifacts/specs/spec-20-6-the-verify-scope-primitive.md`
  summary: MRS-INIT-003 today inspects only planning-artifacts; verify_scope requires both artifact symlinks — 20.7 must absorb the widening.
  evidence: Blind-hunter / design note: semantic widening when CAP-2 replaces the guard with verify_scope.
  location: cli/init.py:MRS-INIT-003 vs pyforge.marshal.scope.verify_scope
  origin: spec-deferred 8790f3aea35c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-2: Soft code-linkage verify reports missing cites in detail but always completes; tightening to fail/block is a product choice beyond CAP-1.

- source_spec: `planning-artifacts/specs/spec-21-2-orchestrated-chain-regeneration.md`
  summary: Soft code-linkage verify reports missing cites in detail but always completes; tightening to fail/block is a product choice beyond CAP-1.
  evidence: Review found verify_code_linkage returns status=complete with missing cite counts in detail only. AC requires read-only verify then orphan report; failing the chain on linkage gaps was not specified.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/chain_regen.py
  origin: spec-deferred bc68c76465f6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-2-2: Dual CLI: marshal chain regenerate (17.4) coexists with marshal planning chain-regenerate (21.2) without deprecation cross-link.

- source_spec: `planning-artifacts/specs/spec-21-2-orchestrated-chain-regeneration.md`
  summary: Dual CLI: marshal chain regenerate (17.4) coexists with marshal planning chain-regenerate (21.2) without deprecation cross-link.
  evidence: Story 17.4 intentionally shipped the four-phase dry-run verb; 21.2 adds the Full orchestrated verb. Documentation/deprecation is out of CAP-1.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/chain.py
  origin: spec-deferred a437fc395281 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-5: CAP-5 help prose hard-codes defaults instead of deriving text from `cap5_defaults()`, inviting future doc/code drift.

- source_spec: `planning-artifacts/specs/spec-21-5-configurable-per-project-invocation.md`
  summary: CAP-5 help prose hard-codes defaults instead of deriving text from `cap5_defaults()`, inviting future doc/code drift.
  evidence: Review pass noted help strings in cli/planning.py duplicate the default matrix returned by core.chain_regen.cap5_defaults(). Cosmetic; tests assert both surfaces independently today.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/planning.py
  origin: spec-deferred 058d8669b433 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-23-1: timing.total / epicMin sum journal minutes and wall-clock ceiling minutes into one numeric rollup while metric text says they are different classes.

- source_spec: `planning-artifacts/specs/spec-23-1-wall-clock-fallback-derivation-from-promoted-spec-revision-fields.md`
  summary: timing.total / epicMin sum journal minutes and wall-clock ceiling minutes into one numeric rollup while metric text says they are different classes.
  evidence: CAP-1 places both on timing.perStory honestly named; full visual/series separation is Story 23.2 (CAP-2). Surfaced by blind-hunter; not a fabricate risk.
  location: docs/dashboard/generate.py:scan_timing
  origin: spec-deferred 2d5dc03c245d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-23-1-2: Journal story_key lacking a leading N-M pattern may not block wall-clock for the matching board sid.

- source_spec: `planning-artifacts/specs/spec-23-1-wall-clock-fallback-derivation-from-promoted-spec-revision-fields.md`
  summary: Journal story_key lacking a leading N-M pattern may not block wall-clock for the matching board sid.
  evidence: Pre-existing journal key convention; loop homes emit N-M-slug keys. Edge-case hunter only; not introduced by CAP-1 derivation logic beyond shared _sid_from_journal_key.
  location: docs/dashboard/generate.py:_sid_from_journal_key
  origin: spec-deferred a67ea55883b2 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-23-2: Velocity panel `sub` still lumps unmeasured stories under "predate loop instrumentation"; full absence-class partitioning is Story 23.3 (CAP-3).

- source_spec: `planning-artifacts/specs/spec-23-2-wall-clock-is-never-blended-with-active-compute.md`
  summary: Velocity panel `sub` still lumps unmeasured stories under "predate loop instrumentation"; full absence-class partitioning is Story 23.3 (CAP-3).
  evidence: CAP-2 only requires wall-clock vs active-compute class labels. Intent explicitly defers 23.3. Surfaced by blind-hunter + intent-alignment.
  location: docs/dashboard/generate.py:scan_timing velocity.sub
  origin: spec-deferred e334aaacbac9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-23-2-2: No runtime render fixture asserts emitted chip class HTML against mixed DASHBOARD_DATA; coverage is generator unit tests + static HTML needles.

- source_spec: `planning-artifacts/specs/spec-23-2-wall-clock-is-never-blended-with-active-compute.md`
  summary: No runtime render fixture asserts emitted chip class HTML against mixed DASHBOARD_DATA; coverage is generator unit tests + static HTML needles.
  evidence: verification-gap review; check_render.js is no-throw only. Acceptable for CAP-2 land; strengthen later if chip regressions recur.
  location: docs/dashboard/index.html
  origin: spec-deferred 44ab09a08fa7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-CANOPY-2026-08-24: Static Guildhall console planning retired; code deletion gated on steward parity

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-factory-console/SPEC.md`
  summary: Lane 1 Wagtail (steward `spec-pyforge-unifying-strategy` CAP-2) supersedes `spec-factory-console` as the estate front-door contract. Planning retirement applied 2026-08-24 via `sprint-change-proposal-2026-08-24-canopy.md`.
  evidence: Operator approved Phase 5 of `docs/dreams/pyforge-unifying-strategy.md`; steward Epics 20 + 30 own Wagtail front door and post-parity removal of `docs/dashboard/` generator / pixi tasks / `data.js`.
  location: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-factory-console/SPEC.md`; `docs/dashboard/` (code — **not deleted this pass**)
  origin: bmad-correct-course — marshal station, headless-express batch (2026-08-24)
  severity: medium
  promoted: 2026-08-24
  status: open
  carve-outs: `docs/dashboard/kedro-viz/**` is atlas-owned publish — not in deletion scope; marshal Epic 16 generator plumbing is not Lane 1 CMS; supervisor bmad-loop ingest deferred to steward Epic 21 (marshal hooks later)
  successor: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md` CAP-2; steward Stories 20.x (front door), 30.2 (code removal)
  resolution_gate: steward Story 30.2 after console-parity inventory (Epic 20 + 21.5)

## DW-OM-2026-08-24 — Operating-model obligations (all eight stations)

- source_spec: cross-cutting (pyforge-unifying-strategy Grounding Q1–Q8; steward SCP operating-model, §6 revisited)
  summary: Estate OM + CAP-18: shared hook-spec in pyforge-core; Warden Epic 9 is the PR-gate retrofit; this station extracts one process hook spec (today's backend = default plugin).
  owner: station planning (this file) + steward (Canopy FRs) + warden (PR-gate hook specs)
  status: open
  recorded: 2026-08-24
  close_when: steward S-32.1 done; marshal S-26.1 done (loop/runner hook spec; today's runner is default plugin); no competing CI verdict
