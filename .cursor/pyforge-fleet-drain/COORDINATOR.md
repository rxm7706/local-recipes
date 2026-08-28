# Fleet drain auto-coordinator

> **SUPERSEDED (2026-08-27, Story 22.7 / FR-193 CAP-7).** The marshal-native
> mode shipped: `marshal factory drain --mode drain_to_zero|leave_one|skip_on_blocked`.
> The marshal process itself now owns sequencing, so the singleton lock below
> is structural rather than a convention an operator must remember to honor.
> Kept as the historical record of the 2026-08-22/23 campaign — **do not
> replay this hand ritual.**

**Role:** Keep marshal + steward draining until `queues.yaml` shows both `drained: true`.

**Playbook:** [PLAN.md](./PLAN.md) — merge-in-agent, one story per station, parallel across stations.

---

## Singleton lock (HARD — always-on)

**Exactly one coordinator may run at a time.** Parallel coordinators caused Story 15-2 triple PRs [#657](https://github.com/rxm7706/local-recipes/pull/657) / [#658](https://github.com/rxm7706/local-recipes/pull/658) / [#659](https://github.com/rxm7706/local-recipes/pull/659) and double-dispatches for 17-1 / 13-3.

### Lock location

[STATUS.md](./STATUS.md) → **Coordinator lock** table. Fields:

| Field | Meaning |
|-------|---------|
| `owner` | Agent/session id that holds the lock (or `parent-chat` if this chat owns dispatch) |
| `held_since` | ISO / local timestamp when claimed |
| `state` | `active` \| `paused` \| `drained` |

### Claim / release

1. **Before** launching any coordinator Task (or before this chat resumes auto-dispatch): read STATUS.md.
2. If `state: active` and `owner` is a **different** live agent → **HALT**. Do not launch a second coordinator. Do not re-dispatch in-flight stories. Tell the operator.
3. To take over: set `state: paused` under the old owner (commit + push), then claim with your id + `state: active` (commit + push). Never claim over a live `active` lock without an explicit operator handoff.
4. On exit (drained or blocked): set `state: drained` or `paused` and clear in-flight rows.

### Parent chat vs background coordinator

- **Either** this Cursor parent chat **or** one background coordinator agent owns the loop — **never both**.
- Parent-chat follow-ups on subagent completions must **not** dispatch a new story if STATUS already lists that station as in-flight, or if a background `owner` is `active`.
- Background coordinator must re-read STATUS before every wave; if lock owner ≠ self → exit immediately.

### Story-level preflight (before every dispatch)

Skip dispatch if **any** of:

1. STATUS in-flight table already has that station
2. Open PR for the story (`gh pr list --search …`)
3. Remote branch `origin/<station>/<epic>-<story>-*` with unmerged work
4. Local worktree already implementing that story
5. Ledger already `done`

If a duplicate PR appears anyway: keep the earliest green merge; close later dups with a comment pointing at the canonical PR (as done for #658/#659 → #657).

---

## Loop (repeat until exit)

1. Confirm singleton lock: STATUS `state: active` and `owner` == this agent/session
2. `python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary`
3. `pixi run -e local-recipes fleet-picture` (ATTENTION block)
4. For each of **marshal**, **steward**:
   - Read ledger head from `queues.yaml` → `stations.<s>.next`
   - Apply story-level preflight above
   - **Skip policy:** steward `12-7` → if blocked on live OCP, skip to next non-12-7, report operator, do not redispatch 12-7
   - If spec missing: draft from `epics.md` (intent-contract shape), commit to main with `status: ready`
   - Launch `generalPurpose` background Task (`run_in_background: true`, **not** a fork) with Phase 2 prompt from PLAN.md
   - Update STATUS.md in-flight table **before** launch returns; commit + push to main
5. If both stations have in-flight agents or open PRs: wait (poll every ~10 min), rescue only on HALT/CI-stuck — **rescue reuses the same agent/worktree**; never spawn a second agent for the same story
6. **Exit** when `generate-queues.py --summary` shows marshal + steward both DRAINED or 0 left → release lock (`state: drained`)

## Wave queue (from queues.yaml order_overrides)

See [queues.yaml](./queues.yaml). Continue sequentially per station after the current in-flight pair.

## Hard rules

- Singleton lock (this document) — no second coordinator
- Never `scripts/bmad-switch` from parallel agents
- `BMAD_ACTIVE_PROJECT=pyforge-<station>` per dispatch
- Merge: `gh pr merge --merge` never squash
- Finalize scoped: `sprint-ledger-sync --project <station>`
