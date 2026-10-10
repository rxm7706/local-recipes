# Preserve manifests (marshal)

Operator-facing JSON manifests produced by recovery tooling — not generated during CI.

- **`orphan_tip_archive.py`** (Story 87.16) writes `orphan-tip-archive-<YYYY-MM-DD>.json` after a dry run. Review rows, mark `reviewed` when ready, then run with `--execute` on the primary clone. Push only after Story 87.15's content gate and explicit operator confirmation.
