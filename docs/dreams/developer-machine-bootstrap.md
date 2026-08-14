---
title: A new contributor or agent is productive on this repo without tribal knowledge
type: practice
owner: steward
status: dreamt
---

# A new contributor or agent is productive on this repo without tribal knowledge

## The Dream

Getting productive on this repo today means reading CLAUDE.md, the skill docs, and enough of
this repo's own conventions (pixi environments, the `local-recipes` vs per-station env split,
the BMAD multi-project marker/symlink dance, which `pixi run -e <env> <task>` invocation does
what) to avoid the documented footguns — none of it wrong, all of it currently living only as
prose a new contributor or a freshly-spun agent has to read and internalize by hand, with no
single command that checks "is this machine/checkout actually set up right" or scaffolds the
parts that are mechanical rather than judgment calls. `steward init`/`setup`/`doctor`-adjacent
tooling would make the mechanical parts of onboarding a command instead of a reading assignment
— shell/PATH setup where relevant, a repo-state self-check, and a scaffold for anything a fresh
clone or a new sibling repo needs before its own tooling works. Framed as a `practice`, not a
`dream`: onboarding never reaches a terminal "done" the way a feature does — it degrades every
time the toolchain changes and has to be re-exercised, the same shape [[packaging-factory]]
already carries in this repo.

## What it looks like when real

- A single command an operator (or a freshly-spun agent session) can run to confirm the checkout
  is in a working state — pixi environments resolvable, the BMAD marker/symlinks agree with the
  current project (composing with [[bmad-switch-scope-enforcement]] once it exists), no dangling
  worktree cruft — rather than discovering a gap mid-task. Emits `--json` for the same reason
  every other check in this repo does (`fleet-picture --json`, every detector's `--json`): a
  self-check that only prints prose can't be composed into a preflight another tool calls.
- Whatever shell/PATH setup this repo's own tooling benefits from (if any is found to be
  needed — see "What is real" below) is a single idempotent, delimiter-bounded write, not a
  hand-edited rc file.
- A scaffolding step for onboarding a NEW sibling repo into this repo's own conventions, if that
  pattern recurs (this repo already has at least one sibling project referenced in prior work,
  `conda-forge-tracker`) — capturing whatever's mechanical about wiring a new repo in.

## What is real

Nothing built yet, and unlike [[bmad-switch-scope-enforcement]] and
[[scratch-worktree-lifecycle]], this Dream has no specific already-bitten incident behind it —
no local getting-started doc exists, and no `init`/`shell-init`/`bootstrap`-shaped tooling exists
in `pyforge-steward` today (checked directly: the package has no module by that name). This is
the most purely aspirational of the three Dreams captured in this batch — a real, plausible gap,
not yet a documented pain point the way DW-1-4-2 or this session's own repeated
`git worktree add` toil are.

A sibling org's `developer-machine-bootstrap` dream (`wf-dev-cli`'s `commands/shell_setup.py`,
`shell_init.py`, `setup.py`, `init_cmd.py`) is considerably larger: managed shell-rc block
injection, a `shell-init` function for env/pixi discovery, a declarative or script-based bootstrap
sequence, and stack-detection scaffolding for Node/Maven/Gradle/Go/Rust/Ruby/.NET repos —
building toward a `pyforge.toml`-equivalent config file that also does not exist in this repo yet.
Most of that surface assumes a multi-language, multi-repo enterprise estate this repo isn't; the
`type: practice` framing and the general "make the mechanical parts of onboarding a command"
shape are what transfer.

## Constraints

- **Never own judgment calls.** A self-check reports what's wrong; it does not silently "fix" a
  developer's deliberate local configuration choice.
- **Idempotent by construction**, matching this repo's own atomic-write conventions (`os.replace`,
  delimiter-bounded rc blocks) rather than append-and-hope.

## Non-goals

- **Not a GUI wizard.** CLI only, matching every other Steward verb.
- **Not stack detection for languages this repo doesn't have.** No Node/Maven/Gradle/Go/Rust/Ruby/.NET
  scaffolding — this repo is Python/pixi, and generalizing beyond that is speculative until a
  second-language need actually appears.
- **Not deciding what belongs in a `pyforge.toml`-equivalent config file** — that decision belongs
  to whichever Dream first needs one ([[scratch-worktree-lifecycle]] does not currently need one,
  scoped to a single mono-repo).

See "Full feature audit" below for the per-feature reasoning behind these and every other
capability the source dream carried that this one doesn't.

## Full feature audit against `developer-machine-bootstrap`

Every capability the sibling org's dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| `steward init` (managed, delimiter-bounded shell rc block) | **Included, hedged** | Kept as a bullet, but not committed to as a concrete verb — no evidence yet that this repo's own tooling actually needs rc-file changes the way a bespoke wrapper might (`pixi run`/`pixi shell` don't require them). A future Spec should confirm the need before building this specific piece. |
| `steward shell-init` (emit a shell function to stdout for `eval`, env/pixi discovery + routing) | **Omitted, not named** (2026-08-14 audit) | A distinct mechanism from `init` — emit-and-eval vs. write-to-rc-file — collapsed into one vague bullet in the first draft. Named here explicitly so a future reader can decide whether it's needed independently of `init`. |
| `steward setup` (declarative/script-based bootstrap sequence, idempotent + resumable) | **Included, hedged** | Kept as "a scaffold for anything a fresh clone... needs," but the sequence-runner design (declarative vs. script mode, resumability) wasn't carried over — only the general shape. |
| `steward initrepo` (stack detection, scaffold `pyforge.toml`) | **Included, narrowed** | Kept as "a scaffolding step for onboarding a new sibling repo," explicitly stripped of multi-language stack detection (see Non-goals). |
| Stack-detection heuristics by marker file | **Omitted, overbroad exclusion** (2026-08-14 audit) | The first draft dismissed the whole marker-file-detection *mechanism* along with the multi-language *scope* it served. A narrower version — "is this a pixi project: does `pixi.toml` exist, does the environment resolve" — is still single-language and plausibly in-scope; it was never called out as a distinct, retained capability. Left as an open question rather than folded in outright, since no concrete need for it has been observed yet (unlike `scratch-worktree-lifecycle`'s `start`/`ls`/`clean`, which map onto directly-observed toil). |
| PowerShell fallback | **Omitted, unverified** | Not mentioned. Defensible on the source's own terms (it treats PowerShell as non-primary too), but this repo has never actually confirmed whether any contributor works on Windows — an assumption, not a checked fact. |
| `argcomplete` tab completion | **Omitted, unverified** | Same repo-wide gap noted in [[scratch-worktree-lifecycle]]'s audit — no PyForge CLI currently registers tab completion; adding it here would set a precedent this one Dream shouldn't decide alone. |

## Kinships

[[pyforge-steward]] (the estate; this Dream's natural home per the same developer-ergonomics
identity as [[scratch-worktree-lifecycle]]) · [[packaging-factory]] (the existing `practice`-type
precedent this Dream's frontmatter follows) · [[scratch-worktree-lifecycle]] (a sibling capability
captured in the same investigation, not directly dependent on this one)

## Realization log

- **2026-08-14** — Dream captured, alongside [[scratch-worktree-lifecycle]] and
  [[bmad-switch-scope-enforcement]], while evaluating a sibling org's dream catalog for PyForge
  fit. Deliberately flagged as the least evidence-backed of the three: no local incident, no
  existing partial tooling, no documented pain point — captured because the gap is plausible and
  the sibling org's shape is a reasonable starting blueprint, not because anything has been bitten
  by its absence yet. Ownership assigned to Steward, matching the source dream's own label and
  steward's established developer-ergonomics identity, with no competing claim found from any
  other station.

- **2026-08-14 (same day)** — Feature-parity audit against the source dream: JSON output added to
  the self-check bullet; `shell-init` and marker-file stack detection named explicitly (they were
  present only implicitly, folded into vaguer bullets, in the first draft). Every source feature
  now carries an explicit disposition in "Full feature audit" rather than living only in a
  conversation transcript.
