# Spike report: Copier API fit (Spike-0, Story 7.6)

**Status:** PASS — all 5 Spike-0 criteria hold on `copier==9.17.0`. No AD-52 amendment, no
`bmad-correct-course` needed. This spike's own gate on Story 10.1 is cleared — but Story 10.1's
`Deps:` are `S-7.6, S-7.3` (epics.md:1925), and S-7.3 remains `blocked` in the tracked sprint
status as of this writing, so Epic 10 build-start is **not** fully unblocked by this story alone.
**Owner station:** Marshal (gates `seed/engine/copier.py`, Epic 10 / Story 10.1).
**Disposition:** spike code discarded per its own constraints — nothing under `src/` changed, no
`copier` dependency added anywhere in this repo. See § Cleanup.

---

## Purpose

Epic 10 will build `seed/engine/copier.py` — the single seam through which the rest of Genesis
speaks to the Copier templating library (A-04, P-02) — on five assumptions about Copier's public
API (AD-52, FR-120, architecture.md § *Spike-0*). Getting one of those assumptions wrong after
seven stories depend on it is far more expensive than getting it wrong now, with nothing built
yet. This spike exercises the real library, on the pinned version, before any of that code
exists, and records a pass/fail verdict with reproducible evidence for each assumption. (The
epics AC also carries the `AD-54` tag alongside `AD-52, A-04, FR-120`; AD-54 governs `marshal
seed check` vs. `bmad_drift_check.py` and is unrelated to Copier's API — none of the five
Spike-0 criteria exercise it, and it is not addressed by this spike.)

## Method

- A throwaway, git-backed Copier template and one or more destination repos were built entirely
  under the OS scratch directory — never under this repo's working tree, never committed.
- `copier==9.17.0` (the architecture's NFR-C2 floor) was installed into an isolated,
  non-repo virtualenv; no other version was tested.
- The template and destinations were exercised exclusively through Copier's **public API**
  (`copier.run_copy`, `copier.run_update`) — never `Worker` internals or private modules — per
  A-04/FR-120's binding constraint that Genesis may only ever depend on that surface.
- Each of the five behaviors in architecture.md § *Spike-0* / the spec's I/O & Edge-Case Matrix
  was driven to an explicit, reproducible outcome, not inferred from reading Copier's source
  alone (source-reading was used only to explain a result once observed, per finding 5 below).
- After the run, the scratch-directory venv, template, and destination repos were discarded; none
  of it is a shipped artifact of this story.

## Results by acceptance criterion

### AC1 — Dry-run copy performs zero writes

**Tested:** `run_copy(tmpl, dst, pretend=True)` against an empty destination.
**Result: PASS.** No files were written to `dst`; the call returned a `Worker` whose `.answers`
was populated and usable, so a caller can inspect what *would* have happened without any
filesystem side effect. This is the mechanism a future `marshal seed --dry-run` (FR-124) can
build on directly.

### AC2 — `skip_if_exists` preserves a pre-existing file and still creates its siblings

**Tested:** a destination with a pre-existing file matching the template's `skip_if_exists` list
(a template with exactly one skipped file and one other file — the sibling count tested is 1,
not a multi-file/glob set).
**Result: PASS.** That file's bytes were left completely untouched by the copy; the template's
other (non-skipped) file was still created normally. Partial-preserve semantics work as the
architecture assumes for this shape; `skip_if_exists` is a pure glob-pattern filter independent
of how many other files the template has, so this is expected to generalize, but a multi-sibling
case was not itself exercised.

### AC3 — `data=` + `defaults=True` fully suppresses interactive prompting

**Tested:** `run_copy` with `data={...}` and `defaults=True`, invoked in a subprocess with
`stdin=DEVNULL`.
**Result: PASS.** The process exited 0 with no prompt attempted. Running with a closed stdin
proves suppression is real rather than merely "no prompt happened to fire" — if Copier had tried
to prompt, reading from a closed stdin would have raised or hung, and it did neither. This is
what makes an unattended `marshal seed init --json --quiet` (FR-123) safe.

### AC4 — Answers-file path is template-configurable

**Tested:** template's `copier.yml` set `_answers_file: .marshal/.copier-answers.yml`; ran
`run_copy` and checked where the answers file materialized.
**Result: PASS.** The file was written at the configured path and **not** at Copier's library
default (`.copier-answers.yml`). AD-52's own specified fallback ("if the answers-file relocation
proves unsupported... it stays at the repo root and the rule is otherwise unchanged",
architecture.md:975-976) does not trigger — Genesis can rely on template-level configuration to
place the answers file inside `.marshal/` as AD-52 specifies.

### AC5 — `run_update` resolves the PEP 440-latest tag, not the lexicographically-largest one

**Tested:** template tagged `v1.9.0`, then `v1.10.0` with changed content; destination copied at
`v1.9.0`; `run_update()` called with no explicit `vcs_ref`.
**Result: PASS.** The update resolved to `v1.10.0` and pulled its content. This confirms Copier
orders tags by parsed version (`1.10.0 > 1.9.0`), not by lexicographic string comparison (which
would incorrectly rank `"1.10.0" < "1.9.0"` and select the wrong tag). Confirmed two ways: the
observed behavior, and by reading `copier._vcs.get_latest_tag` — verified present under that
exact name in the pinned `copier==9.17.0` install itself (not inferred from a different
installed version) — which sorts tags via `packaging.version.parse(...)`, `reverse=True`: an
implementation-level confirmation of the empirical result, not a substitute for it. (This
function's name should be re-checked if the `copier` pin is ever bumped past `<10`.)

**Verdict: all five ACs PASS on `copier==9.17.0`.** Per the spec's own pass criterion ("all five
hold"), this is met outright — no AD-52 amendment and no `bmad-correct-course` pass is triggered.

## Incidental mechanism findings (must-know for Story 10.1 — the Copier engine wrapper)

These two findings did not affect the pass/fail verdict above, but they are load-bearing facts
about *how* to call the public API correctly, discovered only by exercising it. Both are also
recorded as a deferred-work ledger entry addressed to whoever implements S-10.1.

**Finding 1 — the answers file is not auto-generated; the template must ship a literal file for
it.** Copier does not write `.copier-answers.yml` (or its configured relocation, e.g.
`.marshal/.copier-answers.yml`) on its own initiative. The **template** must ship a literal
`{{ _copier_conf.answers_file }}.jinja` file — recommended body:
`{{ _copier_answers|to_nice_yaml -}}`, using the `to_nice_yaml` filter from
`jinja2_ansible_filters.AnsibleCoreFiltersExtension`, which Copier loads as a default Jinja
extension. **Confirmed by reproduction, both directions**: with no such file in the throwaway
template, `run_copy` never wrote the answers file at any path, on any verb tested; adding the
literal `{{ _copier_conf.answers_file }}.jinja` file to the same template made it appear at the
configured path on the next run. This is new information beyond the already-deferred
"`.marshal/.copier-answers.yml` has no manifest entry" gap (Story 7.5's review): that earlier
gap is about manifest *coverage*; this one is about the template *content* required for the
file to come into existence at all — fixing the manifest entry alone would not fix this.

**Finding 2 — `run_update` needs `answers_file=` passed explicitly on every call.**
`run_copy` already knows the template up front and reads its `_answers_file` setting, so AC4
above holds for it unconditionally. `run_update`, however, resolves the *destination's existing*
subproject before it knows which template produced it — a chicken-and-egg problem the library
resolves by defaulting `subproject.answers_relpath` to the hard-coded `.copier-answers.yml`
unless `answers_file=` is passed to the call itself
(`copier._main.Worker.subproject`, `answers_relpath=self.answers_file or Path(".copier-answers.yml")`).
Confirmed by reproduction: omitting `answers_file=` on `run_update` reliably raised
`TypeError: Template not found`, even though the answers file existed on disk at the configured
path. **The future `engine/copier.py` wrapper must hard-code `answers_file=".marshal/.copier-answers.yml"`
on every `run_copy`/`run_update` call** — it cannot rely on template-level configuration alone
for update. `run_recopy` shares `run_update`'s exact `answers_file` parameter and the same
dst-first resolution shape (per its signature), so the same requirement almost certainly applies
there too — **but this spike did not independently exercise `run_recopy`**, only `run_copy` and
`run_update`; treat the `run_recopy` half of this recommendation as inferred by API symmetry,
not empirically confirmed, and worth a quick direct check before or during S-10.1.

## Noted, not actioned

A `Make sure Git >= 2.24 is installed to improve updates.` warning printed during the update test
despite git 2.55 being installed on the test machine; the update still completed correctly via
the documented fallback path (`copier._main.py`'s `except ProcessExecutionError` branch retries
with `--inter-hunk-context=0`). This is not one of the five Spike-0 criteria and required no
action — noted here only for completeness in case a future maintainer sees the same warning and
wonders whether it signals a real problem.

## Cleanup

- Nothing under `src/` was created or modified by this story — `seed/engine/copier.py` remains
  Epic 10's surface to build, not this spike's.
- No `copier` dependency was added to `pixi.toml` or `pyproject.toml` — root-level packaging
  wiring is out of scope for Epic 7 per epic-7-context.md § Technical Decisions.
- The scratch-directory venv, throwaway git template, and destination repos used for the
  investigation were removed; none were ever inside this repo's working tree.

## Known test-coverage gaps (not required by the five Spike-0 criteria; deferred)

Four scenarios adjacent to the five ACs were not exercised in this spike, each beyond what the
epics AC literally requires: `pretend=True` against a non-empty (update-style) destination;
`skip_if_exists` where the listed file does *not* yet exist in the destination (first `init`);
a required template variable with no default, omitted from `data=`, under closed stdin; and a
malformed/non-PEP-440 git tag in `run_update`'s ordering. None of these change the PASS verdict
above; all four are recorded in `deferred-work.md` for whoever hardens `engine/copier.py` (S-10.1)
or its tests to pick up.

## Recommendation

Epic 10 / Story 10.1 can proceed with the assumptions in AD-52, A-04, and FR-120 exactly as
written — no architecture amendment is needed. Story 10.1 also depends on S-7.3 (currently
`blocked`), so this spike alone does not fully unblock Epic 10's build order — see § Status.
Story 10.1's implementation of `seed/engine/copier.py` must incorporate the two mechanism
findings above as hard requirements, not optional refinements: ship the
`{{ _copier_conf.answers_file }}.jinja` file in `seed/templates/`, and pass
`answers_file=".marshal/.copier-answers.yml"` explicitly on every `run_copy`/`run_update` call
the wrapper makes (and, pending a direct check, `run_recopy` too).
