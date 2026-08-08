# Market research — Marshal orchestration, 2026-08-08 refresh

> **Refreshes** `market-agent-orchestration-research-2026-07-31.md` (which
> refreshed the 2026-07-25 chain). That document remains valid history; this
> one re-grounds the competitive posture against what has *shipped since*
> — Epics 1–6 are now **50/50 done** (ledger:
> `planning-artifacts/sprint-status-ledger.yaml`; Epic 4 closed 2026-08-06
> PRs #266/#274–#282, Epic 5 closed 2026-08-07 PRs #283–#288, Epic 6 done
> 9/9) — and widens the analogue set per operator direction: workflow
> orchestrators (Airflow / Dagster / Temporal / Argo), developer-platform
> "one front door" products (Backstage / Port), CI gate mechanics (GitHub
> Actions / Argo Workflows), and the autonomous-agent vendors' own claims
> (Devin / Cursor / Copilot Coding Agent). Facts about Marshal are from the
> shipped tree (`src/shared/packages/pyforge-marshal/`), not from the PRD's
> aspirations.

## 1. What changed since 2026-07-31 (Marshal's side of the table)

The 07-31 doc's competitive row for Marshal read "Epic 1 shipped; supervisor
epics ahead." That row is now stale in Marshal's favor — every property the
"narrowed slot" claimed as *planned* is now *shipped and exercised*:

| Slot property (07-31 claim) | 08-08 shipped evidence |
|---|---|
| Spec as executable contract | Epic 2 done 7/7: standalone verify runner (2.1), never-false-green verdict aggregation (2.2), **frozen-surface scope check, narrowing-only** (2.3), gate-mode ladder with autonomy labels (2.5), spec-binding gate → the FR-64 fidelity slice (`core/spec_binding.py`, `core/spec_surface.py`) |
| Supervisor outside the session | Epic 3 done 8/8: `supervisor/` sidecar with `durability.py` + `__main__.py` — a separate process, not an in-session hook |
| Never-false-green verdict lattice | `core/verdict.py` + `core/gate.py`, meta-tested since Story 1.1 |
| Paper trail survives teardown | Epic 4 done 10/10: `marshal land`, `marshal deploy promote`, journal-first landing (`core/landing.py`, `core/journal.py`, `core/promotion.py`); a real promote/reconcile run closed Epic 5 and *caught its own Story 5.1 spec falling through promotion* (squash-merge blind spot — the tool detected its own paper-trail gap live) |
| Fleet visibility (CAP-5, "Conductor overlap") | Epic 5 done 6/6: `marshal status` (per-home rows, `--run` drill-down, `--escalations`, `--reconcile-ledger` with confirmed/unconfirmed tagging, unpushed-work fold-in), `marshal check` routing the detector registry |
| Portability proven, not claimed (CAP-6) | Epic 6 done 9/9: profile-driven adapter selection, skill-tree projection + drift detection, adapter probe, conformance smoke in an ephemeral home, conformance matrix, entry-file family drift check, upstream-contribution register, tool-surface rendering |

The honest caveat cuts the other way now: the *frontier* rows (Epics 7–12,
the absorbed genesis-installer scope — 36 stories: 35 `backlog`, 8-5
`blocked` on forward-dep S-10.2) are a **different market** — repo
templating/scaffolding (Copier, cruft, cookiecutter, Backstage Software
Templates), not agent orchestration. Section 5 treats it separately.

## 2. Workflow-orchestrator analogues — Airflow, Dagster, Temporal, Argo

Operator ask: how does "deterministic dev-loop orchestration with graduated
gates" compare to the systems that made "deterministic orchestration" a
product category? The comparison is instructive precisely because Marshal is
*not* one of them.

| Property | Airflow | Dagster | Temporal | Argo Workflows | **Marshal** |
|---|---|---|---|---|---|
| Unit of work | task in a DAG | software-defined asset | workflow function (code) | container step | **story under a spec contract** |
| Determinism claim | scheduling determinism | asset lineage/reproducibility | **durable execution: replayable event history** | idempotent steps via retries | deterministic *harness*: no LLM in gate evaluation, byte-stable verdicts |
| Human gate | sensor / manual trigger; Airflow 2.x has no first-class approval | asset checks + branching | `await signal` — first-class human-in-the-loop | `suspend` template + `argo resume` | **gate-mode ladder with autonomy labels** (Story 2.5) + CRITICAL escalation → `bmad-loop-resolve` |
| Survives process death | scheduler restart re-queues | run worker restart | **yes — core product promise** (event-sourced) | k8s controller reschedules | supervisor + journal-first + stage-boundary push (FR-61); *bounded loss*, not zero loss |
| Paper trail | task logs, metadata DB | run/materialization history | full event history | archived workflows | append-only journal + promoted specs + `--reconcile-ledger` against git itself |
| Worker trust model | workers trusted | trusted | trusted | trusted | **worker is an LLM and explicitly untrusted** — the entire design premise |

Three transferable findings:

1. **Temporal's "durable execution" is the strongest external vocabulary for
   FR-61/62/63.** Marshal's durability model (journal-before-the-act,
   promotion-before-teardown, unpushed-work-check) is a *bounded-loss*
   version of what Temporal makes *zero-loss* via event sourcing. If a future
   epic ever needs stronger durability, the Temporal pattern — every state
   transition recorded before the side effect, replay from history — is the
   canonical design, and `core/journal.py` is already append-only, i.e.
   halfway there. Not a recommendation to *adopt* Temporal (a server + DB is
   exactly the infrastructure the zero-server constraint forbids — see
   `technical-pyforge-unification-2026-08-08.md` § 2); a recommendation to
   keep stealing its event-sourcing discipline.
2. **Dagster's asset model rhymes with the Dream-to-Code chain.** A Dagster
   asset declares its upstream deps and the system knows what is stale;
   `dream_chain_check.py` + `bmad-drift-check` + `spec_surface.py` do the
   same for planning artifacts by hand-rolled detector. Atlas already runs
   Dagster (via the Kedro migration) for *data*; the fleet-chain-completeness
   frontier ("regenerate the whole chain from a consolidated Dream") is
   literally an asset-materialization graph over markdown. This is the one
   genuine "should another station adopt Atlas's stack?" candidate — argued
   in the unification doc § 6.
3. **None of the four has an answer for an untrusted worker.** Every
   orchestrator above assumes the task code does what it says. Marshal's
   distinguishing constraint — the worker is a language model that can
   hallucinate success — is why the verdict lattice and the outside-the-
   session supervisor exist. The 07-31 "narrowed slot" survives contact with
   the workflow-orchestrator market untouched: they are complements (and
   design donors), not competitors.

## 3. "One front door" analogues — Backstage, Port

The one-front-door Dream (archived-absorbed → FR-65 `marshal check`; shipped
Story 5.6) and Herald's Pages console overlap the Internal Developer Portal
category:

- **Backstage** (Spotify/CNCF): software catalog + scorecards + **Software
  Templates** (its scaffolder is cookiecutter-descended — the direct analogue
  of Epics 7–12's Copier-based managed-region engine, see
  `domain-research-scaffolder-landscape.md` in this folder, which surveyed
  exactly this before the installer chain existed). Cost profile: a Node
  monorepo app you *operate* — the canonical "with infrastructure" tax.
- **Port**: SaaS IDP — blueprint data model, self-service actions,
  scorecards. Closest conceptual match to the Guildhall's roster + gap
  detection, but SaaS-hosted and schema-first.

Where Marshal + Herald sit: the factory already has a working IDP *shape*
with zero servers — `docs/dashboard/generate.py` derives catalog rows from
tracked ledgers and Dream frontmatter, GitHub Pages hosts it, `marshal
status`/`marshal check` are the CLI front door. What Backstage/Port have that
the factory lacks: **write actions from the UI** (self-service "run this"),
live/refresh-on-event data (the dashboard goes stale — the
`sprint-status-auto-promote` Dream documents three same-session incidents),
and per-entity drill-through (named as `spec-factory-console`'s unbuilt
frontier). Verdict: adopt the *patterns* (scorecards ≈ detector registry
rendered per-station; drill-through), not the platforms — a Backstage
deployment would invert the zero-infrastructure property that makes the
factory portable. Full argument: unification doc § 4.

## 4. Gate/approval mechanics — GitHub Actions, Argo, and the agent vendors

- **GitHub Actions environments + required reviewers** is the mainstream
  "graduated gate": deployment can't proceed until a named human approves.
  Marshal's ladder is finer-grained (per-story `mode:` autonomy labels,
  doc-only classification lowering the gate for prose-only changes — Story
  2.4) and, critically, *local*: no Actions minutes, works offline. But GH's
  version is enforced server-side where no local process can bypass it;
  Marshal's landing gate (`marshal land`) is enforced only where Marshal
  runs. The repo's own inherited linter (maintenance label, env-sync) is the
  only server-side gate today — a real asymmetry worth naming in any
  "with-infrastructure mode" design.
- **Self-hosted Actions runners** are the closest external analogue to loop
  homes: registered, isolated executors pulling work. Differences: runner
  lifecycle is server-orchestrated; loop homes are locally provisioned
  worktrees (`marshal init`, isolation verification Story 1.6) with the
  queue being sprint-status.yaml. A container image of a loop home (unification
  doc § 2) would make the two models nearly interchangeable.
- **Devin** ($500+/mo tier now broadened): still sandbox-not-supervisor; its
  2026 marketing leans on "Devin reviews Devin" — self-report, exactly what
  NFR-4 forbids. **Cursor** background agents: in-IDE, attended-biased, no
  contract layer. **Copilot Coding Agent**: PR-native, gates = code review;
  GitHub's `copilot --acp` public preview (per the 07-25 domain research)
  remains the sanctioned drive-the-agent path and is now *load-bearing* for
  Marshal's Epic 6 adapter story rather than speculative. None of the three
  publishes anything like a verdict lattice or an external supervisor;
  the 07-31 four-property slot **holds on re-check, now with shipped
  evidence rather than PRD citations**.

## 5. The second market Marshal just walked into — scaffolding/templating

Epics 7–12 (extraction manifest, marker/region substitution, findings
scanner, materialize verbs, migrate/update, packaging) compete with a
*different* shelf: **Copier** (which the architecture already commits to
wrapping — S-7.6 spike, S-10.1 single seam), **cruft**, **cookiecutter**,
**Backstage Software Templates**, **Nx/Turborepo generators**, and — the
undated legacy doc in this folder, `domain-research-scaffolder-landscape.md`,
surveyed this shelf and still reads correct on the fundamentals. What none of
the shelf has: **managed regions inside brownfield files** with a sanctioned
opt-out (S-8.5's marker-deletion contract), a never-write guard with a
findings taxonomy, and adoption of an *operating model* (BMAD tiers) rather
than a file tree. That is a genuine gap; it is also 35 unstarted stories of a
product with different users (repo adopters) than Epics 1–6's (the operator
running fleets). The market evidence supports the
`genesis-installer-name-retirement` Dream's instinct that this needs one
coherent design pass, not a renumbering — two CLIs' worth of scope now live
under one binary name.

## 6. Verdict for the PRD/positioning

1. Replace every remaining "planned/ahead" hedge in outward material — the
   four slot properties are shipped; cite PR ranges (#266–#288) and the
   Epic-5 live self-catch as evidence, not benchmarks.
2. Add rows for Temporal-style durable execution and Backstage/Port to the
   competitive analysis **as pattern donors** with an explicit "not adopted
   because zero-infrastructure is the moat" line.
3. Watch items carried forward unchanged from 07-31: BMAD-METHOD roadmap
   "Dev Loop Automation" (convergence, not fork trigger); ACP registry
   breadth (Q-6 triggers still unfired as of last verification); bmad-loop
   pin `>=0.9.0,<0.10` (re-verify at next chain touch — last confirmed
   current 2026-07-31/08-01).
4. New watch item: the Epics 7–12 scaffolder market moves fast (Backstage
   templates, `copier` releases); re-run the scaffolder-landscape survey
   (currently undated legacy) before S-7.6's Copier fit spike executes.
