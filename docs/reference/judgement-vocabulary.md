# The judgement vocabulary — what each word means, positively

Every word here names something that *judges* work in this estate. Until 2026-09-14 four of
them were defined only by what they are **not** — "not a gate", "not a second verdict" — which
is why five separate surfaces each concluded, in their own docstrings, that they were violating
a rule they were not violating. This page states each one positively.

Constitutional authority is `docs/dreams/pyforge-charter.md` § The Lexicon and § Execution
Doctrine; where this page and the Charter disagree, the Charter wins and this page is wrong.

---

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

---

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
- the `*-check` **filename suffix** — ~30 pixi tasks that are detectors

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

---

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
| argparse, on any of them | `2` | invalid arguments |
| script-based detectors (`governance_currency_check.py` and friends) | `{0, 1}` | n/a — this domain has no `2` at all |

Doctor's subset of warden's domain is deliberate and documented (`doctor/verdict.py:4-7`: it
omits warden's policy rung `1` because Doctor reports operability, not policy). The collision
with the aggregator's `2` is **not** deliberate and is tracked as `DW-VOCAB-2026-09-14-8`.

**Never read a detector's result through a pipe.** `cmd | grep x | head -5` then `echo $?`
reports *`head`'s* status, not the detector's, and `head` truncates findings out of view.
Redirect to a file, check the exit code directly, then read the whole list.

---

## What this page deliberately does not do

It does not rule on anything. `Gate`, `Track` and `kernel` were ruled by Charter amendment;
this page restates those rulings for a reader who needs them at hand and adds positive
definitions for the operational words that had none. Adding a word here is documentation;
changing what one *means* is a Charter amendment.
