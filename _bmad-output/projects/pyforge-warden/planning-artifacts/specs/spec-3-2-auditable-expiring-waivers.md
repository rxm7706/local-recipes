<!-- RECOVERED 2026-07-25 from Claude Code session transcript 691544cc-eaa3-4ed2-a090-8d284a11d0c9.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'Story 3.2 — Auditable expiring waivers'
type: 'feature'
created: '2026-07-17'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** pyforge-warden has no escape hatch for a finding a team can't fix immediately — every non-clean finding blocks CI with no auditable, time-boxed way to ship anyway (FR24-FR26).

**Approach:** add a `waiver.py` module implementing the one suppression engine (schema validation + exact finding-id matching + expiry-awareness) plus a `--bypass --reason` CLI path that emits a `.warden-waivers.yaml` stanza via `yaml.safe_dump` for a human to commit; matched, non-expired waivers rewrite a finding's fed rung to `Status.BYPASSED` before `verdict.compose()` runs.

## Boundaries & Constraints

**Always:**
- Waiver I/O uses `yaml.safe_load`/`yaml.safe_dump` only — never `yaml.load`/`unsafe_load`, never string-concatenation (NFR-S4/D1).
- The tool never writes into the scanned repository tree; `--bypass` prints the stanza to stdout only, for the human to commit.
- A waiver `id` must exact-match an existing `Finding.id` (one of the three finding-id families already defined in `models.py`) — no wildcard/glob/prefix matching, ever (NFR-S3, least-privilege). Locally re-declare the three family regexes in `waiver.py` (mirrors `config.py`'s own precedent of locally re-declaring `_SEVERITY_ORDER`/`_CONFIDENCE_RANK` rather than importing across modules) — do not edit `models.py`.
- Every waiver entry that actually suppresses a finding this run is echoed in `--format text` output (NFR-S3).
- A malformed/unparsable/schema-invalid `.warden-waivers.yaml` is fail-closed: record a typed error (reuse `ErrorKind.CONFIG_PARSE` for a YAML syntax/read failure, `ErrorKind.CONFIG_VALIDATION` for a shape/schema failure — `ErrorKind` is a closed enum, only `CveMatchLevel`/`WithholdReason` may grow) with `owner="waiver"`, `axis=AXIS_INGESTION`, and apply zero waivers that run. A missing file is normal (empty waiver set, no error), mirroring `config.py`'s missing-file handling.
- The waiver file's in-file `version` key is validated (must be the literal int `1`); missing/non-integer/unknown → the same typed `CONFIG_VALIDATION` error, never guessed.
- `waiver.py` only rewrites a rung's `Status` to `BYPASSED` (or leaves it untouched) in the list fed to `verdict.compose()`; it must never import a private name from `verdict`, call an exit primitive with a guarded literal, or spell out the 7-rung lattice order — `tests/meta/test_verdict_sole_ownership.py` enforces this for every non-`verdict.py` module and must stay green.
- Expiry comparisons take `now: datetime` as an explicit parameter (never call `datetime.now()` internally) — mirrors `vuln.is_db_stale`'s testability convention.
- `--bypass` requires `--reason` inline (no prompts, ever); `--bypass` without `--reason` is an argparse usage error (exit 2).
- `authorized_by` on an emitted stanza defaults to `getpass.getuser()`, falling back to `"unknown"` if that raises — no CLI flag exists for it.
- `accepted_at`/`expires_at` are ISO-8601 UTC strings (`datetime.now(UTC).isoformat()`); default expiry window = `EffectiveConfig.waiver_default_expiry_days` (new `config.py` key `waiver-default-expiry-days`, default 14 — FR24's "config + per-repo override").

**Block If:** none identified — every open design question below is resolved in Design Notes; if a genuinely new ambiguity surfaces mid-implementation that these boundaries don't cover, halt rather than guess.

**Never:**
- Never add a new `Status`/`ErrorKind` member or amend `report-schema.json`/`ComplianceReport` — the one sanctioned schema amendment is reserved for Story 6.1. `review_required: true` (PRD/epics language) is expressed purely by the existing `Status.BYPASSED` rung; no new report field.
- Never implement expiry **re-block flagging**, `stale-waiver`/`waiver-expired` review notices, or `--warn-only` — that is Story 3.3. Here, an expired entry simply fails to suppress; its finding's original rung is left untouched for the normal lattice to project (which already yields the correct non-zero exit — no extra mechanism needed for that side-effect).
- Never apply waiver-matching to the `indeterminate:coverage-floor:<axis>` rung computed inside `report.py`'s `assemble_report` (Story 3.1, off by default) — out of scope this story.
- Never call `yaml.load`/`yaml.unsafe_load`, and never let a waiver entry's `reason` exceed 1000 characters (reject longer as malformed) — empty string is a valid `reason`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No waiver file | `.warden-waivers.yaml` absent | Scan proceeds unchanged, no waivers applied | No error |
| Valid non-expired match | Entry `id` exact-matches a fed rung's `finding_id`, `expires_at` in the future | That rung's status becomes `bypassed`; echoed in text output; overall composed status `bypassed`, exit 0 (if no other rung outranks it) | No error |
| Valid match, expired | Entry matches but `expires_at` has passed | Rung left untouched (finding's original status stands) | No error (3.3 adds explicit flagging) |
| Malformed YAML | Broken indentation / syntax | Zero waivers applied | Typed `ErrorKind.CONFIG_PARSE`, `owner="waiver"`, `Status.ERROR` rung |
| Unknown/missing `version` | `version: 2` or key absent | Zero waivers applied | Typed `ErrorKind.CONFIG_VALIDATION` |
| Wildcard/malformed id | `id: "vuln:*:*"` or id not matching any finding-id family | Zero waivers applied (whole file rejected) | Typed `ErrorKind.CONFIG_VALIDATION` |
| `--bypass --reason "x"` with blocking findings | One or more non-clean Finding-backed rungs | Stdout gets a `version: 1` + `waivers:` stanza, one entry per blocking finding; run exits 0, status `bypassed` | No error |
| `--bypass` without `--reason` | Missing required flag | Nothing scanned | argparse usage error, exit 2 |
| `--reason` with YAML-hostile content | Quotes, `: `, leading `-`/`?`/`&`, newlines, unicode, empty string | `safe_load(stanza)["waivers"][i]["reason"] == original` exactly | No error |
| Residual un-waived finding alongside a waived one | Two findings, one matched by a waiver, one not | Only the matched rung becomes `bypassed`; the other's own status (e.g. `policy-violation`) still wins the composed verdict | No error |

</intent-contract>

## Code Map

- `src/pyforge/warden/waiver.py` -- NEW. Schema types, `safe_load`/`safe_dump` I/O, matching/suppression, `--bypass` stanza emission — the one suppression engine.
- `src/pyforge/warden/config.py` -- add `waiver-default-expiry-days` to `_RECOGNIZED_KEYS` + `EffectiveConfig.waiver_default_expiry_days` (default 14).
- `src/pyforge/warden/cli.py` -- add `--bypass`/`--reason` flags; wire waiver read/apply/emit between policy evaluation and `assemble_report`.
- `src/pyforge/warden/report.py` -- extend `render_text` to print one non-contract line per applied waiver notice.
- `src/pyforge/warden/models.py` -- read-only reference (`Status.BYPASSED`, `ErrorKind.CONFIG_PARSE`/`CONFIG_VALIDATION`, the three finding-id family grammars) — no edits.
- `src/pyforge/warden/verdict.py` -- read-only reference (`compose()`'s highest-rung-wins semantics already do the right thing) — no edits.
- `tests/unit/test_waiver.py` -- NEW.
- `tests/unit/test_discovery_extract_cli.py` -- extend with `--bypass`/waiver-file CLI integration cases (or a new sibling `test_cli_bypass.py` if that file is already large).

## Tasks & Acceptance

**Execution:**
- [ ] `src/pyforge/warden/config.py` -- add `waiver-default-expiry-days` (positive int) to `_RECOGNIZED_KEYS`, a `_coerce_waiver_default_expiry_days` helper, and `EffectiveConfig.waiver_default_expiry_days: int = 14`, threaded through `ConfigLoader._load` the same way the three existing keys are -- lets a repo override the default 14-day expiry.
- [ ] `src/pyforge/warden/waiver.py` -- NEW: `WaiverEntry`/`WaiverFile` frozen dataclasses (`id`, `reason`, `authorized_by`, `accepted_at`, `expires_at`); `WaiverParseError`/`WaiverValidationError` (mirror `config.py`'s `_ConfigError` shape); `load_waivers(path) -> tuple[WaiverEntry, ...]` (missing file -> `()`; validates `version==1`, unique non-wildcard ids matching one of the three locally-declared finding-id family regexes, non-empty string fields within the 1000-char reason bound, `expires_at > accepted_at`); `apply_waivers(rungs, waivers, *, now) -> tuple[list[rung], list[notice]]` (exact-id match + not-expired -> rewrite `Status` to `BYPASSED`, collect a notice; no match or expired -> untouched); `emit_bypass_stanza(rungs, *, reason, authorized_by, accepted_at, expiry_days) -> str` (one entry per still-non-clean Finding-backed rung, `safe_dump`).
- [ ] `src/pyforge/warden/cli.py` -- add `scan --bypass` (store_true) + `--reason` (str, default None) to `_build_parser`; after parsing, `--bypass` without `--reason` -> `parser.error(...)`. After `rungs.extend(policy_rungs)` and the D2(c) empty-extraction append (before `assemble_report`): read `target / ".warden-waivers.yaml"` via `waiver.load_waivers` (catch `WaiverParseError`/`WaiverValidationError` -> `_record_error` with `ErrorKind.CONFIG_PARSE`/`CONFIG_VALIDATION`, `owner="waiver"`, `axis=AXIS_INGESTION`); apply via `waiver.apply_waivers(rungs, waivers, now=datetime.now(UTC))`; when `args.bypass`, also bypass every still-non-clean Finding-backed rung and `sys.stdout.write(waiver.emit_bypass_stanza(...))` before the report emission block. Pass collected notices to `render_text`.
- [ ] `src/pyforge/warden/report.py` -- extend `render_text(report, *, applied_waivers=())` to append one line per notice (id, reason, authorized_by, expires_at) after the finding/error lines.
- [ ] `tests/unit/test_waiver.py` -- NEW: schema validation (missing/wrong-type/unknown version, duplicate id, wildcard/non-family id, empty reason accepted, reason >1000 chars rejected, `expires_at <= accepted_at`); matching (exact match suppresses; non-match/expired leaves rung untouched); round-trip (`safe_load(safe_dump(...))["reason"] == original` across quotes, `: `, leading `-`/`?`/`&`, newlines, unicode, empty, length-bound); `emit_bypass_stanza` shape (`version: 1`, one entry per blocking rung).
- [ ] `tests/unit/test_discovery_extract_cli.py` (or new sibling) -- CLI-level: `--bypass --reason` on a fixture with a known violation -> exit 0, `status.value == "bypassed"`, stdout contains the stanza; `--bypass` alone -> exit 2; a committed valid non-expired waiver file (no `--bypass`) -> exit 0 bypassed; a malformed waiver file -> exit 2 with a `waiver`-owned error in the report.

**Acceptance Criteria:**
- Given a project with a matching, non-expired `.warden-waivers.yaml` entry, when scanned, then the report's status is `bypassed`, exit code 0, and the waiver is echoed in `--format text` output (FR24).
- Given `--bypass --reason "<text>"` on a run with blocking findings, when scanned, then stdout carries a `.warden-waivers.yaml`-ready stanza (one entry per blocking finding, `version: 1`), the tool writes no file, and the run exits 0 with status `bypassed`.
- Given a malformed, wildcard-id, or unknown-`version` waiver file, when read, then zero waivers apply and the run's status/exit reflect `error`/2 (FR26).
- Given one waived and one un-waived finding in the same run, when scanned, then only the waived rung becomes `bypassed` and the un-waived finding's own status still wins the composed verdict (`verdict.compose`'s existing rules, unchanged).
- Given `--reason` containing quotes, colons, leading YAML indicators, newlines, unicode, or an empty string, when emitted and re-read, then the reason round-trips byte-for-byte (D1).
- Given the full test suite, when run via `pixi run -e pyforge-warden pyforge-warden-test`, then `tests/meta/test_verdict_sole_ownership.py` still passes with `waiver.py` included in its scan.

## Design Notes

- **`review_required` has no new schema field.** `Status.BYPASSED` already exists as a distinct rung (Story 1.1) sitting between `warn` and `clean` specifically for this purpose; the PRD's "`review_required: true`" is that rung's meaning, not a literal JSON key. The one sanctioned `ComplianceReport` amendment is reserved for Story 6.1 (a "suppression rung-discriminator" is explicitly scheduled there) — this story must not anticipate it.
- **Waiver `id` is the sole match key.** `models.py`'s own docstring states finding-id stability is "what waiver matching... depends on" — the id already embeds package (and version, for the vuln family), so no separate `package`/`ecosystem` schema fields are introduced. Least-privilege (NFR-S3) falls out structurally: a glob/wildcard character fails the finding-id family regex, so a wildcard entry is rejected as malformed before it can ever match anything.
- **Malformed waiver file reuses `CONFIG_PARSE`/`CONFIG_VALIDATION`.** `ErrorKind` is closed (only `CveMatchLevel`/`WithholdReason` may grow additively) — the waiver file is config-like committed/human-edited input, so it reuses the same parse-vs-validation split `config.py` already established, with `owner="waiver"` distinguishing the source.
- **Story 3.3 boundary.** Nothing here needs to *report* an expiry event — an expired entry is architecturally identical to "no waiver exists" for this rung, which already produces the correct (non-zero) exit through the untouched original rung. 3.3 adds the explicit review-visible flagging and `--warn-only`.

## Verification

**Commands:**
- `pixi run -e pyforge-warden pyforge-warden-test` -- expected: full suite green, including `tests/meta/test_verdict_sole_ownership.py` with `waiver.py` present.

**Manual checks (if no CLI):**
- `pixi run -e pyforge-warden warden-scan tests/fixtures/projects/vuln_critical --bypass --reason "test"` -- inspect the printed stanza shape and exit code 0.
