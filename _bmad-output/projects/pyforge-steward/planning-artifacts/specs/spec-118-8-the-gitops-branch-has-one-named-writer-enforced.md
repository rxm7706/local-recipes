---
title: "118.8: The gitops branch has one named writer, enforced"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/guild-roster.json
  - .claude/hooks/pre-shell.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic_packs.py
  - recipes/nebari-infrastructure-core/recipe.yaml
---

<intent-contract>

## Intent

**Problem:** CAP-178 says the cloud GitOps source is `gitops/<project_name>`, "a branch that only `nic` writes", and that the session hook denies its force-push. None of that holds as written, and Story 118.3 (backlog) would build on it:

- **No writer identity, two writers.** Dream ruling 4 says only `nic` writes `gitops/*`, but CAP-177 has steward write pack Applications into the GitOps source, which on cloud is that branch. `gitops_root_for` (`src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic_packs.py`) aliases `repository.existing` to the local `~/.nic/gitops/<project_name>` and commits there with no push and no author. The PAT acts as the operator. (STW-M-D1, STW-D-R1, STW-M-Z6.)
- **Enforcement misstated.** The hook loads only deletion-rule prefixes; it has no force-push or commit-on-branch matcher, and `non_fast_forward` exists only as a server ruleset. Spec-118-3 AC1 expects a hook force-push denial no matcher provides, and "no commit authored by `nic`" on `origin/main` names no identity. (STW-M-C4, STW-M-Z2.)
- **Refusal scoped to `validate`.** CAP-178 says "the verb refuses", but spec-118-3 AC2 and its flag fallback name only `validate`; `run_nic` (`deploy_nic.py`) sends `up` straight to `nic deploy`, so a `main`-branch config could deploy. The acceptance half holds (AC2 accepts `gitops/my-nebari-hetzner`). (STW-D-C5.)
- **Two Dream Constraints dropped at mint.** No CAP carries "no secret enters `deploy/nic` or `gitops/*`" (no pre-commit scan, no `GIT_TOKEN` keys-inventory row, and the `DutyResult` summary echoes `nic`'s last output line unredacted) or "nothing on Hetzner without the operator" (only the ledger gates a dispatch, not a run). (STW-M-D5, STW-M-D2.)

**The ruling.** The operator ruled on 2026-11-01, after a read of the nic 0.17.0 source (the `(decision)` entry on the steward memlog): `nic` alone writes `gitops/<project_name>`, under its own deploy key; the `/shared` waiver on rootless kind is ratified; a non-local `deploy nic up` needs `--yes` behind a `session_denials` entry; CAP-177's Warden digest clause narrows to what exists; Story 118.3 gains Deps S-118.8. For Z2 the audit sided with the refute skeptic: the ruleset-before-`up` ordering is already a 118.3 precondition, so no code ordering gate is added. A cost or spend ceiling stays out under AD-6 and the cost Non-goal.

**Approach:** This story changes the chain and the governance roster, not station code. It records the nic-source reading and the ruling, amends CAP-176, CAP-177 and CAP-178 through `--type capability` memlog entries, lands the `session_denials` entry with its hook matcher, re-derives the Spec and FR-50 and FR-52, and amends spec-118-3 and its epics block so 118.3 is dispatchable. Story 118.3 carries the code.

Ledger key: `118-8-the-gitops-branch-has-one-named-writer-enforced`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-steward` CAP-178** — the writer, its enforcement, the branch refusal and the no-secret rule; amended, not re-minted.
- **`spec-pyforge-steward` CAP-176** — the cloud consent gate (`--yes`) and the Non-goal premise that ends when Hetzner runs.
- **`spec-pyforge-steward` CAP-177** — where pack Applications are written on cloud, and the Warden digest clause narrowed to the chart digests steward journals. A fix: no new CAP, no AD moves (AD-1, AD-8, AD-9 as written).

## Acceptance Criteria

- **AC1 — The nic reading.** One memlog `--type event` on `spec-pyforge-steward` records, from the nic 0.17.0 source read read-only (`recipes/nebari-infrastructure-core` points to it), where `repository.existing` clones and whether `nic`'s regeneration commit stages files it did not generate.
- **AC2 — The ruling recorded.** The Dream's 2026-10-31 section Realization log in `docs/dreams/pyforge-steward.md` carries the ruling as a ruling-4 addendum; the `(decision)` memlog entry of 2026-11-01 stands as its record.
- **AC3 — CAP-178 amended.** A `--type capability` memlog entry names (a) the writer: `nic`'s deploy key; (b) enforcement: a `gitops/**` server ruleset with `creation`, `update`, `deletion` and `non_fast_forward` whose only bypass is that key, and the hook claim narrowed to deletion unless a push and force-push matcher joins `session_denials`; (c) the success probe: an author or committer check on `origin/gitops/<project_name>` naming that identity, replacing "no commit authored by `nic`" on `origin/main`; (d) no secret-shaped value enters `src/platform/deploy/nic/` or the rendered GitOps tree, checked before commit; `GIT_TOKEN` gains a `.steward/keys-inventory.yaml` row on CAP-164's pattern, its expiry and scope operator-owned; the `DutyResult` summary stops echoing `nic`'s last output line unredacted.
- **AC4 — CAP-176 and CAP-177 amended.** `--type capability` entries: CAP-176, a non-local `deploy nic up` needs the operator's `--yes`, and the Non-goal premise that no live cloud spend exists ends when Hetzner runs; CAP-177, pack Applications are written into `nic`'s clone before `nic deploy` and steward never pushes the branch ("the verb writes into the GitOps source" reconciled with CAP-178), and the Warden clause narrows to the chart digests steward journals.
- **AC5 — The consent denial.** `docs/governance/guild-roster.json` `session_denials` gains an entry for a non-local `deploy nic up --yes`, modelled on `steward-estate-realize-yes`, and `.claude/hooks/pre-shell.py` gains its matcher in the same change, with `tests/scripts/test_pre_shell_hook.py` covering it. The two never land apart: the hook raises on a declared rule with no matcher (`load_denial_rules`, "drifted: declared-but-unimplemented").
- **AC6 — One event per finding.** One memlog `--type event` per finding id this story carries that the 2026-11-01 audit events do not already record; `bmad-spec` re-derives `SPEC.md` (never by hand), and FR-50 and FR-52 in `_bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md` are re-derived from the amended CAPs.
- **AC7 — Story 118.3 amended before dispatch.** Its tracked story spec: AC1 names the force-push denial's real source (the server ruleset, or the AC5-style matcher if the ruling adds one); AC2's branch refusal runs in `run_nic` for every action, `up` included, before `nic` starts, and a unit test pins `up` refused on branch `main` with usage code 2; the flag fallback (OFF) refuses every action on a `repository.existing` config; AC4 uses the identity probe; the Approach writes pack Applications into `nic`'s clone before `nic deploy`; the Surface lists the `gitops_root_for` `repository.existing` fix in `deploy_nic_packs.py`; three new ACs carry the pre-commit secret scan, the `GIT_TOKEN` inventory row and the `--yes` consent gate. Story 118.3's block in `epics.md` mirrors it: its When line gains "accepts `gitops/<project_name>`", its Flag line widens to every action, and its Then line uses the identity probe.
- **AC8 — Green, no code.** `chain-completeness-check`, `story-status-check`, `spec-surface-check` (a scoped stamp per Spec it names), `governance-currency` and `tests/scripts/test_pre_shell_hook.py` exit 0; no file under `src/shared/packages/pyforge-steward/src/` changes; Story 118.3 stays `backlog`, and only the operator flips it `blocked`.

## Boundaries & Constraints

**Always:**
- Change `SPEC.md` only through memlog entries and a `bmad-spec` re-derive; change `docs/governance/guild-roster.json` `session_denials` only as a governance act, with its matcher in the same change.
- Read the nic source read-only.

**Never:**
- Never create a ruleset, a deploy key, a token, a branch or a Hetzner resource from an agent session (outward work); never hand-edit `SPEC.md`; never add a code ordering gate for the ruleset (Z2 settled for the refute skeptic); never add a cost or spend ceiling (AD-6, the cost Non-goal); never move Story 118.3's status.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-178 (with CAP-176 and CAP-177).

Parent: `spec-pyforge-steward` CAP-178

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack* (operator ruling 4), and its Realization log's 2026-11-01 (the EGM fleet audit) entry.
- Epic: Epic 118.
- Ledger key: `118-8-the-gitops-branch-has-one-named-writer-enforced`.
- Deps: —.
- Blocks: Story 118.3 (its Deps gained S-118.8 on 2026-11-01).
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`; the story's files are `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md` (re-derived), `_bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it.md`, `docs/dreams/pyforge-steward.md`, `docs/governance/guild-roster.json`, `.claude/hooks/pre-shell.py` and `tests/scripts/test_pre_shell_hook.py`.
- Audit: EGM audit 2026-11-01 findings STW-M-D1, STW-M-Z2, STW-M-Z6, STW-M-C4, STW-D-R1 (cluster STW-CL-5), STW-D-C5 (cluster STW-CL-6), STW-M-D5, STW-M-D2 (cluster STW-CL-7); residue `_bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Minted 2026-11-01 by the EGM fleet audit landing (marshal Story 113.7); parked at `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py -q` (the env `pyforge-doctor-scripts-test` runs `tests/scripts` in) — expected: pass, the new denial included.
- `grep -n 'CAP-178' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` — expected: the `--type capability` amendment present.
- `grep -n 'S-118.8' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it.md` — expected: exit 0.
- `git diff --name-only origin/main -- src/shared/packages/pyforge-steward/src` — expected: empty.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `spec-surface-check`, `governance-currency` — expected: exit 0 each.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), clusters STW-CL-5, STW-CL-6 and STW-CL-7, with the operator's ruling of the same date; parked at `backlog`. Deviation from the triage's fix steps: the `session_denials` entry and its `.claude/hooks/pre-shell.py` matcher land in one change here, not the entry here and the matcher in Story 118.3, because the hook refuses a declared rule with no matcher.

## Review Triage Log

- (none yet)
