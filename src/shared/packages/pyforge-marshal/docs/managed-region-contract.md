# Managed region contract

Hybrid artifacts (`hybrid-managed-region` class) are **repo-owned files** containing **tool-owned spans** delimited by marker comments. Genesis may replace only the span on `marshal seed update`; prose outside the markers is never touched.

## Marker grammar

One grammar, rendered through the artifact's declared `format` (`html`, `hash`, or reserved `slashstar`):

```text
<open> marshal-seed:begin region=<name> model-version=<semver> sha=<8-hex> <close>
  … tool-owned body …
<open> marshal-seed:end region=<name> <close>
```

Examples:

- Markdown / HTML comments: `<!-- marshal-seed:begin region=tiers … -->`
- Hash comments (`.gitignore`, TOML, YAML): `# marshal-seed:begin region=model-ignores …`

Region names match `[a-z0-9][a-z0-9-]*` (e.g. `tiers`, `dream-first-workflow`).

## Edit detection

`marshal seed check` hashes **region body content only** (never the marker line itself) and compares against the hash recorded in `.marshal/seed-state.yml`. A hand-edit inside the markers emits `managed-region-modified` (**HARD**). Content outside the markers is ignored for conformance.

If markers are **absent** but the region was never opted out, `managed-region-missing` (**DRIFT**) is reported — run `marshal seed update` to re-insert at the manifest's declared anchor.

## Sanctioned opt-out

**Deleting both markers** (begin and end) for a region is a deliberate, permanent opt-out (FR-112, AD-58):

1. Genesis records the pair in `state.opted_out` on the next mutating run (`adopt` / `update`).
2. While opted out, the tool will **not** re-insert that region (`opted-out`, **INFO**).
3. To restore management: `marshal seed adopt --reinstate <artifact-id>#<region>` (Story 10.6 ships the flag; until then see the last paragraph of this section).

Removing markers is the supported way to say "this repo owns this section now." Do not delete markers casually — the opt-out is durable until reinstated.

The opt-out is per region. State records one span, with its own hash, for each region of an artifact that was installed, so deleting some of an artifact's markers opts out of exactly those regions and leaves the others managed. A deleted region is not a hand-edit: `adopt` and `update` neither refuse the run nor re-insert it, and no `--force` is needed (`--force` is not a reinstate). A region whose markers are still present and whose body was edited is still refused. This holds for both verbs, over a recorded opt-out, over one the run derives from the deleted markers, and over a state written before per-region spans.

Two conditions bound that. The per-region claim holds for state written by this release; a state written before it attests to one region per artifact until the next applying run rewrites the record. If that one recorded region is still present, `update` rewrites every declared region and records each. If it was the region you deleted, the run replaces the old record with one for the sibling regions still in the file, each recorded at its current hash -- they are recorded, not rewritten. And a derived opt-out is recorded by the run that writes state, which is a run with something to apply: an empty-plan run records nothing, so the opt-out stays derived -- read from the file's claim and the deleted markers on every run -- only while that claim's `path` still matches the manifest's.

State written by this release is not readable by an older marshal. The seed-state schema is closed and the package version is unchanged, so `seed_model_version` cannot tell the two apart, and an older marshal reports `state-invalid` for it. The remedy is to upgrade that marshal: restoring `.marshal/seed-state.yml` from version control helps only if you also restore the older marshal's own write of it, and re-running `marshal seed adopt` does not recover it (`adopt` reads state without downgrading `state-invalid`).

There is no reinstate verb yet (Story 10.6; the `--reinstate` spelling above is the planned one). Restoring the markers by hand makes the region present again, and the two verbs treat it differently. `update --run` records the region on its next run. `adopt` refuses an artifact whose other regions are recorded, with "present in the file but never recorded", until `--force`; and `adopt --apply --force` then plans nothing, because every declared region is in the file, so it writes no state and the region stays unrecorded. Use `update --run` to record it. The `opted_out` key stays in state either way.

## What Genesis never does

- Infer structure beyond literal anchor matchers (FR-111).
- Write into paths matching the manifest `never_write` globs (`docs/dreams/*.md`, `**/planning-artifacts/**`, etc.).
- Destroy real content occupying a projection path without a **WARN** refusal (adapter projection is separate; see Marshal adapter docs).

## Related findings

| Situation | Finding | Severity |
|---|---|---|
| Edited inside markers | `managed-region-modified` | HARD |
| Markers gone, not opted out | `managed-region-missing` | DRIFT |
| Markers deleted, opt-out recorded | `opted-out` | INFO |
| Whole hybrid file hand-edited (non-region class confusion) | `managed-file-modified` | HARD |

Remedies: [finding-remedy-reference.md](finding-remedy-reference.md).
