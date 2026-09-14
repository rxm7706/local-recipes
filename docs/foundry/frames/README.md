# Foundry Frames (git store)

Story 53.2 / `spec-intelligence-hub` CAP-2: one Company Frame plus eight
station Frames. Git is the store. Community Frame and a registry are later-caps
and must not appear here.

## Layout

| Path | Role |
|---|---|
| `pyforge.frame.md` | Company Frame (`identifier: pyforge/company`) |
| `stations/<station>.frame.md` | Station Frame (`identifier: pyforge/<station>`); `inherits: [pyforge/company]` |

Stations: herald, marshal, atlas, warden, mason, doctor, scribe, steward.

## Identity is `identifier`, not `name` (Story 53.6)

v0.3 §4.2.1 makes `identifier` the one mandatory identity element and says it
SHOULD be a URI or a **`qualified-ref`** — `publisher "/" frame-name` (§5.3).
Ours are `pyforge/company` and `pyforge/<station>`. It MUST NOT contain `@`,
which §5.3 reserves as the version separator.

`name` aliases `title`, which the element profile marks **MUST NOT be
slug-constrained** — it is a human label, not a key. So `name` carries the
prose form the Charter's branding law asks for (`PyForge Steward`), and the
slug `pyforge-steward` stays reserved for code, where it is also the Python
distribution name. Before 53.6 the two were the same string, and the preflight
keyed identity off `name` — the wrong element, and one that collided with the
dist name.

## Spelling: keep `name` and `inherits`

v0.3 §6.2.1 defines these as **aliases the Markdown encoding requires of a
writer**: the key `name` denotes `title`, and `inherits` denotes `composition`.
`title:`/`composition:` belong to the YAML and JSON encodings — do not
"modernize" these files to them, or v0.2 readers stop accepting the document.

Repeatable elements (`maintainer`, `inherits`) are emitted as **sequences**:
§6.2.1 says "A writer MUST emit a sequence". A scalar stays legal to *read*,
and the preflight reports one rather than rejecting it.

`inherits` resolves by identifier, or by a `path-ref` relative to the child
(`../pyforge.frame.md`), which §5.3 classifies first. Working draft:
https://github.com/openteams-ai/frame-spec/pull/28 (Apache-2.0, still open).
`type: frame [0.3]`; `license` is the Apache-2.0 IRI.

## Preflight

In-repo check: `type` begins with `frame`, plus `identifier` / `name` /
`description` / `visibility` / `maintainer`, the company/station identifier
set, inheritance, and sequence-shaped repeatables. Does **not** call upstream
`validate_frame.py` until frame-spec#28 / #29 merge.

```bash
pixi run -e pyforge-steward frame-preflight
```

Not a detector. Not in `detectors` / `detectors-ci`. Warden stays the sole PR
verdict.

Scribe owns the Frame-store half as a pointer only — these files are the
store; scribe does not ingest them into the knowledge graph in this story.
