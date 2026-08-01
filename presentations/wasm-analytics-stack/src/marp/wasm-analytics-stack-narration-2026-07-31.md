# Narration script — Wasm Analytics Stack

> Extracted from `Wasm Analytics Stack.dc.html` speaker notes (regenerable — do not hand-edit; edit the deck's `data-speaker-notes` in Design and re-extract). 10 scenes.

## Scene 01 — Cover

Wasm Analytics Stack lets a hardened enterprise accept user-uploaded data into an analytical pipeline without widening the trust boundary of the pipeline's own code. It descends from an April 2026 architecture gist that claimed more than today's ecosystem can deliver — and this project corrects that claim rather than re-inheriting it. The honest, narrower scope is itself the differentiator.

## Scene 02 — The maturity verdict

This is the most valuable slide in the deck, and it is a negative result. Verified against primary sources on 2026-07-25: DuckDB's native engine has no WASI build and no WASI roadmap — a search of duckdb slash duckdb for WASI returns zero issues, so the question has never even been asked upstream. dlt's DuckDB destination and dbt-duckdb both inherit that blocker. The only community source of WASI-cross-compiled wheels for this class of library, dicej slash wasi-wheels, is explicitly disclaimed by its own author as a proof of concept not to be relied on for anything serious, and its pandas build directory has not been touched since December 2024. It contains no pyarrow and no duckdb at all. So: dlt, dbt and DuckDB cannot run inside a genuine WASI component today.

## Scene 03 — Act I — The gap that remains

Act I: what the verdict does not remove. Restricted SCC gives process isolation, not code isolation — the Python process inside a hardened pod still has the full language surface available to anything running inside it. There is no second boundary between the pipeline's own trusted code and logic derived from an uploaded file. That gap is real whether or not DuckDB ever ships a WASI build.

## Scene 04 — The scope that survives

The scoping call the verdict forces: a three-lane split. Ordinary Restricted-SCC-hardened processes for the DuckDB-touching pipeline core; a real componentize-py-built WASI component only for the genuinely pure-Python validation step at the trust boundary; and DuckDB-WASM plus Pyodide in the browser for a future read surface, following pyforge-atlas story G1's shipped pattern. AD-3 makes the middle lane a rule, not a preference: no component in the ingest or transform runtime path may declare a wasm32-wasi build target without an ADR amendment citing new upstream evidence.

## Scene 05 — Act II — The seed use case

Act II: one concrete pipeline, end to end. Marcus uploads a weekly headcount-and-cost spreadsheet; three rows fail validation; he sees precise row-level errors within seconds; the file was never partially ingested and the valid rows queue separately from the rejected ones. That is the whole product surface in v1 — not a general ingestion platform.

## Scene 06 — Upload to Gold

The pipeline, stage by stage, with the decisions that keep two independent builders from composing it incompatibly. AD-10: OIDC is validated at a gateway boundary in front of the API, never embedded per-request. AD-1: Excel bytes are parsed into rows entirely outside the sandbox, and only primitive and record types cross the WIT boundary — no shared memory, no Arrow buffers. AD-9: the upload is synchronous, returning the full per-row result in the same HTTP response; the trace ID is a correlation handle, not a polling handle. AD-7: each validated upload triggers exactly one dlt load followed by exactly one dbt run scoped to that load, sequentially, from the same owning process, because DuckDB is single-writer.

## Scene 07 — The non-hollow gate

The differentiating claim, and the reason it is credible. A gate that only proves the component instantiates successfully proves nothing about the sandbox boundary. So AD-4 requires the gate to ship with a meta-test from its first version: deliberately widening the component's declared WIT capabilities without a matching interface change must make the gate fail. If it cannot fail, it is not checking anything. Alongside it, AD-2 makes the dependency denylist a build gate rather than a policy — adding numpy, pandas, pyarrow or pydantic fails pixi run build, not a later runtime error. The philosophy is borrowed from pyforge-atlas story G1's wasm-smoke gate; the mechanism is genuinely different, because G1 has no Wasmtime host, no WIT interface and no capability model.

## Scene 08 — One trace ID, one security context

Two single-source-of-truth decisions that stop the system fragmenting. AD-5: the correlation key is always the bare 32-hex-character W3C trace id — never the full traceparent string, never a UUID, never dashed — minted once at ingress, stored in the dlt load package metadata, passed to dbt as a var, and attached as a custom OpenLineage facet. It is deliberately never conflated with OpenLineage's own runId. AD-6: one canonical security context is authored once under deploy slash, and both the Helm chart and the Podman compose file consume it through a generation step; neither hand-authors its own copy, because that drift is exactly what would silently defeat the parity claim.

## Scene 09 — One toolchain, three environments

One Pixi toolchain builds every artifact the pipeline needs, including the compiled WASI component: a clean checkout plus pixi install and pixi run build produces a runnable digital twin with no manual steps outside Pixi. The same images and the same security context then run under Podman locally and under OpenShift Restricted SCC, with DuckDB state mounted at the same path from a ReadWriteOnce-shaped volume — only the backing implementation differs, never the mount contract. And AD-8 keeps every build-time fetch routable through a mirror: no build script hardcodes a public URL, mirroring the vendored-extension pattern Atlas G1 established.

## Scene 10 — Ships no claim research did not verify

Close on the discipline. The success signal is explicit that this project ships zero claims beyond what the technical research verified as buildable today — and two counter-metrics guard the primary ones. A growing denylist-workaround footprint is a signal to reconsider the WASI bet, not a target to minimize by weakening the boundary. And validation latency must never be improved by moving checks out of the sandbox back into the trusted process, which would satisfy a speed metric while quietly defeating the entire purpose. Planning ran to PRD and architecture depth only: there are no epics and no stories — a far-horizon effort whose stories decompose fresh when it is scheduled.
