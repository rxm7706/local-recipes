# pyforge-warden

Unified dependency-hygiene + vulnerability scanner that orchestrates
[`deptry`](https://deptry.com/) (unused / missing / transitive deps) and
Google's [`osv-scanner`](https://github.com/google/osv-scanner) (known CVEs)
over Python / Conda / Pixi manifests, emitting one schema-validated
`ComplianceReport` and acting as a strict CI/CD exit-code gate.

**Status:** Epics 1–8 shipped. Epic 9 Story 9.2 wraps those engines as the
default plugin bundle on `pyforge.core.hooks` and registers optional
commercial scanners as stubs. Specified in
[`docs/specs/pyforge-warden.md`](../../../../docs/specs/pyforge-warden.md).

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-warden warden-scan          # run the scanner
pixi run -e pyforge-warden pyforge-warden-test  # run the test suite
```

The `pyforge-warden` environment is lean by design (`no-default-feature`): it
carries only the built package plus its conda run-dependencies
(`python`, `deptry`, `osv-scanner`) and a test runner.

## Installing & adopting Warden

Three distribution paths cover local, air-gapped, and team-environment
adoption — pick the one matching your setup; none of them require network
access at scan time (`osv-scanner` runs fully offline against a locally
provisioned database, and KEV/EPSS enrichment is likewise cache-only).

- **Local install** — `pixi global install pyforge-warden` once it ships to
  a channel, or point at this repo's own local conda channel / internal
  JFrog Artifactory mirror in the meantime (the same channel the rest of
  this repo's feedstocks build against).
- **Air-gapped bundle** — `pixi-pack`/`pixi-unpack` a single self-contained
  archive for a host with no channel access at all: pack the
  `pyforge-warden` environment once on a connected machine, `pixi-unpack` it
  wherever the scan needs to run.
- **Team/nebi environments (alpha)** — a [nebi](https://github.com/nebari-dev/nebi)-managed
  team environment is itself a pixi workspace, so `nebi pull <ws>:<tag>` then
  `warden scan .` works with no extra wiring; `nebi push`/`pull` over an OCI
  registry is a candidate path for shipping the scanner env itself, not yet
  the recommended primary one for a security gate.

**First contact:** run `warden scan . --warn-only` in any project — it
reports every finding without failing the run on any of them, the
non-blocking on-ramp for trying the gate before wiring it into CI.
(A missing or out-of-range engine is still loud: it exits `2` even under
`--warn-only`. An unprovisioned offline OSV database is different — the
vulnerability axis composes `indeterminate` *findings*, which block by
default (exit `1`) but are downgraded like any other finding under
`--warn-only`, leaving that axis silently unassessed — so run `--doctor`
first to make sure the environment can assess what you think it is
assessing.)

**Environment self-check:** `warden scan --doctor` verifies the local
install itself — engine versions, the offline OSV database, and the
KEV/EPSS/endoflife feed caches — without scanning a project at all (no
discovery, no network). It exits `0` when everything checks out and `2`
when an engine or the offline OSV database is missing, unreadable, stale,
or out of its tested range, when a *provisioned* feed cache file is
unreadable or invalid, or when the KEV feed is present but stale (its gate
is on by default, so a stale KEV feed blocks every default scan's trusted
verdict) — always naming the specific problem. It never exits `1` —
`--doctor` reports on the environment's operability, never on a project's
policy compliance. An *absent* feed is reported as an informational
"operating air-gapped" line and does **not** fail the check — but note the
default `fail-on-kev` gate: until the KEV feed is provisioned (or that gate
is explicitly disabled), a default-config scan composes `indeterminate` on
the vulnerability axis rather than a trusted verdict.

## PR-gate hook book (Stories 9.1–9.2)

Warden publishes named hook specs on the shared FR-43 API
(`pyforge.core.hooks`). Scanner authors attach Checkmarx/Sonar/GHAS-shaped
plugins here; they do **not** fork Warden or mint a second loader.

| Spec | Name | Owner |
|---|---|---|
| scan | `pyforge.warden.pr_gate.scan` | `warden` |
| aggregate | `pyforge.warden.pr_gate.aggregate` | `warden` |
| verdict | `pyforge.warden.pr_gate.verdict` | `warden` |

**Registration group:** `pyforge.core.hooks` (`ENTRY_POINT_GROUP`) via
`PluginRegistry.register` / `load_entry_points`. There is no
`pyforge.warden.hooks` or `pyforge.warden.plugins` group.

**Default plugin bundle:** Null, Deptry, OSV, License, and Currency — the
same factories `register_engine` already lists. `warden scan` selects those
factories from in-tree plugins and still runs them on the existing thread
pool (including the hygiene filter that skips `DeptryEngine` when there is
no adjacent Python source).

**Optional scanners** (`checkmarx`, `sonar`, `blackduck`, `ghas`,
`profile-local`) are stubs. A default run does not require them. Enable
with `WARDEN_OPTIONAL_SCANNERS` (comma-separated ids). Enabling an optional
scanner may add `plugin_findings`; it cannot replace the Warden verdict
(only `publish_pr_gate_verdict`, owner `"warden"`, publishes the PR-gate).
A successful optional-plugin scan is not a competing PR-gate. Missing or
not-enabled optionals are omitted, not an error — Story 9.3 still owns the
absence-as-failure CI test.

**Scanner-author example.** A plugin is a `HookPlugin`: `hook_spec` (one of
the three names above), `owner` (the scanner, e.g. `"checkmarx"` — never
the verdict spec), and `call(point, context)` at `before` / `after` /
`around`. Register on the canonical group, not a Warden-only one:

```python
# my_scanner/plugin.py
class CheckmarxScanPlugin:
    hook_spec = "pyforge.warden.pr_gate.scan"
    owner = "checkmarx"

    def call(self, point: str, context: dict) -> object:
        # point is "before", "after", or "around"
        return context
```

```toml
# the scanner distribution's pyproject.toml — not Warden's
[project.entry-points."pyforge.core.hooks"]
checkmarx-scan = "my_scanner.plugin:CheckmarxScanPlugin"
```

**No second verdict:** only Warden publishes the PR quality-gate verdict
(`publish_pr_gate_verdict`, owner `"warden"`). A plugin that does not own
the verdict spec raises `SecondVerdictError`. Hooks do not project exit
codes; `verdict.py` remains sole owner of the lattice + `exit_code_for`.
`warden scan` may publish the composed `status` after lattice compose; it
does not let plugins set the process exit code.

**In-tree engines:** Deptry / OSV / license / currency remain listed in
`engines.py` `register_engine`. Story 9.2 wraps those factories; it does
not rewrite the engine classes.
