---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/revoke.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/pages_duty.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - docs/governance/guild-roster.json
verified: 2026-11-24
---

# How to use steward duties that need operator consent

Use the read-only or dry-run form of `cutover`, `pages`, `sync` and `revoke` to see what each would do, and leave the form that changes shared state to the operator.

## When to use this

- You need to validate the capability ledger, or know which root is the root of record.
- You want to see what a Pages build or deploy would run before anyone triggers it.
- A GitHub Projects item and its Jira issue disagree and you want to know which side would win.
- A subject's tasks are running away and someone has to stop them.

## When to skip this

- You want to pause or resume a CI surface: [How to pause and resume CI surfaces](pause-ci.md).
- You want to refresh dependency pins: [How to refresh the estate](refresh-the-estate.md).
- You want to bring up Nebari on kind: [Host Nebari](host-nebari.md).

:::note
**Prerequisites.** Run from the repository root in `-e pyforge-guild`. The forms marked "operator" below reach GitHub, Jira or the platform host and need the operator's credentials.
:::

## Who runs which form

An agent runs the left column. The right column changes shared state, so the operator runs it, or asks for it in plain words in chat.

| Duty | An agent runs | The operator runs |
| --- | --- | --- |
| `cutover` | `cutover plan --check` | `cutover flip --to …` |
| `pages` | `pages status`, `pages build --dry-run`, `pages deploy --dry-run` | `pages deploy` |
| `sync` | `sync reconcile … --dry-run` | `sync reconcile …` |
| `revoke` | Nothing; hand the operator the command | `revoke --sub ID` |

Three steward actions are refused outright by the session hook for an agent: `estate refresh --transitive`, `estate realize --yes`, and `deploy nic up --yes` on any provider but local kind. The reasons are rows of `session_denials` in `docs/governance/guild-roster.json`.

## Steps

### 1. Validate the capability ledger

```bash
pixi run -e pyforge-guild pyforge steward cutover plan --check
```

`--check` is the default. It judges `docs/foundry/capability-ledger.yaml` against the live Specs and the written rules, writes nothing, and prints a count of findings and warnings with one line per item. It exits `1` when there is a finding; warnings do not change the exit code. Add `--json` for the report as JSON, or `--ledger PATH` to judge another file.

`plan --regenerate` and `plan --append` rewrite the ledger. They sit behind the kill switch `pyforge.steward.cutover_ledger_write` and belong inside a story that changes the ledger, on the root that holds the writer lock.

### 2. Leave the root-of-record flip to the operator

```bash
pyforge steward cutover flip --to {local-recipes,foundry}
```

`flip` sets `pyforge.cutover_root`, which names the root of record and hands over the writer lock for every Dream, Spec and ledger row. It is refused while a Marshal loop is running, and it stamps the Realization log. The operator runs it by hand, once. An agent never does; there is no dry-run form.

### 3. Look at Pages without deploying

```bash
pixi run -e pyforge-guild pyforge steward pages status
pixi run -e pyforge-guild pyforge steward pages build --dry-run
pixi run -e pyforge-guild pyforge steward pages deploy --dry-run
```

`status` reads the live site root, the last `pages.yml` run and the Pages row's registry verdict; it never triggers a run. It calls `gh`, so it needs `gh auth login` first. The two dry runs print what would happen and run nothing:

```text
pages build (dry-run): would write docs-site/src/content/fleet-status.json from sprint-ledger-query --format json
pages build (dry-run): pixi run --frozen -e site pages-check
pages deploy (dry-run): gh workflow run pages.yml --ref main
```

Without `--dry-run`, `build` writes `docs-site/src/content/fleet-status.json`, runs `pages-check` and reports the built tree's hash. `deploy` triggers one run of `.github/workflows/pages.yml` on `main` and names it; `--wait` watches the run to the end. A deploy publishes the site, so the operator asks for it.

Every `pages` verb sits behind the flag `pyforge.steward.pages_duty` (on in `dev`), and exits `3` while it is off.

### 4. See what a sync would decide

```bash
pixi run -e pyforge-guild pyforge steward sync reconcile --github-item <ID> --dry-run
pixi run -e pyforge-guild pyforge steward sync reconcile --jira-issue <KEY> --dry-run
```

`reconcile` re-reads a linked GitHub Projects V2 item and its Jira issue and converges the side that is behind. Name the pair with `--github-item` or `--jira-issue`, or pass `--schedule` to reconcile every linked item on the board in one run. `--dry-run` computes and reports the decision and makes no write call.

The mapping of project, field and status ids is read from `.steward/sync-config.yaml` (`--config PATH` names another file); `.steward/sync-config.example.yaml` shows the shape. Without `--dry-run` the command writes to GitHub and Jira, so the operator runs it.

### 5. Stop a runaway subject

```bash
pyforge steward revoke --sub <ID> --python <platform-interpreter>
```

`revoke` stops one subject: it revokes that subject's queued Celery tasks and cancels its live supervisor runs. `--sub` is the `sub` claim of the subject's assertion. Steward does not do the write itself; it runs the platform host's own `manage.py revoke_subject` and reports what that said. `--python` names an interpreter that can import the platform's Django, because the one running steward usually cannot.

There is no dry-run form. An agent that sees a runaway subject gives the operator this command with the subject id filled in.

## How to tell it worked

| Exit | Meaning |
| --- | --- |
| `0` | The duty ran and reported ok. |
| `1` | The duty ran and reported not ok, such as `cutover plan --check` with a finding. |
| `2` | A usage error, or a kill switch that is off. |
| `3` | A documented refusal: `pages` with its flag off. |
| `70` | An internal error. |

Read the exit code directly (`echo $?`), never through a pipe.

## Tips

- `pages status`, `sync reconcile` and `revoke` were not executed for this page: each needs a credential or the platform host. `cutover plan --check` and the two `pages` dry runs were run.
- The live cutover state is in herald's dossier, `docs-site/src/content/dossier/dossier.yml`, never restated in a how-to.
- An outbound vendor load is default deny and needs a named signer; see [How to move vendor extracts through the corridor](move-vendor-extracts-through-the-corridor.md).
- Every flag and exit code is a row of the station contract, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md`.
