---
title: "A first estate caller of mason recipe"
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Once the `recipe` verb family runs in mason's own env (Story 16.1), nothing in the
estate actually invokes it — `pixi.toml:797` is a comment, not a call site, and zero other call
sites exist. All recipe work still routes through `pixi run -e local-recipes recipe-build`. This
is the same "built but not in effect" gap the 2026-09-09 fleet-readiness pass flagged for mason
(steward Epic 49, C6): Story 49.2's effect check requires a caller outside the capability's own
test file, and `mason recipe` has none.

**Approach:** Move one real estate route onto mason: a pixi task (or a CI step) that builds one
recipe through `mason recipe build` rather than `pixi run -e local-recipes recipe-build`, chosen so
the route is exercised on every run of an existing lane rather than only on demand. Record a green
run with its command and output. The delegation boundary is unchanged — mason still wraps CFE
(Rule 1); this does not add recipe knowledge to mason.

## Boundaries & Constraints

**Always:**
- Depends on Story 16.1 (`mason doctor` must report the `recipe` verb available before this story
  can wire a caller to it).
- The new caller must live **outside** mason's own test tree (Story 49.2's effect-gate condition:
  "a caller outside its own test file").
- Choose a route exercised on every run of an existing lane, not only on demand — this is what
  proves the capability is *in effect*, not merely *available*.
- `mason doctor` must report the verb available on the lane's own env after the caller is wired.
- Record the green run's actual command and output as evidence.
- The delegation boundary is unchanged: mason still wraps CFE (Rule 1) — no recipe judgment is
  added to mason to make this route work.
- The effort ends with the Rule-2 retro.

**Never:**
- Do not replace `pixi run -e local-recipes recipe-build` as the estate's primary recipe-build
  route — this story adds one real caller, it does not migrate the whole estate off the existing
  path.
- Do not add recipe-domain knowledge (gotchas, pins, format defaults) to mason to make the new
  caller work — any such judgment stays inside CFE, reached only through the existing wrapper.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New caller added | A pixi task (or CI step) is wired to call `mason recipe build` for one real recipe | The task/step exists outside mason's own test tree | N/A |
| Green run recorded | The new caller is executed | A green run's command + output is recorded as evidence | A red run means the story is not done — no caller should be left pointing at a broken invocation |
| `mason doctor` on the lane's env | `mason doctor` run in the same env the new caller uses | Reports the `recipe` verb available | If unavailable, Story 16.1's fix has not propagated to this lane's env — blocks this story |
| Realization-gate read | The Unifying realization gate inspects mason's CAP-2 status | Reads CAP-2 as "exercised in the running estate" rather than "decomposed and merged" | N/A |

</intent-contract>

## Code Map

- `pixi.toml` — candidate location for the new task (near existing `feature.pyforge-mason.tasks.*`
  entries, or a new one), or alternatively a step added to an existing `.github/workflows/**` lane.
  `pixi.toml:797`'s existing comment marks where the wiring is currently *not* done.
- `.github/workflows/**` — alternative/complementary surface if the route is wired as a CI step
  instead of (or in addition to) a pixi task.
- Documentation naming the route (whichever doc currently tells contributors how recipes are
  built — e.g. `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` or this
  project's own docs) — update to name the new mason-backed route alongside the existing one.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py` (read-only reference) — the
  `recipe build` use-case this story calls into; no code change expected here (Story 16.1 already
  makes it reachable).
- `src/shared/packages/pyforge-mason/src/pyforge/mason/doctor.py` (read-only reference) — the
  report this story's evidence must show flipping to verb-available on the calling lane's env.

## Tasks & Acceptance

**Execution:**
- `[feature]` Wire one real estate route (a pixi task, or a CI workflow step) that builds one
  recipe via `mason recipe build`, placed so it runs on every execution of an existing lane.
- `[feature]` Point that route at mason's own env (post-16.1) so `mason doctor` reports the
  `recipe` verb available there.
- `[docs]` Update whatever documentation names the recipe-build route to mention the new
  mason-backed caller.
- `[chore]` Run the new route, capture a green run's command and output as recorded evidence.

**Acceptance Criteria:**
- Given the `recipe` verb family runs in mason's own env (16.1) but nothing in the estate invokes
  it — `pixi.toml:797` is a comment and there are zero call sites.
- When one real estate route is moved onto mason: a pixi task (or a CI step) that builds one
  recipe through `mason recipe build` rather than `pixi run -e local-recipes recipe-build`, chosen
  so the route is exercised on every run of an existing lane rather than only on demand.
- Then the caller exists outside mason's own test tree, a green run is recorded with its command
  and output, `mason doctor` reports the verb available on that lane's env, and the Unifying
  realization gate can read mason's CAP-2 as *exercised in the running estate* rather than
  *decomposed and merged*. The delegation boundary is unchanged — mason still wraps CFE (Rule 1),
  and the effort ends with the Rule-2 retro.

## Spec Change Log

## Review Triage Log
