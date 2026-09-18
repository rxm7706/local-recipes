---
title: "Story 14.9: The apply retires deprecation shims on purpose (--no-shims)"
type: 'feature'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
baseline_revision: 'e16e38bc53239d219e0a6074951b85629e02b750'
context: []
warnings: [oversized]
deferred: []
# Both items originally deferred here (2026-09-06, first review pass) are resolved as of the
# 2026-09-06 follow-up pass, not carried forward:
#   1. "--no-shims + a nonempty --pin list untested" -- CLOSED: the follow-up pass added
#      test_apply_no_shims_argv_order_holds_with_custom_module_pins, exercising exactly this.
#   2. "_shim_retirement_blockers's default loops_home branch untested" -- MOOT:
#      _shim_retirement_blockers was removed entirely in the follow-up pass (CAP-9's
#      harness/loop-home refusal check had no valid target; see the Spec Change Log above).
---

<intent-contract>

## Intent

**Problem:** `apply_bmad_core_upgrade` has no way to deliberately retire the 21 deprecation
shims (20 `v6-shims` + `bmad-generate-project-context`) the 6.12.0 install still carries
(`installShims: true`). Retiring them today would require a hand-run `bmad-method` invocation
outside steward's own deliberate-apply machinery (no argv support, no pre-flight preview, no
refusal guard against stranding a loop home still on the retired `bmad-dev-auto` id).

**Approach:** Add a `--no-shims` flag that appends `--no-shims` to the installer argv after
`--modules`; add a catalog-declared `shims_to_retire` list surfaced as a new `PreflightReport`
field (always computed, independent of the flag) previewing what a retirement run would remove;
and add a NEW apply-time-only refusal (gated on `no_shims=True`) that reports — never edits — two
foreign-owned surfaces still emitting the retired `bmad-dev-auto` skill id: the marshal harness's
embedded `policy.toml` template and any already-rendered loop-home `policy.toml`. The existing
legacy-custom-name refusal (`refuse_legacy_custom`, trap 2) already blocks ANY apply unconditionally
and needs no change — this story only adds unit tests proving it also holds under `--no-shims`.
This story does NOT run the real `steward upgrade bmad-core --apply --no-shims` command against
this repo's actual installed core — that live run is a separate, later step gated on marshal
Story 30.5 landing first (this repo's harness/loop-homes still emit `bmad-dev-auto` today, so a
real run right now would correctly refuse).

## Boundaries & Constraints

**Always:**
- `--no-shims` inserts literally as the single token `--no-shims` in the installer argv,
  positioned immediately after `--modules <csv>` and before any `--pin` pairs.
- The `shims_to_retire` pre-flight list is computed unconditionally (whether or not `--no-shims`
  is passed) — it is a preview, not a trap requiring remediation, so it must NOT be added to
  `PreflightReport.trap_ids`.
- The harness-template / loop-home-policy refusal check only runs when `no_shims=True`; it never
  runs on a plain (non-`--no-shims`) apply.
- All new tests use temp-dir fixtures and an injected/mocked installer runner + an injected/
  overridable `loops_home` — never touch this repo's real `~/.bmad-loops` or the real
  `harness_bmadloop.py` module content via a live filesystem scan of the actual current state.

**Never:**
- Do not actually execute `steward upgrade bmad-core --apply --no-shims` against this repo.
- Do not edit `src/shared/packages/pyforge-marshal/**` or any `~/.bmad-loops/*/.bmad-loop/policy.toml`
  — both are foreign surfaces, reported only (mirrors CAP-3/CAP-5's existing foreign-surface stance).
- Do not touch `refuse_legacy_custom` itself — it already covers trap 2 unconditionally.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Argv shape | `--apply --no-shims` on a fixture repo/catalog | `ApplyReport.installer_cmd` contains `--no-shims` right after `--modules <csv>`, before any `--pin` pair | N/A |
| Pre-flight preview | Fixture catalog with `shims_to_retire: [...]`, fixture skill-manifest.csv containing a subset | `PreflightReport.shims_to_retire` == the catalog∩installed intersection, sorted; NOT in `trap_ids` | N/A |
| Same-version retirement is a real diff | `target_version == installed_version`, fake installer deletes a fixture shim dir under `--no-shims` | `ApplyReport.zero_diff is False` (a real diff, not trap 12) | N/A |
| Legacy custom halts even with `--no-shims` | A `_bmad/custom/bmad-dev-auto.toml` fixture file present, `no_shims=True` | `apply_bmad_core_upgrade` raises `UpgradeError` (trap 2), before any branch exists | Refusal names the file |
| Harness template still emits the retired id | Fixture repo copy of `harness_bmadloop.py`-shaped file containing `skill = "bmad-dev-auto"`, `no_shims=True` | Refuses with a named reason citing the file path; no branch created | N/A |
| Loop-home policy still emits the retired id | Fixture `loops_home/<home>/.bmad-loop/policy.toml` containing `skill = "bmad-dev-auto"`, `no_shims=True` | Refuses with a named reason citing the home name; no branch created | N/A |
| Both blockers clear | Neither fixture surface names `bmad-dev-auto`, `no_shims=True` | Apply proceeds normally (argv carries `--no-shims`) | N/A |
| Flag off | `no_shims=False` (default) | Argv unchanged from today; no harness/policy scan runs at all | N/A |

</intent-contract>

## Code Map

All changes land in `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` unless
noted. The file is ~4250 lines; anchor by symbol name, not line number.

- **Trap constants** (near the existing `TRAP_...` block, e.g. after `TRAP_LOCAL_CUSTOMIZATION = 16`):
  no new trap constant is needed. The `shims_to_retire` preview is informational (never added to
  `trap_ids`); the harness/loop-home refusal reuses the same `UpgradeError`-raising pattern as
  `refuse_legacy_custom` without a dedicated trap id (it is a pre-apply guard, not a `PreflightReport`
  finding list).
- **`PreflightReport`** (dataclass, ends today with `local_customizations`): append ONE new field,
  last, per the file's own append-only-for-positional-compat convention:
  `shims_to_retire: tuple[str, ...] = ()`.
- **`build_preflight_report`**: `catalog` and `installed_skills = _read_installed_skill_names(repo)`
  are ALREADY local variables in this function (confirmed at the top of its body). Add, near where
  `custom_modules = _custom_module_findings(repo, catalog)` is computed:
  `shims_to_retire = tuple(sorted(name for name in (catalog.get("shims_to_retire") or []) if name in installed_skills))`.
  Pass `shims_to_retire=shims_to_retire` into the returned `PreflightReport(...)` call. Do **not**
  append anything to `trap_ids` for this.
- **`format_preflight`**: after the existing
  `lines.extend(["", "## Local customizations (installer-owned files edited in place)"])` block
  and before `if report.notes:`, add:
  ```python
  lines.extend(
      ["", f"## Shims to retire (--no-shims candidates) [{len(report.shims_to_retire)}]"]
  )
  if not report.shims_to_retire:
      lines.append("(none)")
  for name in report.shims_to_retire:
      lines.append(f"- {name}")
  ```
- **New module-level constant** (near the other `_..._RELATIVE_PATH` constants, e.g. right after
  `_SKILL_MANIFEST_RELATIVE_PATH`):
  `_MARSHAL_HARNESS_TEMPLATE_RELATIVE_PATH = Path("src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py")`
  and `_RETIRED_DEV_SKILL_PATTERN = re.compile(r'skill\s*=\s*"bmad-dev-auto"')` (`re` is already
  imported at the top of this module).
- **New functions**, placed near `refuse_legacy_custom` (before `create_review_branch`):
  - `_shim_retirement_blockers(repo: Path, *, loops_home: Path | None = None) -> tuple[str, ...]`
    — report-only enumeration, never edits anything (both sites are marshal-owned, not steward's).
    Body: `blockers: list[str] = []`; `harness = repo / _MARSHAL_HARNESS_TEMPLATE_RELATIVE_PATH`; if
    `harness.is_file()` and `_RETIRED_DEV_SKILL_PATTERN.search(harness.read_text(encoding="utf-8"))`:
    append `f"{harness.relative_to(repo)} still emits bmad-dev-auto in its policy.toml template"`.
    `home_root = loops_home if loops_home is not None else Path.home() / ".bmad-loops"`; reuse the
    ALREADY-DEFINED `_list_loop_homes(home_root)` helper (defined later in this module — fine, Python
    resolves module globals at call time, not definition order); for each `home` in that list:
    `policy = home / ".bmad-loop" / "policy.toml"`; if `policy.is_file()` and the same pattern
    matches its text: append `f"loop home {home.name}'s rendered policy.toml still names bmad-dev-auto"`.
    Return `tuple(blockers)`.
  - `refuse_shim_retirement_not_ready(repo: Path, *, loops_home: Path | None = None) -> None` —
    `blockers = _shim_retirement_blockers(repo, loops_home=loops_home)`; if empty, return; else
    `raise UpgradeError("refuse --no-shims: the following foreign-owned surfaces still emit the "
    "retired bmad-dev-auto skill id (reported, never edited by steward) — " + "; ".join(blockers))`.
- **`apply_bmad_core_upgrade`**: add two new keyword parameters at the end of the signature,
  `no_shims: bool = False, loops_home: Path | None = None`. Immediately after the existing
  `refuse_legacy_custom(preflight)` call, add:
  ```python
  if no_shims:
      refuse_shim_retirement_not_ready(repo, loops_home=loops_home)
  ```
  (before any branch exists — same placement discipline as the existing refusal.) In the
  `installer_cmd = (...)` tuple construction, insert a `--no-shims` element (as a 1-tuple spread,
  matching the existing `*(part for pin in pins for part in ("--pin", pin))` idiom) immediately
  after `modules_csv` and before that pin-spread: `*(("--no-shims",) if no_shims else ()),`. In the
  `notes` list construction right after the existing `installer argv:` note line, add, only when
  `no_shims`: `notes.append("--no-shims requested: shim retirement is judged by the same trap-12 "
  "zero-diff refusal as any other apply — a same-version run that actually removes shim "
  "directories is a real diff, never treated as a no-op")`.
- **`UpgradeDuty._bmad_core`**: read two new namespace attributes the same way existing ones are
  read: `no_shims = bool(getattr(ns, "no_shims", False))` and
  `loops_home = Path(ns.loops_home) if getattr(ns, "loops_home", None) else None`. Thread both into
  the existing `apply_bmad_core_upgrade(...)` call (only reached when `do_apply` is true — the
  pre-flight branch needs no change, since `shims_to_retire` is already unconditional inside
  `build_preflight_report`).
- **`src/pyforge/steward/cli.py`, `_add_upgrade_subparsers`**: on the `bmad_core` subparser, add
  two arguments, placed near the existing `--installer`/`--branch` arguments:
  `bmad_core.add_argument("--no-shims", action="store_true", help="CAP-9: retire the installed "
  "core's deprecation shims on this apply (installShims: false); refused if a legacy-name "
  "_bmad/custom/** override exists (trap 2) or a foreign harness/loop-home policy still names "
  "the retired bmad-dev-auto skill id (reported, never edited)")` and
  `bmad_core.add_argument("--loops-home", default=None, metavar="DIR", help="override "
  "~/.bmad-loops when checking rendered policy.toml files for --no-shims readiness (tests)")`.
- **`src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.12.0.yaml`**:
  add a new top-level `shims_to_retire:` list (21 entries) right after the existing `skill_adds: []`
  block, with a one-line comment naming the source (skill-manifest.csv `v6-shims` paths + the
  `lifecycle: shim` frontmatter on `bmm-skills/plan/bmad-generate-project-context/SKILL.md`):
  `bmad-checkpoint-preview, bmad-create-architecture, bmad-create-prd, bmad-create-story,
  bmad-dev-auto, bmad-dev-story, bmad-document-project, bmad-domain-research,
  bmad-editorial-review, bmad-editorial-review-prose, bmad-editorial-review-structure,
  bmad-edit-prd, bmad-generate-project-context, bmad-market-research, bmad-quick-dev,
  bmad-review-adversarial-general, bmad-review-edge-case-hunter, bmad-review-verification-gap,
  bmad-sprint-status, bmad-technical-research, bmad-validate-prd` (verified count: 21, against
  the installed `_bmad/_config/skill-manifest.csv` on this branch).

## Follow-up Correction Code Map (2026-09-06, supersedes the harness/loop-home portions above)

Everything above this section is the ORIGINAL Code Map, kept verbatim as the historical record
(some of it now describes code being removed). This section is the actual instruction for the fix.

- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` — **remove**:
  `_MARSHAL_HARNESS_TEMPLATE_RELATIVE_PATH`, `_RETIRED_DEV_SKILL_PATTERN` (both module-level
  constants), `_shim_retirement_blockers`, `refuse_shim_retirement_not_ready` (both functions,
  entirely). In `apply_bmad_core_upgrade`: remove the `loops_home: Path | None = None` parameter
  and the `if no_shims: refuse_shim_retirement_not_ready(repo, loops_home=loops_home)` call site
  (delete the `if` block; do NOT remove the `no_shims` parameter itself or the argv insertion). In
  `UpgradeDuty._bmad_core`: remove the `loops_home = Path(ns.loops_home) if ...` line and the
  `loops_home=loops_home` kwarg passed into `apply_bmad_core_upgrade(...)` (keep `no_shims=no_shims`).
  Bump the module docstring `"""CAP-2+3+6+7 deliberate apply..."""` to
  `"""CAP-2+3+6+7+8+9 deliberate apply..."""` and add a short CAP-9 paragraph (mirror the existing
  CAP-7 paragraph's style: one sentence on what `--no-shims` does, one on the sole refusal being
  trap-2 legacy-custom).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — **remove** the `--loops-home`
  `add_argument` call entirely. Reword the `--no-shims` help text to drop the "or a foreign
  harness/loop-home policy still names..." clause — it should read only about `installShims: false`
  and the trap-2 legacy-custom refusal.
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py` — **delete** these 3
  tests entirely: `test_apply_no_shims_refuses_when_harness_template_names_retired_id`,
  `test_apply_no_shims_refuses_when_loop_home_policy_names_retired_id`,
  `test_apply_no_shims_plain_apply_never_scans_harness_or_loop_home`. **Rewrite** (drop the
  `loops_home=`/`loops.mkdir()` fixture wiring; keep every other assertion unchanged) these 5:
  `test_apply_no_shims_argv_carries_flag_after_modules_before_pins`,
  `test_apply_no_shims_same_version_target_is_a_real_diff_not_zero_diff`,
  `test_apply_no_shims_both_surfaces_clear_proceeds` (also rename — "both surfaces" no longer
  exists as a concept; e.g. `test_apply_no_shims_proceeds_normally`),
  `test_cli_apply_help_names_no_shims_and_loops_home_flags` (rename, e.g.
  `test_cli_apply_help_names_no_shims_flag`; drop the `--loops-home` assertion),
  `test_cli_apply_no_shims_flag_reaches_apply` (drop `--loops-home` from the CLI argv list and its
  `loops.mkdir()` fixture). Update the module docstring (~lines 19-24) to drop the sentence about
  "a NEW apply-time-only refusal blocks when a foreign-owned harness template or rendered
  loop-home `policy.toml`..." — replace with one sentence noting the sole `--no-shims` refusal is
  the pre-existing trap-2 legacy-custom check. **Add** one new test:
  `test_apply_no_shims_argv_order_holds_with_custom_module_pins` — build a fixture combining
  `no_shims=True` with a pin-bearing custom module (reuse `_custom_module_fixture(tmp_path,
  pin="v2.1.0")`, the same helper `test_apply_custom_module_catalog_pin_lands_on_core_argv` uses),
  and assert the full `installer_cmd` tuple shows `--modules <csv>`, then `--no-shims`, then
  `--pin skf=v2.1.0`, in that exact order.
- Do **NOT** touch: `6.12.0.yaml`'s `shims_to_retire:` list, `PreflightReport.shims_to_retire`,
  `build_preflight_report`'s catalog∩installed computation, `format_preflight`'s rendered
  section, any of the 6 tests in `test_upgrade_preflight.py`, or `refuse_legacy_custom` (trap 2)
  and its own test (`test_apply_no_shims_legacy_custom_still_halts_before_branch`) — none of these
  depend on the false premise.

## Tasks & Acceptance

**Execution:**
- `upgrade.py` -- implement every symbol above (`PreflightReport.shims_to_retire`,
  `build_preflight_report` computation, `format_preflight` section, the two new module constants,
  `_shim_retirement_blockers` / `refuse_shim_retirement_not_ready`, `apply_bmad_core_upgrade`'s
  `no_shims`/`loops_home` params + argv + refusal + note, `UpgradeDuty._bmad_core` plumbing) --
  delivers CAP-9.
- `cli.py` -- add `--no-shims` and `--loops-home` to the `bmad-core` subparser -- CLI surface.
- `data/bmad_core_releases/6.12.0.yaml` -- add `shims_to_retire:` (21 entries) -- catalog-declared
  fact, mirrors `legacy_custom_names`/`removals`/`skill_renames`'s existing pattern.
- `tests/unit/test_upgrade_preflight.py` -- one test per I/O-matrix pre-flight row (argv-independent
  rows: pre-flight preview intersection, empty when catalog/installed disjoint, never in `trap_ids`).
- `tests/unit/test_upgrade_apply.py` -- one test per remaining I/O-matrix row: argv shape (extend
  `_fake_installer_script` with a `no_shims: bool = False` kwarg that, when true, asserts
  `"--no-shims" in sys.argv` and deletes one fixture shim-shaped file to produce a real diff);
  same-version-is-a-real-diff (`zero_diff is False`); legacy-custom-halts-under-no-shims (reuse the
  existing `with_legacy_custom=True` repo fixture, assert `UpgradeError` with `no_shims=True`);
  harness-template-blocks (write a fixture file at the SAME relative path containing
  `skill = "bmad-dev-auto"`, assert refusal names it); loop-home-policy-blocks (fixture
  `tmp_path/"loops"/"home1"/".bmad-loop"/"policy.toml"` containing the same line, pass
  `loops_home=tmp_path/"loops"`, assert refusal names `home1`); both-clear-passes-through (neither
  fixture surface present, `no_shims=True`, apply succeeds and argv carries `--no-shims`); CLI flag
  plumbing test (`--no-shims`/`--loops-home` parsed and reach `apply_bmad_core_upgrade`).

**Acceptance Criteria:**
- Given `--apply --no-shims` against a fixture repo/catalog, when the fake installer runs, then
  `ApplyReport.installer_cmd` contains `--no-shims` immediately after the `--modules` pair and
  before any `--pin` pair.
- Given a fixture catalog's `shims_to_retire` list and a fixture skill-manifest.csv, when
  `build_preflight_report` runs (no `--apply` needed), then `PreflightReport.shims_to_retire`
  equals the sorted catalog∩installed intersection and is absent from `trap_ids`.
- Given a same-version target with a fake installer that deletes a fixture shim path under
  `--no-shims`, when `--apply` runs, then `ApplyReport.zero_diff is False`.
- Given a `_bmad/custom/bmad-dev-auto.toml` fixture and `no_shims=True`, when `apply_bmad_core_upgrade`
  runs, then it raises `UpgradeError` before any branch exists (trap 2, unchanged mechanism).
- Given a fixture harness-template file or a fixture loop-home policy.toml naming the retired
  `bmad-dev-auto` skill id, when `--apply --no-shims` runs, then it raises `UpgradeError` naming
  the specific blocking site, before any branch exists.
- Given `pixi run -e pyforge-steward pyforge-steward-test` from
  `src/shared/packages/pyforge-steward`, when run after this story, then it is green.

## Spec Change Log

### 2026-09-06 — bad_spec finding: the harness/loop-home refusal check has no valid target
**Triggering finding:** during a SIBLING story (marshal 30.5), the harness-template rename this
refusal check exists to eventually accept was found FALSE — `bmad_loop`'s `DevPolicy.skill` is a
PERMANENT internal adapter discriminator (`DEV_SKILLS = {"bmad-dev-auto"}`, hard-validated by the
installed package) that must read `"bmad-dev-auto"` forever, on every era; the skill actually
invoked is resolved separately from disk at runtime. This means `_shim_retirement_blockers`'s
scan of the marshal harness template and every rendered loop-home `policy.toml` for this exact
literal will ALWAYS find a match, forever, by design — the check has no valid target and would
refuse `--no-shims` permanently. Checked for a possibly-misapplied-but-salvageable signal first
(per operator direction): traced `bmad_loop`'s own `Engine._dev_skill()` /
`install.dev_primitive_or_default` resolution and confirmed it already gracefully handles a
missing/renamed skill on disk via its own preflight, entirely independent of steward — no
substitute check exists for steward to add.

**What was amended:** `<intent-contract>` is left unmodified (historical record of the original,
now-known-wrong ask). Outside it: the Code Map, Tasks & Acceptance, and I/O & Edge-Case Matrix are
corrected below to describe REMOVING `_shim_retirement_blockers`, `refuse_shim_retirement_not_ready`,
the `_MARSHAL_HARNESS_TEMPLATE_RELATIVE_PATH`/`_RETIRED_DEV_SKILL_PATTERN` constants, the
`loops_home` parameter (from `apply_bmad_core_upgrade` and `UpgradeDuty._bmad_core`), and the
`--loops-home` CLI flag — plus fixing the 8 tests and 2 docstrings/help-texts that depended on the
false premise, per the follow-up review's exhaustive mapping below.

**Known-bad state avoided:** leaving this check in place would make `--no-shims` refuse forever on
this repo's own machine (and every other), even after this exact story's own Story 30.5 sibling
correctly leaves the harness template untouched — a permanent, silent dead end with no operator
recourse short of reading steward's source.

**KEEP:** the `no_shims: bool = False` parameter, the installer-argv insertion
(`*(("--no-shims",) if no_shims else ()),` right after `--modules`, before any `--pin` pairs), the
trap-12 zero-diff note, the entire `shims_to_retire` preview machinery (catalog list,
`PreflightReport` field, `build_preflight_report` computation, `format_preflight` rendering), and
the pre-existing unconditional trap-2 `refuse_legacy_custom` check — none of these depend on the
false premise and all must survive this correction exactly as they are.

## Review Triage Log

### 2026-09-06 — Review pass (Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Intent Alignment Auditor)
- verdicts: 21 findings — high 0, medium 5, low 13, false 3, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter: both memlog entries claimed "15 new tests (94 -> 108)", an internal arithmetic inconsistency (15 new tests from a 94 baseline is 109, not 108) — verified true. Fixed: corrected both memlogs' counts to 94 -> 109 and fixed the preflight itemization.
  - `[low]` `[patch]` Intent Alignment Auditor: same underlying memlog count error as the Blind Hunter row above, reported independently ("94 -> 108" is +14, not the stated "15 new tests") — verified true, same fix applied.
  - `[low]` `[patch]` Blind Hunter: `test_shims_to_retire_absent_from_real_612_catalog_stays_none_by_default` actually loads the 6.11.0 catalog (pre-CAP-9, no `shims_to_retire` key), not 6.12.0 — verified true (its own docstring even said "6.11.0 catalog"). Fixed: renamed to `test_shims_to_retire_absent_key_defaults_to_empty`.
  - `[low]` `[patch]` Intent Alignment Auditor: same naming/docstring slip reported independently ("test name says real_612_catalog... actually exercises 6.11.0") — verified true, same fix applied.
  - `[medium]` `[patch]` Blind Hunter: `test_apply_no_shims_same_version_target_is_a_real_diff_not_zero_diff` didn't isolate its own claim — the fixture's unconditional `updated.txt` writes already guarantee a non-empty diff regardless of whether the `no_shims`-gated shim deletion ran at all — verified true by reading `_fake_installer_script`. Fixed: the test now asserts the fixture shim directory is actually gone and named in `changed_paths`, proving the deletion produced the diff.
  - `[medium]` `[patch]` Verification Gap Reviewer: two tests (`test_apply_no_shims_argv_carries_flag_after_modules_before_pins`, the same-version test above) called `apply_bmad_core_upgrade(no_shims=True)` without `loops_home=`, falling through to the real, unmocked `Path.home() / ".bmad-loops"` — verified true by reading `_shim_retirement_blockers`'s default and confirming neither fixture repo contains the marshal harness path. On a machine with real loop-homes still naming `bmad-dev-auto` (documented true of the dev machine, per this story's own memlog), these tests would raise `UpgradeError` before reaching their assertions. Fixed: both now pass `loops_home=tmp_path / "loops"` (created empty).
  - `[medium]` `[patch]` Verification Gap Reviewer: no test asserts anything about the REAL packaged 6.12.0.yaml's `shims_to_retire` list content — every test uses a synthetic fixture catalog — verified true, mirrors the exact gap Story 46.7's `test_real_catalog_pins_skf_v2_1_0` precedent closed for the `skf` pin. Fixed: added `test_real_612_catalog_shims_to_retire_has_21_entries`.
  - `[medium]` `[patch]` Intent Alignment Auditor: same real-catalog coverage gap reported independently ("no test pins the real 6.12.0 catalog's 21-entry list") — verified true, same fix applied.
  - `[low]` `[patch]` Edge Case Hunter: `harness.read_text()`/`policy.read_text()` in `_shim_retirement_blockers` can raise on non-UTF-8 bytes or a file vanishing mid-read, surfacing as an unhandled exception instead of a clean refusal — verified true (no guard existed). Fixed: wrapped both in `try/except (OSError, UnicodeDecodeError)`, failing closed (treated as a blocker) rather than silently passing.
  - `[medium]` `[patch]` Edge Case Hunter: an explicit `--loops-home` pointing at a nonexistent path silently reports zero blockers (`_list_loop_homes` returns `[]` for a non-dir) — verified true; a typo in an operator override would silently bypass the whole safety check. Fixed: `_shim_retirement_blockers` now raises `UpgradeError` when `loops_home is not None and not loops_home.is_dir()`; the default (`None`) path is untouched and stays silent.
  - `[low]` `[patch]` Edge Case Hunter: `shims_to_retire`'s catalog list is not deduplicated before sorting — a duplicate name would render twice — verified true, trivial fix. Fixed: `sorted(...)` now sorts a set comprehension.
  - `[low]` `[defer]` Blind Hunter: no test exercises `--no-shims` together with a non-empty `--pin` list, so the documented "before any `--pin` pairs" ordering claim is untested against a real pin — verified true (every Story 14.9 test targets 6.11.0, whose catalog has zero pins). Deferred: closing it needs a `_custom_module_fixture`-shaped repo combined with `no_shims=True`, more than a direct/trivial addition; not worth blocking this story for an ordering claim that's still true by direct code inspection (`upgrade.py`'s tuple construction literally places the pin-spread after the `--no-shims` spread).
  - `[low]` `[defer]` Blind Hunter: the default `loops_home=None` → real `Path.home()/".bmad-loops"` resolution branch is never exercised by a test (would need monkeypatching `Path.home`) — verified true. Deferred: low value, the branch is a one-line ternary with no logic to regress.
  - `[low]` `[reject]` Edge Case Hunter: relative `--loops-home` resolves against CWD, not the repo root — verified true as a mechanical fact, but refuted as a defect: `UpgradeDuty._bmad_core` reads `Path(ns.loops_home)` verbatim with no `.resolve()`/repo-anchoring, identical to how the pre-existing `--loops-home` flag on the `pin-fan-out` subcommand already behaves in this same file — not a regression or an inconsistency 14.9 introduced.
  - `[low]` `[reject]` Blind Hunter: `--no-shims`/`--loops-home` silently no-op when `--apply` isn't also passed — verified true as a mechanical fact, but refuted as a defect: `UpgradeDuty._bmad_core` reads `--branch`/`--installer` the identical way (apply-branch-only), an established convention for every apply-only flag on this subcommand, not something 14.9 introduced.
  - `[low]` `[reject]` Blind Hunter: `_RETIRED_DEV_SKILL_PATTERN`'s regex is brittle against single-quoted or differently-formatted assignments (false negative) and would match a stray comment (false positive) — verified true as a mechanical fact, but rejected: today's real `harness_bmadloop.py` has exactly one match and no comments in that shape (independently confirmed), and a fully robust fix would require AST-based extraction of the embedded TOML template from Python source — disproportionate for a report-only guard against a foreign file this station doesn't own.
  - `[low]` `[reject]` Blind Hunter: the preflight preview never indicates whether the two `--no-shims`-blocking foreign surfaces are currently clear, so an operator has no dry-run signal before trying `--apply --no-shims` — verified true, but rejected as out of scope: the spec's own Design Notes deliberately scope this refusal to apply-time only ("a plain pre-flight run has no opinion on shim retirement readiness"), and adding it is a new capability beyond what the story's AC asked for, not a trivial fix.
  - `[low]` `[reject]` Blind Hunter: the new `shims_to_retire:` catalog list is not alphabetically sorted (`bmad-edit-prd` sorts after the `bmad-editorial-review*` trio under ASCII rules) — verified true, but rejected: the code always re-sorts the catalog∩installed intersection before returning it, so the source list's authored order has zero runtime effect.
  - `[false]` `[reject]` Intent Alignment Auditor: the AC's "unit test with an injected runner" wording, read literally against the `InstallerRunner`/`installer_runner=` callable-injection parameter, is not satisfied by any new test (all use the file's dominant `_fake_installer_script`/`installer_bin=` disk-script pattern) — refuted: that disk-script pattern is the established, dominant convention in this exact file (~25 of ~30 pre-existing tests, including every prior Story 14.6/14.7/14.8 test), so "injected runner" reads as generic test-double shorthand, not a literal reference to one specific DI parameter; the diff is on-convention.
  - `[false]` `[reject]` Intent Alignment Auditor: the "21-row report" has no runner concept, so no preflight test uses one — refuted: `build_preflight_report` takes no runner parameter at all (it never spawns a subprocess), so this is correct behavior, not a divergence.
  - `[false]` `[reject]` Intent Alignment Auditor: "only one of the two named refusal checks is new code" (trap 2 is pre-existing, only the harness/loop-home check is new) — refuted as a defect: this is already accurately and explicitly stated in the diff's own memlog entry ("the existing unconditional trap-2 `refuse_legacy_custom` needed no change"); an accurate self-description is not a divergence.

### 2026-09-06 — Follow-up review pass (operator-triggered spec correction; Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Intent Alignment Auditor)
- verdicts: 17 findings — high 0, medium 1, low 6, false 1, maybe-false 0, bad_spec 1 (the already-recorded finding above, confirmed and exhaustively scoped by this pass), moot-by-deletion 8 (findings whose target code is removed by this same pass, not independently verdicted since the removal already resolves them)
- findings:
  - `[bad_spec]` Intent Alignment Auditor: exhaustively mapped every place in the diff depending on the false "harness/loop-home still emits bmad-dev-auto is a blocker" premise (`cli.py` help text + `--loops-home` flag; `upgrade.py`'s two constants, two functions, `loops_home` param + call site + `UpgradeDuty` wiring; `test_upgrade_apply.py`'s module docstring + 8 tests) and confirmed the `shims_to_retire` preview machinery, the `no_shims` argv mechanism, and trap-2 `refuse_legacy_custom` are NOT entangled and must be preserved exactly. This is the same bad_spec finding recorded in the Spec Change Log above; this row exists to record the exhaustive scope mapping as its own evidence trail. Action: full removal + test fixes, per the Code Map below.
  - `[medium]` `[patch]` Verification Gap Reviewer: `--no-shims` argv ordering relative to `--pin` pairs is never jointly exercised with a nonempty `pins` list — every `no_shims=True` test targets the 6.11.0 catalog (zero pins), and the one test with nonempty pins never sets `no_shims=True`; a bug that only manifests with both present (e.g. `--no-shims` accidentally gated on `not pins`) would ship undetected — verified true by reading every `no_shims=True` call site. Fixed: added a new test combining `no_shims=True` with a pin-bearing `_custom_module_fixture`, asserting the full argv order.
  - `[low]` `[patch]` Blind Hunter: `apply_bmad_core_upgrade`'s own docstring (`"""CAP-2+3+6+7 deliberate apply..."""`) was never updated for CAP-8 (Story 14.8) or CAP-9 (this story) — verified true. Fixed (narrow, since this docstring line is directly touched by this same fix pass): bumped to `"""CAP-2+3+6+7+8+9 deliberate apply..."""` and added a one-line CAP-9 paragraph mirroring the existing CAP-7 paragraph's style.
  - `[low]` `[defer]` Blind Hunter: the top-level `upgrade` command blurb in `cli.py` still enumerates only "CAP-1 … CAP-5", never extended for CAP-6/7/8/9 — verified true, but pre-existing (CAP-6/7/8 were also never added in Stories 14.6-14.8) and not introduced by this story. Deferred: a proper fix means catching up 4 capabilities at once, out of this narrow correction's scope.
  - `[low]` `[defer]` Blind Hunter: `ApplyReport` gives CAP-7/CAP-8 their own typed fields but CAP-9 gets none (a JSON consumer must string-search `installer_cmd` for `"--no-shims"`) — verified true. Deferred: adding a field is more than a direct correction (new field + `to_dict` + `format_apply` changes), and the existing `notes`-text signal is sufficient for this story's own stated scope.
  - `[low]` `[defer]` Blind Hunter: nothing gates `--no-shims` against the target version actually supporting it (e.g. `--target 6.10.0 --no-shims` fails as a raw installer-argv error, not a clean steward refusal) — verified true, a real but orthogonal hardening gap. Deferred: out of this narrow correction's scope; worth a future story if it's ever hit in practice (targets are always 6.12.0 in current use).
  - `[low]` `[reject]` Edge Case Hunter: catalog `shims_to_retire` value could be a non-list (string, unhashable entries), silently mis-iterating or raising `TypeError` — verified true as a mechanical possibility, but rejected: the catalog is a single hand-authored, git-reviewed YAML file already covered by `test_real_612_catalog_shims_to_retire_has_21_entries`, and the fix (an isinstance guard + new error path) is more than a direct correction for a low-likelihood authoring mistake.
  - `[low]` `[reject]` Blind Hunter: `--no-shims`/`--loops-home` silently no-op without `--apply` — same finding as the original pass's row, carried forward on its own refutation (matches the identical, pre-existing `--branch`/`--installer` behavior); moot in the same breath since `--loops-home` is removed entirely by this pass.
  - moot-by-deletion (not independently re-verdicted; the code they describe is removed by this pass, per the bad_spec finding above): Blind Hunter's TOML-regex-robustness finding, duplicate-`home_root`-expression finding, CAP-9-vs-CAP-5-loop-home-semantics-disagreement finding, and untested-except-branches finding; Edge Case Hunter's `Path.home()` `RuntimeError` finding, harness-plus-bad-override-combined-message finding, and hardcoded-`bmad-dev-auto`-vs-other-20-shims finding; Verification Gap Reviewer's `--loops-home` operator-typo-guard-untested finding. Each named the now-deleted `_shim_retirement_blockers`/`_RETIRED_DEV_SKILL_PATTERN`/`loops_home` machinery as its subject; removing that machinery resolves all eight without a per-row patch action.

## Design Notes

This spec file lives in the session scratchpad rather than the project's own
`implementation-artifacts/` because `_bmad-output/projects/pyforge-steward/implementation-artifacts`
is a Tier-3 backlink symlink resolving OUTSIDE this worktree (into the shared main checkout),
which the sandbox correctly refuses to write through from an isolated worktree — the same
deviation Stories 46.7 and 46.8 recorded.

**Why `shims_to_retire` is not a trap.** Every other `PreflightReport` list (`legacy_custom`,
`locally_modified`, `local_customizations`, …) names something ALREADY WRONG that the operator
should look at. The shim roster is the opposite — it is a preview of what a future `--no-shims`
run would remove, useful for audit even on a plain pre-flight. Folding it into `trap_ids` would
make every ordinary (non-retiring) pre-flight against 6.12.0 report 21 "problems" that are not
problems.

**Why the harness/loop-home check is apply-time-only, not part of `PreflightReport`.** The
story's own Given/When/Then frames this refusal entirely around `--apply --no-shims`; a plain
pre-flight run has no opinion on shim retirement readiness. This also keeps the change smaller —
no new `PreflightReport` field, no new `format_preflight` section for it.

**Why `_list_loop_homes` can be called before its own definition.** Python only resolves a
function's free variables when it is CALLED, not when it is textually defined; `_shim_retirement_blockers`
sits earlier in the file than `_list_loop_homes` (used by CAP-5's `run_loop_home_gate` further
down), which is safe by the time either function actually runs.

**Why this story never runs the real `--no-shims` apply.** This repo's own
`harness_bmadloop.py` and the operator's real `~/.bmad-loops/*/policy.toml` files still name
`bmad-dev-auto` today (marshal Story 30.5, not yet landed, is what updates them) — a real run
right now would correctly refuse via the exact mechanism this story adds. The live exercise is
Session 2 step 9, gated on Story 30.5 landing first.

## Verification

**Commands:**
- `cd src/shared/packages/pyforge-steward && pixi run -e pyforge-steward pytest tests/unit/test_upgrade_apply.py tests/unit/test_upgrade_preflight.py -q` -- expected: all pass, count strictly greater than the pre-story baseline.
- `cd src/shared/packages/pyforge-steward && pixi run -e pyforge-steward pyforge-steward-test` -- expected: green.
- `cd src/shared/packages/pyforge-steward && pixi run -e pyforge-steward steward upgrade bmad-core --target 6.12.0 --repo-root /home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/.claude/worktrees/agent-a4aeeab0dc588dcf4 --help` -- expected: `--no-shims` and `--loops-home` documented (use `--help`, not a live run).
- `cd src/shared/packages/pyforge-steward && pixi run -e pyforge-steward ruff check --isolated --select I001,F src/pyforge/steward/upgrade.py src/pyforge/steward/cli.py tests/unit/test_upgrade_apply.py tests/unit/test_upgrade_preflight.py` -- expected: clean.
- `cd src/shared/packages/pyforge-steward && pixi run -e pyforge-steward mypy src/pyforge/steward/upgrade.py` -- expected: no more errors than the pre-existing baseline.
- `pixi run -e local-recipes detectors-ci` -- expected: clean or unchanged pre-existing findings only.

## Auto Run Result

**Summary:** Implemented CAP-9 (`--no-shims` deliberate shim retirement) in `pyforge-steward`: a
catalog-declared `shims_to_retire:` list (21 entries) surfaces as an unconditional, non-trap
`PreflightReport.shims_to_retire` preview; `--no-shims` inserts on the installer argv right after
`--modules` and before any `--pin` pairs; a new apply-time-only refusal reports two marshal-owned
foreign surfaces (the embedded harness `policy.toml` template, any rendered loop-home
`policy.toml`) still naming the retired `bmad-dev-auto` skill id. The pre-existing trap-2
legacy-custom refusal needed no change and is now proven to hold under `--no-shims` too. A
four-layer review pass found 21 findings; 11 patched (closing 2 real hermetic-test-isolation bugs,
1 test that didn't prove its own claim, a missing real-catalog assertion, 2 misleading test/memlog
naming issues, an unhandled-exception path, a silent safety-check bypass, and an undeduped list),
2 deferred, 8 rejected on their refutations. The live `--no-shims` apply against this repo's real
installed core was NOT run, per the story's explicit boundary — it is Session 2 step 9, gated on
marshal Story 30.5 landing first.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` — `PreflightReport.shims_to_retire`, `build_preflight_report`/`format_preflight` additions, `_MARSHAL_HARNESS_TEMPLATE_RELATIVE_PATH`/`_RETIRED_DEV_SKILL_PATTERN` constants, `_shim_retirement_blockers`/`refuse_shim_retirement_not_ready`, `apply_bmad_core_upgrade`'s `no_shims`/`loops_home` params + argv + refusal + note, `UpgradeDuty._bmad_core` plumbing.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `--no-shims`/`--loops-home` on the `bmad-core` subparser.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.12.0.yaml` — `shims_to_retire:` (21 entries).
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py` — 9 new tests.
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_preflight.py` — 6 new tests.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/.memlog.md`, `spec-pyforge-steward/.memlog.md`, `spec-scratch-worktree-lifecycle/.memlog.md` — CAP-9 delivery + review-fix narrative, foreign-surface reconcile.
- `scripts/.spec-surface-baseline.json` — re-stamped scoped for `spec-pyforge-steward` and `spec-scratch-worktree-lifecycle`.

**Review findings breakdown:** 21 findings — 11 patched (5 medium, 6 low), 2 deferred (both low,
recorded in frontmatter `deferred`), 8 rejected (5 low as out-of-scope/matches-existing-precedent,
3 false on their refutations).

**Follow-up review recommendation:** `true` — 5 medium-verdict findings were patched this pass
(≥2 medium threshold). Specific unverified risk to re-check: the review-fix pass itself was not
independently re-reviewed by a fresh 4-layer pass — in particular, whether the new
`test_real_612_catalog_shims_to_retire_has_21_entries` and the two now-isolated `loops_home=`
tests are fully correct, and whether the `_shim_retirement_blockers` try/except and invalid-path
guard interact correctly with every existing call site (verified manually above via full-suite
green + direct code reading, but not via a second independent review pass).

**Verification performed:**
- `pixi run -e pyforge-steward pytest tests/unit/test_upgrade_apply.py tests/unit/test_upgrade_preflight.py -q` — 109 passed (was 94).
- `pixi run -e pyforge-steward pyforge-steward-test` — 1106 passed (was 1091).
- `steward upgrade bmad-core --target 6.12.0 --repo-root <worktree> --help` — `--no-shims`/`--loops-home` documented.
- `ruff check --isolated --select I001,F` on all 4 touched source/test files — clean.
- `mypy src/pyforge/steward/upgrade.py` — 17 errors, matches the pre-existing baseline.
- `pixi run -e local-recipes python -m pyforge.doctor.sources spec-surface` — clean after reconcile + scoped re-stamp.
- `pixi run -e local-recipes detectors-ci` — 17/18 clean (pre-existing `dream-chain` finding only, marshal-owned, unrelated to this story).
- Matrix Test Audit: all 8 I/O & Edge-Case Matrix rows covered by a passing, named test (confirmed by running each row's covering test with `-k` filters).

**Residual risks:** the 2 deferred low-severity gaps recorded in frontmatter. The live `--no-shims`
apply against this repo's real installed core remains unexercised by design — Session 2 step 9,
after marshal Story 30.5 lands.

## Auto Run Result (follow-up pass, 2026-09-06)

**Summary:** A sibling story (marshal 30.5) discovered this story's own harness/loop-home refusal
check has no valid target — `bmad_loop`'s `DevPolicy.skill` is a permanent internal adapter
discriminator that must read `"bmad-dev-auto"` forever, on every era, independent of which skill
is actually invoked. Operator directed a spec correction (not a new story) since this branch was
never merged. `_shim_retirement_blockers`, `refuse_shim_retirement_not_ready`, their two module
constants, the `loops_home` parameter (on `apply_bmad_core_upgrade` and `UpgradeDuty._bmad_core`),
and the `--loops-home` CLI flag are all REMOVED. A fresh four-layer follow-up review (briefed with
the verified root cause) exhaustively mapped every dependent site, confirmed the `shims_to_retire`
preview machinery / `no_shims` argv mechanism / trap-2 legacy-custom check are NOT entangled and
survive untouched, found one genuine additional coverage gap (`--no-shims` argv ordering never
jointly tested with a nonempty `--pin` list) and one stale docstring (missing CAP-8/9 in
`apply_bmad_core_upgrade`'s own docstring header), and rejected/deferred the rest (8 findings moot
by the same deletion, 2 pre-existing gaps out of this narrow correction's scope, 1 rejected as
matching established `--branch`/`--installer` precedent).

**Files changed (this pass):** `upgrade.py` (removals + docstring bump), `cli.py` (`--loops-home`
removed, `--no-shims` help reworded), `test_upgrade_apply.py` (3 tests deleted, 5 rewritten/renamed,
1 added), plus governing-spec corrections: `spec-bmad-method-core-upgrade/SPEC.md` (CAP-9),
`spec-bmad-611-era-alignment/SPEC.md` (CAP-12, pyforge-marshal), `spec-bmad-suite-lifecycle/SPEC.md`
(CAP-10), both projects' epics.md (Story 14.9 and marshal Story 30.5 text), 4 memlogs, and
`scripts/.spec-surface-baseline.json` (2 specs re-stamped).

**Review findings breakdown (this pass):** 17 raw findings — 1 `bad_spec` (the exhaustive scope
mapping, already resolved via the Spec Change Log + this fix), 1 medium patched (the pin-ordering
test), 1 low patched (the docstring bump), 2 low deferred (pre-existing CLI blurb / `ApplyReport`
typed-field gaps, not introduced by this story), 1 low deferred (no version-gating on `--no-shims`,
orthogonal hardening), 1 low rejected (catalog non-list type-safety, low-likelihood + non-trivial
fix), 1 low rejected (no-op without `--apply`, matches established precedent, carried from the
original pass), 8 moot-by-deletion (named the removed machinery directly).

**Follow-up review recommendation:** `false` — this is itself the single allowed follow-up pass on
a `done` spec; per protocol the flag is forced `false` at HALT regardless of patch score (and the
actual score doesn't warrant another pass either: only 1 medium + 1 low patched this pass, and no
`high`).

**Verification performed:** `pytest tests/unit/test_upgrade_apply.py tests/unit/test_upgrade_preflight.py -q`
— 107 passed (was 109; net -2 from 3 deletions + 1 addition). `pyforge-steward-test` — 1104 passed
(was 1106). `ruff check --isolated --select I001,F` — clean. `mypy upgrade.py` — 17 errors, matches
the pre-existing baseline. Grep confirms zero remaining references to `_shim_retirement_blockers`,
`refuse_shim_retirement_not_ready`, `_RETIRED_DEV_SKILL_PATTERN`, `_MARSHAL_HARNESS_TEMPLATE_RELATIVE_PATH`,
or the removed `loops_home` parameter anywhere in `upgrade.py`, `cli.py`, or the two test files.
`python -m pyforge.doctor.sources spec-surface` — clean after reconciling 2 specs. `detectors-ci` —
17/18 clean (the same pre-existing, unrelated `dream-chain` finding).

**Residual risks:** none new. The live `--no-shims` apply (Session 2 step 9) remains the next step,
now genuinely unblocked — steward's own refusal surface is limited to the correct, permanent
trap-2 legacy-custom check.
