---
title: '46.1: A bare clone bootstraps the substrate'
type: 'feature'
created: '2026-09-24'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The substrate-nightly publisher is inert: .github/workflows/substrate-nightly.yml
      is not in actions-policy.toml allow_when_enabled, so it stays off even once
      GitHub Actions are re-enabled, and no release assets exist yet.
    evidence: |-
      Review 2026-09-24 (Blind + Intent, grouped). .github/actions-policy.toml has
      enabled = false and allow_when_enabled lists only staged-recipes-linter.yml and
      detectors.yml. Enabling a billed workflow is an operator billing decision, and this
      dispatch was told not to edit that file. Until it is enabled, bootstrap's fetch
      fails with a named reason and every member rebuilds locally (MRS-CTX-003/004).
    location: >-
      .github/actions-policy.toml
    severity: medium
  - summary: >-
      bootstrap reports no freshness: it never compares the manifest's source_commit
      with the clone's HEAD, so a stale pack or release installs silently as fetched,
      and a present member is never refreshed.
    evidence: |-
      Review 2026-09-24 (Blind + Intent, grouped). This is G4 of the substrate-primary
      reordering (spec-token-economy-claude-session-path/.memlog.md line 15), and scribe
      compile_surface owns it. Leaving present members untouched is this slice's spec
      rule. The manifest already records source_commit, so a later freshness check has
      the input it needs.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context_bootstrap.py
    severity: medium
  - summary: >-
      The rebuild fallback cannot complete in the session-default pyforge-guild env:
      codegraph is in no guild lock, and scribe graph compile needs the pyforge-scribe
      extras.
    evidence: |-
      Review 2026-09-24 (Blind + Intent, grouped). The failure is loud and named:
      PosixProcess turns a missing binary into ProcessError (pyforge-core process.py:179),
      and bootstrap reports that as MRS-CTX-004 with the reason. The env composition
      predates this story. Closing the gap needs a pixi.toml change (and an
      environment.yaml regeneration) that this dispatch may not make.
    location: >-
      pixi.toml
    severity: medium
  - summary: >-
      No cloud-runner setup (the Copilot copilot-setup-steps.yml, Devin, Cursor
      background) calls marshal context bootstrap yet, so a bare cloud clone does not
      open already filled.
    evidence: |-
      Review 2026-09-24 (Intent). The Surface of Story 46.1 (epics.md) names only the
      publisher and the CLI. Wiring runner setup while the publisher is disabled would
      make every cloud session fail the fetch and pay a full local rebuild. Wire it once
      the substrate-nightly assets exist.
    location: >-
      .github/workflows/copilot-setup-steps.yml
    severity: medium
  - summary: >-
      The new pyforge context noun alias and the context bootstrap / context pack verbs
      are not documented in the marshal SKILL.md, the grammar reference, or the pyforge
      dispatcher usage text.
    evidence: |-
      Review 2026-09-24 (Blind). The fix edits an agent-context file
      (.claude/skills/pyforge-marshal/0.1.0/pyforge-marshal/SKILL.md, SKF-generated) plus the pyforge-core
      dispatcher usage string. Routing a documentation refresh through the SKF skill
      update keeps the generated skill consistent. The CLI's own --help already lists
      both verbs.
    location: >-
      .claude/skills/pyforge-marshal/0.1.0/pyforge-marshal/SKILL.md
    severity: low
  - summary: >-
      chain-currency-sweep-check reports a pyforge-marshal
      chain-audit-checkpoint-staleness fail, because this story's required memlog
      appends (dated 2026-09-24) are newer than the planning spine's last reconcile.
    evidence: |-
      python scripts/chain_currency_sweep_check.py exits 1 with
      "[chain-currency] pyforge-marshal: chain-audit-checkpoint-staleness: project
      pyforge-marshal: staleness checkpoint fail". At the baseline (12ec9822ff) the
      newest marshal memlog entry was 2026-09-20. The dispatch was required to name its
      governed paths on the memlogs, and clearing the checkpoint is the chain-currency
      reconciler's job per the runbook, not a dev-story edit.
    location: >-
      _bmad-output/projects/pyforge-doctor/CHAIN-CURRENCY-RUNBOOK.md
    severity: low
declared_low_risk: false
baseline_revision: '12ec9822ff94aee0feee02ac3bc3a66c346a138d'
---

<intent-contract>

## Intent

**Problem:** As an agent starting on a cloud runner (Devin, Copilot cloud, Cursor background), I want nightly-built substrate artifacts (codegraph, cocoindex distills, planning-graph export) published as CI/release assets and a `pyforge context bootstrap` fetch-or-rebuild command, So that a bare clone opens on the shared substrate instead of re-deriving it privately at ACU/quota cost.

**Approach:** a publisher (nightly workflow or release-asset upload) for the substrate artifacts, plus the `pyforge context bootstrap` CLI in pyforge-core or marshal (fetch-or-rebuild; rebuild is loud and attributable, never silent).

Ledger key: `46-1-a-bare-clone-bootstraps-the-substrate`. Ledger status (do not edit the ledger): `backlog`. Type / Effort / Deps: feature / L / —.
Living CAP: `spec-pyforge-marshal` CAP-192 (story slice CAP-19(a)) ← `spec-marshal-token-economy` CAP-19 (absorbed).

## Boundaries & Constraints

**Always:**
- Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.
- The substrate is three members, each with one sentinel: structure graph (`.codegraph/codegraph.db`), planning graph (`.claude/data/pyforge-scribe/graph.json`), derived-context distills (`.claude/data/pyforge-scribe/move-list.json`, plus `cocoindex-index.json` when present).
- A published pack is a pair: `substrate-manifest.json` (per-file sha256 + size, source commit, archive sha256) and `substrate.tar.gz` (deterministic bytes).
- Every network use is the explicit `bootstrap` verb, announced on stderr and recorded in the envelope. `--offline` and `--from <dir>` never touch the network.
- A digest mismatch, malformed manifest or unsafe archive entry installs nothing and is a named finding; the member then falls back to a local rebuild.
- Every rebuild is a named WARN finding that states the command run and why the fetch did not serve that member. A member neither fetched nor rebuilt is UNEVALUABLE (exit 1).
- scribe is invoked only through `adapters/scribe_cli.py`; `gh` and `codegraph` only through `ProcessPort`. `core/` stays pure (AD-4).

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not cite absorbed `spec-marshal-token-economy` CAP-19..24 as living numbers; use CAP-192..197.
- Do not flip the parent Dream to `realized` (benchmark artifact is the realized-guard).
- Never overwrite a member already present in the clone. Never `extractall`; never follow symlinks or write outside the member's own roots.
- No network-stack import (`requests`/`httpx`/`urllib`/`socket`) — fetch shells out to `gh`.
- Do not edit `.github/actions-policy.toml` (operator billing decision).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fetch serves all | fresh clone; published pair reachable | every member installed, each file sha256 equals manifest; exit 0 | No error expected |
| Local pack dir | `--from <dir>` holding a pair | same install, no network, `data.source.network` false | No error expected |
| Offline | `--offline`, members missing | each missing member rebuilt; MRS-CTX-003 per member | rebuild failure → MRS-CTX-004, exit 1 |
| Fetch fails | `gh` absent / non-zero / timeout | rebuild fallback, MRS-CTX-003 carries the fetch reason | — |
| Tampered bytes | archive or file digest differs | nothing installed; MRS-CTX-005; rebuild fallback | — |
| Unsafe manifest | absolute path, `..`, foreign-member path, bad hex | refused as malformed; MRS-CTX-005 | — |
| Already present | sentinel exists | member untouched, state `present` | — |
| Pack with gap | `context pack`, one member absent | pair written without it; MRS-CTX-006 | nothing packable → MRS-CTX-007, exit 1 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context.py` -- `add_context_subparser` (refresh/retrieve); handler idiom root→findings→`compute_verdict`→`build_envelope`→`exit_code_for`. Wire `bootstrap` + `pack` here.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py` -- sole scribe invoker; `ScribeCli.resolve_binary`, `refresh` (l.154), outcome dataclasses ok/reason/argv; "every failure degrades".
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py:223` -- `build_codegraph_index(repo_root, *, stale, process)` returns failure reason or None; reuse for structure-graph rebuild.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py:1853` -- `REGISTERED_CODES` MRS-CTX area; `core/verdict.py:1193` `_CLASSIFY_TABLE`; `tests/unit/test_findings.py:392` pins the set.
- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` -- `dispatch_argv` resolves station→binary; unknown station raises `DispatchError`. Stdlib-only leaf.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/parity.py` -- `CLI_ONLY_VERBS` already holds `context`; no MCP change.
- `.github/workflows/herald-live-demo.yml` -- schedule + workflow_dispatch + setup-pixi v0.80.0 idiom to mirror.
- `scripts/pixi_version_registry.py` -- `SITES`; every workflow with `pixi-version:` must be registered.
- `src/shared/packages/pyforge-marshal/docs/air-gapped-deployment.md` -- states no network at runtime; must name the bootstrap path and its offline forms.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `core/verdict.py`, `tests/unit/test_findings.py` -- register MRS-CTX-003 WARN, -004 UNEVALUABLE, -005 WARN, -006 WARN, -007 UNEVALUABLE.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/substrate.py` -- NEW pure module: member table, manifest render/parse with path-safety validation, verify, member-state→finding mapping, asset-name + default-tag constants -- one owner for the substrate contract.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/substrate_store.py` -- NEW: collect+hash member files, deterministic tar.gz pack, `gh release download` via ProcessPort, verify-then-stage-then-replace install -- I/O kept out of core.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py` -- add a rebuild method for `graph compile --nightly` / `index refresh` -- keeps scribe single-invoker.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context_bootstrap.py` + `cli/context.py` -- NEW `marshal context bootstrap` (`--tag`, `--repo`, `--from`, `--offline`) and `marshal context pack` (`--out`, `--source-commit`) handlers with injectable process/scribe seams.
- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` + `tests/unit/test_dispatch.py` -- narrow noun alias `context`→marshal so `pyforge context bootstrap` runs `marshal context bootstrap`; a real station name always wins.
- `.github/workflows/substrate-nightly.yml` -- NEW publisher: nightly cron + workflow_dispatch; builds the three members, `marshal context pack`, uploads the pair to the `substrate-nightly` prerelease with `--clobber`.
- `scripts/pixi_version_registry.py` -- register the new workflow's setup-pixi site.
- `src/shared/packages/pyforge-marshal/docs/air-gapped-deployment.md` -- document the explicit fetch and its `--offline` / `--from` forms.
- `src/shared/packages/pyforge-marshal/tests/unit/test_substrate.py`, `test_substrate_store.py`, `test_cli_context_bootstrap.py`, scribe_cli tests -- unit-test every I/O matrix row plus deterministic-pack identity.

**Acceptance Criteria:**
- Given a fresh clone with no `.codegraph/`, no distills, no planning graph When `pyforge context bootstrap` runs Then it fetches the latest published artifacts and verifies their digests, or rebuilds locally with a named finding And the fetched substrate is byte-identical to what a loop home produced.
- Given a loop home packed with `marshal context pack` and a fresh clone, when `marshal context bootstrap --from <pack>` runs, then every installed file's bytes equal the loop home's file bytes (test-proven round trip).
- Given the same member files packed twice, when both archives are hashed, then the two sha256 values are equal.
- Given `pyforge context bootstrap`, when pyforge-core dispatches it, then argv becomes `marshal context bootstrap`.

## Spec Change Log

## Review Triage Log

### 2026-09-24 — Review pass
- verdicts: 40 findings — high 0, medium 9, low 25, false 6, maybe-false 0
- findings:
  - `[low]` `[patch]` B1 (Blind): the nightly workflow comment says a failed member still publishes the members that built, but the build steps have no `continue-on-error` — true: any failing member step fails the job and uploads nothing, so the comment misleads a maintainer. Fix applied: the comment now states that a failing build step fails the job, nothing is uploaded and the previous pair stays on the release, and that MRS-CTX-006 appears only when a build step exits 0 without its sentinel.
  - `[medium]` `[defer]` B2 (Blind): the new workflow is not in `.github/actions-policy.toml` `allow_when_enabled`, so it stays off even after Actions are re-enabled, and nothing records the needed policy change — true (`allow_when_enabled` lists only `staged-recipes-linter.yml` and `detectors.yml`). Enabling a billed workflow is the operator's billing decision, and this run was told not to edit that file. Deferred with D1.
  - `[low]` `[patch]` B3 (Blind): `actions/checkout` runs at depth 1, so the git surface of `scribe graph compile` (last 100 commits, `compile.py` `_DEFAULT_MAX_COMMITS`) sees one commit and the published graph.json lacks commit history — true. Fix applied: `fetch-depth: 0` on the checkout step.
  - `[medium]` `[patch]` B4 (Blind): `marshal context pack` on an operator host ships graph.json with session-transcript nodes and absolute home paths, and the air-gapped doc directs operators to do that with no warning — true: `compile_graph` reads the transcript surface under `~/.claude/projects` when it exists. Fix applied: the air-gapped doc now warns about this and recommends carrying the published substrate-nightly assets, which are built on a CI runner that has no transcripts. `pack` remains for when no published pair exists.
  - `[medium]` `[defer]` B5 (Blind): bootstrap never compares the manifest's `source_commit` with the clone's HEAD, so a stale pack installs silently as `fetched` — true. Freshness is G4 of the substrate-primary reordering (`spec-token-economy-claude-session-path/.memlog.md` line 15), owned by scribe `compile_surface`, not by this G1 slice. Deferred with D6.
  - `[low]` `[reject]` B6 (Blind): a rebuild after install changes "fetched" members (`scribe index refresh` upserts into the installed graph.json) — true, but only when the pack lacks derived-context, or its install is refused, while planning-graph is fetched. The upsert writes the same graphify nodes the producer's own refresh wrote. The fix (snapshot or re-label) adds state and branches. Recorded as a residual risk.
  - `[low]` `[reject]` B7 (Blind): a failed install leaves an optional file behind that blocks later installs — true only for an OSError mid-install after full verification. The member then falls back to a rebuild (`scribe index refresh` rewrites both files), so nothing stays blocked until a hand delete. The cleanup adds a branch for a rare disk fault.
  - `[medium]` `[defer]` B8 (Blind): the rebuild fallback cannot work in the session-default env — true: `codegraph` is in no `pyforge-guild` lock, and `scribe graph compile` needs the `pyforge-scribe` extras. The failure is loud and named: PosixProcess turns a missing binary into ProcessError (`pyforge-core/process.py:179`), which becomes MRS-CTX-004 with the reason. The env composition predates this story, and closing it needs a `pixi.toml` change that this run may not make. Deferred with D8.
  - `[low]` `[patch]` B9 (Blind): `gh` auth and availability are not distinguished, and the doc's network row omits the auth requirement — partly true. A missing `gh` is already reported as "could not run", and gh's own last line (auth, not found, network) is carried into the reason (`substrate_store.py` fetch_pair). The doc gap is real. Fix applied: the network row now says `gh` must be authenticated (GH_TOKEN or `gh auth login`) with read access to the releases.
  - `[low]` `[patch]` B10 (Blind): the two adapters build their failure tails in opposite stream orders with no separator — true. fetch_pair's tail could come from stdout ahead of gh's stderr error, and lines could merge. Fix applied: both adapters join stdout then stderr with a newline between the non-empty parts, so the tail is the last stderr line.
  - `[low]` `[patch]` B11 (Blind): the doc's claim that a carried pair's archive sha256 can be compared with the published one goes further than the code guarantees — true: gzip bytes depend on the host's zlib build, and a locally packed substrate differs from the runner's. Fix applied: the sentence is narrowed to same-host determinism, and to a carried copy of the published pair verifying against its own manifest.
  - `[low]` `[reject]` B12 (Blind): a dangling-symlink sentinel counts as present — true, and it is the spec's never-overwrite rule: bootstrap never writes through or replaces an existing path. Treating it as missing would need removal logic the spec forbids. Only the envelope's file list differs, which is cosmetic and unlikely in everyday use.
  - `[low]` `[reject]` B13 (Blind): `--tag`/`--repo` are silently ignored with `--offline`/`--from` — true but harmless: the envelope records the source kind. `--tag` has a default, so a mutual-exclusion check needs explicit-flag detection, which is more than a direct correction.
  - `[false]` `[reject]` B14 (Blind): entry sizes are checked only after streaming — refuted. `_stream_entry` compares the tar header size with the manifest size before it reads a byte (`substrate_store.py`, `info.size != expected.size`). The whole archive's sha256 and size are checked against the manifest before the tar is opened.
  - `[low]` `[reject]` B15 (Blind): the `substrate-nightly` tag stays on its first night's commit — true, and already documented: the release notes say the manifest's `source_commit` names the commit each pair came from, and nothing reads the tag's commit. Moving the tag nightly adds delete/re-create steps. AGENTS.md's tag-is-a-version rule governs package versions.
  - `[low]` `[reject]` B16 (Blind): the "refresh cannot reach the substrate codes" meta-test is a source-text assertion, and the nearby "neither code" comment is stale — true that it is weaker than its comment. It only fails on a hypothetical refactor, and the "neither code" comment predates this story and refers to 001/002. An import-level contract is more than a direct correction.
  - `[low]` `[reject]` B17 (Blind): the story spec's frontmatter and body have drifted (created date, status versus body, Source section, Verification list) — every part's fix edits this build's spec.
  - `[low]` `[defer]` B18 (Blind): the new `context` noun alias and the `context bootstrap`/`context pack` verbs are missing from the dispatcher usage text, the marshal SKILL.md and the grammar reference — true. The fix edits an agent-context file (`.claude/skills/pyforge-marshal/0.1.0/pyforge-marshal/SKILL.md`, SKF-generated).
  - `[false]` `[reject]` B19 (Blind): AC1 has no end-to-end test through the front door — refuted as a defect. `test_dispatch.py::test_context_noun_alias_dispatches_to_marshal` pins the exact forwarded argv `["marshal", "context", "bootstrap", …]`, and `test_main_routes_context_bootstrap` drives marshal's `main` with that same argv, so the two halves share one pinned contract.
  - `[false]` `[reject]` B20 (Blind): a `ValueError` message says more than its check verifies — refuted. The pack-side "changed size" check has no digest counterpart to disagree with. tarfile reads exactly the header size, so a same-size change is hashed from the archived bytes into the manifest, and the manifest stays consistent with the archive.
  - `[low]` `[patch]` V1 (Verification gap): `marshal context pack` text output is never run by a test — filed evidence accepted. Fix applied: `TestPack::test_text_output_names_files_and_archive_sha` runs `run_context_pack` in text format and checks the verdict line, each member's file count and the archive's real sha256.
  - `[low]` `[patch]` V2 (Verification gap): a non-default `--tag` is never shown to reach the gh argv — filed evidence accepted. Fix applied: `TestGhArgv::test_explicit_repo` asserts `argv[3] == "t"`, and a `TestFetchServesAll` case asserts that a non-default tag reaches `fake.calls[0][3]`.
  - `[low]` `[reject]` V3 (Verification gap, other): the source-text meta-test does not verify its claim — same root cause as B16, rejected with it.
  - `[medium]` `[defer]` D1 (Intent): the publisher is not operational (Actions disabled, workflow not in `allow_when_enabled`; floating codegraph version; non-atomic `--clobber`) — true for the policy part. The float and the upload race are named limits: the consumer refuses a mismatched pair as MRS-CTX-005. Deferred with B2.
  - `[false]` `[reject]` D2 (Intent): the `NOUN_ALIASES` rewrite changes the shared front-door grammar — refuted as a defect. It delivers the literal `pyforge context bootstrap` the story names, a real station named `context` still wins, and both are pinned in `test_dispatch.py`.
  - `[low]` `[reject]` D3 (Intent): the member identity reads the story's distills as scribe's artifacts rather than the loop-home epic-context distills — the identity claim is refuted. `scribe index refresh` is the cocoindex `compile_surface` derive of the code graph and the move list (`pyforge-scribe/cli.py` index_refresh), which is what "cocoindex distills … nightly-built … published as CI/release assets" can name. The epic-context distills are agent-authored per run: their scribe `derive()` is a no-op, and CI cannot build them. The graph.json upsert side effect it also raises is rejected with B6.
  - `[low]` `[reject]` D4 (Intent): the published substrate is not proven equal to what a real loop home builds — true beyond transport. After the fetch-depth patch, the remaining difference is environmental (tool versions), and a consumer still gets a valid substrate. Pinning a stronger identity means editing this build's spec's byte-identity definition.
  - `[false]` `[reject]` D5 (Intent): the digests give integrity, not authenticity — refuted as a defect. The AC asks bootstrap to verify digests, which it does, and the authenticity limit is documented. Digest pinning is Story 46.2 ("The canonical context bundle is digest-pinned").
  - `[medium]` `[defer]` D6 (Intent): bootstrap reports no freshness or staleness, and present members are never refreshed — true. Freshness is G4, owned by scribe, and never-touch-present is this slice's spec rule. Deferred with B5.
  - `[medium]` `[defer]` D7 (Intent): no runner setup (Copilot `copilot-setup-steps.yml`, Devin, Cursor background) calls bootstrap, so a bare clone does not open already filled — true. The story's Surface names only the publisher and the CLI (`epics.md` Story 46.1). Wiring setup before the publisher is enabled would make every cloud session fail the fetch and pay a full rebuild.
  - `[medium]` `[defer]` D8 (Intent): rebuild semantics and toolchain — the warn-versus-refuse part is refuted, because the AC asks for "rebuilds locally with a named finding", which MRS-CTX-003 WARN is. The producer/consumer toolchain split is real and pre-existing env composition. Deferred with B8.
  - `[low]` `[reject]` D9 (Intent): SPEC CAP-18 still says Copier's fetch is the only network path — true in SPEC.md. The marshal memlog already records bootstrap as the second explicit path. SPEC.md is never hand-edited, and the next `bmad-spec` derive absorbs the memlog.
  - `[false]` `[reject]` D10 (Intent): MRS-CTX-004/007 are built with `Severity.ERROR` yet classify UNEVALUABLE — refuted as an inconsistency. Existing UNEVALUABLE codes are built the same way (MRS-INIT-001/002, `cli/init.py:607,628`), because severity and verdict are separate axes.
  - `[medium]` `[patch]` E1 (Edge): `--from ""` (an unset shell variable) is falsy, so it falls through to the networked gh fetch — true. Fix applied: `elif args.from_dir is not None:`, plus a test showing that `--from ""` never calls gh.
  - `[low]` `[reject]` E2 (Edge): an OSError while installing the sentinel leaves an optional file behind — same root cause as B7, rejected with it.
  - `[low]` `[reject]` E3 (Edge): a staging-write failure is reported as "archive unreadable" — true for the prefix, but the OSError text (for example "No space left on device") is carried into the reason, so the cause is named. Splitting it out adds a try branch for a rare local fault.
  - `[low]` `[patch]` E4 (Edge): the nothing-packable path replaces the collected MRS-CTX-006 findings, and its message says "all absent" even for symlinked or non-regular sentinels — true. Fix applied: MRS-CTX-007 is appended in both nothing-packable branches instead of replacing the list, the message no longer claims absence, and the tests expect three 006 plus one 007 at exit 1.
  - `[low]` `[reject]` E5 (Edge): a symlinked parent directory lets `packable_files` pack bytes from outside the checkout — true, but the file read is still the member's own sentinel, through a link the operator chose. The install side, where writing outside the checkout would matter, already refuses symlinked parents. A component walk adds a branch, and the case is unlikely.
  - `[low]` `[reject]` E6 (Edge): an empty or dash-led `--tag` confuses gh — this only comes from a broken invocation. gh then fails or matches no substrate assets, which becomes a named fetch failure and a rebuild (`substrate_store.py` fetch_pair). Validating it adds a guard.
  - `[low]` `[reject]` E7 (Edge): `scribe index refresh` upserts into a fetched graph.json (a claim against AC1) — same root cause as B6, rejected with it and recorded as a residual risk.

## Design Notes

- **Where the CLI lives.** Logic lives in marshal (it owns MRS-CTX and the scribe adapter). pyforge-core gets only a one-entry noun alias so the literal `pyforge context bootstrap` resolves; that satisfies "pyforge-core or marshal" without a station import in the leaf.
- **What "byte-identical" proves.** codegraph and scribe builds are not reproducible across runs, so identity is claimed between the producer's pack and the consumer's install: the manifest's per-file sha256 is written by `marshal context pack` from the producer's own files, and install refuses any byte that differs. The round-trip test is the oracle.
- **Trust.** Digests prove integrity against the manifest, not authenticity: manifest and archive come from the same release. Recorded as a named limit, not a claim.
- **Rebuild side effects.** `scribe index refresh` upserts into `graph.json`; identity is claimed only for fetched members.
- **Air-gap.** SPEC CAP-18's "only network path is Copier's fetch" covers seed; bootstrap is a second explicit, announced path — recorded on the memlog, SPEC.md untouched.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: pass (station `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: pass (station `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run -e pyforge-core pyforge-core-test` -- expected: pass (dispatch alias).
- `python scripts/spec_surface_reconcile.py` -- expected: exit 0 after memlog entries name every changed governed path.

## Auto Run Result

**Summary.** Story 46.1 (`spec-pyforge-marshal` CAP-192) ships two verbs and a publisher:

- `marshal context bootstrap` fetches, verifies and installs the substrate. The literal `pyforge context bootstrap` reaches it through a one-entry pyforge-core noun alias.
- `marshal context pack` writes the substrate pair.
- `.github/workflows/substrate-nightly.yml` is the nightly publisher.

bootstrap has three sources:

- The default form fetches the published `substrate-nightly` pair with `gh release download`. It announces this on stderr and records it as `data.source.network`.
- `--from <dir>` reads a local pair.
- `--offline` never touches the network.

Before installing anything, bootstrap checks the archive digest and every file's sha256 and size against the manifest. It never extracts with `extractall` and never overwrites a member already present. Each member the fetch did not serve falls back to a local rebuild:

- MRS-CTX-003 (WARN) names the rebuild command and the fetch reason.
- MRS-CTX-004 (UNEVALUABLE, exit 1) reports a member that was neither fetched nor rebuilt.
- MRS-CTX-005 (WARN) reports a refused pack.

`pack` writes a deterministic `substrate.tar.gz` and `substrate-manifest.json`. It reports each unpackable member as MRS-CTX-006 (WARN) and a pack with nothing packable as MRS-CTX-007 (UNEVALUABLE, exit 1).

**Files changed** (relative to baseline 12ec9822ff):

- `.github/workflows/substrate-nightly.yml` (new)
- `scripts/pixi_version_registry.py`
- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py`
- `src/shared/packages/pyforge-core/tests/unit/test_dispatch.py`
- Under `src/shared/packages/pyforge-marshal/src/pyforge/marshal/`:
  - `core/substrate.py` (new)
  - `core/findings.py`
  - `core/verdict.py`
  - `adapters/substrate_store.py` (new)
  - `adapters/scribe_cli.py`
  - `cli/context_bootstrap.py` (new)
  - `cli/context.py`
  - `seed/verbs/kit.py`
- `src/shared/packages/pyforge-marshal/docs/air-gapped-deployment.md`
- Under `src/shared/packages/pyforge-marshal/tests/`:
  - `unit/test_substrate.py` (new)
  - `unit/test_substrate_store.py` (new)
  - `unit/test_cli_context_bootstrap.py` (new)
  - `unit/test_scribe_cli.py`
  - `unit/test_findings.py`
  - `meta/test_derived_context_skill_contract.py`
- Planning record:
  - this spec
  - `spec-pyforge-marshal/.memlog.md`
  - `spec-pyforge-core/.memlog.md`
  - `spec-pyforge-unifying-strategy/.memlog.md` (co-governor of `dispatch.py`)
  - `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md`: tracked twins DW-FU-46-1 through DW-FU-46-1-6 for the six deferrals, written by `python scripts/deferred_work_intake.py --fix --project marshal`

**Review findings.** The first pass produced 40 findings: high 0, medium 9, low 25, false 6, maybe-false 0.

Patched (10):

- Medium (2):
  - E1: an empty `--from` no longer falls through to the networked fetch.
  - B4: the air-gapped doc now warns that a local pack ships host transcript nodes and home paths, and recommends the published pair.
- Low (8):
  - B1: the nightly workflow's comment no longer claims it publishes past a failure.
  - B3: the workflow checks out with `fetch-depth: 0`.
  - B9: the doc names the `gh` auth requirement.
  - B10: failure tails in `fetch_pair` and `ScribeCli.rebuild` are joined stdout then stderr, newline-separated.
  - B11: the doc's sha256 comparison claim is narrowed to one host.
  - E4: MRS-CTX-007 is appended beside the per-member MRS-CTX-006 findings, and no longer says "absent".
  - V1: a test covers pack's text output.
  - V2: tests show a non-default `--tag` reaches the gh argv.

Deferred (6 frontmatter entries). Five cover 8 review findings; the sixth is the chain-currency finding this run introduced:

| Entry | Covers | Severity |
|---|---|---|
| Publisher policy allowlist (`.github/actions-policy.toml`) | B2, D1 | medium |
| Freshness against `source_commit` (G4, scribe-owned) | B5, D6 | medium |
| Rebuild toolchain in `pyforge-guild` (`pixi.toml`) | B8, D8 | medium |
| Cloud-runner setup wiring (`copilot-setup-steps.yml`) | D7 | medium |
| SKILL.md / grammar / usage documentation (agent-context file) | B18 | low |
| chain-currency staleness | not a review finding | low |

Rejected (22):

- The graph.json upsert after a derived-context rebuild (B6 and E7) is rejected. It happens only in a producer-gap case, and it writes the same graphify nodes the producer's own refresh wrote. The Design Notes already limit identity to fetched members, and the fix adds state. It is recorded as a residual risk below.
- A leftover optional file after a mid-install OSError (B7 and E2) is rejected. That member falls back to a rebuild, and `scribe index refresh` recovers it. The cleanup adds a branch for a rare disk fault.
- B12, a dangling-symlink sentinel counting as present, is rejected. It follows the spec's never-overwrite rule, and its only effect is on the envelope's file list, which is cosmetic.
- B13, `--tag` and `--repo` being ignored with `--offline` or `--from`, is rejected. It is harmless, and a mutual-exclusion check needs explicit-flag detection.
- B15, the `substrate-nightly` tag staying on its first commit, is rejected. The release notes state that the manifest's `source_commit` is authoritative, and moving the tag needs delete/re-create logic.
- The source-text meta-test being weaker than its comment (B16 and V3) is rejected. It fails only on a hypothetical refactor, and the "neither code" comment predates this story.
- B17, the story spec's frontmatter/body drift, is rejected, because every part of the fix edits this build's spec.
- Intent D3 (distill identity) is rejected. The distills the story names are the cocoindex `compile_surface` outputs. The epic-context distills are agent-authored and cannot be built nightly in CI.
- Intent D4 (loop-home identity) is rejected. The fix edits this spec's byte-identity definition, AC2 proves the round trip, and the fetch-depth patch removes the producer-side content loss.
- Intent D9 (SPEC CAP-18's single-network-path wording) is rejected. The memlog, the sanctioned channel, already records the second path, and SPEC.md is never hand-edited.
- Edge E3 (staging-write failure labelled "archive unreadable") is rejected. The OSError text is carried into the reason.
- Edge E5 (symlinked parent on the pack side) is rejected. It reads the member's own sentinel through a link the operator chose, and the install side already refuses symlinked parents.
- Edge E6 (empty or dash-led `--tag`) is rejected. It gives a named fetch failure and then a rebuild; validation would add a guard.
- Six false findings are rejected:
  - B14: entry size is checked before streaming, and the archive digest is checked first.
  - B19: both halves of the `pyforge context bootstrap` argv contract are pinned.
  - B20: the pack-side `ValueError` message has no digest check to contradict.
  - D2: the noun alias delivers the literal command the story names.
  - D5: authenticity pinning is Story 46.2.
  - D10: existing UNEVALUABLE codes are also built with `Severity.ERROR`.

**Follow-up review recommendation:** `followup_review_recommended: true`. This first pass patched two medium findings.

The specific unverified risk: B4's mitigation for the air-gap transcript leak is documentation only. `marshal context pack` run on an operator's working checkout still packs `graph.json` exactly as that host compiled it, including session-transcript nodes and absolute home-directory paths. No code refuses or scrubs them, and it is unverified whether `pack` should refuse or strip transcript-derived nodes.

Counts by verdict:

| Verdict | Total | Patched | Deferred | Rejected |
|---|---|---|---|---|
| high | 0 | 0 | 0 | 0 |
| medium | 9 | 2 | 7 | 0 |
| low | 25 | 8 | 1 | 16 |
| false | 6 | 0 | 0 | 6 |
| maybe-false | 0 | 0 | 0 | 0 |

**Verification performed.** Results are for the final tree, after the review patches. Every verdict was read from an exit code.

| Command | Exit | Result |
|---|---|---|
| `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` | 0 | 8600 passed, 1 skipped, 12 deselected |
| `pixi run --frozen -e pyforge-ci pyforge-deps-test` | 0 | 130 passed, 3 skipped |
| `pixi run -e pyforge-core pyforge-core-test` | 0 | 1930 passed |
| `python scripts/spec_surface_reconcile.py` | 0 | "every tracked file governed or allowlisted; no drift" |
| `pixi run -e pyforge-guild spec-surface-check` | 0 | pass |
| `pixi run -e pyforge-guild lint-types` | 0 | ruff, ruff format and mypy clean |
| `pixi run -e pyforge-guild deferred-work-check` | 0 | every deferral has a tracked twin |
| `python scripts/chain_currency_sweep_check.py` | 1 | pyforge-marshal staleness checkpoint (deferred; see residual risks) |

**Baseline stamps reverted.** The implementation agent ran scoped `scripts/spec_surface_check.py --write-baseline` stamps that this dispatch forbids:

- commits 1658005172 and 31e515eacc
- commit 107f5e4c03, after the review fixes

Each time, `scripts/.spec-surface-baseline.json` was restored to its content at baseline_revision 12ec9822ff. The final tree has no baseline change. The reconcile guard and spec-surface-check pass on the memlog entries alone: every governed path this story changed is named on `spec-pyforge-marshal`, `spec-pyforge-core` or `spec-pyforge-unifying-strategy`.

**Residual risks.**

- **Identity is claimed only for fetched members, and a rebuild can break it.** When the pack lacks derived-context, or that member's install is refused, while planning-graph is fetched, the `scribe index refresh` rebuild upserts graphify nodes into the fetched `graph.json`. That file then no longer matches its manifest entry.
- **Integrity, not authenticity.** The manifest and the archive come from the same release. Digest pinning is Story 46.2.
- **The publisher is inert.** `substrate-nightly.yml` is not in `allow_when_enabled`, and GitHub Actions are disabled, so the workflow has never run. Until the operator enables it, the default `bootstrap` fetch fails with a named reason and every missing member rebuilds locally.
- **Rebuild toolchain gap.** `codegraph` and the scribe graph extras are not in `pyforge-guild`, so a rebuild there fails loudly as MRS-CTX-004.
- **No freshness check.** A stale pair installs as `fetched`. This is deferred to G4.
- **chain-currency.** `chain-currency-sweep-check` (a `detectors` lane) reports pyforge-marshal staleness caused by this story's required memlog appends until the chain-currency reconciler runs.
