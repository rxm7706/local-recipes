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
3. To restore management: `marshal seed adopt --reinstate <artifact-id>#<region>`.

Removing markers is the supported way to say "this repo owns this section now." Do not delete markers casually — the opt-out is durable until reinstated.

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
