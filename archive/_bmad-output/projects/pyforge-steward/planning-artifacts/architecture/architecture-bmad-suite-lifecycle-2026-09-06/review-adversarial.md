---
review: adversarial
target: ARCHITECTURE-SPINE.md (bmad-suite lifecycle, epic altitude, status final — post currency-lens edits of 2026-09-06T11:28)
lens: "construct two units one level down that each obey every AD to the letter yet still build incompatibly"
reviewed: 2026-09-06
against: HEAD 35ddefbbc5 plus the same-session working tree — the epic mint (steward 46/47 + 14.9, marshal 30.5/31.x, doctor 20.x, warden 11.x, herald 18.x, scribe 7.1, atlas 24.1, mason 14.1; unstaged) and the staged kin memlogs. Live code cited by path:line. Nothing in the spine or its memlog was edited.
---

# Adversarial review — bmad-suite lifecycle spine

**Verdict: pass-with-fixes.** The paradigm (install-class adapters, wield-by-routing,
relay-never-absorb) and AD-1..AD-8 hold as stated, and the minted stories already improvise
guards for two of the holes (14.9 refuses `--apply` on a stale harness; 31.1 defines the TEA
equivalence predicate). But the stories were minted from a spine that leaves the holes open, so
the guards live in story prose, not in an AD, and several pairs below build incompatibly *as the
live code stands*. Two are blocking before any 46.x story is dispatched (F-1, F-2). Close them
with four new ADs (AD-9..AD-12) and eight tightenings, listed at the end.

## Findings

| # | Sev | Hole (the two units) | Close with |
|---|---|---|---|
| F-1 | critical | 46.2/46.3/46.4/46.8 record modules in `_bmad/config.yaml` (46.2 and 46.4 name it in their Surface); 14.9 and CAP-7/CAP-8 read `_bmad/_config/manifest.yaml`. Two rosters of one entity; TEA's `{test_artifacts}` config has no writer, so a provisioned TEA HALTs at render | new **AD-9** one module roster + one config-pin path |
| F-2 | high | 14.9 (`Deps: S-14.6, marshal:S-30.5`) and 47.5 (`marshal:S-30.5, marshal:S-30.2`) plus nine station stories (`steward:S-46.x`) carry cross-station `Deps:` tokens; marshal's two parsers read them oppositely (skip = fail-open; local key = never ready), doctor's reads them as cross-station; neither story is a ledger `blocked` row. No AD says how a cross-station order is enforced | new **AD-10** cross-station prerequisites are checks, not `Deps:` tokens; tighten AD-5 |
| F-3 | medium | The relays landed on the owners' memlogs (CAP-12/13, CAP-9 — staged) but era-alignment's `SPEC.md:152-158` still mandates `--shims` and `[dev] skill = "bmad-dev-auto"` while its memlog line 61 records "SPEC re-derived" | tighten **AD-7**: a relay is a memlog line **and** a verified re-render on the owner's spec |
| F-4 | high | Six routing stories write "the AGENTS.md managed block (via `bmad-project-context`)"; that block is replaced on refresh and grows only on evidence — a routing line is neither pitfall nor command — and 46.1 decides the routing home *after* the six were minted; AD-2's "changes the row, not the persona" leaves two personas routing one skill | tighten **AD-2**: one durable home (persona skill), one pointer line, one meta-test |
| F-5 | high | AD-6's "wired agrees with the register" has no agreement function: labs never observable, manticore never `wired` (studio outside the repo), bmb `wired` with zero skills on disk (46.4 claims the *existing* SetupSkillBackend lands five skills; it copies none) | tighten **AD-6**: per-class expected value in `SUITE_PACKAGES`; probes observe the register's provisioning path |
| F-6 | high | The studio root has three homes (register cell, studio config, herald runtime — 18.1's Surface reads "the studio root (recorded in `adoption-register.md` row 9)") and the persona routes to `mc-*` skills a repo session cannot load | tighten **AD-3**: one machine-readable per-machine declaration; the persona note is a hand-off |
| F-7 | high | `[epic_surfaces]`: `.claude/skills/**` is now owned by steward 44, 46 and marshal 30, 31 at once; `_bmad/**` by 46 (and 44 after 47.3); steward `"14"` still owns neither, so 14.9 (deletes 21 skill dirs, edits `_bmad/_config/manifest.yaml`) fires MRS-GATE-007 | new **AD-11** surface ownership follows the writer class |
| F-8 | medium | TEA: 31.1 writes `planning-artifacts/test-architecture.md` ×8 by invoking `bmad-testarch-test-design`, which writes to `{test_artifacts}/test-design` (no writer for the key, F-1) through the symlinked `planning_artifacts` path; the oracle 31.1 defines is the drift test 31.2 deletes | tighten **AD-5**: the retiring test's predicate is the oracle and survives; one doc path pinned per station in layer 5 |
| F-9 | medium | One `min_score` knob (46.3/31.3/11.2 — good) but 46.3 needs the knob 31.3 mints and 31.3 depends on 46.3; 31.3 puts a "lens list" in bmad-loop's `[review]` (no such key) instead of `bmad-review`'s `customize.toml`; 11.1's advisory `Finding`s have no id family in warden's frozen five | tighten **AD-4**: lens = `bmad-review` customize override; a versioned `advisory:` family; 46.3 ships the argument, 31.3 the value |
| F-10 | medium | skf's root is declared in three files; 47.2 now proves in a scratch worktree (good) but CAP-7 restores the yaml *from git* while the custom-toml pin is the declared source | new **AD-12** skf's root is declared once; the yaml is derived |
| F-11 | medium | labs: 46.5 installs via `npx skills add` (GitHub HEAD, non-steward) while the Stack/pipeline-truth carry a conda member whose own entry point copies all 22 skills | tighten **AD-1**: one wrapped, pinned writer per class |
| F-12 | medium | Readiness has no P line for re-provisioning the module/labs skills in foundry; fnd:AD-5's carve-out keeps them as real dirs but nothing re-creates them | tighten **AD-8**: P18, the register's provisioning-path column is the foundry replay list |
| F-13 | low | The register's status cell is a second ledger; 46.10 (`@next` rehearsal, findings to the core-upgrade memlog) is minted in Epic 46 though AD-7 assigns the mechanism to core-upgrade | tighten AD-6/AD-7: status cell = pointer keys; file mechanism stories under the owning chain |
| F-14 | low | 46.8 re-provisions CIS over the C11 lines; the CAP-8 scan does not cover conda-installed modules, so 31.4's widening cannot see them | fold into AD-9 |

Attacks that did **not** open a hole (so they are not re-run): AD-3's "byte-identical `_bmad/`
before and after" (46.6 records a checksum; the CAP-8 scan and `frozen-path-changed` are
root-anchored); AD-4's "none joins `detectors`" (`tea-playwright-check` is in no workflow and no
detector set; 46.3 and 31.3 restate it); the guard tuple vs the catalog's `legacy_custom_names`
(the guard's `SCAN_GLOBS` is an include-list that excludes code and steward data,
`test_no_retired_bmad_skill_ids.py:119-133`; 30.5 widens it to the harness template); the skf
`uninstall` hazard (AGENTS pitfall + P15); bmb-beside-skf naming (`provision.py:482-506`
collision check, 46.4 asserts it); the retirement ordering *inside* 14.9 (its refuse-AC names
the template and every rendered home).

---

## F-1 (critical) — Two rosters of "installed modules"; the apply reads one, provision writes the other

**Unit A — steward 46.2 / 46.3 / 46.4 / 46.8.** Obey AD-1 (drive the member's installer), AD-6
(register row first), steward AD-1. 46.2's Surface names "`_bmad/config.yaml` manifest section";
46.4's Then reads "`_bmad/config.yaml` gains the `bmb` section". That is `provision.py:509-559`
(`_record_module_manifest`) and `--list-modules` reads the same file (`:860-882`). The file does
not exist on the 6.12 tree (6.12 ships `_bmad/config.toml`), so today `--list-modules` reports
`cis: available` while ten `bmad-cis-*` dirs are installed. The bmb backend also drives
`merge-config.py --config-path _bmad/config.yaml` (`provision.py:583-595`), a file the 6.12
renderer never opens: `_bmad/custom/config.toml:9-13` records that `render_skill.py`'s
`load_central_config()` merges only the four `_bmad/config*.toml` / `_bmad/custom/config*.toml`
layers.

**Unit B — steward 14.9 and cadence step 4.** Obey AD-7 and CAP-6/7. `read_installed_modules`
takes `modules:` from `_bmad/_config/manifest.yaml` (`upgrade.py:657-676`, which lists
`core, bmm, skf`) and the apply passes exactly that to `--modules`; CAP-7 selects "every
`source: custom` module in `_bmad/_config/manifest.yaml`"; the CAP-8 scan compares only skills
with a packaged twin under `bmm-skills/` or `core-skills/` (`upgrade.py:1047-1058, 1084-1100`)
and `_bmad/scripts/*.py` with a packaged counterpart (`:1133-1140`).

**Why they build incompatibly.** After 46.x four modules are "installed" by A's roster and
invisible to B's: no apply selects or protects them; their in-place edits (C11's fifteen CIS
lines) can never reach P7's "zero ungoverned" signal (47.1) or 31.4's widening; pipeline-truth's
module census (`suite.py:449-457` reads the yaml keys, or `.claude/skills` prefixes) and
`--list-modules` answer differently. And provisioning TEA succeeds while TEA cannot render:
its workflows reference `{test_artifacts}` 122 times (module.yaml keys `test_artifacts`,
`test_design_output`, `test_stack_type`, `test_framework`); the CondaInstall backend writes no
answers anywhere (`_module_variable_defaults` serves the setup-skill path only); 46.3's
acceptance never mentions a config answer — the same "missing config value" HALT class as C2.
Marshal 31.1 would then author `[modules.tea]` in steward's pin layer to use what steward
provisioned: two owners of one config surface.

**Close with — new AD-9 "One module roster, one config-pin path".** Binds CAP-2, CAP-6, CAP-9.
Installer-tree modules are rostered by `_bmad/_config/manifest.yaml`; every steward-provisioned
module is rostered in exactly one machine-readable place that `--list-modules`, pipeline-truth's
module census, the apply's post-core re-provision step and the CAP-8 scan all read — decided in
46.1 before 46.2 lands (recommended: `_bmad/custom/config.toml [modules.<code>]`, the pin layer
that survives applies, carrying the module's `module.yaml` answers at the installer's own key
path plus `provisioned_by` / `installer` / `skills`; the yaml retired). The provisioning story
answers the module's variables in the same PR; the CAP-8 scan compares conda-module skills
against `share/<pkg>/{skills,agents,workflows}` (closes F-14). `_bmad/config.yaml` is a defect
after AD-9, as a manual copy is under AD-1. Tighten AD-6's test to "the `wired` column read from
the AD-9 roster".

## F-2 (high) — Cross-station `Deps:` tokens have three meanings and no AD

**Unit A — steward 14.9 and 47.5 as minted.** `14.9: Deps: S-14.6, marshal:S-30.5`
(`epics.md:1147`); `47.5: Deps: S-14.9, marshal:S-30.5, marshal:S-30.2` (`:2871`), and 47.5's
own acceptance writes `marshal:S-30.5, marshal:S-30.2` into 44.5. Both obey AD-7 (owners kept)
and AD-8 (a story per prerequisite). Nine station stories (herald 18.1–18.3, doctor 20.4, warden
11.1/11.2, scribe 7.1, atlas 24.1, marshal 31.1/31.3/31.6) carry `steward:S-46.x` the same way.

**Unit B — the three readers of that token.** (1) Fleet drain, `dispatch.py:2556, 3031` via
`dispatch_fleet.parse_epics_dependencies`: `if dep_match.group("station"): continue`
(`dispatch_fleet.py:365-366`) — the token is *skipped*, so 14.9 is ready the moment S-14.6 is
done, before 30.5 (fail-open). (2) Single-station dispatch, `dispatch.py:865` via
`spec_deps.story_deps_from_epics`: the prefix is captured then dropped (`spec_deps.py:24-27,
35-50`; `identity.normalize` sees `<epic>.<seq>`) — `marshal:S-30.5` becomes steward `30.5`
(no such story → never `done` → excluded from `ready_backlog` forever, fail-closed), and
`marshal:S-30.2` becomes steward Story 30.2 "Delete the generator and its inbound refs", ledger
`done` — satisfied by the wrong story. (3) Doctor's `forward-dependency` detector parses the
prefix as a genuine cross-station reference (`doctor/sources/deps.py:132-148`), so its verdict
is `measured` while marshal computes the opposite. The convention AGENTS.md already carries
("a cross-project gate is a ledger `blocked` row the operator flips") was not applied: 14.9 and
47.5 sit at `backlog` (`sprint-status-ledger.yaml:54, 181`).

**Why they build incompatibly.** One token, three semantics, no spine rule. The only real guard
is the refusal 14.9 improvised in its own AC ("refused … when the marshal harness template or any
rendered loop-home policy still emits `bmad-dev-auto`") — right, but it exists because the story
author noticed, not because an AD required it; the nine station stories have no such guard and
either dispatch early (fleet drain) or never (station dispatch). Loop homes are git worktrees
sharing the tracked `.claude/skills/` with untracked rendered policies (`scripts/bmad-loop-
worktree:15`), so an early 14.9 without the refusal would strand all eight.

**Close with — new AD-10 "Cross-station prerequisites are checks, not `Deps:` tokens".** Binds
CAP-9, CAP-10, every station relay. A `Deps:` field never carries a foreign station key (the
epic pass strips the nine + two above into prose "after steward 46.x"); a cross-station
prerequisite is (a) a ledger `blocked` row the operator flips **and** (b) a machine check inside
the consuming story's own ACs against the producer's live artifact, run before the irreversible
act — 14.9's refusal is the template; 31.1/11.2 refuse when `steward provision --list-modules`
(AD-9 roster) lacks `tea`; 44.5 refuses while `cutover-readiness.md` P11/P12 are red as read by
`steward cutover plan`. Tighten AD-5: a caller deletion's equivalence check names the
*producer's* rendered artifacts (the eight policies), not the tracked template.

## F-3 (medium) — The relay landed on the memlogs; one rendered SPEC still says the opposite

The staged kin memlogs now carry the CAPs this spine cites: era-alignment CAP-12 (memlog `:58`),
CAP-13 (`:60`) and an `(event) SPEC re-derived 2026-09-06 … the two shim constraints and the TEA
non-goal replaced` (`:61`); core-upgrade CAP-9 (`:59`) with its SPEC re-rendered and staged
(`SPEC.md:125`). But `spec-bmad-611-era-alignment/SPEC.md` is untouched in the tree: `:152-153`
still reads "Shims stay installed through the v7 cut … every apply passes `--shims`" and `:158`
"keeps `[dev] skill = "bmad-dev-auto"`". Two units: marshal 30.5 minted from the memlog's
superseding text vs any later `bmad-spec validate` / `bmad-build` reading the rendered constraint
— they contradict, and the memlog's own event line claims a re-render that is not on disk.

**Close with — tighten AD-7.** A relay is complete only when the owner's memlog carries the
dated `(capability)` line **and** the owner's SPEC is re-rendered in the same commit, verified by
`chain-completeness-check` (or a grep in the epic pass's readiness gate) before the relayed story
is dispatched. Register § 3's posture lines cite the memlog line numbers, not "retired by memlog".

## F-4 (high) — One "managed block", two owners that rewrite it wholesale, and a routing line is not evidence

**Unit A — herald 18.2/18.3, doctor 20.4, warden 11.1, scribe 7.1, atlas 24.1, marshal 31.6.**
Each obeys AD-2 to the letter; each Surface reads "`AGENTS.md` managed block (via
`bmad-project-context`)" and each Then reads "the AGENTS block cites it".

**Unit B — `bmad-project-context` itself, and 46.1.** The `<!-- bmad:context -->` block
(`AGENTS.md:8-61`) says "edits inside this block are replaced on refresh"; the skill's contract
is that the block "grows only on new evidence" — a pitfall from an observed mistake or a command
whose correct form is not the obvious guess (`bmad-project-context/SKILL.md:85, 103-105`); a
refresh re-verifies every line and removes those whose evidence is gone. A routing note ("reach
for `bmad-os-root-cause-analysis` when …") is neither, so the skill will decline it or drop it
on the next refresh (the 30.5 pitfall refresh is already scheduled). 46.1's acceptance then
"verifies and closes the Spec's routing-note open question: persona skill + AGENTS block, or
block only" — decided after the six stories that depend on the answer were minted with
"persona + block". AD-2's own rule compounds it: "a second station wanting a skill changes the
row, not the persona" leaves the old wielder's persona note in place — two personas route one
skill, the state AD-2 exists to prevent. (The SKF block is not the target here, but `skf-export`
rebuilds it from manifest snippets — `update-context.md:39,109` — so it is no home either.)

**Close with — tighten AD-2.** The routing note has exactly one durable home: the wielding
persona skill (`bmad-agent-<station>/SKILL.md`, estate-authored, moves to `skills/personas/`
under fnd:AD-5). AGENTS.md carries one pointer line ("skill routing: `adoption-register.md § 2`")
placed once through `bmad-project-context` under *Where things are* — never per-skill lines. A
re-route story edits the register row **and both** persona skills. Add the test AD-6 has and AD-2
lacks: a meta-test that every register § 2 skill dir is named by exactly one persona skill and
by CLAUDE.md never. Settle it in the spine now; 46.1 then verifies rather than decides.

## F-5 (high) — AD-6's agreement has no function; three members can never agree, one agrees vacuously

**Unit A — steward 46.1.** Restates AD-6 verbatim: `wired` agrees for 13/13, "disagreement is a
finding on the register".

**Unit B — steward 46.9.** Scope is the installer-tree `installed` probe only; `probe_wired`
(`suite.py:503-605`) is untouched.

**Why they build incompatibly.** Per class the probe returns: labs → `documented` when the
string `bmad-labs/skills` appears in the playbook or matrix (`suite.py:472-481`) — 46.5's "four
dirs and no other" is unobservable to it; manticore → module census on the *repo's*
`.claude/skills` for prefix `mc-` (`:498-500, 598-603`) — AD-3 and 46.6 put every `mc-*` in
`<studio>/.claude/skills/`, so manticore reads `unwired` forever while the row says wield; bmb →
`wired` on a `_bmad/config.yaml` key `bmb` (`SUITE_PACKAGES` `wire_bmad_config_keys=("bmb",)`)
which the SetupSkillBackend writes while copying no skill (`provision.py:583-640` runs
`merge-config.py` + `merge-help-csv.py` only) — 46.4's Given/Then says the "existing
`SetupSkillBackend`" lands five skills; it cannot, so either the story extends the backend (its
Surface allows it) or the register and the tool agree on a wired module with nothing wielded.
skf `present`, loop `provisionable`, eval `runnable` have no verdict mapping. AD-6's tie-break
then blames the register for the tool's blind spots, permanently.

**Close with — tighten AD-6.** Agreement is a declared function: each `SUITE_PACKAGES` row
carries the expected probe value for verdict `wield` in its class (`wire_policy` exists,
`suite.py:110`), and each class probe observes the *provisioning path the register names* —
labs: the named skill dirs and no other labs dir; manticore: the AD-3 declaration (F-6) and its
`mc-*` census; bmb: the five skill dirs. The register's `Wired` column is derived from
`pipeline-truth --json`, never typed. Name the owner: widen 46.9 to the wired predicate or mint
a 46.x story.

## F-6 (high) — The studio root has three homes, and the persona routes to skills another root holds

**Unit A — steward 46.6.** Surface: playbook row, `.gitignore`, register row 9 cell, a doc; the
studio's own `_bmad/custom/config.toml [modules.manticore]`. No machine-readable declaration.

**Unit B — herald 18.1.** Surface: "the studio root (recorded in `adoption-register.md` row 9)",
`bmad-agent-herald` (routes `mc-*`), "a `herald deck …` verb or documented studio invocation".
Herald code needs the root at run time; `pyforge.toml` carries only `[project] name`; the story
points at a markdown cell.

**Why they build incompatibly.** Three declarations of one path with no derivation rule (a
fourth if herald mints a config key; a per-machine home path in a tracked file if `~/` wins).
`bmad-agent-herald` is a repo-root skill while every `mc-*` lives only under
`<studio>/.claude/skills/` — a repo session cannot invoke what the persona "routes to"; AD-2's
"routes to it from its persona skill" and AD-3's "separate root" cannot both be literal. If
`presentations/_studio/` wins, a second `_bmad/` sits under the repo and `resolve_config.py`'s
project-root walk becomes ambiguous for a skill launched inside it.

**Close with — tighten AD-3.** The studio root is declared once, machine-readable and
per-machine (`PYFORGE_STUDIO_ROOT`, or a gitignored `pyforge.local.toml` key); herald's CLI,
pipeline-truth's manticore probe and the register all *cite* it; the register cell is a pointer.
The persona note is a hand-off ("open a session in `<studio>`; run `mc-*` there"), never a route;
`mc-*` are never provisioned into the repo tree. Decide in-repo vs `~/` in 46.1, since 46.6 and
18.1 are already minted against the answer.

## F-7 (high) — Epic surfaces now overlap on purpose, and Epic 14 still owns nothing it writes

**Unit A — steward 14.9.** Deletes 21 dirs under `.claude/skills/`, rewrites
`_bmad/_config/manifest.yaml` and `skill-manifest.csv`, restores `_bmad/skf/config.yaml`.

**Unit B — the tracked `[epic_surfaces]`.** Steward `"14"` (`marshal-policy.toml:176-185`) lists
neither `.claude/skills/**` nor `_bmad/**`; `"46"` lists both; `"47"` lists `_bmad/skf/**`;
`"44"` lists `.claude/skills/**` + `AGENTS.md` + `pixi.toml`; marshal `"30"` and `"31"` list
`.claude/skills/**`, `"31"` also `AGENTS.md` and `_bmad/scripts/bmad_tea_playwright.py`; herald
18 / doctor 20 / warden 11 / scribe 7 / atlas 24 each list `AGENTS.md`.

**Why they build incompatibly.** 14.9 fires MRS-GATE-007 as minted. `.claude/skills/**` now has
four owners and `AGENTS.md` seven; the gate cannot tell an intended shared file from the
two-epics-one-path clash it exists to catch, so it will either be silenced by ever-wider globs
or fire on legitimate work. 47.3 makes the `_bmad/**` overlap (44 vs 46) explicit.

**Close with — new AD-11 "Surface ownership follows the writer class".** Binds CAP-2, CAP-9,
CAP-10. `.claude/skills/<installer-written>/**` and `_bmad/**` are steward provision/upgrade
surfaces (Epics 14, 46); `.claude/skills/bmad-agent-<x>/**` belongs to station `<x>`; the
`bmad:context` block is `bmad-project-context`'s and the SKF block `skf-export`'s (no epic row
lists `AGENTS.md` for hand edits — the routing stories reach it only through the skill); Epic 44
lists these paths only for the move story and only after 46/47 close. Every story that writes a
path ships its `[epic_surfaces]` row in the same PR — add to Consistency Conventions beside the
ledger rule. Immediate fix: give `"14"` `.claude/skills/**` and `_bmad/**`.

## F-8 (medium) — TEA: the oracle is defined in a story and deleted by the next; the doc path has no owner

**Unit A — marshal 31.1 / 31.2.** 31.1 defines the equivalence report well — "every story id and
every live test path the generator emitted present in the TEA output, `TBD`-free" — that *is*
`test_tea_architecture_drift.py`'s predicate. 31.2 then deletes both meta-tests and re-expresses
the drift guard "as a TEA `bmad-testarch-trace` run or an explicit accepted loss".

**Unit B — steward 46.3.** Provisions TEA (`bmad-tea-install` copies `agents/bmad-tea` +
`workflows/testarch` into `.claude/skills/`, `bin/bmad-tea-install:52-53`); no config answer.

**Why they build incompatibly.** 31.1's Surface is `planning-artifacts/test-architecture.md`
×8, but `bmad-testarch-test-design` writes to `{test_artifacts}/test-design`
(module.yaml `test_design_output.result = "{test_artifacts}/{value}"`) and `{test_artifacts}`
has no writer (F-1); per-station output needs a layer-5 override under `BMAD_ACTIVE_PROJECT`,
while TEA's skills resolve through the `planning_artifacts`-style key that "does NOT compose
with a project's `output_folder` override" — eight documents can land in one project's tree.
And the one oracle that makes AD-5's check meaningful is the test 31.2 deletes; "accepted loss"
is AD-5's failure mode by another name.

**Close with — tighten AD-5.** The retiring test's predicate is the oracle: it is re-pointed at
TEA's output and kept (deleted only by a memlog decision that retires the predicate itself); the
document has one writer (31.1) and one path per station pinned in that station's
`.bmad-config.toml`; TEA's `{test_artifacts}` answer is authored by the provisioning story
(AD-9). The spine, not 31.1, states the predicate.

## F-9 (medium) — One knob, a circular dependency, a lens list in the wrong file, and no id family

**Unit A — steward 46.3.** "a pixi task `tea-test-review` wraps `… --min-score <N>` with `N`
read from a policy value marshal 31.3 owns"; `Deps: S-46.1`.

**Unit B — marshal 31.3 and warden 11.1/11.2.** 31.3 `Deps: steward:S-46.3`, mints
`review.min_score` in `core/policy.py` + `policy.json` and "a lens list" in
`adapters/harness_bmadloop.py`'s review-step policy; 11.2 wraps 46.3's pixi task; 11.1's outputs
"surface as advisory findings only, a test proves `compose()` ignores them".

**Why they build incompatibly.** (a) The single knob is right, but 46.3 needs the value 31.3
mints and 31.3 depends on 46.3 — a cycle across stations that F-2's parsers cannot even see.
(b) bmad-loop's `[review]` table has `enabled / trigger / on_timeout / on_status_contradiction`
(`harness_bmadloop.py:307-320`), no lens key; the lens set is `{workflow.lenses}` resolved from
`bmad-review`'s `customize.toml` (`bmad-review/SKILL.md:10, 28`), overridable under
`_bmad/custom/` — the fleet's precedent for harness lenses is in-place edits of installer-owned
skill steps (inventory C5), which P7/P13 forbid and the CAP-8 scan flags. (c) A warden `Finding`
id must match one of five families (`models.py:388-396`; `report-schema.json:307-310`, frozen);
an advisory from `tea-test-review` or `bmad-os-review-pr` has none.

**Close with — tighten AD-4.** 46.3 ships the task taking `--min-score` as an argument (default
80); 31.3 supplies the value from `review.min_score`; the lens is a `bmad-review` customize
override under `_bmad/custom/`, never a harness-policy key or an in-place skill edit; warden's
advisory rides a new `advisory:<tool>:<subject>` family added by a versioned schema bump in
11.1, or is emitted as a non-`Finding` note — decided in the spine.

## F-10 (medium) — skf's root is declared three times; CAP-7 restores the wrong one

47.2 now proves in a scratch worktree ("never edited in place") — the proof half is closed. The
declaration half is not: `_bmad/skf/config.yaml:16-18` (`skills_output_folder: .claude/skills`),
`_bmad/custom/config.toml [modules.skf]` (the C17 pin, `{project-root}/.claude/skills`) and the
regenerated `_bmad/config.toml [modules.skf]` all state it; CAP-7 restores the yaml *from git*
after every apply while the pin is the declared source — the moment 44.5 flips the root, the
yaml and the pin diverge on the next apply. Units: 47.2's recorded key vs 14.7's restore.

**Close with — new AD-12 "skf's root is declared once".** The custom-toml pin is the single
declaration; `_bmad/skf/config.yaml` is derived (CAP-7's restore becomes a re-render from the
pin, not a checkout); 47.2 records the exact key; flipping the root is a 44.5 act.

## F-11 (medium) — labs: two install paths, two versions, one row

46.5's Surface: `.claude/skills/{mcp-builder,…}` "installed via `npx skills add bmad-labs/skills
--skill <name>`" — GitHub HEAD at run time, not steward. The Stack table, pipeline-truth and
mason carry a conda member `bmad-labs-skills 1.0.0.dev0 @HEAD` whose recipe ships
`bmad-labs-skills-install` copying all 22 skills into `.claude/skills/`
(`recipes/bmad-labs-skills/recipe.yaml:60-63`); `installed` reads conda-meta. AD-1 says steward
is the only writer of suite skills yet names a non-steward writer; two writers, different bytes
and versions; the conda entry point would violate 46.5's "no other labs skill" meta-test.

**Close with — tighten AD-1.** Plugin-path is steward-wrapped (`steward provision --plugin labs
--skill <name>`, calling `npx skills add` pinned to the recipe's commit), or the conda entry
point with a `--skill` allowlist is the path and `npx` is banned — one, not both; the register's
provisioning-path cell equals the wrapper's invocation; the AD-9 roster records each labs skill.

## F-12 (medium) — No readiness line re-provisions the module/labs skills in foundry

47.1's P1–P17 have owners; none covers `.claude/skills/bmad-testarch-*`, `bmad-os-*`,
`bmad-cis-*`, `bmad-bmb-*` and the four labs dirs — conda/npx-written, tracked today, outside
`_bmad/`. The corrected fnd:AD-5 row says they "stay real directories (the carve-out)", but
nothing re-creates them in foundry: fnd:AD-12 moves `_bmad/` whole, 44.11's link step generates
adapters for estate skills only. Units: 47.1 vs 44.5/44.11.

**Close with — tighten AD-8.** P18: every register row with verdict `wield` is re-provisioned in
foundry by its class adapter from the register's provisioning-path cell — the replay list;
tracked copies are never moved. Owner steward, a 47.x story.

## F-13 (low) — The status cell is a second ledger; one mechanism story sits in the wrong chain

Register rows carry "46.3, marshal 31.1–31.3, warden 11.2" where the convention says one key or
`—`; `sprint-ledger-sync` is the one ledger of record (P5, fnd:AD-12) and nothing syncs the
cell. 46.10 (`@next` rehearsal; "findings are appended to the core-upgrade memlog") is minted in
Epic 46 with `Deps: S-14.9` — by AD-7 the mechanism is core-upgrade's. Tighten AD-6/AD-7: status
cell = pointer keys only, no state words; a story for a mechanism another chain owns is filed
under that chain's epic.

## F-14 (low) — CIS re-provision vs the C11 lines and 31.4

46.8 overwrites the ten `bmad-cis-*/SKILL.md` from the packaged revision — the right fix, since
the packaged copy is newer — but the CAP-8 scan does not cover conda-installed modules (F-1), so
a genuinely local line among the fifteen would be clobbered silently and 31.4's widening cannot
see it. Folded into AD-9.

---

## ADs to add or tighten (for the spine's next memlog entry)

New:
- **AD-9** One module roster, one config-pin path (F-1, F-14).
- **AD-10** Cross-station prerequisites are checks, not `Deps:` tokens (F-2).
- **AD-11** Surface ownership follows the writer class (F-7).
- **AD-12** skf's root is declared once (F-10).

Tightened:
- **AD-1** plugin-path has one wrapped, pinned writer (F-11).
- **AD-2** one durable routing home + one pointer line + a persona↔register meta-test (F-4).
- **AD-3** one machine-readable studio declaration; the persona note is a hand-off (F-6).
- **AD-4** lens by customize override; a named finding family; argument vs value split (F-9).
- **AD-5** the retiring test's predicate is the oracle; producer artifacts for caller deletions (F-2, F-8).
- **AD-6** agreement is a declared per-class function; `Wired` derived; status cell = pointer (F-5, F-13).
- **AD-7** a relay is a memlog line plus a verified re-render on the owner's spec (F-3, F-13).
- **AD-8** P18 foundry re-provision from the register's provisioning-path column (F-12).

Blocking before any 46.x / 14.9 dispatch: F-1 and F-2 (the stories are minted; the AD text must
exist so the guards live in the spine, not in prose, and `"14"`'s surface row must be widened).
F-3's rendered-SPEC re-render is a one-commit fix. The rest can land as the stories are driven,
provided the AD text exists first.
