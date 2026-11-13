---
title: "46.1: Each atlas capability's marker says what is built, open or retired"
type: 'chore'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: heavy
story: '46.1'
spec: pyforge-atlas
surface:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-36-3-the-query-plane-estate-source-has-a-producer.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-46-1-each-atlas-capability-s-marker-says-what-is-built-open-or-retired.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-pyforge-atlas-2026-07-25/brief.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - docs/dreams/pyforge-atlas.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-42-2-any-manifest-becomes-one-comparable-inventory-behind-one-exit-code-sits-behind-a-kill-switch.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-41-1-fr-15-names-the-capability-minted-from-its-constraint-and-the-spec-s-cut-text-is-restored.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-36-1-the-basilisk-population-runs.md
  - docs/governance/fr-baseline.json
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The cutover readiness audit at main `82a2b18828` read the atlas Spec's capability markers against the tree. Fourteen satellite capabilities (CAP-18..CAP-31) read `(shipped 2026-09-09)` with no code; CAP-44..CAP-47 read shipped for the views runtime the operator retired on 2026-09-09; CAP-7, CAP-43, CAP-52 and CAP-58..CAP-60 read plain shipped although an attended half never ran or a story is still blocked; CAP-61..CAP-67 and CAP-69 read ready with every citing story done. A second root that reads these markers would rebuild what was retired and trust a parity that was never signed. Spec text is wrong, code is right.

**Approach:**
- **The memlog is already written.** The mint of 2026-11-10 logged one entry per amended capability in `spec-pyforge-atlas/.memlog.md` (the `decision`, `correction`, `change` and `note` entries after the 2026-11-10 `Cutover readiness mint` event). The `correction` the independent review of the mint appended the same day (the last 2026-11-10 entry before this story) replaces six of those marker literals with the ruled grammar: CAP-18..CAP-31, CAP-44..CAP-47, CAP-7, CAP-43, CAP-52 (row 8 below), CAP-66, and CAP-67, which carries no open leg because Story 36.2 recorded its attended run; render that entry's literals, not the earlier ones. Read each against the tree; where the tree disagrees, append a `correction` first. For CAP-61..CAP-67 and CAP-69, read the date the last citing story reached `done` from each story spec's Auto Run Result (never guessed) and append one `change` entry naming the dates.
- **Render, never hand-edit.** Re-derive `SPEC.md` through the anchored script render the operator approved for this PR (second addendum, ruling 7): a python3 script that asserts each anchor occurs exactly once before it replaces it; then run the bmad-spec self-validation twice and log each pass as a memlog event (`Self-validate pass 1/2 after script render …`, `… pass 2/2 …`).
- **Marker grammar.** CHAIN-STANDARD § 4 as steward Story 120.3 amends it (ruling 2 of the second addendum): `(retired <date>[: <reason>])`, and a qualifier after a semicolon (`not met: <clause>, DW-<id>`, `operator act open, DW-<id>`, `superseded by CAP-n`). There is no `(unbuilt)` token. CAP-64 and CAP-65 hold to the story-close figures `live-sources.md` records (ruling 4) and carry no open leg.
- **Story 36.3's story spec.** Write `specs/spec-36-3-the-query-plane-estate-source-has-a-producer.md`: `type: 'feature'`, `status: 'blocked'`, the `flag:` block for `pyforge.atlas.estate_source_producer` in the shape of `spec-42-2-…` (the key joins `flags.json` only when the story is built); blocking condition: no steward story exports the platform tables through `pyforge.core.station_port`.
- **The chain-currency cascade.** The brief, the PRD, the spine and `epics.md` each gain `updated:` and one dated `Currency reconciliation — 2026-11-10 (Story 46.1)` section; the PRD's and the spine's say both satellites are retired, never built, and that their Python text binds nothing; `currency_review` gains a 2026-11-10 line; the `docs/specs/…` input paths in the PRD, spine and epics frontmatter gain their `archive/` prefix.
- **The deferred rows.** Write DW-atlas-46-1-1..9 into `deferred-work-ledger.md` (in this Spec's `surface:`): 1 package comments cite the pre-`tests/unit/` layout and the archived intake spec's sections; 2 most open rows carry no `severity:`; 3 atlas still reads A's conda-forge-expert tree and, in attended parity, the legacy `cf_atlas.db`; 4 seven atlas gate tasks run only in `-e local-recipes` (written: steward declined moving them, steward Story 124.1; the row's body names the plan's working id `DW-atlas-cutover-2026-11-10-4`, which steward Story 124.1's spec cites, so that cite resolves by grep); 5 the attended floors of CAP-64 and CAP-65 can only be measured where the legacy `cf_atlas.db` exists (its fix line cites ruling 4: the capabilities hold to the story-close figures); 6 `tier-taxonomy.md` and `complete-export-contract.md` are live contracts under `archive/`; 7 the OpenLineage producer URI points at `…/tree/main/pyforge-atlas`, which does not exist; 8 Story 24.2's attended, credentialed run (CAP-43's one recorded run, the absorbed spec-atlas-kedro-catalog-expansion:CAP-8) has not happened, so CAP-43 stays ready and CAP-52's live-execution half stays open (operator-owned; no other open row names it: Story 24.2 cites only DW-FU-23-5, closed 2026-10-03); 9 (DW-atlas-46-1-9, which Stories 41.2 and 41.3 cite) the retired Unity satellite's 48 first-defined ids (FR-23..FR-60, NFR-1..NFR-10) stay arrowless and baselined in `docs/governance/fr-baseline.json` `projects.pyforge-atlas` for good: Story 41.3, which owned them, is retired, and Story 41.2's `Fold provenance` record section suppresses duplicates only (doctor's `sources/one_chain.py` `_fr_definitions` still returns a first definition there), so doctor Story 58.4's `--prune` keeps them (owner: none; retired satellite history held in the baseline; doctor Story 58.4 replaces the baseline's hand-maintained `owners.pyforge-atlas` rows, which name Stories 41.2 and 41.3, with one row naming this one). Story 48.4's reconcile event names the file.
- Ledger modes are not this story's: CAP-18..CAP-31 `retire`, CAP-7 `A-only` until mason Story 39.2, CAP-68 `B-only` are written by the capability ledger's owner (steward Stories 121.3 and 121.7).

Ledger key: `46-1-each-atlas-capability-s-marker-says-what-is-built-open-or-retired`.
Type / Effort / Deps: chore / L / none.

### Living CAP citations

- `spec-pyforge-atlas` CAP-7, CAP-18..CAP-31, CAP-43..CAP-47, CAP-52, CAP-58..CAP-69 (markers; the retired capabilities keep their text as history)

## Acceptance Criteria

Each command runs from the worktree root; read every verdict from its exit code, never through a pipe.

- **AC1 — Each of CAP-18..CAP-31 reads exactly `(retired 2026-11-10: never built)`, with no further qualifier.** Expected: exit 0, prints [] (today it prints all 14).

  ```bash
  python3 -c 'import re,sys;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();mk={m.group(1):m.group(2) for m in re.finditer(r'"'"'(?m)^- \*\*CAP-(\d+) — .*?← [^(\n]*\((.*)\)\s*$'"'"',s)};bad=[n for n in range(18,32) if mk.get(str(n))!='"'"'retired 2026-11-10: never built'"'"'];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC2 — CAP-44..CAP-47 read retired by the 2026-09-09 ruling.** Expected: exit 0, prints [].

  ```bash
  python3 -c 'import re,sys;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();d=dict(re.findall(r'"'"'(?m)^- \*\*CAP-(\d+) — (.*)$'"'"',s));bad=[n for n in range(44,48) if '"'"'(retired 2026-09-09'"'"' not in d[str(n)] or '"'"'(shipped'"'"' in d[str(n)]];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC3 — CAP-61..CAP-67 and CAP-69 read shipped; CAP-68 and CAP-43 read ready.** Expected: exit 0, prints [].

  ```bash
  python3 -c 'import re,sys;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();d=dict(re.findall(r'"'"'(?m)^- \*\*CAP-(\d+) — (.*)$'"'"',s));bad=[n for n in '"'"'61 62 63 64 65 66 67 69'"'"'.split() if '"'"'(shipped '"'"' not in d[n]]+[n for n in ['"'"'43'"'"','"'"'68'"'"'] if '"'"'(ready '"'"' not in d[n]];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC4 — Each capability with an open half names the story or deferred-work row it waits on.** Expected: exit 0, prints [].

  ```bash
  python3 -c 'import re,sys;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();b=lambda n:re.search(r'"'"'(?ms)^- \*\*CAP-%d — .*?(?=^- \*\*CAP-\d+ — |^## )'"'"'%n,s).group(0);need={7:['"'"'DW-B1-1'"'"','"'"'DW-B4-1'"'"','"'"'DW-B4-2'"'"','"'"'DW-B4-3'"'"'],43:['"'"'24.2'"'"','"'"'DW-atlas-46-1-8'"'"'],52:['"'"'24.2'"'"','"'"'DW-atlas-46-1-8'"'"'],58:['"'"'DW-H3'"'"'],59:['"'"'DW-H3'"'"'],60:['"'"'DW-H3'"'"'],66:['"'"'DW-atlas-36-1-1'"'"'],20:['"'"'spec-pyforge-steward:CAP-153'"'"']};bad=[(n,w) for n,ws in need.items() for w in ws if w not in b(n)];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC5 — Every satellite subsection says retired, and every section that names Python 3.12 or 3.13 names the 3.14 floor (decision D6).** Expected: exit 0, prints [] (today it prints the ten `### Satellite:` headings and the sections at lines 767, 801, 972 and 985).

  ```bash
  python3 -c 'import re,sys;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();secs=re.split(r'"'"'(?m)^(?=#{2,3} )'"'"',s);bad=[x.splitlines()[0] for x in secs if x.startswith('"'"'### Satellite:'"'"') and '"'"'Retired 2026-11-10'"'"' not in '"'"' '"'"'.join(x.splitlines()[:5])];bad+=[x.splitlines()[0] for x in secs if re.search(r'"'"'3\.1[23]\b'"'"',x) and '"'"'3.14 floor'"'"' not in x];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC6 — The stale story counts are gone and the parity-gate story is named by its real key.** Expected: exit 0.

  ```bash
  ! grep -qE "the 32 stories merged|\(32/32, 2026-07-18\)" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md && grep -q "Story 24.3" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  ```

- **AC7 — Story 36.3 has a tracked story spec at status blocked that carries its flag block.** Expected: exit 0; the JSON object it prints has verdict pass or warn, never red (a `type: feature` spec with no `flag:` block is `flag-missing`).

  ```bash
  grep -qE "^status: '?blocked'?" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-36-3-the-query-plane-estate-source-has-a-producer.md && grep -q "key: pyforge.atlas.estate_source_producer" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-36-3-the-query-plane-estate-source-has-a-producer.md && python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-36-3-the-query-plane-estate-source-has-a-producer.md
  ```

- **AC8 — The nine deferred rows of this effort are in the ledger.** Expected: exit 0 (all nine rows: row 4 is written because steward declined moving the seven gate tasks, steward Story 124.1, and its body names the alias `DW-atlas-cutover-2026-11-10-4`; row 8 is the one CAP-43 and CAP-52 name; row 9 holds the 48 retired satellite ids the baseline keeps).

  ```bash
  test "$(grep -cE '^### DW-atlas-46-1-[1-9]: ' _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md)" -eq 9 && grep -q 'DW-atlas-cutover-2026-11-10-4' _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  ```

- **AC9 — The planning detectors stay green after the cascade.** Expected: exit 0 for each (read each exit code, never through a pipe).

  ```bash
  pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild memlog-fidelity-check && pixi run -e pyforge-guild story-status-check && pixi run -e pyforge-guild deferred-work-check && pixi run -e pyforge-guild flag-gate-check
  ```

- **AC10 — Every retired marker and every qualifier keeps the ruled grammar.** Expected: exit 0, prints [] (today it prints the capabilities with no qualifier yet). A `not met` clause is `not met: <clause>, DW-<id>`, an `operator act open` clause is `operator act open, DW-<id>`, a `superseded by` clause is `superseded by CAP-n`, a retired lead is `retired <date>[: <reason>]`, and no marker says `unbuilt`; CAP-7, CAP-43, CAP-52 and CAP-58..CAP-60 carry a `not met` qualifier (CAP-7 names DW-B4-1 and DW-B4-2), CAP-44..CAP-47 end at `superseded by CAP-50`, CAP-66 ends at `operator act open, DW-atlas-36-1-1`, and CAP-67 carries no open leg.

  ```bash
  python3 -c 'import re,sys;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();mk={m.group(1):m.group(2) for m in re.finditer(r'"'"'(?m)^- \*\*CAP-(\d+) — .*?← [^(\n]*\((.*)\)\s*$'"'"',s)};Q=[('"'"'not met'"'"',r'"'"'not met: .+, DW-[A-Za-z0-9-]+'"'"'),('"'"'operator act open'"'"',r'"'"'operator act open, DW-[A-Za-z0-9-]+'"'"'),('"'"'superseded by'"'"',r'"'"'superseded by CAP-\d+'"'"')];bad=[(n,p) for n,m in mk.items() for p in m.split('"'"'; '"'"')[1:] for k,rx in Q if p.startswith(k) and not re.fullmatch(rx,p)];bad+=[(n,m.split('"'"'; '"'"')[0]) for n,m in mk.items() if m.startswith('"'"'retired'"'"') and not re.fullmatch(r'"'"'retired \d{4}-\d{2}-\d{2}(: [^;]+)?'"'"',m.split('"'"'; '"'"')[0])];bad+=[(n,'"'"'unbuilt'"'"') for n,m in mk.items() if '"'"'unbuilt'"'"' in m];bad+=[(n,'"'"'no not-met qualifier'"'"') for n in '"'"'7 43 52 58 59 60'"'"'.split() if '"'"'; not met: '"'"' not in mk[n]];bad+=[(n,'"'"'not superseded by CAP-50'"'"') for n in '"'"'44 45 46 47'"'"'.split() if not mk[n].endswith('"'"'; superseded by CAP-50'"'"')];bad+=[('"'"'66'"'"','"'"'no operator act'"'"') for _ in [0] if not mk['"'"'66'"'"'].endswith('"'"'; operator act open, DW-atlas-36-1-1'"'"')];bad+=[('"'"'67'"'"','"'"'an open leg'"'"') for _ in [0] if re.search(r'"'"'; (not met|operator act open)'"'"',mk['"'"'67'"'"'])];bad+=[('"'"'7'"'"',w) for w in ['"'"'DW-B4-1'"'"','"'"'DW-B4-2'"'"'] if w not in mk['"'"'7'"'"']];print(bad);sys.exit(1 if bad else 0)'
  ```

## Boundaries & Constraints

**Always:**
- Append the memlog first, then render; log both self-validate passes.
- Keep each retired capability's intent and success as history under the lead '(retired, never built)' or its retired note.
- Read every date from the tree; quote the story spec it came from.

**Never:**
- Never hand-edit `SPEC.md`; never renumber, reuse or remove a CAP id.
- Never write an `(unbuilt)` marker or a ledger mode.
- Never touch `src/` or CAP-73's text or marker (the mint rendered it; Story 48.4 flips its marker to shipped once Stories 47.1 and 47.2 are done, ruling 6 of the second addendum).

</intent-contract>

## Binding

- Parent: `spec-pyforge-atlas` CAP-7, CAP-18..CAP-31, CAP-43..CAP-47, CAP-52, CAP-58..CAP-69 (markers; the retired capabilities keep their text as history).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-11-10 (cutover readiness) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the entry of that date and its two addenda).
- Epic: Epic 46, minted 2026-11-10 with this story.
- Ledger key: `46-1-each-atlas-capability-s-marker-says-what-is-built-open-or-retired`.
- Deps: none.
- Cross-station deps: steward:S-120.3 (CHAIN-STANDARD § 4's retired marker and qualifiers).
- Flag: none (`type: chore`: planning artifacts only, no runtime path; spec-feature-flag-governance Q1).
- Surface: `marshal-policy.toml` `[epic_surfaces]."46"`, narrowed by this spec's `surface:`.
- Minted 2026-11-10 in the atlas mint of the one cutover-readiness PR (branch `cutover-readiness-2026-11-10`); built in the same PR.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: exit 0.

**Run before the push:** the acceptance commands above, each read from its exit code.

## Auto Run Result

Status: backlog (minted 2026-11-10).

Build 2026-11-11 (wave BUILD-1; the status moves at the ledger close, not here):
- Memlog first: two `correction` entries and one `change` entry (the shipped dates and where each was read; the
  Story 24.3 key and the Spec's head note), then the anchored script render of `SPEC.md` (62 anchors, each asserted
  once), then both self-validate passes logged as `event` entries.
- Shipped dates: only Stories 34.14, 34.15 and 35.5 carry a dated `done` in an Auto Run Result, and Story 32.1 in its
  Spec Change Log; for Stories 25.1, 36.1, 36.2, 37.12, 37.13 and 38.1 the date is the landing merge that names the
  key (the memlog `correction` records this). CAP-61 2026-10-11, CAP-62 2026-10-17, CAP-63 2026-10-24, CAP-64 and
  CAP-65 2026-11-01, CAP-66 2026-10-19, CAP-67 2026-10-21, CAP-69 2026-10-24.
- The rendered text cites the ruling without "brief decision D5": that brief is not in the tree, so the cite would not
  resolve for a reader of the Spec.
- Row 9 follows the tree: Story 41.2's spec (orchestrator decision 2026-11-11) and doctor Story 58.4's AC12 say Story
  41.2 writes the one `owners.pyforge-atlas` row and 58.4's final prune keeps it, so the row says that rather than
  "58.4 replaces".
- `deferred-work-ledger.md`'s two stale `### DW-` counts (216, 178) now read 229, the count after rows 1..9.
- Story 36.3's story spec is written `blocked` with its flag block; `flag_gate_check.py --spec` prints verdict `pass`.

## Spec Change Log

- 2026-11-10: minted from the station Dream's entry of 2026-11-10 (cutover readiness) under the operator's rulings of 2026-11-10 ("Accept all", "Retire both", "Accept all, run mint"). Acceptance adjusted by the rulings: the deferred-row check expects all seven rows (steward declined moving the gate tasks); CAP-64 and CAP-65 carry no open leg (ruling 4); markers follow CHAIN-STANDARD § 4 as steward Story 120.3 amends it (ruling 2), so the plan's colon forms became semicolon qualifiers; the memlog entries were written at the mint; AC4 looks for the qualified `spec-pyforge-steward:CAP-153` (CHAIN-STANDARD § 2: a citation of another Spec's capability is always qualified).

- 2026-11-10 (review of the mint): the marker literals follow the ruled grammar exactly (a memlog `correction` replaced six); AC1 asserts the exact retired marker; AC4 and AC8 add DW-atlas-46-1-8 (Story 24.2's attended run, which no open row named); AC10 rejects a qualifier outside the three ruled forms; CAP-73's marker is Story 48.4's (ruling 6).

- 2026-11-10 (second review of the mint): row 8 names the right capability (CAP-43, which carries the absorbed spec-atlas-kedro-catalog-expansion CAP-8; this Spec's own CAP-8 is the read surface); row 4's body names the alias `DW-atlas-cutover-2026-11-10-4` that steward Story 124.1's spec cites; row 9 is added (the 48 retired Unity ids the FR baseline keeps once Story 41.3 is retired, simulated with doctor's parser and prune), so AC8 counts nine rows (rule R4: each gap is a deferred-work row).

- 2026-11-11 (third review of the mint): row 8 cites the absorbed capability in the qualified form `spec-atlas-kedro-catalog-expansion:CAP-8` (CHAIN-STANDARD § 2: another Spec's capability is always `spec-<x>:CAP-n`), so the row the build copies into the deferred-work ledger cannot be read as this Spec's CAP-8. Row 9 says doctor Story 58.4 replaces the two stale atlas `owners` rows of the FR baseline with one row naming DW-atlas-46-1-9 (58.4's AC12 holds it).

## Review Triage Log

- (none yet)
