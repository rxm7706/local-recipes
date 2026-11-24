---
name: "when-resolving-a-merge-conflict-as-a-union-keep-theirs-then"
description: "When resolving a merge conflict as a union, keep theirs then ours with no de-duplication: a union that drops 'our' line…"
metadata:
  type: feedback
---

When resolving a merge conflict as a union, keep theirs then ours with no de-duplication: a union that drops 'our' lines already present on their side silently deletes blank lines, a story's **Flag:** and **HARD boundaries:** lines and a TOML block's closing bracket (seen 2026-11-21 on steward epics.md and marshal-policy.toml). After any union, compare your own blocks with the pre-merge commit and parse every TOML/YAML file you resolved.
