---
type: frame [0.3]
identifier: pyforge-steward
license: https://www.apache.org/licenses/LICENSE-2.0
name: pyforge-steward
description: Station Frame for Steward — provisioner of keys, deploy, provision, budget, workspace, upgrade, and suite. Load when running estate duties or opening worktrees.
visibility: private
owner: steward
version: 0.1.0
scope: station
inherits: pyforge
---

# Steward

- Grammar: `pyforge steward …` / `steward`. Do not import `pyforge.steward` internals.
- Duties return `DutyResult` and never `sys.exit`; `main()` owns the process exit code.
- Prefer `pyforge steward workspace start <slug>` over hand `git worktree add`.
- Owns the Intelligence Hub estate recording and in-repo Frame preflight. Relays Track to marshal and Frame-store pointers to scribe.
