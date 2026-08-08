# pyforge-warden — Epic 5 & 6 Retrospective (effort closeout)

**Date:** 2026-07-25 · **Facilitator:** Amelia (Developer, adapted) · **Project Lead:** rxm7706
**Scope:** Epic 6 (multi-axis expansion, 10 stories) + Epic 5 (fleet-readiness, 2 stories) — the final two epics, completed this session and merged to main via **PR #110**. Warden is **31/31, all 6 epics done**.

> **Format note.** This is a solo / AI-driven loop effort, not a multi-person team. The retro's *substance* (lessons, action items, readiness) is run faithfully; the party-mode team-dialogue theater is intentionally omitted rather than fabricated — inventing struggles that didn't happen would be dishonest and useless. Findings below are grounded in the live run journals, story specs, and this session's record.

## 1. Summary

Eight stories driven to done this session via bmad-loop under `per-story-spec-approval` (6.3 → 6.5 → 6.7 → 6.8 → 6.9 → 6.6 → 5.1 → 5.2; 6.10/6.1/6.2/6.4 predate this session). Each gate got an independent frozen-trio scope-check + a canonical `--frozen` verify. Final validation on the merged tree: **fast suite 1,936 passed**, **slow corpus/oracle suite 11 passed** (2,000-recipe corpus + differential-oracle + strace egress counter proving 0 network), **dogfood self-scan** composes `bypassed`/exit 0. Closed out with a git-history purge of a rotated leaked credential + `copilot-to-api.md`, then the batch-PR.

## 2. What went well

- **The frozen-schema discipline held perfectly.** Every one of the 8 gates was scope-checked (`git diff` of `report-schema.json` / `models.py` / `verdict.py` == empty). All 8 came back clean — the guard cost seconds and gave real confidence that no producer widened the contract 6.1 froze.
- **Adversarial review earned its keep.** The loop's reviewers caught genuine, security-relevant defects: 6.3's alias-collision silent-misroute; 5.1's **cross-package fixed-version attribution** (a wrong "upgrade to ≥X" remediation — Warden's cardinal false-green risk) and a `--doctor` TOCTOU crash. All fixed with tests before merge.
- **Model tiering worked as designed.** Sonnet default; opus for the two hard stories (6.5, 6.9). No quality regressions traced to tier.
- **The fleet-scale validation is real, not decorative.** 5.2's strace egress counter proves the socket-deny promise across a full 2,000-recipe scan; the dogfood scan runs Warden on itself and exits clean.
- **The history purge executed cleanly** — verified byte-identical HEAD trees, exactly-the-leaked-files diff on the loop branch, zero-conflict merge preserving all of main's session work.

## 3. Challenges

- **bmad-loop idle-strand was the dominant friction.** A mid-response API "Connection closed" leaves the dev/review session parked at the prompt until the per-session token cap (~4M weighted) or time cap fires, *then* defers. It hit **6.8 (dev attempt 1)**, **6.9 (BOTH dev attempts → deferred)**, and **5.1 (review-1 crossed the 4M cap)**. Real wall-clock and token cost, and it turned 6.9 into a manual recovery.
- **6.9 required hand recovery.** The stalled session had *committed* its work (`f8e1648d2c`) before dropping; the loop deferred the story but the commit survived on the story branch. Recovering it (scope-check + full suite + manual adversarial review → labeled merge) worked but is off the happy path.
- **Follow-up-review debt.** Several stories flagged `followup_review_recommended: true` (6.2, 6.3, 6.7, 6.8, 5.1, 5.2). This resolved better than feared (see lessons) but 6.2's `license.py` follow-up remains genuinely advisable.
- **Artifact fragility.** Some warden impl-artifacts are 0-byte husks (spec-1-1..1-4), same Tier-3 truncation class as atlas — the durable record is the merged PRs + memory, not these files.

## 4. Lessons learned

1. **Idle-strand is the #1 process gap** — and the fix belongs in bmad-loop (idle timeout / keepalive nudge / shorter session cap), not in per-run babysitting. The external tmux+log-mtime strand watchdog (25-min threshold) was an effective *stopgap* this session; it should not be the permanent answer.
2. **A stalled-but-committed story is recoverable, deterministically:** the dev commit survives on `bmad-loop/<run>/<story>`; verify the frozen trio is empty + the full suite is green + do the review the stall skipped, then `git merge --no-ff` with the exact `Merge bmad-loop/<run>/<story> …` subject (the dashboard's git-mode detection keys on it).
3. **Verify a hypothesized bug against the validation layer before patching.** On 6.9 I proposed a guard for an `IndexError` in `plan_remediations` — then the regression test *couldn't construct the input* because `Finding.__post_init__` validates the id family. The "bug" was unreachable; I reverted the dead defensive code and merged the original. Adversarial *verification* is as important as adversarial *hunting*.
4. **The loop auto-discharges follow-up reviews on resume.** 5.1's `followup_review_recommended: true` made the resume run the deeper review *inline* (two cycles) before merging — so the "combined review debt" I kept deferring was largely paid automatically. Trust the resume to run the follow-up; don't hand-track it as separate debt.
5. **History-rewrite gotcha:** a branch that forked *before* a file's HEAD-removal still carries the file in its tree — merging it reintroduces the file. The loop branch had exactly this (it forked pre-removal), so the purge had to rewrite the loop branch too, or PR #110 would have re-added the leaked files. Purge *every* branch that forks before the removal.

## 5. Action items

| # | Action | Owner | Status |
|---|---|---|---|
| A1 | **bmad-loop idle-strand detection** — add an idle-timeout / keepalive to the session watchdog so a dropped API connection defers fast instead of burning the ~4M session cap. Retire the external strand-watchdog stopgap once landed. | rxm7706 (next bmad-loop touch) | open |
| A2 | **Document the stalled-but-committed recovery procedure** (lesson 2) in the bmad-loop notes / pyforge-warden memory so it's not re-derived under pressure. | rxm7706 | open (captured in memory) |
| A3 | **Follow-up review of `license.py` (6.2)** — landed at the 3-review-cycle cap; a fresh independent pass on this compliance-critical axis remains advisable (also flagged in PR #109). | rxm7706 | open |
| A4 | **Verify-before-patch as review doctrine** (lesson 3): when a review hypothesizes a defect, test its reachability against the model/validation layer before writing a fix. | crew practice | adopted |
| A5 | **History-rewrite playbook** (lesson 5): fresh-clone `git-filter-repo` when worktrees exist; purge all branches that fork before a HEAD-removal. | rxm7706 | captured in deferred-history-purge memory |

## 6. Readiness assessment

- **Testing/quality:** ✅ fast 1,936 + slow corpus/oracle 11 (incl. egress proof) + dogfood exit 0; frozen trio untouched.
- **Deployment:** ✅ merged to `main` (PR #110, tip `d6a86780`). Release gate `v1-publish-jfrog-internal-and-v1x-public-pypi-conda-forge` is **unblocked** (6.6 landed the version-range pins + `--version` pre-flight).
- **Security:** ✅ leaked `sk-ant` key rotated (user-confirmed) + purged from all git history.
- **Blockers:** none. Warden is complete; the v1 publish is a release-gate, not a further epic.

## 7. Next

No next epic — Warden's 6 epics are done. The forward work is the **v1 publish** (release-gate, separate from story flow) and A1–A3 above. The single highest-leverage follow-up is **A1 (bmad-loop idle-strand detection)** — it cost the most this session and benefits every future loop effort.
