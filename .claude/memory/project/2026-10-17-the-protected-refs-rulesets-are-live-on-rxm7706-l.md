---
name: "2026-10-17-the-protected-refs-rulesets-are-live-on-rxm7706-l"
description: "2026-10-17: the protected-refs rulesets are live on rxm7706/local-recipes, matching docs/governance/rulesets/protected-…"
metadata:
  type: project
---

2026-10-17: the protected-refs rulesets are live on rxm7706/local-recipes, matching docs/governance/rulesets/protected-refs.json (protected_refs_ruleset_check.py exit 0): protected-refs-attempt-preserve-branches, protected-refs-loop-branches, protected-refs-tags (archive/preserve/rescue tags: no delete, update or force-push) and protected-refs-restrict-preserve-branch-creation (no new preserve/** or archive/** branches), all with no bypass actors -- not even the operator can delete or move a protected tag without first turning the ruleset off. The undeclared protected-refs-no-deletion ruleset was deleted on purpose: recover/** branches must stay deletable because worktree_sweep's retire flow archives them to a tag and then deletes them. AGENTS.md's 'server rulesets remain the guarantee' now holds live.
