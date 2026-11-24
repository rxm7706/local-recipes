---
name: "never-fetch-history-in-a-pages-or-docs-site-workflow-with-gi"
description: "Never fetch history in a Pages or docs-site workflow with git's --filter=tree:0: Starlight's last-updated lookup runs g…"
metadata:
  type: feedback
---

Never fetch history in a Pages or docs-site workflow with git's --filter=tree:0: Starlight's last-updated lookup runs git log --name-status over the docs, and on a treeless partial clone every commit it walks fetches its trees one request at a time, so the Astro build runs silent until the job's 20 minute timeout cancels it (PR #2378, 2026-11-22: two Pages builds cancelled, no error in the log). Use --filter=blob:none, which keeps trees local and still skips file contents: git fetch --no-tags --filter=blob:none --unshallow origin <sha>. steward's test_pages_yml_never_fetches_history_without_trees reds a tree:0 filter in pages.yml. A silent CI build that hits its timeout on a step that reads git history is this trap until a tree filter is ruled out.
