# Memlog — spec-33-3-the-layers-are-enabled-on-factory-spin-or-spin-is-declared-a-two-layer-engine

## 2026-09-09 — Story 33.3 implementation ruling

**Branch taken:** wire layer enabled on `factory spin` via bmad-loop profile overlay (not the
two-layer-engine declaration).

**Evidence:** `attempt_spin_wire_layer` in `adapters/harness_bmadloop.py` copies the packaged
bmad-loop profile, rewrites `binary`/`launch_args`/`env` from marshal's harness `[wrapper]`, and
atomically writes `<loop_home>/.bmad-loop/profiles/<adapter>.toml` before `harness.spin`. When
headroom resolves on PATH, `wire.applied=True` and no `MRS-SPIN-017` fires.

**Also landed:** `_compose_spin_policy` folds `read_repo_policy_defaults()` on spin (both
`_resolve_model_tiering` and `_spawn_supervisor_sidecar` composition sites), closing `DW-FU-28-2-3`.

**Residual:** derived-context and planning-graph layers remain unavailable on spin (by design —
bmad-build-auto step 01). Adapters without a marshal `[wrapper]` (e.g. codex-only paths) still
degrade wire with a named reason.
