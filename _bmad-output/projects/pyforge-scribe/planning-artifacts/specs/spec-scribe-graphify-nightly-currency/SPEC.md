---
spec: scribe-graphify-nightly-currency
status: ready
owner-dream: docs/dreams/scribe-graphify-nightly-currency.md
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py
  - scripts/scribe_nightly_trigger.py
  - pixi.toml
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-graphify-nightly-currency.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# SPEC — The nightly graph still knows the code

## Why

A pain to solve: the 02:30 full rebuild drops every `code:` node `scribe index build` wrote, and the graphify adapter cannot call live graphifyy because `graphify.extract` is a submodule after `collect_files`. The scheduled graph is not the graph the operator just built.

## Capabilities

- **CAP-1**
  - **intent:** An operator can ingest `src/shared/packages/` through `scribe index build` or a compile with the graphify extra on, against the graphifyy this estate installs.
  - **success:** `ingest_repo` returns `code:` `GraphNode`s when the target has extractable files; `graphify.extract` being a module after `collect_files` does not raise `TypeError`.
  - **verified:** 2026-09-13 — PASS — `pixi run -e pyforge-scribe scribe index build` wrote 37464 `code:` nodes through the persist port (no TypeError).
- **CAP-2**
  - **intent:** The estate-owned nightly trigger compiles with the graphify extra enabled for that process so the rebuilt store still contains the code surface.
  - **success:** With `SCRIBE_GRAPHIFY_EXTRA` unset, the trigger exports `1` before `scribe graph compile --nightly`; an explicit `0` is left alone. After that compile, `graph.json` has `kind=code` nodes whenever graphifyy ingested the default target.
  - **verified:** 2026-09-13 — PASS — `pyforge-scribe-nightly-compile` rebuilt 37834 nodes (37464 `code`, 0 invalidated); store mtime 2026-09-13 07:38.
- **CAP-3**
  - **intent:** The nightly compile includes each Herald deck fact ledger so agents can recall the numbers the posters are supposed to show, without ingesting the derived presentation tree.
  - **success:** `compile_graph` writes one `kind=doc` node per `presentations/<slug>/facts.yaml`; a missing `presentations/` directory yields zero nodes and no error. No `project/*.dc.html`, slide fragment, dated Marp file, or deck-engine copy is a compile source.

## Constraints

- Unset `SCRIBE_GRAPHIFY_EXTRA` on an interactive compile still skips the extra (AD-6).
- `graphifyy` is a declared dependency of the `pyforge-scribe` pixi feature so the trigger's environment can `import graphify`. The third-party import stays lazy and inside `extras/graphify.py`.
- Compile degrades to a warning when ingest fails; it never fails the scheduled run red. `scribe index build` still exits 2 if graphifyy is absent.
- One persist path: compile-with-extra-on, not a second store and not a required post-compile `index build` hop.

## Non-goals

- A GitHub Actions workflow as the trigger.
- Changing GraphStore engines or creating `graphify-out/` at the foundry root.
- Turning every interactive `scribe graph compile` into a graphify ingest.
- Ingesting `presentations/` wholesale (fragments, `.dc.html`, dated Marp, copied deck engine).

## Success signal

`pixi run -e pyforge-scribe scribe index build` exits 0 and writes `code:` nodes. A following `SCRIBE_GRAPHIFY_EXTRA=1 scribe graph compile --nightly` (or the trigger with the extra unset) leaves `code:` nodes in `graph.json`.

## Assumptions

- The installed crontab already invokes `pyforge-scribe-nightly-compile`; changing the trigger body is enough — no reinstall required for CAP-2.
