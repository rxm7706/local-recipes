---
title: "Technical research — the PyForge station dossier"
chain: "pyforge-unifying-strategy"
type: "technical"
created: "2026-08-30"
updated: "2026-09-01"
status: "ready"
decision: "What does every PyForge station actually do, and where do their conventions agree or diverge — evidence now lives on pyforge-unifying-strategy § Fleet conventions; this dossier is the living map for any operator working across more than one station"
---

# Technical research — the PyForge station dossier

A full-source investigation of all eight PyForge stations (`atlas`, `doctor`, `herald`,
`marshal`, `mason`, `scribe`, `steward`, `warden`) plus the shared `pyforge-core` foundation
they build on. Run 2026-08-30 as seven parallel, independent source investigations (one fork
per station, `marshal` investigated separately in an earlier pass the same session), each
citing file:line for every claim and flagging anything it could not verify rather than
inferring it. A rendered companion artifact (interactive HTML) was published the same session;
this file is the durable, git-tracked record of its findings, kept current by the refresh
procedure at the bottom.

## 0. The shared spine

Every station sits on `pyforge-core`, a deliberately pure-stdlib leaf that depends on none of
them. It does no station's job — it owns the mechanisms every station kept reinventing
separately, until seven of them were consolidated into one place each (the realization of
[[pyforge-core]], the Dream this research's own methodology descends from).

**One CLI, discovered at runtime.** `pyforge <station> <command>` is a single console script
(`pyforge.core.dispatch:main`) that does no station work itself — it maps a station token to
that station's own primary console script and forwards argv to it as a subprocess. The map is
built by walking installed package metadata first, falling back to scanning sibling
`pyproject.toml` files when running from an editable checkout. `pyforge-core` and
`pyforge-testing-kit` are excluded from the station map. Atlas is the one station flagged as a
known exception to a separate CLI-AST-introspection check, tracked against a named waiver spec
under Steward's own planning artifacts.

**Seven mechanisms, formerly seven copies:**

| Module | What it replaced |
|---|---|
| `core.verdict.Lattice` | Warden, Marshal, and Doctor each hand-rolled their own rank/exit-domain dict comprehension; Herald hand-rolled an `isinstance` dispatch loop. Confirmed imported by all four. |
| `core.atomic_write` | Twenty hand-written tmp-file-then-`os.replace` copies across six stations (Herald 6, Atlas 5, Marshal 3, Steward 2, Scribe 1, Warden 3), three different naming conventions, none sharing code. |
| `core.hooks` | The one plugin-registration surface, one entry-point group (`pyforge.core.hooks`), stdlib `importlib.metadata` only. A plugin may only `publish_verdict` for the spec it owns — a second attempt raises `SecondVerdictError`. |
| `core.errors.PyforgeError` | Every station's own exception root re-parents onto this bare marker (Herald's `HeraldError`, Mason's `CfeUnresolvedError`) without touching any subclass's own constructor. |
| `core.process` | Moved **verbatim** from Marshal's own `ports/process.py` + `adapters/process_posix.py` — Marshal's own subprocess abstraction became the fleet's shared primitive. |
| `core.report` | Shared report-envelope schema data plus a pure dict-merge; each station keeps its own `jsonschema.validate` call site. |
| `core.landing_evidence` | Every consumer asking "did story X land on main" — Doctor's `story-status`, Marshal's `merged_story_keys`/`retire` — now shares one grammar. |

Also present: `core.assertion` (a host-mint RS256 signing client — the CLI never signs
locally), and `pyforge-testing-kit`, a deliberately *separate* leaf from `pyforge-core` so test
fixtures never couple into every station's runtime install.

## 1. Atlas — the intelligence layer

*"Atlas provides data… Warden uses that data… the only code edge between them points the
other way."* — the package's own README.

**24,184 lines, 119 files** — the largest station. `requires-python >= 3.14`, the fleet's
highest floor. A genuine Kedro project: `pyforge-atlas <command>` is, under a thin `--version`
intercept, Kedro's own CLI routing — there is no Atlas-specific command tree. The real
Atlas-specific surface is 13 MCP tools: 8 pipeline triggers (`core`, `vcs_health`,
`pypi_intelligence`, `vulnerability`, `seed_gaps`, `universal_sbom`, `derived_artifacts`,
`upstream_discovery`), dataset read/list, and two natural-language query tools.

`read_dataset` never hands back raw data — every result carries a provenance envelope
recording when the underlying data was actually built (never a read-time clock stand-in).
MCP tool bodies are AST-scan-enforced to contain zero business logic.

**The load-bearing finding**: the legacy SQLite system (`cf_atlas.db`) is **still running, in
parallel, right now**, by binding design decision, not oversight. The rewrite is code-complete
(46 stories, 8 live pipelines), but a documented rule states the legacy orchestrator keeps
running until a credentialed, human-signed parity event proves exact row/value parity — and
the code's own retirement-eligibility check currently, correctly, returns `allowed=False`.
Parts of Atlas's own dashboard still read `cf_atlas.db` directly today.

A "Boring Semantic Layer" (BSL) is the single metric-translation interface over the canonical
Parquet store, Ibis-to-DuckDB. Two dashboard code paths coexist: a pure-Kedro Vizro package and
a separate legacy-bridge layer rendering Bokeh fragments from the old CLI scripts.

Relationships: → Warden (the one optional code import, one-directional); → Mason (a named
"downstream handoff" from the trending-candidates engine, not independently confirmed from
Mason's side); → conda-forge-expert (a dedicated agent-to-agent bridge module); → `pyforge-core`
(heavy, 15 confirmed import sites).

## 2. Doctor — advisory diagnostics, and the one station that judges Marshal

*"Charter §6, ratified 2026-07-28: the Doctor holds the verdict on the Marshal's own
conformance — the one station that would otherwise grade itself. The Marshal may not weaken,
re-threshold, or disable a check that judges the Marshal."*

**16,830 lines, ~26 files.** Four commands: `check` (pre-flight), `monitor --fleet` (cf_atlas
Watch axes — staleness and CVE by default), `diagnose --target`, `backlog-intake`. A finding is
one of a closed three-state `OK/WARN/FAIL`. The exit domain `{0, 2, 130}` is a documented,
tested subset of Warden's `{0, 1, 2, 130}` — Doctor reports operability, never policy.

Six of Doctor's own modules exist specifically to judge Marshal's output — dashboard
truthfulness, the Dream-to-Code chain, forward-dependency blindness in the story picker,
project-doc currency, the tracked sprint ledger's regression-freedom, Marshal's own durability
record. The largest, `sources/chain.py`, is 4,435 lines on its own. Verified structurally: the
module judging Marshal's durability does not import `pyforge.marshal` at all — only git history
and journals. Marshal has no code-level lever over its own verdict.

27 distinct finding sources, each tagged with a *subject* station and an *owning* station — the
mechanism making the Marshal-oversight rule machine-checked, not aspirational.

Relationships: → Warden (the one real code dependency, optional extra); ← Marshal (judged, not
judging); → Atlas (read-only external signal source).

Doc-drift found: the README claims "28 stories shipped" while the code cites story numbers
well past that.

## 3. Herald — the Dream-to-deck bridge, and the fleet's comms desk

*"Dream-to-deck bridge CLI — seeds, pulls, and syncs Claude Design decks via the herald deck
subcommands."*

**13,271 lines, 24 files.** 47 stories / 12 epics shipped. Five top-level commands: `deck`
(seed/pull/status/watch/push/qa/pptx-spec/pptx-fill) and "the Four Moments" — `progress`,
`success`, `notice`, `scheduler`. The deck bridge core is transport-agnostic by construction: an
AST-walking test enforces that no composed deck operation can import a concrete transport
adapter, an LLM SDK, or dynamic-import machinery. Two export pipelines coexist deliberately:
the original Marp/HTML path (non-editable `.pptx` output) and a purpose-built pipeline using
python-pptx's real object model.

`progress`/`success`/`notice` consolidated onto one shared SQLite file; the deck bridge's own
state deliberately stayed separate. Every write handler passes through one auth gate that is
explicitly a stub today — no real credential verification, flagged as an open assumption in its
own docstring.

**A correction, not a confirmation**: Herald's own source contains **no MCP server code at
all** — zero `FastMCP`/server decorators anywhere. It's an MCP *client* (calls out to Claude
Design), not a server. See §9 — this turns out to be correct behavior per an existing
architecture ruling, not a gap.

Relationships: explicit non-dependency on Steward for secrets (Steward's key module is
provisioning-shaped, not a runtime secret-fetch accessor); explicit refusal to let a deck
export be mistaken for a Warden verdict (`SecondVerdictError` on a second attempt); ships its
own React/Vite dashboard listing all 8 stations.

## 4. Marshal — deterministic BMAD-loop supervisor

*"Deterministic BMAD-loop supervisor: wraps bmad-loop with gates-as-objects, run supervision,
landing, fleet status, and adapter portability."* — the package's own `pyproject.toml`.

Two independent, alternative dispatch engines, neither wrapping the other. **bmad-loop** is a
real, separate binary with its own review/retry/landing machinery; Marshal renders its policy
file whole every time (gitignored, never hand-edited), launches/attaches/resumes it, and reads
its journals. **bmad-build-auto** is not a binary — a workflow prompt handed to a directly
launched coding-agent CLI session (Claude/Cursor/Copilot/Gemini/Devin, policy-ordered, each
candidate live-authchecked after a real 2026-08-27 incident where three dispatches died
silently on an auth wall a presence-probe couldn't see). Marshal built six dedicated,
side-effect-free modules to supervise this second engine, because it ships none of its own.

A six-rung verdict lattice (`ERROR`→`CLEAN`, exit codes 4→0) plus `EXIT_USAGE=2` and
`EXIT_SIGINT=130`. A four-layer policy fold (code default → repo defaults → project layer →
invocation flags, last wins) governs a closed 29-key vocabulary. Landing rules are drawn
straight from this repo's own `CLAUDE.md` PR gates.

`marshal seed` (Genesis) is the installer, not the runtime — six verbs (init/adopt/check/
update/explain/version), five ownership classes per managed file.

~40 CLI commands across 12 verb groups; the installed skill file documents 4 of them.
`bmad-loop >=0.11.0,<0.12` is the one real BMAD package dependency; no `bmad-method` dependency
exists anywhere in the package.

## 5. Mason — the Artisan Builder, a CLI front door onto conda-forge-expert

*"…wrap the conda-forge-expert craft by subprocess rather than reimplement it — the skill
stays canonical… It is never forked."* — the package's own README.

**9,052 source lines, 24,783 test lines (2.7×, the heaviest ratio in the fleet).** No dedicated
content skill — by policy, not gap: the persona skill explicitly forbids creating one. `mason
recipe`'s eight verbs are 1:1 thin subprocess wrappers over ten named conda-forge-expert script
adapters — literally the CFE skill's own MCP surface, re-projected as a CLI. `package`
(build/ship) and `environment` (lock/check) are genuinely CFE-independent.

Capability tiering is enforced by AST meta-test: `doctor.py`/`package.py`/`environment.py` must
import cleanly with zero CFE installed; `recipe.py` is the only module allowed `import cfe` at
module scope. `engines/twine.py` never passes `env=` to its subprocess call — publish
credentials reach twine only through natural process-environment inheritance, structurally
tested.

Already dogfoods itself: a wheel/sdist and a `.conda` artifact for Mason both exist, built with
its own `package build`.

Two modules cite Steward story numbers and a Steward-owned concept ("Lane 1 media," an
install-class registry pattern) directly inside Mason's own code — unresolved, flagged rather
than explained away.

## 6. Scribe — the append-only write path for checked-in team memory

*"Direct-capture CLI for checked-in team memory (.claude/memory/) — the append-only write path
for team-relevant decisions, ADRs, and project state."*

**3,279 lines — the smallest station.** Three commands: `capture` (direct / `--promote` /
`--transcripts`), `graph compile [--nightly]`, `recall QUERY [--semantic]`. A strict three-layer
pipeline: capture (write-only, append-only) → compile (a full, non-incremental rebuild every
run, from six surfaces including local `git log`, read-only, never fetch) → recall (reads the
compiled result only). Node identity is derived deterministically, so unchanged-source compiles
are byte-identical.

Despite the name, the compiled "graph" has no separate edge object — nodes are flat facts. A
bi-temporal-lite supersession mechanism marks a superseded record ended, never deletes it.
`recall` is deliberately dumb by default: pure lexical token-overlap scoring, no LLM, no
network — every ranked candidate is filtered by resolvable citation *before* return. An
unresolvable query gets an explicit "no grounded answer," never a fabricated one.

**A genuine cross-station wiring, confirmed in code**: Scribe's storage layer is swappable by
an "owner" string through the shared plugin registry, and the two non-default backends are
attributed in Scribe's own comments to *other* stations — a Postgres+pgvector backend is
Steward's to maintain; a third reads and writes `atlas.duckdb` directly, Atlas's own database
file.

**Doc-drift found**: the README's status line says all 9 stories/2 epics are shipped and
`compile`/`recall` are fully implemented; the paragraph directly beneath it still says those
same two commands print a "not yet implemented" notice and exit 0 — a leftover pre-Epic-2
fragment. Source code confirms the header is right and the body is stale.

## 7. Steward — the Provisioner, credentials, deployment, platform

*"A result is evidence, not a scratchpad."* — `DutyResult`'s own docstring.

**15,756 source lines, 19,429 test lines.** Thirteen "duties" (`keys`, `deploy`, `provision`,
`budget`, `sync`, `workspace`, `upgrade`, `suite`, plus a five-command bootstrap group); the
README documents 6. Every duty's result is a frozen dataclass; no duty may ever call
`sys.exit` — the CLI dispatcher catches every way a duty can end and projects it to a
documented code, so an unexpected crash lands on **70** (literally BSD's `sysexits.h`
`EX_SOFTWARE`), deliberately distinct from `1` ("a duty ran and legitimately reported
failure").

**A correction to the parent framing**: there is no literal CMS anywhere in Steward's source.
What it actually owns is **Lane 1 `/console/`** — an operator dashboard, successor to this
repo's own retired GuildHall Pages console. It performs zero status derivation of its own: a
precondition guard refuses to publish the dashboard when Marshal's tracked sprint ledger is
missing/stale/unreadable, and separately wraps Doctor's own fleet-scan output.

Relationships: ← Marshal (console precondition source); ← Doctor (second consumed status
source, via fleet-scan); → Scribe (maintains two of its three storage backends). No direct
Herald coupling found in Steward's own source.

## 8. Warden — the compliance gate, dependency hygiene, licenses, CVEs

*"Unified dependency-hygiene + vulnerability scanner… emitting one schema-validated
ComplianceReport and acting as a strict CI/CD exit-code gate."*

**17,767 lines, 31 files.** Unlike every other station, the CLI is essentially one subcommand
(`scan`, ~20 flags) plus `--doctor` as a flag, not a subcommand — read-only local checks only,
never network, can never exit `1` ("reports operability, not policy," the same phrase Doctor's
own gotcha uses independently). A seven-rung `Status` lattice — the fleet's largest — built on
the same shared `pyforge.core.verdict.Lattice` Marshal and Doctor also import, confirmed
directly against `pyforge-core`'s own source, including in Marshal's own file even though
Marshal's own investigation this session didn't surface that import.

Four real compliance axes (hygiene/deptry, vulnerabilities/osv-scanner+KEV+EPSS, license,
currency) run in parallel worker threads but apply results back in fixed registration order,
keeping the verdict deterministic regardless of thread completion order. Four commercial-scanner
stubs (Checkmarx, SonarQube, Black Duck, GHAS) are registered through the same shared plugin
mechanism — a default scan stays green with all four absent, by design.

A fix-PR actuator is the one module permitted forge-API network egress — strictly opt-in,
strictly post-verdict, closed to two remediation shapes only. Fully offline at scan time
otherwise. Manifest support reaches Python, Conda (incl. legacy `meta.yaml` v0), Pixi, and
conda-forge's own `recipe.yaml` v1 directly.

Tags its own decisions differently from the rest of the fleet: Story numbers, FR/NFR codes,
single-letter design codes (`D2`, `D12`) — no `AD-N` found anywhere.

## 9. Cross-fleet synthesis

**Who judges whom.** Doctor → Marshal is a binding governance ruling, structurally enforced
(the judging code never imports Marshal's package). Warden → Doctor and → Atlas are
one-directional optional dependencies. Steward's console reads Marshal's and Doctor's output
rather than computing its own. Herald explicitly refuses to let an export be mistaken for a
Warden verdict, and explicitly documents a non-dependency on Steward for secrets.

**The shared spine, confirmed four times over.** The verdict-lattice consolidation claim in
`pyforge-core`'s own docstring — that Warden, Marshal, and Doctor each used to hand-roll this,
and Herald hand-rolled something structurally similar — was independently confirmed from every
one of those four stations' own source, not just asserted once and trusted. The shared
plugin-hook group is used by Marshal, Doctor, Atlas, Mason, Steward, Scribe, and Warden — none
maintains a station-specific alternative.

**A systemic documentation-drift pattern.** Marshal's installed skill documents 4 of ~40 real
commands. Doctor's README claims 28 shipped stories against code citing higher numbers.
Steward's README documents 6 of its 13 real duties. Scribe's README contradicts itself in
adjacent paragraphs. Same failure mode recurring at every station that ships fast: the README
is written once, near a milestone, and never revisited as the surface keeps growing underneath
it.

**No repo-wide decision-tagging standard.** Marshal, Mason, Atlas, and part of Steward tag
`AD-N` at wildly different registry sizes with no shared numbering; Scribe keeps a small,
contained `AD-N` set; Warden and the rest of Steward use Story/FR/NFR/D-codes instead.

**MCP-server placement — reconciled, not open.** [[pyforge-unifying-strategy]] already rules
that MCP and portal compute mount on the shared host ASGI (`POST /stations/<name>/mcp`), not
per station — "not a deferred microservice program." Read against that ruling: Herald's and
Scribe's complete absence of MCP server code is *correct*. Atlas's own standalone MCP server
module is the actual candidate for reconciliation.

**Scale, side by side:**

| Station | Source lines | Files | Shape |
|---|---|---|---|
| Atlas | 24,184 | 119 | Largest — a real Kedro project plus 11 pipeline packages |
| Warden | 17,767 | 31 | Densest per-file — one CLI verb, four real engines |
| Doctor | 16,830 | ~26 | Dominated by one 4,435-line Marshal-oversight module |
| Steward | 15,756 | ~20 | 13 duties; heaviest tested among the "real" stations (1.2:1) |
| Herald | 13,271 | 24 | Deck bridge core + Four Moments + own dashboard |
| Mason | 9,052 | 18 | Heaviest test ratio of all (2.7:1) |
| Scribe | 3,279 | 13 | Smallest — capture/compile/recall, nothing more |
| pyforge-core | — | 9 | The leaf every one of the above builds on |

## 10. What's verified, what isn't

No investigation fully read every module in its station — each prioritized the CLI surface,
the core domain model, and cross-station coupling, and named what it left unread rather than
inferring its contents. Design-decision registries were only partially glossed everywhere.
Several cross-station claims (Atlas→Mason's trending handoff, whether Atlas's dashboard reads
the same BMAD status source Marshal and Steward do) were named from one side only and not
independently confirmed from the other.

## Refresh procedure

**This is a snapshot, not a maintained reference — that distinction is the point.** Four of the
findings above exist specifically because a station's own docs went stale between milestones;
publishing this file once and never re-running it would make it a fifth. This section is the
repeatable method, not a promise that it runs itself: the substantive work — reading source,
judging what a docstring actually means, reconciling one station's claim against another's — is
LLM-driven synthesis, not a deterministic script. What's repeatable is the *procedure*, the same
way the `conda-forge-expert` skill's own quarterly audit (`.claude/skills/conda-forge-expert/automation/`)
is a versioned prompt run on demand, not a cron job that writes findings unsupervised.

**Method:**

1. **Enumerate stations live, never hardcode the roster.**
   `ls -d src/shared/packages/pyforge-*` minus `pyforge-core` and `pyforge-testing-kit` is the
   current fleet. This is deliberate — a ninth station added later is picked up automatically
   by the procedure, not missed because a list in this file wasn't updated.

2. **One parallel fork per station**, each given a tailored prompt asking it to:
   - Read `pyproject.toml` in full (identity, version, entry points, dependencies, especially
     any `pyforge.core.hooks` registrations and any cross-station optional extras).
   - Enumerate the full CLI command tree from the actual argparse/CLI front door — not from
     the README or skill index, which this investigation found undercounts the real surface at
     every station that has one.
   - Identify the 2-4 central domain concepts / key types / architectural seams (a
     `ports/`+`adapters/` Protocol split, an AST-enforced purity boundary, a plugin registry —
     whatever the station's own code actually uses).
   - Collect design-decision tags (`AD-N`, `Story N.M`, `FR-N`, single-letter codes —
     whichever convention that station uses) with a one-line gloss each, sourced from
     docstrings actually read.
   - Read the README in full and note the gap, if any, between what it claims and what the
     code's own story/epic citations support.
   - Name every cross-station relationship found (imports, explicit non-dependencies,
     docstring-cited coupling to another station's concepts) — these are what make the
     cross-fleet synthesis possible, and they're usually stated explicitly in a docstring
     somewhere if you're looking for them.
   - Report file:line citations for every claim, and explicitly flag what wasn't read rather
     than inferring it.

3. **Synthesize**, reusing this file's own section shape (§1–§8 one per station, §9 the
   cross-fleet synthesis, §10 the honesty ledger) so a diff against the previous version is
   legible. The cross-fleet synthesis is where the real value sits — it only exists because all
   eight were read in the same pass; re-run it fresh each time rather than patching individual
   station sections in isolation, since a fix in one station can invalidate a claim made about
   it from another station's side.

4. **Republish** the companion HTML artifact (redeploy to the same URL rather than minting a
   new one) and update this file's `updated:` frontmatter field and this section's own "last
   run" line below.

5. **Feed findings back to [[pyforge-unifying-strategy]] § Fleet conventions**
   if a refresh surfaces a new convention gap, or clears an existing one — that
   section's table should track this file's findings, not diverge from them.

**Cost, measured, not estimated.** The 2026-08-30 run's seven station forks (Marshal was
investigated separately, in an earlier pass the same session, and its token cost wasn't
captured in this figure) consumed **4,792,579 tokens** combined — Herald 683,590 · Doctor
677,272 · Mason 682,433 · Atlas 686,341 · Steward 672,411 · Warden 693,295 · Scribe 697,237.
This is a genuinely expensive procedure per run, not a background job to schedule casually.

**Cadence: on-demand, not scheduled.** Given the measured cost above, this should not run on a
fixed timer the way `conda-forge-expert`'s quarterly upstream audit does — the value here comes
from a human deciding a refresh is worth the token spend (a new station shipped, a major
architecture ruling landed in [[pyforge-unifying-strategy]], or enough time has passed that the
doc-drift findings above are themselves suspected stale), not from a clock. Trigger it
deliberately.

**Last run**: 2026-08-30 (this file).
