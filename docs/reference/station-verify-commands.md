# Station verify commands

Single lookup table for what `marshal factory dispatch`/`drain` actually runs to verify
each PyForge station's stories, and — just as important — the **exact byte-identical
string** every story spec's `## Verification` → `**Commands:**` section must declare for
that station (`MRS-GATE-011`, `core/gate.py::check_spec_binding`).

## Why this exists

Every station's `verify_commands` lives in its own
`_bmad-output/projects/pyforge-<station>/planning-artifacts/marshal-policy.toml` — that
file stays the single source of truth. This doc is a **derived, at-a-glance mirror** of
those 8 files, kept in one place so a spec author (or an agent drafting a new story spec)
doesn't have to open all 8 to find the right command, and so a fleet-wide sweep for drift
is a five-second visual diff instead of eight separate file reads.

**Regenerate/check freshness:**
```
for st in atlas doctor herald marshal mason scribe steward warden; do
  echo "=== $st ==="
  grep -A5 "^verify_commands" "_bmad-output/projects/pyforge-$st/planning-artifacts/marshal-policy.toml"
done
```
If this doc and that output disagree, this doc is stale — trust the `.toml` files and
update the table below.

## The two gates this matters for

- **`MRS-GATE-010`** — a story's spec has no `## Verification` → `**Commands:**` section
  at all ("no Success signal to bind against"). Every story spec authored for a
  station **must** carry one before it can reach `marshal factory dispatch`.
- **`MRS-GATE-011`** — the spec HAS a Verification section, but a command it declares is
  no longer among the station's current `verify_commands` (policy narrowed/renamed it
  since the spec was written). The compare is a **whitespace-collapse string match**, no
  argv parsing — `pixi run --frozen -e X t` ≠ `pixi run -e X t`. Use the exact string
  below, verbatim, including (or omitting) `--frozen`.

Both were discovered live 2026-08-30/31: no station had ever declared a
`## Verification` section until marshal's automated dispatch path actually reached one
(first atlas, then marshal's own Epic 28 and scribe's Epic 6), and a fleet-wide sweep
then found 338 already-shipped specs across all 8 stations whose declared commands had
drifted from current policy. Both classes were backfilled/reconciled fleet-wide the same
day — see each PR below for the mechanics.

## The table

| Station | `verify_commands` (verbatim, in order) |
|---|---|
| atlas | `pixi run -e pyforge-atlas kedro-test`<br>`pixi run -e pyforge-atlas kedro-catalog-check` |
| doctor | `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` |
| herald | `pixi run --frozen -e pyforge-herald pyforge-herald-test` |
| marshal | `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`<br>`pixi run --frozen -e pyforge-ci pyforge-deps-test` |
| mason | `pixi run --frozen -e pyforge-mason pyforge-mason-test` |
| scribe | `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` |
| steward | `pixi run --frozen -e pyforge-steward pyforge-steward-test` |
| warden | `pixi run --frozen -e pyforge-warden pyforge-warden-test` |

**Note the asymmetry**: atlas's commands are deliberately **un-frozen** — its specs
predate the rest of the fleet's `--frozen` convention, and GATE-011's shallow string
compare means switching atlas to `--frozen` would itself become a fleet-wide refusal
across every atlas spec unless every atlas spec were updated in the same change. Don't
"fix" this asymmetry casually; if it's ever done, it's a dedicated, fleet-scoped effort,
not a drive-by.

## Template for a new spec's Verification section

Copy the block for your station verbatim (single-line bullets — `parse_success_signal`
truncates the Commands list at the first wrapped/non-bullet continuation line, so don't
wrap a bullet across multiple lines):

```markdown
## Verification

**Commands:**
- `<verbatim command from the table above>` — expected: <what a green run proves for this story>.
```

One bullet per command in the table, same order, verbatim strings. Add story-specific
`expected:` text — that part isn't gated, only the backtick-quoted command itself is.

## Keeping this from going stale again

`marshal-policy.toml`'s `verify_commands` should be treated as a genuine interface: a
change to it is a change every story spec for that station implicitly depends on. When
you edit a station's `verify_commands`, in the same change:

1. Update this table.
2. Grep that station's specs for the OLD command string and reconcile any hit (the same
   surgical single-bullet-block replacement used in the 2026-08-30/31 backfill — see
   `git log --oneline --grep "GATE-011"` for the pattern).

There's no automated detector for this yet (unlike `bmad-drift-check`'s coverage of other
fleet-wide drift classes) — until one exists, this is a manual discipline, not a gate.
