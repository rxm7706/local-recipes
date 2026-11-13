---
title: '57.1: The doctor Spec''s markers and text say what the code does'
type: 'docs'
created: '2026-11-10'
status: 'done'
story: 57-1-the-doctor-spec-s-markers-and-text-say-what-the-code-does
spec: spec-pyforge-doctor
difficulty: 'heavy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: docs-only   # prose and planning artifacts only; the capabilities it writes down are existing code (spec-feature-flag-governance Q2; roster list)
surface:
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/glossary.md'
  - 'src/shared/packages/pyforge-doctor/README.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-24-2-an-import-linter-contract-catches-the-class-structurally.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-19-1-the-suite-watched-set-matches-the-channel-catalog-and-upstream-follows-recipe-registry/.memlog.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-19-1-the-suite-watched-set-matches-the-channel-catalog-and-upstream-follows-recipe-registry.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Spec text is wrong where the code is right (decision D4; no code changes).

**Approach:** Write the amendments as memlog entries, one per group, then re-derive once: markers by mapping each CAP to its stories through `rekey-2026-09-17.md` and the epics' FR/AD lines, reading the ledger key and confirming the named code or document exists; the closed one-time campaigns retire (operator ruling of 2026-11-10); CAP-33, CAP-50, CAP-53 retire with the reason in the intent; headings cut at a period or at 80 characters are restored; Why, NFR-1, the AD-2 Constraint, the first Non-goal and Open Questions 1 and 3 say what the code does.

Ledger key: `57-1-the-doctor-spec-s-markers-and-text-say-what-the-code-does`.
Type / Effort / Deps: docs / L / —.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-96** — `doctor flags kill-switch` is Doctor's one actuator (minted 2026-11-10; the verb stays in Doctor by ruling).
- **`spec-pyforge-doctor` CAP-98** — the platform's policy suite is judged by Doctor; **CAP-99** — a config key set at two paths is named (both minted 2026-11-10, existing code).
- **`spec-pyforge-doctor` CAP-93** — gains the reintroduction-gate sentence (dashboard-drift and check-layout measure absence).

## Boundaries & Constraints

**Always:**
- Marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it: `(ready <date>)`, `(shipped <date>)`, `(retired <date>[: <reason>])`, semicolon qualifiers allowed; no `(unbuilt)` token.
- The station Spec's frontmatter stays `status: ready` (CHAIN-STANDARD section 4).
- Keep every amended capability's heading unless the heading was cut (CAP-45, CAP-47, CAP-65 and any cut at a period or at 80 characters), so no ledger heading drifts silently.

**Never:**
- Never change code in this story; never stamp (Story 58.4 stamps once).
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — Every capability definition carries exactly one dated marker in the section 4 grammar, and no in-progress or draft one.** Expected: prints `100 []`, exit 0 (93 capabilities plus CAP-94 to CAP-100; 40 fail this today).

  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md',encoding='utf-8').read();d=[l for l in t.splitlines() if re.match(r'^- \*\*CAP-\d+ \u2014 ',l)];bad=[l[:14] for l in d if len(re.findall(r'\((?:ready|shipped|retired) \d{4}-\d{2}-\d{2}(?:: [^;)]+)?(?:; [^)]+)?\)',l))!=1 or re.search(r'\((?:in-progress|draft) \d',l)];print(len(d),bad);sys.exit(1 if bad or len(d)!=100 else 0)"
  ```

- **AC2 — Only this change's capabilities still read ready, and exactly the ruled set reads retired.** Expected: exit 0; prints the ready list (a subset of 94..100) and the 23 retired ids (CAP-33, CAP-50, CAP-53 and the twenty closed one-time campaigns).

  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md',encoding='utf-8').read();r=sorted(int(m) for m in re.findall(r'(?m)^- \*\*CAP-(\d+) .*\(ready \d',t));x=sorted(int(m) for m in re.findall(r'(?m)^- \*\*CAP-(\d+) .*\(retired \d{4}-\d{2}-\d{2}[:)]',t));print(r,x);sys.exit(0 if set(r)<=set(range(94,101)) and x==[33,37,38,39,40,41,45,46,47,49,50,51,52,53,55,56,60,61,65,66,67,68,70] else 1)"
  ```

- **AC3 — The closed one-time campaigns read the ruled marker.** Expected: exit 0; prints CAP-37..CAP-41, CAP-45..CAP-47, CAP-49, CAP-51, CAP-52, CAP-55, CAP-56, CAP-60, CAP-61, CAP-65..CAP-68 and CAP-70.

  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md',encoding='utf-8').read();c=sorted(int(m) for m in re.findall(r'(?m)^- \*\*CAP-(\d+) .*\(retired 2026-11-10: closed one-time campaign\)',t));print(c);sys.exit(0 if c==[37,38,39,40,41,45,46,47,49,51,52,55,56,60,61,65,66,67,68,70] else 1)"
  ```

- **AC4 — The Spec no longer denies what the CLI ships.** Expected: exit 1 (no match).

  ```bash
  git grep -nE 'three verbs|no `--fix`/actuator exists|-e local-recipes' -- _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  ```

- **AC5 — No success clause depends on a deleted path.** Expected: prints `[]`, exit 0.

  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md',encoding='utf-8').read();b=[l[:70] for l in t.splitlines() if '**success:**' in l and re.search(r'docs/specs/|gists/INDEX\.md|docs/dashboard/kedro-viz|--specs',l)];print(b);sys.exit(1 if b else 0)"
  ```

- **AC6 — CAP-93 says what `every` means and names the reintroduction gates.** Expected: each prints 1 or more.

  ```bash
  grep -c 'ten FR-15 names' _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md && grep -c 'reintroduction gate' _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  ```

- **AC7 — The two story specs, the README and the DW row agree with the ledger.** Expected: the two git grep exit 1 (no match); the last prints 1.

  ```bash
  git grep -nE "^status: 'in-review'" -- _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-24-2-*.md _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-*.md; git grep -nE '95 stories|22 epics|the 22 detector' -- src/shared/packages/pyforge-doctor/README.md; grep -A12 '^### DW-doctor-egm-2026-11-05-1:' _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md | grep -c 'status: closed'
  ```

- **AC8 — Doctor's chain detectors raise no FAIL about the doctor chain.** Expected: exit 0; each line prints an empty list.

  ```bash
  for s in fr-without-cap status-body-consistency capability-effect; do pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources $s --json > "${TMPDIR:-/tmp}/doc-$s.json"; python3 -c "import json,os,sys;f=json.load(open(os.environ.get('TMPDIR','/tmp')+'/doc-$s.json'));b=[x['check'] for x in f if x['status']=='fail' and 'pyforge-doctor' in json.dumps(x)];print('$s',b);sys.exit(1 if b else 0)" || exit 1; done
  ```

- **AC9 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-57-1-*.md)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-96, CAP-98, CAP-99 (minted 2026-11-10); markers and text of CAP-11, CAP-17, CAP-20, CAP-26..CAP-81, CAP-82..CAP-93 amended; FR-29 ← CAP-96, FR-30 ← CAP-98, FR-31 ← CAP-99.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 57, minted with this story.
- Ledger key: `57-1-the-doctor-spec-s-markers-and-text-say-what-the-code-does` (`backlog`).
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."57"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- Spec text is wrong where the code is right (D4; no code changes). The mint already wrote CAP-94 to CAP-100 and the CAP-59, CAP-87 and CAP-93 amendments; this story writes the rest.
- Groups: (1) `(in-progress 2026-09-17)` becomes `(shipped <date>)` for CAP-26..CAP-32, CAP-34..CAP-36, CAP-42..CAP-44 and CAP-71 (the date the last realizing story reached done, or 2026-09-17 when all were done at the fold); (2) `(draft 2026-09-17)` becomes `(shipped <date>)` for CAP-72..CAP-76 (Stories 21.12 to 21.16 are done; CAP-74 keeps its measured-and-rejected outcome); (3) stale `(ready ...)` becomes `(shipped <date>)` for CAP-48, CAP-54, CAP-69 and CAP-77..CAP-81; (4) CAP-82..CAP-93 each gain `(shipped <date of its last story>)`; (5) the closed one-time campaigns CAP-37..CAP-41, CAP-45..CAP-47, CAP-49, CAP-51, CAP-52, CAP-55, CAP-56, CAP-60, CAP-61, CAP-65..CAP-68 and CAP-70 read `(retired 2026-11-10: closed one-time campaign)` (operator ruling of 2026-11-10; their intent says what the campaign closed: CAP-51's says docs/intake/README.md routes intake and the gists index it once named is gone; CAP-66, CAP-67, CAP-68 and CAP-70 say their ledgers live in an archived Dream); (6) CAP-33, CAP-50 and CAP-53 read exactly `(retired 2026-08-21)`, `(retired 2026-10-10)` and `(retired 2026-10-15)`, the reason in the intent (CAP-33 split out to CAP-10 on 2026-08-21; docs/specs/ deleted by `070f73edad`; docs/dashboard/kedro-viz/ deleted by `87e8e58c3a`), and the success clause stops asserting the deleted path.
- Text: headings of CAP-45, CAP-47, CAP-65 (and any cut at a period or at 80 characters) restored to a whole clause; bare pre-fold `CAP-n` inside the folded CAPs re-keyed through `rekey-2026-09-17.md` (CAP-45's `CAP-4..7` is CAP-38..CAP-41); CAP-17's success states the behaviour and names its fixture test; CAP-69 says what the code measures (30 pixi.toml commits since a ledger section's last touch, read from archive/docs/dreams/pixi-candidate-currency.md); CAP-11, CAP-20, CAP-46: `-e local-recipes` becomes `-e pyforge-guild`, and CAP-20 names `chain-layers-audit`; CAP-81 names the `frontmatter-duplicate-keys` source (Story 42.1); CAP-93 gains one sentence: dashboard-drift and check-layout are reintroduction gates for Guildhall files A retired (their OK on any tree measures absence), and whether B carries them is the ledger row's mode under modes.md's written rules.
- Why, Constraints, Non-goals, Open Questions: five verbs and the sources dispatcher, not three; NFR-1 and the first Non-goal name the two sanctioned writes (the `--surface` file, CAP-96); the AD-2 Constraint binds `doctor` and `python -m pyforge.doctor.sources`, not the aggregate (AD-15); Open Questions 1 and 3 close with the code's answer (every env-hygiene finding is WARN; the surface is a file).
- The `(shipped ...)` markers add no capability-effect finding (that check keys on Spec frontmatter status shipped/realized, `capability_effect.py:53`). The ledger modes of the retired campaigns are control-plane's (steward Stories 121.3 and 121.7), not this story's.
- The DW-doctor-egm-2026-11-05-1 row closes here as its own fix says (`every` means the ten FR-15 names), citing the mint's CAP-93 amendment. The README replaces its counts with a pointer to contract.md.
- Scribe's request: the story-level folder `spec-19-1-.../` holds a `.memlog.md` and no SPEC.md; its three lines fold into the story spec of the same name as a dated note and the folder goes (no baseline key names it).
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.

## Gate findings (build, BUILD-1)

- 2026-11-11, `pixi run -e pyforge-marshal pyforge-marshal-test`: `test_tracked_story_specs_carry_each_top_level_frontmatter_key_once` reads `spec-19-1-.../.memlog.md`, which `git ls-files` still lists after this story removed it on disk. Transient, no fix: staging the deletion in the wave commit clears it; a probe of the same logic over the remaining files finds 0 offenders.
