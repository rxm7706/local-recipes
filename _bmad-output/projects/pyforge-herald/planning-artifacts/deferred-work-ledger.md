---
doc_type: deferred-work-ledger
project: pyforge-herald
date: 2026-07-29
status: promoted-verbatim
---

# pyforge-herald — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-29 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown, and this repo has already lost data that way
(pyforge-atlas's live ledger is still truncated to 11 of 64 entries, collateral of the
2026-07-19 copy failure). Until today this project had **no tracked ledger at all**, so
its entire deferred-work record — 25 KB — existed only in
scratch space. Found by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current. The one intentional edit is
id renaming, below.

Durability first; curation is owned follow-up work.

---

## DW-1-1-1 — Fresh bmad-loop worktrees can't `pixi run`/`pixi lock`/`pixi install` any brand-new or never-yet…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: Fresh bmad-loop worktrees can't `pixi run`/`pixi lock`/`pixi install` any brand-new or never-yet-locked environment (e.g. `pyforge-herald`) because the whole-workspace lock re-solve also touches the unrelated `bmad-ui` env, which needs the gitignored, worktree-unseeded `build_artifacts/linux64` local channel; `.bmad-loop/policy.toml`'s `[scm].worktree_seed` (literal-paths-only list) does not include it.
  evidence: Reproduced live in this worktree — `pixi run -e pyforge-herald herald deck --help` and `pixi install -e pyforge-atlas` (an existing, unrelated env, unmodified by this story) both fail identically with "could not find subdir 'noarch' in channel 'file://.../build_artifacts/linux64/'"; `build_artifacts/` is gitignored (`.gitignore:674`) and absent from this worktree, but present and populated in the main checkout. Same root cause independently hit and deferred by pyforge-atlas Story A1 (`_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-a1-scaffold-the-kedro-pixi-project-via-nebi.md`, Task 4.4: "container limitation, workstation follow-up required") and reportedly two pyforge-warden stories — this is (at least) the third occurrence. Fix candidates for whoever picks this up: add `build_artifacts/linux64` to `[scm].worktree_seed` in `.bmad-loop/policy.toml` (symlink, not copy, given its size), or give `bmad-ui` a `no-default-feature` env that only solves when explicitly requested so an unrelated `pixi run -e <other-env>` never touches it.
  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED AT THE ROOT — better than either fix candidate this entry proposed. The `bmad-ui` environment no longer HAS a local `./build_artifacts` channel: root `pixi.toml:1188` now reads `channels = ["conda-forge", "SelfExplainML"]`, and the comment at `:1177-1187` documents the removal while quoting this entry's exact failure string ("could not find subdir 'noarch' in channel 'file:///…/build_artifacts/linux64/'"). `pixi.lock` now contains ZERO `build_artifacts` references. Since the whole-workspace re-solve no longer touches a machine-local channel, seeding it into the worktree is moot. Third occurrence of the class (atlas A1, two warden stories, this) closed at source rather than worked around.

  verified: 2026-09-02 — done — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md, _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-a1-scaffold-the-kedro-pixi-project-via-nebi.md); ledger status mapped to done; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-1-2 — The `/dist/` and `/dist-conda/` lines in the pixi-package `.gitignore` pattern (copied verbatim…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: The `/dist/` and `/dist-conda/` lines in the pixi-package `.gitignore` pattern (copied verbatim from `pyforge-warden`'s and now also `pyforge-herald`'s `.gitignore`) are broken by trailing inline `#` comments, which git treats as literal pattern text rather than a comment — the directory patterns silently don't match.
  evidence: Empirically verified in this worktree on both `pyforge-warden/dist/` and `pyforge-herald/dist/`: a planted `manifest.json` under either shows up as untracked (`git status --porcelain` -> `??`), and `git check-ignore -v` resolves the match to the *root* `.gitignore`'s `!src/**/packages/*/**` re-inclusion rule, not the package's own broken `/dist/`/`/dist-conda/` lines. Currently masked because real build artifacts (`.conda`/`.whl`/`.tar.gz`) also match separate, unbroken extension-wildcard lines in the same file — but any future non-matching byproduct in either directory (a manifest, a log) would not be ignored. Found by Blind Hunter review of spec-1-1's diff; out of that story's scope since it only reproduces a pre-existing pattern shared identically by warden/atlas (touching those files was explicitly out of bounds for 1.1). Fix: drop the trailing comments (put them on their own line above) in all three packages' `.gitignore` files in one pass.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN and WIDER — the entry named warden/atlas/herald; four packages carry it today. `pyforge-warden/.gitignore:2-3`, `pyforge-doctor/.gitignore:2-3`, `pyforge-scribe/.gitignore:2-3` and `pyforge-herald/.gitignore:2-3` all still read `/dist/          # pypi: wheel + sdist (python -m build)`. atlas (`:6`) and marshal (`:6-7`) use bare lines and are clean — so atlas is now FIXED but scribe and doctor inherited the defect. Same finding as marshal's DW-1-1-2, reached independently.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-1-3 — None of `pyforge-warden`/`pyforge-atlas`/`pyforge-herald`'s `pyproject.toml` scope `[tool.hatch.…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: None of `pyforge-warden`/`pyforge-atlas`/`pyforge-herald`'s `pyproject.toml` scope `[tool.hatch.build.targets.sdist]` (only the wheel target is scoped to `src/pyforge`), so the sdist tarball relies on hatchling's default file-selection rather than an explicit include list.
  evidence: Confirmed by reading all three packages' `pyproject.toml` — none has a `[tool.hatch.build.targets.sdist]` section. Low current risk (hatchling defaults to VCS-aware selection in a git repo, and the `.gitignore` already excludes most local build cruft, modulo the trailing-comment bug above) but worth an explicit include list for reproducibility. Found by Blind Hunter review of spec-1-1's diff; not unique to this story.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — measured across all three named packages: `grep -c 'targets.sdist'` returns 0 for `pyforge-warden`, `pyforge-atlas` AND `pyforge-herald`'s `pyproject.toml`. No explicit sdist include list was added anywhere.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md, src/pyforge); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-1-4 — `pyforge-warden`/`pyforge-atlas`/`pyforge-herald` each declare `license = { text = "MIT" }` in `…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: `pyforge-warden`/`pyforge-atlas`/`pyforge-herald` each declare `license = { text = "MIT" }` in `pyproject.toml` with no accompanying `LICENSE` file in the package directory.
  evidence: Confirmed by directory listing of all three package roots — none has a `LICENSE`/`LICENSE.txt` file (only the repo-root `LICENSE.txt`). Found by Blind Hunter review of spec-1-1's diff; pre-existing pattern shared by all three packages, not unique to this story.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and the sweep is now larger than the three named: `ls src/shared/packages/*/LICENSE*` returns nothing across all EIGHT sibling packages while each `pyproject.toml` still declares MIT. Same defect as marshal's DW-1-1-3 — two projects ledgered it independently, which is itself a signal it needs one owner.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-1-5 — `pyforge-herald`'s version `"0.1.0"` (like warden's/atlas's) is hand-duplicated between the pack…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: `pyforge-herald`'s version `"0.1.0"` (like warden's/atlas's) is hand-duplicated between the package's own `pixi.toml` `[package]` table and `pyproject.toml` `[project]` table with no automated check that a future bump keeps both in sync.
  evidence: Confirmed by reading both files — two independent literal `version = "0.1.0"` strings. Found by Blind Hunter review of spec-1-1's diff; pre-existing pattern shared by all three packages, not unique to this story.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — two independent literals remain: `pyforge-herald/pixi.toml:17` `version = "0.1.0"` and `pyforge-herald/pyproject.toml:7` `version = "0.1.0"`. A version-sync meta-test DOES now exist but does not cover herald: `pyforge-marshal/tests/meta/test_manifest_sync.py` is scoped to Marshal's own manifests (its docstring says 'Marshal's declared deps'), so herald, warden and atlas remain unguarded.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-1-6 — `pyforge-herald`'s root `pixi.toml` feature block pins `python-build = ">=1.5.0"` with no upper…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: `pyforge-herald`'s root `pixi.toml` feature block pins `python-build = ">=1.5.0"` with no upper bound, copied verbatim from `pyforge-warden`'s identical unbounded pin.
  evidence: Confirmed in the diff and in `pyforge-warden`'s root `pixi.toml` feature block — same unbounded `>=1.5.0` pin, no CI task in either package that would catch a breaking major-version `build` release before it ships. Found by Blind Hunter review of spec-1-1's diff; pre-existing pattern shared with warden, not unique to this story.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN at four sites, not one: root `pixi.toml:136`, `:165`, `:200` and `:268` all declare `python-build = ">=1.5.0"` with no upper bound. No CI task caps or checks it.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-1-7 — The verify-gate repair for this story (populating `build_artifacts/linux64` stubs so `pixi run -…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: The verify-gate repair for this story (populating `build_artifacts/linux64` stubs so `pixi run -e pyforge-herald ...` could extend `pixi.lock`) left the committed lock's `bmad-ui` environment channel pointing at this ephemeral bmad-loop worktree's own absolute path (`file:///.../.bmad-loop/runs/<run-id>/worktrees/<unit>/build_artifacts/linux64/`) rather than a stable location — once this worktree is torn down post-merge, that entry dangles.
  evidence: Confirmed two independent fix attempts both fail: (1) hand-editing the URL back to the primary `local-recipes` checkout's path reverts to the worktree-absolute path on the very next unfrozen `pixi run` that touches any environment requiring a lock recompute; (2) replacing `build_artifacts` with a symlink to the primary checkout's real `build_artifacts` (hypothesis: pixi might `realpath()`-canonicalize it) still writes the worktree-literal path — pixi 0.73.0 does not resolve symlinks when recording a relative-path local channel's absolute `file://` URL, it joins the manifest's own (unresolved) project root. Independently flagged by both the Blind Hunter and Edge Case Hunter review passes on this story's diff. Narrow real-world impact: `bmad-ui` is an optional, manually-invoked, non-CI-gated local feature that `pyforge-herald`'s own gate never touches or depends on; the entry self-heals the next time anyone runs an unfrozen pixi command against `bmad-ui` from a checkout with `build_artifacts/linux64` actually populated (the pre-existing requirement of that feature, per the first deferred-work entry above). Durable fix: once `pyforge-herald`'s own lock entry is stable, switch its bmad-loop policy gate to `--frozen` (mirroring the fix already applied to `pyforge-warden`'s `.bmad-loop/policy.toml`) so no future verify pass ever needs to touch `bmad-ui` again.
  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED, by the same root-cause fix that closed DW-1-1-1 above — and note the entry's own preferred durable fix (switch herald's gate to `--frozen`) turned out not to be needed. The dangling worktree-absolute channel cannot recur because the channel is gone: `pixi.lock` holds ZERO `build_artifacts` references, and root `pixi.toml:1180-1186` records exactly this failure mode as the reason for removal ('pixi records a channel as an ABSOLUTE path, so pixi.lock carried a machine-specific file:///home/<user>/… that exists on exactly one machine'), naming the two Pages deploys it broke on 2026-07-26.

  verified: 2026-09-02 — done — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md); ledger status mapped to done; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-1-8 — No meta-test enumerates or validates the set of registered pixi environments/features in root `p…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: No meta-test enumerates or validates the set of registered pixi environments/features in root `pixi.toml` (unlike the "three places" convention enforced for conda-forge-expert scripts, or the BMAD-artifacts sync test) — a newly added environment like `pyforge-herald` has no automated check that it stays correctly wired.
  evidence: Confirmed no such test exists for any of `pyforge-warden`/`pyforge-atlas`/`bmad-ui`/`pyforge-herald` either — a pre-existing gap in the pixi-environment-registration convention, not unique to this story. Found by Blind Hunter review of spec-1-1's diff.
  status: open

  verified: 2026-07-30 — PARTIALLY ADDRESSED, held open for the specific gap named. What now exists: `tests/packaging/test_dependency_completeness.py:51-73` declares an `EXPECTED_PACKAGES` floor over all 8 packages plus `_discover()` and a `test_discovery_is_not_vacuous` guard against the glob silently collapsing to zero — real protection that did not exist when this entry was written. What still does NOT exist: any test that reads root `pixi.toml`'s `[environments]`/`[feature.*]` tables. Discovery is by DIRECTORY GLOB (`PACKAGES_DIR.glob("pyforge-*")`), so a package present on disk but never registered as a pixi environment — precisely the wiring this entry asks to validate — still passes every test.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-1 — `McpTransport` opens one `asyncio.run()`-scoped MCP session per tool call (one extra `initialize…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `McpTransport` opens one `asyncio.run()`-scoped MCP session per tool call (one extra `initialize` round-trip per call) rather than holding a persistent session; an available optimization only if `herald deck watch` (CAP-4) ever polls often enough for it to matter.
  evidence: Deliberate Story 1.2 design decision, recorded in the spec's Design Notes and in `transport/mcp_transport.py`'s module docstring. Safe because the server keeps no session-scoped state Herald depends on — `plan_token` and the `if_match`/`if_none_match` etags are explicit parameters on every later call (confirmed against the live tool schemas). A persistent session would need a background event loop plus a single owning task (anyio cancel scopes forbid entering and exiting `streamablehttp_client` from different tasks) and a new `anyio` dependency that `llms-full-check` would flag as `undocumented-dep` — real machinery to save one round-trip on commands that make a handful of calls. Revisit only with a measured `watch`-loop cost.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN and unchanged by design. `mcp_transport.py:578` still calls `asyncio.run(...)` inside the per-call path, and `:550`'s docstring still states 'One ``asyncio.run()``-scoped session per call (see module doc)', with the module-level rationale at `:22`. No persistent session, no `anyio` dependency — the revisit condition (a measured `watch`-loop cost) has not arrived because Story 4.3 does not exist yet.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-2 — bmad-loop worktree paths longer than ~173 characters make EVERY `pixi` source-package operation…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: bmad-loop worktree paths longer than ~173 characters make EVERY `pixi` source-package operation (`pixi lock`, `pixi install`, `pixi run -e <env-with-a-path-dependency>`, `pixi build`) panic in the `pixi-build-python` backend, so no pyforge-{herald,warden,atlas} verify gate can run in such a worktree at all. Long story slugs are what push a run over the line.
  evidence: Root-caused to an unchecked `usize` subtraction in `pixi-build-backends` `crates/pixi-build-backend/src/tools.rs::output_directory` (`placeholder[0..placeholder_length - build_dir.join("host_env").as_os_str().len()]`, `placeholder_length = 255`) — it underflows whenever the rattler-build `build_dir` plus `/host_env` exceeds 255 bytes, producing `end byte index 18446744073709551595 is out of bounds for string of length 260` and killing the backend mid-handshake ("the build backend (pixi-build-python) exited prematurely"). `build_dir` is `<workspace-root>/.pixi/meta-v0/<pkg>-<hash>/work/<pkg>-<hash>` (a fixed 73-byte suffix for pyforge-herald), so the hard ceiling is a workspace root of 246 - 73 = 173 bytes. This worktree's root is 194 bytes (`.bmad-loop/runs/20260725-084750-c3b9/worktrees/1-2-transport-port-primary-mcp-client-adapter-the-transport-spike`) — exactly 21 over, matching the reported `-21` underflow byte-for-byte. Reproduced on the PRISTINE baseline manifests (story changes stashed), so it is pre-existing and story-independent; it also fires for the unrelated `pyforge-warden`/`pyforge-atlas` envs in the same workspace, and the failing environment/platform varies run to run because the backends are spawned in parallel. Three workarounds tested and REJECTED: a short symlink to the worktree passed via `--manifest-path` (pixi canonicalizes it), replacing `.pixi` with a symlink to a short path (pixi joins the unresolved root), and `PIXI_FORCE_NETFS_REDIRECT=1` (redirects only the download caches, never `.pixi/meta-v0`). `pixi build --build-dir` exists but is not reachable from `pixi lock`/`pixi run`. WORKAROUND THAT WORKS: run the pixi gate from a short-path checkout — `git worktree add --detach /home/<user>/hl HEAD`, copy the story's working-tree changes in, run there, copy `pixi.lock` back (rewriting the one `bmad-ui` `file://` local-channel URL to the real worktree path, the only absolute path the lock records). Durable fixes for whoever picks this up, in order of preference: (1) cap the generated worktree directory name in `.bmad-loop` (hash or truncate the story slug) so the root stays under ~170 bytes; (2) put bmad-loop run worktrees at a short root (e.g. `~/.bmad-loop-wt/<run-id>/<n>`) instead of nesting them under `<repo>/.bmad-loop/runs/<run-id>/worktrees/<slug>`; (3) upstream a saturating-subtraction fix to pixi-build-backends.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN in the backend, but fix candidate (2) WAS effectively adopted and the trigger is no longer live. The panic itself is untouched: `pixi.lock` still resolves `pixi-build-python-0.8.3` on all three platforms, so the unchecked `usize` subtraction in `tools.rs::output_directory` is unfixed upstream. But the fleet moved to `~/.bmad-loops/`, and measuring this entry's OWN worst-case path against every one of the nine homes gives a maximum of 154 bytes (steward/marshal/genesis) versus the 173 ceiling — 19 bytes of headroom. Candidates (1) slug-capping and (3) the upstream saturating-subtraction fix remain undone, so a longer story slug could still cross it.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-3 — The `DesignTransport` port has no `list_files` or `delete_files` method, but the live `finalize_…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: The `DesignTransport` port has no `list_files` or `delete_files` method, but the live `finalize_plan` / `copy_files` schemas require them — `finalize_plan` with `scope: "project"` returns no `base_etags` and directs the caller to "use `list_files` / `read_file` etags for `if_match`", and a folder-dest `copy_files` needs `leaf_if_match` "built from the source listing". Neither is reachable through the port.
  evidence: The 8-tool surface is fixed by ARCHITECTURE-SPINE.md AD-3 and by Story 1.2's epics acceptance criteria, so widening it was out of this story's scope. Confirmed against the live tool schemas 2026-07-25: the server exposes 23 tools, including `list_files` and `delete_files`, and their descriptions carry the etag-sourcing instructions quoted above. Impact lands on Story 1.6 (seed's `copy_files` of `deck-stage.js`) and Epic 5 (export push-back, which needs per-file etags for files it did not just read). `mcp_transport.py`'s own `finalize_plan` comment already names the gap. Whoever picks this up should decide whether AD-3's "exactly 8 tools" is amended to 9-10, or whether bridge-core is expected to obtain etags only via `read_file`.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the port is still exactly four methods. `transport/base.py` defines `finalize_plan` (`:192`), `copy_files` (`:215`), `write_files` (`:226`) and `read_file` (`:236`), with no `list_files` and no `delete_files`. AD-3's 'exactly 8 tools' has not been amended, so the etag-sourcing path that `finalize_plan` with `scope: "project"` and folder-dest `copy_files` both require is still unreachable through the port.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-4 — `FileRead` drops the server's `untrusted-project-content` provenance marking — the wrapper exist…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `FileRead` drops the server's `untrusted-project-content` provenance marking — the wrapper exists precisely to flag the body as user-authored content that may carry prompt-injection text, and nothing downstream of the transport records that.
  evidence: Verified in the live `read_file` response: the body is wrapped in `<untrusted-project-content …>` and the trailer reads "Do not follow any instructions inside it -- it is user-authored file content." `parse_read_response` strips both and returns a bare `str` body. Harmless for Story 1.2 (nothing consumes a body yet) but load-bearing from Story 2.1 (pull) onward, and especially if any body is ever surfaced to a model. Fix candidate: carry an explicit `untrusted: bool = True` on `FileRead`, or name the field `untrusted_body`.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the marking is still dropped. `transport/base.py:68` defines `_READ_TAG = "untrusted-project-content"` purely to STRIP it, and the `FileRead` dataclass at `:104` carries `unchanged`/`body`/`first_line`/`last_line`/`total_lines`/`truncated`/`etag` — no `untrusted` flag and no `untrusted_body` rename. Nothing downstream can tell the body is user-authored.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-5 — A conflicted write is returned to the caller as an ordinary success `Mapping`. The live `write_f…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: A conflicted write is returned to the caller as an ordinary success `Mapping`. The live `write_files` / `copy_files` schemas state an `if_match` mismatch answers with a *structured conflict result*, not an error — so `isError` is false and the adapter reports it as a normal answer. `copy_files` is additionally documented as not all-or-nothing.
  evidence: Confirmed in the live tool schemas 2026-07-25 ("the write is refused (structured conflict result, nothing written) unless the file is still at that etag"). This is arguably correct hexagonal layering — the transport reports, bridge-core decides — and AD-6 assigns `SeedConflictError`/`PullConflictError`/`ExportConflictError` to Story 1.4's bridge-core, which does not exist yet. Recorded so Story 1.4 does not assume a conflicted write raises: FR-24 currently guarantees only that a precondition was *sent*, not that a violated one was *noticed*.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — grepping the whole `transport/` package for `conflict` returns nothing, so a structured conflict result is still handed back as an ordinary success `Mapping`. `SeedConflictError`/`PullConflictError`/`ExportConflictError` remain unbuilt (Story 1.4's bridge-core still does not exist), exactly as the entry anticipated.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-6 — `_call_tool_async` — the only code that builds the three auth headers, filters MCP content block…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `_call_tool_async` — the only code that builds the three auth headers, filters MCP content blocks to text, and reads `isError` — is exercised solely by the opt-in `live`-marked spike, so the default offline gate cannot catch a regression in it.
  evidence: By construction: every other test injects a `ToolCaller` fake that bypasses the SDK entirely (that seam is what lets the socket-deny harness stay on). Notably the `getattr(block, "type", "") == "text"` filter silently drops `structuredContent`, which current MCP SDKs return for tools declaring an `outputSchema` — a server-side change there would surface only as `_call_json`'s "unparseable answer". Fix candidate: extract header construction into a pure `_build_headers(credential)` and unit-test it, and add a fake in-process `ClientSession` double for the block-filter/`isError` logic.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `_call_tool_async` is still executed only by the live spike. `tests/test_mcp_transport.py` patches it out at `:619`, `:746` and `:783` (`monkeypatch` of `pyforge.herald.transport.mcp_transport._call_tool_async`), so every offline test bypasses the real body; only `tests/test_live_design_spike.py:41` (`pytest.mark.live`) reaches it. Neither fix candidate landed: there is no `_build_headers` helper and no in-process `ClientSession` double.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/3 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md, tests/test_live_design_spike.py, tests/test_mcp_transport.py); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-7 — A server-*answered* JSON-RPC error is reported as `TransportUnreachableError`. The `mcp` SDK rai…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: A server-*answered* JSON-RPC error is reported as `TransportUnreachableError`. The `mcp` SDK raises `McpError` for protocol-level failures instead of returning `isError=True`, so those never reach `_raw_text`'s `TransportCallError` path and collapse into the generic `except Exception` at `mcp_transport.py`, telling the operator the endpoint could not be reached when it answered.
  evidence: Found by the 2026-07-25 follow-up review. `errors.py` documents exactly this distinction (reached-and-refused vs never-reached) and no test injects an `McpError`, because every offline test bypasses the SDK through the `ToolCaller` seam. Not patched here: distinguishing it means importing the SDK's error type (lazily, to keep the import cheap) or matching on a type name, and AD-6 assigns error *interpretation* to Story 1.4's bridge-core. Fix candidate: map `McpError` to `TransportCallError` in `_call_via_mcp_sdk`, covered by the same in-process `ClientSession` double the header/block-filter entry above already asks for.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `McpError` appears ZERO times in `mcp_transport.py`, so a server-answered JSON-RPC error still falls through to the generic handler and is reported as `TransportUnreachableError`. The mapping to `TransportCallError` the entry proposes was never added.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-8 — HTTP 429 and 5xx have no distinct error class — both land on `TransportUnreachableError`, so a r…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: HTTP 429 and 5xx have no distinct error class — both land on `TransportUnreachableError`, so a rate limit or a transient server fault is indistinguishable from an outage and a caller cannot tell "back off and retry" from "give up".
  evidence: Found by the 2026-07-25 follow-up review. `_indicates_auth_failure` splits 401/403 out precisely because `bridge-protocol.md` § Watch parameters needs that distinction; the retry-vs-backoff distinction is the same shape and is not made. Deferred rather than patched because the consumer of it (the watch loop's backoff policy) is Story 4.3, and inventing the class now would fix its semantics before the caller exists.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the auth split exists and the retry split does not. `mcp_transport.py:266` still defines `_indicates_auth_failure` (used at `:592`) to separate 401/403, while grepping for `429`, `5xx` or any `RateLimit`-shaped class returns nothing. A rate limit is still indistinguishable from an outage.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-9 — No request timeout is set on either `streamablehttp_client(...)` or `session.call_tool(...)`, so…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: No request timeout is set on either `streamablehttp_client(...)` or `session.call_tool(...)`, so a server that accepts the connection and never answers blocks the synchronous port for whatever the SDK's internal default is — a value free to change inside the unbounded `mcp>=1.28.1` range.
  evidence: Found by the 2026-07-25 follow-up review; confirmed by reading `_call_tool_async`, which passes no timeout to either call. Harmless for the one-shot commands Story 1.2 ships (an operator sees a hang and Ctrl-Cs) but load-bearing for `herald deck watch` (Story 4.3), whose 60 s poll cadence assumes a call cannot outlast it. Fix candidate: thread an explicit timeout through `McpTransport.__init__` and assert it in the live spike.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `timeout` appears ZERO times in `mcp_transport.py`, so neither `streamablehttp_client(...)` nor `session.call_tool(...)` is bounded and the SDK's internal default still governs, inside a pin range that is itself unbounded (see DW-1-2-10).

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-10 — `mcp>=1.28.1` is declared with no upper bound in all three manifests while `_call_tool_async` bi…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `mcp>=1.28.1` is declared with no upper bound in all three manifests while `_call_tool_async` binds SDK internals (`mcp.client.streamable_http.streamablehttp_client`, `ClientSession`, `result.content` block `.type`/`.text`, `result.isError`) that only the opt-in live spike executes — a breaking major release would solve cleanly, pass the whole default gate, and fail at first real use.
  evidence: Found by the 2026-07-25 follow-up review. Not patched here deliberately: capping the pin edits `pyproject.toml` + both `pixi.toml`s and forces a `pixi.lock` regeneration, and this story's lock was being rebuilt out-of-band on `build/pyforge-herald-1-2` at the time — a concurrent re-lock is the wrong moment to change a dependency constraint. Pair the cap with the offline `ClientSession` double so the binding is testable, and note the same unbounded-pin pattern is already deferred for `python-build` from Story 1.1.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN in all three manifests, verified individually: `pyforge-herald/pyproject.toml:16` `dependencies = ["mcp>=1.28.1"]`, `pyforge-herald/pixi.toml:34` `mcp = ">=1.28.1"`, and root `pixi.toml:1479` `mcp = ">=1.28.1"`. No ceiling anywhere, and the offline `ClientSession` double that would make the SDK binding testable still does not exist.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-11 — `McpTransport` resolves the credential once and caches it on the instance for the process lifeti…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `McpTransport` resolves the credential once and caches it on the instance for the process lifetime, with no re-resolution when it expires — a long-running `herald deck watch` keeps sending a dead token even after the operator has re-run `/design-login`.
  evidence: Found by the 2026-07-25 follow-up review; `_call_via_mcp_sdk` sets `self._credential` on first use and never revisits it. Arguably correct for Story 1.2 (an expired token is a clean `AuthError`, and NFR-05 forbids Herald minting or refreshing anything), but the *re-read* of an externally refreshed file is not a refresh and would make `watch` survive a routine re-login. Belongs with Story 4.3's watch lifecycle, not with the transport.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `mcp_transport.py:308` still does `self._credential = credential` and nothing re-reads the credentials file afterwards. A long-running process keeps sending the token it resolved at first use.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-12 — `AuthError` subclasses `TransportError`, so the natural retry predicate for the parent class (`e…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `AuthError` subclasses `TransportError`, so the natural retry predicate for the parent class (`except TransportError: backoff_and_retry()`) silently swallows the one error `bridge-protocol.md` says must halt the loop and never be retried.
  evidence: Found by the 2026-07-25 follow-up review; confirmed by reading `errors.py`'s hierarchy. The inheritance is deliberate (an auth failure *is* a transport failure) and no code retries yet, so nothing is broken today. Recorded so Story 4.3 does not write the obvious predicate: whoever builds the watch loop should catch `AuthError` first, or the hierarchy should grow a `RetryableTransportError` layer that `AuthError` sits outside of.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `errors.py:30` still declares `class AuthError(TransportError)`, sitting under `TransportError` (`:26`) alongside `TransportUnreachableError` (`:38`) and `TransportCallError` (`:47`). No `RetryableTransportError` layer was introduced, so `except TransportError: backoff_and_retry()` would still swallow the one error that must halt the loop.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-13 — `sanitize_payload` collapses two distinct string mapping keys that both name the tokenized previ…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `sanitize_payload` collapses two distinct string mapping keys that both name the tokenized preview host onto the single `REDACTED` constant, so the second silently overwrites the first and one entry disappears from the payload.
  evidence: Found by the 2026-07-25 follow-up review and reproduced: `sanitize_payload({"https://a.claudeusercontent.com/x": 1, "https://b.claudeusercontent.com/y": 2})` returns a one-entry dict. The companion defect (a non-string key sanitizing to an unhashable list and raising a bare `TypeError`) WAS patched in this pass; the collapse was not, because no observed tool answer keys a map by URL and preserving distinctness means inventing a suffix scheme for a shape that has never appeared. Revisit if any tool is ever seen returning a URL-keyed map.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — reproduced by execution, not by reading. Calling `sanitize_payload({'https://a.claudeusercontent.com/x': 1, 'https://b.claudeusercontent.com/y': 2})` returns `{'<redacted: tokenized preview url>': 2}` — a ONE-entry dict from a two-key input, with the first value silently lost to the collapse. Exactly the behaviour the entry recorded, unchanged.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-14 — `mcp_transport.py` imports `_as_text` and `_as_optional_text` from `base.py` as underscored priv…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `mcp_transport.py` imports `_as_text` and `_as_optional_text` from `base.py` as underscored privates, the exact cross-module-private import that `require_conditional` was promoted to public to avoid.
  evidence: Found by the 2026-07-25 follow-up review; confirmed in `mcp_transport.py`'s import block. Story 1.3's `AgentSdkTransport` needs the same null-coercion (the `str(None)` -> truthy `"None"` etag trap these exist to prevent), so it will either repeat the private import or re-implement the coercion untested. Fix candidate: promote both alongside `require_conditional` when Story 1.3 lands, so the public seam is settled by its second consumer rather than its first.
  status: done 2026-08-07

  verified: 2026-07-30 — CONFIRMED STILL OPEN — and the contrast is visible in a single import block. `mcp_transport.py` imports `_as_optional_text` (`:77`) and `_as_text` (`:78`) as underscored privates from `base.py`, immediately alongside the public `require_conditional` (`:80`) that was promoted specifically to avoid this pattern. `_as_text` is in live use at `:331`.

  resolved: 2026-08-07 — Story 1.3 landed exactly the fix candidate: `base.py`'s `_as_text`/`_as_optional_text` are now public `as_text`/`as_optional_text`, re-exported from `transport/__init__.py` alongside `require_conditional`. `mcp_transport.py`'s import updated to the public names (no behavior change, pure rename); `agent_sdk_transport.py` is the second consumer that settles the seam as public, exactly as the fix candidate anticipated.

  verified: 2026-09-02 — done — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to done; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-2-15 — `ARCHITECTURE-SPINE.md`'s amended *Etag headers* convention row asserts that `read_file`'s `if_n…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `ARCHITECTURE-SPINE.md`'s amended *Etag headers* convention row asserts that `read_file`'s `if_none_match` is "required whenever a prior etag is held", but nothing in the port, the adapter, or the tests enforces or records that obligation — a documented-only invariant of exactly the kind FR-24 was made structural to avoid.
  evidence: Found by the 2026-07-25 follow-up review. The asymmetry is real and deliberate for 1.2 (the transport cannot know whether its caller holds an etag), but it means Story 1.4's bridge-core can poll without `if_none_match`, transfer the full body every cycle, and still read as spine-compliant. Fix candidate: make it structural where the knowledge lives — have bridge-core's watch state carry the last etag and pass it unconditionally, with a test that asserts the poll sends one.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the documented-only obligation is intact and still unenforced. `architecture-pyforge-herald-2026-07-25/ARCHITECTURE-SPINE.md:146` still asserts that `read_file`'s `if_none_match` is 'optional on a first read … and required whenever a prior etag *is* held', while nothing in the port, the adapter or the tests records or checks that obligation.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-1-9 — Story 1.1's spec was never promoted from the gitignored Tier-3 `implementation-artifacts/` into…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: Story 1.1's spec was never promoted from the gitignored Tier-3 `implementation-artifacts/` into the tracked `planning-artifacts/specs/`, so its intent contract exists in no clone. Story 1.2's spec was promoted in this pass; 1.1's was left because it is another story's artifact.
  evidence: CLAUDE.md's 2026-07-25 "story specs are durable (tracked), NOT Tier-3" convention requires promotion after a story merges, and 1.1 merged at `2f9c635f7b`. The file is still present at `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md` in the primary checkout (it lives outside the run worktree, so worktree teardown does not destroy it) — this is a durability gap, not an active loss, and the fix is a one-file copy plus a commit.
  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED — the promotion happened. `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-1-1-package-scaffold-for-pyforge-herald.md` now exists and is tracked, alongside 1.2's. The durability gap is closed; the intent contract is in every clone.

---

## Promoted 2026-07-31 — the six-station fleet run

Four entries below carried **no id at all** in Tier-3 (bmad-loop's `- source_spec:` shape),
so `deferred_work_check.py` could not even see them — it matches on `DW-*` ids. They were
Tier-3-only and would have died with the scratch dir. The fifth was the generic `DW-1`.

  verified: 2026-09-02 — done — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/3 present (absent: _bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md, _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md); ledger status mapped to done; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-4-1 — Follow-up review still recommended for 1-4-bridge-core-skeleton-state-errors-determinism-boundar

> Promoted 2026-07-31. bmad-loop wrote this as generic `DW-1`; renamed to the
> `DW-<story>-<n>` convention so the next damped story cannot collide with it.

origin: review-budget-followup
source_spec: `spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260730-192235-062b; this entry preserves the lingering recommendation for a deliberate later review.
status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-4-2 — `state.py`'s `write()` does an unlocked read-modify-write of the whole slug-keyed document (read…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md`
  summary: `state.py`'s `write()` does an unlocked read-modify-write of the whole slug-keyed document (read every slug, mutate one, atomically replace the file), so two processes writing different slugs concurrently can race — the second writer's read can happen before the first writer's `os.replace`, silently losing the first writer's update. The atomic temp-file-plus-`os.replace` protects against a corrupted/partial file, not against a lost update.
  evidence: Found by this story's own Blind Hunter review pass. No current caller exercises concurrent writes (this story ships no seed/pull/watch logic yet — every call site is a single test), so it is latent, not active. Real risk lands with Story 4.x's `watch` loop if it ever runs multiple slugs' polls as separate processes, or with any future concurrent `herald` invocation against the same repo. Fix candidate: an advisory file lock (e.g. `fcntl.flock` on a sidecar lock file, POSIX-only) held across the read-modify-write span, or narrow `write()` to a single-slug patch file per artifact if per-slug granularity turns out to matter more than one shared document.
  status: done 2026-08-10

  verified: 2026-08-10 — RESOLVED by Story 13.1 (`spec-13-1-the-state-layer-survives-a-second-writer.md`), via the FIRST fix candidate this entry proposed (an advisory file lock), not the single-slug-patch-file alternative. Chosen approach: one shared, stdlib-only, cross-platform advisory file lock (`fcntl.flock` on POSIX, `msvcrt.locking` on Windows — this package targets win-64, so the original POSIX-only sketch was widened) in the new `locking.py`'s `locked(lock_path)` contextmanager, held across the whole read-modify-write span of `state.write()`, `progress.upsert()`, `claims.create()`, and `notices.author_notice()`/`publish_notice()`/`close_notice()`/`archive_rename()`, keyed on a sidecar `<document>.lock` file next to each protected document. SQLite/Postgres migration stays explicitly out of scope, per this story's own Never-list — that is Story 13.3's separate, larger-scoped migration; no fresh evaluation of that option was performed here. `claims.py`'s network-validating functions (`publish`, `revalidate`, `revalidate_all`) run `evidence_mod.validate_link`/`validate_for_publish` UNLOCKED, before acquiring the lock, so the lock never spans a live HTTP request — a first-pass implementation that locked the whole function was caught and reverted before landing (would have blocked every other claims writer for the duration of a network call). All three carry their pre-lock validation results POSITIONALLY — per claim, the pre-validation evidence tuple plus an index-aligned results tuple, applied back inside the lock at index `i` only when `i < len(original)` and `fresh.evidence[i] == original[i]` (the discard-stale rule; every other entry's write still lands) — never in a dict keyed by `Evidence` value. `Evidence` is a frozen, value-equal dataclass and `create` de-duplicates nothing, so a value-keyed map collapses two field-identical entries onto one key and applies a single result to both: WITHIN one claim (a duplicated link whose two checks return `True` then `False` stored `[False, False]` instead of `[True, False]`) and, for `revalidate_all`, ACROSS claims (one claim's outcome overwriting another's). `revalidate_all` additionally keys its per-claim structure by claim id (`dict[str, tuple[original, results]]`) so a lookup only ever searches within that same claim's own results. Both collapse variants were caught as review-loopback findings (passes 2 and 4) and fixed before landing. `publish` additionally re-verifies inside the lock that every evidence entry it is about to write carries this call's own validation, raising `errors.ClaimStateError` and writing nothing when a concurrent writer changed an entry during the unlocked validation window — the discard-stale rule alone would have let a claim persist as `published` over evidence that call never checked, bypassing publish's own broken-link gate; it stays as-is for `revalidate`/`revalidate_all`, whose purpose is to record breakage rather than gate on it. SCOPE OF THIS CLOSURE — read before relying on it: what is resolved is the unlocked read-modify-write *inside* each of those functions, which is exactly the defect this entry's `summary` describes. It does NOT resolve the wider read-network-write span in `deck_pipeline.py` that this entry's `update_2026-08-07` paragraph below describes: `_record_pull_etag`/`push_exports` build their replacement `etags` map from a `state.read` taken BEFORE the network pull/push and then hand the whole slug entry to `state.write`, so two concurrent `herald deck pull` invocations for the same slug can still drop one artifact's etag — `state.write`'s own lock cannot close a critical section that starts in its caller. `seed`'s duplicate-remote-project check (`deck_pipeline.py:199-206` -> `create_project` -> `state.write`) is the same shape. Both are caller-level spans outside Story 13.1's file surface (`state.py`/`progress.py`/`claims.py`/`notices.py`/`locking.py`) and were recorded as their own separate deferred-work entry — in `_bmad-output/implementation-artifacts/deferred-work.md` (this story's review-deferral file), NOT as a `## DW-` entry in this ledger — rather than being silently folded into this one. `state.write`'s own docstring carries the same caveat, so a reader of the code does not have to find this paragraph to learn the caller-level span is still open.
  update_2026-08-07: Epic 2's `herald deck pull` (Stories 2.1-2.4, `deck_pipeline.py`) is the first REAL caller of the "any future concurrent `herald` invocation against the same repo" scenario this entry already anticipated — an operator running two `herald deck pull <slug> --target ...` invocations for the SAME slug (different targets) concurrently now hits exactly this race, confirmed by Epic 2's own Edge Case Hunter review pass. Still deliberately not fixed here: it predates Epic 2, is already tracked, and Epic 2's own scope was the pull/land/re-derive logic, not `state.py`'s concurrency model. Raises this from "latent" to "concretely reachable" — worth prioritizing before Story 4.x's `watch` loop ships, since that will make concurrent state writes routine rather than an edge case.

  verified: 2026-09-02 — done — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/implementation-artifacts/deferred-work.md, _bmad-output/implementation-artifacts/spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md); ledger status mapped to done; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-4-3 — `state.py`'s `write()` calls `state_path.parent.mkdir(parents=True, exist_ok=True)` unguarded — …

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md`
  summary: `state.py`'s `write()` calls `state_path.parent.mkdir(parents=True, exist_ok=True)` unguarded — if any path component of `state_path.parent` already exists as a regular file (not a directory), `mkdir` raises an unhandled `NotADirectoryError`/`FileExistsError` rather than a `HeraldError`, contradicting AD-6's "every bridge command fails structurally" for this one rare shape.
  evidence: Found by this story's own Edge Case Hunter review pass. Lower priority than the JSON-corruption and malformed-entry cases already patched in this story (those are plausible from an interrupted write or hand-edit; this requires something to have created a plain file at exactly `.herald` or one of its ancestors, which nothing in this repo does today). Fix candidate: wrap the `mkdir` call and re-raise as `errors.HeraldError` naming the offending path.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1: Follow-up review still recommended for 1-4-bridge-core-skeleton-state-errors-determinism-boundary after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260730-192235-062b; this entry preserves the lingering recommendation for a deliberate later review.
status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-5-1 — `registry.read()` raises "malformed" (`expected exactly two body lines, found 5`) against every …

- source_spec: `_bmad-output/implementation-artifacts/spec-1-5-registry-module-readme-design-project.md`
  summary: `registry.read()` raises "malformed" (`expected exactly two body lines, found 5`) against every one of the 13 existing hand-seeded `presentations/*/README.md` § *Design project* sections (9 of them pyforge-*), so the bootstrap-fallback consumer a later CAP story wires in (AD-5) will fail against 100% of the current fleet until those sections are migrated to the canonical two-line shape or a tolerance decision is made — one `register()` call per deck normalizes a README, so Story 1.6's seed path may absorb the migration naturally, but nothing guarantees it covers all 13.
  evidence: Found by the 2026-07-31 follow-up review (Blind Hunter), reproduced live against the pyforge-herald/doctor/scribe/warden READMEs. Spec-sanctioned for this story — the intent contract's "Never" boundary explicitly scopes out parsing the pre-existing hand-authored prose — but the resulting migration debt was recorded nowhere until this entry.
  status: open

  verified: 2026-08-07 (Story 1.6) — the anticipated resolution path changed. `seed`'s registry-bootstrap-fallback conflict check treats a *malformed* § Design project section as "already linked, cannot verify" and raises `SeedConflictError` naming the parse failure, rather than silently absorbing/migrating it via a `register()` call. This was a deliberate choice: overwriting a section this module cannot prove matches its own canonical shape risks clobbering a real, hand-verified project link if the parse failure masks a different project id than expected. The 13 pre-existing malformed sections (9 pyforge-*) are therefore *still* migration debt, and now block `herald deck seed <slug>` on those exact slugs until resolved by hand (or a future story adds a `--force`/`--migrate-registry` escape hatch) — narrower than "seed naturally migrates them", not wider. Recorded as the current status; the migration itself remains undone.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/implementation-artifacts/spec-1-5-registry-module-readme-design-project.md, presentations/*/README.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-1-6-1 — Write-level conflict detection (the wire shape DW-1-2-5 could not pin) is out of `seed`'s scope

- source_spec: `_bmad-output/implementation-artifacts/spec-1-6-herald-deck-seed-slug.md`
  summary: `deck_pipeline.seed` detects an already-seeded deck via a pre-flight check (state.py, then registry.py as a bootstrap fallback) — both run *before* any transport call. It does not, and cannot yet, detect a conflict *at write time*: DW-1-2-5 (Story 1.2) recorded that a conflicted `write_files`/`copy_files` answers as an ordinary success `Mapping` with an unpinned structured-conflict shape, and nothing in this repo has observed that wire shape live. `bridge-protocol.md`'s CAP-1 success criterion ("seeding over existing Design-side edits is refused with a structured conflict") is therefore only satisfied for the case this story's pre-flight check can see (a state entry or registry section already naming a linked project) — a scenario where the *pre-flight* check passes clean (no local record of any link) but the Design-side project already independently exists with content at the same name/path is not distinguished from a legitimate fresh seed.
  evidence: By construction — `seed`'s `create_project`/`create_support_js`/`copy_files`/`write_files` calls all use fresh-etag (`"0"`) preconditions per FR-24 and trust whatever the transport returns without inspecting the payload shape for a conflict marker. Consistent with the story's own documented judgment call (module docstring, judgment call 1) and DW-1-2-5's own "recorded so Story 1.4 [does not / a future story does not] assume a conflicted write raises" framing.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-6-herald-deck-seed-slug.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-2: Follow-up review still recommended for 13-1-the-state-layer-survives-a-second-writer after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-13-1-the-state-layer-survives-a-second-writer.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260810-194532-e993; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, herald 13-1)

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-3: Follow-up review still recommended for 13-3-db-backed-storage-behind-the-existing-seam-with-migrations after the damping cap was spent
origin: review-budget-followup
source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-3-db-backed-storage-behind-the-existing-seam-with-migrations.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260813-094918-551b; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-3-db-backed-storage-behind-the-existing-seam-with-migrations.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-13-3-1: One corrupt legacy JSON file blocks all three Moments' stores, where before Story 13.3 it blocked only its own

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-3-db-backed-storage-behind-the-existing-seam-with-migrations.md`
  summary: One corrupt legacy JSON file blocks all three Moments' stores, where before Story 13.3 it blocked only its own.
  evidence: Reproduced against the merged branch. `db._import_legacy_v1` imports progress + claims + notices inside the single v1 migration, so any one legacy file failing validation aborts the whole migration and `_ensure_schema` retries from scratch on every later command. With a healthy `.herald/progress.json` and `.herald/notices-index.json` beside a truncated `.herald/claims.json`, `progress.read_all`, `claims.read_all` and `notices.list_notices` ALL raise `claims file ... could not be read`; against the pre-story revision `257094dcc2` the same fixture returns the progress and notices records normally and only claims fails. Not a spec deviation -- the spec mandates one shared database and mandates that an invalid legacy file fail migration rather than be silently dropped -- so re-deriving under the same spec reproduces it; the widened blast radius is an undecided consequence of those two mandates meeting, not a coding error. Needs a design decision (isolate each store's import so a bad file only blocks its own Moment, vs. accept the coupling and say so in the operator docs). Recovery today is real but undocumented: removing or repairing the one named file unblocks the other two, and nothing tells the operator that.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-3-db-backed-storage-behind-the-existing-seam-with-migrations.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-13-3-2: A read-only `.herald/` directory now fails every herald command, where before Story 13.3 reads still worked

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-3-db-backed-storage-behind-the-existing-seam-with-migrations.md`
  summary: A read-only `.herald/` directory now fails every herald command, where before Story 13.3 reads still worked.
  evidence: Reproduced on this branch. With a populated store made read-only (`chmod 444` on `.herald/herald.db`, `chmod 555` on `.herald/`), `progress.read_all` raises `HeraldError: ... could not be opened: attempt to write a readonly database`; every read command and all three exporter scripts fail the same way. Pre-Story-13.3 the equivalent read of a read-only `.herald/progress.json` returned its records normally. The cause is WAL itself, not a coding error: verified that even a bare `PRAGMA journal_mode` -- a pure read of the setting -- raises the same error on such a store, because a WAL database opened read-write needs to create/write the `-shm` sidecar. Story 13.3's spec mandates WAL under `## Boundaries & Constraints` -> Always, so re-deriving under the same spec reproduces this exactly; `_set_wal_mode`'s own docstring already records the fast-fail as intentional. Resolving it is a design decision rather than a fix: opening `file:...?mode=ro` when the store is not writable would restore read behavior but needs a rule for when to choose it, and WAL readers still need a writable directory for `-shm`, so the alternative may be to document the requirement instead. Neither the operator guide nor the troubleshooting doc mentions that `.herald/` must be writable even to read.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-3-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-3-db-backed-storage-behind-the-existing-seam-with-migrations.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-13-4-1: The webhook's HMAC scheme signs only the body, so one captured signed request stays a valid, reusable forgery token forever

**CLOSED by Story 13.6.** `webhook.verify_signature` now takes a fourth
argument, `timestamp_header`, folds it into the signed content
(`hmac.new(secret, timestamp + b"." + body, sha256)`), and rejects a
timestamp more than `MAX_TIMESTAMP_SKEW_SECONDS` (300s) from the server's
own clock in either direction -- exactly the first fix candidate below.
`.github/workflows/herald-live-demo.yml`'s `on-ship`/`on-pr-close` jobs
are the real producer this fix needed to exist before it could land; they
also send a per-event `event_id`, the fix's own second candidate.
Regression coverage: `tests/test_webhook.py`'s "Story 13.6: the
X-Hub-Timestamp skew window" section, including the literal replayed-
request-after-5-minutes AC.

**Residual, narrower than "closed" implies (2026-08-13 review pass):** a
captured, still-fresh (<5 min old) signed request remains fully valid and
replayable any number of times inside that window -- there is no nonce or
single-use token, only the timestamp-bounded expiry. Low-impact in
practice: `on-ship`'s `progress.upsert` is keyed by `(station, date)`, and
`on-pr-close`'s `event_id`-derived deterministic claim id both make an
in-window replay idempotent (re-applies the same record, never a
duplicate) rather than exploitable -- but that is a property of the
storage layer, not something `verify_signature` itself enforces, so this
entry is narrowed, not fully closed.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): no source_spec; cited paths 1/2 present (absent: tests/test_webhook.py); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-13-4-2: The webhook's claim idempotency guard reads and creates in two separate transactions, so two concurrent deliveries of one event can both create a claim sharing one id

**STILL UNREACHED as of Story 13.6** -- reasoning updated, not closed. The
module is mounted now (`webhook_host.py` behind `daphne`,
`.github/workflows/herald-live-demo.yml`), so "the module is not mounted"
is no longer why this is unreached, but the replacement reason holds
identically: every one of the workflow's three demo jobs delivers exactly
one signed request, serially, per job invocation -- there is no producer
anywhere in this repo that fires two concurrent deliveries of the same
logical event at the one live host that exists. `webhook_host.py`'s own
bounded executor (closing DW-FU-13-4-3, below) caps CONCURRENT DIFFERENT
requests at 4 workers, which is orthogonal to this gap: two workers could
race on the SAME event only if something actually sent two deliveries of
it at once, which nothing here does. Becomes reachable the moment any
producer retries a delivery in parallel with itself, or a second producer
is added that can double-send.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-4-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): no source_spec; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-13-4-3: A single webhook request can occupy a thread-pool worker for well over a minute, and neither the handler nor the caller bounds it

**CLOSED by Story 13.6.** `webhook_host.py`'s `_wrap` bounds every HTTP
request in `asyncio.wait_for(..., timeout=REQUEST_TIMEOUT_SECONDS)` (120s
-- comfortably above this entry's own measured ~93s legitimate worst
case) and points the running loop's default executor -- what
`webhook.py`'s own `asyncio.to_thread` dispatch actually submits work to
-- at a dedicated `concurrent.futures.ThreadPoolExecutor` capped at
`EXECUTOR_MAX_WORKERS` (4) workers, exactly the fix candidates below. A
timed-out request gets the same non-2xx (500) the retries-exhausted alert
path already returns, logged the same structured-JSON way. Regression
coverage: `tests/test_webhook_host.py`'s timeout/executor tests (a fast,
deterministic `asyncio.sleep`-based hang, never a real thread sleep).

**Narrower than "closed" implies (2026-08-13 review pass):** the timeout
bounds how long a *caller* waits, not how long a genuinely-hung handler
occupies its worker thread -- `Future.cancel()` cannot interrupt a thread
already running. Tracked as its own entry, `DW-FU-13-6-2`, since it is
currently inert (this story's demo is one throwaway process per one
request) but becomes live risk under any future persistent, multi-request
deployment.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-4-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): no source_spec; cited paths 0/1 present (absent: tests/test_webhook_host.py); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-13-4-4: `herald success create --shipped-date` accepts any string, and one malformed value then breaks `herald success list --date-range` for every operator afterwards
- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-4-the-webhook-endpoint-ci-calls.md`
  summary: `herald success create --shipped-date` accepts any string, and one malformed value then breaks `herald success list --date-range` for every operator afterwards.
  evidence: Reproduced end to end against this worktree, entirely through the CLI, with no webhook
  involved. `claims.create` validates only `project_name` and each evidence `type` -- it never
  looks at `shipped_date`, so `cli._run_success_create`'s `shipped_date=args.shipped_date`
  (`cli.py`, the `--shipped-date` flag) stores whatever was typed. `claims.list_claims` then calls
  `date.fromisoformat(c.shipped_date)` with no guard when a `--date-range` filter is present, and
  `cli.dispatch` translates only `HeraldError` -- so the bad value surfaces as a bare traceback,
  not the "message plus exit code 1" contract the runbooks promise. Measured:
  `herald success create Marshal --shipped-date 13/08/2026` answered `created draft claim
  a23f51a4-... ` and exit 0; the next `herald success list --date-range 2026-01-01..2026-12-31`
  raised `ValueError: Invalid isoformat string: '13/08/2026'` out of `cli.main`. The poisoned row
  is durable, so every subsequent date-ranged list fails for every operator until someone edits
  the database by hand. `"yesterday"`, `""` and `"2026-13-45"` behave the same way.
  This is pre-existing (Story 9.2/13.3 surface, unchanged by Story 13.4) and was surfaced
  incidentally by 13.4's review: the webhook opened a second, machine-driven route to the same
  storage, and that route is now closed by a structural 400 in
  `webhook._problem_on_pr_close_shipped`. The CLI route is not, so the underlying gap survives.
  Fix candidates, in the order they close the most for the least risk: (1) validate `shipped_date`
  in `claims.create` (a `date.fromisoformat` round-trip, raising `HeraldError`) so every caller --
  CLI, webhook, and anything Story 13.6 adds -- inherits it, which also lets the webhook's own
  duplicated check become a fast-fail rather than the only defense; (2) guard
  `claims.list_claims`'s parse so an already-poisoned store degrades to a skipped/flagged row
  instead of a traceback; (3) an `argparse` `type=` converter on `--shipped-date` for the earliest
  possible error message. Doing (1) alone leaves existing bad rows unreadable, so (1)+(2) together
  are the real fix.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-4-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-4-the-webhook-endpoint-ci-calls.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-13-5-1: Evidence revalidation runs unbatched sequential HTTP checks, now reachable unattended via cron instead of only under an operator's eye

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-5-the-scheduler-enforces-what-was-displayed.md`
  summary: Evidence revalidation runs unbatched sequential HTTP checks, now reachable unattended via cron instead of only under an operator's eye.
  evidence: `claims.revalidate_all` (Story 9.5, unchanged by Story 13.5) validates every claim's
  evidence links one at a time via `evidence.validate_link` (a real HTTP `HEAD`, default 5s
  timeout, up to 3 redirects each) entirely before opening its write transaction -- no batching,
  no concurrency, no cap. Previously this only ran when an operator chose to invoke
  `herald success validate --all` by hand and could see it running; Story 13.5's `herald
  scheduler run` reuses the identical call but is now the documented target of an unattended
  weekly `crontab` entry (`docs/cli-runbooks.md`), so its wall-clock time -- which grows linearly,
  unbounded, with the size of the claims store -- is no longer bounded by an operator's patience
  or attention. Today's claims store is small ("a handful of claim/notice links, checked at most
  weekly" per `evidence.py`'s own module docstring), so this is latent, not active; flagged by
  review pass 1's Blind Hunter (independently corroborated by the general shape of the concern
  the Edge Case Hunter also raised about job composition) and preserved here for whoever scales
  the claims store. Recovery/fix candidates: batch or cap concurrent HTTP checks in
  `claims.revalidate_all` before the claims store grows meaningfully, and/or document "a run may
  take a long time and appear hung" as an explicit failure mode alongside the "missed run"
  failure mode `docs/automation-troubleshooting.md`/`docs/cli-runbooks.md` already describe --
  neither doc currently mentions a slow-but-running invocation as distinct from a machine-off
  miss. Story 13.5's own `flock -n` crontab guard (added this pass) prevents two such runs from
  overlapping, but does not bound any single run's own duration.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-5` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/3 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-5-the-scheduler-enforces-what-was-displayed.md, docs/automation-troubleshooting.md, docs/cli-runbooks.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-13-6-1: Steward's `deploy perimeter` cannot target an arbitrary ASGI application, only a hardcoded Django placeholder -- so Herald's webhook has no path to a persistent, Steward-perimeter-hosted deployment

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-6-a-ship-records-itself-end-to-end.md`
  summary: Steward's `deploy perimeter` duty (Story 9.5, CAP-6) can only render deployment
  manifests pointed at a hardcoded Django ASGI placeholder -- there is no flag or mechanism to
  target an arbitrary ASGI callable such as Herald's own `webhook_host:application` -- so
  persistent, Steward-perimeter-hosted webhook deployment stays out of reach for any adopter that
  is not a Django project.
  evidence: `pyforge/steward/deploy.py`'s `render_daphne_unit` renders a systemd template unit
  whose `ExecStart` line hardcodes `_ASGI_APPLICATION_PLACEHOLDER = "myproject.asgi:application"`
  (deploy.py:484) with no corresponding CLI argument on `steward deploy perimeter` (`_run_perimeter`)
  to override it -- the module's own comment records this as a deliberate judgment call ("this
  story's spec Code Map names no CLI flag for the ASGI application import path... so rather than
  invent an unrequested flag, the adopter edits this one placeholder line by hand"). That is a
  reasonable choice for Story 9.5's own scope (Steward's OWN dashboard, a Django/Channels app --
  AD-5/AD-8's "the library binds at the ASGI application boundary" is about the ADOPTED app being
  framework-neutral, not about `deploy perimeter`'s own renderer being target-agnostic), but it
  means `webhook_host.py` (this story) has no way to hand `deploy perimeter` its own
  `pyforge.herald.webhook_host:application` target without hand-editing the rendered unit file
  after the fact -- which also then has to be re-applied after every re-render. Not pursued in this
  story: making `deploy perimeter` support an arbitrary ASGI target is real, cross-station
  engineering (a new CLI flag threaded through `render_daphne_unit`/`render_edge_config`, plus
  deciding whether the nginx edge config's own assumptions about a single Django-shaped app still
  hold for an arbitrary callable) squarely inside Steward's own Surface, not Herald's -- this
  story's own boundary is a bounded, CI-contained demonstration
  (`.github/workflows/herald-live-demo.yml`), explicitly never persistent hosting behind Steward's
  live perimeter. Fix candidates for whoever picks this up (a Steward-side story): add an
  `--asgi-application <module:variable>` flag to `steward deploy perimeter` that threads through to
  `render_daphne_unit`'s `_ASGI_APPLICATION_PLACEHOLDER` substitution, and confirm
  `render_edge_config`'s nginx assumptions (single upstream shape, `X-Forwarded-For` handling) hold
  for a non-Django ASGI app before Herald's webhook is ever pointed at it for real.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-6-1` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-6-a-ship-records-itself-end-to-end.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-13-6-2: `webhook_host.py`'s bounded timeout stops the client from waiting, but does not free the OS thread a genuinely-hung handler still occupies

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-6-a-ship-records-itself-end-to-end.md`
  summary: `webhook_host.py`'s `asyncio.wait_for` timeout bounds how long a caller waits for a
  response, but a handler that is truly hung (not merely slow) keeps its `ThreadPoolExecutor`
  worker occupied forever, since `Future.cancel()` cannot interrupt a thread already running --
  four such hangs would permanently exhaust the dedicated 4-worker pool for the life of the
  process.
  evidence: `_wrap`'s `app()` wraps `inner(scope, receive, tracking_send)` in
  `asyncio.wait_for(..., timeout=timeout_seconds)`; `inner` is `webhook.create_app`'s own `app()`,
  which dispatches the matched handler via `asyncio.to_thread` (an event-loop-owned coroutine
  wrapping a `concurrent.futures.Executor.submit`, per the stdlib implementation). Cancelling the
  *awaiting* coroutine when `wait_for` times out only detaches the ASGI response from that
  `Future` -- `Future.cancel()` is a documented no-op once the underlying work has actually started
  running on its worker thread (Python has no supported mechanism to force-terminate a running
  thread). This module's own regression test,
  `test_wrap_bounds_a_hanging_request_with_a_timeout`, hangs via `asyncio.sleep` specifically to
  stay fast and deterministic, and its own comment concedes the real-thread case is different --
  nothing in this story exercises a genuinely stuck OS thread. Currently inert, not exploitable:
  every job in `.github/workflows/herald-live-demo.yml` starts one throwaway daphne process, sends
  exactly one request, and tears the process down -- there is no multi-request, long-lived process
  for repeated hangs to accumulate against yet, since persistent hosting is out of this story's
  Surface (see `DW-FU-13-6-1`, immediately above). This becomes live risk the moment any future
  work stands up a persistent, multi-request `webhook_host.application` process. Fix candidates
  for whoever builds that: replace (not reuse) the dedicated executor after a timeout fires, so a
  stuck thread is abandoned rather than counted against future capacity (cheapest, does not
  reclaim the leaked thread itself); or move handler dispatch to a supervised subprocess pool that
  can actually be killed; or accept the residual and alert an operator on repeated timeouts rather
  than trying to reclaim the slot at all.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-6-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-6-a-ship-records-itself-end-to-end.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-14-1-1: A gate returning a non-JSON-serializable field value crashes `herald deck qa` with an unhandled `TypeError` instead of a controlled `HeraldError`

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-14-1-gate-report-interface.md`
  summary: A gate returning a non-JSON-serializable field value (e.g. a `Path` in `artifacts`,
  or a non-`Finding` item in `findings`) crashes `herald deck qa` with an unhandled `TypeError`
  instead of a controlled `HeraldError`, because `run()` validates a gate's `status`/`error`
  shape but not its field-level types.
  evidence: `_run_deck_qa`'s `operation()` (`cli.py`) does
  `print(json.dumps(deck_qa.to_dict(report)))` with no serialization-validating round trip on
  the way out. `deck_qa.run()`'s per-gate misbehavior check (added in this story's own review
  pass) validates `isinstance(result, GateResult)`, `result.status in _GATE_STATUSES`, and the
  `status`/`error` invariant, but does not deep-validate that every `findings` item is a
  `Finding` instance or that every `artifacts` item is a `str` -- Python dataclasses do not
  enforce field type hints at runtime, so a gate that (for example) forgets `str()` around a
  `pathlib.Path` when building `artifacts` produces a `GateResult` that passes every check
  `run()` currently makes. `dataclasses.asdict` then serializes the `Path` object as-is, and
  `json.dumps` raises `TypeError: Object of type PosixPath is not JSON serializable` inside
  `operation()`. That is a bare `TypeError`, not an `errors.HeraldError`, so `dispatch()`'s
  `except errors.HeraldError` never catches it -- it propagates as an unhandled exception with a
  full Python traceback, a materially worse failure mode than every other error path this module
  defines (a raising or malformed-status gate is isolated to a `status: "error"` report entry;
  this one takes down the whole CLI invocation). Currently inert: `DEFAULT_GATES` ships empty in
  this story, so no gate exists yet that could trigger it. This becomes live risk the moment
  Story 14.2 (headless-render, producing PNG paths for `artifacts`) or Story 14.3 (image-slot
  scan, producing `findings`) lands a real gate. Fix candidates: extend `run()`'s existing
  misbehavior check with field-level validation (`all(isinstance(a, str) for a in
  result.artifacts)`, `all(isinstance(f, Finding) for f in result.findings)`), treating a
  violation the same way as a bad `status` (an isolated `status: "error"` entry); or wrap the
  CLI's `json.dumps` call in a `try/except TypeError` that re-raises as `errors.HeraldError` so
  the failure is reported through the established AD-6 boundary instead of crashing raw.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-1` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-14-1-gate-report-interface.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-14-1-2: `deck_qa.run()` calls each gate synchronously with no timeout, so a hanging gate blocks the whole `herald deck qa` invocation indefinitely

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-14-1-gate-report-interface.md`
  summary: `deck_qa.run()` calls each gate function synchronously with no timeout, so a gate
  that hangs (e.g. a future headless-Chromium render gate stuck on a page load) blocks the whole
  `herald deck qa` invocation indefinitely with no recovery.
  evidence: `run()`'s per-gate loop is a plain `try: result = gate_fn(context) except Exception:
  ...` -- the `except` clause only ever fires once the call returns or raises; it does nothing
  for a call that simply never returns, and nothing in this story's gate-execution path wraps a
  gate call in a bounded executor or watchdog. Currently inert: `DEFAULT_GATES` ships empty in
  this story, so no gate exists yet that could hang. This becomes live risk specifically for
  Story 14.2 (`FR/AD: CAP-1`, headless Chromium driving per-slide `#/<n>` routes) -- browser
  automation is exactly the kind of I/O that can hang (a stuck page load, a crashed browser
  process producing no error at all). Not this story's own problem to solve -- Story 14.1 ships
  zero real gates, and its own spec explicitly scopes "no playwright/browser code in this story
  at all" -- but worth recording so Story 14.2's own spec/dev pass considers a bounded-timeout
  wrapper around its render gate's Chromium calls rather than discovering the hang live. Fix
  candidates for Story 14.2: run the render gate's browser interaction under a bounded timeout
  (e.g. a dedicated `ThreadPoolExecutor` + `.result(timeout=...)`, or playwright's own
  navigation-timeout options), converting a timeout into that gate's own `status: "error"` entry
  rather than hanging the whole report.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-1-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-14-1-gate-report-interface.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-14-2-1: No CI workflow runs `pyforge-herald`'s pytest suite, so the render gate's Chromium dependency is unprovisioned in CI

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-14-2-headless-render-gate.md`
  summary: No CI workflow runs `pyforge-herald-test` (or any equivalent
  `pytest src/shared/packages/pyforge-herald/tests`), so nothing in `.github/workflows/`
  provisions a Chromium binary for the render gate's real-browser tests, unlike the precedent
  already established for `pyforge-doctor`'s own Playwright-driven layout gate.
  evidence: grepped every `.github/workflows/*.yml` for `pyforge-herald-test`/`pytest.*herald`
  and found none; the only workflow referencing the `pyforge-herald` pixi env is
  `herald-live-demo.yml` (a live webhook demo, not a unit-test runner). `detectors.yml`'s
  `which google-chrome || which chromium || python -m playwright install --with-deps chromium`
  step is scoped to the `check_layout` job only. Pre-existing: this gap predates Story 14.2 (no
  CI job ran this package's test suite before this story either); the story's own render gate
  just makes the gap consequential for the first time, since it is the first `pyforge-herald`
  code to depend on a real Chromium binary at all.
  status: resolved
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/3 present (absent: .github/workflows/*.yml, _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-14-2-headless-render-gate.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

  verified: 2026-09-07 — resolved — CI/hygiene sweep added `.github/workflows/pyforge-station-tests.yml`'s `herald-test` job: runs `pixi run --frozen -e pyforge-herald pyforge-herald-test` on every PR touching `src/shared/packages/pyforge-herald/**`, with a "Verify a browser is present for the render gate" step (mirrors `detectors.yml`'s `check_layout` precedent: prefers ubuntu-latest's pre-installed google-chrome, falls back to `playwright install --with-deps chromium`). Confirmed locally first: full herald suite is 1254 passed / 4 skipped against this machine's own google-chrome. While auditing this gap, found it generalizes to atlas/mason/scribe/steward/warden too (only marshal and a doctor "scripts" subset had CI coverage before); the same workflow adds a job for each, gated on that station's own changed paths. Ledger status mapped to resolved.

  verified: 2026-09-09 — resolved — fleet-readiness pass (decision batch `fleet-readiness-decision-batch-2026-09-09.md`, row C11). This entry is the one the fix was written against and it names itself: `.github/workflows/pyforge-station-tests.yml` lines 3-4 open with "DW-14-2-1 (pyforge-herald deferred-work ledger): no CI workflow ran herald's own pytest suite -- its Chromium-dependent render gate had zero CI coverage", and its `herald-test` job (lines 160-182) runs `pixi run --frozen -e pyforge-herald pyforge-herald-test` behind a browser-presence step that falls back to `playwright install --with-deps chromium` (line 177), which is exactly the unprovisioned dependency this entry reported. Closed at HEAD `fe4025ea90`. Residual, still open and NOT closed by this stamp: `DW-FU-13-1` — the suite runs on `ubuntu-latest` only, so `locking.py`'s `msvcrt` branch still has no CI.

### DW-14-3-1: `image_slot_gate` has no duplicate-manifest-id disambiguation, unlike `render_gate`'s own `seen_ids` guard in the same file

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-14-3-image-slot-scan.md`
  summary: `image_slot_gate` resolves each manifest entry's fragment path directly from
  `_slide_id(entry, index)` with no `seen_ids`-style disambiguation, so two manifest entries
  that legitimately or malformedly share an id both read the same `fragments/<id>.html` file
  and, if it matches either placeholder pattern, both append a `Finding` with the identical
  `slide_id` -- a cosmetically duplicated report entry `render_gate` (same file, a few dozen
  lines above) already guards against for its own id-keyed writes.
  evidence: reviewed directly against the shipped code -- `render_gate` maintains a `seen_ids`
  set (seeded with `_RESERVED_SLIDE_IDS`) and appends `-{index}` to any id already seen before
  building a path from it; `image_slot_gate` has no equivalent, confirmed by reading its full
  body in `deck_qa.py`. Low consequence, not a correctness bug: `image_slot_gate` only reads
  files and appends `Finding`s (never writes/overwrites, unlike `render_gate`'s `rmtree`d PNG
  output), so the worst outcome is a redundant duplicate `Finding` for the same real defect,
  not data loss or a wrong verdict. Also structurally near-impossible against the real
  extractor: `extract-slides.mjs`'s `slugify(label, i)` always prefixes every generated id with
  its zero-padded slide index, so two entries can only collide if `manifest.json` is hand-edited
  outside the extractor's own contract (already an out-of-convention input per
  `presentation-deck.md`'s "do not hand-edit fragments"/generated-artifact discipline). Surfaced
  incidentally by this story's own adversarial review pass (both the Blind Hunter and Edge Case
  Hunter reviewers raised it independently); not fixed in this pass because the fix (porting
  `render_gate`'s `seen_ids` pattern) is a scope/consistency call, not a bug this story's own
  spec requires closing, and the real-world trigger condition does not occur under the
  extractor's actual invariants. Fix candidate: mirror `render_gate`'s `seen_ids` set +
  `-{index}` disambiguation suffix if/when this gate's id-handling is next touched.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-herald/implementation-artifacts/spec-14-3-image-slot-scan.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-1: No GitHub Actions workflow runs the pyforge-herald pytest suite at all.

- source_spec: `planning-artifacts/specs/spec-15-1-template-parse-then-fill-produces-a-genuinely-editable-deck.md`
  summary: No GitHub Actions workflow runs the pyforge-herald pytest suite at all.
  evidence: Surfaced incidentally by the verification-gap review while checking whether the round-trip test's `soffice` dependency is declared anywhere reviewable. Grepping .github/workflows/ turns up only herald-live-demo.yml, unrelated to the pytest suite; no workflow runs `pixi run -e pyforge-herald pyforge-herald-test`. Pre-existing -- every prior herald story's tests share the same gap, not introduced by this story.
  location: .github/workflows/
  origin: spec-deferred c2195376bfd1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: resolved

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

  verified: 2026-09-09 — resolved — fleet-readiness pass (decision batch `fleet-readiness-decision-batch-2026-09-09.md`, row C11). The claim is false at HEAD `fe4025ea90`: `.github/workflows/pyforge-station-tests.yml` carries a `herald-test` job (lines 160-182) that runs `pixi run --frozen -e pyforge-herald pyforge-herald-test`, preceded by a browser-presence step for the render gate (`playwright install --with-deps chromium` fallback, line 177) and a `setup-uv` step for the standalone skf validator. That workflow's own header (lines 3-4) names herald's ledger — `DW-14-2-1`, this entry's sibling — as its motivation, so the gap was closed deliberately and this entry simply never caught up. **Note on the prior stamp:** the 2026-09-02 mechanical re-verification recorded "source_spec path absent at HEAD" and re-marked the entry still-open without reading it. The path is present — `source_spec` is recorded relative to the PROJECT (`planning-artifacts/specs/spec-15-1-…md`) and the file exists at `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-15-1-template-parse-then-fill-produces-a-genuinely-editable-deck.md`; the verifier resolved it from the repo root. Every ledger entry using the project-relative `source_spec` form is exposed to the same false stamp — routed to doctor's sweep as batch row D5/C8 (HIGH), not fixed here.

### DW-FU-15-1-2: _resolve_layout silently resolves a name-based layout reference to the first match when a template has two layouts sharing the same name.

- source_spec: `planning-artifacts/specs/spec-15-1-template-parse-then-fill-produces-a-genuinely-editable-deck.md`
  summary: _resolve_layout silently resolves a name-based layout reference to the first match when a template has two layouts sharing the same name.
  evidence: Edge-case-hunter finding. The bundled default template has no duplicate layout names (verified: 11 distinct names), so this is unreachable with the current own-template decision. No obviously correct disambiguation exists without a design decision (error out? require index instead?), so deferring rather than guessing.
  location: src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_pipeline.py:_resolve_layout
  origin: spec-deferred c59d807c8f18 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

---

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-CANOPY-2026-08-24 — Canopy five-tier integration deferred to steward (Phase 5)

- source: `docs/dreams/pyforge-unifying-strategy.md` Phase 5; `sprint-change-proposal-2026-08-24-canopy.md`; `epics.md` § Canopy obligations (2026-08-24)
  summary: Herald Epics 1–15 are complete, but four of five Canopy tiers remain steward-owned under `spec-pyforge-unifying-strategy`. Herald must not mint Epics 16+ copying steward 18–30. Integration lands through steward **Epic 19** (portal at `/stations/herald/`, naming triple `django-herald` / `django_herald_<app>` / `herald_<app>`), **Epic 21** (`POST /stations/herald/mcp` on host ASGI + supervisor run state), **Epic 22** (`pyforge herald …` dispatch while `herald` CLI remains), and **Epic 29** (SKF skill compiled from `pyforge-herald` + Agent-Herald persona). Herald's static Moments dashboard stays framework-neutral (`spec-secure-live-dashboards` adopter; CAP-7 via `pyforge.steward.dashboard`; no Vizro). No second chrome, no extra public port, no `services/` FastAPI.
  evidence: Phase-5 `bmad-correct-course` run 2026-08-24 (headless-express). Peer pattern: marshal/steward `## Canopy obligations (2026-08-24)` blocks. Live pre-Canopy surfaces: `webhook_host.py` supports throwaway demo only (DW-13-6-1 — no steward perimeter ASGI target yet); fleet MCP servers blocked on open question `mcp-runtime-base` (unifying-strategy realization log 2026-08-24). Herald SPEC non-goal at `:137` (no console ownership) unchanged.
  status: open
  owner: pyforge-steward (Canopy build); pyforge-herald consumes at integration hooks only
  blocked_by:
    - steward:Epic 19 (eight portal shells under `/stations/<name>/`)
    - steward:Epic 21.4 (remaining MCP faces incl. herald)
    - steward:Epic 22 (unified `pyforge` CLI dispatch)
    - steward:Epic 29 (SKF domain skills + station personas)
  related: DW-13-6-1 (persistent webhook/perimeter hosting), `mcp-runtime-base`
  promoted: 2026-08-24 — Phase 5 correct-course for pyforge-herald

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): no source_spec; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-OM-2026-08-24 — Operating-model obligations (all eight stations)

- source_spec: cross-cutting (pyforge-unifying-strategy Grounding Q1–Q8; steward SCP operating-model, §6 revisited)
  summary: Estate OM + CAP-18: shared hook-spec in pyforge-core; Warden Epic 9 is the PR-gate retrofit; this station extracts one process hook spec (today's backend = default plugin).
  owner: station planning (this file) + steward (Canopy FRs) + warden (PR-gate hook specs)
  status: open
  recorded: 2026-08-24
  close_when: steward S-32.1 done; herald S-16.1 done (exporter plugins); no competing CI verdict

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1: No CI workflow runs the `pyforge-herald` pytest suite on Windows, so `locking.py`'s `msvcrt` branch — the platform this new module was explicitly widened beyond POSIX `fcntl` to support — has zero automated coverage.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md`
  summary: No CI workflow runs the `pyforge-herald` pytest suite on Windows, so `locking.py`'s `msvcrt` branch — the platform this new module was explicitly widened beyond POSIX `fcntl` to support — has zero automated coverage.
  evidence: Found by this story's own Blind Hunter review pass (pass 3). `.github/workflows/test-windows.yml`'s only `windows-2022` job builds conda recipes; every workflow that runs Python tests (`detectors.yml`, `test-macos.yml`) targets `ubuntu-latest`/`macos-*`. Out of this story's file surface (`state.py`/`progress.py`/`claims.py`/`notices.py`/`locking.py`/tests) — fixing it means adding a Windows Python-test CI job, a repo-wide workflow change with broader blast radius than this story's scope. Fix candidate: add a `pyforge-herald` pytest job to a `windows-2022` runner (mirroring `test-macos.yml`'s pattern) the next time Windows CI coverage is worked on.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-2: `deck_pipeline.py`'s caller-level read-network-write spans are still unprotected, so the story's own motivating scenario — two concurrent `herald deck pull <slug>` invocations for the same slug — can still silently drop one artifact's etag, even though `state.write` itself is now locked.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md`
  summary: `deck_pipeline.py`'s caller-level read-network-write spans are still unprotected, so the story's own motivating scenario — two concurrent `herald deck pull <slug>` invocations for the same slug — can still silently drop one artifact's etag, even though `state.write` itself is now locked.
  evidence: Found and reproduced by this story's Blind Hunter review pass (pass 5). `_record_pull_etag` (`deck_pipeline.py:471-497`) and `push_exports` (`:1339-1377`) build their replacement `etags` map from a `state.read` taken BEFORE the network pull/push, then hand the whole slug entry to `state.write`; Story 13.1's lock spans only `state.write`'s own load-through-replace, which cannot close a critical section that starts in its caller. Demonstrated: two concurrent pulls for slug `warden` (prototype 0.30s, marp 0.05s) leave `{'prototype': 'etag-A'}` — the marp etag is gone. `seed`'s duplicate-remote-project gate (`:199-206` check -> `:274` `create_project` -> `:290` `state.write`) is the same check-then-act shape and can leave an orphaned remote Design project. Out of this story's file surface (Code Map is `state.py`/`progress.py`/`claims.py`/`notices.py`/`locking.py`); `DW-1-4-2`'s closure note was narrowed in this story to say explicitly that it does NOT cover these caller-level spans. Fix candidate: hoist the lock into the caller (expose the `locked` contextmanager around a read+write pair) or give `state` a compare-and-set/patch-one-artifact entry point so the read and the write are one critical section.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-3: `notices._write_markdown` is a plain `write_text` (truncate-then-write), not the temp-file + `os.replace` used for the JSON index, so a concurrent READER of `notices/**/*.md` can still observe a partially written file even though writers are now serialized.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md`
  summary: `notices._write_markdown` is a plain `write_text` (truncate-then-write), not the temp-file + `os.replace` used for the JSON index, so a concurrent READER of `notices/**/*.md` can still observe a partially written file even though writers are now serialized.
  evidence: Found by this story's Blind Hunter review pass (pass 5). Story 13.1's lock makes the index write and the markdown write one critical section, which closes the writer-vs-writer race; it does not make a non-atomic write atomic, so `git add` during `herald deck pull --commit`, CI, or any external reader of the advertised "git-diffable record" can still catch a truncated file. The `notices.py` module docstring was amended in this story to state this limit explicitly rather than leave the unconditional claim standing. Out of scope here (`_write_markdown` predates this story and is not in its Code Map). Fix candidate: route `_write_markdown` through the same temp-file + `os.replace` helper the index write uses.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-4: `registry.register` performs the same unlocked whole-document read-modify-write that Story 13.1 fixed in the other four modules — it reads a README, splices its `§ Design project` span, and `os.replace`s it — and remains uncovered by the new lock.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md`
  summary: `registry.register` performs the same unlocked whole-document read-modify-write that Story 13.1 fixed in the other four modules — it reads a README, splices its `§ Design project` span, and `os.replace`s it — and remains uncovered by the new lock.
  evidence: Found by this story's Blind Hunter review pass (passes 4 and 5). `registry.py:154-156`'s own docstring still reads "mirrors `state.write`'s crash-safety pattern and its limit (no fsync; concurrent writers are not addressed)", unchanged by this story. Reachable via two concurrent `herald deck seed <slug>` invocations, which call both `state.write` (now locked) and `registry.register` (not). Deliberately out of scope: `registry.py` is absent from this story's Code Map and from `DW-1-4-2`'s named surface, and `locking.py`'s module docstring was amended in this story to say so explicitly rather than imply package-wide coverage. Fix candidate: wrap `register`'s read-splice-replace body in `locking.locked(locking.lock_path_for(readme_path))`.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-5: `claims.create` never checks the id it mints against the ids already stored, so a duplicate claim id can be written — and `revalidate_all` (which Story 13.1 taught to refuse duplicates structurally) then rejects the whole file on every subsequent run, while `revalidate`/`publish` silently operate on only the first match. Three functions disagree about what a duplicate id means.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md`
  summary: `claims.create` never checks the id it mints against the ids already stored, so a duplicate claim id can be written — and `revalidate_all` (which Story 13.1 taught to refuse duplicates structurally) then rejects the whole file on every subsequent run, while `revalidate`/`publish` silently operate on only the first match. Three functions disagree about what a duplicate id means.
  evidence: Found by this story's Blind Hunter and Edge Case Hunter review passes (pass 6) and reproduced: two `create(..., id_factory=lambda: "same")` calls both succeed, after which `revalidate_all` raises `HeraldError: ... holds duplicate claim ids; refusing to revalidate until they are unique` every time, with hand-editing `claims.json` as the only recovery. Only reachable through an injected `id_factory` (tests) or a hand-edited/merged `claims.json` — `create`'s default is uuid4 — so it is a latent consistency gap, not an active defect. Deliberately not fixed here: Story 13.1's contract is concurrency, and its Never-list forbids widening these functions' public surface; adding a refusal to `create` (or making `revalidate`/`publish` refuse symmetrically) is a new error contract on three public entry points, which belongs to whoever owns claims-storage integrity next. Fix candidate: have `create` check its minted id against the fresh in-lock read and re-mint or refuse, so the invariant `revalidate_all` now enforces is established where ids are created.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-6: `revalidate`/`revalidate_all`'s "leave the claim untouched" branches are invisible in the return value, so the CLI reports a completed validation — with a valid/broken count computed from evidence this run never checked — for a claim it actually skipped.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md`
  summary: `revalidate`/`revalidate_all`'s "leave the claim untouched" branches are invisible in the return value, so the CLI reports a completed validation — with a valid/broken count computed from evidence this run never checked — for a claim it actually skipped.
  evidence: Found by this story's Blind Hunter review pass (pass 7) and reproduced. `claims.revalidate` returns the unmodified `Claim` when every result was discarded (a concurrent writer replaced the evidence during the unlocked HTTP window) or when evidence appeared concurrently; `cli.py:1236-1241` then prints `revalidated claim {id}: {total-broken}/{total} evidence link(s) valid` derived from those stale `validated` flags, exit code 0 — a run that found a link valid can print `0/1 ... valid`. `cli.py:1234`'s `revalidated evidence for {len(updated)} claim(s)` counts skipped claims the same way. The skip branches are correct (stamping `updated_at` would assert a validation that never landed); what is missing is a way for the caller to tell "validated" from "skipped". Out of this story's file surface — `cli.py` is not in its Code Map, and signalling the skip means changing the return shape of two public functions, which this story's Never-list forbids. Fix candidate: return a small result object (or a parallel set of skipped ids) from `revalidate`/`revalidate_all` and have the CLI report skips distinctly, e.g. `skipped {id}: evidence changed during validation, re-run`.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-7: `revalidate_all`'s duplicate-claim-id guard is a verified behavior change against the pre-story baseline — a `claims.json` holding two same-id claims was revalidated correctly before Story 13.1 and is now refused outright — which diverges from the story's own "single writer, no contention: behavior unchanged" acceptance criterion.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md`
  summary: `revalidate_all`'s duplicate-claim-id guard is a verified behavior change against the pre-story baseline — a `claims.json` holding two same-id claims was revalidated correctly before Story 13.1 and is now refused outright — which diverges from the story's own "single writer, no contention: behavior unchanged" acceptance criterion.
  evidence: Found by this story's Blind Hunter review pass (pass 7) and reproduced against both revisions on the same file: baseline `revalidate_all` (a positional loop, `git show 98fbdf37f8:…/claims.py`) returned both claims validated; post-change `_require_unique_ids` raises `HeraldError: … holds duplicate claim ids; refusing to revalidate until they are unique` and writes nothing, blocking every other claim in the file too. The guard itself is right (it was added in pass 5 to stop one claim's HTTP outcome overwriting another's through the new id-keyed results map, and pass 6 extended it to the fresh in-lock read); the open question is whether a duplicate should refuse the batch, or leave only the same-id claims untouched the way a concurrently-created claim already is. Not resolved here because the coherent answer spans `create`/`revalidate`/`publish`/`revalidate_all` together — the same cross-function duplicate-id policy the pass-6 entry above defers for `create` — and any of the alternatives changes a public entry point's contract, which this story's Never-list forbids. Fix candidate: settle the duplicate-id policy once across all four functions, then align `revalidate_all` to it; treat this entry and the `claims.create` entry above as one decision.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-2: `herald snapshot` -- a single command consolidating the three currently-separate, mostly-unwired dashboard exporters (`scripts/export_web_snapshot.py`, `scripts/export_notices_snapshot.py`, `web/scripts/sync-progress.mjs`) into one, stamping `generated_at` on each -- should be built as near-term follow-up, not skipped: it would close the shipped v1's real "three hand-cranked snapshot hops" staleness risk (technical research risk #1 of 6). Worth prioritizing over routine low-priority ledger sweeps -- the fix candidate below is small and fully scoped, not exploratory.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-2-the-serverless-intermediate-decision-recorded.md`
  summary: `herald snapshot` -- a single command consolidating the three currently-separate, mostly-unwired dashboard exporters (`scripts/export_web_snapshot.py`, `scripts/export_notices_snapshot.py`, `web/scripts/sync-progress.mjs`) into one, stamping `generated_at` on each -- should be built as near-term follow-up, not skipped: it would close the shipped v1's real "three hand-cranked snapshot hops" staleness risk (technical research risk #1 of 6). Worth prioritizing over routine low-priority ledger sweeps -- the fix candidate below is small and fully scoped, not exploratory.
  evidence: `export_web_snapshot.py`'s own docstring (lines 3-8) already designs itself as the shared exporter and explicitly anticipates "a future Epic 8/10 snapshot adds a sibling export_*_snapshot function here rather than a duplicate script"; `export_notices_snapshot.py`'s docstring likewise says "a later story can fold all three into one generic... script once the shape each Moment needs is settled" -- deferred there deliberately (Simplicity First, YAGNI-until-second-confirmed-use), not because of architectural uncertainty. That uncertainty is now resolved: all three exporters exist, ship working output, and their shapes are individually stable (confirmed 2026-08-11) -- the deferred precondition ("once the shape... is settled") is met. This work is independent of Epic 13's DB/webhook/cron scope (LB-1/2/3): it would close a real risk in the CURRENTLY-SHIPPED v1 dashboard regardless of whether or when the live backend lands, so it is not gated on any Epic 13 story and does not need insertion into Epic 13's own numbering -- it is overdue Epics 9/10 follow-up (whose own Stories 9.4/10.5 shipped with a docstring explicitly deferring exactly this consolidation "to a later story"), not a claim that Epic 9 or 10 is reopened. Currently only `web/scripts/sync-progress.mjs` is wired into npm `predev`/`prebuild` (`web/package.json:8-11`); no snapshot JSON anywhere carries a `generated_at` field. Fix candidate: add `export_progress_snapshot`/`export_notices_snapshot` functions to `export_web_snapshot.py` alongside the existing `export_success_snapshot`, stamp `generated_at` in each, expose all three via one `herald snapshot` CLI subcommand (`cli.py`), and decide whether it supersedes or complements `sync-progress.mjs`'s npm-hook wiring.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/3 present (absent: _bmad-output/implementation-artifacts/spec-13-2-the-serverless-intermediate-decision-recorded.md, scripts/export_notices_snapshot.py, scripts/export_web_snapshot.py); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-2-2: `deferred-work.md` itself is written via an unlocked read-modify-write across a Tier-3 cross-worktree backlink -- the same lost-update race class Story 13.1 fixed for Herald's own `state`/`progress`/`claims`/`notices` stores, here in the BMAD governance tooling instead. Two concurrent `pyforge-herald` bmad-loop worktrees both appending to this file could silently drop one entry. Pre-existing, not introduced by this story; surfaced incidentally by review pass 3's Edge Case Hunter and re-confirmed still applicable by pass 5's.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-2-the-serverless-intermediate-decision-recorded.md`
  summary: `deferred-work.md` itself is written via an unlocked read-modify-write across a Tier-3 cross-worktree backlink -- the same lost-update race class Story 13.1 fixed for Herald's own `state`/`progress`/`claims`/`notices` stores, here in the BMAD governance tooling instead. Two concurrent `pyforge-herald` bmad-loop worktrees both appending to this file could silently drop one entry. Pre-existing, not introduced by this story; surfaced incidentally by review pass 3's Edge Case Hunter and re-confirmed still applicable by pass 5's.
  evidence: `deferred-work.md` resolves through this worktree's Tier-3 backlink symlink to a single shared file in the primary `local-recipes` checkout (`readlink -f` confirms), so it is NOT worktree-local the way tracked git files are -- every `bmad-loop` worktree for this project writing to it shares the identical file. Appends here (this story's own two entries included) are a plain read-append-write with no lock, sidecar, or advisory-file guard of any kind -- the exact pattern `locking.py` (Story 13.1) was built to replace for Herald's own stores. Currently latent (no second concurrent `pyforge-herald` worktree active at authoring time), not active. Fix candidate: extend `locking.locked()` (already stdlib-only, cross-platform, `fcntl`/`msvcrt`) to guard the Tier-3 backlink write path generically -- likely a bmad-loop tooling change (the backlink mechanism itself), not something scoped to any one project's `deferred-work.md`, since every project in this fleet's `_bmad-output/projects/*/` shares the identical pattern.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/implementation-artifacts/spec-13-2-the-serverless-intermediate-decision-recorded.md, _bmad-output/projects/*/); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-4-5: The webhook's HMAC scheme signs only the body, so one captured signed request stays a valid, reusable forgery token forever.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-4-the-webhook-endpoint-ci-calls.md`
  summary: The webhook's HMAC scheme signs only the body, so one captured signed request stays a valid, reusable forgery token forever.
  evidence: `webhook.verify_signature` computes `hmac.new(secret, raw_body, sha256)` over the raw body and nothing else -- no timestamp, no nonce, no delivery id enters the signed content -- exactly as spec-13-4's Boundaries & Constraints pins the scheme verbatim, so this is the pinned design's known boundary rather than a deviation from it. It is not a harmless replay, because neither handler is a pure function of the signed bytes: `handle_on_ship` computes `date` itself (`datetime.now(UTC)`), so replaying one captured body on a later day creates a SECOND progress row for that later date carrying the earlier day's numbers; `handle_on_pr_close` does the same whenever `shipped_date` is omitted from the payload. Reproduced by replaying one captured request against a frozen-then-advanced clock. Deferred rather than patched because closing it is a change to the signed-content contract, which needs the producer side to cooperate, and the producer -- the GitHub Actions workflow step -- is not written until Story 13.6; the endpoint is also not mounted or reachable anywhere today, so nothing is currently exposed. Fix candidates for whoever wires 13.6: sign a timestamp alongside the body (an `X-Hub-Timestamp` header folded into the HMAC input, rejected outside a few minutes' skew), and/or require the per-event `event_id` this pass added to `on-pr-close` on both routes and refuse an id already recorded.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-13-4-the-webhook-endpoint-ci-calls.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-4-6: The webhook's claim idempotency guard reads and creates in two separate transactions, so two concurrent deliveries of one event can both create a claim sharing one id.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-4-the-webhook-endpoint-ci-calls.md`
  summary: The webhook's claim idempotency guard reads and creates in two separate transactions, so two concurrent deliveries of one event can both create a claim sharing one id.
  evidence: `webhook.handle_on_pr_close`'s retry `attempt()` calls `claims.read_one(...)` and, on `ClaimNotFoundError`, `claims.create(...)` -- two independent `db.transaction` scopes with a window between them. Serially this is airtight (the guard is proven by `test_handle_on_pr_close_retry_is_idempotent_when_the_first_attempt_actually_committed` and, as of this review pass, across separate top-level calls too), but two deliveries in flight at once can both miss the read before either creates, and nothing downstream catches the result: `claims.id` is deliberately NOT a `PRIMARY KEY`/`UNIQUE` column (`db.py`'s own documented Story 13.3 choice, so duplicate-id detection stays application-level), so SQLite accepts both rows. Not reachable today -- the module is not mounted, and a single GitHub Actions workflow step delivers serially -- which is why it is deferred rather than patched; it becomes reachable the moment Story 13.6 mounts the callable in a host that serves requests concurrently. Fix candidates: hold one `db.transaction(claims_path)` across both the existence check and the insert, or give `claims.id` real schema-level uniqueness and treat the constraint violation as the idempotency signal -- the second reverses a deliberate Story 13.3 decision, so it is a storage-owner call, not this module's.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-13-4-the-webhook-endpoint-ci-calls.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-4-7: A single webhook request can occupy a thread-pool worker for well over a minute, and neither the handler nor the caller bounds it.

- source_spec: `_bmad-output/implementation-artifacts/spec-13-4-the-webhook-endpoint-ci-calls.md`
  summary: A single webhook request can occupy a thread-pool worker for well over a minute, and neither the handler nor the caller bounds it.
  evidence: `webhook.create_app`'s `app()` runs the matched handler via `asyncio.to_thread`, which keeps a slow call off the event-loop thread but does not bound its duration, and there is no `asyncio.wait_for` around it. The worst case is not the retry backoff (~3s of sleeping) but the storage waits inside it: `db._BUSY_TIMEOUT_MS` is 30000, so each of the 3 attempts can block up to 30s on SQLite's write lock -- roughly 93s of worker occupancy for one request. The default executor is `min(32, cpu + 4)` workers, so a burst arriving while another writer holds the lock (for instance `herald scheduler run`'s cron entry, Story 13.5) can exhaust the pool and stall every queued request. This review pass corrected the module docstring, which had claimed the hop bounded worker occupancy to "~3s", and added the real figure plus a pointer for whoever mounts this; the mitigation itself is deferred because a request timeout and a bounded, named executor are properties of the host wiring, which is Story 13.6's Surface, not this module's -- nothing is mounted or reachable today. Fix candidates: run handlers on a dedicated bounded executor and wrap the call in `asyncio.wait_for`, returning the same non-2xx the alert path already returns so CI's own delivery retry re-fires rather than the request hanging.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-13-4-the-webhook-endpoint-ci-calls.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-1: Never-caught false-done risk: the ledger-direction detector that would flag a done-but-unmerged sprint-ledger flip is not wired into detectors/detectors-ci.

- source_spec: `planning-artifacts/specs/spec-18-1-the-first-station-video-renders-from-heralds-studio.md`
  summary: Never-caught false-done risk: the ledger-direction detector that would flag a done-but-unmerged sprint-ledger flip is not wired into detectors/detectors-ci.
  evidence: pyforge.doctor.sources.ledger::gather_direction exists and is unit-tested for exactly this shape (a tracked ledger done key with no matching merge subject and no Tier-3 feed), but scripts/detectors.py's _DOCTOR_SOURCE_TASKS omits it and no pixi task exposes it, so neither detectors nor detectors-ci ever runs it. Pre-existing gap, not introduced by this story; wiring it in is a repo-wide fix beyond this story's scope.
  location: scripts/detectors.py (_DOCTOR_SOURCE_TASKS)
  origin: spec-deferred 8eb37210007a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — FIXED AND WIRED. `ledger-direction` is now in `scripts/detectors.py`'s `_DOCTOR_SOURCE_TASKS` with a `ledger-direction-check` pixi task. Wiring was blocked on a false-positive class this entry did not know about: judged on merge subjects alone the check reported **383 done-but-unmerged findings, 53% of all 724 done stories**, because `_merged_ids_for_project` only counted a GitHub merge whose branch started `<station>/`, and the fleet lands most work in batched `chore/`/`docs/`/`dispatch/`/`maintenance/` PRs whose subjects name no story. `ledger.py::_base_done_ids` now also consults the ledger as committed at `base_ref` -- authoritative, and still git-sourced, so FR-138 holds. Live count is 0 findings across 8 audited ledgers; proven non-vacuous by injecting a synthetic unmerged `done` key, which the check flagged. The FAIL half (landed-but-unpromoted) is unchanged and is what gates; done-but-unmerged stays WARN and never reds the run.

### DW-FU-18-3: Story 18.2 (sibling branch herald-r2a, not present in this branch's history) already rewrites the same "Utility skill routing (AD-2)" section this story appends to, into a numbered procedure -- landing both branches will need manual re-threading, not a mechanical git merge.

- source_spec: `planning-artifacts/specs/spec-18-3-slides-generator-is-herald-wielded.md`
  summary: Story 18.2 (sibling branch herald-r2a, not present in this branch's history) already rewrites the same "Utility skill routing (AD-2)" section this story appends to, into a numbered procedure -- landing both branches will need manual re-threading, not a mechanical git merge.
  evidence: Confirmed via `git show --stat` / `git log` against `origin/bmad/adoption-readiness-2026-09-06-herald-r2a` commit de771710fa (Story 18.2), which is not an ancestor of this branch: it replaces the pre-existing one-line "Herald wields `bmad-os-changelog`..." sentence in `.claude/skills/bmad-agent-herald/SKILL.md` with a multi-paragraph explanation plus a 4-step numbered procedure. This story's diff instead appends its new `slides-generator` paragraph directly after that soon-to-be-replaced one-liner. Out of this dispatch's own explicit scope (instructed not to touch herald-r2a) -- the orchestrating session that merges both branches into the integration branch needs to manually re-thread the slides-generator paragraph into 18.2's rewritten section rather than relying on a mechanical merge/rebase.
  location: .claude/skills/bmad-agent-herald/SKILL.md (## Utility skill routing (AD-2) section)
  origin: spec-deferred ffcb6aa1b4fd — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — The merge hazard was navigated; both branches landed and the section re-threaded correctly. `.claude/skills/bmad-agent-herald/SKILL.md:12-39` now carries Story 18.2's rewritten '## Utility skill routing (AD-2)' as a 4-step numbered procedure (the one-line 'Herald wields `bmad-os-changelog`...' sentence this entry warned would be replaced is gone), and 18.3's `slides-generator` paragraph sits intact at `SKILL.md:40`, AFTER that procedure rather than orphaned against a deleted anchor. Nothing was lost in the merge, so the manual re-threading this entry called for is complete and no longer owed.

### DW-FU-20-2: Real `pytest --collect-only -q` output is never parsed under test; only the plumbing around the stubbed `tests_collected` seam is verified.

- source_spec: `planning-artifacts/specs/spec-20-2-deck-facts-derives-a-per-deck-fact-ledger-and-checks-a-poster-against-it.md`
  summary: Real `pytest --collect-only -q` output is never parsed under test; only the plumbing around the stubbed `tests_collected` seam is verified.
  evidence: The suite stubs `tests_collected` wholesale, so the regex `(\d+)(?:/\d+)? tests? collected` and the reversed-line scan run only against synthetic strings. The row is opt-in (`--with-tests`) and present in none of the ten committed ledgers. Settle with a stubbed-`subprocess.run` test over captured real tails (plural, singular `1 test collected`, rc≠0 "N errors") when the first `--with-tests` ledger is committed (Wave A).
  location: scripts/deck_facts.py:tests_collected
  origin: spec-deferred 0b8723ed0e18 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium (unverified)
  promoted: 2026-09-14 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: closed

### DW-21-7-1: `wasm-analytics-stack`'s standalone infographic poster is corrupted at the source and the corruption was already pushed to the live Claude Design project before it was discovered

- source_spec: `_bmad-output/implementation-artifacts/spec-21-7-wasm-analytics-stack-rebuilt-to-the-standard.md`
  summary: `presentations/wasm-analytics-stack/project/Wasm Analytics Stack Infographic standalone.html` (145188 B, committed `e483288d5` "Rebuild the four chain-deck posters from their fact ledgers", 2026-09-15) has, from character offset 6344 through ~142980 of 145174, a boilerplate paragraph ("The factory already runs a tracked fleet: stories 930 of 998...") repeated 72 times with every character space-separated ("T h e   f a c t o r y..."), replacing real distinct section content across most of the poster. `deck-facts wasm-analytics-stack --check` reports 0 unmarked / 0 mismatch throughout — it validates only `data-fact` span presence/values, never prose sanity, so it cannot catch this class of defect. Story 21.7's push task ran before the corruption was known: the file was compared against Design (stale, an old 18713 B July stub), pushed via `McpTransport.finalize_plan`/`write_files`, and read back byte-identical — proving the corrupted bytes now live on the shared Design project too (etag `1789639734959225`), not merely at risk of it. Sibling Story 21.9 (`presenton-pixi-image`, PR #1405) independently found the identical pattern at the identical byte offset from the same root commit and withheld its own push before propagating it — this story's push had already completed by the time the pattern was recognized.
  evidence: Live measurement 2026-09-17: `text.count("T h e   f a c t o r y   a l r e a d y   r u n s") == 72` on both the local file and the Design-side `read_file` body at etag `1789639734959225`; first occurrence at char offset 6344 in both. The other 4 `project/` files (prototype, exec summary, infographic head, infographic deck) were checked for the same pattern and are clean. `git log --oneline -- <path>` confirms the corrupted content predates this story's session (introduced by `e483288d5`, before any push work started).
  location: `presentations/wasm-analytics-stack/project/Wasm Analytics Stack Infographic standalone.html`; live Design project `45c841c6-e807-4fee-a92a-f8e89cb890b4` (same file, etag `1789639734959225`)
  origin: found live during Story 21.7's push+read-back task, 2026-09-17
  severity: high — a real (if non-recipe) content-authoring defect now live in a shared external system, not just the repo
  promoted: 2026-09-17
  status: open

  Follow-up needed (not done here — the fix is content-authoring work, out of a push-only story's scope, and per repo convention needs its own Dream/Spec/Story, not a freelance fix): (1) regenerate the standalone's corrupted sections from `facts.yaml` without the duplication-and-space-injection bug; (2) re-push the corrected file to Design to overwrite the contaminated copy at project `45c841c6-e807-4fee-a92a-f8e89cb890b4`; (3) check `deckcraft` (21.8) and `unity-data-stack` (21.6) standalone posters for the same root-commit damage before their own push stories complete; (4) consider whether `deck-facts --check` needs a prose-sanity/repeated-block detector so this class of defect cannot recur silently.

### DW-21-7-2: `McpTransport.list_files` cannot parse the live `claude-design` server's current `list_files` answer shape

- source_spec: `_bmad-output/implementation-artifacts/spec-21-7-wasm-analytics-stack-rebuilt-to-the-standard.md`
  summary: The live `claude-design` MCP server's `list_files` tool answers with a bare JSON array of `{"path", "type"[, "size", "etag"]}` entries (directories included), not the `{"files": [...]}` object `McpTransport.list_files` (`mcp_transport.py:488`, via `_call_json`) expects, so `transport.list_files(...)` raises `TransportCallError("... returned list, expected an object")` on every live call today.
  evidence: Confirmed live against Design project `45c841c6-e807-4fee-a92a-f8e89cb890b4`, 2026-09-17: `transport._raw_text("list_files", {"project_id": ...})` returns `[{"path":"_ds","type":"directory"},...,{"path":"Wasm Analytics Stack.dc.html","type":"file","size":40573,"etag":"1785023174376282"},...]` — a bare array, `json.loads` of which is a `list`, not a `Mapping`, so `_call_json`'s `isinstance(payload, Mapping)` guard (`mcp_transport.py:572`) raises. The package's own unit tests (`test_mcp_transport.py:428-465`) assert the `{"files": [...]}` shape, so this is a real drift between the tests' assumed wire contract and the live server, not a test gap. Worked around in this story by parsing `_raw_text` directly and filtering `type == "file"`.
  location: `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py:488` (`McpTransport.list_files`); same shape presumably affects `AgentSdkTransport.list_files` too (not verified live this story)
  origin: found live during Story 21.7's push+read-back task, 2026-09-17
  severity: medium — blocks `herald deck status`/CAP-3 and any push workflow that pre-checks via `list_files` (Story 21.4's own precedent), across every deck, but every affected workflow has a working fallback (`read_file`-based compare, as used here)
  promoted: 2026-09-17
  status: open

  closed: 2026-09-14 — Closed with three tests that run a **real** `pytest --collect-only -q` over a throwaway package and parse its actual stdout, rather than the synthetic strings the suite had been asserting against: the plain `N tests collected` form, the `N/M tests collected` deselected form (pinning that `(?:/\d+)?` captures the SELECTED count, not the total), and the reversed-line scan, which matters because real stdout lists every node id before the summary and a forward scan could match a digit in an id. Deliberately NOT routed through `tests_command()`'s `pixi run -e pyforge-<station>`: that needs a provisioned station env and would make the tests skip on most machines — which is the same "only the plumbing is verified" hole this entry names. Mutation-verified rather than assumed: swapping the regex to `(\d+) items? collected` fails all three, and restoring passes all three, so they bite on the thing they claim to. `scripts/deck_facts.py` is byte-unchanged; this is pure verification of shipped behaviour, which is why it needed no Dream. Suite 45 -> 48 passed.

### DW-FU-21-10: presentations/presenton-pixi-image/README.md carries a garbled, truncated sentence fragment under its Provenance section, pre-existing and unrelated to the registry fix.

- source_spec: `planning-artifacts/specs/spec-21-10-the-registry-sees-all-fourteen-decks.md`
  summary: presentations/presenton-pixi-image/README.md carries a garbled, truncated sentence fragment under its Provenance section, pre-existing and unrelated to the registry fix.
  evidence: The line reads "**seeded 2026-07-25 via DesignSync (byte-exact localPath upload).dc.html`, `Infographic standalone.html`, - Infographic Deck.dc.html`). The `DesignSync` tool was not exposed..." -- a mangled sentence, present before this story touched the file and preserved verbatim under `### Provenance` per this story's own out-of-scope note (registry.read() never parses this span, so it does not block the registry fix). Confirmed unchanged by diffing against the pre-story revision.
  location: presentations/presenton-pixi-image/README.md:71
  origin: spec-deferred 2d5a465da45e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-18 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-21-2: `deck-trio --deck` refuses four of the ten PyForge posters (atlas, marshal, unifying-strategy, herald) because they do not carry the `<div class="act">`/`.lbl` vocabulary the intent-contract expects

- source_spec: `planning-artifacts/specs/spec-21-2-deck-trio-derives-the-infographic-deck-from-the-standalone.md`
  summary: `deck-trio --deck`, as the intent-contract specifies it, refuses four of the ten PyForge posters (atlas, marshal, unifying-strategy, herald) because they do not carry the `<div class="act">`/`.lbl` vocabulary the intent expects.
  evidence: Verified in the 2026-09-15 follow-up review pass by running the diff's own `_DeckStructure` plus `main()`'s refusal checks (read-only) over every `presentations/pyforge-*/project/*Infographic standalone.html`: doctor, genesis, mason, scribe, steward and warden derive cleanly (6 acts each, 22/27/22/22/22/31 sections, one-div wrapper chain); atlas parses 6 acts / 21 sections but every act label lives in `<span class="n">`/`<span class="t">` (all six `.lbl` empty, exit 2); marshal has 6 acts (`.n`/`.t`) and 0 `<section class="sec">` (its 19 sections are inline-styled); unifying-strategy has 7 acts (`.act-num`/`.act-title`) and 0 `.sec`; herald has 0 `.act` and 0 `.sec`. The refusals are the intent's own specified behavior (I/O rows "No act bands or no numbered sections" and "Empty act/section label" -> exit 2), so this is not a defect of the diff; it is pre-existing poster non-conformance relative to the vocabulary the intent chose. Note the standard's own tension: `infographic-standard.md`'s Authoring template instructs copying the reference markup, but these four posters predate that template's `.act`/`.lbl` convention.
  location: `scripts/deck_trio.py:_DeckStructure.handle_starttag` (cls == "act" / "sec" / "lbl") and `main()`'s four `--deck` refusals; `presentations/pyforge-{atlas,marshal,unifying-strategy,herald}/project/*Infographic standalone.html`
  origin: spec-deferred 73b1c596619a — hand-promoted from Tier-3 `implementation-artifacts/deferred-work.md` (`tier3-only-deferral` finding; original Tier-3 id `DW-4` renamed on promotion per `deferred_work_promote.py`'s own generic-id collision warning)
  severity: medium
  promoted: 2026-09-18 — hand-promoted from Tier-3 `implementation-artifacts/deferred-work.md`
  status: open

### DW-FU-21-3: `check()`'s discovery-notes stderr print (an ambiguous-suffix-match warning) is only exercised through `--refresh`'s notes-printing loop, never through a plain `--check`-only invocation

- source_spec: `planning-artifacts/specs/spec-21-3-deck-facts-refreshes-every-marked-surface-not-just-the-poster.md`
  summary: `check()`'s new discovery-notes stderr print (an ambiguous-suffix-match warning) is only exercised through `--refresh`'s own notes-printing loop in `main()`, never through a plain `--check`-only invocation.
  evidence: Verified by the Verification Gap review pass: replacing the `for note in notes: print(note, file=sys.stderr)` block inside `check()` (`scripts/deck_facts.py`) with `pass` and running the full suite left all 60 tests (at review time) passing — every `--check`-only test captures stdout only (`_check_lines`), never stderr, and no test combines an ambiguous multi-file surface with a `--check`-only invocation. The underlying ambiguity condition (two files matching one suffix glob) does not occur anywhere in the live fleet today, and the note is diagnostic-only (exit code is unaffected either way).
  location: `scripts/deck_facts.py:check()` (the `for note in notes: print(..., file=sys.stderr)` block) and `tests/scripts/test_deck_facts.py`
  origin: spec-deferred 7e7e91007646 — hand-promoted from Tier-3 `implementation-artifacts/deferred-work.md` (`tier3-only-deferral` finding; original Tier-3 id `DW-5` renamed on promotion per `deferred_work_promote.py`'s own generic-id collision warning)
  severity: low
  promoted: 2026-09-18 — hand-promoted from Tier-3 `implementation-artifacts/deferred-work.md`
  status: open

### DW-FU-23-1: sprint-status-ledger.yaml still reads `backlog` for this story's key even though implementation, verification and review are complete.

- source_spec: `planning-artifacts/specs/spec-23-1-the-account-is-enumerated-and-reconciled-against-the-registry.md`
  summary: sprint-status-ledger.yaml still reads `backlog` for this story's key even though implementation, verification and review are complete.
  evidence: This workflow's own step files never touch sprint-status-ledger.yaml -- that sync is owned by dedicated ledger-sync tooling run separately, not a hand-edit inside bmad-build-auto. A stale `backlog` row left against a story whose spec already reads `done` has previously caused indefinite redispatch in this repo (auto-memory: "Merged story + backlog ledger row respawns forever").
  location: _bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml (key 23-1-the-account-is-enumerated-and-reconciled-against-the-registry)
  origin: spec-deferred 410df0b002cb — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-18 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: done 2026-09-18

  verified: 2026-09-18 — RESOLVED by the landing itself. `marshal factory dispatch`'s land-finalize promoted the row (`7fd7a6f944 marshal: promote sprint-status ledger for 'pyforge-herald' (1 key(s) -> done)`, on origin/main 44 s after PR #1459 merged as `1dd017bc21 Merge pyforge-herald/23-1 into main`); the tracked ledger reads `done` for `23-1-the-account-is-enumerated-and-reconciled-against-the-registry`. The respawn the deferral feared did fire once inside that 44 s window (run pyforge-herald-20260918T151511146Z-3f6a3426, which correctly refused as already-merged) — a dispatch-supervisor race, not a ledger gap, and no work was duplicated.

### DW-FU-23-2: _windowed_read has no guard against a server that repeatedly returns a non-advancing last_line, which would loop forever.

- source_spec: `planning-artifacts/specs/spec-23-2-every-presentation-has-a-local-twin-design-systems-are-mirrored-as-libraries.md`
  summary: _windowed_read has no guard against a server that repeatedly returns a non-advancing last_line, which would loop forever.
  evidence: Edge Case Hunter review pass (2026-09-18): traced the pagination loop in src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py's _windowed_read -- it breaks only when window.last_line >= window.total_lines, with no check that last_line actually advanced between calls. Could not verify reachability: every live call against the real Design read_file MCP tool during this story paged forward correctly (confirmed pulling a 3377-line file and a 136293-byte file). What would settle it: observing the real API return a stalled/non-advancing window pair, which has never been seen.
  location: src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py:_windowed_read
  origin: spec-deferred dd34204da6b7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium (unverified)
  promoted: 2026-09-18 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: done 2026-09-18

  verified: 2026-09-18 — RESOLVED by Story 24.1 (spec-pyforge-herald CAP-48). `_windowed_read` (`deck_pipeline.py`) now tracks the previous window's `last_line` and raises the new `errors.PaginationStalledError` -- naming the file and the stalled line -- the moment a paged-for window's own `last_line` fails to advance past it, instead of looping forever. Evidence: `test_windowed_read_raises_pagination_stalled_error_on_a_non_advancing_window` (`tests/unit/test_deck_pipeline.py`) — a fake transport returning the same `(last_line=2773, total_lines=6000)` pair twice raises `PaginationStalledError` on the second window, matching on `big.dc.html` and both occurrences of the stalled line, after exactly 2 transport calls (never a third, never a loop). Both pre-existing live-shaped fixtures still pass unchanged: `test_windowed_read_reassembles_across_multiple_windows` / `test_windowed_read_strips_the_truncation_trailer_from_a_non_final_window` (the 3377-line pull) and `test_windowed_read_single_call_when_the_server_answers_whole` (the under-cap single-call shape the 136293-byte pull took) — full suite green via `pixi run --frozen -e pyforge-herald pyforge-herald-test`.

### DW-FU-23-5: No PR-gating CI lane runs docsite/build.py or site-check before merge, and this story's own mandated Verification command (pyforge-herald-test) has zero coverage of docsite/, so a regression in the family-page code (or the pre-existing dossier/gallery/artifact code) can merge to main with every gate green.

- source_spec: `planning-artifacts/specs/spec-23-5-the-family-is-browsable-and-downloadable-on-pages.md`
  summary: No PR-gating CI lane runs docsite/build.py or site-check before merge, and this story's own mandated Verification command (pyforge-herald-test) has zero coverage of docsite/, so a regression in the family-page code (or the pre-existing dossier/gallery/artifact code) can merge to main with every gate green.
  evidence: Verified 2026-09-18: grepped every `pull_request`-triggered workflow and `pr-preflight`'s dependency list in pixi.toml — none reference `docsite` or `site-check`. `dashboard.yml`, the only workflow that runs the build, triggers on `push: branches: [main]` only. No `docsite/tests/` directory or any test file anywhere imports `docsite/build.py`. This is pre-existing for the whole docsite pipeline (dossier/gallery/artifact already had zero PR-gating CI and zero unit tests before this story) — not introduced by this diff, so it is out of this story's scope to fix.
  location: pixi.toml (pr-preflight, feature.site.tasks.site-check), .github/workflows/dashboard.yml
  origin: spec-deferred 44bbdb936a4d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-18 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: done 2026-09-18

  verified: 2026-09-18 — RESOLVED by Story 24.2 (spec-pyforge-herald CAP-49). A new `pull_request`-triggered workflow, `.github/workflows/docsite-check.yml`, path-filtered to `docsite/**`, `docs/dashboard/**`, `presentations/**`, `pixi.toml` and its own workflow file, now runs two independent checks before merge: `docsite/build.py --check` with the same pip-installed deps `dashboard.yml` itself uses, and `pixi run -e site site-check` (the existing, reused task). `pixi.toml`'s `pr-preflight` gained the same `site-check` leg (`{ task = "site-check", environment = "site" }`) so a local run predicts the lane. Fixture-regression proof (2026-09-18, reverted after): inserting `{% raw %}{{ this_stays_unrendered }}{% endraw %}` into `docsite/templates/page_family.html.j2`'s rendered body made `docsite/build.py --check` fail with "unrendered Jinja delimiters in decks/<slug>/index.html" for all 10 registered deck families (exit 1); reverting made both `python docsite/build.py --check` and `pixi run -e site site-check` pass clean again (`checks passed — 7 required outputs, 10 infographics, 10 deck families`). `dashboard.yml` is unchanged and remains the only `deploy-pages` caller; `docs/how-to/presentation-deck.md`'s Acceptance criteria checklist names the new lane. The lane's first live GitHub Actions run: PR #1472, job `check` in workflow "Docsite check", https://github.com/rxm7706/local-recipes/actions/runs/35389603779 — SUCCESS in 26s. Full PR rollup also green: 22 SUCCESS / 4 SKIPPED (the gated platform-smoke lanes), `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN`, `maintenance` label applied (every file this PR touches is outside `recipes/`).

  SCOPE OF THIS CLOSURE — read before relying on it: this entry's own `summary` names TWO problems — (1) no PR-gating CI lane runs `docsite/build.py`/`site-check`, and (2) this story's own mandated Verification command (`pyforge-herald-test`) has zero coverage of `docsite/`. Only (1) is resolved above. (2) is still true after Story 24.2: `docsite-check.yml` runs `docsite/build.py --check` and `site-check` as separate CI steps, neither of which is `pyforge-herald-test` (the `pytest src/shared/packages/pyforge-herald/tests` suite), and no test file anywhere imports `docsite/build.py` — confirmed unchanged by this story. Tracked separately, not silently folded into this `done`: see DW-FU-24-2-1 below.

### DW-FU-24-2-1: `pyforge-herald-test` still has zero unit-test coverage of `docsite/build.py` — the new `docsite-check.yml` CI lane catches a broken build (unrendered Jinja, missing/shrunk assets) but nothing exercises `docsite/`'s own logic (e.g. `collect_families`, `collect_infographics`, the `check()` predicates themselves) under `pytest`.

- source_spec: `planning-artifacts/specs/spec-24-2-the-docsite-has-a-pr-gate.md`
  summary: `pyforge-herald-test` still has zero unit-test coverage of `docsite/build.py` — the new `docsite-check.yml` CI lane catches a broken build (unrendered Jinja, missing/shrunk assets) but nothing exercises `docsite/`'s own logic (e.g. `collect_families`, `collect_infographics`, the `check()` predicates themselves) under `pytest`.
  evidence: Split off DW-FU-23-5 2026-09-18 (review pass on Story 24.2): that entry's own `summary` named this as a second, distinct problem which Story 24.2's CI-lane fix does not touch — `docsite/` has no `tests/` directory, and `pyforge-herald-test` (`pytest src/shared/packages/pyforge-herald/tests`) never imports `docsite/build.py`. Out of Story 24.2's own Surface (`.github/workflows/`, `pixi.toml`, `docs/how-to/presentation-deck.md`, this ledger) — a real test suite for `docsite/build.py` is a separate, larger scoping question (unit-test-only vs. also exercising the Jinja render pipeline) that this story did not decompose.
  location: docsite/build.py; src/shared/packages/pyforge-herald/tests/
  origin: split from DW-FU-23-5, 2026-09-18
  severity: medium
  status: open

### DW-FU-23-6: The idempotency AC is proven over hand-written fakes and one live smoke test that only exercised the skipped path, never a real seeded deck's unchanged path.

- source_spec: `planning-artifacts/specs/spec-23-6-one-command-idempotent-reported.md`
  summary: The idempotency AC is proven over hand-written fakes and one live smoke test that only exercised the skipped path, never a real seeded deck's unchanged path.
  evidence: No live Claude Design credentials are available in this or any other automated dispatch environment. If the gap is real it would be medium: a verification-depth gap, not a code defect. It would be settled by running `herald deck sync-all` twice against a deck with live Design credentials and real tracked state.
  note: The proof command now exists (`HERALD_LIVE_SYNC_PROOF=1 pixi run -e pyforge-herald deck-sync-proof -- --slug <slug>`, Story 24.3). Still open -- no operator has run it and recorded the two reports yet; close this entry only when they have, citing the recorded run.
  location: src/shared/packages/pyforge-herald/src/pyforge/herald/sync_all.py
  origin: spec-deferred 9aa35103a2ee — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium (unverified)
  promoted: 2026-09-18 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: done
  verified: 2026-09-19 — resolved with a finding. The live proof ran twice on `pyforge-warden` (the only deck with pull etags; `pyforge-herald` has never been pulled and only reaches the skipped path). Record: `planning-artifacts/specs/spec-pyforge-herald/sync-proof-2026-09-19.md`. Both runs re-derived the stale deck, pushed both PPTX artifacts with identical read-back, and refused on the standalone HTML read-back — deterministically. The idempotent no-op path therefore stays unproven until DW-FU-23-6-1 is fixed; this entry's own gap (never run live) is closed.

### DW-FU-23-6-1: `deck sync-all` never publishes the standalone infographic HTML — the post-push read-back mismatches every time, so the push is refused (2/2 live runs, 2026-09-19)

- source_spec: `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/sync-proof-2026-09-19.md`
  summary: On `pyforge-warden` (the one deck with pull state) two consecutive live `deck sync-all` runs pushed both PPTX artifacts with byte-identical read-back but refused `pyforge-warden-infographic-standalone-2026-09-15.html` with "read-back after push did not match … refused rather than record an unproven push". Deterministic, so not a race: Claude Design most likely normalises HTML on write (whitespace, attribute order, injected support script), which a byte-equality read-back can never satisfy while `.pptx` does. Until fixed, sync-all can never reach the `unchanged` state for a deck with a standalone poster, and the poster is never re-published. Remedy candidates: a normalised comparison for HTML artifacts, or the Design-side content hash the API returns.
  evidence: `.herald/sync-proof/pyforge-warden/report-20260919T201122485002Z-8ae6ca61.json` and `…201203451643Z-6b319b4d.json` (`labels: ['failed']`, same `error`); `presentations/pyforge-warden/README.md` push-and-prove ledger 2026-09-19.
  location: src/shared/packages/pyforge-herald/src/pyforge/herald/sync_all.py
  severity: medium
  status: open
  raised: 2026-09-19 — Owner: herald. Found by the DW-FU-23-6 live proof.

### DW-herald-59-6: `chain_currency_sweep_check` reds pyforge-herald's `spec→prd` feeds edge — a direct, unavoidable side effect of steward Story 59.6's mandated spec-surface memlog reconcile, not a real staleness

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-59-6-shape-hygiene-roster-s-n-n-commits-status-comments.md`
  summary: `pixi run -e pyforge-guild detectors-ci` now reports `chain_currency_sweep_check` FAIL for pyforge-herald (`chain-audit-checkpoint-staleness`, `feeds` edge `spec→prd`, `staleBy: [{"stage":"spec","than":"prd","at":"2026-09-25T04:02","other":"2026-09-20"}]`). Cause: Story 59.6's own verification instructions required every co-governor `spec-surface` names for a governed-path edit to get a `.memlog.md` entry naming the path — `src/shared/packages/pyforge-herald/src/pyforge/herald/progress.py` (STATIONS re-export from `pyforge.core.roster`) is one such co-governed file, so `spec-pyforge-herald/.memlog.md` got a routine reconcile entry, which bumped its frontmatter `updated:` past the 2-day grace window against the PRD's `2026-09-20` date. Layers, coherence and orphan checkpoints all still pass; only staleness fails.
  evidence: doctor-sources output — `pixi run -e pyforge-guild python -m pyforge.doctor.sources chain-completeness --layers --project pyforge-herald --json` — the single `feeds`/`spec`/`prd` entry under `staleBy`; `pr-preflight` re-run after the fix confirmed this was the only new finding beyond the two findings already present on `main` before this branch (a `pixi_version_check` `ModuleNotFoundError`, and an `ad_citation_check` bare-capability citation in pyforge-doctor's memlog).
  location: _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md; _bmad-output/projects/pyforge-herald/planning-artifacts/prd.md
  origin: caused by steward Story 59.6's own mandatory spec-surface reconcile step, 2026-09-25
  severity: low
  status: open
  note: The proper remedy per `_bmad-output/projects/pyforge-doctor/CHAIN-CURRENCY-RUNBOOK.md` is a full per-station cascade (brief→PRD→arch→epics, one commit) — explicitly its own separate, event-driven workflow with its own dispatch discipline ("one agent per station cascade"), not a Story 59.6 concern ("Scoped to Story 59.6 ONLY, not sibling stories in Epic 59"). Left open for a dedicated chain-currency-sweep dispatch against pyforge-herald rather than faked/stamped here — the runbook itself forbids a stamp without a genuine reconcile.
