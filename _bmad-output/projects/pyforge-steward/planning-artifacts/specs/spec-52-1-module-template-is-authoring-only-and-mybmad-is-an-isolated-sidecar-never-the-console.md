---
title: 'Module-template is authoring-only and mybmad is an isolated sidecar never the console'
type: 'feature'
created: '2026-09-13'
status: 'backlog'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The 2026-09-06 adoption register left `bmad-module-template` (row 11)
and `mybmad-dashboard` (row 13) at `skip`. The campaign now wants every suite
member wielded, but those two cannot be wielded as modules or as `/console/`.
Silent register edits violate CAP-1 (a row changes only by Story).

**Approach:** One Story flips both rows. module-template becomes **authoring
tool only** beside `bmad-builder` — documented path, never
`steward provision --module` into `.claude/skills/`. mybmad becomes **isolated
opt-in sidecar** via the existing `mybmad` launcher. It is not `/console/`
because it carries its own Postgres and its own auth; `/console/` is
django-pyforge + Keycloak/OIDC + `DATABASE_URL`. `bmad-dashboard` (row 12)
already holds the same never-console rule for the VS Code surface.

## Boundaries & Constraints

**Always:**
- Change rows 11 and 13 through this Story plus a memlog line on
  `spec-bmad-suite-lifecycle`; re-derive that SPEC with `bmad-spec` (never
  hand-edit `SPEC.md`).
- Keep `retired-console-check` green: no second Guildhall-class console.
- Keep Epic 44 `blocked` keys untouched.

**Never:**
- Never provision `bmad-module-template` into `.claude/skills/`.
- Never mount mybmad at `/console/`, join it to platform OIDC, or make it a
  PR / `detectors-ci` gate.
- Never treat this Story as permission to replace the django-pyforge host.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Authoring a new BMAD module | operator + `bmad-builder` + template | Scaffold used off-tree; `.claude/skills/` unchanged | `steward provision --module` of the template is refused or undocumented-as-forbidden |
| Operator wants BMAD UI | `mybmad` launcher | Sidecar process, own datastore/auth | Not reachable as `/console/` |
| Operator wants the estate console | browser → `/console/` | django-pyforge + OIDC unchanged | n/a |
| pipeline-truth | register after flip | `wired` agrees: template not a module; mybmad launcher-only | mismatch fails the story |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` — rows 11 and 13.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md` + `bmad-spec` re-derive of `SPEC.md` Non-goals.
- Steward / `bmad-builder` docs for the authoring path.
- `mybmad` launcher docs (feature `bmad-ui`): isolation contract.

## Acceptance Criteria

1. Register row 11 is `wield (authoring tool only)`; row 13 is `wield (isolated opt-in sidecar)`.
2. Lifecycle SPEC Non-goals re-derived: no longer "skip these two"; authoring-tool + sidecar contract instead.
3. No `/console/` mount, no platform OIDC join, `retired-console-check` green.
4. `pipeline-truth` `wired` agrees with the register.
5. Ledger key `52-1-module-template-is-authoring-only-and-mybmad-is-an-isolated-sidecar-never-the-console` exists; this Story does not self-close as `done` in the mint commit.
