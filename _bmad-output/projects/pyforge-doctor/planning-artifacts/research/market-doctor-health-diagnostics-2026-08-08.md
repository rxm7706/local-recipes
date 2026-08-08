---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-doctor.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/retros/retro-doctor-2026-08-08.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/research/domain-preflight-health-diagnostics-tooling-research-2026-07-25.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/
research_type: 'market'
research_topic: 'Competitive/analogue landscape for ecosystem health & diagnostics CLIs (pyforge-doctor, post-ship)'
research_goals: 'Fill the missing market-research slot in Doctor''s planning set — now that all 16 stories shipped, map the real external tools Doctor''s three verbs compete with or borrow from, and the internal prior art (Warden, Atlas, Herald) it consolidates, so future Doctor scope decisions (v2, new axes, persistent surfaces) can be made against a named landscape instead of re-derived intuition.'
user_name: Rxm7706
date: '2026-08-08'
web_research_enabled: true
source_verification: true
scope_note: 'Doctor is an internal tool with no commercial positioning need — "market" here means the analogue landscape: which external tools solve each of Doctor''s three jobs, where an external tool could substitute for internal build, and where Doctor''s consolidation is genuinely differentiated. This is the first market-type report for Doctor (the 2026-07-25 set deliberately skipped it pre-build); it is written POST-ship, so every positioning claim is checked against what actually shipped, not what was planned.'
---

# Research Report: Market/Analogue Landscape — Doctor Health & Diagnostics CLI

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Market (analogue landscape — internal tool, post-ship)

---

## 0. Why this report exists now

Doctor's 2026-07-25 planning set contained domain and technical research but deliberately
no market report ("LIGHT scope by design — Doctor is an internal-facing developer tool").
That was the right call pre-build. Post-ship (16/16 stories, Epics 1–4 merged via PRs
#156/#162/#167/#290/#299/#303), the question inverts: Doctor now *exists*, and the next
scope decisions — new watch axes, a richer persistent surface, any `--fix` actuator —
should be made against a named external landscape. Three of Doctor's shipped surfaces
(`check`, `monitor --fleet`, `diagnose --prescribe`) each have a mature external analogue
category; this report maps each, states a build-vs-borrow verdict, and inventories the
internal prior art Doctor consolidated (which is itself Doctor's real "competition" — the
five CLIs an operator would otherwise run by hand).

## 1. Verb-by-verb competitive analogues

### 1.1 `doctor check` — the "doctor CLI" category

| Tool | What it checks | Relevant delta vs. Doctor |
|---|---|---|
| `brew doctor` | Homebrew install/env sanity | The namesake; read-only, nameable checks (`--list-checks`) — Doctor adopted both (checks/registry.py; read-only enforced by an AST meta-test since Story 1.1). |
| `flutter doctor` | Toolchain presence, tri-state ✅/⚠️/❌ | Doctor's `DoctorStatus` {OK, WARN, FAIL} (models.py) is the same tri-state, now shipped and load-bearing across all four epics. |
| `npm doctor` | Node/registry/cache/permissions, 5 named categories | Category-per-check taxonomy → Doctor's closed `Source` enum (8 members). |
| **`conda doctor`** (conda ≥23.5) | Env inconsistencies: missing files per package, altered packages; extensible via the `health_checks` plugin hook (`CondaHealthCheck`); newer versions add opt-in `conda doctor --fix` / `--fix <name>` with confirm/dry-run plumbing | The closest ecosystem-native analogue, and directly relevant since the factory IS a conda shop. Two takeaways: (a) conda's own doctor stays *environment-integrity* scoped — it does not cover engine availability, fleet staleness, or credential hygiene, so Doctor does not duplicate it; (b) conda doctor's `--fix` design (explicit opt-in, per-check, confirm-gated, dry-run-aware) is the reference shape if Doctor ever grows an actuator — it validates the PRD's "read-only by default, any fix is explicit opt-in" stance with a shipped in-ecosystem precedent. |
| `pip check` | Declared-dependency consistency of the installed env | Single-purpose, binary, no taxonomy — the "before" state Doctor's consolidation thesis argues against; Warden's deptry engine already covers this axis with more depth, and Doctor wraps Warden. |
| `datadog-agent health` vs. `datadog-agent status` / `diagnose` / `flare` | Agent self-health vs. richer status vs. connectivity vs. support bundle | Datadog's CLI splits "is the agent internally healthy" (health) from "what is it doing" (status) from "can it connect" (diagnose) — the same operability-vs-detail split Warden's `--doctor` exit-code contract drew ("doctor reports operability, not policy") and Doctor inherited wholesale. The `flare` support-bundle verb is a named gap Doctor has no equivalent of (see §4). |

**Verdict:** the check verb shipped squarely inside category conventions (read-only,
tri-state, nameable checks, operability-scoped exit codes). No external tool substitutes:
`conda doctor` and `pip check` cover env-integrity slices Doctor deliberately delegates
(to conda itself, and to Warden's deptry engine respectively); none covers Doctor's
one net-new check, credential/env hygiene (checks/env_hygiene.py — the `JFROG_API_KEY`
unconditional-injection class of finding).

### 1.2 `doctor monitor --fleet` — probes and pulse monitors

- **Kubernetes probes** are the strongest structural validation of the three-verb split:
  liveness ("restart if dead"), readiness ("route traffic only if ready"), startup
  ("don't judge until initialized") are three *distinct contracts with distinct
  consumers*, deliberately not one flag-parameterized probe. Doctor's `check` (readiness
  before Marshal spins the factory) / `monitor` (liveness of the fleet, continuous) /
  `diagnose` (targeted post-hoc) is the same consumer-driven split, and the shipped exit-code
  discipline (check answers "sound to start?", never "did a policy gate fail?") mirrors how a
  readiness probe must never encode application-level business failure.
- **Nagios / Icinga lineage**: the grandfather pattern for "N independent checks, each with
  its own tri-state (OK/WARNING/CRITICAL) and its own plugin, aggregated into one fleet
  board." Doctor's `Finding(source, check, status, message, evidence)` tuple is a
  Nagios-plugin-output structural descendant (with `evidence` replacing perfdata). The
  Nagios lesson Doctor already absorbed via architecture rather than pain: per-instrument
  degradation (one sub-instrument unreachable → its own FAIL finding, others keep running —
  `_gather_abandonment`'s partial-degrade contract in sources/atlas.py) instead of
  all-or-nothing.
- **healthchecks.io / dead-man's-switch monitors** invert the polarity: the monitored thing
  pings *in*, silence is the alarm. Doctor's `monitor --fleet` is pull-only, point-in-time —
  there is no scheduled invocation and no "monitor didn't run" alarm. If Doctor's weekly-pulse
  job ever goes unattended (Marshal-scheduled), a dead-man's-switch on the pulse itself is
  the missing piece; today a silently-not-running monitor is invisible. Named gap, not v1 debt.
- **Renovate Dependency Dashboard / Dependabot** (covered in depth in the 2026-07-25 domain
  report): per-repo surfaces that don't natively aggregate cross-repo. The prediction that
  cf_atlas gives Doctor the fleet-scale data model Renovate users hand-roll **held in
  practice**: `monitor --fleet` shipped with zero new data pipeline — four axes
  (staleness/cve/abandonment/adoption) all read existing atlas tools over MCP-or-CLI.

**Verdict:** no external monitor substitutes, because the differentiator is the data
source (cf_atlas) not the monitoring shape. The one borrowable idea not yet borrowed is
the dead-man's-switch on the pulse itself.

### 1.3 `doctor diagnose --prescribe` — triage and remediation ordering

- **Dependabot's CVSS+EPSS+KEV three-pillar triage** was the domain report's model for
  ranking, and the shipped `rank()` (prescribe.py: `_is_kev` / `_epss_score` /
  `_classify_blast_radius` → `_rank_factors_and_sort_key`) implements exactly severity ×
  exploitability × blast-radius with explainable `rank_factors` — no opaque score, per the
  report's "ordering must be explainable" requirement. This landed as designed.
- **OSV-Scanner guided remediation / Endor Labs upgrade-impact**: full transitive-resolver
  remediation. Doctor explicitly stopped short (FR-13 is single-hop: `recommend_safe_upgrade`
  returns a target *or* an explicit reason why not — `safe_upgrade_target`/`safe_upgrade_reason`
  always-paired in `Prescription`). If future demand pulls toward multi-hop resolution, the
  build-vs-borrow answer is *borrow*: OSV-Scanner's guided remediation exists, is
  conda-forge-consumable, and re-implementing a resolver was a named non-goal in both the
  Dream and PRD.
- **Partition-before-rank** (GitHub's snooze-until-patch, pip-audit's fixability filter)
  shipped as the `Partition` enum {ACTIONABLE, BLOCKED, ACCEPTED_RISK} with "every Finding
  lands somewhere." Post-ship market note: this design choice produced Doctor's one
  two-consumer shipped bug (a clean OK finding is classified ACTIONABLE by design, and both
  `rank()` and `_action_text` initially treated it as needing action — caught by the
  2026-08-07 batch adversarial pass, fixed in PR #299). External tools sidestep this by not
  emitting clean findings at all; Doctor's "report health, not just problems" stance is a
  real differentiator but carries this recurring edge-case cost (see the technical refresh).

## 2. Internal prior art — the real "incumbents" Doctor displaced

Doctor's actual competition was never external tools; it was the status quo of five hand-run
internal CLIs. Post-ship inventory of what it consolidated and on what terms:

| Incumbent | How Doctor consumes it | Substitution quality |
|---|---|---|
| Warden `--doctor` self-check | Library import of `run_doctor_checks` at the ONE sanctioned import site (sources/warden.py, AD-1, meta-test-enforced); degrades to a FAIL finding on any warden absence/breakage instead of crashing | Full wrap, no reimplementation — the cleanest consolidation in the package. Warden's CLI `--doctor` remains independently usable (correct facade behavior). |
| Atlas `staleness-report`, `cve-watcher`, `feedstock-health`, `release-cadence`, `adoption-stage`, `version-downloads` | MCP-first/CLI-fallback via one shared `_fetch_rows` seam (sources/atlas.py, AD-6); each row → one Source-tagged `Finding` | Full wrap for the monitor use-case; the raw CLIs remain the escape hatch for tool-specific flags Doctor doesn't surface (e.g. `staleness-report --by-epss`). |
| Herald's MCP transport | Pattern reuse (lazy import, one-session-per-call, injectable caller seam), swapped remote-HTTP+OAuth → local stdio | Precedent reuse, not code reuse — see technical refresh for whether that should be extracted. |
| Hand-reconciliation by operator | Replaced by one `DoctorReport` JSON envelope, one schema, `--json` on every verb | The core value delivered; PRD §1's "one habit" framing is now literally true. |

## 3. Build-vs-borrow verdicts (forward-looking)

1. **Actuator (`--fix`)** — if ever built, copy `conda doctor --fix`'s shape (per-check
   opt-in, confirm-gated, dry-run-aware), not a bulk auto-fix. Warden's `--open-fix-prs`
   is the in-house precedent for actuators living behind explicit flags.
2. **Multi-hop upgrade resolution** — borrow (OSV-Scanner guided remediation) rather than
   extend FR-13; the single-hop boundary was drawn deliberately twice (Dream + PRD).
3. **Support bundle** — a `doctor flare`-style "collect everything for a bug report" verb
   is cheap, matches the Datadog/`kubectl support-bundle` convention, and has no internal
   equivalent; candidate for a v1.x story if Doctor findings start getting escalated to
   humans who need reproduction context.
4. **Pulse dead-man's-switch** — do not build a scheduler into Doctor; Marshal owns
   scheduling. The healthchecks.io pattern belongs at the Marshal layer, consuming
   Doctor's exit code.
5. **New detection engines** — the Dream's "no new instruments without a matching decision"
   boundary held through v1 (env-hygiene was the only one) and every external analogue that
   tempts otherwise (Datadog integrations, Nagios plugins) is a data-source play Doctor
   should route through Atlas/Warden instead.

## Assumptions

- "Market" = analogue landscape for an internal tool; no TAM/pricing/competitor-share
  analysis is meaningful or attempted.
- External-tool facts rely on vendor docs and current web verification (conda doctor's
  plugin hook + `--fix`; Datadog agent CLI verb split); Kubernetes probe semantics and
  Nagios conventions are long-stable and cited from general documentation.
- Internal claims are checked against shipped code at
  `src/shared/packages/pyforge-doctor/src/pyforge/doctor/` and the 2026-08-08 retro, not
  planning documents.

## Open Questions

- Does the factory want a `doctor flare` support-bundle verb (§3.3), or is `--json` output
  plus the repo's session transcripts sufficient reproduction context in practice?
- When Marshal wires `doctor check` as an unattended pre-flight gate, does the pulse
  (`monitor --fleet`) also get scheduled — and if so, where does the "the pulse didn't run"
  alarm live (Marshal policy vs. an external dead-man's-switch)?
- The adoption axis is opt-in (never in `monitor --fleet`'s default `staleness,cve` set,
  by Story 4.3 design). Should real usage data ever promote it to the default set, that is
  a PRD-level default change, not a code tweak — track demand before touching it.

## Sources

External (verified 2026-08-08):
- [Conda doctor: Detecting conda environment inconsistencies easily — conda.org blog](https://conda.org/blog/2023-06-01-conda-doctor/)
- [Health Checks plugin hook — conda documentation](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/health_checks.html)
- [`conda doctor`: possible health checks — conda/conda#12753](https://github.com/conda/conda/issues/12753)
- [conda doctor subcommand API — conda documentation](https://docs.conda.io/projects/conda/en/stable/dev-guide/api/conda/plugins/subcommands/doctor/index.html)
- [Datadog Agent CLI commands and troubleshooting](https://www.devopsschool.com/blog/datadog-agent-troubleshooting-guide/)
- [Datadog Agent Cheatsheet (health vs. status vs. diagnose vs. flare)](https://drdroid.io/cheatsheets/datadog-agent)
- Kubernetes probe semantics (liveness/readiness/startup), Nagios plugin conventions,
  healthchecks.io dead-man's-switch model, Renovate/Dependabot/OSV-Scanner: see the
  2026-07-25 domain report's source list — re-validated as still-current framing, not
  re-fetched wholesale.

Internal:
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/retros/retro-doctor-2026-08-08.md`
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md`
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/{models,prescribe,score,fleet_surface}.py`,
  `sources/{warden,atlas}.py`, `checks/{env_hygiene,registry}.py`
- `docs/dreams/pyforge-doctor.md` (realized) and `docs/dreams/pyforge-doctor-dependency-health.md` (archived)
