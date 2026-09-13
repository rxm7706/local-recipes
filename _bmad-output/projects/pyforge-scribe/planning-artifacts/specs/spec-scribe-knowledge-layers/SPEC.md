---
spec: scribe-knowledge-layers
status: ready
owner-dream: docs/dreams/scribe-knowledge-layers.md
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py
  - AGENTS.md
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-knowledge-layers.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — Layered knowledge, not one bag

## Why

The compiled graph mixes planning truth with an AST dump and a leaky retro glob. Recall is first lexical hit. Stale compares working-tree mtime to git author date, so a full rebuild withholds nodes it just wrote. Agents load MEMORY.md and never call `scribe recall`. Wiring PyForge to that bag would search the loudest node, not the contract.

## Capabilities

- **CAP-1**
  - **intent:** After a full rebuild, a node is stale only when its source file's latest git commit is authored after this compile started.
  - **success:** A committed file whose working-tree mtime is older than that commit is not flagged stale on the compile that just read it. `stale_count` is 0 unless a commit timestamp is after `compiled_at`.
- **CAP-2**
  - **intent:** Compile walks exclude archive trees, `implementation-artifacts/`, and `tests/` directories. Retros are only `planning-artifacts/retros/*.md`.
  - **success:** No `doc` or `memlog` node cites `archive/`, `implementation-artifacts/`, a path segment `tests`, a `*retro*` story spec, a skill template, or a team-memory filename that merely contains `retro`.
- **CAP-3**
  - **intent:** Named contract surfaces join the compile as `kind=doc`: active Dreams (`docs/dreams/*.md` with status `dreamt`|`pitched`|`specified`), active folder SPECs (`_bmad-output/projects/*/planning-artifacts/specs/*/SPEC.md` with status `ready`|`in-progress`), and Herald `presentations/*/facts.yaml`.
  - **success:** Those paths produce one node each; `realized`/`archived` Dreams and `shipped`/`draft` SPECs are omitted; missing trees are zero nodes and no warning.
- **CAP-4**
  - **intent:** Default `scribe recall` (and `answer()`) excludes `kind=code`. `--kind` selects kinds explicitly. Marshal `--scope` is unchanged.
  - **success:** An unscoped query whose only overlap is a `code:` node returns `no grounded answer found` unless `--kind code` (or `kinds={"code"}`) is passed.
- **CAP-5**
  - **intent:** Session agents have a durable instruction to use `scribe recall` for decisions and not treat graphify AST or `codegraph` as the same product.
  - **success:** `AGENTS.md` outside the `bmad:context` replace-block states when to recall, that default recall omits `code:`, and that Marshal `codegraph` owns navigation.

## Constraints

- Code ingest still writes through `open_graph_store` when the graphify extra is on.
- `valid_from` stays source-mtime so two compiles of unchanged sources stay byte-identical except for an actual stale flip.
- Cocoindex stays off `compile_graph`.
- Do not ingest `docs/` wholesale, `recipes/`, or the presentations export tree.

## Non-goals

- Replacing `codegraph.db`.
- Semantic/pgvector as the PyForge default.
- Portal UI redesign beyond inheriting CLI/`answer()` kind defaults.

## Success signal

`scribe recall` without `--kind` never returns a `code:` citation. A compile after CAP-1/2/3 writes Dreams, ready SPECs, and fact ledgers as `doc` and does not flag those just-read files stale because of mtime-vs-git.

## Assumptions

- Dream status vocabulary is `dreamt|pitched|specified|realized|archived`.
- Folder `SPEC.md` status vocabulary includes `ready|in-progress|shipped|draft`.
