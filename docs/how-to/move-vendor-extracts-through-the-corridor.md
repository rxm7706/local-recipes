---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/passport.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/quarantine.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/glass.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/corridor/corridor.yaml
verified: 2026-11-17
---

# How to move vendor extracts through the corridor

Use steward's `load`, `passport`, `quarantine` and `glass` duties to record a vendor's extract file once, give its rows an identity, shelve the rows that have none, and see whether today's drop arrived.

## When to use this

- A vendor sent an extract file and it must be recorded exactly once.
- An inbound row has no identity yet and needs one, or needs to wait for a human.
- Standup asks whether the vendor's file arrived today.
- An extract has to leave the estate, signed.

## When to skip this

- You are reconciling a GitHub Projects item with its Jira issue. That is `steward sync`; see [How to use steward duties that need operator consent](use-steward-duties-that-need-operator-consent.md).

> [!NOTE]
> **Prerequisites.** These duties write to and read from the platform database. They need the `pyforge-steward[dashboard]` extra and a configured Django project (`DJANGO_SETTINGS_MODULE` set). Without them every verb refuses with a message and exit `1`; it never crashes. In `-e pyforge-guild` the refusal reads `Django ORM unavailable`; in `-e pyforge-steward`, `DJANGO_SETTINGS_MODULE is unset and django settings are not configured`.

> [!IMPORTANT]
> `load`, `passport mint` and `quarantine admit` write shared records. An agent runs only the two reads, `glass` and `quarantine shelf`. An outbound load carries data out of the estate: the operator runs it.

## The terms

| Term | Meaning |
| --- | --- |
| **Waybill** | A label you supply for one drop. A load is keyed on the file's hash and its waybill. |
| **Transport** | How the file arrived. Declared in `src/shared/packages/pyforge-steward/corridor/corridor.yaml`; `app-upload` is on, `shared-folder` and `email` are off. |
| **Work Passport** | A freshly minted UUID that is a row's identity. A Jira key or GitHub item id is only a nickname on it. |
| **Quarantine shelf** | Where an inbound row without a passport waits until a human links it. |
| **Glass** | The freshness reading of the most recent inbound load. |

## Steps

### 1. Load an inbound extract

```bash
pyforge steward load inbound --file <path> --waybill <label>
```

The load is idempotent: loading the same file with the same waybill again is a no-op, not a duplicate. `--transport NAME` names a declared transport and defaults to `app-upload`; a transport whose state is off is refused. `--corridor DIR` (before `inbound`) points at another directory holding `corridor.yaml`.

### 2. Give a row an identity

```bash
pyforge steward passport mint --vendor-id <name> [--jira-key KEY] [--github-item-id ID] [--title TEXT]
```

Every call mints a new UUID. Two mints with the same vendor and the same Jira key never merge, so mint once per row.

### 3. Shelve a row that has no passport

```bash
pyforge steward quarantine admit --vendor-id <name> [--jira-key KEY] [--github-item-id ID] [--title TEXT] [--arrived-at ISO8601]
pyforge steward quarantine shelf
```

`admit` puts the row on the shelf. Inside the missing-passport window, 14 days from `--arrived-at` (default: now), it also mints a passport for the row. After the window it refuses to mint, and the row lands on the shelf with no passport.

`shelf` lists the rows nobody has linked yet; `--include-linked` adds the ones a human already linked.

### 4. Check whether today's drop arrived

```bash
pyforge steward glass
```

`glass` reads the most recent inbound load and reports it twice, as `standup` and as `shipped`. Both are the same reading. Each has one of four states:

| State | Meaning |
| --- | --- |
| `unborn` | Nothing has ever loaded. |
| `fresh` | A drop arrived today. |
| `stale` | The last drop was not today. |
| `failed` | Today's drop is an empty file. |

`glass export --format {csv,markdown}` renders the two rows as a table. It sits behind the flag `pyforge.steward.glass_export`, which is off; `--flag enable_glass_export=true` turns it on for one call.

### 5. Send an outbound extract (operator)

```bash
pyforge steward load outbound --file <path> --waybill <label> --slice <name> --signer <name>
```

Outbound is default deny. A new outbound load is refused without a named `--slice` and a recorded `--signer`, the person who authorized that slice. It uses the same declared transports as inbound; it does not push to anyone's system.

## How to tell it worked

| Exit | Meaning |
| --- | --- |
| `0` | The duty ran and reported ok. |
| `1` | The duty ran and reported not ok, including a refusal because Django is unavailable. |
| `2` | A usage error. |
| `70` | An internal error. |

Add `--json` (before the verb, as in `steward glass --json` or `steward load --json inbound …`) for machine-readable output. After a load, `glass` should read `fresh`.

## Tips

- No verb on this page completed for this page: no configured platform database was available. `glass` and `quarantine shelf` were run and refused as the prerequisites note says. The rest is taken from `--help`, the modules and the station contract. Which pixi environment carries a configured Django project for these duties was not established here.
- The loader never parses the file's content. It records the hash, the waybill and the transport.
- Every flag is a row of the station contract, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md`.
