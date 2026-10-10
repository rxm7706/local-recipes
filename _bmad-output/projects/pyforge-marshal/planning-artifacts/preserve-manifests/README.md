# Preserve manifests (marshal)

Operator-facing JSON manifests produced by recovery tooling — not generated during CI.

- **`orphan_tip_archive.py`** (Story 87.16) writes `orphan-tip-archive-<YYYY-MM-DD>.json` after a dry run. Review rows, mark `reviewed` when ready, then run with `--execute` on the primary clone. Push only after Story 87.15's content gate and explicit operator confirmation.
- **`legacy_preserve_promote.py`** (Story 87.12) writes `legacy-preserve-promote-<YYYY-MM-DD>.json` listing legacy refs, proposed `preserve/` or `archive/` twins, `rescue/dangling-*` classifications (no tag changes), and operator-gate rows for ruleset/roster updates. Run `--execute` on the primary clone after review; use `--push-reviewed` only on rows marked `reviewed` in the manifest.
