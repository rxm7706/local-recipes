---
name: "a-union-merge-of-a-memlog-keeps-both-sides-frontmatter-updat"
description: "A union merge of a memlog keeps both sides' frontmatter updated: lines, and a memlog with two updated: keys is malforme…"
metadata:
  type: feedback
---

A union merge of a memlog keeps both sides' frontmatter updated: lines, and a memlog with two updated: keys is malformed (memlog.py and the YAML readers refuse it). After resolving a memlog conflict main-first, keep one updated: key, the later stamp, then scan: every tracked *.memlog.md frontmatter should hold exactly one updated: line (Story 100.7, 2026-10-14, fixed in commit 55ccdbb90c).
