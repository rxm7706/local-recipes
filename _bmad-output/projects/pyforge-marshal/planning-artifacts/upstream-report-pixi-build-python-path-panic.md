# Upstream report (DRAFT — not filed): `pixi-build-python` panics on long build paths

**Status:** written up 2026-07-25, **deliberately not filed** (operator decision). Ready to
submit to `prefix-dev/pixi-build-backends` verbatim if/when we choose to.
**Owner station:** Marshal (the harness this breaks is `bmad-loop`'s verify gate).
**Local mitigation:** shipped — see § Our mitigations.

---

## Title

`pixi-build-python` 0.8.3 panics with a byte-index underflow on long build working directories

## Summary

Any source-package build (`path = { … }` dependency on a workspace member) fails when the build
`workDirectory` path is long enough. The backend exits before producing output; the failure is a
Rust panic, not a diagnostic:

```
× the build backend (pixi-build-python) exited prematurely.
│ Build backend output:
│ thread 'main' (1081876) panicked at crates/pixi_build_backend/src/tools.rs:461:13:
│ end byte index 18446744073709551608 is out of bounds for string of length 260
```

`18446744073709551608` is `usize::MAX - 7`, i.e. an unsigned underflow of `len - 8` (or similar)
where `len` is smaller than the subtrahend — a slice computed from a path/prefix length without a
saturating or checked guard.

## Environment

- `pixi-build-python` **0.8.3** (latest on conda-forge as of 2026-07-25)
- Linux x86-64, `pixi` workspace with `preview = ["pixi-build"]`
- Package layout: workspace member at `src/shared/packages/<name>/` with its own `[package]` +
  `[package.build.backend] name = "pixi-build-python"`, consumed via
  `<name> = { path = "src/shared/packages/<name>" }`

## Reproduction

1. Create a pixi workspace with a `pixi-build-python` source-package member.
2. Check it out at a **short** path — build succeeds.
3. Check the *same* commit out at a **deep** path (we use `git worktree`, which is how we hit it)
   and run any command that solves the environment unfrozen (`pixi run -e <env> <task>`).
4. The backend panics as above.

Measured on our side (controlled experiment, recorded 2026-07-14): the same package **solves at a
149-char root and panics at a 162-char root**. In today's failures the worktree root was 81 chars
but the eventual build `workDirectory` was ~238 — so the trigger correlates with the *full*
working-directory path handed to the backend, not the workspace root alone. The `260` in the panic
message is a string length in that neighbourhood, consistent with the slice being computed against
a path string.

## Impact

Path length is an environmental property, so this is invisible until a CI system, a
`git worktree`, or a nested checkout pushes the path over the line — then **every** build of a
source package fails, with a panic rather than an actionable error. For us it took out the verify
gate of an autonomous build loop across three concurrent lines (worktree paths ~194 chars), and
the failure presented as an unrelated environment fault, costing several dev-session retries
before it was root-caused.

## Suggested fix

Guard the slice in `crates/pixi_build_backend/src/tools.rs:461` — `checked_sub` / `saturating_sub`
or a `get(..)` returning `Option` — and surface a real error (or simply handle the short-string
case) instead of panicking. A regression test with a deliberately long `workDirectory` would pin it.

## Workarounds (all verified by us)

1. **`--frozen`** on any command that would otherwise re-solve — the panic is in the *build/solve*
   path, so a frozen environment never reaches it. *(Caveat: a never-locked environment cannot be
   solved frozen — bootstrap the lock once from a short path.)*
2. **Shorten the path** — keep the workspace root (and any worktree root) short.
3. **`detached-environments = true`** plus a `build_artifacts` symlink — observed to make the exact
   unfrozen command pass 111/111 in our case.

## Related hazard worth mentioning upstream

When an unfrozen re-solve *does* succeed inside a git worktree, it rewrites `pixi.lock` with
**worktree-absolute `file://…` channel paths** for a local channel directory. Those paths are
meaningless outside that worktree, and an automated `git add -A` will happily commit them —
poisoning the lock for every other checkout. A relative or workspace-root-relative encoding of
local channel paths would avoid this.

---

## Our mitigations (shipped 2026-07-25)

| # | Mitigation | Where |
|---|---|---|
| 1 | `[verify]` commands run `--frozen` on every build line | each loop home's `.bmad-loop/policy.toml`; documented in the shared policy comments |
| 2 | Loop homes moved to a **short root** — `~/.bmad-loops/<slug>` instead of `../<repo>-loop-<slug>`; worst-case build `workDirectory` **238 → 192 chars** | `scripts/bmad-loop-worktree` (`BMAD_LOOP_HOME_ROOT` overrides; set it to the repo parent to restore the sibling layout) |
| 3 | New-environment bootstrap: solve the lock once from the main (short) checkout before a loop line runs frozen | procedure, applied for `pyforge-doctor` 1.1 |

**Not applied:** pinning past the bug — **there is nothing to pin to.** Our backend spec is already
`version = "0.*"` (floating), and conda-forge's newest `pixi-build-python` **is** 0.8.3. A fix will
be picked up automatically when one is published.

## Provenance

First characterised 2026-07-14 during pyforge-warden story 1.1 (controlled 149-vs-162 experiment,
recorded in that project's deferred-work ledger). Independently re-hit 2026-07-25 across the
herald, doctor and scribe build lines, where it caused repeated verify-gate failures until
root-caused. This document consolidates both.
