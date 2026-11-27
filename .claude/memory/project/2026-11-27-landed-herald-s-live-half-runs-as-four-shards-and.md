---
name: "2026-11-27-landed-herald-s-live-half-runs-as-four-shards-and"
description: "2026-11-27 LANDED: herald's live half runs as four shards, and its site builds write Pagefind's files whole under load.…"
metadata:
  type: project
---

2026-11-27 LANDED: herald's live half runs as four shards, and its site builds write Pagefind's files whole under load. PR #2438 merged as f1a1baa064 (Merge pyforge-steward/117-33 into main; herald Stories 63.1 and 64.1, steward Story 117.33, spec-pyforge-steward CAP-175 realized with no text change), with 50 checks passed. In 63.1, test_53_3_no_framed_page_without_the_export_or_without_the_shell split into the check on shell and a test that makes its own build, and a guard reds a grouped test that builds. In 117.33, herald-live-test runs with --splits 4. In 64.1, docs-site/package-lock.json moves Pagefind's nine packages from 1.5.2 to 1.6.0, which ends the two-builds test's flake (truncated service-mode output). Measured on CI: herald's slowest live job went from 108-111 s to 94-97 s, and its tests from 63-72 s to 53-59 s. Measured and left: lint-types' pixi setup (52 s: a 1.82 GB cache, 33 s of it untarring; a trimmed environment would save 5 to 8 s on a job PRs do not wait on). Levers still open: Detectors' scripts-suite library part (98 s: an 18 s full-history checkout, 24 s for two environments, 44 s of scripts-lib-test), Platform CI's 45 to 50 s of fixed setup per shard, and herald-live's about 40 s per job.
