# Fleet drain auto-coordinator

**Role:** Keep marshal + steward draining until `queues.yaml` shows both `drained: true`.

**Playbook:** [PLAN.md](./PLAN.md) — merge-in-agent, one story per station, parallel across stations.

## Loop (repeat until exit)

1. `python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary`
2. `pixi run -e local-recipes fleet-picture` (ATTENTION block)
3. For each of **marshal**, **steward**:
   - Read ledger head from `queues.yaml` → `stations.<s>.next`
   - **Skip dispatch** if story already `done`, or open PR exists for that story, or remote branch `origin/<s>/<epic>-<story>-*` exists with unmerged work, or an agent is already in-flight for that station (see STATUS.md)
   - **Skip policy:** steward `12-7` → if blocked on live OCP, skip to `12-8`, report operator, do not redispatch 12-7
   - If spec missing: draft from `epics.md` (intent-contract shape), commit to main with `status: ready`
   - Launch `generalPurpose` background Task (`run_in_background: true`, **not** a fork) with Phase 2 prompt from PLAN.md
   - Update STATUS.md in-flight table; commit + push to main
4. If both stations have in-flight agents or open PRs: wait (poll every ~10 min), rescue only on HALT/CI-stuck
5. **Exit** when `generate-queues.py --summary` shows marshal + steward both DRAINED or 0 left

## Wave queue (from queues.yaml order_overrides)

See [queues.yaml](./queues.yaml). After 11-6 + 12-5: **marshal 12-1**, **steward 12-6**, then continue sequentially per station.

## Hard rules

- Never `scripts/bmad-switch` from parallel agents
- `BMAD_ACTIVE_PROJECT=pyforge-<station>` per dispatch
- Merge: `gh pr merge --merge` never squash
- Finalize scoped: `sprint-ledger-sync --project <station>`
