---
title: '21.10: The registry sees all fourteen decks'
type: 'fix'
created: '2026-09-16'
status: 'done' # draft | ready-for-dev | in-progress | in-review | done | blocked | awaiting-operator
baseline_revision: 'fc0cbb4df00b283f3396fc2fa2bf8e2a2802d402'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/specs/presentation-deck.md']
warnings: ['oversized'] # four README edits + one doc edit + a memlog landing note carry enough investigation detail (register()'s destructive-span semantics, the four project ids, the bootstrap glob gap) that re-deriving it at dispatch time would be wasteful
deferred:
  - summary: >-
      presentations/presenton-pixi-image/README.md carries a garbled, truncated sentence
      fragment under its Provenance section, pre-existing and unrelated to the registry fix.
    evidence: |-
      The line reads "**seeded 2026-07-25 via DesignSync (byte-exact localPath upload).dc.html`,
      `Infographic standalone.html`, - Infographic Deck.dc.html`). The `DesignSync` tool was not
      exposed..." -- a mangled sentence, present before this story touched the file and preserved
      verbatim under `### Provenance` per this story's own out-of-scope note (registry.read() never
      parses this span, so it does not block the registry fix). Confirmed unchanged by diffing
      against the pre-story revision.
    location: >-
      presentations/presenton-pixi-image/README.md:71
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 20.13 registered the ten PyForge decks and left the four chain decks unlinked; registry.read cannot parse deckcraft's 24-line body.

**Approach:** Re-register each through registry.register with history under ### Provenance and re-run the bootstrap. herald deck status --repo-root . reports all fourteen decks linked. A fresh clone reproduces it from READMEs. agentic-sdlc is left to Story 23.2. Dispatch this only after the four Claude Design pushes (21.6–21.9).

## Boundaries & Constraints

**Always:**
- herald deck status reports all fourteen decks linked with project ids.
- A fresh clone reproduces the registry from READMEs alone.

**Never:**
- Do not declare agentic-sdlc unlinked by design — Story 23.2 owns that register.
- Do not mark this story done before the four Design pushes exist to register.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| after register | herald deck status --repo-root . | fourteen linked | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-deck-family-lockstep CAP-4` (folded 2026-09-17 into `spec-pyforge-herald` **CAP-23** — same intent, new home; `spec-deck-family-lockstep/.memlog.md` stays the CAP-4 historical record per its own fold note, so this story's landing entry goes there, not the new file).
Surface: presentations/{unity-data-stack,wasm-analytics-stack,deckcraft,presenton-pixi-image}/README.md; .herald/bridge-state.json bootstrap..
Ledger key: `21-10-the-registry-sees-all-fourteen-decks`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-21-10-the-registry-sees-all-fourteen-decks.md`.

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/registry.py:137` -- `register(readme_path, project_name, project_id, file_url)`. Replaces the **whole span** from the `## Design project (the bridge's far end)` heading through the next `#`-prefixed line (any level) or EOF. A `### Provenance` boundary must already exist right after the intended 2-line body *before* calling `register`, or everything below the heading (tables, ledger prose) is destroyed -- this is why the fix is "insert `### Provenance` first, then register," not "register, then reorganize."
- `presentations/wasm-analytics-stack/README.md:51-73` -- malformed span (multi-line project sentence + inline pull instructions + Seeded table + note) before `## Ledger` at line 74.
- `presentations/deckcraft/README.md:48-74` -- same shape (the story's "24-line body"), before `## Ledger` at line 75.
- `presentations/presenton-pixi-image/README.md:49-75` -- same shape before `## Ledger` at line 76; line 71 has a garbled sentence fragment ("**seeded 2026-07-25 via DesignSync (byte-exact localPath upload).dc.html`, ...") -- preserve verbatim under `### Provenance`, do not rewrite (out of scope for this story).
- `presentations/unity-data-stack/README.md:48-58` -- **already compliant** (Story 21.6 added `### Provenance` 2026-09-17). This is the worked template: 2-line body, then `### Provenance` (no blank line needed), then preserved prose. No edit needed; `registry.read()` on it already succeeds -- verify only.
- `presentations/pyforge-warden/README.md:73-81` -- second worked example (blank line variant before `### Provenance`), confirms both spacings parse.
- `docs/specs/presentation-deck.md:153-165` -- the bootstrap snippet (glob `presentations/pyforge-*/README.md` only matches the ten `pyforge-*` decks) and the stale prose "the four chain decks sit there deliberately" (line 164-165) -- both need updating so the four chain decks are enumerated and swept, `agentic-sdlc` remains the only deliberately-unlinked one.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py:1120-1190` -- `_status_for_slug`/`_known_slugs`: `linked` is read **solely** from `.herald/bridge-state.json` (never calls `registry.read` itself), which is why re-running the bootstrap after registering is mandatory, not optional.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/state.py:41,46` -- `DEFAULT_STATE_PATH = Path(".herald/bridge-state.json")` (gitignored, absent in a fresh worktree/clone), `DeckState(project_id, etags, last_pull)`, `write(state_path, slug, DeckState)`.
- `src/shared/packages/pyforge-herald/tests/unit/test_registry.py` -- existing `register`/`read` unit coverage; no new test needed here since neither function's behavior changes, only the README content does (a `tests/` addition would be testing content, not code -- Simplicity First).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-lockstep/.memlog.md` -- append the CAP-4 landing entry here (see Binding).

## Tasks & Acceptance

**Execution:**
- `presentations/wasm-analytics-stack/README.md` -- insert `### Provenance` right after where the canonical 2-line body will sit, moving the existing "bound to Modernist / pull it with the MCP bridge" sentence + Seeded table + note under it unchanged; then call `registry.register(path, "Wasm Analytics Stack deck", "45c841c6-e807-4fee-a92a-f8e89cb890b4", "https://claude.ai/design/p/45c841c6-e807-4fee-a92a-f8e89cb890b4?file=Wasm+Analytics+Stack.dc.html")` -- rewrites the heading's span to the canonical 2 lines, leaving `### Provenance` and everything under it untouched.
- `presentations/deckcraft/README.md` -- same treatment with `("Deckcraft deck", "59c42e9c-7c90-431d-adae-b0021dd3f727", "https://claude.ai/design/p/59c42e9c-7c90-431d-adae-b0021dd3f727?file=Deckcraft.dc.html")`.
- `presentations/presenton-pixi-image/README.md` -- same treatment with `("Presenton, Conda-Native deck", "c824a332-8e43-4b17-bf84-f38307085289", "https://claude.ai/design/p/c824a332-8e43-4b17-bf84-f38307085289?file=Presenton+Conda-Native.dc.html")`.
- `docs/specs/presentation-deck.md` -- widen the bootstrap snippet to also sweep the four chain-deck READMEs by explicit slug (not a wider glob, so `agentic-sdlc` is never accidentally swept); correct the stale "four chain decks sit there deliberately" sentence to name `agentic-sdlc` (owned by Story 23.2) as the only deliberate holdout.
- Run the updated bootstrap snippet once (repo root as cwd) to populate `.herald/bridge-state.json` for `unity-data-stack`, `wasm-analytics-stack`, `deckcraft`, `presenton-pixi-image` (none is `pyforge-*`-prefixed, so none is covered by the original loop -- all four need the widened sweep).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-lockstep/.memlog.md` -- append a landing entry recording all fourteen decks linked and the two doc/code touch points.

**Acceptance Criteria:**
- Given the three re-registered READMEs, when `pyforge.herald.registry.read()` is called on each, then it returns a `DesignProject` with no `HeraldError` (exactly two body lines).
- Given the widened bootstrap has been run once against this worktree, when `herald deck status --repo-root .` runs, then all fourteen `presentations/*` decks except `agentic-sdlc` report `linked: true` with the correct `project_id`, and `agentic-sdlc` reports `linked: false` (untouched, Story 23.2's).
- Given a fresh clone (no `.herald/bridge-state.json`), when the bootstrap snippet in `docs/specs/presentation-deck.md` is run, then it reproduces the same fourteen linked entries from the READMEs alone -- no other state is consulted.
- Given the existing `test_registry.py` suite, when it is re-run after the README edits, then it still passes unchanged (the module's behavior is not touched, only content).

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test -k registry` -- expected: all `registry.py` unit tests still pass (module code is unchanged; this guards against an accidental typo in the manual edits breaking the round-trip in a way the CLI check below wouldn't isolate).
- `pixi run -e pyforge-herald python -c "from pyforge.herald import registry; from pathlib import Path; [print(p, registry.read(p)) for p in sorted(Path('presentations').glob('*/README.md'))]"` -- expected: every chain deck + pyforge-* deck prints a `DesignProject(...)`; `agentic-sdlc` and any other never-registered deck prints `None`; no `HeraldError` traceback.
- `pixi run -e pyforge-herald herald deck status --repo-root .` -- expected: JSON array with all fourteen target decks (`unity-data-stack`, `wasm-analytics-stack`, `deckcraft`, `presenton-pixi-image` + the ten `pyforge-*`) at `linked: true`; `agentic-sdlc` at `linked: false`.

**Manual checks (if no CLI):**
- Diff each edited README against its pre-edit version to confirm no content (Seeded tables, Ledger sections, historical notes) was lost -- only reorganized under `### Provenance` and the 2-line body normalized.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 12 findings — high 0, medium 4, low 6, false 2, maybe-false 0
- findings:
  - `[low]` `[reject]` Frontmatter `warnings` comment says "four README edits" but only three READMEs were actually edited (`unity-data-stack` needed none) — fix is to edit this build's spec's own comment text.
  - `[low]` `[reject]` Acceptance Criteria wording ("all fourteen `presentations/*` decks except `agentic-sdlc`") reads ambiguously as fourteen-total-including-`agentic-sdlc` rather than fifteen-total/fourteen-linked — fix is to reword this build's own spec text.
  - `[low]` `[reject]` Pre-existing stray double period in the spec's own Binding "Surface:" line ("bootstrap..") — fix is to edit this build's spec; the typo predates this diff (this run never touched that line).
  - `[low]` `[defer]` `presentations/presenton-pixi-image/README.md:71` carries a garbled, truncated sentence fragment under Provenance — verified pre-existing (byte-unchanged by this diff) and explicitly out of this story's registry-linking scope per the Code Map's own note; logged to frontmatter `deferred:`.
  - `[false]` `[reject]` Claimed gap: no sprint/status ledger update reflects the `in-review` transition — refuted: ledger sync (`sprint-status.yaml` / `sprint-status-ledger.yaml`) is the orchestrator's/sprint-planning's own bookkeeping, not a per-story bmad-build-auto responsibility, and this run's own invocation explicitly forbids writing `sprint-status.yaml`.
  - `[false]` `[reject]` Claimed gap: `context:` frontmatter omits the touched memlog/CAP-23 host spec — refuted: per `spec-template.md`'s own doc-comment, `context:` lists pre-implementation reading material for the implementer, not an exhaustive touched-file manifest; the memlog edit is already fully specified in `## Tasks & Acceptance`.
  - `[low]` `[patch]` `docs/specs/presentation-deck.md`'s bootstrap snippet called `sorted()` on only the `pyforge-*` glob, then appended the four chain-deck paths unsorted, producing a non-deterministic-looking final order despite the `sorted()` call — fixed by sorting the combined list once, at iteration time.
  - `[low]` `[reject]` Claimed gap: Code Map doesn't explain `_known_slugs`'s enumeration, leaving it "unverifiable" whether `agentic-sdlc` appears explicitly as `linked: false` — fix is to expand this build's spec's Code Map prose; also empirically moot (verified live: `agentic-sdlc` does appear explicitly at `linked: false`).
  - `[medium]` `[patch]` `docs/specs/presentation-deck.md`'s bootstrap snippet called `registry.read(readme)` with no exception handling, so any one malformed README (a documented recurring failure mode — see `unity-data-stack`'s own incident note) would crash the entire loop and leave every later deck's bridge-state unwritten, contradicting the adjacent prose's own claim that a malformed section "is reported unlinked rather than guessed at" — fixed by wrapping the call in `try/except HeraldError: continue`.
  - `[medium]` `[patch]` Verification-gap layer (pre-verified): no automated test asserted `registry.read()` succeeds against the real `presentations/*/README.md` files this story edited — only a manual CLI one-liner in `## Verification` proved it, so a future regression would ship undetected by CI — fixed by adding `src/shared/packages/pyforge-herald/tests/meta/test_deck_registry_sections.py`.
  - `[medium]` `[patch]` Grouped with the prior row (same root cause): the diff's evidence that "fourteen decks report `linked: true`" rested only on the memlog's self-report prose, with no committed artifact independently verifying it — the same new test closes this gap.
  - `[medium]` `[patch]` `docs/specs/presentation-deck.md`'s new prose ("`agentic-sdlc` is the only deck left unregistered by design") retained the exact "by design" framing the intent-contract's own Never boundary prohibits ("Do not declare agentic-sdlc unlinked by design") — fixed by rewording to "the only deck still unregistered — Story 23.2 owns that register."

## Auto Run Result

**Summary:** Fixed the three malformed chain-deck README registry sections (`wasm-analytics-stack`, `deckcraft`, `presenton-pixi-image`) by inserting a `### Provenance` boundary right after the canonical 2-line body and calling `registry.register()`, preserving all existing prose/tables untouched below it. `unity-data-stack` needed no edit (already compliant since Story 21.6). Widened the fresh-clone bootstrap snippet in `docs/specs/presentation-deck.md` to sweep the four chain decks by explicit slug, corrected its stale "sit there deliberately" prose, hardened it against a future malformed README (`try`/`except HeraldError`), and fixed its misleading partial `sorted()` call. Added a regression test guarding the real `presentations/*/README.md` tree. Landed a CAP-4 memlog entry.

**Files changed:**
- `presentations/wasm-analytics-stack/README.md` — registry section normalized to 2-line body + `### Provenance`.
- `presentations/deckcraft/README.md` — same.
- `presentations/presenton-pixi-image/README.md` — same.
- `docs/specs/presentation-deck.md` — bootstrap snippet widened to the four chain decks, hardened against `HeraldError`, sort fixed, stale prose corrected without the prohibited "by design" framing.
- `src/shared/packages/pyforge-herald/tests/meta/test_deck_registry_sections.py` — new regression test: every real deck README parses via `registry.read()` or is explicitly allowlisted (`agentic-sdlc`).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-lockstep/.memlog.md` — CAP-4 landing entry appended.

**Review findings breakdown:**
- 12 findings from 4 layers (Blind Hunter 8, Edge Case Hunter 1, Verification Gap 1, Intent Alignment 2).
- 4 patched: bootstrap `sorted()` ordering fix (low); bootstrap `try/except HeraldError` hardening (medium); new regression test closing the no-automated-verification gap, grouped from 2 findings (medium); reworded "by design" phrasing to comply with the Never boundary (medium).
- 1 deferred: pre-existing garbled sentence fragment in `presentations/presenton-pixi-image/README.md:71`, out of scope, logged to frontmatter `deferred:`.
- 5 rejected: three spec-text-only nitpicks (rejected per "fix is to edit this build's spec" — the "four README edits" comment miscount, the fourteen/fifteen AC wording, the pre-existing stray double period), one spec-text completeness claim also rejected on the same basis (Code Map's `_known_slugs` explanation, also empirically moot), and two false claims (a sprint/status-ledger update — explicitly out of scope and forbidden by this run's own invocation; a `context:` completeness claim — refuted by the field's own documented purpose).

**Follow-up review recommendation:** `true`. Three medium-severity entries were patched on this first pass, meeting the two-or-more-medium threshold. Specific unverified risk: the patches (bootstrap hardening, the new regression test, and the reworded prose) were authored and verified by the same session that ran this review, not by an independently re-engaged implementation subagent — a follow-up pass should independently confirm the new test's `DELIBERATELY_UNREGISTERED` allowlist design (a hardcoded skip-list) doesn't mask a future deck that should be linked but silently isn't, and that the `try/except HeraldError` swallow in the bootstrap snippet doesn't hide a real future regression behind a quiet "unlinked" status.

**Verification performed:**
- `pixi run -e pyforge-herald pyforge-herald-test -k registry` — 72/72 passed, both before and after patches.
- `pixi run -e pyforge-herald pyforge-herald-test` (full suite) — 1369 passed, 4 skipped (includes the new `test_deck_registry_sections.py`).
- `registry.read()` swept over every `presentations/*/README.md` — all fourteen target decks return a `DesignProject`, `agentic-sdlc` returns `None`, no `HeraldError`.
- Simulated a fresh clone (`.herald/` removed) and ran the widened, hardened bootstrap snippet verbatim — `herald deck status --repo-root .` reports exactly 14 `linked: true` (with correct `project_id`s) and `agentic-sdlc` `linked: false`.
- Diffed every edited README against its pre-edit content — no material lost, only reorganized under `### Provenance`.

**Residual risks:** See the follow-up review recommendation above. Additionally, the deferred garbled-prose fragment in `presenton-pixi-image/README.md` remains unfixed (tracked, low severity, does not affect registry parsing).
