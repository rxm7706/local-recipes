---
name: "2026-11-27-landed-the-guild-image-s-secret-scans-pass-and-do"
description: "2026-11-27 LANDED: the guild image's secret scans pass, and doctor's live test runs on a dispatched run. PR #2444 merge…"
metadata:
  type: project
---

2026-11-27 LANDED: the guild image's secret scans pass, and doctor's live test runs on a dispatched run. PR #2444 merged as 17fa5148e3 (Merge pyforge-steward/118-10 into main; steward Story 118.10, doctor Story 71.1), with 54 checks passed and 8 skipped. Since PR #2425 (Story 118.9) every push to main had failed both guild-container jobs on six lines of django-pyforge's test keypair. golden.py now holds that base64 at 76 a line, wraps it at 64 at load, and formats its private PEM header at load; warden's hygiene.py and vuln.py build their token sets from the string module. The PEM strings and the sets are unchanged, and steward's secret table does not change. tests/scripts/test_guild_image_package_sources_scan_clean.py scans the shipped package sources and their compiled code on every pull request. doctor-live-test's step that names the base tip as origin/main now also runs on workflow_dispatch, fetching main and deepening until git merge-base resolves. A marshal copier-update test failure seen the same day did not reproduce and is recorded on its own (PR #2445).
