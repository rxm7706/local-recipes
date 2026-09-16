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
(`../pyforge.frame.md`), which §5.3 classifies first. `license` is the
Apache-2.0 IRI.

## `type: frame` — bare, no version token (Story 64.1)

The draft's 2026-09-14 revision (§6.2.1) says the working draft *carries no
version number until a release assigns one*; a document written to it omits
the token, and upstream's own examples now read bare `type: frame`. Our
`frame [0.3]` stamped a version no release has assigned, so the nine Frames
are bare. **Which draft we conform to is recorded by the pin below, not by
the token.** `frame [0.2]` remains valid and denotes the released spec.

## Upstream pin (the one declared source)

[`upstream-pin.yaml`](upstream-pin.yaml) names the frame-spec heads this
estate conforms to — the working draft
([#28](https://github.com/openteams-ai/frame-spec/pull/28),
`spec/v0.3-working-draft`) and the reference validator
([#29](https://github.com/openteams-ai/frame-spec/pull/29),
`spec/v0.3-validator`, based on #28). We operate as if these heads become
v0.3. Re-pin only with a memlog line on `spec-pyforge-steward` naming the new
SHAs and what moved. **Nothing is ever committed or commented upstream.**

## Conformance profile (Story 64.2)

§7 makes a conformance profile a MUST for every implementation.
[`conformance-profile.yaml`](conformance-profile.yaml) is PyForge's, for the
in-repo reader: reads Markdown, writes nothing, resolves no composition,
`visibility` is declared intent, and — §9 — it says plainly that no trust
configuration exists yet because the only source it reads is this repository.
The first PyForge component that loads a Frame into a model's context revises
this file *before* it lands (`spec-pyforge-steward` Constraint CAP-6).

## Preflight and upstream check

In-repo check: `type` begins with `frame`, plus `identifier` / `name` /
`description` / `visibility` / `maintainer`, the company/station identifier
set, inheritance, and sequence-shaped repeatables.

```bash
pixi run -e pyforge-steward frame-preflight        # in-repo, offline
pixi run -e pyforge-steward frame-upstream-check   # opt-in, network: upstream's validator at the pin
```

`frame-upstream-check` fetches frame-spec at the pinned validator SHA into a
temp dir and runs *its* `tools/validate_frame.py` over the nine Frames and
`--check-profile` over our profile (exit `0` ok / `1` upstream FAIL / `2`
could not run). The tool is never vendored. Verified 2026-09-16 at
`4596579f`: 9/9 OK, profile complete.

Neither is a detector. Neither joins `detectors` / `detectors-ci`. Warden
stays the sole PR verdict.

Scribe owns the Frame-store half as a pointer only — these files are the
store; scribe does not ingest them into the knowledge graph in this story.
