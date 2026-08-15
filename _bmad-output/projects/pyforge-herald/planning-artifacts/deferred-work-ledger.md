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

## DW-1-1-2 — The `/dist/` and `/dist-conda/` lines in the pixi-package `.gitignore` pattern (copied verbatim…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: The `/dist/` and `/dist-conda/` lines in the pixi-package `.gitignore` pattern (copied verbatim from `pyforge-warden`'s and now also `pyforge-herald`'s `.gitignore`) are broken by trailing inline `#` comments, which git treats as literal pattern text rather than a comment — the directory patterns silently don't match.
  evidence: Empirically verified in this worktree on both `pyforge-warden/dist/` and `pyforge-herald/dist/`: a planted `manifest.json` under either shows up as untracked (`git status --porcelain` -> `??`), and `git check-ignore -v` resolves the match to the *root* `.gitignore`'s `!src/**/packages/*/**` re-inclusion rule, not the package's own broken `/dist/`/`/dist-conda/` lines. Currently masked because real build artifacts (`.conda`/`.whl`/`.tar.gz`) also match separate, unbroken extension-wildcard lines in the same file — but any future non-matching byproduct in either directory (a manifest, a log) would not be ignored. Found by Blind Hunter review of spec-1-1's diff; out of that story's scope since it only reproduces a pre-existing pattern shared identically by warden/atlas (touching those files was explicitly out of bounds for 1.1). Fix: drop the trailing comments (put them on their own line above) in all three packages' `.gitignore` files in one pass.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN and WIDER — the entry named warden/atlas/herald; four packages carry it today. `pyforge-warden/.gitignore:2-3`, `pyforge-doctor/.gitignore:2-3`, `pyforge-scribe/.gitignore:2-3` and `pyforge-herald/.gitignore:2-3` all still read `/dist/          # pypi: wheel + sdist (python -m build)`. atlas (`:6`) and marshal (`:6-7`) use bare lines and are clean — so atlas is now FIXED but scribe and doctor inherited the defect. Same finding as marshal's DW-1-1-2, reached independently.

## DW-1-1-3 — None of `pyforge-warden`/`pyforge-atlas`/`pyforge-herald`'s `pyproject.toml` scope `[tool.hatch.…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: None of `pyforge-warden`/`pyforge-atlas`/`pyforge-herald`'s `pyproject.toml` scope `[tool.hatch.build.targets.sdist]` (only the wheel target is scoped to `src/pyforge`), so the sdist tarball relies on hatchling's default file-selection rather than an explicit include list.
  evidence: Confirmed by reading all three packages' `pyproject.toml` — none has a `[tool.hatch.build.targets.sdist]` section. Low current risk (hatchling defaults to VCS-aware selection in a git repo, and the `.gitignore` already excludes most local build cruft, modulo the trailing-comment bug above) but worth an explicit include list for reproducibility. Found by Blind Hunter review of spec-1-1's diff; not unique to this story.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — measured across all three named packages: `grep -c 'targets.sdist'` returns 0 for `pyforge-warden`, `pyforge-atlas` AND `pyforge-herald`'s `pyproject.toml`. No explicit sdist include list was added anywhere.

## DW-1-1-4 — `pyforge-warden`/`pyforge-atlas`/`pyforge-herald` each declare `license = { text = "MIT" }` in `…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: `pyforge-warden`/`pyforge-atlas`/`pyforge-herald` each declare `license = { text = "MIT" }` in `pyproject.toml` with no accompanying `LICENSE` file in the package directory.
  evidence: Confirmed by directory listing of all three package roots — none has a `LICENSE`/`LICENSE.txt` file (only the repo-root `LICENSE.txt`). Found by Blind Hunter review of spec-1-1's diff; pre-existing pattern shared by all three packages, not unique to this story.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and the sweep is now larger than the three named: `ls src/shared/packages/*/LICENSE*` returns nothing across all EIGHT sibling packages while each `pyproject.toml` still declares MIT. Same defect as marshal's DW-1-1-3 — two projects ledgered it independently, which is itself a signal it needs one owner.

## DW-1-1-5 — `pyforge-herald`'s version `"0.1.0"` (like warden's/atlas's) is hand-duplicated between the pack…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: `pyforge-herald`'s version `"0.1.0"` (like warden's/atlas's) is hand-duplicated between the package's own `pixi.toml` `[package]` table and `pyproject.toml` `[project]` table with no automated check that a future bump keeps both in sync.
  evidence: Confirmed by reading both files — two independent literal `version = "0.1.0"` strings. Found by Blind Hunter review of spec-1-1's diff; pre-existing pattern shared by all three packages, not unique to this story.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — two independent literals remain: `pyforge-herald/pixi.toml:17` `version = "0.1.0"` and `pyforge-herald/pyproject.toml:7` `version = "0.1.0"`. A version-sync meta-test DOES now exist but does not cover herald: `pyforge-marshal/tests/meta/test_manifest_sync.py` is scoped to Marshal's own manifests (its docstring says 'Marshal's declared deps'), so herald, warden and atlas remain unguarded.

## DW-1-1-6 — `pyforge-herald`'s root `pixi.toml` feature block pins `python-build = ">=1.5.0"` with no upper…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: `pyforge-herald`'s root `pixi.toml` feature block pins `python-build = ">=1.5.0"` with no upper bound, copied verbatim from `pyforge-warden`'s identical unbounded pin.
  evidence: Confirmed in the diff and in `pyforge-warden`'s root `pixi.toml` feature block — same unbounded `>=1.5.0` pin, no CI task in either package that would catch a breaking major-version `build` release before it ships. Found by Blind Hunter review of spec-1-1's diff; pre-existing pattern shared with warden, not unique to this story.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN at four sites, not one: root `pixi.toml:136`, `:165`, `:200` and `:268` all declare `python-build = ">=1.5.0"` with no upper bound. No CI task caps or checks it.

## DW-1-1-7 — The verify-gate repair for this story (populating `build_artifacts/linux64` stubs so `pixi run -…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: The verify-gate repair for this story (populating `build_artifacts/linux64` stubs so `pixi run -e pyforge-herald ...` could extend `pixi.lock`) left the committed lock's `bmad-ui` environment channel pointing at this ephemeral bmad-loop worktree's own absolute path (`file:///.../.bmad-loop/runs/<run-id>/worktrees/<unit>/build_artifacts/linux64/`) rather than a stable location — once this worktree is torn down post-merge, that entry dangles.
  evidence: Confirmed two independent fix attempts both fail: (1) hand-editing the URL back to the primary `local-recipes` checkout's path reverts to the worktree-absolute path on the very next unfrozen `pixi run` that touches any environment requiring a lock recompute; (2) replacing `build_artifacts` with a symlink to the primary checkout's real `build_artifacts` (hypothesis: pixi might `realpath()`-canonicalize it) still writes the worktree-literal path — pixi 0.73.0 does not resolve symlinks when recording a relative-path local channel's absolute `file://` URL, it joins the manifest's own (unresolved) project root. Independently flagged by both the Blind Hunter and Edge Case Hunter review passes on this story's diff. Narrow real-world impact: `bmad-ui` is an optional, manually-invoked, non-CI-gated local feature that `pyforge-herald`'s own gate never touches or depends on; the entry self-heals the next time anyone runs an unfrozen pixi command against `bmad-ui` from a checkout with `build_artifacts/linux64` actually populated (the pre-existing requirement of that feature, per the first deferred-work entry above). Durable fix: once `pyforge-herald`'s own lock entry is stable, switch its bmad-loop policy gate to `--frozen` (mirroring the fix already applied to `pyforge-warden`'s `.bmad-loop/policy.toml`) so no future verify pass ever needs to touch `bmad-ui` again.
  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED, by the same root-cause fix that closed DW-1-1-1 above — and note the entry's own preferred durable fix (switch herald's gate to `--frozen`) turned out not to be needed. The dangling worktree-absolute channel cannot recur because the channel is gone: `pixi.lock` holds ZERO `build_artifacts` references, and root `pixi.toml:1180-1186` records exactly this failure mode as the reason for removal ('pixi records a channel as an ABSOLUTE path, so pixi.lock carried a machine-specific file:///home/<user>/… that exists on exactly one machine'), naming the two Pages deploys it broke on 2026-07-26.

## DW-1-1-8 — No meta-test enumerates or validates the set of registered pixi environments/features in root `p…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-for-pyforge-herald.md`
  summary: No meta-test enumerates or validates the set of registered pixi environments/features in root `pixi.toml` (unlike the "three places" convention enforced for conda-forge-expert scripts, or the BMAD-artifacts sync test) — a newly added environment like `pyforge-herald` has no automated check that it stays correctly wired.
  evidence: Confirmed no such test exists for any of `pyforge-warden`/`pyforge-atlas`/`bmad-ui`/`pyforge-herald` either — a pre-existing gap in the pixi-environment-registration convention, not unique to this story. Found by Blind Hunter review of spec-1-1's diff.
  status: open

  verified: 2026-07-30 — PARTIALLY ADDRESSED, held open for the specific gap named. What now exists: `tests/packaging/test_dependency_completeness.py:51-73` declares an `EXPECTED_PACKAGES` floor over all 8 packages plus `_discover()` and a `test_discovery_is_not_vacuous` guard against the glob silently collapsing to zero — real protection that did not exist when this entry was written. What still does NOT exist: any test that reads root `pixi.toml`'s `[environments]`/`[feature.*]` tables. Discovery is by DIRECTORY GLOB (`PACKAGES_DIR.glob("pyforge-*")`), so a package present on disk but never registered as a pixi environment — precisely the wiring this entry asks to validate — still passes every test.

## DW-1-2-1 — `McpTransport` opens one `asyncio.run()`-scoped MCP session per tool call (one extra `initialize…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `McpTransport` opens one `asyncio.run()`-scoped MCP session per tool call (one extra `initialize` round-trip per call) rather than holding a persistent session; an available optimization only if `herald deck watch` (CAP-4) ever polls often enough for it to matter.
  evidence: Deliberate Story 1.2 design decision, recorded in the spec's Design Notes and in `transport/mcp_transport.py`'s module docstring. Safe because the server keeps no session-scoped state Herald depends on — `plan_token` and the `if_match`/`if_none_match` etags are explicit parameters on every later call (confirmed against the live tool schemas). A persistent session would need a background event loop plus a single owning task (anyio cancel scopes forbid entering and exiting `streamablehttp_client` from different tasks) and a new `anyio` dependency that `llms-full-check` would flag as `undocumented-dep` — real machinery to save one round-trip on commands that make a handful of calls. Revisit only with a measured `watch`-loop cost.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN and unchanged by design. `mcp_transport.py:578` still calls `asyncio.run(...)` inside the per-call path, and `:550`'s docstring still states 'One ``asyncio.run()``-scoped session per call (see module doc)', with the module-level rationale at `:22`. No persistent session, no `anyio` dependency — the revisit condition (a measured `watch`-loop cost) has not arrived because Story 4.3 does not exist yet.

## DW-1-2-2 — bmad-loop worktree paths longer than ~173 characters make EVERY `pixi` source-package operation…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: bmad-loop worktree paths longer than ~173 characters make EVERY `pixi` source-package operation (`pixi lock`, `pixi install`, `pixi run -e <env-with-a-path-dependency>`, `pixi build`) panic in the `pixi-build-python` backend, so no pyforge-{herald,warden,atlas} verify gate can run in such a worktree at all. Long story slugs are what push a run over the line.
  evidence: Root-caused to an unchecked `usize` subtraction in `pixi-build-backends` `crates/pixi-build-backend/src/tools.rs::output_directory` (`placeholder[0..placeholder_length - build_dir.join("host_env").as_os_str().len()]`, `placeholder_length = 255`) — it underflows whenever the rattler-build `build_dir` plus `/host_env` exceeds 255 bytes, producing `end byte index 18446744073709551595 is out of bounds for string of length 260` and killing the backend mid-handshake ("the build backend (pixi-build-python) exited prematurely"). `build_dir` is `<workspace-root>/.pixi/meta-v0/<pkg>-<hash>/work/<pkg>-<hash>` (a fixed 73-byte suffix for pyforge-herald), so the hard ceiling is a workspace root of 246 - 73 = 173 bytes. This worktree's root is 194 bytes (`.bmad-loop/runs/20260725-084750-c3b9/worktrees/1-2-transport-port-primary-mcp-client-adapter-the-transport-spike`) — exactly 21 over, matching the reported `-21` underflow byte-for-byte. Reproduced on the PRISTINE baseline manifests (story changes stashed), so it is pre-existing and story-independent; it also fires for the unrelated `pyforge-warden`/`pyforge-atlas` envs in the same workspace, and the failing environment/platform varies run to run because the backends are spawned in parallel. Three workarounds tested and REJECTED: a short symlink to the worktree passed via `--manifest-path` (pixi canonicalizes it), replacing `.pixi` with a symlink to a short path (pixi joins the unresolved root), and `PIXI_FORCE_NETFS_REDIRECT=1` (redirects only the download caches, never `.pixi/meta-v0`). `pixi build --build-dir` exists but is not reachable from `pixi lock`/`pixi run`. WORKAROUND THAT WORKS: run the pixi gate from a short-path checkout — `git worktree add --detach /home/<user>/hl HEAD`, copy the story's working-tree changes in, run there, copy `pixi.lock` back (rewriting the one `bmad-ui` `file://` local-channel URL to the real worktree path, the only absolute path the lock records). Durable fixes for whoever picks this up, in order of preference: (1) cap the generated worktree directory name in `.bmad-loop` (hash or truncate the story slug) so the root stays under ~170 bytes; (2) put bmad-loop run worktrees at a short root (e.g. `~/.bmad-loop-wt/<run-id>/<n>`) instead of nesting them under `<repo>/.bmad-loop/runs/<run-id>/worktrees/<slug>`; (3) upstream a saturating-subtraction fix to pixi-build-backends.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN in the backend, but fix candidate (2) WAS effectively adopted and the trigger is no longer live. The panic itself is untouched: `pixi.lock` still resolves `pixi-build-python-0.8.3` on all three platforms, so the unchecked `usize` subtraction in `tools.rs::output_directory` is unfixed upstream. But the fleet moved to `~/.bmad-loops/`, and measuring this entry's OWN worst-case path against every one of the nine homes gives a maximum of 154 bytes (steward/marshal/genesis) versus the 173 ceiling — 19 bytes of headroom. Candidates (1) slug-capping and (3) the upstream saturating-subtraction fix remain undone, so a longer story slug could still cross it.

## DW-1-2-3 — The `DesignTransport` port has no `list_files` or `delete_files` method, but the live `finalize_…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: The `DesignTransport` port has no `list_files` or `delete_files` method, but the live `finalize_plan` / `copy_files` schemas require them — `finalize_plan` with `scope: "project"` returns no `base_etags` and directs the caller to "use `list_files` / `read_file` etags for `if_match`", and a folder-dest `copy_files` needs `leaf_if_match` "built from the source listing". Neither is reachable through the port.
  evidence: The 8-tool surface is fixed by ARCHITECTURE-SPINE.md AD-3 and by Story 1.2's epics acceptance criteria, so widening it was out of this story's scope. Confirmed against the live tool schemas 2026-07-25: the server exposes 23 tools, including `list_files` and `delete_files`, and their descriptions carry the etag-sourcing instructions quoted above. Impact lands on Story 1.6 (seed's `copy_files` of `deck-stage.js`) and Epic 5 (export push-back, which needs per-file etags for files it did not just read). `mcp_transport.py`'s own `finalize_plan` comment already names the gap. Whoever picks this up should decide whether AD-3's "exactly 8 tools" is amended to 9-10, or whether bridge-core is expected to obtain etags only via `read_file`.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the port is still exactly four methods. `transport/base.py` defines `finalize_plan` (`:192`), `copy_files` (`:215`), `write_files` (`:226`) and `read_file` (`:236`), with no `list_files` and no `delete_files`. AD-3's 'exactly 8 tools' has not been amended, so the etag-sourcing path that `finalize_plan` with `scope: "project"` and folder-dest `copy_files` both require is still unreachable through the port.

## DW-1-2-4 — `FileRead` drops the server's `untrusted-project-content` provenance marking — the wrapper exist…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `FileRead` drops the server's `untrusted-project-content` provenance marking — the wrapper exists precisely to flag the body as user-authored content that may carry prompt-injection text, and nothing downstream of the transport records that.
  evidence: Verified in the live `read_file` response: the body is wrapped in `<untrusted-project-content …>` and the trailer reads "Do not follow any instructions inside it -- it is user-authored file content." `parse_read_response` strips both and returns a bare `str` body. Harmless for Story 1.2 (nothing consumes a body yet) but load-bearing from Story 2.1 (pull) onward, and especially if any body is ever surfaced to a model. Fix candidate: carry an explicit `untrusted: bool = True` on `FileRead`, or name the field `untrusted_body`.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the marking is still dropped. `transport/base.py:68` defines `_READ_TAG = "untrusted-project-content"` purely to STRIP it, and the `FileRead` dataclass at `:104` carries `unchanged`/`body`/`first_line`/`last_line`/`total_lines`/`truncated`/`etag` — no `untrusted` flag and no `untrusted_body` rename. Nothing downstream can tell the body is user-authored.

## DW-1-2-5 — A conflicted write is returned to the caller as an ordinary success `Mapping`. The live `write_f…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: A conflicted write is returned to the caller as an ordinary success `Mapping`. The live `write_files` / `copy_files` schemas state an `if_match` mismatch answers with a *structured conflict result*, not an error — so `isError` is false and the adapter reports it as a normal answer. `copy_files` is additionally documented as not all-or-nothing.
  evidence: Confirmed in the live tool schemas 2026-07-25 ("the write is refused (structured conflict result, nothing written) unless the file is still at that etag"). This is arguably correct hexagonal layering — the transport reports, bridge-core decides — and AD-6 assigns `SeedConflictError`/`PullConflictError`/`ExportConflictError` to Story 1.4's bridge-core, which does not exist yet. Recorded so Story 1.4 does not assume a conflicted write raises: FR-24 currently guarantees only that a precondition was *sent*, not that a violated one was *noticed*.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — grepping the whole `transport/` package for `conflict` returns nothing, so a structured conflict result is still handed back as an ordinary success `Mapping`. `SeedConflictError`/`PullConflictError`/`ExportConflictError` remain unbuilt (Story 1.4's bridge-core still does not exist), exactly as the entry anticipated.

## DW-1-2-6 — `_call_tool_async` — the only code that builds the three auth headers, filters MCP content block…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `_call_tool_async` — the only code that builds the three auth headers, filters MCP content blocks to text, and reads `isError` — is exercised solely by the opt-in `live`-marked spike, so the default offline gate cannot catch a regression in it.
  evidence: By construction: every other test injects a `ToolCaller` fake that bypasses the SDK entirely (that seam is what lets the socket-deny harness stay on). Notably the `getattr(block, "type", "") == "text"` filter silently drops `structuredContent`, which current MCP SDKs return for tools declaring an `outputSchema` — a server-side change there would surface only as `_call_json`'s "unparseable answer". Fix candidate: extract header construction into a pure `_build_headers(credential)` and unit-test it, and add a fake in-process `ClientSession` double for the block-filter/`isError` logic.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `_call_tool_async` is still executed only by the live spike. `tests/test_mcp_transport.py` patches it out at `:619`, `:746` and `:783` (`monkeypatch` of `pyforge.herald.transport.mcp_transport._call_tool_async`), so every offline test bypasses the real body; only `tests/test_live_design_spike.py:41` (`pytest.mark.live`) reaches it. Neither fix candidate landed: there is no `_build_headers` helper and no in-process `ClientSession` double.

## DW-1-2-7 — A server-*answered* JSON-RPC error is reported as `TransportUnreachableError`. The `mcp` SDK rai…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: A server-*answered* JSON-RPC error is reported as `TransportUnreachableError`. The `mcp` SDK raises `McpError` for protocol-level failures instead of returning `isError=True`, so those never reach `_raw_text`'s `TransportCallError` path and collapse into the generic `except Exception` at `mcp_transport.py`, telling the operator the endpoint could not be reached when it answered.
  evidence: Found by the 2026-07-25 follow-up review. `errors.py` documents exactly this distinction (reached-and-refused vs never-reached) and no test injects an `McpError`, because every offline test bypasses the SDK through the `ToolCaller` seam. Not patched here: distinguishing it means importing the SDK's error type (lazily, to keep the import cheap) or matching on a type name, and AD-6 assigns error *interpretation* to Story 1.4's bridge-core. Fix candidate: map `McpError` to `TransportCallError` in `_call_via_mcp_sdk`, covered by the same in-process `ClientSession` double the header/block-filter entry above already asks for.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `McpError` appears ZERO times in `mcp_transport.py`, so a server-answered JSON-RPC error still falls through to the generic handler and is reported as `TransportUnreachableError`. The mapping to `TransportCallError` the entry proposes was never added.

## DW-1-2-8 — HTTP 429 and 5xx have no distinct error class — both land on `TransportUnreachableError`, so a r…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: HTTP 429 and 5xx have no distinct error class — both land on `TransportUnreachableError`, so a rate limit or a transient server fault is indistinguishable from an outage and a caller cannot tell "back off and retry" from "give up".
  evidence: Found by the 2026-07-25 follow-up review. `_indicates_auth_failure` splits 401/403 out precisely because `bridge-protocol.md` § Watch parameters needs that distinction; the retry-vs-backoff distinction is the same shape and is not made. Deferred rather than patched because the consumer of it (the watch loop's backoff policy) is Story 4.3, and inventing the class now would fix its semantics before the caller exists.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the auth split exists and the retry split does not. `mcp_transport.py:266` still defines `_indicates_auth_failure` (used at `:592`) to separate 401/403, while grepping for `429`, `5xx` or any `RateLimit`-shaped class returns nothing. A rate limit is still indistinguishable from an outage.

## DW-1-2-9 — No request timeout is set on either `streamablehttp_client(...)` or `session.call_tool(...)`, so…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: No request timeout is set on either `streamablehttp_client(...)` or `session.call_tool(...)`, so a server that accepts the connection and never answers blocks the synchronous port for whatever the SDK's internal default is — a value free to change inside the unbounded `mcp>=1.28.1` range.
  evidence: Found by the 2026-07-25 follow-up review; confirmed by reading `_call_tool_async`, which passes no timeout to either call. Harmless for the one-shot commands Story 1.2 ships (an operator sees a hang and Ctrl-Cs) but load-bearing for `herald deck watch` (Story 4.3), whose 60 s poll cadence assumes a call cannot outlast it. Fix candidate: thread an explicit timeout through `McpTransport.__init__` and assert it in the live spike.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `timeout` appears ZERO times in `mcp_transport.py`, so neither `streamablehttp_client(...)` nor `session.call_tool(...)` is bounded and the SDK's internal default still governs, inside a pin range that is itself unbounded (see DW-1-2-10).

## DW-1-2-10 — `mcp>=1.28.1` is declared with no upper bound in all three manifests while `_call_tool_async` bi…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `mcp>=1.28.1` is declared with no upper bound in all three manifests while `_call_tool_async` binds SDK internals (`mcp.client.streamable_http.streamablehttp_client`, `ClientSession`, `result.content` block `.type`/`.text`, `result.isError`) that only the opt-in live spike executes — a breaking major release would solve cleanly, pass the whole default gate, and fail at first real use.
  evidence: Found by the 2026-07-25 follow-up review. Not patched here deliberately: capping the pin edits `pyproject.toml` + both `pixi.toml`s and forces a `pixi.lock` regeneration, and this story's lock was being rebuilt out-of-band on `build/pyforge-herald-1-2` at the time — a concurrent re-lock is the wrong moment to change a dependency constraint. Pair the cap with the offline `ClientSession` double so the binding is testable, and note the same unbounded-pin pattern is already deferred for `python-build` from Story 1.1.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN in all three manifests, verified individually: `pyforge-herald/pyproject.toml:16` `dependencies = ["mcp>=1.28.1"]`, `pyforge-herald/pixi.toml:34` `mcp = ">=1.28.1"`, and root `pixi.toml:1479` `mcp = ">=1.28.1"`. No ceiling anywhere, and the offline `ClientSession` double that would make the SDK binding testable still does not exist.

## DW-1-2-11 — `McpTransport` resolves the credential once and caches it on the instance for the process lifeti…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `McpTransport` resolves the credential once and caches it on the instance for the process lifetime, with no re-resolution when it expires — a long-running `herald deck watch` keeps sending a dead token even after the operator has re-run `/design-login`.
  evidence: Found by the 2026-07-25 follow-up review; `_call_via_mcp_sdk` sets `self._credential` on first use and never revisits it. Arguably correct for Story 1.2 (an expired token is a clean `AuthError`, and NFR-05 forbids Herald minting or refreshing anything), but the *re-read* of an externally refreshed file is not a refresh and would make `watch` survive a routine re-login. Belongs with Story 4.3's watch lifecycle, not with the transport.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `mcp_transport.py:308` still does `self._credential = credential` and nothing re-reads the credentials file afterwards. A long-running process keeps sending the token it resolved at first use.

## DW-1-2-12 — `AuthError` subclasses `TransportError`, so the natural retry predicate for the parent class (`e…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `AuthError` subclasses `TransportError`, so the natural retry predicate for the parent class (`except TransportError: backoff_and_retry()`) silently swallows the one error `bridge-protocol.md` says must halt the loop and never be retried.
  evidence: Found by the 2026-07-25 follow-up review; confirmed by reading `errors.py`'s hierarchy. The inheritance is deliberate (an auth failure *is* a transport failure) and no code retries yet, so nothing is broken today. Recorded so Story 4.3 does not write the obvious predicate: whoever builds the watch loop should catch `AuthError` first, or the hierarchy should grow a `RetryableTransportError` layer that `AuthError` sits outside of.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — `errors.py:30` still declares `class AuthError(TransportError)`, sitting under `TransportError` (`:26`) alongside `TransportUnreachableError` (`:38`) and `TransportCallError` (`:47`). No `RetryableTransportError` layer was introduced, so `except TransportError: backoff_and_retry()` would still swallow the one error that must halt the loop.

## DW-1-2-13 — `sanitize_payload` collapses two distinct string mapping keys that both name the tokenized previ…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `sanitize_payload` collapses two distinct string mapping keys that both name the tokenized preview host onto the single `REDACTED` constant, so the second silently overwrites the first and one entry disappears from the payload.
  evidence: Found by the 2026-07-25 follow-up review and reproduced: `sanitize_payload({"https://a.claudeusercontent.com/x": 1, "https://b.claudeusercontent.com/y": 2})` returns a one-entry dict. The companion defect (a non-string key sanitizing to an unhashable list and raising a bare `TypeError`) WAS patched in this pass; the collapse was not, because no observed tool answer keys a map by URL and preserving distinctness means inventing a suffix scheme for a shape that has never appeared. Revisit if any tool is ever seen returning a URL-keyed map.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — reproduced by execution, not by reading. Calling `sanitize_payload({'https://a.claudeusercontent.com/x': 1, 'https://b.claudeusercontent.com/y': 2})` returns `{'<redacted: tokenized preview url>': 2}` — a ONE-entry dict from a two-key input, with the first value silently lost to the collapse. Exactly the behaviour the entry recorded, unchanged.

## DW-1-2-14 — `mcp_transport.py` imports `_as_text` and `_as_optional_text` from `base.py` as underscored priv…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `mcp_transport.py` imports `_as_text` and `_as_optional_text` from `base.py` as underscored privates, the exact cross-module-private import that `require_conditional` was promoted to public to avoid.
  evidence: Found by the 2026-07-25 follow-up review; confirmed in `mcp_transport.py`'s import block. Story 1.3's `AgentSdkTransport` needs the same null-coercion (the `str(None)` -> truthy `"None"` etag trap these exist to prevent), so it will either repeat the private import or re-implement the coercion untested. Fix candidate: promote both alongside `require_conditional` when Story 1.3 lands, so the public seam is settled by its second consumer rather than its first.
  status: done 2026-08-07

  verified: 2026-07-30 — CONFIRMED STILL OPEN — and the contrast is visible in a single import block. `mcp_transport.py` imports `_as_optional_text` (`:77`) and `_as_text` (`:78`) as underscored privates from `base.py`, immediately alongside the public `require_conditional` (`:80`) that was promoted specifically to avoid this pattern. `_as_text` is in live use at `:331`.

  resolved: 2026-08-07 — Story 1.3 landed exactly the fix candidate: `base.py`'s `_as_text`/`_as_optional_text` are now public `as_text`/`as_optional_text`, re-exported from `transport/__init__.py` alongside `require_conditional`. `mcp_transport.py`'s import updated to the public names (no behavior change, pure rename); `agent_sdk_transport.py` is the second consumer that settles the seam as public, exactly as the fix candidate anticipated.

## DW-1-2-15 — `ARCHITECTURE-SPINE.md`'s amended *Etag headers* convention row asserts that `read_file`'s `if_n…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md`
  summary: `ARCHITECTURE-SPINE.md`'s amended *Etag headers* convention row asserts that `read_file`'s `if_none_match` is "required whenever a prior etag is held", but nothing in the port, the adapter, or the tests enforces or records that obligation — a documented-only invariant of exactly the kind FR-24 was made structural to avoid.
  evidence: Found by the 2026-07-25 follow-up review. The asymmetry is real and deliberate for 1.2 (the transport cannot know whether its caller holds an etag), but it means Story 1.4's bridge-core can poll without `if_none_match`, transfer the full body every cycle, and still read as spine-compliant. Fix candidate: make it structural where the knowledge lives — have bridge-core's watch state carry the last etag and pass it unconditionally, with a test that asserts the poll sends one.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the documented-only obligation is intact and still unenforced. `architecture-pyforge-herald-2026-07-25/ARCHITECTURE-SPINE.md:146` still asserts that `read_file`'s `if_none_match` is 'optional on a first read … and required whenever a prior etag *is* held', while nothing in the port, the adapter or the tests records or checks that obligation.

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

## DW-1-4-1 — Follow-up review still recommended for 1-4-bridge-core-skeleton-state-errors-determinism-boundar

> Promoted 2026-07-31. bmad-loop wrote this as generic `DW-1`; renamed to the
> `DW-<story>-<n>` convention so the next damped story cannot collide with it.

origin: review-budget-followup
source_spec: `spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260730-192235-062b; this entry preserves the lingering recommendation for a deliberate later review.
status: open

## DW-1-4-2 — `state.py`'s `write()` does an unlocked read-modify-write of the whole slug-keyed document (read…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md`
  summary: `state.py`'s `write()` does an unlocked read-modify-write of the whole slug-keyed document (read every slug, mutate one, atomically replace the file), so two processes writing different slugs concurrently can race — the second writer's read can happen before the first writer's `os.replace`, silently losing the first writer's update. The atomic temp-file-plus-`os.replace` protects against a corrupted/partial file, not against a lost update.
  evidence: Found by this story's own Blind Hunter review pass. No current caller exercises concurrent writes (this story ships no seed/pull/watch logic yet — every call site is a single test), so it is latent, not active. Real risk lands with Story 4.x's `watch` loop if it ever runs multiple slugs' polls as separate processes, or with any future concurrent `herald` invocation against the same repo. Fix candidate: an advisory file lock (e.g. `fcntl.flock` on a sidecar lock file, POSIX-only) held across the read-modify-write span, or narrow `write()` to a single-slug patch file per artifact if per-slug granularity turns out to matter more than one shared document.
  status: done 2026-08-10

  verified: 2026-08-10 — RESOLVED by Story 13.1 (`spec-13-1-the-state-layer-survives-a-second-writer.md`), via the FIRST fix candidate this entry proposed (an advisory file lock), not the single-slug-patch-file alternative. Chosen approach: one shared, stdlib-only, cross-platform advisory file lock (`fcntl.flock` on POSIX, `msvcrt.locking` on Windows — this package targets win-64, so the original POSIX-only sketch was widened) in the new `locking.py`'s `locked(lock_path)` contextmanager, held across the whole read-modify-write span of `state.write()`, `progress.upsert()`, `claims.create()`, and `notices.author_notice()`/`publish_notice()`/`close_notice()`/`archive_rename()`, keyed on a sidecar `<document>.lock` file next to each protected document. SQLite/Postgres migration stays explicitly out of scope, per this story's own Never-list — that is Story 13.3's separate, larger-scoped migration; no fresh evaluation of that option was performed here. `claims.py`'s network-validating functions (`publish`, `revalidate`, `revalidate_all`) run `evidence_mod.validate_link`/`validate_for_publish` UNLOCKED, before acquiring the lock, so the lock never spans a live HTTP request — a first-pass implementation that locked the whole function was caught and reverted before landing (would have blocked every other claims writer for the duration of a network call). All three carry their pre-lock validation results POSITIONALLY — per claim, the pre-validation evidence tuple plus an index-aligned results tuple, applied back inside the lock at index `i` only when `i < len(original)` and `fresh.evidence[i] == original[i]` (the discard-stale rule; every other entry's write still lands) — never in a dict keyed by `Evidence` value. `Evidence` is a frozen, value-equal dataclass and `create` de-duplicates nothing, so a value-keyed map collapses two field-identical entries onto one key and applies a single result to both: WITHIN one claim (a duplicated link whose two checks return `True` then `False` stored `[False, False]` instead of `[True, False]`) and, for `revalidate_all`, ACROSS claims (one claim's outcome overwriting another's). `revalidate_all` additionally keys its per-claim structure by claim id (`dict[str, tuple[original, results]]`) so a lookup only ever searches within that same claim's own results. Both collapse variants were caught as review-loopback findings (passes 2 and 4) and fixed before landing. `publish` additionally re-verifies inside the lock that every evidence entry it is about to write carries this call's own validation, raising `errors.ClaimStateError` and writing nothing when a concurrent writer changed an entry during the unlocked validation window — the discard-stale rule alone would have let a claim persist as `published` over evidence that call never checked, bypassing publish's own broken-link gate; it stays as-is for `revalidate`/`revalidate_all`, whose purpose is to record breakage rather than gate on it. SCOPE OF THIS CLOSURE — read before relying on it: what is resolved is the unlocked read-modify-write *inside* each of those functions, which is exactly the defect this entry's `summary` describes. It does NOT resolve the wider read-network-write span in `deck_pipeline.py` that this entry's `update_2026-08-07` paragraph below describes: `_record_pull_etag`/`push_exports` build their replacement `etags` map from a `state.read` taken BEFORE the network pull/push and then hand the whole slug entry to `state.write`, so two concurrent `herald deck pull` invocations for the same slug can still drop one artifact's etag — `state.write`'s own lock cannot close a critical section that starts in its caller. `seed`'s duplicate-remote-project check (`deck_pipeline.py:199-206` -> `create_project` -> `state.write`) is the same shape. Both are caller-level spans outside Story 13.1's file surface (`state.py`/`progress.py`/`claims.py`/`notices.py`/`locking.py`) and were recorded as their own separate deferred-work entry — in `_bmad-output/implementation-artifacts/deferred-work.md` (this story's review-deferral file), NOT as a `## DW-` entry in this ledger — rather than being silently folded into this one. `state.write`'s own docstring carries the same caveat, so a reader of the code does not have to find this paragraph to learn the caller-level span is still open.
  update_2026-08-07: Epic 2's `herald deck pull` (Stories 2.1-2.4, `deck_pipeline.py`) is the first REAL caller of the "any future concurrent `herald` invocation against the same repo" scenario this entry already anticipated — an operator running two `herald deck pull <slug> --target ...` invocations for the SAME slug (different targets) concurrently now hits exactly this race, confirmed by Epic 2's own Edge Case Hunter review pass. Still deliberately not fixed here: it predates Epic 2, is already tracked, and Epic 2's own scope was the pull/land/re-derive logic, not `state.py`'s concurrency model. Raises this from "latent" to "concretely reachable" — worth prioritizing before Story 4.x's `watch` loop ships, since that will make concurrent state writes routine rather than an edge case.

## DW-1-4-3 — `state.py`'s `write()` calls `state_path.parent.mkdir(parents=True, exist_ok=True)` unguarded — …

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md`
  summary: `state.py`'s `write()` calls `state_path.parent.mkdir(parents=True, exist_ok=True)` unguarded — if any path component of `state_path.parent` already exists as a regular file (not a directory), `mkdir` raises an unhandled `NotADirectoryError`/`FileExistsError` rather than a `HeraldError`, contradicting AD-6's "every bridge command fails structurally" for this one rare shape.
  evidence: Found by this story's own Edge Case Hunter review pass. Lower priority than the JSON-corruption and malformed-entry cases already patched in this story (those are plausible from an interrupted write or hand-edit; this requires something to have created a plain file at exactly `.herald` or one of its ancestors, which nothing in this repo does today). Fix candidate: wrap the `mkdir` call and re-raise as `errors.HeraldError` naming the offending path.
  status: open

### DW-1: Follow-up review still recommended for 1-4-bridge-core-skeleton-state-errors-determinism-boundary after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260730-192235-062b; this entry preserves the lingering recommendation for a deliberate later review.
status: open

## DW-1-5-1 — `registry.read()` raises "malformed" (`expected exactly two body lines, found 5`) against every …

- source_spec: `_bmad-output/implementation-artifacts/spec-1-5-registry-module-readme-design-project.md`
  summary: `registry.read()` raises "malformed" (`expected exactly two body lines, found 5`) against every one of the 13 existing hand-seeded `presentations/*/README.md` § *Design project* sections (9 of them pyforge-*), so the bootstrap-fallback consumer a later CAP story wires in (AD-5) will fail against 100% of the current fleet until those sections are migrated to the canonical two-line shape or a tolerance decision is made — one `register()` call per deck normalizes a README, so Story 1.6's seed path may absorb the migration naturally, but nothing guarantees it covers all 13.
  evidence: Found by the 2026-07-31 follow-up review (Blind Hunter), reproduced live against the pyforge-herald/doctor/scribe/warden READMEs. Spec-sanctioned for this story — the intent contract's "Never" boundary explicitly scopes out parsing the pre-existing hand-authored prose — but the resulting migration debt was recorded nowhere until this entry.
  status: open

  verified: 2026-08-07 (Story 1.6) — the anticipated resolution path changed. `seed`'s registry-bootstrap-fallback conflict check treats a *malformed* § Design project section as "already linked, cannot verify" and raises `SeedConflictError` naming the parse failure, rather than silently absorbing/migrating it via a `register()` call. This was a deliberate choice: overwriting a section this module cannot prove matches its own canonical shape risks clobbering a real, hand-verified project link if the parse failure masks a different project id than expected. The 13 pre-existing malformed sections (9 pyforge-*) are therefore *still* migration debt, and now block `herald deck seed <slug>` on those exact slugs until resolved by hand (or a future story adds a `--force`/`--migrate-registry` escape hatch) — narrower than "seed naturally migrates them", not wider. Recorded as the current status; the migration itself remains undone.

## DW-1-6-1 — Write-level conflict detection (the wire shape DW-1-2-5 could not pin) is out of `seed`'s scope

- source_spec: `_bmad-output/implementation-artifacts/spec-1-6-herald-deck-seed-slug.md`
  summary: `deck_pipeline.seed` detects an already-seeded deck via a pre-flight check (state.py, then registry.py as a bootstrap fallback) — both run *before* any transport call. It does not, and cannot yet, detect a conflict *at write time*: DW-1-2-5 (Story 1.2) recorded that a conflicted `write_files`/`copy_files` answers as an ordinary success `Mapping` with an unpinned structured-conflict shape, and nothing in this repo has observed that wire shape live. `bridge-protocol.md`'s CAP-1 success criterion ("seeding over existing Design-side edits is refused with a structured conflict") is therefore only satisfied for the case this story's pre-flight check can see (a state entry or registry section already naming a linked project) — a scenario where the *pre-flight* check passes clean (no local record of any link) but the Design-side project already independently exists with content at the same name/path is not distinguished from a legitimate fresh seed.
  evidence: By construction — `seed`'s `create_project`/`create_support_js`/`copy_files`/`write_files` calls all use fresh-etag (`"0"`) preconditions per FR-24 and trust whatever the transport returns without inspecting the payload shape for a conflict marker. Consistent with the story's own documented judgment call (module docstring, judgment call 1) and DW-1-2-5's own "recorded so Story 1.4 [does not / a future story does not] assume a conflicted write raises" framing.
  status: open

### DW-2: Follow-up review still recommended for 13-1-the-state-layer-survives-a-second-writer after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-13-1-the-state-layer-survives-a-second-writer.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260810-194532-e993; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, herald 13-1)


### DW-3: Follow-up review still recommended for 13-3-db-backed-storage-behind-the-existing-seam-with-migrations after the damping cap was spent
origin: review-budget-followup
source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-3-db-backed-storage-behind-the-existing-seam-with-migrations.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260813-094918-551b; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

### DW-13-3-1: One corrupt legacy JSON file blocks all three Moments' stores, where before Story 13.3 it blocked only its own

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-3-db-backed-storage-behind-the-existing-seam-with-migrations.md`
  summary: One corrupt legacy JSON file blocks all three Moments' stores, where before Story 13.3 it blocked only its own.
  evidence: Reproduced against the merged branch. `db._import_legacy_v1` imports progress + claims + notices inside the single v1 migration, so any one legacy file failing validation aborts the whole migration and `_ensure_schema` retries from scratch on every later command. With a healthy `.herald/progress.json` and `.herald/notices-index.json` beside a truncated `.herald/claims.json`, `progress.read_all`, `claims.read_all` and `notices.list_notices` ALL raise `claims file ... could not be read`; against the pre-story revision `257094dcc2` the same fixture returns the progress and notices records normally and only claims fails. Not a spec deviation -- the spec mandates one shared database and mandates that an invalid legacy file fail migration rather than be silently dropped -- so re-deriving under the same spec reproduces it; the widened blast radius is an undecided consequence of those two mandates meeting, not a coding error. Needs a design decision (isolate each store's import so a bad file only blocks its own Moment, vs. accept the coupling and say so in the operator docs). Recovery today is real but undocumented: removing or repairing the one named file unblocks the other two, and nothing tells the operator that.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-3` there) during the pre-shutdown deferred-work audit.

### DW-13-3-2: A read-only `.herald/` directory now fails every herald command, where before Story 13.3 reads still worked

- source_spec: `_bmad-output/projects/pyforge-herald/implementation-artifacts/spec-13-3-db-backed-storage-behind-the-existing-seam-with-migrations.md`
  summary: A read-only `.herald/` directory now fails every herald command, where before Story 13.3 reads still worked.
  evidence: Reproduced on this branch. With a populated store made read-only (`chmod 444` on `.herald/herald.db`, `chmod 555` on `.herald/`), `progress.read_all` raises `HeraldError: ... could not be opened: attempt to write a readonly database`; every read command and all three exporter scripts fail the same way. Pre-Story-13.3 the equivalent read of a read-only `.herald/progress.json` returned its records normally. The cause is WAL itself, not a coding error: verified that even a bare `PRAGMA journal_mode` -- a pure read of the setting -- raises the same error on such a store, because a WAL database opened read-write needs to create/write the `-shm` sidecar. Story 13.3's spec mandates WAL under `## Boundaries & Constraints` -> Always, so re-deriving under the same spec reproduces this exactly; `_set_wal_mode`'s own docstring already records the fast-fail as intentional. Resolving it is a design decision rather than a fix: opening `file:...?mode=ro` when the store is not writable would restore read behavior but needs a rule for when to choose it, and WAL readers still need a writable directory for `-shm`, so the alternative may be to document the requirement instead. Neither the operator guide nor the troubleshooting doc mentions that `.herald/` must be writable even to read.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-13-3-2` there) during the pre-shutdown deferred-work audit.

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
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-14-2` there) during the pre-shutdown deferred-work audit.

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
