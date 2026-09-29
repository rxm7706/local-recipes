# Backends and sources (companion)

Load-bearing tables for `spec-self-hosted-bmad-marketplace`. The kernel cites
this file; do not duplicate the rows in SPEC.md.

## Ship backends (execution layer)

Config names which backends are active. Git is never a ship backend — it is
the edit store.

| Backend | What it does | v1 default |
|---|---|---|
| conda / pixi channel | noarch index package; SelfExplainML locally; Artifactory when air-gapped | on |
| object storage | same snapshot as a blob on the consumed S3-style store (Epic 50) | off |
| git bundle / tarball | same snapshot as a file | available |

A new backend implements the same snapshot interface. It does not change
CAP-1..4.

## Sources (what may appear on the list)

| Source | What it feeds | v1 default |
|---|---|---|
| estate listings | YAML we authored and steward reviewed | on |
| wielded suite | official modules we already install | on |
| public BMAD catalog | their marketplace, cited, never a blind mirror | off |
| estate Frames | `docs/foundry/frames/` | on |
| Claude-skill registry | `skillsctl` (SKU B) | empty slot |

A listing names exactly one source. It cannot appear without steward review
unless it is already in the wielded suite (Certified).
