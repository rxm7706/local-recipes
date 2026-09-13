# Foundry Frames (git store)

Story 53.2 / `spec-intelligence-hub` CAP-2: one Company Frame plus eight
station Frames. Git is the store. Community Frame and a registry are later-caps
and must not appear here.

## Layout

| Path | Role |
|---|---|
| `pyforge.frame.md` | Company Frame (`name: pyforge`) |
| `stations/<station>.frame.md` | Station Frame; `inherits: pyforge` |

Stations: herald, marshal, atlas, warden, mason, doctor, scribe, steward.

## `inherits` convention

Station Frames inherit the Company Frame by **name** (`inherits: pyforge`),
matching Frame Spec v0.2's example style. The in-repo preflight also accepts a
path that resolves to the company file (relative to the child).

## Preflight

In-repo four-field check (plus named `owner`). Does **not** call upstream
`tools/validate_frames.py`.

```bash
pixi run -e pyforge-steward frame-preflight
```

Not a detector. Not in `detectors` / `detectors-ci`. Warden stays the sole PR
verdict.

Scribe owns the Frame-store half as a pointer only — these files are the
store; scribe does not ingest them into the knowledge graph in this story.
