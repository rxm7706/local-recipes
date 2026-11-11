# pyforge-core

General documentation (architecture, operations, how-tos): docs/MAP.md at the repository root.

The shared leaf every pyforge station may depend on, and that depends on
none of them: pure stdlib at import, zero third-party runtime dependencies
(spec-pyforge-core:CAP-1). See
[`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md`](../../../../_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md)
for the leaf's Spec, and its companion
[`contract.md`](../../../../_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/contract.md)
(spec-pyforge-core:CAP-12) for the public contract: every module with the
capability that governs it, every public name a station may import, the
environment variables, feature-flag keys, exit codes, entry points and the
Python floor. `tests/meta/test_public_contract.py` fails the suite when the
source and the contract differ, so a change to that surface changes
`contract.md` in the same change. The hook-spec contract is
[`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-32-1-shared-hook-spec-and-plugin-registration-in-pyforge-core.md`](../../../../_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-32-1-shared-hook-spec-and-plugin-registration-in-pyforge-core.md).

## Modules

Import from the module; the package itself (`pyforge.core`) exports only
`__version__`. The public names of each module are in `contract.md`.

| Module | What it is | Governed by |
|---|---|---|
| `pyforge.core.atomic_write` | The one tmp-in-dir + `os.replace` write | spec-pyforge-core:CAP-2 |
| `pyforge.core.verdict` | The verdict-lattice rank and exit-domain bookkeeping | spec-pyforge-core:CAP-3 |
| `pyforge.core.report` | The base report envelope schema and its compose | spec-pyforge-core:CAP-4 |
| `pyforge.core.errors` | The shared exception root, `PyforgeError` | spec-pyforge-core:CAP-5 |
| `pyforge.core.process` | The one subprocess seam (`ProcessPort`, `PosixProcess`) | spec-pyforge-core:CAP-6 |
| `pyforge.core.dispatch` | The `pyforge <station> <noun> <verb>` front door | spec-pyforge-unifying-strategy:CAP-5, spec-pyforge-core:CAP-11 |
| `pyforge.core.roster` | The one Guild station roster | spec-pyforge-steward:CAP-137 |
| `pyforge.core.hooks` | The shared hook-spec and plugin registration | spec-pyforge-unifying-strategy:CAP-18 |
| `pyforge.core.client` | The host-relative station API client | spec-pyforge-unifying-strategy:CAP-6 |
| `pyforge.core.assertion` | The host-mint assertion client | spec-pyforge-unifying-strategy:CAP-6 |
| `pyforge.core.station_port` | The in-process station API port | spec-pyforge-unifying-strategy:CAP-6 |
| `pyforge.core.flags` | The fleet-wide CLI flag contract and kill switch | spec-feature-flag-governance:CAP-5, spec-feature-flag-governance:CAP-7, spec-pyforge-unifying-strategy:CAP-13 |
| `pyforge.core.cutover_root` | The root of record and its forge slug | fnd:CAP-8, spec-pyforge-core:CAP-13 |
| `pyforge.core.landing_evidence` | The one grammar of landing-evidence shapes | spec-pyforge-marshal:CAP-126 |
| `pyforge.core.preserve_refs` | The one grammar for preserved-work refs | spec-pyforge-marshal:CAP-287, spec-pyforge-steward:CAP-165 |
| `pyforge.core.published_loop` | The read side of the run-state publisher | spec-pyforge-unifying-strategy:CAP-17, spec-pyforge-marshal:CAP-227 |
| `pyforge.core.league_measure` | The published-measure cite gate | spec-pyforge-steward:CAP-46 |

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
name a tracked story spec (today `spec-24-3-atlas-s-mcp-tools-pass-the-cli-tool-parity-gate`,
which superseded the preparatory `spec-22-prep-atlas-kedro-cli-introspection`, now under `archive/`);
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
