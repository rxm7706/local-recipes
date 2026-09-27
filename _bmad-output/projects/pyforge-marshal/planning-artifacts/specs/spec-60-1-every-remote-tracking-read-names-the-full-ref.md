---
title: '60.1: Every remote-tracking read names the full ref'
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** git resolves a short name like `origin/main` to a local branch or tag of that name before the remote-tracking ref `refs/remotes/origin/main`. Stories 57.1 (`refresh`) and 59.1 (the landing heal) each closed this trap in one place. A sweep on 2026-09-27 found marshal still hands git the short name in:
- dispatch verify's scope diff (`_SCOPE_BASE`);
- dispatch land's behind-count, merge-tree preview and changed files (`_ORIGIN_MAIN`);
- the dispatch supervisor's scope base;
- the dispatch worktree base, landing subjects and ledger fallback read (`cli/dispatch.py`);
- deploy's push-route subjects;
- `spec_text_at_ref`'s default ref;
- land's ledger read and loop-home fast-forward;
- the sprint-ledger promotion publish, `commit_paths_onto_remote_tip` — a write: it builds a commit on the tip it resolves and pushes it (found by review 1);
- `watch`'s loop-branch read (found by review 1).

A stray local `origin/main` would make each of these read, diff or fast-forward to a commit the remote never had.

**Approach:** a new pure module `core/refs.py` defines:
- `remote_tracking_ref(branch, remote="origin") -> "refs/remotes/<remote>/<branch>"`;
- `ORIGIN_MAIN = remote_tracking_ref("main")`;
- `ORIGIN_MAIN_SHORT = "origin/main"` for messages.

Every call site above reads a ref from it. The two private copies, `adapters/vcs_git._ORIGIN_MAIN_REF` and `dispatch_land._ORIGIN_MAIN_REF`, become the shared constant. Human-facing finding messages keep saying `origin/main`.

Ledger key: `60-1-every-remote-tracking-read-names-the-full-ref`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-270 (FR-216); CAP-267 (57.1), CAP-269 (59.1).

## Acceptance Criteria

- Given a local branch named `origin/main` on an unverified commit When dispatch verify computes its scope diff Then it diffs against the remote-tracking tip
- Given the same shadow When dispatch land counts behind and previews the merge Then both use the remote-tracking tip
- Given the same shadow When land fast-forwards a loop home Then the home lands on the remote-tracking tip, not the shadow's commit
- Given the package source When scanned Then no expression outside `core/refs.py` builds a short remote ref — string, f-string, concatenation, `%`-format or `"/".join` (a meta test pins it, every known spelling in its self-test)
- Given a local branch or tag named `origin/main` one commit ahead of the remote When the ledger is published onto the remote tip Then the remote's `main` never receives the shadow's commit
- Given no shadowing ref When any of these runs Then its behaviour is unchanged

## Boundaries & Constraints

**Always:** one helper in `core/`; the refname is full wherever git reads it; messages keep `origin/main`.

**Never:**
- Do not change what is fetched, pushed or merged when no shadow exists.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no shadow | ordinary repo | identical results | — |
| local branch `origin/main` | on an unverified commit | ignored by every read | — |
| local tag `origin/main` | on an unverified commit | ignored by every read | — |
| publish with a shadow ahead | branch or tag `origin/main` one commit ahead | the promotion commit is built on the remote tip; the shadow never reaches the remote | — |
| `--base release` (land, refresh) | `refs/remotes/origin/release` | full refname via the helper | a missing ref fails as before |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-270 (FR-216).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (night) — Proposed: marshal names the remote's branch, never a name something local can wear*.
Ledger key: `60-1-every-remote-tracking-read-names-the-full-ref`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

### Review 1 — 2026-09-27, independent adversarial reviewer, working tree on `dispatch-full-refname` — FAIL (1 high, 2 medium)

Verified clean: with no shadow every changed call site behaves identically (worktree add `--no-track`, behind-count, subjects, three-dot diffs, merge-tree oid, `show`, fast-forward; a missing remote fails the same way); `refresh`'s `tip_ref` and `ORIGIN_MAIN_SHORT` reach messages only; no short refs in TOML/YAML/JSON/shell under the package; nothing outside the package calls these paths; `core/refs.py` is pure (AD-4 holds).

- `[high]` `[patch]` **The ledger-promotion publish built on the short name and pushed** — `commit_paths_onto_remote_tip` resolved `{remote}/{ref}`; a branch or tag shadow one commit ahead was published onto the remote's `main`. **Fix:** `remote_tracking_ref(ref, remote)^{commit}`; `test_publishing_onto_the_remote_tip_never_carries_a_shadow[branch|tag]`.
- `[medium]` `[patch]` **`cli/watch.py` rev-parsed `origin/loop/<slug>`** — `remote_tracking_ref(f"loop/{slug}")`.
- `[medium]` `[patch]` **The meta matcher caught only two spellings** — it now flags any whitespace-free string, f-string, `+`, `%` or `"/".join` building `<rev>..origin/…` or `{remote}/{…}`; `test_the_scan_catches_every_spelling_and_spares_messages` pins ten spellings (both live ones) and four non-refs.
- `[low]` `[patch]` The planning text overclaimed until the above — CAP-270, the Story's Surface, this spec's Intent and AC amended.
- `[low]` `[patch]` The real-git tests were adapter-level and the behind-count case did not separate short from full — the behind-count test now puts the shadow where the home is (short: 0, full: 1); tag shadows added; the module docstring says what each layer proves.
- `[nit]` `[patch]` Stale docstrings (`vcs_git`, `ports/vcs`, `deploy`), `cli/init.py`'s operator hint (now `refs/remotes/origin/main`), `dispatch_land` importing another module's private name, `display_ref`'s join. `[nit]` `[note]` The fast-forward reflog now names the full ref; `VcsCommandError` text inside MRS-DISP-044 carries it; nothing parses either.
