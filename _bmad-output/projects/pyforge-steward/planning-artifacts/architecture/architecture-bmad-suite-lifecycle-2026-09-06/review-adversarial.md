---
review: adversarial
target: ARCHITECTURE-SPINE.md (bmad-suite lifecycle, epic altitude, status final)
lens: "construct two units one level down that each obey every AD to the letter yet still build incompatibly"
reviewed: 2026-09-06
against: HEAD 35ddefbbc5 (live code cited by path:line; nothing in the spine or memlog was edited)
---

# Adversarial review — bmad-suite lifecycle spine

**Verdict: pass-with-fixes.** The paradigm (install-class adapters, wield-by-routing,
relay-never-absorb) and AD-1..AD-8 hold as stated, but eight of the pairs below build
incompatibly *as the live code stands today*, not hypothetically. Two are blocking for the epic
pass (F-1, F-2): minted as the spine now reads, the stories would record modules in a roster the
apply never reads and would let the `--no-shims` apply land ahead of the harness flip with no
machine to stop it. Close them with the four new ADs (AD-9..AD-12) and the five tightenings
listed at the end before `bmad-create-epics-and-stories` runs.

## Findings

| # | Sev | Hole (the two units) | Close with |
|---|---|---|---|
| F-1 | critical | Steward provision (46.2/3/4/8) records modules in `_bmad/config.yaml`; the apply (14.9) and CAP-7/CAP-8 read `_bmad/_config/manifest.yaml`. Two rosters of one entity; TEA's config has no writer at all | new **AD-9** one module roster + one config-pin path |
| F-2 | critical | 14.9 deletes the `bmad-dev-auto` dir; 30.5 re-points 8 untracked loop-home policies to it. No machine orders them: `Deps:` is station-local and silently remaps foreign keys | new **AD-10** cross-station prerequisites are checks, not `Deps:` tokens; tighten AD-5 |
| F-3 | high | The CAPs this spine "relays" (era-alignment CAP-12/13, core-upgrade CAP-9) exist in no owner memlog; era-alignment's rendered SPEC still mandates `--shims` and `[dev] skill = "bmad-dev-auto"` | tighten **AD-7**: a relay is a verified memlog line on the *owner's* spec, re-rendered before minting |
| F-4 | high | Six station routing stories write "the AGENTS.md managed block"; there are two blocks, each rewritten wholesale by its owner (`bmad-project-context`, `skf-export`) | tighten **AD-2**: one durable home (persona skill), one pointer line, one meta-test |
| F-5 | high | AD-6's "wired agrees with the register" has no agreement function: labs never observable, manticore never `wired` (studio outside the repo), bmb `wired` with zero skills on disk | tighten **AD-6**: per-class expected value in `SUITE_PACKAGES`; probes observe the register's provisioning path |
| F-6 | high | The studio root has three homes (register cell, studio's own `_bmad/custom/config.toml`, herald runtime) and the persona routes to `mc-*` skills a repo session cannot load | tighten **AD-3**: one machine-readable per-machine declaration; the persona note is a hand-off |
| F-7 | high | `[epic_surfaces]`: Epic 44 owns `.claude/skills/**` + `AGENTS.md`; Epics 14/46/47 write them and own neither `.claude/skills/**` nor `_bmad/**`; no `"46"`, `"47"`, marshal `"30"` rows exist → MRS-GATE-007 on every story here, or overlapping owners | new **AD-11** surface ownership follows the writer class |
| F-8 | medium | TEA: 31.1 writes the doc, 31.2 deletes the generator + the only oracle (`test_tea_architecture_drift.py`), TEA writes to `{test_artifacts}/test-design`, not `planning-artifacts/test-architecture.md`; "equivalence" undefined | tighten **AD-5**: the retiring test's predicate is the oracle; one doc path pinned per station in layer 5 |
| F-9 | medium | One `tea-test-review` score, two thresholds (31.3 `--min-score`, 11.2 `warn`), and warden's frozen five-family `Finding.id` grammar has no slot for it; the lens precedent (C5) is in-place skill edits | tighten **AD-4**: one policy knob; lens = `bmad-review` customize override; a versioned `advisory:` family or a non-Finding note |
| F-10 | medium | skf's root is declared in three files (`_bmad/skf/config.yaml`, `_bmad/custom/config.toml [modules.skf]`, regenerated `_bmad/config.toml`); 47.2's proof needs a fourth value and CAP-7 restores the yaml from git | new **AD-12** skf's root is declared once; the yaml is derived; the proof runs detached |
| F-11 | medium | labs: 46.5 runs `npx skills add` (GitHub HEAD, non-steward) while the Stack/pipeline-truth carry a conda member with its own installer that copies all 22 skills | tighten **AD-1**: plugin-path is steward-wrapped and pinned, or the conda entry point is the path — one, not both |
| F-12 | medium | Readiness has no P line for re-provisioning the module/labs skills in foundry; fnd:AD-12 moves `_bmad/` but `.claude/skills/bmad-testarch-*` etc. live outside it and are tracked today | tighten **AD-8**: P18, the register's provisioning-path column is the foundry replay list |
| F-13 | low | The register's status cell is a second ledger ("46.3, marshal 31.1–31.3, warden 11.2" vs the one-key convention); 46.10 (`@next` rehearsal) and half of 14.9 are minted here though AD-7 assigns them to core-upgrade | tighten AD-6/AD-7: status cell = pointer keys only; file mechanism stories under the owning chain |
| F-14 | low | 46.8 re-provisions CIS over the C11 in-place lines; the CAP-8 scan does not cover conda-installed modules, so 31.4's widening cannot see them | fold into AD-9 (scan covers `share/<pkg>` modules) |

Attacks that did **not** open a hole (recorded so they are not re-run): AD-3's "byte-identical
`_bmad/` before and after" is well-formed (the CAP-8 scan and `frozen-path-changed` are
root-anchored); AD-4's "none joins `detectors`" holds today (`tea-playwright-check` appears in no
workflow and no detector set); the guard tuple vs the catalog's `legacy_custom_names` do not
collide (the guard's `SCAN_GLOBS` is an include-list that excludes code and steward data,
`test_no_retired_bmad_skill_ids.py:119-133`); the skf `uninstall` hazard is guarded by AGENTS.md
pitfall + P15; bmb-beside-skf naming (`bmad-bmb-*`/`bmad-agent-builder` vs `skf-*`) passes the
wire-time collision check (`provision.py:482-506`).

---

## F-1 (critical) — Two rosters of "installed modules"; the apply reads one, provision writes the other

**Unit A — steward 46.2 / 46.3 / 46.4 / 46.8 (`steward provision --module …`).** Obeys AD-1
(drives the member's own installer), AD-6 (register row first), steward AD-1 (wraps). Records the
module by writing a top-level `<name>:` key into `_bmad/config.yaml`
(`provision.py:509-559 _record_module_manifest`), and `--list-modules` reads the same file
(`provision.py:860-882 module_install_states`). That file does not exist on the 6.12 tree
(`ls _bmad/config.yaml` → absent; 6.12 ships `_bmad/config.toml`), so today `--list-modules`
reports `cis: available` while ten `bmad-cis-*` dirs are installed. The bmb backend additionally
drives `merge-config.py --config-path _bmad/config.yaml` (`provision.py:583-595`) — a 6.10-era
file the 6.12 renderer never opens: `_bmad/custom/config.toml:9-13` records that
`render_skill.py`'s `load_central_config()` merges only the four `_bmad/config*.toml` /
`_bmad/custom/config*.toml` layers.

**Unit B — steward 14.9 (`--no-shims` apply) and the cadence step 4.** Obeys AD-7 (the apply
stays with core-upgrade) and CAP-6/7. `read_installed_modules` takes `modules:` from
`_bmad/_config/manifest.yaml` (`upgrade.py:657-676`), which lists `core, bmm, skf`
(`_bmad/_config/manifest.yaml:6-28`); the apply passes exactly that to `--modules`. CAP-7 selects
"every `source: custom` module in `_bmad/_config/manifest.yaml`". The CAP-8 scan enumerates
installed skills and compares only those with a packaged twin under `bmm-skills/` or
`core-skills/` (`upgrade.py:1047-1058, 1084-1100`) and `_bmad/scripts/*.py` with a packaged
counterpart (`upgrade.py:1133-1140`).

**Why they build incompatibly.** After 46.x, four modules are "installed" by A's roster and
invisible to B's: no apply selects or protects them; their in-place edits (C11's fifteen CIS
lines) can never reach P7's "zero ungoverned" signal or 31.4's widening; pipeline-truth's module
census (`suite.py:449-457 _bmad_config_keys` on the yaml, or `.claude/skills` prefixes) and
`--list-modules` answer differently. Worse, provisioning TEA succeeds while TEA cannot render:
its workflows reference `{test_artifacts}` 122 times (module.yaml keys `test_artifacts`,
`test_design_output`, `test_stack_type`, `test_framework`), and the CondaInstall backend writes
no answers anywhere (`_module_variable_defaults` is used by the setup-skill path only) — the
same "missing config value" HALT class as C2. Marshal 31.1 would then have to author
`[modules.tea]` in steward's pin layer to use what steward provisioned: two owners of one
config surface.

**Close with — new AD-9 "One module roster, one config-pin path".** Binds CAP-2, CAP-6, CAP-9.
Rule: installer-tree modules are rostered by `_bmad/_config/manifest.yaml` (the installer's);
every steward-provisioned module is rostered in exactly one machine-readable place that
`--list-modules`, pipeline-truth's module census, the apply's post-core re-provision step and the
CAP-8 scan all read — decide it in 46.1 before 46.2 lands (recommended: `_bmad/custom/config.toml
[modules.<code>]`, the pin layer that survives applies, carrying the module's `module.yaml`
answers at the installer's own key path plus `provisioned_by`/`installer`/`skills`; retire the
yaml). The provisioning story answers the module's variables in the same PR; the CAP-8 scan
compares conda-module skills against `share/<pkg>/{skills,agents,workflows}`. `_bmad/config.yaml`
is a defect after AD-9, like a manual copy under AD-1. Tighten AD-6's test to "the `wired` column
read from the AD-9 roster".

## F-2 (critical) — Cross-station order is unenforced; the parser cannot express it

**Unit A — steward 14.9.** Obeys AD-5 (records an "old id vs live id" equivalence check) and
AD-7. Lands `installShims: false` and deletes 21 dirs including `.claude/skills/bmad-dev-auto`.

**Unit B — marshal 30.5.** Obeys steward AD-5 (marshal owns the harness) and AD-7. Edits the
template (`harness_bmadloop.py:328 skill = "bmad-dev-auto"`) and re-renders the eight loop homes'
`.bmad-loop/policy.toml`.

**Why they build incompatibly.** Loop homes are git worktrees (`scripts/bmad-loop-worktree:15`,
`~/.bmad-loops/<slug>`) sharing the tracked `.claude/skills/`; their rendered policy is untracked.
If 14.9 merges first, any home that fast-forwards onto main has a policy naming a skill dir that
no longer exists — every dev pass fails. A's equivalence check cannot see B's artifact: the live
ids are in eight untracked files outside steward's tree. AD-7 orders *cadence steps*, not
stories, and nothing in the spine names the machine that orders 30.5 before 14.9. The obvious
tool — `Deps:` — is station-local and silently wrong across stations: `spec_deps.py:24-27`
`DEP_RE` captures a `station:` prefix, `parse_deps_text` (`:35-50`) discards it, and `normalize`
(`identity.py:134`) sees only `<epic>.<seq>`. So `Deps: marshal:30.5` on 14.9 becomes steward
`30.5` (no such story → never `done` → 14.9 undispatchable forever), and `marshal:30.2` on 44.5
(47.5, G2) becomes steward Story 30.2 "Delete the generator and its inbound refs"
(`epics.md:1983`) — satisfied by the wrong story. AGENTS.md already carries the pitfall
("Marshal's `Deps:` parser is station-local; a cross-project gate is a ledger `blocked` row the
operator flips") but the spine never restates it, and 47.5 as written walks into it.

**Close with — new AD-10 "Cross-station prerequisites are checks, not `Deps:` tokens".** Binds
CAP-9, CAP-10, and 47.5. Rule: a `Deps:` field never carries a foreign station key. A
cross-station prerequisite is (a) a ledger `blocked` row the operator flips **and** (b) a
machine check inside the consuming story's own ACs against the producer's live artifact, run
before the irreversible act: 14.9 refuses `--apply` unless `bmad-loop validate` across all eight
homes plus the template report `bmad-build-auto` (prove-landed already runs the per-home
validate, `release-cadence.md` step 5); 44.5 refuses while `cutover-readiness.md` P11/P12 are
red as read by `steward cutover plan`. Tighten AD-5: for a caller deletion the equivalence check
names the *producer's* rendered artifacts (eight policies), not the tracked template.

## F-3 (high) — The relayed CAPs do not exist where the epic pass will look

**Unit A — marshal 30.5, minted by `bmad-create-epics-and-stories` from
`spec-bmad-611-era-alignment`.** That spec's rendered `SPEC.md:152-158` still says "Shims stay
installed through the v7 cut … every apply passes `--shims` explicitly" and "keeps `[dev] skill =
"bmad-dev-auto"`"; its memlog line 19 carries the same constraint; a grep of that memlog for
`CAP-12` / `CAP-13` returns nothing — only a 2026-09-06 correction note that *mentions*
`--no-shims` while pointing at this chain. The spine (AD-7, CAP-10) and `adoption-register.md § 3`
assert the posture "retired by memlog" and cite "era-alignment CAP-12 / CAP-13".

**Unit B — steward 14.9, minted from this chain and "core-upgrade CAP-9".** The core-upgrade
`SPEC.md` has CAP-1..CAP-8 only; its memlog line 58 names Story 14.9 but no CAP-9.

**Why they build incompatibly.** Both stories obey their own spec; the specs contradict. A story
minted from era-alignment's text keeps `bmad-dev-auto` and passes `--shims`; a story minted from
this spine removes both. The spine's relay model ("this chain relays by memlog and never mints a
story a kin chain already owns") presupposes the owner's memlog carries the relayed CAP — it does
not, for all three.

**Close with — tighten AD-7.** A relay is complete only when (1) the owner's `.memlog.md` carries
a dated `(decision)` line minting the CAP id this spine cites, (2) the owner's SPEC is re-rendered
(or the constraint line is retired in the same memlog entry), and (3) `chain-completeness-check`
(or a one-line grep in the epic pass's readiness gate) proves the id exists before the story is
minted. Until then the register § 3 posture lines are claims, not relays.

## F-4 (high) — Two AGENTS.md managed blocks, two owners that rewrite wholesale

**Unit A — herald 18.2, doctor 20.4, warden 11.1, scribe 7.1, marshal 31.6, atlas 24.1.** Each
obeys AD-2 to the letter: a routing line "in that station's persona skill and the AGENTS.md
managed block". AGENTS.md has two managed blocks: `<!-- bmad:context -->` (`AGENTS.md:8-61`,
"Managed by bmad-project-context; edits inside this block are replaced on refresh") and
`<!-- SKF:BEGIN … SKF:END -->` (`AGENTS.md:211-264`, rebuilt from `.export-manifest.json` snippets
by `skf-export`, `update-context.md:39,109`). A station story picks one and hand-splices a line.

**Unit B — steward 47.2 (`skf-export` root proof) and the post-30.5 `bmad-project-context`
refresh** (open-items: "AGENTS.md pitfall line … recorded by `bmad-project-context` after 30.5
lands"). Each obeys P14 ("AGENTS.md block written only by `bmad-project-context` / `skf-export`")
and its own contract: skf rebuilds its block from the manifest (a hand line is not a snippet →
gone); project-context replaces its block from the ledger, and "the block grows only on new
evidence" — a routing note is neither a pitfall nor a command (`bmad-project-context/SKILL.md:85,
103-105`).

**Why they build incompatibly.** Every routing line placed by A is erased by B's next run, or A
violates P14 by writing the block by hand. AD-2's own rule compounds it: "a second station wanting
a skill changes the row, not the persona" leaves the old wielder's persona note in place — two
personas route one skill, which is the exact state AD-2 says it prevents. The memlog defers the
home to 46.1, but the six routing stories are minted in the same pass.

**Close with — tighten AD-2.** The routing note has exactly one durable home: the wielding
persona skill (`bmad-agent-<station>/SKILL.md`, estate-authored, moves to `skills/personas/` under
fnd:AD-5). AGENTS.md carries one pointer line ("skill routing: `adoption-register.md § 2`") placed
through `bmad-project-context` under *Where things are* — never per-skill lines, in neither
block. A re-route story edits the register row **and both** persona skills. Add the test AD-6 has
and AD-2 lacks: a meta-test that every register § 2 skill dir is named by exactly one persona
skill (and `CLAUDE.md` by none).

## F-5 (high) — AD-6's agreement has no function; three members can never agree, one agrees vacuously

**Unit A — steward 46.1 (register).** Obeys AD-6: rows say labs `wield — skill-by-skill`,
manticore `wield — Herald studio`, bmb `wield — beside skf`; CAP-1 success is "`wired` agrees for
13/13".

**Unit B — steward 46.9 (pipeline-truth installed-stage fix).** Obeys AD-6 and its scope: changes
the `installed` probe for bmad-method to read `_bmad/_config/manifest.yaml`; leaves `probe_wired`
(`suite.py:503-605`) as is.

**Why they build incompatibly.** `probe_wired` returns, per class: labs → `documented` when the
string `bmad-labs/skills` appears in the playbook or matrix (`suite.py:472-481`) — CAP-6's
"exactly four skills, no other" is unobservable; manticore → module census on the *repo's*
`.claude/skills` for prefix `mc-` (`suite.py:498-500, 598-603`) — AD-3 puts every `mc-*` in
`<studio>/.claude/skills/`, so manticore reads `unwired` forever while the row says wield; bmb →
`wired` on a `_bmad/config.yaml` key `bmb` (`SUITE_PACKAGES` `wire_bmad_config_keys=("bmb",)`)
which the SetupSkillBackend writes without copying a single skill (`provision.py:583-640` runs
`merge-config.py` + `merge-help-csv.py` only; `share/bmad-builder/skills/` holds five) — the
register and the tool "agree" on a wired module with nothing wielded. skf `present`, loop
`provisionable`, eval `runnable` are class values with no verdict mapping. AD-6's tie-break
("disagreement is a finding on the register, not on the tool") then blames the register
permanently for the tool's blind spots.

**Close with — tighten AD-6.** Agreement is a declared function, not a reading: each
`SUITE_PACKAGES` row carries the expected probe value for verdict `wield` in its class
(`wire_policy` already exists, `suite.py:110`), and each class probe observes the *provisioning
path the register names* — labs: the named skill dirs present and no other labs dir; manticore:
the AD-3 studio declaration (F-6) and its `mc-*` census; bmb: the five skill dirs. The register's
`Wired` column is derived from `pipeline-truth --json` at edit time, never typed. Either 46.9's
scope widens from installed-stage to the wired predicate or a 46.x story owns it — name which.

## F-6 (high) — The studio root has three homes, and the persona routes to skills another root holds

**Unit A — steward 46.6.** Obeys AD-3: chooses the root, provisions via `--custom-source`, writes
`[modules.manticore]` in the studio's own `_bmad/custom/config.toml`, records the path "as a
register cell".

**Unit B — herald 18.1.** Obeys AD-2 and AD-3: routes `mc-*` (15) from `bmad-agent-herald` and
renders one `.mp4` from a deck's speaker notes. Herald's code (`deck_pipeline.py`) needs the root
at run time; `pyforge.toml` carries only `[project] name = "local-recipes"`; nothing
machine-readable holds it, so 18.1 mints a fourth home (a herald config key or an env var) or
parses markdown.

**Why they build incompatibly.** Three declarations of one path (register cell, studio config,
herald runtime) with no derivation rule; if 46.6 picks `~/pyforge-studio/`, the herald key is a
per-machine home path in a tracked file. And `bmad-agent-herald` is a repo-root skill while every
`mc-*` lives only under `<studio>/.claude/skills/` — a repo session cannot invoke what the persona
"routes to"; AD-2's "routes to it from its persona skill" and AD-3's "separate root" cannot both
be literal. (If `presentations/_studio/` is chosen, a second `_bmad/` sits under the repo and
`resolve_config.py`'s project-root walk becomes ambiguous for any skill launched from inside it.)

**Close with — tighten AD-3.** The studio root is declared once, machine-readable and per-machine
(`PYFORGE_STUDIO_ROOT`, or a gitignored `pyforge.local.toml` key), and herald's CLI, pipeline-
truth's manticore probe and the register all *cite* it; the register cell is a pointer. The
persona note is a hand-off ("open a Claude Code session in `<studio>`; run `mc-*` there"), never a
route; `mc-*` are never provisioned into the repo tree. Decide in-repo vs `~/` in 46.1, not 46.6,
because 46.6 and 18.1 are minted in the same pass.

## F-7 (high) — Epic surfaces name Epic 44 as the owner of what Epics 14/46/47 write

**Unit A — steward 14.9 and 46.2–46.8.** Obey AD-1 ("steward is the only writer of suite
skills"): write `.claude/skills/**`, `_bmad/_config/manifest.yaml`, the AD-9 roster.

**Unit B — the tracked `[epic_surfaces]` marshal enforces (MRS-GATE-007).** Steward
`marshal-policy.toml:514-545` — `"44"` lists `.claude/skills/**`, `.cursor/skills/**`,
`AGENTS.md`, `CLAUDE.md`, `pixi.toml`; `"14"` (`:176-185`) has neither `.claude/skills/**` nor
`_bmad/**`; no `"46"` / `"47"` row exists; marshal has no `"30"` row. 47.3 adds `_bmad/**` to
`"44"` (G1).

**Why they build incompatibly.** Every provisioning and apply story fires the gate, or the epic
pass mints overlapping rows so two epics own one path — the exact clash the gate exists to catch
— with 44 (the move) and 46 (the provisioning) both claiming `.claude/skills/**` while the
cutover is `blocked`.

**Close with — new AD-11 "Surface ownership follows the writer class".** Binds CAP-2, CAP-9,
CAP-10. Rule: `.claude/skills/<installer-written>/**` and `_bmad/**` are steward provision/upgrade
surfaces (Epics 14, 46); the `bmad:context` block is `bmad-project-context`'s and the SKF block is
`skf-export`'s (no epic row lists `AGENTS.md` for hand edits); Epic 44 lists these paths only for
the move story and only after 46/47 close. Every story here that writes a path ships its
`[epic_surfaces]` row in the same PR — add that to the Consistency Conventions "State &
cross-cutting" row beside the ledger rule.

## F-8 (medium) — TEA: three owners of one document and no equivalence oracle

**Unit A — marshal 31.1 / 31.2.** Obeys AD-5: runs `bmad-testarch-*` for eight stations, then
deletes `_bmad/scripts/bmad_tea_playwright.py`, its two meta-tests and two pixi tasks "in the same
story that records an equivalence check".

**Unit B — steward 46.3.** Obeys AD-1: provisions TEA (`bmad-tea-install` copies
`agents/bmad-tea` + `workflows/testarch` into `.claude/skills/`, `bin/bmad-tea-install:52-53`) and
declares the `tea-test-review` pixi task.

**Why they build incompatibly.** TEA writes to `{test_artifacts}/test-design` (module.yaml
`test_design_output.result = "{test_artifacts}/{value}"`), a path family unrelated to
`planning-artifacts/test-architecture.md`; its output is a narrative test design. The generator's
output is a deterministic Story Coverage Matrix whose only oracle is
`test_tea_architecture_drift.py` (every epic story id present, no `TBD`, idempotent) — and 31.2
deletes that oracle. "Equivalence" between the two is undefined, so AD-5's check is either
rubber-stamped or never passes (CAP-4 then narrows, which the Spec allows but the register row 6
does not anticipate). Per-station output needs a layer-5 override written under
`BMAD_ACTIVE_PROJECT`; TEA's skills resolve through the `planning_artifacts` key that "does NOT
compose with a project's `output_folder` override" (CLAUDE.md) — eight docs can land in one
project's tree.

**Close with — tighten AD-5.** The equivalence oracle is the retiring test's own predicate, run
against TEA's output *before* the deletion in the same story; the meta-tests are re-pointed at
TEA's output, not deleted, unless the predicate itself is retired by memlog. The document has one
writer (marshal 31.1) and one path per station pinned in that station's `.bmad-config.toml`
(layer 5), and TEA's `{test_artifacts}` answer is authored by the provisioning story (AD-9).

## F-9 (medium) — One score, two thresholds, two finding grammars

**Unit A — marshal 31.3.** Obeys AD-4: `tea-test-review --base origin/main --min-score N` as a
lens in the review step, "exits with a real code".

**Unit B — warden 11.2.** Obeys AD-4: the same tool as an advisory finding at `warn`.

**Why they build incompatibly.** `--min-score` is decided at 31.3; 11.2 picks its own — one score,
two verdicts on one PR. Warden's `Finding.id` must match one of five families
(`models.py:388-396`; `report-schema.json:307-310`, a frozen external contract) — a TEA or
`bmad-os-review-pr` finding has none, so 11.x either breaks the schema or mis-files under
`hygiene:`. In marshal, lenses resolve from `{workflow.lenses}` in `bmad-review`'s
`customize.toml` (`bmad-review/SKILL.md:10,28`) — a sanctioned override under `_bmad/custom/`
exists, but the fleet's precedent for harness lenses is in-place edits of installer-owned skill
steps (inventory C5), which P7/P13 forbid and the CAP-8 scan flags.

**Close with — tighten AD-4.** (a) One `min_score` knob in marshal-policy consumed by both
callers; (b) the lens is a `bmad-review` customize override under `_bmad/custom/`, never an
in-place skill edit; (c) warden's advisory rides a new `advisory:<tool>:<subject>` id family added
by a versioned `report-schema.json` bump in the same story, or is emitted as a non-Finding note —
decide in the spine, not in 11.2.

## F-10 (medium) — skf's root is declared three times; 47.2's proof needs a fourth

**Unit A — steward 47.2.** Obeys fnd:AD-5 and AD-8: proves `skf-export` accepts
`skills/stations/<x>/` — which requires setting `skills_output_folder` /
`snippet_skill_root_override` (skf hard-maps `claude-code → .claude/skills/`,
`managed-section-format.md`; only the override reaches another root).

**Unit B — core-upgrade CAP-7 (14.7, shipped) and the C17 pin.** Restores `_bmad/skf/config.yaml`
from git after every apply (`skills_output_folder: .claude/skills`, `_bmad/skf/config.yaml:16-18`);
`_bmad/custom/config.toml [modules.skf] skills_output_folder = "{project-root}/.claude/skills"`
is the pin the installer regenerates `_bmad/config.toml [modules.skf]` from.

**Why they build incompatibly.** If 47.2 edits the tracked yaml, CAP-7 re-clobbers it or the pin
disagrees with the yaml on the next apply; if it edits the pin, the yaml (which skf skills read)
still says `.claude/skills` until the next apply. Three declarations, no derivation.

**Close with — new AD-12 "skf's root is declared once".** The custom-toml pin is the single
declaration; `_bmad/skf/config.yaml` is derived (CAP-7's restore becomes a re-render from the pin,
not a `git checkout`); 47.2 proves in a detached worktree with a temporary override and records
the exact key; flipping the root is a 44.5 act.

## F-11 (medium) — labs: two install paths, two versions, one row

**Unit A — steward 46.5.** Obeys AD-1's plugin-path rule: `npx skills add bmad-labs/skills
--skill <name>` — fetches GitHub HEAD at run time, writes `.claude/skills/<name>`, is not steward.

**Unit B — the Stack table / pipeline-truth / mason.** Obey CAP-1 and the register: a conda member
`bmad-labs-skills 1.0.0.dev0 @HEAD` whose recipe ships `bmad-labs-skills-install` copying all 22
skills into `.claude/skills/` (`recipes/bmad-labs-skills/recipe.yaml:60-63`); `installed` is read
from conda-meta.

**Why they build incompatibly.** AD-1 says steward is the only writer of suite skills yet names a
non-steward writer for this class; two writers of the same dirs with different bytes and
versions; the conda entry point would violate CAP-6 ("no other labs skill present").

**Close with — tighten AD-1.** Plugin-path is steward-wrapped (`steward provision --plugin labs
--skill <name>`, calling `npx skills add` pinned to the recipe's commit), or the conda entry
point with a `--skill` allowlist is the path and `npx` is banned — one, not both; the register's
provisioning-path cell must equal the wrapper's invocation, and the AD-9 roster records each
labs skill.

## F-12 (medium) — No readiness line re-provisions the module/labs skills in foundry

**Unit A — steward 47.1 (readiness checklist).** Obeys AD-8: every P line has an owner and a
story; P1–P17 as listed.

**Unit B — steward 44.5 / 44.11.** Obey fnd:AD-5 (adapters generated per machine; installer-
written dirs "stay real directories") and fnd:AD-12 (`_bmad/` moves whole).

**Why they build incompatibly.** `.claude/skills/bmad-testarch-*`, `bmad-os-*`, `bmad-cis-*`,
`bmad-bmb-*` and the four labs dirs are conda/npx-written, tracked today, and outside `_bmad/`;
nothing moves or re-provisions them, and no P line says who does. The "Re-derived by the cutover"
paragraph lists `.claude/skills/` adapters (estate skills) only.

**Close with — tighten AD-8.** Add P18: every register row with verdict `wield` is re-provisioned
in foundry by its class adapter from the register's provisioning-path cell — the replay list;
tracked copies are never moved. Owner steward, a 47.x story.

## F-13 (low) — The status cell is a second ledger; two mechanism stories are filed under the wrong chain

Register rows carry "46.3, marshal 31.1–31.3, warden 11.2" where the convention says one key or
`—`; `sprint-ledger-sync` is the one ledger of record (P5, fnd:AD-12) and nothing syncs the cell.
46.10 (`@next` rehearsal) "appends findings to the core-upgrade memlog" (`release-cadence.md`) —
by AD-7 it is core-upgrade's (Epic 14), and 14.9 is one key for two chains' deliverables (the
flag and the live apply). Tighten AD-6/AD-7: the status cell holds pointer keys only, never state
words; a story for a mechanism another chain owns is filed under that chain's epic.

## F-14 (low) — CIS re-provision vs the C11 lines and 31.4

46.8's idempotent re-provision overwrites the ten `bmad-cis-*/SKILL.md`; C11 says the packaged
copy is the newer one, so this is the fix — but the CAP-8 scan does not cover conda-installed
modules (F-1), so if any of the fifteen lines were local, nothing would have said so, and 31.4's
surface widening cannot see them. Folded into AD-9.

---

## ADs to add or tighten (summary for the spine's next memlog entry)

New:
- **AD-9** One module roster, one config-pin path (F-1, F-14).
- **AD-10** Cross-station prerequisites are checks, not `Deps:` tokens (F-2).
- **AD-11** Surface ownership follows the writer class (F-7).
- **AD-12** skf's root is declared once (F-10).

Tightened:
- **AD-1** plugin-path has one wrapped writer (F-11).
- **AD-2** one durable routing home + a pointer line + a persona↔register meta-test (F-4).
- **AD-3** one machine-readable studio declaration; persona note is a hand-off (F-6).
- **AD-4** one threshold knob; lens by customize override; a named finding family (F-9).
- **AD-5** the retiring test's predicate is the oracle; producer artifacts for caller deletions (F-2, F-8).
- **AD-6** agreement is a declared per-class function; `Wired` derived, status cell = pointer (F-5, F-13).
- **AD-7** a relay is a verified memlog line on the owner's spec (F-3, F-13).
- **AD-8** P18 foundry re-provision from the register's provisioning-path column (F-12).

Blocking for the epic pass: F-1 and F-2 (and F-3, because it decides which text 30.5 is minted
from). The rest can land as the epic pass mints, provided the AD text exists first.
