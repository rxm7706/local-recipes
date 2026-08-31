---
title: 'Story 12.4: Dream chain gap count surfaces in the ambient ATTENTION block'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
baseline_revision: '7a05d2003404ea43fc0d7552440df2a89ce2c886'
final_revision: '73b5fae5b476afde24f1a3c0d6f54e236b906d45'
---

<intent-contract>

## Intent

**Problem:** `pyforge.doctor.sources dream-chain` already knows, per Dream, which Dreams
fleet-wide have no Spec (INV-1 `dream-without-spec` findings — 17 live today, e.g.
`bmad-loop-liveness-footgun`, sitting unspecced for weeks) — but that signal only surfaces
when someone remembers to invoke the detector. Nothing ambient names the gap in the report
an operator already checks every landing pass, so unspecced Dreams go unnoticed until a
pointed manual run (CAP-4, `spec-fleet-hygiene-verification-exemplar-program`).

**Approach:** Add a `dream_chain_gap_findings()` consumer to `scripts/fleet_picture.py`
mirroring `bmad_core_drift_findings`/`verification_staleness_findings`' established
subprocess shape (`sys.executable -m pyforge.doctor.sources dream-chain --json`), filtered
to the `dream-without-spec` (and `dream-chain-unevaluable`) kinds; `main()`'s ATTENTION
block prints ONE `watch`-list count line naming N and a few example slugs. No `pyforge-doctor`
package change — the detector already emits everything needed.

## Boundaries & Constraints

**Always:**
- `fleet_picture.py` never imports `pyforge.doctor` directly — cross-package data only via
  the `sys.executable -m pyforge.doctor.sources <check> --json` subprocess pattern the two
  adjacent consumers already establish.
- The new function raises on failure; degrading to one "could not check dream-chain gaps"
  `watch` line is `main()`'s job, via the same `try/except Exception` idiom every other
  ATTENTION probe uses. `fleet-picture` must still always exit 0.
- **Accept exit codes {0, 2} from the subprocess as success.** This is the one deliberate,
  load-bearing deviation from the `check=True` idiom the two sibling consumers use: unlike
  their WARN-only sources (which exit 0), `dream-without-spec` findings are FAIL-status, so
  `exit_code_for` makes the CLI exit 2 on ANY real gap (verified live: exit=2 with 17 gaps
  today). A verbatim `check=True` mirror would raise `CalledProcessError` on exactly the
  case this story exists for and degrade every real invocation to "could not check". Any
  OTHER exit code still raises.
- Keep `dream-chain-unevaluable` findings visible: `chain.py`'s own history (its
  `_collect_dreams`/`_collect_specs` docstrings) records that an unreadable `docs/dreams/`
  once turned a real `dream-without-spec` FAIL into silence. If the consumer filtered them
  out, a zero count would be indistinguishable from an unevaluable chain — so when any
  unevaluable finding is present, `main()` appends one "count may be understated" line.
- Ambient report only, never a gate: the line goes to `watch`, never `needs`; no exit-code
  change; silent when the count is 0 and nothing is unevaluable (matching
  `bmad_core_drift_findings`' clean-state silence).

**Block If:** none identified — reuses an already-shipped detector and an
already-established integration pattern; the exit-code deviation above is resolved in this
spec, not left open.

**Never:**
- Never modify `src/shared/packages/pyforge-doctor/` — `gather_dream_chain` already emits
  the needed findings; this story is consumer-side only.
- Never print one line per unspecced Dream (17 today would flood the block) — one count
  line, with at most 3 example slugs.
- Never count the other dream-chain kinds (`spec-without-dream-link`, `owner-unassigned`,
  `spec-location-mismatch`, INV-3 kinds, the vacuous `dream-chain` OK) toward N — CAP-4 is
  the Dreams-without-Spec count only.
- Never touch `loop_home_staleness`, `bmad_core_drift_findings`,
  `verification_staleness_findings`, `running_stations`, or any other existing
  `fleet_picture.py` behavior.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real gaps | CLI exits 2, JSON has 17 `dream-without-spec` + other kinds | Function returns the 17 (+ any unevaluable); `main()` prints one `watch` line: count 17 + first 3 slugs + `dream-chain-check` pointer | No error |
| Clean chain | CLI exits 0, JSON is the single `dream-chain` OK finding | Function returns `[]`; no line printed | No error |
| Unevaluable only | JSON has `dream-chain-unevaluable` but no `dream-without-spec` | No count line; one "could not be fully evaluated — count may be understated" `watch` line | No error |
| Gaps + unevaluable | Both kinds present | Count line AND understated-warning line | No error |
| Subprocess hard failure | Exit code not in {0, 2} (e.g. 127) | Function raises `CalledProcessError` | Caller degrades to one "could not check dream-chain gaps" `watch` line |
| Malformed JSON | stdout not JSON | Function raises `json.JSONDecodeError` | Caller degrades, same line |

</intent-contract>

## Code Map

- `scripts/fleet_picture.py` -- (1) `dream_chain_gap_findings(repo=REPO, timeout=30)` directly
  after `verification_staleness_findings` (timing comment: ~0.4s bare module, ~4s through pixi
  env startup; 30s carries margin, same idiom as the sibling consumers' commented bounds);
  (2) a pure `_dream_chain_watch_lines(findings) -> list[str]` helper (see Design Notes);
  (3) `main()` wiring after the verification-staleness `try/except`:
  `watch.extend(_dream_chain_watch_lines(dream_chain_gap_findings()))` inside
  `try/except Exception: watch.append("could not check dream-chain gaps")`.
- `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_dream_chain_gap.py`
  (new) -- mirrors `test_fleet_picture_verification_staleness.py`'s
  `_load_fleet_picture()`/monkeypatched-`subprocess.run` harness; the fake
  `CompletedProcess` must carry a settable `returncode` to pin the exit-code contract; also
  unit-tests `_dream_chain_watch_lines` directly (pure function, no monkeypatching needed).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` +
  `sources/__init__.py::degrade_on_exception` -- READ ONLY reference: `_check_dream_chain`
  (INV-1 branch), `_gather_dream_chain` (finding shapes), the total-degrade WARN shape.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/fleet_picture.py` -- add `dream_chain_gap_findings()` -- subprocess to
  `-m pyforge.doctor.sources dream-chain --json` WITHOUT `check=True`; raise
  `CalledProcessError(returncode, cmd, output=stdout, stderr=stderr)` unless returncode in
  {0, 2}; parse JSON; return items whose `check` is `dream-without-spec` or
  `dream-chain-unevaluable`, OR whose `check` is `dream-chain` with `status == "warn"` (the
  `degrade_on_exception` total-degrade shape; the vacuous OK is the same `check` with
  `status == "ok"` and stays filtered); docstring records the exit-code deviation, why, and
  its honest limit (argparse usage errors also exit 2 with empty stdout -- the JSON parse is
  the guard that actually fires there)
- [x] `scripts/fleet_picture.py` -- add pure `_dream_chain_watch_lines(findings)` -- count
  line when any `dream-without-spec` item exists: count + up to 3 example slugs from
  `(f.get("evidence") or {}).get("subject", "?")`, each sanitized
  `.split(chr(10))[0][:40]`, + the `pixi run -e local-recipes dream-chain-check` pointer;
  one directionally-neutral line ("dream-chain could not be fully evaluated -- the
  Dreams-without-Spec count may be wrong in either direction") when any
  unevaluable-equivalent item (either shape above) is present; `[]` otherwise
- [x] `scripts/fleet_picture.py` -- wire into `main()`'s ATTENTION block via
  `watch.extend(...)` inside `try/except Exception: watch.append("could not check
  dream-chain gaps")`
- [x] `test_fleet_picture_dream_chain_gap.py` -- unit-test the I/O matrix AND the helper:
  gaps-at-exit-2 returned (load-bearing); filter keeps both unevaluable shapes and drops
  `spec-without-dream-link`/`owner-unassigned`/`spec-location-mismatch`/the OK finding;
  unevaluable-only fixture at returncode 0 (its real exit code); non-{0,2} raises (cmd shape
  asserted on the raise paths too); malformed-JSON raises; helper: count-line format,
  3-slug cap, per-slug sanitization, neutral-wording line, both-lines case, `[]` when clean

**Acceptance Criteria:**
- Given N Dreams fleet-wide with no Spec, when `fleet-picture` runs, then its ATTENTION
  block names the count N in the `watch` list without any separate `dream-chain`
  invocation (CAP-4) — verified live against today's real 17-gap fleet.
- Given the dream-chain CLI exits 2 with valid JSON (the normal any-gap case), when
  `dream_chain_gap_findings()` runs, then it returns the findings rather than raising.
- Given the subprocess fails hard (exit ∉ {0, 2}, timeout, malformed JSON), when
  `fleet-picture` runs, then it degrades to one "could not check dream-chain gaps" line
  and still exits 0.
- Given the pre-existing fleet_picture + doctor test suites, when they run after this
  change, then every existing test still passes unmodified.
- Given the dream-chain gather totally degrades (exit 0, one `check="dream-chain"`
  `status="warn"` finding from `degrade_on_exception`), when `fleet-picture` runs, then the
  ATTENTION block carries the could-not-fully-evaluate line -- never silence.

## Design Notes

- **Two unevaluable shapes, one meaning.** `chain.py` emits per-cause
  `dream-chain-unevaluable` findings, but `degrade_on_exception` (wrapping the WHOLE gather)
  emits its WARN under `check="dream-chain"` -- the same `check` as the vacuous OK, separable
  only by `status`. Both mean "the count cannot be trusted"; the filter and the helper treat
  them identically. Verified live: total degrade exits 0 (WARN never changes the exit code),
  so no exception reaches `main()`'s except -- silence was the failure mode.
- **Directionally-neutral wording.** The intent-contract's literal "count may be understated"
  predates the review finding that spec-side unevaluable causes INFLATE the count (Specs
  dropped from `covered` make INV-1 fire falsely -- `_collect_specs`'s own comments). Per the
  Spec Change Log's precedence note, build "may be wrong in either direction", not the
  contract's literal string.
- **Helper extraction, unlike 11.7.** 11.7's `main()` consumer only echoed a pre-formatted
  `message`, so main()-level testing was rightly skipped there; this story's consumer ASSEMBLES
  a line (count, slug cap, sanitization), so that logic lives in a pure, directly-tested
  helper and `main()` stays one `watch.extend` inside the standard try/except.

## Spec Change Log

### 2026-08-21 — bad_spec loopback 1 (from review pass 1)

**Triggering findings (3 medium, deduplicated across Blind Hunter + Edge Case Hunter, each
re-verified against live code by the orchestrator before triage):**

1. **Total-degrade WARN masked.** `gather_dream_chain` is wrapped by `degrade_on_exception`,
   which on any unexpected exception emits ONE WARN finding named after its check argument —
   `check="dream-chain"`, `status="warn"` (verified at `sources/__init__.py::degrade_on_exception`)
   — and WARN-only means the CLI exits 0. The spec's filter enumeration (`dream-without-spec` +
   `dream-chain-unevaluable` only) dropped it, so a totally-degraded detector rendered the report
   silent — indistinguishable from a clean chain, the exact masking the Boundaries forbid. Only
   `status` distinguishes it from the vacuous OK (same `check` value).
2. **"Understated" is directionally wrong.** Spec-side unevaluable causes (unreadable
   `_bmad-output/projects/` or a project's `specs/` dir, a malformed spec entry —
   `chain.py::_collect_specs`'s own false-FAIL-propagation note) remove Specs from the `covered`
   set, so INV-1 then reports their Dreams as `dream-without-spec`: the count is OVERSTATED, with
   the unevaluable WARN alongside. Only the unreadable-`docs/dreams/` cause understates. The two
   intent-contract occurrences of "count may be understated" (Always bullet; I/O-matrix
   "Unevaluable only" row) are factually wrong about direction. The contract is read-only under
   this workflow, so THIS entry is the precedence record: the governing intent (unevaluable
   visibility so the count's trustworthiness is flagged — CAP-4 itself says nothing about
   direction) has exactly one reading, and the built line must be directionally neutral
   ("count may be wrong in either direction"), not the contract's literal string.
3. **Count-line assembly untested in `main()`.** The new formatting logic (count, 3-slug cap,
   pointer) had no unit test — unlike 11.7's precedent, where `main()` only echoed a
   pre-formatted `message`. Amended: the assembly becomes a small pure helper, unit-tested.

**Amendments (all outside `<intent-contract>`):** Code Map, Tasks, and new Design Notes rewritten
to (a) classify `check=="dream-chain" and status=="warn"` as unevaluable-equivalent (the vacuous
OK is the same `check` with `status=="ok"` and stays filtered), (b) directionally-neutral line
wording, (c) a pure `_dream_chain_watch_lines(findings)` helper called by `main()` inside the
existing try/except, unit-tested directly. Seven low findings folded into the same amendment so
re-derivation lands them: honest docstring on the exit-2 ambiguity (argparse usage errors also
exit 2 with empty stdout — the JSON parse is the guard that actually fires there), attach stderr
to the raised `CalledProcessError`, per-slug sanitization (first line, 40-char cap) instead of a
raw join, `(f.get("evidence") or {})` for present-but-null evidence, unevaluable-only test
fixture at returncode 0 (its real exit code), cmd-shape assertions on the raise-path tests,
timing comment corrected (~0.4s bare module; the earlier ~4s included pixi task startup).

**Known-bad states avoided:** (1) silent `[]` on total degrade; (2) an operator told "at least N"
while N is actually inflated; (3) untested f-string/slug-cap logic in `main()`.

**KEEP (worked, verified, must survive re-derivation):** the {0,2} exit-code acceptance with
`check=False` + raise on any other code (the load-bearing deviation, with tests pinning exit 2,
1, and 127); the subprocess-mirror shape and raises-while-caller-degrades contract; consumer-side
only (no `pyforge-doctor` package change); one count line + up to 3 example slugs + the
`pixi run -e local-recipes dream-chain-check` pointer, `watch` never `needs`, silent when clean;
the `test_fleet_picture_verification_staleness.py`-mirroring harness with settable `returncode`;
ruff-clean against the file's 12-finding pre-existing baseline.

## Review Triage Log

### 2026-08-21 — Review pass 1

- intent_gap: 0
- bad_spec: 3: (high 0, medium 3, low 0)
- patch: 7: (high 0, medium 0, low 7) — moot for in-place fixing (code re-derived); folded into
  the loopback amendment above so the re-derivation lands them
- defer: 0
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[medium]` `[bad_spec]` Edge Case Hunter: total-degrade WARN (`check="dream-chain"`,
    `status="warn"`, exit 0) filtered to `[]` — report silent, indistinguishable from a clean
    chain. Verified against `sources/__init__.py::degrade_on_exception`. Spec amended: that shape
    is unevaluable-equivalent.
  - `[medium]` `[bad_spec]` Blind Hunter: "count may be understated" directionally wrong —
    spec-side unevaluable causes inflate the count (`chain.py::_collect_specs` false-FAIL
    propagation, confirmed in its own comments). Spec amended to directionally-neutral wording;
    the Change Log entry above carries the intent-contract precedence note.
  - `[medium]` `[bad_spec]` Blind Hunter: count-line assembly untested in `main()`. Spec amended:
    pure `_dream_chain_watch_lines` helper, unit-tested.
  - `[low]` `[patch]` (folded x7 into the amendment): exit-2-ambiguity docstring honesty; stderr
    attached to `CalledProcessError`; per-slug sanitization (newline/length injection — deduped
    Blind Hunter + Edge Case Hunter); `evidence` present-but-null guard; unevaluable-only fixture
    at exit 0; raise-path cmd-shape assertions; timing-comment accuracy.
  - rejected (3, low): (1) `timeout`/`cwd` unpinned by tests — the sibling harnesses share the
    identical property (their `_fake_run` also ignores kwargs); established convention,
    over-pinning for the stakes; (2) third copy of the `_load_fleet_picture` harness should
    consolidate into a conftest — consolidation would edit sibling stories' landed test files,
    outside this story's surface, and the duplication pattern predates this story at N=2;
    (3) doctor package suite not re-run inside the review subagent — moot, the orchestrator
    re-ran it this same pass (1141 passed, 2 skipped).

### 2026-08-21 — Review pass 2 (on the re-derived implementation)

- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 0, low 4)
- defer: 1: (high 0, medium 0, low 1)
- reject: 6: (high 0, medium 0, low 6)
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (dedupe): `evidence.subject`
    present-but-null (or non-string) reached `.split` and raised out of the pure helper —
    `main()`'s except then converts a REAL gap count into "could not check dream-chain gaps".
    Unreachable from today's producer (always a str), but the `?` default already signaled
    intended tolerance. Fixed: `str((... or {}).get("subject") or "?")`; two new parametrized
    tests (None -> `?`, 42 -> `42`).
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (dedupe): `\r`/ESC (legal in POSIX
    filenames; a subject is a `docs/dreams/*.md` stem) survived the newline-only split while
    the adjacent comment claimed injection was closed — terminal overwrite/spoof of the
    printed line. Fixed: per-slug control-char scrub (`[\x00-\x1f\x7f]` -> `?`) after the
    first-line split, before the 40-char cap; comment now states exactly what is guarded; new
    test pins `\r` and `\x1b`. (The sibling consumers share the gap file-wide — left alone,
    outside this story's surface.)
  - `[low]` `[patch]` Blind Hunter: `main()`'s except comment claimed "reached on hard failure
    only", but a helper bug, an `OSError`, or wrong-shape JSON also land there with a real gap
    fleet upstream. Fixed: comment now enumerates "any probe or assembly failure" and scopes
    the never-case to the normal any-gap path.
  - `[low]` `[patch]` Blind Hunter: the filter's status asymmetry (`dream-chain-unevaluable`
    kept at ANY status vs `dream-chain` requiring `warn`) was deliberate but undocumented.
    Fixed: one docstring sentence recording the intent (a future FAIL-status unevaluable item
    must not silently vanish).
  - `[low]` `[defer -> DW-FU-12-4]` Blind Hunter: pre-existing foreign defect surfaced
    incidentally — `spec-dream-to-code-model-self-verification/SPEC.md:13`'s glob-less,
    trailing-slash surface entry (`.claude/skills/conda-forge-expert/tests/meta/`) matches
    nothing under `chain.py::_glob_to_re`'s exact-match rule; the directory is actually
    governed by pyforge-mason's `spec-packaging-factory` blanket glob. Minted into doctor's
    Tier-3 deferred-work file (worktree-local; relayed in the Auto Run Result since Tier-3 in
    a story worktree is ephemeral).
  - rejected (6, low; reviewer severities re-assigned by consequence): (1) the degrade AC's
    `main()` wiring untested — the assembly logic WAS extracted and tested per pass 1's
    remedy; the residual try/except + literal string is the identical shape of all five
    adjacent probes, none main()-tested (file-wide convention; a real `main()` test needs 6+
    faked subprocess surfaces — disproportionate); the degrade path is pinned at function
    level and the live smoke covers the wiring; (2) exit-2-with-clean-JSON consistency window
    — unreachable under `exit_code_for`'s verified contract; docstring already scopes its
    claim to the argparse case ("the guard that actually fires THERE"); (3) non-list-JSON
    shapes untested — the function's contract is "raises, caller degrades", already pinned
    for three failure classes; pinning the incidental exception type over-specifies;
    (4) trust line carries no command pointer in the unevaluable-only scenario —
    spec-conformant as built (the amended wording is verbatim), the line names `dream-chain`,
    and the scenario requires a broken tree with zero surviving gaps (rare, cosmetic);
    (5) harness `sys.modules`/global-`subprocess` patching hazards — convention shared
    verbatim with both siblings, monkeypatch teardown reverts the patch; diverging only this
    copy is worse; (6) module docstring / pixi task description do not enumerate the new
    probe — pre-existing pattern (10.3/11.7's probes are equally unenumerated) and
    `pixi.toml` is deliberately untouched (its change trips the repo's ungated env-sync CI
    gate, far outside this story's surface).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary.** `fleet_picture.py` now surfaces the Dreams-without-Spec gap count ambiently in
its ATTENTION `watch` list (CAP-4): a new `dream_chain_gap_findings()` consumer shells out to
`python -m pyforge.doctor.sources dream-chain --json` via the file's established subprocess
discipline, with the ONE load-bearing deviation from the sibling consumers — exit codes
{0, 2} are both success, because `dream-without-spec` findings are FAIL-status and make the
CLI exit 2 on any real gap (a verbatim `check=True` mirror would have degraded every real
invocation). The filter keeps `dream-without-spec`, per-cause `dream-chain-unevaluable`, and
`degrade_on_exception`'s total-degrade WARN (`check="dream-chain"`, `status="warn"` — caught
in review pass 1; without it a totally-degraded detector looked identical to a clean chain).
A pure `_dream_chain_watch_lines()` helper assembles one count line (count + up to 3
sanitized example slugs + the `dream-chain-check` pointer) and, when any
unevaluable-equivalent item is present, one directionally-NEUTRAL trust line (pass 1 found
"understated" factually wrong: spec-side unevaluable causes INFLATE the count). `main()`
wiring is one `watch.extend` inside the standard `try/except` degrade idiom; never `needs`,
never an exit-code change, silent when clean. No `pyforge-doctor` package change.

**Files changed:**
- `scripts/fleet_picture.py` — `dream_chain_gap_findings()` (+ exit-code-deviation docstring
  incl. its honest argparse-exit-2 limit and the filter's status-asymmetry rationale), pure
  `_dream_chain_watch_lines()` (per-slug first-line split + control-char scrub + 40-char cap,
  null/non-string subject tolerance), `main()` ATTENTION wiring.
- `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_dream_chain_gap.py` (new)
  — 22 tests: exit-code contract (2-is-success load-bearing, 1/127 raise with cmd + stderr
  asserted), filter (both unevaluable shapes kept, each singly at exit 0; INV-0/2 kinds + the
  vacuous OK dropped), malformed/empty stdout, and the pure helper (exact line format, 3-slug
  cap, newline/control-char sanitization, null evidence/subject, neutral wording pinned with
  an explicit `"understated" not in` guard, both-lines, clean-silence).
- Doctor Tier-3 `deferred-work.md` (worktree-local, ephemeral) — DW-FU-12-4 minted (foreign
  glob-less spec-surface entry defect; relay to the shared checkout when landing).

**Review findings breakdown:** pass 1 (Blind Hunter + Edge Case Hunter, no shared context):
3 medium bad_spec — total-degrade WARN masked; "understated" directionally wrong;
count-assembly untested in `main()` — triggering one spec-amendment loopback and full
re-derivation, with 7 low findings folded into the amendment and 3 rejected. Pass 2 (fresh
hunters on the re-derived diff): 0 intent_gap, 0 bad_spec, 4 low patched (subject
null/non-string guard; control-char scrub; except-comment accuracy; status-asymmetry
docstring), 1 low deferred (DW-FU-12-4), 6 low rejected (reasoning in the triage log).

**Follow-up review recommendation:** false — pass 2's independent review of the re-derived
code found no intent/spec-level issues; its four patches are localized (one expression + two
comments + one docstring sentence), behavior-preserving on the live path, and each is pinned
by a new test.

**Verification performed (orchestrator-run, post-patch):** four fleet_picture meta test
modules — 40 passed (22 new + 18 pre-existing); `pyforge-doctor-test` — 1141 passed,
2 skipped (package untouched, regression guard); `ruff check scripts/fleet_picture.py` — 12
findings before AND after (identical pre-existing set, verified via `git stash` baseline
comparison), new test file clean; `pixi run --frozen -e local-recipes fleet-picture` — exit
0, ATTENTION shows `17 Dream(s) with no Spec (e.g. asgi-multiplexer-monolith,
bmad-loop-liveness-footgun, bmad-method-core-upgrade) -- run pixi run -e local-recipes
dream-chain-check for the full list` against today's real 17-gap fleet, run both before and
after the pass-2 patches.

**Residual risks:** the committed test file joins pyforge-mason's `spec-packaging-factory`
blanket-glob surface — the landing session should expect a `drift-presumed` WARN there until
that baseline is re-stamped AFTER `git add` (the three sibling test files already carry the
same pre-existing WARN); the underlying mis-scoped surface entry is DW-FU-12-4. The
intent-contract's literal "understated" wording remains superseded by the Spec Change Log's
precedence note (contract is read-only under this workflow).
