# pyforge-core

The shared leaf every pyforge station may depend on, and that depends on
none of them. Pure stdlib, zero third-party runtime dependencies. Stories
14.2–14.4 extracted the atomic-write primitive, verdict lattice, report
envelope, exception root, and subprocess guard here. Story 32.1 adds the
**shared hook-spec and plugin registration** surface (`pyforge.core.hooks`)
in this same package — stations consume it; they do not ship a second
loader. See
[`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md`](../../../../_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md)
for the leaf contract, and
[`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-32-1-shared-hook-spec-and-plugin-registration-in-pyforge-core.md`](../../../../_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-32-1-shared-hook-spec-and-plugin-registration-in-pyforge-core.md)
for the hook-spec contract.

**Status:** The leaf is no longer an empty 14.1 scaffold. Primitives live
here; the canonical plugin group is `pyforge.core.hooks` only. Story 22.1
adds the unified `pyforge` console script (CAP-5 / FR-13): dispatch to
existing station binaries, never a second implementation of station logic.

## Unified CLI (`pyforge <station> <noun> <verb>`)

`pyforge` maps the station token to that distribution's **primary** console
script (`steward`, `warden`, `pyforge-atlas`, … — never a sibling `*-mcp`
extra) and forwards the rest of argv through `PosixProcess`.

```text
pyforge steward keys list   →  steward keys list
pyforge mason recipe build  →  mason recipe build
```

No station duty tables live in `pyforge.core.dispatch`. A verb added to a
station CLI is reachable because forwarding has no allowlist; CI generates
a parity matrix from sibling `pyproject.toml` files plus AST introspection
(`add_parser` / Typer commands). If those two surfaces drift, the build
fails. A CLI that cannot be introspected (atlas Kedro/Click today) must
name a preparatory story (`spec-22-prep-atlas-kedro-cli-introspection`);
silently omitting the station is a test failure.

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-core pyforge-core-test  # run the test suite
```

The `pyforge-core` environment is lean by design (`no-default-feature`): it
carries only the built package (stdlib only, no runtime dependency beyond
`python`) and a test runner. `dependencies = []` in `pyproject.toml` stays
empty — no pluggy, no setuptools as a runtime dep.

## Hook-spec shape and plugin registration

`pyforge.core.hooks` publishes:

| Piece | Role |
|---|---|
| `HookSpec` | `name` + process `owner` |
| `HookPlugin` | protocol: `hook_spec`, `owner`, `call(point, context)` |
| `PluginRegistry` | `register`, `load_entry_points`, `invoke(point, context, *, spec_name=)` |
| `DummyPlugin` | in-tree dummy for spec `pyforge.core.example` / owner `core` |
| `HOOK_POINTS` | `before`, `after`, `around` |
| `publish_verdict` | owner-matched verdict publish only |

**Entry-point group:** `pyforge.core.hooks` (`ENTRY_POINT_GROUP`). The
loader uses `importlib.metadata.entry_points(group=...)`, then
load/instantiate. A bad target raises `PluginError`; a declared name is
never silently skipped.

**`around`:** `plugin.call("around", context)` may run
`context["next"](context)` to continue the chain. If `next` is absent,
`around` is still invoked (documented equivalent). Unknown points raise
`PluginError`. `invoke` requires `spec_name` so loading the dummy entry
point never runs it on another process's hooks.

**Dummy plugin:** declared on `pyforge.core.hooks` for the example spec
`pyforge.core.example` / owner `core`. Stations invoke their own spec
name; they do not treat the dummy as a production plugin.

**No second verdict:** `publish_verdict(spec, plugin, verdict)` is allowed
only when `plugin.hook_spec == spec.name` **and** `plugin.owner ==
spec.owner`. Otherwise it raises `SecondVerdictError` (a `PyforgeError`).
The dummy owns `pyforge.core.example` / `core`; a plugin must not publish a
verdict for a process another owner specified.

Station packages must **not** declare a parallel group
`pyforge.<station>.hooks` or `pyforge.<station>.plugins`. That is a
conformance failure (`tests/meta/test_plugin_registration_conformance.py`).

### Not plugin surfaces

These are **not** plugin extension points (`NOT_PLUGIN_SURFACES`):

- Pixi task names
- Golden Path artifact identity
- parent infra kinds
- host import boundary (`pyforge.*` under `src/platform/`)
- the Warden verdict itself

## The leaf constraint

`tests/meta/test_leaf_constraint.py` structurally enforces two rules for
every module under `pyforge.core`:

- no import from `pyforge.<X>` for any `X != "core"` — no station import,
  ever;
- no import outside `sys.stdlib_module_names` and the `pyforge` namespace
  itself — no third-party runtime dependency, ever.

Both guards are proven non-vacuous against synthetic-violation fixtures,
not just by scanning the real package. `importlib.metadata` is stdlib.
