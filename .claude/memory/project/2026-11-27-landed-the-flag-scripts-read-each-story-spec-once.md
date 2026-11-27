---
name: "2026-11-27-landed-the-flag-scripts-read-each-story-spec-once"
description: "2026-11-27 LANDED: the flag scripts read each story spec once and each path without walking its parents. PR #2440 merge…"
metadata:
  type: project
---

2026-11-27 LANDED: the flag scripts read each story spec once and each path without walking its parents. PR #2440 merged as 29745b439d (Merge pyforge-doctor/70-1 into main; doctor Story 70.1, spec-pyforge-steward CAP-175 realized with no text change), with 21 checks passed. scripts/flag_rule.py keeps each frontmatter block's YAML parse by its text and hands each caller a deep copy. repo_relative resolves only when the lexical form is not under the root, and flag_rule.lexical_tail answers relative_to with one comparison; flag_inventory._classify_surface uses it too. Locally, flag_inventory.py went from 17.0 s to 7.8 s and flag_gate_check.py from 4.75 s to 2.9 s, with identical reports, outputs, judgments and frontmatter reads. On CI, the Detectors workflow went from 129 s to 98 s, its library job from 124 s to 84 s, and scripts-lib-test from 58 s to 31 s. Levers still open: Detectors' scripts-suite (stdlib) at 94 s (24 s checkout, 51 s pyforge-doctor-scripts-test); atlas-test at 101-114 s; marshal-test (4) at 97 s against 78-85 s for the other shards; and the local full preflight's oversubscription, with 16 lanes at once each running -n auto, 345 s for 49 lanes.
