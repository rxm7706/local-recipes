---
name: "a-scoped-spec-surface-stamp-scripts-spec-surface-check-py-wr"
description: "A scoped spec-surface stamp (scripts/spec_surface_check.py --write-baseline --spec X) reconciles a drifted path only wh…"
metadata:
  type: feedback
---

A scoped spec-surface stamp (scripts/spec_surface_check.py --write-baseline --spec X) reconciles a drifted path only when the Spec's .memlog.md text contains that path's FULL repo-relative string (the rule is 'path in memlog_text'): a memlog line that groups files by directory or names only basenames reconciles nothing and the stamp refuses with 'baseline untouched' and an --accept list. Name every drifted path in full in the memlog event (the refusal prints the exact list), then stamp. Caught 2026-10-27 landing steward 117.4 (113 marked test modules).
