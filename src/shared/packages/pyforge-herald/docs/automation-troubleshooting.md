# Herald "Automation" Troubleshooting Guide

Story 12.4 (honestly scoped). The original epics spec for this story asked
for "webhook not firing," "cron job missed," "auto-extract failed," and
"stale link warning" diagnoses. "Webhook not firing" and "cron job
missed" cannot happen in this codebase, because no webhook or cron
infrastructure exists — see `docs/dreams/herald-moments-2-4-live-backend.md`
for the full, unbuilt live-backend design and why the first pass was
scaled down to a CLI an operator runs by hand. This caveat applies to the
whole guide; it is not repeated per section below.

What *does* exist, and can genuinely misbehave, is the CLI-triggered
equivalent of each of those automations — including "auto-extract" (see
below): Epic 9's `herald success create` is its direct replacement, an
operator-run command rather than a PR-close webhook trigger. This guide
covers those real, reproducible failure modes.

## Stale or broken evidence links (the `herald success validate` scope)

**What it replaces:** the original spec's weekly async re-validation
cron, which would silently re-check every published claim's evidence and
presumably alert on breakage. There is no cron; instead, an operator runs
`herald success validate` by hand whenever they want a check.

### Diagnosis

*(The claim id below, `a17e2b60-...`, is from a separate scratch session
than the ones in `cli-runbooks.md`/`operator-guide.md` — every `herald
success create` mints a fresh UUID, so ids don't match across these docs'
independently-captured examples. This one's evidence is deliberately
broken to demonstrate `validate`; the other docs' examples use clean
evidence to demonstrate the happy path.)*

```
$ herald success validate --all
revalidated evidence for 2 claim(s)
```

This never fails loud on its own (its whole point is to surface breakage,
not reject it) — it updates each evidence item's `validated`/
`validated_at` fields in place. To see what actually broke, follow up with
`herald success get <claim-id>` or `herald success review <claim-id>`,
which show each item's `(validated)`/`(unvalidated)` status:

```
$ herald success review a17e2b60-4c8f-4e11-9d02-f6a3b0d8c721
...
evidence:
  - [test_results] test results: https://example.com/nonexistent-9999 (unvalidated)
```

Or check a single claim directly:

```
$ herald success validate a17e2b60-4c8f-4e11-9d02-f6a3b0d8c721
revalidated claim a17e2b60-4c8f-4e11-9d02-f6a3b0d8c721: 0/1 evidence link(s) valid
```

`herald success validate` takes exactly one of `<claim-id>` or `--all` —
supplying both, or neither, is a usage error:

```
$ herald success validate --all a17e2b60-...
herald: HeraldError: herald success validate: supply exactly one of <claim-id> or --all
```

The web dashboard's Success tab also shows this per-item, live from the
last export: a ✗ badge means "this link may be broken," a ⚠ badge means
"hasn't been validated recently; review it" (i.e. `validated=false`
without ever being explicitly rechecked). See
[`web-ux-guide.md`](web-ux-guide.md#success-tab).

### Fix

Evidence on an already-published claim cannot be edited in place through
this CLI today (there is no `herald success edit-evidence` or similar).
The practical remedy: fix the broken URL at its source (the linked
system), then re-run `herald success validate <claim-id>` to confirm it
now resolves. If the link is permanently gone, note it in a follow-up
notice/comment — there is no supported way to remove an evidence item from
a published claim.

**Distinct from a *publish-time* failure.** `herald success publish`
itself also validates evidence, but does so *before* writing anything —
see [`cli-runbooks.md`](cli-runbooks.md#evidence-link-validation-failure)
for that case, which is a hard abort (`EvidenceLinkError`, exit 1, claim
stays a draft), not a soft flag like `validate` produces on an already-
published claim.

## "Auto-extract failed" (the `herald success create` scope)

**What it replaces:** the original spec's PR-close webhook, which would
have auto-extracted a draft claim's `project_name`/`shipped_date`/evidence
from CI's payload the moment a PR merged with all gates green. There is no
webhook; instead, an operator runs `herald success create <project>` by
hand, supplying the same fields explicitly via flags (see
[`cli-runbooks.md`](cli-runbooks.md#how-to-publish-a-success-claim) for the
full create -> review -> publish walkthrough).

### Diagnosis

There is no "extraction" step to fail — `create` either succeeds (a draft
claim is written) or refuses with a `HeraldError` naming what's wrong.
Two real failure modes:

- **Empty/whitespace-only project name** — refused before any write:
  ```
  $ herald success create "   "
  herald: HeraldError: project_name must not be empty
  ```
  Fix: supply a real project name.

`create` takes evidence via three fixed flags — `--evidence-test-results`,
`--evidence-metrics`, `--evidence-adoption` — each a URL string for that
evidence type; there's no free-form evidence-type flag to mistype, and no
validation of the URLs themselves happens at create time (that's
`success publish`'s job — see [`cli-runbooks.md`](cli-runbooks.md#evidence-link-validation-failure)).

Once created, review the draft with `herald success review <claim-id>`
before publishing (see [`cli-runbooks.md`](cli-runbooks.md#how-to-publish-a-success-claim))
to catch anything the create step accepted but shouldn't have (a wrong
project name, a mistyped evidence URL) before it becomes a published,
citable record.

## Malformed local storage file (the `HeraldError` you'll see instead of a "DB corruption" alert)

**What it replaces:** database-level integrity checks/alerts a real
persistence layer would have. Local storage here is one JSON file per
Moment (`.herald/progress.json`, `.herald/claims.json`,
`.herald/notices-index.json`), so "corruption" means "the JSON doesn't
parse" or "a record is missing an expected field."

### Diagnosis

Any read or write against a broken file raises a plain `HeraldError`
naming the file and the parse problem, exit code 1:

```
$ herald success list
herald: HeraldError: claims file /path/to/.herald/claims.json could not be read: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
```

This is reproducible: hand-edit any `.herald/*.json` file into invalid
JSON (a stray brace, a trailing comma outside what the parser tolerates,
truncated output from an interrupted write) and every subsequent `herald`
command touching that file fails the same way until it's fixed.

### Fix

- Restore the file from git history if it's tracked (it usually isn't —
  `.herald/` is operator-local state, not committed), or from a backup.
- Otherwise, open the file and hand-fix the JSON syntax error the message
  points at (line/column are from Python's `json` module and are
  accurate).
- There is no repair or recovery tool built into `herald` for this.

## Stale web snapshot (no live API to "miss" — a manual export that wasn't re-run)

**What it replaces:** the "operator alerts for automation failures" AC.
There is nothing to alert on here because there is no automation to fail —
the web dashboard is a static bundle reading pre-generated JSON, and it is
the operator's job to regenerate that JSON after a CLI write. See
[`web-ux-guide.md`](web-ux-guide.md) for the full explanation and the
per-Moment regeneration commands.

### Diagnosis

The dashboard shows **old data with no error** — this is the most common
and least obvious of the three failure modes in this guide, because
nothing actually breaks. Symptoms:

- You ran `herald progress <station> --update` (or `success publish`, or
  `notice publish`) and the corresponding web tab still shows the
  previous state, or an empty state you thought you'd already cleared.
- `herald <moment> list` (or `get`) at the CLI shows the new/updated
  record, confirming the write itself succeeded.

If instead the panel shows an explicit **error state** ("Could not load
progress.json." / "Could not load success claims." / "Could not load
operations notices."), that's a different, harder failure — the snapshot
file is missing entirely or fails to parse as JSON. `web/scripts/sync-progress.mjs`
specifically fails loud (`JSON.parse` on the source) rather than shipping
bad data; the two Python exporters likewise raise on read failure — trace
that back to [Malformed local storage file](#malformed-local-storage-file-the-heralderror-youll-see-instead-of-a-db-corruption-alert)
above if the underlying `.herald/*.json` itself is broken.

### Fix

Re-run the exporter for whichever Moment changed:

| Moment | Command |
|---|---|
| Progress | `npm run sync-progress` (from `web/`) |
| Success | `python scripts/export_web_snapshot.py --repo-root <repo-root>` |
| Operations | `python scripts/export_notices_snapshot.py --repo-root <repo-root>` |

Then reload the page (or re-run `npm run dev`/`build`, which re-syncs
Progress automatically via its `predev`/`prebuild` hook — Success and
Operations still need the manual step either way, since only Progress's
exporter is wired into an npm script).
