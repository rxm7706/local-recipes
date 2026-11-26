---
sources:
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py
  - scripts/detectors.py
  - tests/scripts/test_exit_code_domains_are_declared.py
  - scripts/governance_currency_check.py
  - docs/governance/guild-roster.json
  - src/shared/packages/pyforge-core/src/pyforge/core/exit_domains.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py
verified: 2026-11-25
---

# The judgement vocabulary — what each word means, positively

Every word here names something that *judges* work in this estate. Until 2026-09-14 four of
them were defined only by what they are **not** — "not a gate", "not a second verdict" — which
is why five separate surfaces each concluded, in their own docstrings, that they were violating
a rule they were not violating. This page states each one positively.

Constitutional authority is `docs/dreams/pyforge-charter.md` § The Lexicon and § Execution
Doctrine; where this page and the Charter disagree, the Charter wins and this page is wrong.

## The two that carry constitutional weight

**verdict** — a station's judgement **about work it did not do**. Reserved. Only a station
publishes one, and only Warden publishes *the PR verdict*. A deterministic check that fails CI
is not a verdict however loudly it exits. `pyforge-warden` enforces this mechanically: a plugin
that does not own the verdict spec raises `SecondVerdictError`.

**gate** — three legitimate senses, ruled 2026-09-14. Say which:

| Sense | Who | Blocks a PR? |
|---|---|---|
| **the PR verdict** | Warden, solely | yes |
| **the harness gate** — `detectors-ci`, a `*-check` task, `gate_mode`, a loop's verify gate | any surface | may fail CI; this is not a verdict |
| **BMAD's readiness gate** — `PASS` / `CONCERNS` / `FAIL` | upstream | not ours to redefine |

The second sense is why `detectors-ci` failing CI has never been a violation: § Execution
Doctrine already places CI verify gates in the **harness**, the unit of governance. Governance
gates; stations judge.

## The operational four

**detector** — a bounded, deterministic reader that produces `Finding`s and declares its own
scope. `DETECTOR = {"scope": "repo"}` reads tracked files only and runs anywhere;
`{"scope": "runtime"}` reads host state (tmux, `~/.bmad-loops`, gitignored Tier-3 feeds) and
therefore cannot run in CI. Registered in `scripts/detectors.py`. A detector **reports**; it does
not decide what to do about what it finds.

**check** — overloaded, and the overload is not worth removing because three of its four jobs
are load-bearing in different layers. Say which when it is not obvious from context:

- the `Finding.check` **field** — which check produced this finding
- `marshal check` — a **CLI verb** that relays the detector registry
- a **scope check** — one of marshal's three gate kinds
- the `*-check` **task-name suffix** — about 70 pixi tasks, most of them detectors

**preflight** — a check that runs **before** the thing it guards, and whose failure means "do not
proceed", not "this is broken". `frame-preflight` is the exemplar: it is explicitly **not** a
detector, never joins `detectors`/`detectors-ci`, and Warden stays the sole PR verdict.

**advisory** — a finding that **obliges a reader, not a pipeline**. It is recorded, it is
expected to be read, and nothing blocks if it is ignored. This is the positive definition the
estate lacked: "advisory" does not mean *unimportant*, it means *the decision stays with a
human*. Doctor's findings are advisory by design — Doctor reports operability, not policy.

**lens** — a named point of view a reviewer or review agent applies to the same artifact, so that
two passes over one diff look for different things. Used by `bmad-review` and the Guard library.
A lens produces findings; it never produces a verdict.

## Severity and exit codes

`fail` · `warn` · `ok` are Doctor's three; **`warn` never changes an exit code**.

**Exit codes do not agree across surfaces, and `2` inverts** — this is the estate's sharpest
trap, and it has caused at least one real misread:

| Surface | Domain | What `2` means |
|---|---|---|
| a doctor source (`python -m pyforge.doctor.sources <name>`) | `{0, 2, 130}` | **FAIL — findings exist** |
| `scripts/detectors.py` (the aggregator) | `{0, 1, 2}` | **could not run** |
| `pyforge-warden` | `{0, 1, 2, 130}` | error |
| `pyforge-marshal` | `{0, 1, 2, 3, 4, 130}` | scope-violation (`3` is gate-failed) |
| `pyforge-marshal seed` | `{1, 2, 3, 4, 5, 10}` | usage error (`5` is an invalid state file, `10` an internal error) |
| `pyforge-mason` | `{0, 1, 2, 3, 130}` | usage error (`3` is conda-forge-expert not found) |
| `pyforge-herald` | `{0, 1, 2, 3, 4, 130}` | usage error, or a verb whose flag is off (`3` is a conflict, `4` a transport failure) |
| `pyforge-steward` | `{0, 1, 2, 3, 70, 130}` | usage error, or a kill switch that is off (`3` is a documented refusal, which is also how `ci`, `pages` and `estate` answer with their flag off; `70` a crash; `keys exec` and `deploy nic` return their child's own code) |
| `pyforge-scribe` | `{0, 1, 2}` | usage error or could not run (`1` is `catalog bmad-estate --check` drift) |
| `pyforge-atlas` | `{0, 1, 2, 130}` | usage error, or a refused flag (`pyforge atlas` itself exits `0`, `1` or `2`; `130` is its other entry points') |
| argparse, on any of them | `2` | invalid arguments |
| script-based detectors (`scripts/*_check.py`) | `{0, 1}` or `{0, 1, 2}` | **could not run**, where the script has a `2` (`flag_gate_check.py`, `pixi_version_check.py`); `governance_currency_check.py` returns `0` or `1` and exits `2` only when it crashes |

Doctor's subset of warden's domain is deliberate and documented (the module docstring of Doctor's `verdict.py`: it
omits warden's policy rung `1` because Doctor reports operability, not policy). The collision
with the aggregator's `2` is **not** deliberate, and it stays: changing a live exit code would break
every caller that reads one. What changed is that it is declared, not only described.

**The declaration.** The first ten rows are declared once, by member name and number, in
`docs/governance/guild-roster.json`'s `exit_code_domains` (domains `doctor`, `detectors`, `warden`,
`marshal`, `marshal-seed`, `mason`, `herald`, `steward`, `scribe`, `atlas`), which also declares doctor's domain a narrowing of warden's
(`exit_code_domains_narrowing`); `pyforge.core.exit_domains` carries the same table for in-process
code (spec-pyforge-steward:CAP-184, `DW-VOCAB-2026-09-14-8`). Doctor's, warden's and marshal's verdict
modules, marshal's `seed/errors.py` and `scripts/detectors.py` take their numbers from it, and
`tests/scripts/test_exit_code_domains_are_declared.py` fails when a module, or this table, differs from
the declaration. Mason, herald, steward, scribe and atlas have no verdict module: each spells its own
numbers, and a meta-test in its own suite (`test_exit_codes_match_the_exit_declaration.py`) fails when
one differs from its declared domain (steward Story 142.1). Read a code in the domain of the surface that produced it, never another's.

**The aggregator's four row words.** `scripts/detectors.py` reads each row as `pass`,
`FINDINGS` (exit `1`), `unknown` (could not run, exit `2`) or **`unmeasured`**. A Doctor row is
`unmeasured` when the source ran but measured nothing: its findings hold no `fail` and every one
is a gather failure (`is_gather_failure` in Doctor's `models.py`: a cannot-evaluate `warn` with
evidence `unevaluable: true`, a `degrade_on_exception` `warn`, the atlas sentinel). `unmeasured`
is never `pass`: the text table marks it `○` and the summary line counts it. It is a warning the
merge bar does not fail on, so it exits `0` (spec-pyforge-doctor AD-15, operator ruling of
2026-11-10). An empty result still reads `pass`, because a source returns nothing only after it
measured.

**Never read a detector's result through a pipe.** `cmd | grep x | head -5` then `echo $?`
reports *`head`'s* status, not the detector's, and `head` truncates findings out of view.
Redirect to a file, check the exit code directly, then read the whole list.

## What this page deliberately does not do

It does not rule on anything. `Gate`, `Track` and `kernel` were ruled by Charter amendment;
this page restates those rulings for a reader who needs them at hand and adds positive
definitions for the operational words that had none. Adding a word here is documentation;
changing what one *means* is a Charter amendment.
