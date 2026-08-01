# Narration script — Wasm Analytics Stack - Infographic Deck

> Extracted from `Wasm Analytics Stack - Infographic Deck.dc.html` speaker notes (regenerable — do not hand-edit; edit the deck's `data-speaker-notes` in Design and re-extract). 7 scenes.

## Scene 01 — Cover

Wasm Analytics Stack: a second boundary at the one place untrusted input first touches the system.

## Scene 02 — The maturity verdict

The central scoping fact, and a negative result: DuckDB has no WASI build and no WASI roadmap, so dlt, dbt and DuckDB cannot be sandboxed today.

## Scene 03 — The three-lane split

AD-3 turns the verdict into a rule: conventional processes for the DuckDB-touching core, a real WASI component for validation, and the browser lane deferred to v2.

## Scene 04 — The seed use case

Four decisions keep two independent builders from composing the pipeline incompatibly: the WIT data shape, the synchronous upload, the single-writer cardinality, and the one trace-ID wire format.

## Scene 05 — The non-hollow gate

A gate that only proves the component instantiates proves nothing. AD-4 ships a meta-test from version one; AD-2 makes the denylist a build gate rather than a policy.

## Scene 06 — One toolchain, three environments

One Pixi toolchain, one canonical securityContext with two consumers, one mount contract, and every build-time fetch routable through a mirror.

## Scene 07 — The close

Ships zero claims beyond what the research verified as buildable, with two counter-metrics guarding the primary ones.
