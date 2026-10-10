## Title

Close superseded staged-recipes PRs #33977 and #33978 (lfx-arxiv, lfx-docling bundles)

## Body

`langflow-feedstock` now publishes the lfx-arxiv and lfx-docling bundles. The operator's staged-recipes PRs **#33977** (`lfx-arxiv`) and **#33978** (`lfx-docling`) are superseded and should be closed with a short comment pointing at the feedstock packages.

## Reproduce or evidence

- mason Story 25.15 deferred row — five duplicate langflow-suite directories retire into `recipes/langflow`
- `archive/docs/specs/langflow-conda-forge.md:155-156` — cites #33977 and #33978

## Local workaround

Work proceeds from `recipes/langflow` and the feedstock; no need to merge the staged-recipes PRs.

## What resolution unblocks here

Retire registry item `staged-recipes-lfx-bundles-superseded` after the operator closes both PRs (kind `pr-close`).
