---
title: "46.2: The atlas capabilities describe the code that runs"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: medium
story: '46.2'
spec: pyforge-atlas
surface:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-46-2-the-atlas-capabilities-describe-the-code-that-runs.md
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py
  - archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/.memlog.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Spec says seven pipelines where twelve are registered; CAP-51 and CAP-52 carry no intent or success; six capabilities cite companions that exist only under `archive/`; the 'live by default' Constraint does not name the flag that ships off; the data-root precedence covers one of four resolvers; and the attended floors lean on a database a second root will not have. Spec text is wrong or silent, code is right. The scope decision is to state the legacy reads as they are, not to re-plumb them.

**Approach:**
- **The memlog is already written.** The mint of 2026-11-10 logged the `change`, `correction` and `constraint` entries for CAP-1, CAP-35, CAP-36, CAP-43, CAP-50..CAP-52, CAP-54..CAP-56, CAP-59, CAP-64, CAP-65, CAP-69..CAP-72 and the two Constraints. Read each against the tree and append a `correction` where it disagrees; then render through the anchored script with both self-validate passes logged, as Story 46.1 does.
- **CAP-64 and CAP-65 (ruled).** Ruling 4 of the second addendum: both hold to the story-close figures `live-sources.md` records. The text says so; `live-sources.md`'s header paragraph gains the sentence that begins 'A root with no legacy database' and says such a root is held to those recorded figures. Only the header paragraph of `live-sources.md` changes.
- **The spine.** AD-3's heading becomes 'AD-3 — Seven sealed domain pipelines, five governed additions; producer owns the dataset (FR-2)' and the first sentence of its Rule 'the sealed migration set is exactly spec § 5.2 (…); twelve pipelines are registered (see the amendment below)'. The 2026-08-26 / 2026-11-01 amendment on the same rule stays. The naming-convention row and the structural seed gain the five governed additions. The id `AD-3` and its `Binds:` line do not move.
- **The cascade.** The PRD, the spine and `epics.md` each gain one dated `Currency reconciliation — 2026-11-10 (Story 46.2)` section recording these edits.
- MUST 3's companion half (`catalog-contract.md`, `gate-contract.md`) is Story 47.2's; the record of every outside read is `contract.md`, Story 47.1's. Ledger modes are not this story's.

Ledger key: `46-2-the-atlas-capabilities-describe-the-code-that-runs`.
Type / Effort / Deps: chore / M / S-46.1.

### Living CAP citations

- `spec-pyforge-atlas` CAP-1, CAP-35, CAP-36, CAP-43, CAP-50..CAP-52, CAP-54..CAP-56, CAP-59, CAP-64, CAP-65, CAP-69..CAP-72; the Constraints 'One frozen exit-code convention' and 'Public sources live by default'

## Acceptance Criteria

Each command runs from the worktree root; read every verdict from its exit code, never through a pipe.

- **AC1 — CAP-1 no longer says exactly seven and no capability is hollow.** Expected: exit 0.

  ```bash
  ! grep -q "exactly seven typed domain pipelines" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md && ! grep -q "The absorbed Spec's success clause is the record" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  ```

- **AC2 — Every cite of the five archived companions in the Capabilities section is a path that exists.** Expected: exit 0, the list is empty and the count is at least 6.

  ```bash
  python3 -c 'import re,sys,os;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();c=s[s.index('"'"'## Capabilities'"'"'):s.index('"'"'## Constraints'"'"')];n=['"'"'complete-export-contract.md'"'"','"'"'tier-taxonomy.md'"'"','"'"'org-audit-precedent.md'"'"','"'"'kedro-skills-audit-report.md'"'"','"'"'vscode-kedro-decision.md'"'"'];hits=re.findall(r'"'"'\x60([^\x60\s]*(?:%s))\x60'"'"'%'"'"'|'"'"'.join(map(re.escape,n)),c);bad=[h for h in hits if not os.path.exists(h)];print(len(hits),bad);sys.exit(1 if bad or not hits else 0)'
  ```

- **AC3 — The Spec names the legacy reads, the live-sources flag, the non-conda-forge channel and the bring-up tool's exit codes.** Expected: exit 0, prints [].

  ```bash
  python3 -c 'import sys;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();need=['"'"'pyforge.atlas.live_public_sources'"'"','"'"'SelfExplainML'"'"','"'"'lasuite_bringup'"'"','"'"'PYFORGE_ATLAS_SEED_ROOT'"'"','"'"'PYFORGE_ATLAS_LOCAL_RECIPES_DIR'"'"','"'"'vuln-db'"'"','"'"'env_inspect.py'"'"','"'"'legacy_surface'"'"'];bad=[n for n in need if n not in s];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC4 — CAP-69 states all four data-root resolvers and CAP-36 no longer leans on views/.** Expected: exit 0, prints [].

  ```bash
  python3 -c 'import re,sys;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();b=lambda n:re.search(r'"'"'(?ms)^- \*\*CAP-%d — .*?(?=^- \*\*CAP-\d+ — |^## )'"'"'%n,s).group(0);bad=[w for w in ['"'"'_env_or'"'"','"'"'tools/bootstrap.py'"'"','"'"'admission'"'"','"'"'dashboard/data.py'"'"','"'"'whitespace'"'"','"'"'conf/base/catalog.yml'"'"','"'"'gate-contract.md'"'"'] if w not in b(69)];bad+=['"'"'CAP-36 names views/'"'"'] if '"'"'views/'"'"' in b(36) else [];bad+=['"'"'CAP-%d names -e local-recipes'"'"'%n for n in (50,69) if '"'"'-e local-recipes'"'"' in b(n)];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC5 — No stale test path and no A-tree literal for the member remain in the Spec.** Expected: exit 0.

  ```bash
  ! grep -q "tests/catalog/test_no_inline_io.py" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md && ! grep -q 'member is .src/shared/packages/pyforge-atlas.' _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  ```

- **AC6 — live-sources.md says where its floors can be measured.** Expected: exit 0 (the header paragraph gains the sentence that begins 'A root with no legacy database' and says it has the recorded story-close figures only).

  ```bash
  grep -q "root with no legacy database" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  ```

- **AC7 — The spine's naming row and structural seed list the five governed additions.** Expected: exit 0, prints [] (today it prints all five).

  ```bash
  python3 -c 'import sys;L=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md'"'"').read().splitlines();row=[l for l in L if l.startswith('"'"'| Pipeline/node/dataset naming'"'"')][0];seed='"'"'\n'"'"'.join(L[L.index('"'"'## Structural Seed'"'"'):L.index('"'"'## Capability → Architecture Map'"'"')]);add=['"'"'upstream_discovery'"'"','"'"'artifactory_downloads'"'"','"'"'semantic_packages'"'"','"'"'query_plane_cache'"'"','"'"'catalog_index'"'"'];bad=[a for a in add if a not in row or a not in seed];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC8 — AD-3's heading and the first sentence of its Rule no longer say the pipeline set is seven.** Expected: exit 0 (the AD-3 id and its `Binds:` line stay; only the heading words and the Rule's first sentence change).

  ```bash
  ! grep -q 'Seven fixed domain pipelines' _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md && ! grep -q 'the pipeline set is exactly spec § 5.2' _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md && grep -qE '^### AD-3 — ' _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  ```

## Boundaries & Constraints

**Always:**
- Append the memlog first (a `correction` where the tree disagrees), then render; log both self-validate passes.
- Cite an archived companion by a full path that exists.

**Never:**
- Never hand-edit `SPEC.md`; never move a file under `archive/`.
- Never name an env inline for `dashboard-dryrun` or `dashboard-serve`: cite `gate-contract.md`.
- Never change `live-sources.md` beyond its header paragraph.

</intent-contract>

## Binding

- Parent: `spec-pyforge-atlas` CAP-1, CAP-35, CAP-36, CAP-43, CAP-50..CAP-52, CAP-54..CAP-56, CAP-59, CAP-64, CAP-65, CAP-69..CAP-72; the Constraints 'One frozen exit-code convention' and 'Public sources live by default'.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-11-10 (cutover readiness) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the entry of that date and its two addenda).
- Epic: Epic 46, minted 2026-11-10 with this story.
- Ledger key: `46-2-the-atlas-capabilities-describe-the-code-that-runs`.
- Deps: S-46.1.
- Cross-station deps: none.
- Flag: none (`type: chore`: planning artifacts only, no runtime path; spec-feature-flag-governance Q1).
- Surface: `marshal-policy.toml` `[epic_surfaces]."46"`, narrowed by this spec's `surface:`.
- Minted 2026-11-10 in the atlas mint of the one cutover-readiness PR (branch `cutover-readiness-2026-11-10`); built in the same PR.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: exit 0.

**Run before the push:** the acceptance commands above, each read from its exit code.

## Auto Run Result

Status: backlog (minted 2026-11-10).

Build 2026-11-11 (wave BUILD-2; the status moves at the ledger close, not here):
- Memlog first: four `correction` entries read the 2026-11-10 entries against the tree, then the anchored script
  render of `SPEC.md` (26 anchors, each asserted once after a check-only run), then both self-validate passes logged
  as `event` entries.
- Where the tree disagreed with the logged text: `artifactory_downloads` writes five Parquet datasets and one TSV
  partition, not "4 catalog entries"; twelve pipelines are registered at the default of CAP-13's kill switch (eleven
  with it off); `wasm/build.py` expects Node 22 at `/opt/node22/bin` while the env carries nodejs 24; the workbook and
  its dated identity and Mason handoff tabs were retired by Story 23.9, so CAP-51 and CAP-52 describe the Parquet
  actuators, the `Work` bucket and the dated AOSS-Free CSV and name their tests; `pyforge.atlas.live_public_sources`
  gates only the refreshers wired from Story 34.4 on, and CAP-65's VCS and registry fetches do not read it.
- One clause no 2026-11-10 entry logged: the Constraint 'Seven closed domain pipelines' said "The pipeline set is
  fixed." against CAP-1's twelve; it gains one dated sentence (a memlog `correction` records it).
- The PRD's FR-77 carried the same A-tree member literal as CAP-69; its first consequence is amended in place, dated,
  and recorded in the PRD's reconciliation section.
- Commands: the eight acceptance commands exit 0 (AC2 prints `6 []`); `pixi run --frozen -e pyforge-atlas
  kedro-catalog-check` exits 0; the tests the restored capabilities cite exit 0 (CAP-1 pair 27 passed, CAP-51 pair 2
  passed, CAP-52 79 passed).

## Spec Change Log

- 2026-11-10: minted from the station Dream's entry of 2026-11-10 (cutover readiness) under the operator's rulings of 2026-11-10 ("Accept all", "Retire both", "Accept all, run mint"). Acceptance adjusted by the rulings: CAP-64 and CAP-65 hold to the story-close figures in `live-sources.md` (ruling 4), where the plan left 'what a root with no legacy database is held to' as an operator question; the memlog entries were written at the mint.

## Review Triage Log

- (none yet)
