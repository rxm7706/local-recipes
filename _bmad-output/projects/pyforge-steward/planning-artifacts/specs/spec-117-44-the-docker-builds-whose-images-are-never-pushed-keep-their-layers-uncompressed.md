---
title: '117.44: The docker builds whose images are never pushed keep their layers uncompressed'
type: 'chore'
created: '2026-11-28'
status: 'in-progress'
story: 117-44-the-docker-builds-whose-images-are-never-pushed-keep-their-layers-uncompressed
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'scripts/guild_image_ci.sh'
  - '.github/workflows/platform-ci.yml'
  - 'docs/reference/github-workflows.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** the runner's docker stores images in containerd and compresses every layer when a build exports it. On the push to `main` of 2026-11-28, that export took 167 s of the guild image's 345 s build, 48.8 s of Platform CI's `container` (docker) build and 45.4 s of `container-dbgpt` (docker). Those images are only run on the runner, by the gates and smoke tests that follow, and then deleted: nothing pushes them or records their IDs. A local benchmark on the same docker (29.9, containerd snapshotter) exported a 400 MB layer in 7.9 s compressed and 2.3 s uncompressed.

**Approach:** the docker leg of each of those three builds writes its image with `--output type=image,name=<tag>,compression=uncompressed` in place of `-t <tag>`. The image is tagged and loaded as before, and every gate and smoke test runs it by the same name. Podman's legs are unchanged (podman stores layers uncompressed already). The golden-path promotion's builds are unchanged: it records their image IDs and may push them by digest. `build-platform-image` is unchanged: its images go to the portability smokes' clusters.

Ledger key: `117-44-the-docker-builds-whose-images-are-never-pushed-keep-their-layers-uncompressed`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change); works with CAP-131 (the image proves itself at build time).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Each image keeps its name, and every gate and smoke test still runs it.

**Never:**
- Never change a build whose image is pushed, recorded by ID or loaded into a cluster.

## Acceptance Criteria

**Given** a docker leg of the guild, platform or dbgpt image build
**When** it builds
**Then** its image is stored uncompressed under the same name, and its gates pass
**And** the podman legs and the golden-path promotion build as before

- **AC1 — A dispatched run.** Both `guild-container` legs pass, and the docker leg's `exporting layers` line is well under its 167 s.
- **AC2 — Platform CI on a dispatched run.** `container` and `container-dbgpt` pass on both engines.

</intent-contract>
