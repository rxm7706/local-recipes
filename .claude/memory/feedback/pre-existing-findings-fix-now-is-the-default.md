---
name: "pre-existing-findings-fix-now-is-the-default"
description: "Pre-existing findings: fix-now is the default. \"Pre-existing\" explains why a finding is not yours — never why it stays.…"
metadata:
  type: feedback
---

Pre-existing findings: fix-now is the default. "Pre-existing" explains why a finding is not yours — never why it stays.

When a detector, test, or gate reports something your change did not cause, verifying that it is pre-existing answers "did I break this?" and nothing else. The only two legitimate reasons to leave it unfixed in the same sitting: (a) it is a Dream-sized effort (then seed the Dream, per the Dream-first rule); (b) it is blocked on something you can name (a ruling, a credential, a merge). "Another station's artifact", "needs judgment", "advisory in CI", "not in this PR's scope", and "recorded as deferred work" are not on the list — if the judgment is needed, make it or ask; if it is another station's file, edit it and say so in the PR. A deferred-work entry for something fixable now is a broken window with a label on it; never present one as closure.

**Why:** documenting a finding cannot be wrong, so under uncertainty agents drift toward it — that optimises the agent's own error rate, not the estate being correct, and it leaves `pr-preflight` red on every machine while reading as diligence. Live instance (2026-09-14): `detectors-ci` was red on `ad_citation_check` with 61 bare CAP/AD citations already on `origin/main`, plus 28 herald `drift-presumed` warnings; a careful DW entry was written and the work deferred with exactly those reasons. The operator's response was "why do you keep skipping pre-existing findings." The herald warnings took twenty minutes once the detector's own remedy line was read; all 61 citations were fixed by qualification the same hour, and the count itself was wrong (the detector prints ten rows per class). Earlier instance (2026-08-08): four failing meta-tests and 61 spec-surface findings carried across sessions as "byte-identical to HEAD" until the operator said "why leave broken windows"; three of four closed in under an hour.

**How to apply:** when reporting a pre-existing finding, state the disposition in the same breath — fixing now, or Dream-sized (seeded), or blocked on <named thing>. Read the detector's own remedy line before deciding it needs judgment. Check whether the detector truncates its output before recording a count. If the fix touches repo tooling itself (a detector, a check script), it is chain work — a Story under the owning Spec, not a hand-patch in a passing branch.
