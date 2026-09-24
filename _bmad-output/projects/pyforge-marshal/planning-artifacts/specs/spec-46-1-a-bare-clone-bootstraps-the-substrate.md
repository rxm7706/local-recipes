---
title: '46.1: A bare clone bootstraps the substrate'
type: 'feature'
created: '2026-09-24'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md'
warnings: ['oversized']
deferred: []
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
