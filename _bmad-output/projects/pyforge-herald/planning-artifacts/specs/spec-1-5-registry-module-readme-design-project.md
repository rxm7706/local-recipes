<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Registry module — README § Design project'
type: 'feature'
created: '2026-07-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '8800e0635b0620c2e156f669dd2525736298c105'
final_revision: '755e9d54b16d5e787e25d08907832a33338d8fc5'
---

<intent-contract>

## Intent

**Problem:** Bridge-core has nowhere to durably record or read back a deck's linked Claude
Design project (name, id, file URL) in the deck's own README, so Story 1.6 (`seed`) and every
later CAP story would each invent ad-hoc markdown handling for the same block instead of
sharing one owner (AD-8).

**Approach:** Add `registry.py`, the sole owner of a deck README's `## Design project (the
bridge's far end)` block: `register()` appends the block when absent or replaces it in place
when present (never duplicating), `read()` parses it back into a `DesignProject` record,
returning `None` when absent and raising `errors.HeraldError` on anything malformed —
mirroring `state.py`'s AD-6 discipline and joining `test_bridge.py`'s existing coverage-pin
sweep, which already names this exact module.

## Boundaries & Constraints

**Always:**
- Exactly two functions plus one frozen dataclass: `register(readme_path: Path, project_name:
  str, project_id: str, file_url: str) -> None`, `read(readme_path: Path) -> DesignProject |
  None`, `DesignProject(project_name: str, project_id: str, file_url: str)`. This diverges from
  the epics AC's illustrative `register(slug, ...)`/`read(slug)` shape the same way Story 1.4
  diverged from the architecture spine's Structural Seed diagram (documented there as
  "illustrative, not binding"): every other bridge-core module (`state.py`) takes an explicit
  path and never assumes a cwd, and a README is already 1:1 with its own deck, so a slug key
  inside the file would serve no purpose the shared `bridge-state.json`'s slug-keying serves.
- Canonical section, heading fixed (matches the four already-hand-seeded pyforge-* deck
  READMEs' own heading text): `## Design project (the bridge's far end)`, followed by exactly:
  `Prototype lives in Claude Design project **"{project_name}"** (\`{project_id}\`):` then
  `{file_url}` on its own line. `register()` against a README with no existing section appends
  it, separated from prior content by exactly one blank line; against a README that already has
  it, replaces the span from the heading line through the next `#`-prefixed line or EOF, in
  place.
- Both functions read/write UTF-8 text; `register()` writes atomically (temp file in the same
  directory + `os.replace`, mirroring `state.write`'s crash-safety pattern — same documented
  limit: no fsync, concurrency is not addressed).
- Every failure is `errors.HeraldError` naming `readme_path` (AD-6): `register()` against a
  missing `readme_path` raises (this module never fabricates a whole README from nothing);
  `read()` returns `None` for a missing file or a missing section (mirrors `state.py`'s
  "absent = None" symmetry) but raises when the section heading exists and its body does not
  match the canonical two-line shape.
- Add `registry` to `test_bridge.py`'s `_BRIDGE_CORE_MODULES` tuple — its own coverage-pin test
  already names this exact module and fails until it is swept or excluded with cause; registry
  has no cause for exclusion (it is bridge-core, not the CLI layer or a transport adapter), and
  must independently pass the existing adapter/inference/dynamic-import identifier checks
  parametrized over `_BRIDGE_CORE_MODULES` (true by construction — it imports only `re`,
  `os`, `tempfile`, `dataclasses`, `pathlib`, and `.errors`).

**Never:**
- No parsing of the four already-hand-authored deck READMEs' existing prose
  (`presentations/pyforge-{herald,marshal,mason,doctor}/README.md`, plus older decks with
  divergent wording) — those predate this module and vary in phrasing; this story's round-trip
  guarantee covers only registry.py's own canonical output. Do not edit any file under
  `presentations/` or any planning-artifacts file (mirrors Story 1.4's identical boundary).
- No bootstrap-fallback wiring into `bridge.py`/`state.py` (AD-5's "read only as a bootstrap
  fallback when no state file exists") — that consumer lands with a later CAP story.
- No `slug` parameter and no `presentations/<slug>/README.md` path derivation inside
  `registry.py` — resolving `readme_path` against a repo root is the caller's job (Story 1.6+),
  matching `state.py`'s own documented split.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Register into a README with no section | README with unrelated heading content, no `## Design project...` | Section appended at end, separated by one blank line | No error expected |
| Register updates in place | README already carries the section (from a prior `register`) | Body replaced with the new name/id/url; heading appears exactly once, nothing duplicated | No error expected |
| Read after register | Freshly registered README | `read()` returns a `DesignProject` equal to the registered fields | No error expected |
| Read, no section | README with unrelated content only | Returns `None` | No error expected |
| Read, missing file | `readme_path` does not exist | Returns `None` | No error expected |
| Register, missing file | `readme_path` does not exist | Raises | `HeraldError` naming `readme_path` |
| Read, malformed section body | Heading present, body text does not match the two-line shape | Raises | `HeraldError` naming `readme_path` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/registry.py` -- create -- `DesignProject`
  + `register`/`read`
- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- reference (read-only) --
  `HeraldError` every failure wraps into
- `src/shared/packages/pyforge-herald/src/pyforge/herald/state.py` -- reference (read-only) --
  the explicit-path / atomic-write / AD-6 discipline this module mirrors
- `src/shared/packages/pyforge-herald/tests/test_registry.py` -- create -- the I/O matrix rows,
  using `tmp_path`
- `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- edit -- add `registry` to
  `_BRIDGE_CORE_MODULES`
- `presentations/pyforge-herald/README.md` -- reference (read-only) -- the hand-seeded
  `## Design project` section's existing heading/prose this canonical form matches in heading
  text only

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/registry.py` -- create --
  `DesignProject` dataclass + `register(readme_path, project_name, project_id, file_url)` +
  `read(readme_path)`, atomic write, section-span replace, structural-failure discipline
- [x] `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- edit -- import `registry`,
  add it to `_BRIDGE_CORE_MODULES`
- [x] `src/shared/packages/pyforge-herald/tests/test_registry.py` -- create -- the I/O matrix
  rows above, plus a duplicate-register-does-not-duplicate-the-heading test

**Acceptance Criteria:**
- Given `registry.py` as the sole owner of a deck README's § *Design project* block, when
  `register(readme_path, project_name, project_id, file_url)` is called against a README with
  no existing section, then the section is appended in the canonical two-line form
- Given that freshly-registered README, when `read(readme_path)` is called, then it returns a
  `DesignProject` with the same three fields, round-tripping cleanly
- Given a README that already carries the section, when `register` is called again for the same
  deck, then the existing block is updated in place — the heading appears exactly once
- Given the extended `_BRIDGE_CORE_MODULES` sweep, when `pyforge-herald-test` runs, then
  `test_bridge_core_sweep_covers_every_non_excluded_package_module` and every adapter/inference/
  dynamic-import check parametrized over it pass for `registry.py` with no code changes to
  `test_bridge.py` beyond the tuple edit

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 6: (medium 2, low 4)
- defer: 0
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` **Replacing an existing section that is followed by more content
    silently swallowed the blank line separating them** — reproduced live by both reviewers
    independently: re-registering a README that had `...url\n\n## Quick start...` produced
    `...url\n## Quick start...` with the separator gone, a formatting regression that survived
    because the shipped test only checked substring presence, not exact text. `register()` now
    inserts exactly one blank line before any following content on replace, regardless of how
    much spacing the replaced span itself held; the affected test now pins the full expected
    text instead of substrings.
  - `[medium]` `[patch]` **`register()` accepted an empty or newline-carrying
    `project_name`/`project_id`/`file_url`, silently writing a body its own `read()` could not
    parse back** — reproduced live: an empty `project_name` or `project_id` breaks the
    `_BODY_LINE1_RE` match (the regex requires at least one character inside the quotes/
    backticks), and an embedded newline in any field spills into a third line, both turning a
    successful `register()` into an immediate `read()` failure — breaking this module's central
    round-trip promise. `register()` now refuses any of the three fields up front (empty, `\n`,
    or `\r`) as `HeraldError`, before touching the filesystem. Five new parametrized tests pin
    the refusal and confirm nothing is written.
  - `[low]` `[patch]` A section at end-of-file with no following heading pulls every trailing
    blank line into its span, so a README ending in extra blank lines after the URL falsely
    tripped `read()`'s "expected exactly two body lines" check — a false rejection of otherwise
    well-formed data. `read()` now trims trailing blank lines from the body before the length
    check; test added.
  - `[low]` `[patch]` The missing-file error message embedded a design-rationale aside
    (`"(register() never fabricates a README from nothing)"`) in user-facing text, inconsistent
    with `state.py`'s terser messages. Reworded to state only the fact; the rationale stays in
    the docstring.
  - `[low]` `[patch]` The module's heading-detection limitation (an exact-string, whole-line
    match with no awareness of hand-edited heading variants or the heading text appearing inside
    unrelated content such as a fenced code example) was undocumented, so `register()` silently
    appending a second section in either case would have looked like a bug rather than a known,
    scoped-out limitation. Documented in the module docstring, consistent with this module's own
    "Never parse arbitrary hand-authored prose" boundary.
  - `[low]` `[patch]` The malformed-body test claiming to cover "a malformed section body" wrote
    only one body line, so it exercised the same line-count branch as the dedicated
    one-body-line test — the `_BODY_LINE1_RE` mismatch branch was completely unverified.
    Rewritten to supply exactly two body lines with the first failing the regex, actually
    exercising the previously-dead branch.
- Rejected as noise (3): `pytest.raises(HeraldError, match=str(readme_path))` using an unescaped
  path as a regex pattern — mirrors `test_state.py`'s identical, already-shipped convention
  (`match=str(state_path)`), which survived three rounds of adversarial/edge-case review
  unflagged; `os.replace` not accounting for `readme_path` being a symlink — speculative, no
  deck README in this repo is symlinked, and no established module documents symlink behavior
  either; `register()`'s exception-wrap being narrower than `state.write`'s (`OSError` only vs.
  `OSError`/`TypeError`/`ValueError`/`RecursionError`) — the broader wrap exists because
  `json.dump` serializes arbitrary values, while `fh.write(new_text)` writes a plain `str` that
  cannot raise those types; the docstring's "mirrors the crash-safety pattern and its limit"
  claim is accurately scoped to the atomic temp-file+`os.replace` mechanism, not to an identical
  exception matrix.

### 2026-07-31 — Review pass (follow-up)

- intent_gap: 0
- bad_spec: 0
- patch: 11: (medium 2, low 9)
- defer: 1: (high 1)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` **A `project_name` embedding the template's own closing envelope
    (`"** (` + backtick) shifted `_BODY_LINE1_RE`'s non-greedy match, so `register()` succeeded
    and `read()` returned *silently wrong* fields** — reproduced live: name `'A"** (`B`):'` with
    id `'C'` read back as name `'A'`, id `'B`):"** (`C'`, corrupting both fields with no error,
    which is worse than any raise and a direct hole in the round-trip promise the first pass's
    validation was added to close. `register()` now re-parses the exact line it is about to
    write and refuses fields that do not read back as themselves. (An id embedding the same
    delimiters mid-string round-trips exactly — the id group is anchored between the first
    backtick and the line-final `` `): `` — so only genuinely diverging inputs are refused;
    the test pins both a refused and that non-diverging shape.)
  - `[medium]` `[patch]` **The `\n`/`\r` field check missed every other line boundary
    `str.splitlines` recognizes (`\x0b`, `\x0c`, `\x85`, `\u2028`, `\u2029`…) and a trailing
    `\n`** — both functions parse with `splitlines`, so a `\u2028`-carrying field was accepted
    and then read back as a malformed three-line body. The check is now
    `value.splitlines() != [value]`, which refuses exactly what would not survive the file's own
    line discipline; parametrized tests added for `\u2028`, `\x0b`, and a trailing newline.
  - `[low]` `[patch]` A `file_url` starting with `#` was accepted, but the URL sits on a line of
    its own, so it read back as the heading that ends the section (`found 1`), and a re-register
    then replaced only the truncated span, stranding the old URL line below the new section.
    Refused up front; test added.
  - `[low]` `[patch]` A non-string field raised a raw `TypeError` from `"\n" in value` instead
    of `HeraldError` — `state.py` refuses annotation-violating inputs structurally
    (`isinstance` → `HeraldError`), so registry now mirrors that discipline; test case added.
  - `[low]` `[patch]` A field carrying a lone surrogate (`json.loads('"\ud800"')` can produce
    one) passed the line checks, then crashed `fh.write` mid-write with a raw
    `UnicodeEncodeError`. Now refused at validation (before the filesystem is touched), and the
    write wrap widened from `OSError` to `(OSError, ValueError)` mirroring `state.write`'s
    "wrap anyway — a raw leak through the AD-6 contract is worse than a redundant guard"
    rationale (this pass found the prior rejection of that widening was wrong in exactly this
    case: `fh.write` of a plain `str` *can* raise `UnicodeEncodeError`, a `ValueError`).
  - `[low]` `[patch]` `register()` silently replaced the README's permission bits with
    `mkstemp`'s private 0600 (`os.replace` carries the temp file's mode) — reproduced 0644→0600.
    Unlike `state.write` (which owns its file from birth), registry edits a pre-existing tracked
    file, so the mode is now copied from the original onto the temp before replace; test added.
  - `[low]` `[patch]` The module docstring's "the four already-hand-seeded pyforge-* deck
    READMEs" count is wrong — 13 READMEs under `presentations/` carry the exact heading, 9 of
    them pyforge-* (the spec's own "four" predates the fleet's growth). Count dropped from the
    docstring (derive-don't-declare); the fleet-wide read() consequence is the deferred entry
    below.
  - `[low]` `[patch]` The write re-serializes the *whole file* with `\n` line endings
    (`splitlines` + `join`), so a CRLF README — or an exotic separator inside unrelated prose —
    comes back normalized, touching every line boundary in the file, not just the owned span.
    Documented as a module-docstring limit (no behavior change; no CRLF file exists in the
    fleet).
  - `[low]` `[patch]` The documented fenced-code limitation was narrower than the actual hole:
    not just the literal heading text inside a fence, but *any* `#`-prefixed line inside fenced
    content bounds the section span early (the spec's own span rule is "next `#`-prefixed line
    or EOF"). Docstring clause widened.
  - `[low]` `[patch]` `read()`'s "expected exactly two body lines, found N" message counted
    leading blank lines invisibly (a hand-seeded README reports "found 5" for what a human reads
    as four content lines plus a blank) — the count's rule is now stated in the message, and a
    new test pins the standard-markdown blank-under-heading shape as an intended raise.
  - `[low]` `[patch]` Coverage gaps closed with six further tests: multi-trailing-blank-line
    trimming on the append path (docstring claimed it; only single-`\n` was tested), raw-binary
    (`UnicodeDecodeError`) wrapping on both functions, a failed `os.replace` surfacing as
    `HeraldError` with the original byte-identical and no leaked temp file, and a heading with
    no body at EOF ("found 0").
- Deferred (1): `[high]` `read()` raises "malformed" against every one of the 13 existing
  hand-seeded `presentations/*/README.md` sections (reproduced live on herald/doctor/scribe/
  warden: "found 5"), so the later CAP story's bootstrap-fallback consumer fails against 100% of
  the current fleet until the sections are migrated (one `register()` per deck normalizes a
  README) or a tolerance decision is made. Spec-sanctioned here — the intent contract's "Never"
  boundary explicitly scopes out the hand-authored prose — but the migration debt was recorded
  nowhere; now ledgered.
- Rejected as noise (6): whitespace-only fields (round-trip is preserved — `"   "` reads back
  as itself; the module is deliberately not a semantic URL/name validator, and the `""` refusal
  is mechanical, not semantic); heading-with-trailing-whitespace tolerance (the documented
  exact-match limitation class pass 1 already resolved as documented, backed by the spec's
  "Never" boundary); the claimed `state.py`-docstring contradiction ("that fallback lands with
  `registry.py`, not this module" names the read-side owner and is compatible with registry
  deferring the *wiring* to a later story — and `state.py` is reference/read-only in this
  story's Code Map anyway); tests omitting `encoding=` on `read_text`/`write_text` (mirrors
  `test_state.py`'s shipped convention, same rationale as pass 1's regex-match rejection);
  UTF-8-BOM heading masking (speculative — no BOM README exists in the repo; same class as the
  rejected symlink finding); `os.replace` symlink clobbering (re-raise of pass 1's explicit
  rejection, unchanged facts).

## Design Notes

**Why `readme_path` instead of `slug`.** The epics AC's `register(slug, ...)`/`read(slug)`
reads as illustrative shorthand, not a binding signature — `state.py`'s own docstring states
the "resolve against a real repo root is the caller's job" split explicitly, and every existing
bridge-core test writes through `tmp_path`, never a chdir. A README is already 1:1 with its
deck, so nothing inside the file needs a slug key the way the shared `bridge-state.json` does.

**Section-replace span is heading-to-next-heading-or-EOF.** If a caller's README ever has
non-heading content directly under this section with nothing after it (a hand-maintained table,
say), a later `register()` call replaces that content too — a documented limitation, not a
silent bug, and out of reach for this story's own README-free test fixtures.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: all tests pass, no new skips,
  egress-deny fixture unaffected (this module opens no socket)
- `pixi run -e local-recipes llms-full-check` -- expected: clean (registry.py adds no new
  dependency — stdlib only)
- `ruff format --check .` / `ruff check .` on this story's new/edited files -- expected: clean
  (whole-package `ruff check .` still carries the 4 pre-existing `transport/` findings noted in
  Story 1.4's spec, out of this story's scope)

## Auto Run Result

**Summary.** Follow-up review pass (this run) over the already-implemented Story 1.5:
`registry.py` — sole owner of a deck README's `## Design project (the bridge's far end)`
section, with `register()` (append-or-replace, atomic, permission-preserving) and `read()`
(round-trip parse, absent = `None`, malformed = `HeraldError`), swept into
`test_bridge.py`'s `_BRIDGE_CORE_MODULES`. Two fresh reviewers (Blind Hunter + Edge Case
Hunter) ran against the full baseline diff; 18 deduplicated findings triaged: 11 patched,
1 deferred to the ledger, 6 rejected.

**Files changed (this pass, commit `755e9d54`):**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/registry.py` — up-front refusal of
  delimiter-embedding / non-string / any-`splitlines`-boundary / `#`-leading-URL / unencodable
  fields; permission-bit preservation across `os.replace`; write wrap widened to
  `(OSError, ValueError)`; docstring corrections (README count, whole-file LF re-serialization,
  fence-span limitation); clarified body-line-count error message.
- `src/shared/packages/pyforge-herald/tests/test_registry.py` — 12 new/extended cases pinning
  every new refusal plus mode preservation, multi-blank append trimming, binary-corruption
  wrapping, failed-replace cleanup, and two malformed-shape raises.
- `src/shared/packages/pyforge-herald/tests/test_bridge.py` — import-block sort only (ruff
  I001 auto-fix).

**Review findings breakdown:** patch 11 (medium 2, low 9) — all fixed this pass; defer 1
(high) — the 13 hand-seeded fleet READMEs all raise on `read()` until migrated, ledgered as a
new deferred-work entry; reject 6 (details in the 2026-07-31 triage log above).

**Follow-up review recommendation:** false — the patches are localized input-refusal guards,
docstring corrections, and tests in a single module, each pinned by a dedicated test; two
consecutive passes show converging severity (pass 1 fixed live formatting/round-trip bugs,
this pass exotic-input guards), so a third independent pass is unlikely to pay for itself.

**Verification performed:** `pixi run -e pyforge-herald pyforge-herald-test` → 276 passed,
2 skipped (both pre-existing) in 0.4s; `ruff format --check` + `ruff check` on the three
story files → clean; `pixi run -e local-recipes llms-full-check` → clean (231 active deps
covered, no drift; registry stays stdlib-only).

**Residual risks:** the deferred fleet-README migration (the later CAP bootstrap-fallback
story fails against all 13 current READMEs until each is normalized via `register()` or a
tolerance decision lands — now ledgered); heading detection remains exact-string whole-line
(hand-edited variants append a second section — documented, spec-sanctioned); no fsync and
no concurrent-writer handling (inherited, documented limit of the `state.write` pattern).

