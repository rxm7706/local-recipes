---
title: 'The cluster bring-up is documented, reproducible, and key-disciplined'
type: 'feature'
created: '2026-08-23'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment/cluster-bringup-facts.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 12.1 shipped the vanilla chart + OCP overlay, but no reproducible path exists from a fresh workstation to a Running OpenShift Local cluster with the platform image in the internal registry — CAP-1 is unowned, and the steward keys inventory has no OCP/GitHub credential rows yet.

**Approach:** Add `src/platform/deploy/overlays/ocp/cluster-bringup.md` — the operator-locked bring-up runbook grounded in `cluster-bringup-facts.md` (CRC 2.63.0 / OpenShift 4.22.7) covering both the Podman Desktop extension path and the Linux `crc`-on-PATH path, the internal-registry push pattern, and helm image-registry seams. Seed `.steward/keys-inventory.yaml` with the first three `provenance: observed` entries (pull secret, kubeadmin, GitHub PAT metadata only). Cross-link from `deploy/README.md` and `overlays/ocp/README.md`.

## Boundaries & Constraints

**Always:**
- Document only verified facts from `cluster-bringup-facts.md` and shipped deploy surfaces — no improvised steps.
- Internal-registry push is the canonical image path (`podman login/tag/push` → ImageStream); never `--docker-image` / host-socket shortcuts.
- Platform image build uses repo-root context: `podman|docker build -f src/platform/Containerfile -t … .` (Story 10.3 contract).
- Keys inventory stores metadata only — never pull-secret JSON, kubeadmin password, or PAT values.
- helm/kubectl from `platform-dev` pixi env (pap:AD-16).

**Block If:** none — documentation + inventory seeding only; live cluster not required for this story.

**Never:**
- No chart template changes (Stories 12.5–12.7).
- No live-cluster verification claims (Story 12.7).
- No secrets committed; no `steward keys encrypt` automation in this story.
- No sprint-status-ledger edits.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Podman Desktop path | Extension + pull secret on first start | Doc reaches Running + `oc whoami` = kubeadmin | Doc names extension catalog + Linux `crc` prerequisite |
| Linux crc path | `crc` 2.63.0 on PATH, 4 cores / 10.5 GB / 35 GB free | `crc start` → Running; `eval $(crc oc-env)` | Doc cites unsupported Ubuntu/Debian explicitly |
| Registry push | Built `platform:local` image | ImageStream `<project>/platform:local` pullable in-cluster | Doc includes `--tls-verify=false` + kubeadmin token login |
| Keys inventory | Fresh repo clone | `.steward/keys-inventory.yaml` loads via `load_inventory`; three observed rows | Conformance test proves parseability |
| helm lint | Unchanged charts | `helm lint` core + overlay green | N/A |

</intent-contract>

## Code Map

- `src/platform/deploy/overlays/ocp/cluster-bringup.md` — NEW bring-up runbook (CAP-1)
- `.steward/keys-inventory.yaml` — NEW first credential inventory entries (metadata only)
- `src/platform/deploy/README.md` — link OpenShift section to bring-up doc
- `src/platform/deploy/overlays/ocp/README.md` — link prerequisites to bring-up doc
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_list.py` — assert repo inventory loads
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment/cluster-bringup-facts.md` — read-only ground truth

## Tasks & Acceptance

**Execution:**
- [x] `cluster-bringup.md` — document both bring-up paths, login, keys discipline, image build, internal-registry push, helm image `--set` seams, verification checklist
- [x] `.steward/keys-inventory.yaml` — three `observed` entries: pull secret, kubeadmin, GitHub PAT (`read:project`)
- [x] `deploy/README.md` + `overlays/ocp/README.md` — cross-links; scope OCP "Honest limitations" to attended overlay verification (12.7), name bring-up doc as the cluster path
- [x] `test_keys_list.py` — `test_repo_keys_inventory_yaml_loads` against `default_inventory_path()`

**Acceptance Criteria:**
- Given a fresh workstation and only this repo's docs, when the operator follows `cluster-bringup.md` end to end, then they reach cluster Running, `oc` authenticated, platform image pushed via the internal registry, with zero steps outside the doc.
- Given the three cluster/GitHub credentials obtained during bring-up, when recorded per the doc's keys discipline, then `.steward/keys-inventory.yaml` lists them as `provenance: observed` with no secret values anywhere in git.
- Given unchanged charts, when `pixi run -e platform-dev helm lint …` runs, then both charts pass.

## Spec Change Log

## Review Triage Log

## Design Notes

- Mints the OpenShift/registry-posture AD the steward spine anticipates (`epics.md` Story 12.4 FR/AD).
- Story 12.9's optional CI job will consume the registry commands from `cluster-bringup-facts.md`; this story lands the human runbook those commands belong to.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `3773229684` (2026-08-23, "Merge pull request #638 from rxm7706/steward/12-4-cluster-bringup"). Ledger row `12-4-the-cluster-bring-up-is-documented-reproducible-and-key-disciplined: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.steward/keys-inventory.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-4-the-cluster-bring-up-is-documented-reproducible-and-key-disciplined.md`, `src/platform/deploy/README.md`, `src/platform/deploy/overlays/ocp/README.md`, `src/platform/deploy/overlays/ocp/cluster-bringup.md`, `src/shared/packages/pyforge-steward/tests/conformance/test_keys_list.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
