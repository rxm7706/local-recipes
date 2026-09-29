---
title: '31.2: How to deploy the docs site to GitHub Enterprise Pages'
type: 'docs'
created: '2026-09-28'
status: 'backlog'
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: docs-only
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-31-1-the-pages-artifact-builds-for-the-host-that-deploys-it.md
  - docs/how-to/air-gapped-mirror-setup.md
  - docs/map.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 31.1 makes the one Pages build take the site URL and base path of the host that
deploys it, so the enterprise copy of the repository can deploy the same artifact to an internal
GitHub Enterprise Pages site. No written procedure covers the enterprise side, so the second host
would live in one person's head.

**Approach:** One how-to, `docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md`, in the
Diátaxis how-to shape. It covers:
- keeping the enterprise copy of the repository in step with `main`;
- enabling Pages with GitHub Actions as its source;
- a runner that reaches the internal conda mirror, by linking `docs/how-to/air-gapped-mirror-setup.md`
  rather than restating it;
- turning `pyforge.herald.pages_second_host` on;
- checking the deployed site with `pages-check` and with a browser that has no route to the
  internet.

The page is registered in `docs/map.yaml`, doctor's registry, with a co-governor reconcile on
`spec-pyforge-doctor`. `docs/MAP.md` is re-rendered with `docs-map-render`, and
`docs/how-to/README.md` gains one link line.

Ledger key: `31-2-how-to-deploy-the-docs-site-to-github-enterprise-pages`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: docs / S / S-31.1.
Flag: exempt, `docs-only` (`feature-flag-governance:CAP-1`, the closed list).

### Living CAP citations

- `spec-pyforge-herald` CAP-56 (FR-10.5; decision D6 in `.memlog.md`); AD-21 (amended 2026-09-28 (night)).
- `spec-pyforge-doctor` governs `docs/how-to/**` and `docs/map.yaml`.

## Acceptance Criteria

- Given the how-to When it is read Then it names each enterprise-side step with its command or setting, in order, and ends with the check that the deployed site makes no request to another origin
- Given the how-to When it mentions the conda mirror Then it links `docs/how-to/air-gapped-mirror-setup.md` and restates none of it
- Given `docs/map.yaml` When `docs-map-hygiene-check` runs Then the page is listed once (quadrant how-to, owner herald, kind authored) and the check exits 0
- Given `docs/MAP.md` When `docs-currency-check` runs Then it exits 0

## Tasks

- [ ] Write the how-to
- [ ] Add its `docs/map.yaml` row and re-render `docs/MAP.md` with `docs-map-render`
- [ ] Add the link line to `docs/how-to/README.md`
- [ ] Spec-surface reconcile on `spec-pyforge-herald` and `spec-pyforge-doctor`, then one scoped stamp each

## Boundaries & Constraints

**Always:**
- Link, never copy: the air-gapped mirror steps stay in their own how-to.
- Every command in the page resolves in this repository (`docs-currency-check`).
- The PR carries the `maintenance` label.

**Never:**
- Do not add a workflow, a second artifact or a second deploy caller; the page documents Story 31.1's mechanism only.
- Do not put a credential, token or internal hostname of a real enterprise in the page; use `ghe.example`.
- Do not edit another station's pages beyond the one `docs/map.yaml` row and the `docs/how-to/README.md` link line.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new page | not in `docs/map.yaml` | `docs-map-hygiene-check` reds until the row lands | exit 1 then 0 |
| stale command | a backticked task that does not exist | `docs-currency-check` reds | fix the page |
| restated mirror steps | copied text | review finding | link instead |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald` CAP-56 (FR-10.5; D6).
Architecture: AD-21 (amended 2026-09-28 (night)).
Dream: `docs/dreams/pyforge-herald.md` § Realization log → *2026-09-28 (night) — Proposed: a deck can be read inside the airgap, from the portal and from an internal Pages site, and each current export is also kept in object storage*.
Ledger key: `31-2-how-to-deploy-the-docs-site-to-github-enterprise-pages`.
Ledger status at mint: `backlog`.
Deps: S-31.1 (the mechanism the page documents).
Flag: exempt, `docs-only`.

## Epic excerpt

**Type:** docs • **Effort:** S • **Deps:** S-31.1 • **FR/AD:** spec-pyforge-herald CAP-56 (FR-10.5; D6); AD-21 • flag-exempt: docs-only

**Given** Story 31.1 makes the build take the deploying host's URL, and no written procedure exists for the enterprise side
**When** the how-to lands
**Then** it names each enterprise-side step with its command or setting, links the air-gapped mirror how-to instead of restating it, and ends with the check that the deployed site makes no request to another origin
**And** `docs-map-hygiene-check` and `docs-currency-check` exit 0, and `pyforge-herald-test` is green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild docs-map-hygiene-check` — expected: exit 0.
- `pixi run -e pyforge-guild docs-currency-check` — expected: exit 0.
- When Story 27.4 has landed: the docs validators (`validate-doc-links.js`, `validate-sidebar-order.js`) exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and the scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Review Triage Log
