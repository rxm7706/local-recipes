---
deferred_work_file: '{implementation_artifacts}/deferred-work.md'
---

# Step 4: Review

## RULES

- YOU MUST ALWAYS SPEAK OUTPUT in your Agent communication style with the config `{communication_language}`
- No human interaction: do not ask questions or wait for approval in this step.
- All review subagents must run at the same model capability as the current session.

## INSTRUCTIONS

Change `{spec_file}` status to `in-review` in the frontmatter before continuing.

### Construct Diff

Read `{baseline_revision}` from `{spec_file}` frontmatter. If `{baseline_revision}` is missing or `NO_VCS`, use best effort to determine what changed. Otherwise, construct `{diff_output}` covering all changes — tracked and untracked — since `{baseline_revision}`.

Do NOT `git add` anything — this is read-only inspection.

### Review

Launch Blind Hunter and Edge Case Hunter in parallel without prior conversation context.

- **Blind Hunter** — prompt:
  > Invoke the `bmad-review-adversarial-general` skill on this diff:
  >
  > {diff_output}
- **Edge Case Hunter** — prompt:
  > Invoke the `bmad-review-edge-case-hunter` skill on this diff:
  >
  > {diff_output}

### Classify

1. Deduplicate all review findings.
2. Assign severity to each finding by consequence for the artifact's main consumer (software user, document reader, etc).
   Disregard any severity assigned by a reviewing subagent. Review subagents operate under by-design information asymmetry and do not have enough context to set final severity for this workflow.
   - `low`: none or cosmetic
   - `medium`: tolerable
   - `high`: intolerable
3. Route each finding into exactly one triage category. The first three categories are **this story's problem** — caused or exposed by the current change. The last two are **not this story's problem**.
   - **intent_gap** — caused by the change; cannot be resolved from the spec because the captured intent is incomplete. Do not infer intent unless there is exactly one possible reading.
   - **bad_spec** — caused by the change, including direct deviations from spec. The spec should have been clear enough to prevent it. When in doubt between bad_spec and patch, prefer bad_spec — a spec-level fix is more likely to produce coherent code.
   - **patch** — caused by the change; trivially fixable without human input. Just part of the diff.
   - **defer** — pre-existing issue not caused by this story, surfaced incidentally by the review. Collect for later focused attention.
   - **reject** — noise. Drop silently. When unsure between defer and reject, prefer reject — only defer findings you are confident are real.
4. Append a new entry to the `## Review Triage Log` section in `{spec_file}`, in this format:
   ```markdown
   ### {date} — Review pass
   - intent_gap: count
   - bad_spec: count
   - patch: count
   - defer: count
   - reject: count
   - addressed_findings:
     - `[high|medium|low]` `[patch|bad_spec]` <finding summary and action taken in this pass>
   ```
   Where `count` is either just `0`, or total with breakdown by severity `N: (high Nhigh, medium Nmedium, low Nlow)`.
   If no patch was fixed and no bad_spec repair loopback was triggered in this pass, write:
   ```markdown
   - addressed_findings:
     - none
   ```
5. Process findings in cascading order. If intent_gap exists, lower findings are moot; follow the intent_gap branch below. If bad_spec exists, lower findings are moot since code will be re-derived. If neither exists, process patch and defer normally. Before each bad_spec loopback, read `{spec_file}` frontmatter `review_loop_iteration` (missing means `0`), increment it by 1, and write it back. If it exceeds 5, append the triage-log entry for this pass with `addressed_findings: none`, then HALT with status `blocked` and blocking condition `review repair loop exceeded 5 iterations (non-convergence)`.
   - **intent_gap** — Root cause is inside `<intent-contract>`. Revert code changes. Append the triage-log entry for this pass with `addressed_findings: none`, then HALT with status `blocked`, blocking condition `intent gap in intent contract`, and include the intent-gap findings.
   - **bad_spec** — Root cause is outside `<intent-contract>`. Do not modify content inside `<intent-contract>`. Before reverting code: extract KEEP instructions for positive preservation (what worked well and must survive re-derivation). Revert code changes. Read the `## Spec Change Log` in `{spec_file}` and strictly respect all logged constraints when amending the sections outside `<intent-contract>` that contain the root cause. Append a new change-log entry recording: the triggering finding, what was amended, the known-bad state avoided, and the KEEP instructions. Append the triage-log entry for this pass, listing every bad_spec finding that triggered the spec amendment and implementation loopback under `addressed_findings`. Read fully and follow `./step-03-implement.md` to re-derive the code, then this step will run again.
   - **patch** — Auto-fix. These are the only findings that survive loopbacks. After auto-fixing, append the triage-log entry for this pass, listing every patch fixed in this pass under `addressed_findings`.
   - **defer** — Append one new entry to `{deferred_work_file}` using the format below. Do not modify existing entries or look for duplicate content — that check is a judgment call about substance, separate from the mechanical id-uniqueness scan below, which is always required.

     Handle defer findings strictly one at a time: mint the id, then write the complete entry — heading and fields together, in a single append — before minting the next finding's id. Never append the fields first and add the heading afterwards; an interrupted two-step write leaves exactly the anonymous `- source_spec:` bullet this procedure exists to eliminate.

     Minting the id — every new entry must carry a unique id; never append an anonymous `- source_spec:` bullet.
     1. Resolve the active station: run `python3 {project-root}/_bmad/scripts/resolve_config.py --project-root {project-root} --key project`, read **stdout only** (a warning line on stderr must not reach the JSON parse), and take `.project.slug` from it. Keep that raw value — the `pyforge-`-stripped form of it is used only for the mason-vs-other branch test in step 3, never for the path cross-check below. If the command fails, or stdout has no non-empty `.project.slug` (including an empty `{}`), treat the station as unknown. Resolution honors `BMAD_ACTIVE_PROJECT` and then the active-project marker, which is per-working-tree mutable state — normally written once at worktree setup, but not immutable, and it can name a different station in a different tree than the one you are running in. Treat the answer as best-effort, never as an invariant, and always resolve it against this run's `{project-root}`.

        Then cross-check the answer against the file you are about to append to, because the station name and the destination path come from two independently-mutable pieces of per-worktree state: the slug above comes from the active-project marker, while `{deferred_work_file}` resolves through the `_bmad-output/implementation-artifacts` **symlink**. These have desynced in production. Resolve the real path (`readlink -f {deferred_work_file}`) and require its `projects/<slug>/` component to equal the **raw, unstripped** slug. The project directories are named `pyforge-doctor`, `pyforge-mason`, and so on, so comparing the `pyforge-`-stripped form against them can never match and would declare every station unknown on every run — making the mason branch unreachable. Strip `pyforge-` only for the mason-vs-other branch test in step 3. If they disagree, treat the station as unknown and say so in `evidence:` — never mint station A's id shape into station B's ledger.

        `readlink -f` prints nothing and exits non-zero when a **parent directory** of the path is missing; it succeeds when only the final filename is absent. A station taking its first-ever defer legitimately has no `implementation-artifacts/` directory yet, so on an empty result resolve the nearest existing ancestor and take the `projects/<slug>/` component from that. An unresolvable path is a not-yet-created one, not a desync, and must not silently degrade a brand-new station to unknown.
     2. Derive `{story}` from `{spec_file}`'s filename: strip a leading `spec-` if present, then match exactly two leading numeric groups plus an optional single trailing letter (`<digits>-<digits><letter>?`) — both groups can be multi-digit (e.g. `spec-6-10-....md` → `6-10`, not `6-1`), and matching stops at the second group (e.g. `spec-2-1-3-way-merge-....md` → `2-1`, not `2-1-3`). Keep the letter: `pyforge/marshal/core/identity.py` is this repo's sole owner of the story-key format, its key shape is `<epic>-<seq><letter>?`, and its `promoted_id` renders `DW-FU-6-1a` — dropping the letter would mint story `6-1a`'s deferral under story `6-1`'s id, conflating two distinct stories. (Silently truncating a letter-suffixed key is the documented AD-38 incident; no such spec file exists in the fleet today, so this is a latent shape, not a live one.) If the filename does not begin with such a key, use the whole filename stem instead (the name without its `.md` extension, `spec-` already stripped). But take the stem only when it actually identifies the spec: durable story specs live at `planning-artifacts/specs/spec-<slug>/SPEC.md`, whose stem is the constant `SPEC` — every one of the fleet's 57 such specs would collapse onto the same id, destroying the provenance the id exists to carry. When the stem is empty or is a generic container name (`SPEC`, `spec`, `README`, `index`), use the **parent directory** name instead (`spec-` stripped the same way), which is the slug that names the spec. Either way, replace every character outside `[A-Za-z0-9-]` with `-`, collapse runs of `-`, and trim leading/trailing `-`, so the id stays a single parseable token that no consumer's `rstrip("-")` can fold onto a different id. `{story}` must be non-empty when this finishes: an empty one mints an id with nothing after the prefix, which the harvest reads as the bare phantom described at the end of this bullet. If sanitizing empties it, use the parent directory name instead, sanitized the same way.
     3. Re-read `{deferred_work_file}` fresh — including any entry appended earlier in this same pass — immediately before minting each id, and collect the ids already in play to pick the next one.

        Collect **every `DW-` token anywhere in the text, not only the ones in headings** — this is the set the consumers actually see. `pyforge/doctor/sources/chain.py::_ids` (the deferred-work detector, whose `_ENTRY_RE` is `^#{2,4}\s+DW-…` for headings but whose `_DW_RE` harvest is file-wide) tokenizes with `\bDW-[A-Za-z0-9][A-Za-z0-9-]*` and then `rstrip("-")`s the result, so an id cited only inside an earlier entry's `evidence:` prose counts just as much as one in a heading. Scanning headings alone is measurably unsafe: doctor's Tier-3 file mentions four follow-up ids (`DW-FU-6-4`, `-6-5`, `-6-6`, `-6-8`) in prose with no matching heading, so a heading-only scan would happily mint one of them again and silently conflate a generic defer with an unrelated follow-up promotion. Apply the same `rstrip("-")` when comparing, so a trailing separator cannot hide a collision.

        Harvest the tokens; do not read the files whole. `grep -ohE '\bDW-[A-Za-z0-9][A-Za-z0-9-]*' <files> | sort -u` satisfies this step exactly — it is the detector's own pattern — and is the preferred form. These ledgers are large (136 KB and 146 KB in this repo today) and this step runs once per defer finding, so reading them in full would spend the pass's remaining budget on prose you have no use for.

        Collect from the station's **tracked** ledger as well as from `{deferred_work_file}`. Resolve it as the sibling of the **resolved** Tier-3 path — `<directory of readlink -f {deferred_work_file}>/../planning-artifacts/deferred-work-ledger.md` — never as a worktree-relative `_bmad-output/planning-artifacts/…`. In a bmad-loop run worktree those are different files: `implementation-artifacts` symlinks out to the shared checkout while `planning-artifacts` is a worktree-local git checkout frozen at the branch point. Measured in this repo: the worktree-local copy is 16 KB against the shared copy's 28 KB and is missing six ids the shared one carries. An id that already exists in the tracked ledger belongs to a different, already-recorded item; reusing it makes the new entry masquerade as that one, pass the tier3-vs-tracked comparison, and become uncloseable.

        If a file does not exist, treat its contribution as empty — the append creates `{deferred_work_file}`, and a station's first-ever defer legitimately has no tracked ledger. But an **unreadable** file is not an absent one: if a read fails for any reason other than non-existence (permissions, a dangling symlink target), do not treat it as empty — that mints a duplicate over an id you simply could not see. Open the `evidence:` note with the literal token `ledger-unread:` and mint with a fresh `-<n>` suffix beyond any id you did manage to read. If the failure left you with no ids at all, treat the base id as already taken and start at `-2`, since you cannot see whether it is.

        Compare ids as **complete tokens**, never as bare string prefixes: an id runs to the end of its `DW-` token, so `DW-FU-4-14` is not an occurrence of `DW-FU-4-1`.

        Call the id you would mint without any suffix the **base id**. A collected id counts toward the suffix number only when it is exactly the base id, or the base id followed by `-` and a remainder that is **one plain integer and nothing else**. Judge the whole remainder after the base id, never just the last segment: mason's ledger carries `DW-1-10-1`, whose last segment is the integer `1` but whose remainder after the base `DW-1-1` is `0-1` — that id belongs to story `1-10`, not story `1-1`, and must take no number out of circulation for it. Anything else (a `-draft` suffix, a longer numeric tail) is likewise ignored and reserves nothing. A collected bare base id counts as suffix `1` — that rule is about the base id itself, not about its trailing characters, so it holds identically whether `{story}` is numeric (`7-1`) or a fallback slug (`deferred-work-visibility`, whose trailing segment is not an integer).
        - **mason** — base id `DW-{story}`; always mint a suffix, `DW-{story}-<n>`, where `<n>` is one past the highest counting suffix, compared numerically not lexicographically (start at `1` if none count).
        - **every other station, including unknown** — base id `DW-FU-{story}`; mint it bare unless it or a `DW-FU-{story}-…` id was collected, in which case mint `DW-FU-{story}-<n>` one past the highest counting suffix, compared numerically. If the bare id was collected and nothing else counts, that gives `-2`; never re-mint the bare id you just collected.

        Both branches draw on the single collected id set from step 3 — every `DW-` token from both files, not just headings. Re-reading fresh narrows, but cannot fully eliminate, a race against another concurrent worktree minting into the same station's file at the same instant — that residual is accepted, matching how this file is already shared read/append across worktrees elsewhere in this workflow.

     Head the entry with the minted `{id}`, repeating the same sentence used for `summary:` as the heading title:
     ```markdown
     ### {id}: <one sentence>
     - source_spec: `{spec_file}`
       summary: <one sentence>
       evidence: <why this is real>
     ```
     If the station could not be resolved in step 1, say so in `evidence:`, opening the note with the literal token `station-unresolved:` — the fallback shape is indistinguishable afterwards from a correctly-resolved non-mason id, so without a fixed token to grep for, the degradation stays unobservable no matter how it is worded.

     In the heading title and the `summary:`/`evidence:` prose alike, never write `DW-` immediately followed by a letter or digit unless you mean that exact, real id. The heading is not exempt: it repeats the `summary:` sentence verbatim, so a shape token written there lands in the file twice. The detector's harvest (`chain.py::_ids`, named in step 3) takes every `DW-…` token anywhere in the file, not only headings, so an illustrative token like `` `DW-B<n>` `` mints a phantom deferral (`DW-B`) with no tracked twin and reds the deferred-work check. Note this bites the very shapes this procedure names: writing `` `DW-FU-<story>` `` in prose yields the phantom `DW-FU`, because the harvest stops at the first non-alphanumeric and strips the trailing `-`. Write shape placeholders so the character after `DW-` is not alphanumeric (`` `DW-<story>-<n>` `` is safe), or describe the shape in words.
   - **reject** — Drop silently.

## Finalize

Prepare `Auto Run Result` details:
- Summary of implemented change
- Files changed with one-line descriptions
- Review findings breakdown: patches applied, items deferred, items rejected
- Follow-up review recommendation: `true` when the final review pass made review-driven changes significant enough to benefit from an independent follow-up review; otherwise `false`. Use judgment, not a fixed numeric threshold. Base the judgment on the final pass's triage log and fixes, including patched-finding volume, consequence/severity, breadth, behavior/API/security/data impact, and implementation complexity. Many low-severity patched findings can be significant by volume. Do not recommend follow-up for only a few localized low-consequence fixes.
- Verification performed, including command outcomes or manual inspection notes
- Any residual risks

Set `{spec_file}` frontmatter `followup_review_recommended` from the judgment above.

If version control is available, commit. Do not push.

Capture `final_revision` (current HEAD after committing, or `NO_VCS` if version control is unavailable) into `{spec_file}` frontmatter.

Set `{spec_file}` frontmatter `status: done`.

HALT with status `done`.
