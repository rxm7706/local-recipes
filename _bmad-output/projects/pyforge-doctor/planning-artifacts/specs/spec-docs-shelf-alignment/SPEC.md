---
id: SPEC-docs-shelf-alignment
status: ready
owner-dream: docs/dreams/docs-shelf-alignment.md
created: "2026-09-14"
updated: "2026-09-14"
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/docs-shelf-alignment.md
  - ../../../../../../docs/dreams/general-docs-consistency.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated
> contract for what to build, test, and validate. The source Dream is for
> traceability — consult it only for narrative rationale this contract
> intentionally omits.

# Leftover docs fold into Diátaxis, one page for both audiences

## Why

[[general-docs-consistency]] / Epic 22 shipped the map and the identity
detector. The leftover shelf is still here because that campaign forbade
touching `docs/specs/` and planning-artifacts, and because humans and
agents were left on different binders. A 2026-09-14 sweep named the
residue. The five design questions that kept this Spec at `draft` are
answered below; CAP-1..7 are now commitments.

## Capabilities

- **CAP-1**
  - **intent:** A fact useful to an operator lives once under `docs/` (or
    a named MAP exception). `AGENTS.md` / `CLAUDE.md` / `README.md` /
    `SKILL.md` point; they do not restate.
  - **success:** No operational procedure is copied verbatim across an
    entry point and a quadrant file without one side being a pointer.
    SKILL.md may keep wielding notes that name CLI grammar only.

- **CAP-2**
  - **intent:** Unique operational steps from marshal
    `development-guide.md` / `deployment-guide.md` and package
    air-gap/adoption guides land in the existing tutorial / how-to /
    explanation files. Those binders become stubs pointing at `docs/`
    and at `SYNC-RUNBOOK.md` for CFE pin re-ground. Redirect stubs in
    `docs/reference/` are deleted after the pointer sweep.
  - **success:** One tutorial path, one air-gap how-to, one air-gap
    explanation. No third copy. The planning tree still exists; the
    700-line mixed binders do not remain the human/agent split.

- **CAP-3**
  - **intent:** Sunset `docs/specs/` by frontmatter `status:`.
    `shipped` and `superseded` move to `archive/docs/specs/`.
    `in-progress` stays in `docs/specs/` until the effort closes.
    Each `workflow` file moves its body to `docs/how-to/`; a stub
    remains at `docs/specs/<name>.md` with `status: workflow` and a
    pointer — `bmad_drift_check.py --specs` only globs that directory
    and checks the CLAUDE.md filename index.
  - **success:** No shipped/superseded Tier-1 spec remains the live
    home. The three workflow procedures are findable as how-tos. A
    stub still makes `--specs` and the CLAUDE.md index true.

- **CAP-4**
  - **intent:** Route intake using `docs/intake/README.md` and
    `gists/INDEX.md`. Do not mint Dream YAML onto gist dumps.
  - **success:** Nothing a specified/realized/archived Dream already
    absorbed remains in intake.

- **CAP-5**
  - **intent:** Inbound links to the five files now under
    `archive/_bmad-output/` resolve.
  - **success:** `docs/intake/README.md` and station `specs/README.md`
    files cite the archive path. No live doc cites the old root path.

- **CAP-6**
  - **intent:** `docs/dashboard/kedro-viz/` stays the Kedro-Viz upload
    root. MAP/README state the rule: one subfolder per board; a Vizro
    tree is `docs/dashboard/vizro/` only when that board publishes.
    Do not mint an empty `vizro/` directory in this campaign.
  - **success:** MAP lists publish roots as outside the four quadrants.
    kedro-viz is not renamed. No empty `docs/dashboard/vizro/` exists
    unless an upload story created it.

- **CAP-7**
  - **intent:** A new Doctor source (not an extension of
    `general_docs_consistency`) flags a leftover-shelf file that is
    neither on the MAP, nor intake-routed, nor archived, nor a named
    exception — bounded, textual, warn-only, fail-open.
  - **success:** Re-adding a dated campaign note at `_bmad-output/`
    root, or a second air-gap how-to outside the cluster, is a finding
    with a quoted path. `general_docs_consistency` fixtures stay
    identity-only. Never a second PR gate.

## Constraints

- CAP-1..6 of `spec-general-docs-consistency` stay shipped.
- Dreams, active Tier-2 Specs, and Tier-3 output are not moved into
  Diátaxis. Extracting duplicate operational prose is allowed; moving
  `epics.md` is not.
- Relocate and correct; do not regenerate accurate prose.
- Doctor findings stay advisory — never a second PR gate.
- Do not mint Dream frontmatter onto raw gist files.
- Do not rename `docs/dashboard/kedro-viz/` to vizro.
- Do not mint an empty `docs/dashboard/vizro/` in this campaign.
- Workflow stubs stay at `docs/specs/*.md` so `--specs` keeps working.
- Decomposition is doctor Epic 23, not a steward epic.

## Non-goals

- A full editorial pass of skills, presentations, or recipe READMEs.
- Refreshing the five already-known stale reference files named as a
  non-goal of the parent Spec.
- Extending `general_docs_consistency` to do path occupancy.
- Billing, marketplace, or foundry-product docs.

## Success signal

Entry points are indexes; leftover shelf files are folded, archived, or
named on the MAP; legacy specs are sunset by `status:` with workflow
stubs left behind; intake matches its own routing rule; archive
citations resolve; `docs/dashboard/vizro/` does not exist unless a
publish story created it; a new warn-only Doctor source replays a
planted leftover-shelf fixture and stays silent on a clean MAP.

## Assumptions

- Parent Dream [[general-docs-consistency]] remains `realized`.
- Owner is doctor. Steward is kinship for archive-path convention only.
