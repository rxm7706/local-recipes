---
title: 'Adapter probe with a machine-scoped record'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 2
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md', '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-6-3-projection-drift-detection-that-can-actually-fail.md', '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-6-1-profile-driven-adapter-selection-project-scoped.md']
warnings: []
baseline_revision: 'HEAD as of 2026-08-07, immediately after S-6.3 (open PR, not yet merged, but stable)'
---

<intent-contract>

## Intent

**Problem:** Epic 6's own goal names the gap directly: "BMAD runs on any agent" is
today an aspiration, not a fact, because nothing OBSERVES what a configured adapter
actually supports on THIS operator's machine. Stories 6.1-6.3 resolve/select/project/
verify skill-tree PLACEMENT, but none of them ever launches or interrogates the
adapter's own binary -- Marshal's portability claims to date rest entirely on a
declarative `CLIProfile` (packaged TOML), never on a live observation. FR-43 requires
a `marshal adapters probe` action that DOES observe: binary presence, its version, the
profile's own declared capabilities, and real probe output from the harness -- and
records that observation somewhere durable enough to inform Story 6.5's smoke run and
Story 6.6's conformance matrix, without leaking whatever a probed CLI's `--version`/
`--help`/JSON output happens to carry (an operator's own installed binary output is
exactly the kind of free text that can contain a stray token, a local username, or a
path -- the same class of risk AD-34 already names for pane-derived content).

**Approach:** `HarnessPort` (`ports/harness.py`) gains one new method,
`adapter_probe(adapter_name, project) -> AdapterProbe` -- a bundled-facts value type
mirroring `UsageSnapshot`/`RunStatusSnapshot`'s own "facts the caller could not have
known in advance" convention, since the AC asks for three distinct facts (presence+
version, declared capabilities, probe output) captured together as one observation.
`BmadLoopHarness` (`adapters/harness_bmadloop.py`) implements it by reusing the
EXISTING `_get_profile` seam (raises `HarnessError` for an unknown adapter name or an
unimportable `bmad_loop`, the identical contract `adapter_binary`/`adapter_seed_files`
already have) to resolve the profile, then: (1) `binary_present`/a single sanctioned
`<binary> --version` subprocess call, mirroring `harness_version`'s own "never raise,
degrade to `None`" convention -- an absent binary is NOT an error, it is the AC's own
`"unavailable"` outcome; (2) a curated, pure subset of the resolved `CLIProfile`'s own
already-declared fields (`hookless`, `hooks.dialect`, `usage_parser`, `skill_tree`,
`model_flag`) as `capabilities` -- no new upstream surface, no subprocess; (3) ONE
bounded subprocess call to the REAL installed `bmad-loop probe-adapter --cli <name>
--json` in its default SCAN mode (confirmed live against the installed 0.9.0 package,
`bmad_loop/probe.py`: SCAN is "zero process launch beyond `--version`/`--help`",
never the interactive, tmux-launching `--probe` mode -- that mode is explicitly out of
this story's scope, see Boundaries & Constraints), whose stdout is redacted AT
CAPTURE via the EXISTING `_redact_text` helper (the same `to_redacted({"text": text});
json.loads(...)["text"]` round-trip `run_status_snapshot`'s `paused_reason`/
`defer_reason` and `observer_mux.py::pane_content` already establish for AD-34 --
"pane-derived content is redacted at capture, before it enters `core`") before it is
ever returned to a caller. `core/conformance.py` (already this epic's home for
adapter-facts status vocabulary) gains a SECOND, independent closed status pair --
`STATUS_AVAILABLE`/`STATUS_UNAVAILABLE` -- and a pure `build_probe_record(probe) ->
dict` shaping function (mirroring `core.egress.build_gate_record`'s own "caller
already gathered every fact, this function only shapes" convention), classifying
`STATUS_UNAVAILABLE` if and only if `binary_present` is `False`; this is a DIFFERENT
vocabulary from `STATUS_LINK_TARGET_CONFIRMED`/`ADDED`/`REMOVED`/`MODIFIED` (a
different fact -- "does this adapter exist on this host" is not "did a projected tree
drift" -- never conflated, never sharing a constant).

`cli/adapters.py` gains the new standalone action `marshal adapters probe <slug>
--adapter <name>` (the `probe` slot the Consistency Conventions table already
reserved, confirmed live in this same file's own docstring: `adapters <sub>:
sync|probe|conform|matrix|check`), `run_adapters_probe`, reusing the SAME slug/home
preconditions `sync`/`conform` already check (`MRS-ADP-001`/`002` verbatim -- the
`MRS-DEPLOY-003` "same code, same tier, a new call site" precedent this epic's own
Story 6.3 already applied twice). It calls `harness.adapter_probe`, shapes the result
via `build_probe_record`, and -- AD-34's own "redaction is a port-boundary property,
never a call-site one" -- routes the WHOLE shaped record through `core.egress.
to_redacted` (the ONE redacting serializer this package owns; `probe_output` is
ALREADY redacted once, at capture, by `_redact_text` inside the adapter -- routing the
outer record through `to_redacted` again is idempotent on already-redacted text and is
what makes every OTHER field -- `binary_version`, `capabilities` values -- covered by
the SAME single serializer AD-34 requires, rather than assuming only `probe_output`
could ever carry something secret-shaped) before writing. The write target is AD-37's
"single declared machine-scoped path for host-and-adapter facts" -- which this
codebase has ALREADY built, for a different fact: `cli/init.py::_ack_state_path`
resolves `$MARSHAL_STATE_HOME` (or `~/.local/state/pyforge-marshal`, anchored absolute)
as exactly that path, currently used only for `adapter-acknowledgements.json`. This
story extracts the base-directory half of that function into a new, shared
`_machine_state_dir() -> Path` (`_ack_state_path` becomes a one-line caller of it,
behavior UNCHANGED) and adds a SECOND filename under the SAME base directory,
`adapter-probes.json` -- one JSON object, keyed by adapter name, each value the
adapter's LATEST probe record (mirrors `adapter-acknowledgements.json`'s own "one file,
one collection" shape rather than proliferating one file per adapter). `cli/adapters.py`
imports `_machine_state_dir` from `.init` at MODULE level, mirroring this same file's
own existing `from .init import _home_path` -- no new circular-import risk, since this
is the SAME direction (`adapters.py -> init.py`) that import already establishes.

**Read-only reporting vs. a run that depends on it (AD-31).** `run_adapters_probe`
NEVER registers a `Finding` for `binary_present is False` -- the AC's own "reports it
as `unavailable` and exits 0" is satisfied structurally: an absent adapter produces
`data.probe.status == "unavailable"` with an EMPTY findings list, so `compute_verdict`
folds to `Verdict.CLEAN` and exits `0`. This is a genuine, stated interpretive call:
the epics AC's own prose ("the same condition is `unevaluable` anywhere a run depends
on it") is read as pointing at an ALREADY-SHIPPED precedent, not a new obligation this
story must build -- `cli/init.py::run_preflight`'s `MRS-PREFLIGHT-004` already reports
"the configured adapter... its binary is not on PATH" at `Verdict.ERROR` (a real,
blocking prerequisite check, the tier every one of `MRS-PREFLIGHT-001`-`009` shares),
because THAT call site is a run precondition. This story's own `probe` verb is a
DIFFERENT call site -- explicitly read-only, explicitly reporting, never gating a
launch -- so it needs no new code and no new tier: the SAME real-world fact
("`claude` is not on PATH") already classifies differently by CONTEXT in this
codebase, exactly as AD-31 requires, and this story's only obligation is to not
regress `MRS-PREFLIGHT-004`'s own existing blocking behavior while adding the
non-blocking one.

## Boundaries & Constraints

**Always:**
- **`HarnessPort.adapter_probe` never raises for an absent adapter binary or a
  probe-subprocess failure** -- only for an unknown `adapter_name` or an unimportable
  `bmad_loop` (`_get_profile`'s existing contract, reused verbatim). Every other
  failure (binary absent, `--version` unparseable/timed out, `probe-adapter --json`
  non-zero/timed out/non-JSON) degrades to a `None`/`False` field on the returned
  `AdapterProbe`, never an exception -- mirrors `harness_version`'s own "never raises"
  convention for the identical class of subprocess flakiness.
- **`probe_output` is redacted BEFORE it ever leaves `adapters/harness_bmadloop.py`**
  (AD-34's "pane-derived content is redacted at capture, before it enters `core`"),
  via the SAME `_redact_text` helper `run_status_snapshot` already uses -- no second,
  bespoke redaction vocabulary for this one new field.
- **The outer probe record is ALSO routed through `core.egress.to_redacted` at the
  `cli/adapters.py` write boundary**, never at any earlier call site -- `RecordPort.
  write_redacted_atomic` accepts ONLY a `Redacted` payload (the structural half of
  AD-34's guarantee, `tests/meta/test_ad34_egress_registry_completeness.py`), so no
  code path can write an unredacted record even by omission.
- **`run_adapters_probe` reuses `MRS-ADP-001`/`002` verbatim** for the slug-shape and
  home-provisioned preconditions it shares with `sync`/`conform` (AD-31's
  `MRS-DEPLOY-003` precedent, already applied twice this epic).
- **The write target resolves through the SAME `_machine_state_dir()`/
  `MARSHAL_STATE_HOME` override `_ack_state_path` already established** -- one shared
  base-directory resolver, never a second env-var convention or a second default path.
- **A probe record NEVER lands in any project's own artifacts** (loop home, Tier-3
  store, or `planning-artifacts/`) -- `run_adapters_probe` touches the loop home only
  to resolve the project-local profile overlay `HarnessPort.adapter_probe` reads
  (`project` is passed for THAT resolution only, mirroring `adapter_binary`'s existing
  contract) and writes nowhere under it.
- **`marshal adapters probe` never mutates the loop home, the skill-tree projection,
  or the projection manifest** -- read-only with respect to every artifact `sync`/
  `conform` own; its only write is the one machine-scoped file.

**Never:**
- **No live launch of the probed adapter.** `bmad-loop probe-adapter`'s own `--probe`
  flag (tmux session, a real content-free turn, hook-payload capture) is explicitly
  OUT of this story's scope -- this story invokes only the DEFAULT scan mode ("zero
  process launch beyond `--version`/`--help`", confirmed live against the installed
  0.9.0 `bmad_loop/probe.py` module docstring). A future story may add `--probe`
  support; this one does not, and `adapter_probe`'s own implementation never passes
  `--probe`.
- **No second redaction vocabulary.** Every redacting call in this story's own new
  code goes through `core.egress.to_redacted`/the existing `_redact_text` helper --
  no new regex, no new secret-key list.
- **No new `Verdict.UNEVALUABLE`-labeled reporting of "adapter absent" from this
  verb.** That reading belongs to a run precondition (`MRS-PREFLIGHT-004`, already
  shipped, unchanged by this story); `probe`'s own read-only surface reports
  `"unavailable"` as plain DATA, with no finding and no non-zero exit.
- **No dispatch on adapter name.** `adapter_probe` reads everything it needs from the
  resolved `CLIProfile` plus two generic subprocess primitives (`--version`,
  `bmad-loop probe-adapter --json`) -- no `if adapter_name == "..."` branch anywhere
  (AD-19, this codebase's existing meta-test `test_ad19_no_adapter_branch.py` already
  covers this file).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| A named adapter's binary is present and versioned | Ordinary case | `status == "available"`, `binary_version` set, `capabilities` populated, `probe_output` a redacted JSON string | No finding |
| A named adapter's binary is absent from `PATH` | Not installed on this host | `status == "unavailable"`, `binary_version: null`, `probe_output: null` | No finding; exits 0 |
| `--version` subprocess call fails/times out (binary present) | Flaky/hung binary | `binary_version: null`, everything else still populated | No finding (mirrors `harness_version`'s own degrade) |
| `bmad-loop probe-adapter --cli <name> --json` exits non-zero, times out, or emits non-JSON | Probe subsystem unavailable/broken | `probe_output: null`, `probe_note` names why | No finding (best-effort observation) |
| The `--cli` name is unknown to `bmad_loop`'s own profile registry AND no `--binary` override applies | Truly unknown adapter | `HarnessError` from `adapter_probe` (via `_get_profile`) | Registered finding (`MRS-ADP-014`, UNEVALUABLE) |
| `bmad_loop` itself is not importable | Broken/absent install | `HarnessError` from `adapter_probe` | Registered finding (`MRS-ADP-014`, UNEVALUABLE) |
| `probe_output`'s raw text contains a token-shaped or secret-keyed value | e.g. a stray API key in `--help` output | Redacted twice (at capture via `_redact_text`, again idempotently at the outer `to_redacted` write) -- never reaches disk in plaintext | No finding |
| Writing the machine-scoped record fails (unwritable `MARSHAL_STATE_HOME`, disk full) | I/O failure | Envelope still reports the observed `data.probe` (the OBSERVATION succeeded even if the WRITE did not) | Registered finding (`MRS-ADP-015`, ERROR) |
| A pre-existing `adapter-probes.json` is malformed JSON | Corrupt bookkeeping | Treated as an empty collection (mirrors `_read_acknowledged`'s own degrade); this probe's own entry still writes | Registered finding (`MRS-ADP-016`, WARN) |
| `--adapter` is omitted or blank | Missing required identifier | No filesystem/harness touch at all | Registered finding (`MRS-ADP-013`, UNEVALUABLE) |
| An unresolvable/malformed project slug | Precondition | No filesystem/harness touch at all | Registered finding (`MRS-ADP-001` reused, ERROR), mirrors `sync`/`conform` |
| The named loop home is not provisioned | Precondition | No filesystem/harness touch at all | Registered finding (`MRS-ADP-002` reused, ERROR), mirrors `sync`/`conform` |
| Two probes of different adapters, same machine, same day | Ordinary repeated use | Each write MERGES into the same `adapter-probes.json` (read-modify-write, keyed by adapter name) -- probing `codex` never erases `claude`'s own prior entry | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/harness.py` -- EDIT. New frozen dataclass `AdapterProbe`
  (`adapter: str`, `binary: str`, `binary_present: bool`, `binary_version: str | None`,
  `capabilities: Mapping[str, object]`, `probe_output: str | None`, `probe_note: str |
  None`) mirroring `UsageSnapshot`/`RunStatusSnapshot`'s own "facts the caller could
  not have known in advance" convention. New `HarnessPort.adapter_probe(adapter_name,
  project) -> AdapterProbe` method, docstring mirroring `adapter_binary`'s exact
  raise-contract ("Raises `HarnessError` for an unknown `adapter_name` or an
  unimportable `bmad_loop`; never raises for anything else -- an absent binary or a
  failed probe subprocess degrades to `None`/`False` fields").
- `src/pyforge/marshal/adapters/harness_bmadloop.py` -- EDIT. New module constant
  `_PROBE_TIMEOUT_S = 30.0` (generous relative to `_VERSION_TIMEOUT_S = 5.0`: scan
  mode's own `--help` capture is documented up to 80 lines). New `_CAPABILITY_FIELDS`
  -- the curated, named subset of `CLIProfile` this story reads (`hookless`,
  `hooks.dialect`, `usage_parser`, `skill_tree`, `model_flag`). New `BmadLoopHarness.
  adapter_probe`: resolves the profile via the EXISTING `self._get_profile(adapter_name,
  project)` (unchanged, reused verbatim -- the same `HarnessError` contract);
  `binary_present = self.binary_present(profile.binary)`; if absent, returns
  immediately with `binary_version=None`, `probe_output=None`, `probe_note="binary not
  found on PATH"` (capabilities still populated -- pure data, no subprocess needed);
  if present, one `_run([profile.binary, "--version"])` call (mirrors `harness_version`'s
  own parse-or-`None` shape) for `binary_version`, then one `_run(["bmad-loop",
  "probe-adapter", "--cli", adapter_name, "--json"], timeout_s=_PROBE_TIMEOUT_S)` call;
  on a clean `returncode == 0` result, redact `result.stdout` via the EXISTING
  `_redact_text` static method and store it as `probe_output` (`probe_note=None`); on
  any other outcome (`None`, non-zero, or `_redact_text` itself returning `None` for an
  unredactable payload), `probe_output=None` with a `probe_note` naming which.
- `src/pyforge/marshal/core/conformance.py` -- EDIT. New status constants
  `STATUS_AVAILABLE = "available"`, `STATUS_UNAVAILABLE = "unavailable"` (a SECOND,
  independent closed pair -- never merged into `ALL_STATUSES`, which stays Story 6.3's
  own tree-drift vocabulary unchanged). New pure `build_probe_record(probe:
  ports.harness.AdapterProbe) -> dict[str, object]`: `status = STATUS_UNAVAILABLE if
  not probe.binary_present else STATUS_AVAILABLE`; returns a plain dict with keys
  `adapter`, `binary`, `status`, `binary_present`, `binary_version`, `capabilities`
  (`dict(probe.capabilities)`), `probe_output`, `probe_note` -- no I/O, no clock, no
  `os`/`subprocess`/adapters import (AD-4 unchanged; this module imports
  `ports.harness.AdapterProbe` only for the type hint, the SAME "ports declare shapes"
  layering `core/skill_projection.py` already crosses for its own port-typed
  parameters).
- `src/pyforge/marshal/cli/init.py` -- EDIT. Extract `_ack_state_path`'s base-directory
  resolution into a new `_machine_state_dir() -> Path` (the `MARSHAL_STATE_HOME`
  override / `~/.local/state/pyforge-marshal` default / CWD-anchoring logic, verbatim,
  unchanged behavior); `_ack_state_path` becomes `return _machine_state_dir() /
  _ACK_STATE_FILENAME`, a pure one-line caller. No other change to this file's own
  Story 1.7 surface.
- `src/pyforge/marshal/cli/adapters.py` -- EDIT. Module-level `from .init import
  _home_path, _machine_state_dir` (extends the existing import statement -- same
  direction, no new circular-import risk). New `_PROBE_STATE_FILENAME =
  "adapter-probes.json"`. New `add_adapters_subparser` nested action `probe`
  (`marshal adapters probe <slug> --adapter <name> [--format]`). New
  `_render_text_probe(data, findings) -> str` mirroring `_render_text_conform`'s own
  shape. New `run_adapters_probe(args, *, fs=None, harness=None, context=None)`: slug
  shape (`MRS-ADP-001`) -> home provisioned (`MRS-ADP-002`) -> `--adapter` non-blank
  (`MRS-ADP-013`, checked before any harness/filesystem touch) -> `harness.
  adapter_probe(adapter, home)` wrapped in `try`/`except HarnessError`
  (`MRS-ADP-014`) -> `record = build_probe_record(probe)`, `data["probe"] = record` ->
  read the existing `adapter-probes.json` (via `fs.read_text`, degrading malformed/
  missing JSON to `{}` with `MRS-ADP-016` on malformed -- mirrors `cli/init.py::
  _read_acknowledged`'s own degrade) -> merge `{adapter: record}` into it -> `fs.
  write_redacted_atomic(_machine_state_dir() / _PROBE_STATE_FILENAME,
  to_redacted(merged))` wrapped in `try`/`except FsError` (`MRS-ADP-015`) -> `_emit`
  with `command="adapters probe"`, `renderer=_render_text_probe`. No finding is EVER
  registered for `record["status"] == "unavailable"` on its own.
- `src/pyforge/marshal/core/findings.py` -- EDIT. Register four new codes:
  `MRS-ADP-013` (missing/blank `--adapter`), `MRS-ADP-014` (`adapter_probe` raised
  `HarnessError`), `MRS-ADP-015` (writing the machine-scoped record failed),
  `MRS-ADP-016` (a pre-existing `adapter-probes.json` was malformed JSON).
- `src/pyforge/marshal/core/verdict.py` -- EDIT. Classify `MRS-ADP-013` at
  `Verdict.UNEVALUABLE` (mirrors `MRS-STATUS-003`'s own "a required companion
  argument is missing, checked before any I/O" tier), `MRS-ADP-014` at
  `Verdict.UNEVALUABLE` (mirrors `MRS-SPIN-014`'s own "an adapter name could not be
  resolved to a real profile" tier), `MRS-ADP-015` at `Verdict.ERROR` (mirrors
  `MRS-ADP-006`/`008`'s own "a real write was attempted and failed" tier), `MRS-ADP-016`
  at `Verdict.WARN` (mirrors `MRS-ADP-009`'s own "malformed bookkeeping degrades,
  never blocks" tier).
- `tests/unit/test_harness_bmadloop_probe.py` -- NEW. `adapter_probe` matrix: binary
  present + versioned + probe JSON captured; binary absent (no subprocess calls at
  all, asserted via a spy `_run`); `--version` failure degrades `binary_version` only;
  `probe-adapter --json` failure/timeout/non-JSON degrades `probe_output` only with a
  `probe_note`; unknown adapter / unimportable `bmad_loop` raise `HarnessError`;
  `probe_output` redaction round-trip (a synthetic token-shaped string in the faked
  subprocess stdout comes back sentinel-substituted, never verbatim).
- `tests/unit/test_conformance.py` -- EDIT. `build_probe_record` matrix: available,
  unavailable, `binary_version`/`probe_output`/`probe_note` each `None` independently;
  `STATUS_AVAILABLE`/`STATUS_UNAVAILABLE` never appear in `ALL_STATUSES` (the tree-drift
  vocabulary stays closed and unchanged).
- `tests/unit/test_adapters_cli.py` -- EDIT. `run_adapters_probe` matrix reusing the
  existing `FakeFs`/`FakeHarness` doubles (extended with `adapter_probe`): available,
  unavailable (no finding, exit 0), unknown adapter, missing `--adapter`, malformed
  slug, home not provisioned, write failure, pre-existing malformed `adapter-probes.json`
  (merge preserves other adapters' entries), `--format text` rendering, and a
  round-trip proving the WRITTEN file's bytes are the `to_redacted` output (never a
  bare `json.dumps` of the unredacted record).
- `tests/unit/test_init.py` -- EDIT. `_machine_state_dir`/`_ack_state_path` behavior
  is UNCHANGED (existing tests keep passing unmodified); one new test asserts
  `_ack_state_path() == _machine_state_dir() / "adapter-acknowledgements.json"`,
  pinning the refactor did not change the resolved path.
- `tests/unit/test_findings.py` -- EDIT. `REGISTERED_CODES` snapshot gains the four
  new codes.
- `tests/meta/test_ad11_write_boundary.py` -- EDIT (audited during implementation; a
  new write target -- `adapter-probes.json` under the SAME machine-scoped base
  `adapter-acknowledgements.json` already uses -- needs no new allowed-target entry if
  that test already permits the machine-scoped base directory generically; extended
  only if it currently hardcodes the ack filename specifically).
- `tests/meta/test_probe_json_contract.py` -- NEW (NFR-9). Imports the REAL installed
  `bmad_loop.probe` module directly (test-only exception to AD-3's "only
  `adapters/harness_bmadloop.py` imports `bmad_loop`" rule -- the SAME exception
  `tests/meta/test_ad34_egress_registry_completeness.py` already takes to inspect
  package internals) and asserts, character-for-character: `bmad_loop.probe.
  SCHEMA_VERSION == 2` (a bump means the JSON document's own shape changed and this
  test must be revisited before trusting `probe_output`'s contents downstream), and
  that `render_json`'s own output for a synthetic `ProfileFinding` contains EXACTLY
  the key set this story's own docstring names (`schema_version`, `cli`, `mode`,
  `known_profile`, `binary`, `binary_found`, `dialect`, `usage_parser`,
  `hooks_registered`, `declared_events`, `version`, `help`, `captured_events`,
  `transcript`, `tokens`, `warnings`, `next_steps`) -- a key added, renamed, or removed
  upstream fails this test loudly, rather than silently changing what `probe_output`
  (opaque to Marshal today -- stored, never parsed) actually contains.

## Design Notes

- **Why `adapter_probe` invokes `bmad-loop probe-adapter`'s SCAN mode, never `--probe`.**
  The AC's own "probe output" is satisfied by either mode, but `--probe` launches the
  real adapter CLI in a live tmux session for a real (if content-free) turn --
  interactive-adjacent, environment-dependent (needs a working multiplexer + an
  authenticated CLI), and far more expensive than a routine `marshal adapters probe`
  invocation should be. SCAN mode -- confirmed live against the installed 0.9.0
  `bmad_loop/probe.py` module docstring as "zero process launch beyond `--version`/
  `--help`" -- matches this story's own Effort: M budget and its AC's plain-English
  "records binary presence and version... and probe output" far better than a live
  launch would. A future story may add `--probe` support explicitly; this one does
  not, and the Boundaries & Constraints section states this as a genuine, recorded
  scope decision rather than a silent omission.
- **Why "the profile's declared capabilities" is read as a curated field subset, not a
  literal `capabilities` attribute.** `bmad_loop.adapters.profile.CLIProfile` (the
  installed 0.9.0 package, confirmed live) has no field named `capabilities` -- the
  AC's own phrasing describes WHAT a profile declares about an adapter's support
  surface, not a literal upstream attribute name. `hookless` (HTTP/SSE-only, no
  hook-driven completion detection), `hooks.dialect` (does it support hooks at all,
  and which shape), `usage_parser` (does it support token-usage tracking), `skill_tree`
  (where does it read skills from), and `model_flag` (can per-story model tiering
  reach it, Story 6.1's own FR-51 concern) are exactly the fields THIS package's own
  other `HarnessPort` methods already read individually (`adapter_binary`/
  `adapter_seed_files`/`adapter_first_run_note`) -- this story bundles a READ-ONLY
  reporting subset of the SAME profile, adding no new upstream dependency.
- **Why `probe_output` is stored OPAQUE, never parsed.** `bmad-loop probe-adapter
  --json`'s own document (SCHEMA_VERSION 2) is a rich, nested structure Marshal has no
  present use for beyond "did the probe subsystem produce something, and what did it
  say" -- parsing and re-shaping it into Marshal's own typed fields would duplicate a
  schema this story's own NFR-9 contract test already pins the SHAPE of without
  needing to consume every field. Storing the whole (already twice-redacted) JSON text
  verbatim keeps this story's own scope to "capture and record," leaving "interpret"
  for whichever later story (6.5's smoke run, 6.6's matrix) actually needs a typed
  field out of it -- at which point that story reads THIS field, never re-invokes the
  subprocess a second way.
- **Why AD-31's "unevaluable anywhere a run depends on it" needed no new code.** See
  the Intent section's own paragraph -- `MRS-PREFLIGHT-004` already exists, already
  fires at `Verdict.ERROR` (this codebase's own "a real precondition ran and failed"
  tier, not literally the enum member `Verdict.UNEVALUABLE`) for the identical
  real-world fact from a run-dependent call site. Re-reading the AC's "unevaluable" as
  a REFERENCE to that shipped precedent, rather than a literal instruction to emit
  `Verdict.UNEVALUABLE` from a NEW code, avoids inventing a second, differently-tiered
  classification for the same underlying fact this codebase's own AD-31 doctrine
  ("the SAME code never classifies two different rungs depending on context") argues
  against -- this story adds nothing to the `MRS-PREFLIGHT-*` area at all.
- **Why the machine-scoped write extracts `_machine_state_dir()` rather than
  duplicating `_ack_state_path`'s override logic.** AD-37 requires ONE declared
  machine-scoped path (a base directory), not one per fact stored under it --
  `cli/init.py::_ack_state_path` already resolves that base correctly (`
  MARSHAL_STATE_HOME` override, CWD-anchored-if-relative, `~/.local/state/
  pyforge-marshal` default) for Story 1.7's own acknowledgement file. Copying that
  logic into `cli/adapters.py` would create a second, driftable spelling of the SAME
  path AD-37 declares as singular; extracting it into a small shared helper (reused,
  never duplicated) is the direct structural expression of "single declared path."
- **Why the conformance matrix (AD-37's OTHER half) is explicitly out of this story's
  scope.** The architecture's own 2026-07-30 amendment (F-7) resolved the matrix to a
  TRACKED, per-host artifact at `planning-artifacts/conformance/matrix/<hostname>.md`
  -- a wholly different write target, format, and story (6.6). This story's own AC
  text and epics-doc Surface line name only the RAW probe record, which AD-37's text
  is explicit stays machine-scoped ("Raw probe records stay machine-scoped -- they are
  transient host facts, not a claim"). Nothing in this story writes to, or reads from,
  the tracked matrix path.
- **Why `MRS-ADP-016`'s malformed-file degrade merges rather than overwrites.** A
  malformed `adapter-probes.json` (hand-edited, or corrupted mid-write by an unrelated
  process) is treated as an empty collection for READING purposes -- mirrors
  `_read_manifest`'s own Story 6.2 precedent -- but this run's own successful probe
  still writes its own entry, so one malformed file never blocks the operator from
  recording a fresh, valid observation; it only means whatever OTHER adapters' prior
  entries were in that corrupted file are lost (named by the WARN finding, never
  silently absorbed).
- **No shape-pinning precedent existed in this codebase for NFR-9's "fails loudly on
  upstream drift" requirement** (researched directly: `grep`ped every test file under
  `tests/meta/` and `tests/unit/test_harness_bmadloop_*.py` for `SCHEMA_VERSION`/
  `dataclasses.fields`/"contract test" -- none exists; the closest sibling is
  `HARNESS_VERSION_RANGE_TEXT`'s own `>=0.9.0,<0.10` VERSION-range guard, which pins a
  number, not a document SHAPE). `tests/meta/test_probe_json_contract.py` is
  therefore this story's own new idiom -- importing the real installed package
  in-process (test-only, mirroring the ALREADY-established `test_ad34_egress_
  registry_completeness.py` exception to AD-3's layering) and asserting both the
  version constant and the literal key set, rather than a live subprocess round-trip
  (which would need a real `bmad-loop` install matching the pinned range to run at
  all, and this test should fail identically whether or not one is present on the CI
  host).

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **2897 passed** (2867
  baseline from S-6.3 + 30 new: `HarnessPort.adapter_probe`'s own 11 unit tests
  (`test_harness_bmadloop_probe.py`), `core.conformance.build_probe_record`'s 4
  (`test_conformance.py`), `run_adapters_probe`'s 13 (`test_adapters_cli.py`), one
  `_ack_state_path`/`_machine_state_dir` pinning test (`test_init.py`), plus the
  `REGISTERED_CODES` snapshot addition (`test_findings.py`) and the NEW
  `tests/meta/test_probe_json_contract.py` (2, NFR-9)).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 3 failed, all pre-existing
  accepted baseline (2 `pyforge-steward` -- `_http` module-alias gap, `age` conda-only
  run-dep; 1 `pyforge-doctor` -- `mcp` dependency gap), unrelated to this story.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- AD-3, AD-4, AD-9 all KEPT (87 files, 484 dependencies analyzed).

## Review Triage Log

No adversarial review pass was run for this session (single-agent implementation, no
Blind Hunter/Edge Case Hunter fan-out requested, mirroring Story 6.3's own precedent
for when one is not requested). One design bug was caught and fixed during
self-implementation, surfaced by the FULL test suite rather than a separate review
pass:

- `run_adapters_probe`'s local variable `record = build_probe_record(probe)`
  SHADOWED the function's own `record: RecordPort` parameter of the identical name --
  the very next line's `record.write_redacted_atomic(...)` call then crashed with
  `AttributeError: 'dict' object has no attribute 'write_redacted_atomic'`, caught
  immediately by `test_adapters_cli.py`'s own new probe tests (8 of 13 failed on first
  run). Fixed by renaming the local to `probe_record`; `record` stays the injected
  port for the rest of the function.
- A second self-review gap: `MRS-ADP-016` (the malformed-existing-record WARN finding)
  was initially registered with `Severity.ERROR`, following an over-general reading of
  this codebase's own "severity is presentational, most existing UNEVALUABLE/ERROR-tier
  findings use `Severity.ERROR`" pattern -- but AD-39's own envelope-consistency
  invariant (`core/model.py::Envelope.__post_init__`) forbids an `Envelope` whose
  `status` is `ok` (which `Verdict.WARN` folds to) from carrying any `Severity.ERROR`
  finding. `test_probe_malformed_existing_record_degrades_to_empty_with_warn` caught
  this immediately (`ValueError: status 'ok' but at least one finding has severity
  'error'`); fixed by matching `MRS-ADP-009`/`MRS-ADP-011`'s own existing precedent
  (WARN-tier codes use `Severity.WARN`, never `Severity.ERROR`).

**Follow-up review recommendation: false** -- both fixes are narrow, test-driven
corrections to newly-added code (a variable-naming collision and a severity/tier
mismatch, both caught before this session's own verification run completed), not new
open design questions.

## Review Triage Log

### 2026-08-07 -- Review pass (Blind Hunter + Edge Case Hunter, parallel, no shared context, security-focused given the redaction/machine-scoped-write surface)
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 3, medium 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `high` `patch` (Blind Hunter) **Redaction bypass: field-name-based secret redaction never applied to `probe_output`.** The original implementation wrapped the WHOLE `bmad-loop probe-adapter --json` document as one opaque string value (`{"text": <document>}`) before calling `to_redacted` -- the field-NAME half of redaction (`is_secret_key`, e.g. any key ending `_TOKEN`/`_KEY`/`_SECRET`) only ever recurses into a real `Mapping`, so it never saw the document's actual keys, only a single giant string scanned by the five hardcoded token-shape regexes. A secret-shaped field (e.g. a literal `session_token` key) whose value did not happen to match one of those five shapes would have written to the machine-scoped `adapter-probes.json` in plaintext. Fixed: new `_redact_probe_output` parses `probe_result.stdout` first; a well-formed JSON `dict` (the contract `tests/meta/test_probe_json_contract.py` already proves this document IS) is redacted DIRECTLY via `to_redacted` (both halves: field-name AND shape), then re-serialized; anything that fails to parse falls back to the original opaque-string wrap rather than raising. New tests: `test_adapter_probe_output_redacts_secret_shaped_field_names_not_just_token_regexes`, `test_adapter_probe_output_falls_back_to_opaque_redaction_for_non_json_output`.
  - `high` `patch` (Blind Hunter) **Lost-update race on the shared `adapter-probes.json`.** `run_adapters_probe`'s read-merge-write (`existing[adapter_name] = probe_record`, then one write) had no lock -- two concurrent `marshal adapters probe` invocations for DIFFERENT adapters would each read the same starting state and whichever write landed last silently discarded the other's already-succeeded observation, no error, no finding. Fixed using the SAME injectable `FsPort.acquire_advisory_lock`/`release_advisory_lock` pair `cli/deploy.py::run_promote` already established (AD-42) -- never a second, raw `fcntl` mechanism (an initial raw-`fcntl` fix was tried first and reverted: it broke every `FakeFs`-based unit test by doing real OS-level I/O against fake in-memory paths regardless of the injected double, which is exactly the port-abstraction discipline this codebase's own architecture exists to preserve). New test: `test_probe_lock_contention_reports_error_finding_writes_nothing`.
  - `high` `patch` (Edge Case Hunter) **Already-merged Story 6.3 regression, surfaced by this story's own integration test run: `marshal preflight` failed at ERROR for the ordinary "adapter configured, never yet synced" case.** `gather_conformance_findings`'s unconditional wiring into `run_preflight` treats a tree that is desired but never previously projected (`STATUS_ADDED`) as real drift -- correct for the operator-invoked `marshal adapters conform` audit, but wrong for a routine preflight check running on every invocation, including immediately after `marshal init` before the operator has ever run `sync`. Verified live: `tests/integration/test_init_worktree.py::test_preflight_end_to_end_converges_seeds_and_acknowledges` (pre-existing, untouched by this diff) failed identically whether or not this story's own changes were stashed -- confirming the root cause is Story 6.3's own `cli/init.py` wiring, not anything new here. Fixed: new `treat_never_synced_as_drift: bool = True` parameter on `gather_conformance_findings` (default preserves `run_adapters_conform`'s existing strict behavior); `run_preflight` now passes `False`. `removed`/`modified` (a tree that WAS projected and no longer is, or now resolves elsewhere) are real drift either way and are never filtered. New unit test: `test_gather_conformance_findings_never_synced_is_not_drift_when_asked`. The integration test itself also needed a one-line fixture fix (seed a `.claude/skills` directory) to unmask and confirm the fix, since its own synthetic loop home is not a real git-worktree checkout and so never had the canonical tree Story 6.3's own `MRS-ADP-003` unconditionally checks for.
  - `medium` `patch` (Edge Case Hunter) **`AdapterProbe.probe_note`'s docstring overclaimed a "non-JSON output" degrade path that does not exist** -- corrected to describe the actual, deliberate "opaque, never validated or refused" contract (which the redaction fix above makes more precise, not less: a document is redacted fully when it parses, opaquely when it does not, but never rejected either way).

**Follow-up review recommendation: false** -- all four findings are isolated (the redaction gap to one capture-time function, the race to one write path, the preflight regression to one call-site parameter, the docstring to one paragraph), each covered by a dedicated new test proving the fix; no new design questions opened.

**Re-verification (2026-08-07, after all four patches):** `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` (the FULL suite, including `@pytest.mark.slow` integration tests, not just the fast default loop) -- **2910 passed**; `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 3 failed, all pre-existing accepted baseline (2 `pyforge-steward`, 1 `pyforge-doctor` `mcp` gap), unrelated; `lint-imports` -- AD-3/AD-4/AD-9 all KEPT (87 files, 484 dependencies).

</intent-contract>
