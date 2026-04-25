# Skill Automation

Scheduled jobs that keep the `conda-forge-expert` skill aligned with upstream conda-forge changes. The canonical job is the **quarterly live-doc audit** — it fetches conda-forge.org/news/, the pinning feedstock, rattler-build releases, and other upstream sources, then opens a PR with surgical edits to the skill (or appends a no-op entry to `AUDITS.log` if nothing changed).

## Where the routine lives

The audit is registered as a **remote Claude Code routine** in Anthropic's cloud. The routine config (cron, environment, prompt, allowed tools) is stored at `claude.ai/code/routines`, **not** in this repo. Each fire spawns an isolated cloud sandbox with a fresh git checkout — your local machine doesn't need to be on for it to run.

| Field | Value |
|-------|-------|
| Routine ID | `trig_015z9XF8ExDJuN9qsZYGYKcu` |
| Name | `conda-forge-expert quarterly doc audit` |
| Cron | `0 14 1 */3 *` (Jan/Apr/Jul/Oct 1 at 14:00 UTC) |
| Local time | 9:00 AM America/Chicago in CDT months (Apr/Jul/Oct); 8:00 AM in CST (Jan) |
| Repo | `https://github.com/rxm7706/local-recipes` |
| Environment | `local-recipes` (anthropic_cloud) |
| Model | `claude-sonnet-4-6` |
| Manage at | `https://claude.ai/code/routines/trig_015z9XF8ExDJuN9qsZYGYKcu` |

The exact prompt the routine runs is committed alongside this README at [`quarterly-audit.prompt.md`](quarterly-audit.prompt.md) so it stays under version control even though the trigger lives elsewhere.

## Choosing where to run an audit

| Mode | Runs where | When to use |
|------|------------|-------------|
| **Remote routine (default)** | Anthropic's cloud sandbox | Background, hands-off, opens a PR you review later. Picked because it doesn't need your laptop on and it works against a clean checkout. |
| **Local on-demand** | Your machine via `claude` CLI | You want to test prompt changes, run an off-cycle audit, or work without internet for the cloud sandbox. See [`run-audit-local.sh`](run-audit-local.sh). |
| **Local on a schedule** | Your machine via `cron` / `systemd` | You'd rather pay nothing for cloud runs and accept the laptop-must-be-on tradeoff. Same script, just wired to your local scheduler. |

The remote and local modes share the same prompt file, so behavior is identical apart from where the agent runs.

## Run an audit locally (on demand)

Requires the [`claude`](https://claude.ai/code) CLI on your `$PATH`.

```bash
# From the repo root:
.claude/skills/conda-forge-expert/automation/run-audit-local.sh
```

The script:

1. Loads the prompt from `quarterly-audit.prompt.md`
2. Invokes `claude -p "$prompt"` in non-interactive mode
3. Lets the agent edit, commit, and push from your local working tree

By default it runs against the current branch — pass `--branch <name>` to check out (or create) a different branch first. Pass `--dry-run` to print the prompt and exit without invoking Claude.

## Schedule the local script (optional)

If you'd rather not use the remote routine, drop the script into a local cron entry. The schedule below mirrors the remote routine.

```cron
# crontab -e — quarterly conda-forge skill audit, 9am Chicago on the 1st
0 9 1 1,4,7,10 *  cd ~/UserLocal/Projects/Github/rxm7706/local-recipes && .claude/skills/conda-forge-expert/automation/run-audit-local.sh >> /tmp/cf-audit.log 2>&1
```

Or as a systemd timer (`~/.config/systemd/user/cf-audit.{service,timer}`):

```ini
# cf-audit.service
[Unit]
Description=conda-forge-expert quarterly doc audit
[Service]
Type=oneshot
WorkingDirectory=%h/UserLocal/Projects/Github/rxm7706/local-recipes
ExecStart=%h/UserLocal/Projects/Github/rxm7706/local-recipes/.claude/skills/conda-forge-expert/automation/run-audit-local.sh

# cf-audit.timer
[Unit]
Description=Quarterly conda-forge skill audit
[Timer]
OnCalendar=*-01,04,07,10-01 09:00:00
Persistent=true
[Install]
WantedBy=timers.target
```

```bash
systemctl --user enable --now cf-audit.timer
```

## Recreate the remote routine

If the routine is ever deleted (only doable via `https://claude.ai/code/routines`), recreate it by feeding `quarterly-audit.prompt.md` to `/schedule` and pointing it at the same repo + cron expression:

```text
/schedule

Create a quarterly recurring agent. Cadence: every 3 months on the 1st at 09:00
America/Chicago. Repo: rxm7706/local-recipes. Environment: local-recipes.
Tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch.
Prompt: see .claude/skills/conda-forge-expert/automation/quarterly-audit.prompt.md
```

The cron expression resolves to `0 14 1 */3 *` — 14:00 UTC matches 9am Chicago in CDT. The Jan firing lands at 8am Chicago because of standard time; that's an accepted drift, not a bug.

## Audit log

When the agent finds no upstream changes worth a PR, it appends a one-line entry to [`AUDITS.log`](AUDITS.log) at the audit root rather than opening a noise-only PR. That file accumulates over time as a record of "we checked, nothing moved."

## Files in this directory

- [`README.md`](README.md) — this file
- [`quarterly-audit.prompt.md`](quarterly-audit.prompt.md) — the prompt the agent runs (cloud or local)
- [`run-audit-local.sh`](run-audit-local.sh) — local-runner wrapper
- `AUDITS.log` — created on first no-op audit; tracks dates with no upstream changes
