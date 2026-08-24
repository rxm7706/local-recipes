---
title: 'One build, whole Guild — a single Containerfile builds one image with all eight station CLIs'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/_bmad-output/implementation-artifacts/epic-7-context.md']
warnings: ['oversized']
baseline_revision: '9850f743cc63bc60ea40e3db698a6f3069e8eaf5'
final_revision: '4761c7dc92e5701b73af9ea5155acf229426dcfd'
---

<intent-contract>

## Intent

**Problem:** The factory's eight station CLIs (`marshal`, `steward`, `pyforge-atlas`, `warden`, `doctor`, `mason`, `herald`, `scribe`) only run from a bare-metal checkout with per-station pixi environments — there is no single deployable image for the whole Guild, and two of the eight CLIs (`pyforge-atlas`, `scribe`) do not implement `--version` at all today (verified live: both exit 2 with "no such option").

**Approach:** Compose one lean `pyforge-container` pixi environment from the eight existing `pyforge-*` features (same `no-default-feature` composition pattern already proven by `pyforge-ci`), add a multi-stage `Containerfile` that materializes that environment in a pixi builder stage and copies the full repo checkout plus the materialized environment into a minimal runtime stage (`marshal` as the default command), and add the two missing `--version` flags so the epic's AC is literally true.

## Boundaries & Constraints

**Always:**
- Compose `pyforge-container` from the eight existing `pyforge-*` pixi features verbatim (`no-default-feature = true`), mirroring the `pyforge-ci` precedent — no new dependency curation or splitting of existing features.
- Ship the full repo checkout in the image, not just installed wheels: every duty module locates the repo root via marker-file walk-up, and `steward/keys.py` imports CFE's `_http.py` from the checkout at import time.
- Multi-stage build following pixi's documented container pattern: a `ghcr.io/prefix-dev/pixi` builder stage runs `pixi install --frozen -e pyforge-container` and `pixi shell-hook`; the runtime stage copies the checkout + materialized env and does not itself carry the pixi binary.
- Default `CMD` is `marshal`; every station CLI stays reachable by overriding the run command (e.g. `docker run <image> steward --version`).
- Fix `pyforge-atlas` and `scribe`'s missing `--version` by mirroring the exact idiom the other six stations already use (argparse/click `action="version"` equivalent, Typer eager callback) — no other behavior change to either CLI.

**Block If:** none — see Design Notes for why the Marshal-research "sequence after the pyforge-core consolidation decision" note is not treated as a hard blocker here.

**Never:**
- Do not bake `local-recipes` or any packaging-tier tooling (CFE, rattler-build, conda-smithy) into this image — out of scope per the epic's Non-goals.
- Do not implement marshal-mediated dispatch to sibling station CLIs (e.g. `marshal steward ...`) — not required by this story's AC.
- Do not implement the credential secret-scan build gate, volume-mounted durable state, or the build-time smoke-gate script — those are Stories 7.3/7.4/7.5.
- Do not restructure any station's own subprocess-guard/atomic-write/verdict-lattice code (the separate, unbuilt `pyforge-core` consolidation) — every station's code is consumed as-is.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Image build | `docker build -f Containerfile -t pyforge-guild .` from repo root | Build completes successfully | Build fails loudly if `pixi install` fails — no silently partial image |
| Default run | `docker run --rm pyforge-guild` | Runs `marshal` with no args (its own bare-invocation behavior) | N/A |
| Per-station version check | `docker run --rm pyforge-guild <cli> --version` for each of the 8 CLIs | Each prints a version string, exit 0 | N/A |
| Atlas/scribe version, pre-fix baseline | `pyforge-atlas --version` / `scribe --version` today | Currently exit 2, "no such option" | This story adds the flag to both |

</intent-contract>

## Code Map

- `pixi.toml` -- add `[environments] pyforge-container` composed from the eight `pyforge-*` features, `no-default-feature = true` -- the lean multi-station env the image installs
- `Containerfile` (repo root, new) -- multi-stage: pixi builder stage materializes `pyforge-container`; runtime stage copies checkout + env, `ENTRYPOINT` sources the shell-hook then execs its args, default `CMD ["marshal"]`
- `.dockerignore` (repo root, new) -- excludes `.git/`, `.pixi/`, `_bmad-output/implementation-artifacts/`, and other heavy/irrelevant paths from the build context so `COPY . /pyforge` stays sane
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py` -- the only station CLI with zero `--version` support today
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` -- Typer app has no `--version` option today

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py` -- intercept `--version` in `main()` before `configure_project`/`find_run_command` runs, print `pyforge-atlas {__version__}`, return before Kedro dispatch -- gives atlas's CLI the same `--version` contract every other station already has, without touching Kedro's own command routing
- [x] `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` -- add an `@app.callback()` on `app` with an eager `--version` option that echoes `pyforge.scribe.__version__` and exits -- standard Typer idiom, mirrors warden/doctor/mason/herald
- [x] `pixi.toml` -- add the `pyforge-container` environment entry (features = the eight `pyforge-*` features, `no-default-feature = true`), placed alongside the other `pyforge-*` env entries in `[environments]`
- [x] `.dockerignore` -- exclude `.git/`, `.pixi/`, `_bmad-output/implementation-artifacts/`, `archive/`, and other build-irrelevant paths
- [x] `Containerfile` -- builder stage `FROM ghcr.io/prefix-dev/pixi:0.76.1` (matches `feature.python`'s `pixi >=0.76.2` floor; bump if that floor moves), `COPY . /pyforge`, `WORKDIR /pyforge`, `RUN pixi install --frozen -e pyforge-container` + `pixi shell-hook -e pyforge-container -s bash > /shell-hook.sh`; runtime stage on a minimal base (`ubuntu:24.04`), `COPY --from=builder /pyforge /pyforge`, `WORKDIR /pyforge`, an entrypoint script that sources `/shell-hook.sh` then `exec "$@"`, `CMD ["marshal"]`

**Acceptance Criteria:**
- Given the Containerfile, when `docker build -f Containerfile -t pyforge-guild .` runs from the repo root, then it completes successfully.
- Given the built image, when each of the eight station CLIs is invoked with `--version` via `docker run --rm pyforge-guild <cli> --version`, then each prints a version string and exits 0.
- Given the built image, when run with no command override, then `marshal` runs as the default command.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 2, medium 3, low 2)
- defer: 3: (high 0, medium 2, low 1)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[high]` `[patch]` `.dockerignore` didn't exclude `.env`/`.env.github`/`.secrets`/`.claude/settings.local.json`/`.claude/data/` — `COPY . /pyforge` would bake locally-present credentials/mutable runtime cache into a shareable image layer. Added the exclusions.
  - `[high]` `[patch]` Neither `FROM` stage pinned `--platform`; the workspace's `pixi.toml` declares no `linux-aarch64`, so building on an arm64 Docker host would fail `pixi install --frozen` outright. Pinned `--platform=linux/amd64` on both stages.
  - `[medium]` `[patch]` `.dockerignore` didn't exclude `presentations/` (~659MB, Herald deck output, irrelevant to any station CLI) — baked into the final image unnecessarily. Added the exclusion.
  - `[medium]` `[patch]` Atlas's `--version` intercept did an unscoped `"--version" in cli_args` membership check, diverging from marshal's documented "root-only, wins before anything else claims parsing" convention (`pyforge-atlas run --version` would have silently short-circuited to print-version instead of a normal Kedro usage path). Scoped the check to `cli_args[0] == "--version"`.
  - `[medium]` `[patch]` No regression test coverage existed for either `--version` addition. Added `test_version_flag_prints_version_and_exits_0` to `pyforge-scribe/tests/unit/test_cli.py` and a new `pyforge-atlas/tests/test_main_version.py` (3 tests incl. the position-scoping fix); all pass.
  - `[low]` `[patch]` Containerfile's usage comment implied uniform short CLI names (`docker run <image> steward --version`) without noting atlas's console-script is `pyforge-atlas`, not `atlas`. Comment corrected.
  - `[low]` `[patch]` `pixi.toml`'s `requires-pixi` comment enumerates every pixi-version pin location ("keep all five in step") but didn't list the new Containerfile pin. Updated to six and added the Containerfile reference.
  - `[medium]` `[defer]` `pyforge-container` inherits atlas's test-only/GUI tooling (`kedro-viz`, `playwright`) because no `pyforge-*` feature separates runtime from test-only deps — pre-existing across all 8 stations, not this story's to fix. Logged to deferred-work.md.
  - `[medium]` `[defer]` Runtime image has no `USER` directive, runs as root — real hardening gap, not named in any planning artifact, non-trivial to patch safely (ownership/HOME handling) without a full re-verify; Story 7.3 owns container security hardening. Logged to deferred-work.md.
  - `[low]` `[defer]` Version-resolution inconsistency (dynamic `importlib.metadata` in steward/mason vs. hardcoded literal in atlas/scribe/warden/herald/doctor) — pre-existing since each station's own Story 1.1, this story only consumes existing `__version__` values. Logged to deferred-work.md.
  - `[low]` `[reject]` "entrypoint.sh's `set -e` silently kills the entrypoint with no diagnostic" — `set -e` under bash is fail-fast by design and prints the failing command; not a defect.
  - `[low]` `[reject]` "Multi-stage rationale oversells its own savings" — the comment's "no pixi binary in the final image" claim is independently verified true (`which pixi` exits 1); this is a tone nitpick on an accurate comment.
  - `[low]` `[reject]` "Nothing in the diff proves the AC in CI" — an automated build-time smoke gate is explicitly Story 7.5's scope (declared out of 7.1's Never clause); the AC was independently verified by hand (`docker build` + per-CLI `--version` loop, all 8 exit 0).

### 2026-08-09 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 4, medium 2, low 3)
- defer: 6: (high 1, medium 4, low 1)
- reject: 9: (high 0, medium 2, low 7)
- addressed_findings:
  - `[high]` `[patch]` `pyforge-atlas --version` emitted **nine** stdout lines, eight of them the build host's wrapped absolute checkout path, not the one clean version line every other station prints. Importing `kedro.framework.project` installs Kedro's rich logging config at import time, and that import sat at module scope — so it fired before the intercept could run, making the comment's "before `configure_project`/`find_run_command` run" untrue in practice. Moved both Kedro imports inside `main()`, below the intercept. Verified in the real image: 9 lines → 1, rc 0, no path leak.
  - `[high]` `[patch]` `.dockerignore`'s depth-agnostic patterns were written in `.gitignore` syntax, but Docker matches each pattern against the whole context-relative path — so bare `__pycache__/`, `*.log`, `*.egg-info/`, `.pytest_cache/`, `node_modules/`, `build/`, `dist/` etc. only ever matched at the root. 67 nested `__pycache__` dirs under `src/**` were riding into the image. Added `**/` prefixes; verified in-image 67 → 0.
  - `[high]` `[patch]` `_bmad-output/implementation-artifacts` is only a **symlink**, so that exclusion was a no-op against the real Tier-3 trees under `_bmad-output/projects/*/implementation-artifacts` (run state, transcripts, patches, logs for every station that has run locally). Added the physical pattern; verified 0 in-image.
  - `[high]` `[patch]` `.dockerignore` missed three secret-shaped roots its own comment implied it covered: `.steward/` (keys-inventory.yaml carries identity_path pointers, provenance and rotation history; budget.yaml the spend ceilings) plus `.private` and `SDKs/`, both already gitignored as secret-shaped. Added all three.
  - `[medium]` `[patch]` This story's 20th pixi env left `bmad-drift-check` **red** (`[surface-changed] pixi_envs: 19 → 20`) with six `[count-stale]` findings across pyforge-marshal's `index.md`, `architecture.md`, `architecture-bmad-infra.md`, `integration-architecture.md`, `deployment-guide.md` and `project-overview.md` — CLAUDE.md's always-on sync rule was unmet. Updated all six (correcting the product-env enumerations, which were stale well past this story at 6 of 11) and re-stamped the baseline; detector now `OK`.
  - `[medium]` `[patch]` `.dockerignore`'s `presentations/` comment claimed the tree is "irrelevant to any station CLI" and that "no marker-file walk-up ever looks here" — false: herald's whole deck duty is rooted there (`deck_pipeline.py`: `repo_root / "presentations" / slug`). The exclusion still stands on size (84MB), but `herald deck` is host-only in this image; the comment now says so instead of asserting the opposite.
  - `[low]` `[patch]` `pixi.toml`'s `requires-pixi` comment said "keep all **six** in step" — there are seven (`.github/workflows/kedro-viz-publish.yml:69` was unlisted) and they do not match (feature pins + environment.yaml at 0.76.1; this floor and both workflow pins at 0.75.0). Comment corrected to enumerate seven and state the real, unequal values; the mismatch itself deferred.
  - `[low]` `[patch]` Atlas's `--version` intercept read only positional args while the dispatch immediately below it forwards `**kwargs` to Click — so Click's own `main(args=[...])` keyword form silently bypassed the flag. Intercept now resolves positional → `kwargs["args"]` → `sys.argv[1:]`, matching the dispatch.
  - `[low]` `[patch]` Test coverage could not catch its own subject. The three `capsys` tests stayed green while the shipped CLI was emitting nine lines, because Kedro's banner fires at collection, outside `capsys`'s window; and `test_version_not_first_token_does_not_short_circuit` asserted a bare `SystemExit` that any failure would satisfy. Added a subprocess test asserting exactly one stdout line, a keyword-form test, and pinned the position-scoping test to Click's exit 2. 3 tests → 5, all pass.
  - `[high]` `[defer]` Image ships no `git`/`gh`/`pixi`/`tmux`, so marshal's git-worktree orchestration and steward's `provision`/`deploy build` cannot run in-container. Barred from patching here by the Always clause ("compose the eight features verbatim, no new dependency curation"); named explicitly in a new `Containerfile` SCOPE block and logged to deferred-work.md.
  - `[medium]` `[defer]` Seven pixi-version pin sites disagree (0.75.0 vs 0.76.1) with no detector enforcing them — pre-existing since the 2026-07-30 `pixi update`. Logged to deferred-work.md.
  - `[medium]` `[defer]` Neither base image is digest-pinned (`ubuntu:24.04`, `ghcr.io/prefix-dev/pixi:0.76.1` are mutable tags), so the OS layer can change under a `--frozen` conda layer. Story 7.3's hardening scope. Logged to deferred-work.md.
  - `[medium]` `[defer]` Station CLI runs as PID 1 with no init and no SIGTERM handler, so `docker stop` stalls to SIGKILL. Story 7.3's scope. Logged to deferred-work.md.
  - `[medium]` `[defer]` The composed env re-solves the graph and ships versions no suite exercises (verified: dagster 1.13.16 in `pyforge-atlas` vs 1.13.17 in `pyforge-container`); no `pyforge-container` test/smoke task exists. Story 7.5's scope. Logged to deferred-work.md.
  - `[low]` `[defer]` `COPY . /pyforge` immediately before `pixi install` discards all build-cache reuse, contradicting the header's claim to follow pixi's documented pattern (which splits the copy). Logged to deferred-work.md.
  - `[medium]` `[reject]` "No `USER` directive, runs as root" and "non-root/OpenShift random-UID ownership" — already logged to deferred-work.md by the prior pass; re-logging would duplicate a live entry.
  - `[medium]` `[reject]` "Nothing proves the AC in CI / no automated Containerfile coverage" — the prior pass rejected this on the same grounds and they still hold: an automated build-time smoke gate is Story 7.5's declared scope, and all three ACs were re-verified by hand this pass.
  - `[low]` `[reject]` "Add `__version__`-vs-`pyproject.toml` drift tripwires to the new tests" — that is the already-deferred version-resolution inconsistency's work, not new coverage this story owes.
  - `[low]` `[reject]` "`main("--version")` as a bare string mis-parses per-character" — no such caller exists; Click mishandles a bare string identically before and after this change.
  - `[low]` `[reject]` "shell-hook bakes a literal PATH, so `docker run -e PATH` is discarded" — that is `pixi shell-hook`'s documented behavior working as designed; overriding PATH at run time is a non-scenario for this image.
  - `[low]` `[reject]` "Empty `CMD` override (`command: []`) exits 0 silently" — standard shell behavior when the operator explicitly asks for no command; not a defect.
  - `[low]` `[reject]` "Editable `.pth` files hard-code `/pyforge`, so runtime WORKDIR must match" — true but both stages pin `/pyforge`; no defect today, and the fixed-path contract is Story 7.2's scope.
  - `[low]` `[reject]` "Excluding `presentations/` breaks herald's deck duty" — the exclusion is correct on size; only the comment's justification was wrong, and that was patched.
  - `[low]` `[reject]` "Containerfile comments carry rationale that lives nowhere else" — comment placement is the right home for build-file rationale; the SCOPE-block patch strengthened it.

### 2026-08-09 — Review pass (third)
- intent_gap: 0
- bad_spec: 0
- patch: 13: (high 3, medium 5, low 5)
- defer: 2: (high 0, medium 2, low 0)
- reject: 11: (high 0, medium 3, low 8)
- addressed_findings:
  - `[high]` `[patch]` `.dockerignore`'s `.pixi/` swallowed **`.pixi/config.toml`, which is git-tracked** and carries `run-post-link-scripts = "insecure"` — so the image's `pixi install` ran with post-link scripts DISABLED while every host install runs them. Proven rather than argued: `loaders.cache` appears in no conda package's `paths.json` (it is generated by `.gdk-pixbuf-post-link.sh`), and `pyforge-container` ships gdk-pixbuf, gtk3, librsvg and graphviz. Rewritten as `.pixi/*` + `!.pixi/config.toml` (so Docker drops each child wholesale instead of walking the multi-GB env) plus `recipes/*/.pixi/` and `src/**/.pixi/` for the nested workspaces. Verified in the rebuilt image: `/pyforge/.pixi/config.toml` present, `…/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache` now present.
  - `[high]` `[patch]` `**/*.log` swallowed `.claude/skills/conda-forge-expert/tests/fixtures/error_logs/unmatched.log` — the repo's **only** tracked `.log`. Its absence recreates the exact false-green `.gitignore` was patched to fix earlier the same day (2026-08-09, doctor 6.7): `test_failure_analyzer.py`'s two unmatched-log cases assert "Log file not found" instead of the no-match contract. Negated narrowly, mirroring `.gitignore`'s own fix rather than weakening `*.log`. Verified present in-image.
  - `[high]` `[patch]` No `.bmad-loop/` exclusion. A loop home is itself a full repo checkout — this story was developed in one — so `docker build .` from a loop home ships every run's transcripts, patches and logs: **11GB** in the steward home, and agent transcripts are exactly the kind of thing that carries a pasted credential. Added, mirroring `.gitignore`'s four `.bmad-loop/*` entries.
  - `[medium]` `[patch]` Six gitignored secret-/host-state-shaped roots the new secrets block implied it covered were missing: `/.herald/` (AD-5's repo-local bridge/etag store — the exact analogue of the `.steward/` entry the prior pass added), `.claude/skills/data/`, and the build-host BMAD identity set (`_bmad/custom/.active-project`, `_bmad/config.user.toml`, `_bmad/_memory/`, `_bmad-output/planning-artifacts`, `_root-fallback-fork-*`) — baking the last of those in makes two hosts produce two different images from one commit. All added; all verified absent in-image.
  - `[medium]` `[patch]` The header's claim that un-`**/`-prefixed entries "are deliberately root-anchored because that is the only place they exist" was **false**, and it is the load-bearing justification for every such line: `recipes/.idea/` is tracked (10 files) and shipped, and `recipes/insightforge/pixi.toml` is a nested pixi workspace whose `.pixi/` the root-anchored rule misses. Widened `.idea/`/`.vscode/`/`.junie/` to `**/`; header rewritten to state what was actually verified and to name tracked-file swallowing as the hazard, with the audit command.
  - `[low]` `[patch]` The at-any-depth sweep the prior pass started stopped short of `.mypy_cache/`, `.ruff_cache/`, `.hypothesis/`, `htmlcov/`, `.coverage`, `.venv/` (every tool installed by this workspace's own features) and of the conda-factory leavings a checkout that has run a local build carries (`conda-bld/`, `miniforge3/`, `*.conda`, `*.tar.bz2` — none tracked). Added.
  - `[medium]` `[patch]` `Containerfile`'s `--frozen` comment claimed it "fail[s] loudly on a stale pixi.lock rather than silently re-solving". Per `pixi install --help` it does the **opposite** — `--frozen` "doesn't update lock file if it isn't up-to-date with the manifest" (silent), and `--locked` is the flag that aborts. The flag is KEPT (`--frozen` is this repo's convention at every call site, per its own recorded decision not to rewrite call sites to `--locked`); the comment now states what it really guarantees and whose job keeping the lock current remains.
  - `[medium]` `[patch]` Nothing documented that **every** invocation must go through the entrypoint: the station CLIs are on PATH only because `/entrypoint.sh` sources the shell-hook, so `docker exec <ctr> marshal` and `docker run --entrypoint marshal` fail "executable file not found". Deliberately NOT papered over with a baked `ENV PATH` — that would resolve the binary while still missing the activation env (SSL_CERT_FILE, GDK_PIXBUF_MODULE_FILE, …), trading a loud failure for a quiet one. Documented, with `docker exec <ctr> /entrypoint.sh marshal …` as the working form.
  - `[low]` `[patch]` The header documented `docker run` usage but never the build command, and `-f` is not optional: BuildKit only auto-detects the name `Dockerfile`, so `docker build -t x .` fails outright. Added, noting podman/buildah accept `Containerfile` unflagged.
  - `[medium]` `[patch]` The scribe memlog — a durable, contract-hash-bearing tracked artifact — asserted a fleet precedent that does not exist: "the standard Typer idiom already used by warden/doctor/mason/herald". None of them use Typer; warden/doctor/mason/herald/steward all use argparse `action="version"` and marshal a custom `argparse.Action`. Scribe is the fleet's **only** Typer CLI. Corrected to say the CONTRACT is what is mirrored, not the mechanism, with an explicit "do not cite this as a Typer precedent".
  - `[low]` `[patch]` `pixi.toml`'s `requires-pixi` comment (rewritten by the prior pass) was still wrong twice: it said SEVEN pin sites when there are EIGHT — the `"$schema"` URL two lines above it also pins `v0.75.0` — and called all three workflow pins EXACT when `staged-recipes-linter.yml`'s is a floor (`pixi>=0.76.2`). Corrected, with each site labelled floor-vs-exact.
  - `[low]` `[patch]` Atlas's `--version` arg resolution disagreed with itself about `None`: the keyword branch tested `is not None`, the positional branch tested truthiness, so `main(None)` — Click's documented "read `sys.argv`" shape — produced a non-empty `(None,)`, resolved `cli_args` to `None` and silently skipped the intercept, while `main(args=None)` honored it. Both branches now test `is not None`; regression test added.
  - `[low]` `[patch]` The subprocess regression test asserted stdout only, so a logging config emitted on **stderr** — the normal destination for a logging handler — would keep it green while `pyforge-atlas --version 2>&1` stayed exactly as polluted as before the deferred-import fix. Now asserts the banner and the checkout path are absent from the combined streams. Atlas version tests 5 → 6, all pass.
  - `[medium]` `[defer]` Nothing keeps `.dockerignore` in step with `.gitignore` — this pass found eight divergences by hand and the next `.gitignore` addition will diverge the same way. The fix is a detector (tracked-file-swallow check + secret-root cross-check), new tooling with its own three-place wiring. Logged to deferred-work.md.
  - `[medium]` `[defer]` `bmad-drift-check`'s count rule matches one literal phrasing (`N pixi envs`) and has no feature-count fingerprint, so 32 stale occurrences ("17 features" ×18, "18 envs"/"18 pixi environments" ×14) sit across nine marshal planning docs while the detector reports OK. Live values are 20 envs / 21 features. Not patched here on purpose: the PRD's own retro records that a partial re-grounding leaves the set "INTERNALLY INCONSISTENT, worse than uniformly stale", and some occurrences are inside `sync_lineage` retro prose that must not be rewritten — this needs a full SYNC-RUNBOOK pass plus a widened detector. Logged to deferred-work.md.
  - `[medium]` `[reject]` "Swap `--frozen` for `--locked` so a stale lock fails the build" — the comment was wrong and was fixed, but the flag is right: `--frozen` is this repo's recorded convention at every call site ("do not go rewriting call sites to `--locked`").
  - `[medium]` `[reject]` "No `USER` directive, runs as root" and `[medium]` `[reject]` "PID 1 with no init, `docker stop` stalls to SIGKILL" — both are already live deferred entries from the prior pass; re-logging would duplicate them.
  - `[low]` `[reject]` "'lean'/'minimal' oversell what the env ships (playwright, kedro-viz, hatchling, pytest)" — `pyforge-container` is genuinely lean relative to the default env, and the substantive bloat is already a live deferred entry.
  - `[low]` `[reject]` "The `--platform=linux/amd64` pin still needs qemu/Rosetta binfmt on an arm64 host" — true of every `--platform` pin; an emulation prerequisite is a Docker-host property, and the comment claims only that the pin fixes the missing-lock-entry failure, which it does.
  - `[low]` `[reject]` "`.sync-baseline.json`'s `git_head` is one commit behind HEAD" — inherent to stamp-then-commit ordering, the field is not fingerprinted, and both detectors report OK.
  - `[low]` `[reject]` "`docker run --entrypoint /entrypoint.sh <img>` with no CMD exits 0 silently" — standard behavior when the operator explicitly asks for no command; the prior pass rejected the sibling finding on the same grounds.
  - `[low]` `[reject]` "Stripping Tier-3 makes deploy/journal readers report 'no evidence'" — the exclusion IS the prior pass's leak fix, and reporting no evidence when none is present is correct.
  - `[low]` `[reject]` "Add `**/conf/**/*credentials*`" — no such file exists tracked or by convention here; `conf/` holds only `base/`.
  - `[low]` `[reject]` "Give scribe's `--version` a subprocess test like atlas's" — the import-time-banner class that test guards does not exist for Typer, and scribe has no `__main__.py` to invoke.
  - `[low]` `[reject]` "Add `__version__`-vs-`pyproject.toml` drift tripwires" — that is the already-deferred version-resolution entry's work; the prior pass rejected it on the same grounds.

### 2026-08-09 — Review pass (fourth)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 1, medium 4, low 2)
- defer: 2: (medium 1, low 1)
- reject: 1: (high 0, medium 0, low 1)
- addressed_findings:
  - `[high]` `[patch]` `.dockerignore`'s secrets block had **no `conf/` rule**, so `src/shared/packages/pyforge-atlas/conf/local/credentials.yml` was **baked into the image** — verified present at 436 bytes in the built image, the only secret-shaped untracked file that got in. It is Kedro's canonical local-credentials path, auto-generated by atlas's `tests/orchestration/conftest.py` on any checkout that has run its orchestration gates, carrying keys `bigquery_adc`/`github_token` and the instruction "Replace with real values for live runs" — so today's stub is one maintainer-follows-the-instruction away from a real token in a shareable layer. Atlas's own `.gitignore` declares the path secret **twice** (`conf/local/**`, `conf/**/*credentials*`). The third pass **rejected** adding a counterpart on the premise "no such file exists tracked or by convention here; `conf/` holds only `base/`" — both halves refuted: there are three `conf/` trees and two carry a `local/`. Added `**/conf/local/*` + `!**/conf/local/.gitkeep` (both `.gitkeep`s are tracked) + `**/conf/**/*credentials*`. Verified: gone from the image, both `.gitkeep`s and all of `conf/base/` survive.
  - `[medium]` `[patch]` `entrypoint.sh` ended in `exec "$@"`, so bash parsed a **leading-dash first argument as its own option**. Two live consequences at a `CMD ["marshal"]` image: `docker run <image> --version` died with `exec: --: invalid option` (rc 2 — a message about bash, not about the image), and `docker run <image> -c /usr/bin/env` **silently ran the command in a sub-shell with an empty environment at rc 0** — precisely the quiet failure the Containerfile header says it refuses to trade a loud one for. Changed to `exec -- "$@"`; both now return honest `exec: <arg>: not found` at rc 127, and normal invocation is unaffected (all 8 CLIs re-verified).
  - `[medium]` `[patch]` The blanket `.bmad-loop/` rule the third pass added **swallowed the git-tracked `.bmad-loop/bmad_loop_hook.py`** (verified absent from the image) — the only unintended tracked-file swallow in the build. Its comment claimed to "mirror `.gitignore`'s four `.bmad-loop/*` entries", but those four (`runs/`, `cache/`, `policy.toml`, `skill-projection.json`) are narrow **precisely so the hook stays tracked**; the blanket rule is a strict superset. This is the file's own named hazard, and its own audit instruction was not run on the rule that introduced it. Added the negation, corrected the comment.
  - `[medium]` `[patch]` `Containerfile`'s entrypoint rationale — the load-bearing argument for deliberately not baking `ENV PATH` — named `SSL_CERT_FILE`, `GDK_PIXBUF_MODULE_FILE` and `FONTCONFIG_FILE` as what the shell-hook sets. **All three are empty in the real image** and no `activate.d` script in the env sets any of them (the env's three are `libarrow`, `libglib`, `libxml2-split`, contributing `GSETTINGS_SCHEMA_DIR` and `XML_CATALOG_FILES`). An operator reading it would believe bypassing the entrypoint costs TLS trust, which is false. The decision stands; the comment now names what the hook genuinely contributes and records that the earlier evidence was wrong.
  - `[medium]` `[patch]` `pixi.toml`'s `requires-pixi` comment — rewritten by each of the three prior passes (five → six → seven → eight) — was still wrong: there are **NINE** pin sites. `.github/actions/sync-pypi-mappings/action.yml:44` pins **EXACT `v0.73.0`**, and its own adjacent comment says to keep it in step with this key. That makes it a **fourth** EXACT site and the only one currently **below** the `>=0.75.0` floor — the exact condition the comment warns about. Corrected, with the live consequence named. (The version mismatch itself remains the existing deferred entry; not re-logged.)
  - `[low]` `[patch]` `**/data.locks/` was missing: ~90 gitignored atlas run-admission lock/holder files, each recording a build-host pid and run id, rode into any image built while atlas's tests were running (verified: absent from the pass-3 image, present in the pass-4 pre-patch image). Functionally harmless by luck rather than design — exclusion is a live `flock` no image can carry, and a dead holder is reclaimed — but the same doctrine already applied to `.claude/data/` says the image must not be a function of what happened to be running on the build host. Added.
  - `[low]` `[patch]` `Containerfile`'s SCOPE block said `herald deck` is host-only without noting that **half of it is host-only quietly**: `seed` raises a `HeraldError`, but `status` returns `[]` at rc 0. Sharpened, with an explicit "do not read `[]` from this image as 'the Guild has no decks'". (Herald's own code is out of scope here — deferred.)
  - `[medium]` `[defer]` `herald deck status` returns an empty list at exit 0 when `presentations/` is absent, inverting the guarantee its own docstring states — `_known_slugs()` guards on `presentations_dir.is_dir()`. Station-owned code, barred by this story's Never clause. Logged to deferred-work.md.
  - `[low]` `[defer]` `spec_surface_check.py` validates only tracked-files-into-surface, never surface-entries-out, so `spec-unified-container`'s `surface:` has named the nonexistent `scripts/container-gates` since before this story with the detector reporting OK. Pre-existing; detector work. Logged to deferred-work.md.
  - `[low]` `[reject]` "`PIXI_EXE=/usr/local/bin/pixi` is exported pointing at a path absent from the runtime stage" — true and verified, but it is `pixi shell-hook`'s documented output working as designed in exactly the multi-stage pattern this story is required to follow, no in-repo consumer reads it, and the prior pass rejected the sibling finding ("shell-hook bakes a literal PATH") on the same grounds.

## Design Notes

- **`--version` gap is pre-existing, not container-introduced.** Verified live: `pyforge-atlas --version` and `scribe --version` both exit 2 today. FR-22's AC is literal, so this story closes the gap with the same idiom the other six stations already use, rather than narrowing the AC.
- **Why `/pyforge`, not a placeholder deferred to Story 7.2.** 7.2's cross-story note frames "fixed path" as a property layered onto 7.1's output, but no artifact names any candidate path besides `/pyforge`. This story adopts it directly; 7.2's own scope is documenting/hardening the ~173-byte length-panic rationale, not picking a different path.
- **Why the pending `pyforge-core` consolidation is not a Block If.** Marshal's research suggests sequencing after its § 7 consolidation decision, but the PRD, `epics.md` ("Deps: Epic 6" only), and `sprint-status-ledger.yaml` (`epic-7: backlog`, unlike blocked `epic-8`) all agree Epic 7 needs only Epic 6, and this epic's Non-goals already say station code is "consumed as-is." A later `pyforge-core` rebuild supersedes this image normally.
- **Follows pixi's own documented container pattern**: `ghcr.io/prefix-dev/pixi` builder → `pixi install --frozen` → `pixi shell-hook` → copy `.pixi` + shell-hook into a bare final stage, no pixi binary in production — not a bespoke build shape.

## Verification

**Commands:**
- `pixi install -e pyforge-container --frozen` -- expected: resolves and materializes without solver errors (sanity-check the new environment definition before wrapping it in a build)
- `docker build -f Containerfile -t pyforge-guild-test .` -- expected: exits 0
- `for cli in marshal steward pyforge-atlas warden doctor mason herald scribe; do docker run --rm pyforge-guild-test "$cli" --version || echo "FAIL: $cli"; done` -- expected: every line prints a version string, no `FAIL` lines
- `docker run --rm pyforge-guild-test` -- expected: runs `marshal`'s own no-args behavior (usage line, exit 0)

## Auto Run Result

Status: done — fourth review pass (follow-up on a `done` spec; `review_loop_iteration` reset to 0).

**Change implemented (this pass).** No intent_gap and no bad_spec, so the intent contract and the
implementation shape were untouched. Seven review-driven patches landed: one real security fix, one
runtime behavior fix, two build-context fidelity fixes, and four comment corrections.

**Files changed**
- `.dockerignore` — added `**/conf/local/*` + `!**/conf/local/.gitkeep` + `**/conf/**/*credentials*` (the credential leak), `!.bmad-loop/bmad_loop_hook.py` (tracked-file swallow), `**/data.locks/` (build-host run state); header rewritten for the now-four negations plus a new paragraph on why untracked secret-shaped files are the half a tracked-file audit cannot see.
- `Containerfile` — `exec "$@"` → `exec -- "$@"`; entrypoint rationale re-evidenced; SCOPE block sharpened on herald's quiet-vs-loud split.
- `pixi.toml` — `requires-pixi` pin-site enumeration eight → nine, naming `sync-pypi-mappings`' exact `v0.73.0` below the floor.
- `.../spec-unified-container/.memlog.md` — surface reconcile entry for this pass.
- `scripts/.spec-surface-baseline.json` — re-stamped, scoped to `pyforge-steward/spec-unified-container` only.

**Review findings breakdown.** 7 patched (high 1, medium 4, low 2) · 2 deferred (medium 1, low 1) · 1 rejected (low 1). Both reviewers independently found the credentials leak, the `.bmad-loop/` swallow and the false activation-var claim; the `exec --` defect came from the Edge Case Hunter, the ninth pin site and the herald `status` behavior from the Blind Hunter. Every finding was re-verified against the repo and the real image before triage — the high finding reverses a premise the third pass had rejected.

**Verification performed**
- `docker build -f Containerfile -t pyforge-guild-final .` → rc 0.
- All 8 station CLIs `--version` in-image → rc 0 each; `pyforge-atlas --version` is exactly one clean line.
- Bare `docker run` → `marshal` usage, rc 0.
- Fix-specific: `credentials.yml` absent while both `conf/local/.gitkeep`s and all of `conf/base/` survive; `bmad_loop_hook.py` present while `runs/`/`cache/` are gone; `docker run <img> --version` and `-c /usr/bin/env` both now rc 127 with an honest not-found instead of rc 2 bash-option / silent rc 0.
- **Bidirectional context audit, clean for the first time:** zero untracked files in the image outside `.pixi/`; zero tracked files swallowed beyond the deliberate `archive/` / `presentations/` / IDE sets.
- `environment.yaml` re-exported byte-identical (the ungated CI sync gate); `spec_surface_check.py` OK; `bmad_drift_check.py` OK (2 pre-existing informational `pin-behind` snapshots).
- `pytest` — atlas `test_main_version.py` 6 passed; scribe `test_cli.py` 17 passed. No Python changed this pass.

**Residual risks**
- The `exec -- "$@"` change alters argument handling on every path into the image. Normal invocation is re-verified across all eight CLIs, but any caller that relied on bash consuming a leading-dash argument would now see rc 127 — that reliance was the defect, so the change is intended.
- The image is still unexercised by any automated gate (Story 7.5) and unhardened (no `USER`, no digest pins, no init — Story 7.3); all three remain live deferred entries, re-confirmed not re-logged.
- `.dockerignore` and `.gitignore` still drift by hand, which is how the credentials rule came to be missing; the detector that would close it is a live deferred entry.

**Follow-up review recommended: true.** This pass landed a high-severity credential-leak fix and a change to how every container invocation parses its arguments — behavior and security impact, not a handful of localized cosmetic fixes.
