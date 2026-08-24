---
doc_type: deferred-work-ledger
project: pyforge-steward
date: 2026-07-31
status: promoted-verbatim
---

# pyforge-steward — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-31 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown. Until today this project had **no tracked
ledger at all**, so its entire deferred-work record — 21 KB, 21 entries — existed
only in scratch space. Produced by the 2026-07-30/31 six-station fleet run and found
by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current.

**The one intentional edit is id assignment.** bmad-loop's damping output writes either
no id or a generic `DW-<n>`, which collides the moment another story is damped. Each
entry here is keyed `DW-<story>-<n>` from its own `source_spec`, per the convention the
sibling ledgers and the detector both use.

---

### DW-1-2-1

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: `keys.py`'s drift-detection **assignment**-recognition (`_find_credential_assignments`) only recurses into `ast.If` bodies and only matches a literal `subscript[key] = os.environ-sourced-value` shape — a credential attachment nested inside `for`/`while`/`try`/`with`, or expressed via `.update(...)`, dict-merge (`{**headers, "X": ...}`), `.setdefault(...)`, or passed directly as a kwarg (`requests.get(url, headers={"X": os.environ["Y"]})`) with no intermediate subscripted variable, would bypass detection entirely even with zero scope gate present.
  evidence: Confirmed by hand-tracing `_find_credential_assignments` in `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` — it only branches on `ast.Assign`/`ast.If`, nothing else. Found by both review agents during Story 1.2's review pass 2026-07-30. Same "Never: not a pluggable rule engine" scope boundary as the gate-recognition gap above; worth hardening together if Story 1.6's `audit --drift` CLI verb is ever pointed at more than `_http.py` itself.
  status: open

### DW-1-2-2

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: `HostScopedCredential` carries no field identifying which specific credential/env-var it represents (only `hosts`) — `resolve_headers` returns whatever `_http.py`'s `auth_headers_for` happens to resolve for a matched host, so two credentials with overlapping host sets are indistinguishable and there's no way to label an entry for display/audit purposes.
  evidence: `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `HostScopedCredential` dataclass has only a `hosts: tuple[str, ...]` field. Story 1.5's own AC (`_bmad-output/planning-artifacts/epics.md`, Story 1.5) already requires `steward keys list` to enumerate "that identity's name, scope, last-rotated timestamp" — so a `name` field will need to land on this dataclass (or its Story-1.5 inventory counterpart) regardless; flagged now so Story 1.5 doesn't rediscover it from scratch.
  status: open

### DW-1-2-3

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: `resolve_headers` gates *whether* ambient auth attaches, not *which* credential — an in-allowlist URL receives whatever `_http.py`'s host-blind chain resolves first (JFROG_API_KEY at priority 1 for ANY host), so a credential allowlisting a non-JFrog host (e.g. `github.com`) ferries the ambient JFrog key to that host. Distinct from the earlier no-identity-field entry (display/audit labeling): this is about which header attaches. Spec-conformant (the story's Boundaries mandate full delegation and host-membership-only decisions, and the wrapper strictly narrows the ungated baseline), so not fixable this story — needs a per-credential header-selection design decision in a later keys story, likely landing together with the Story-1.5 identity field.
  evidence: Confirmed by execution 2026-07-30 (Story 1.2 follow-up review): `resolve_headers(HostScopedCredential(hosts=("github.com",)), "https://github.com/x")` with `JFROG_API_KEY` set returned `{'X-JFrog-Art-Api': ...}`. `_http.py`'s own `auth_headers_for` docstring documents step-1 JFrog injection as "the documented cross-resolver leak". A docstring scope note was added to `HostScopedCredential` this pass so callers are not misled meanwhile.
  status: open

### DW-1-2-4

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: Executed (not hand-traced) drift-scanner probes against mutations of the real `_http.py` pin down the detector's limits beyond the two earlier detector entries — (i) removing the `skip_auth` gate IS caught (exactly one finding at the `auth_headers_for` JFrog-attach line, so the realistic regression the story guards is covered), but (ii) the same regression respelled with `os.getenv("JFROG_API_KEY")` yields 0 findings, (iii) any unrelated early-return guard above the attachment (e.g. `if not url: return {}`) suppresses detection entirely, and (iv) Compare-form presence checks (`os.environ.get("K") is not None`, `"K" in os.environ`) are misclassified as scope gates, exempting the whole function.
  evidence: All four results produced by running `keys.scan_source` on mutated copies of the real `_http.py` source during Story 1.2's follow-up review pass 2026-07-30. Same "Never: not a pluggable rule engine" scope boundary as the two earlier detector entries — harden together with them in/after Story 1.6's `audit --drift` verb.
  status: open

### DW-1-2-5

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: `resolve_headers` never consults the URL scheme — an in-allowlist host receives the credential header over plaintext `http://` exactly as over `https://`. Inherited from `_http.py`'s own scheme-blind chain (every ungated caller has this today), but the keys duty is the natural place for a scheme gate (or warning) when the resolver grows in a later story.
  evidence: `keys.py`'s `resolve_headers` computes only `urlparse(url).hostname`; the scheme is never read. Confirmed by execution 2026-07-30: `resolve_headers(cred, "http://artifactory.example.com/x")` returns the API-key header.
  status: open

### DW-1-3-1

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_directory_for_secrets`/`scan_file_for_secrets` recurse via unfiltered `Path.rglob("*")` — pointed at a real repo root (Story 1.6's eventual dogfood use case), this walks `.git`'s object store, `.pixi`, and any build/cache tree with no exclusion list, which is both slow and a plausible false-positive source (packfile bytes can coincidentally contain pattern-shaped substrings).
  evidence: Confirmed by reading `scan_directory_for_secrets` in `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` — no path filtering exists. Flagged by Story 1.3's adversarial review pass 2026-07-30. Out of this story's tested scope (only run against small fixture directories); must be addressed before Story 1.6 wires `steward keys audit --drift`'s dogfood task against the real repo.
  status: open

### DW-1-3-2

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: The plaintext-secret pattern table (`_SECRET_PATTERNS`) covers an Anthropic `sk-ant-` key, a plaintext `age` identity, and a PEM header — but omits the JFrog-API-key shape, which is one of the two named historical incidents motivating this whole epic. Deliberate: JFrog Artifactory API keys have no stable, literal, universally-recognizable prefix to pattern-match narrowly (unlike the three included shapes), so adding one risks becoming the general-purpose/high-entropy heuristic this story's spec explicitly forbids.
  evidence: `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `_SECRET_PATTERNS` tuple has exactly 3 entries, no JFrog-shaped pattern. Flagged by Story 1.3's adversarial review pass 2026-07-30. Revisit if a stable JFrog-token format is ever confirmed, or if Story 1.6 needs to close this specific gap by another means.
  status: open

### DW-1-3-3

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `encrypt_file`/`decrypt_file` pass `--output <path>` straight to `age`, writing directly to the final destination with no temp-file+rename on Steward's side — an interrupted `age` process (SIGINT, disk full) could leave a truncated/corrupt file sitting exactly at a path this feature's premise is to commit to git. Whatever atomicity guarantee exists is `age`'s own responsibility (AD-1: wrap, never reimplement), not independently verified here.
  evidence: `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `encrypt_file`/`decrypt_file` bodies are a single `subprocess.run(..., check=True)` call with no pre/post staging. Flagged by Story 1.3's adversarial review pass 2026-07-30; no test covers an interrupted write.
  status: open

### DW-1-3-4

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: No `.gitattributes` entry marks `*.age` as binary (`-diff -merge -text`). Not yet actionable — no `.age` file is committed as a durable repo artifact by this story (only ephemeral `tmp_path` test fixtures) — but worth adding once Story 1.4/1.5 starts committing real encrypted payloads under `.steward/`.
  evidence: Repo-root `.gitattributes` has no `*.age` rule (checked 2026-07-30, Story 1.3 review pass). Premature to add now since nothing matches it yet.
  status: open

### DW-1-3-5

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: If the `age` binary is missing from PATH, `encrypt_file`/`decrypt_file` raise an uncaught `FileNotFoundError` (not `subprocess.CalledProcessError`), which `KeysDuty.run` doesn't catch — `cli.main()`'s generic exception handler projects it to `EXIT_INTERNAL` with a raw traceback rather than a clean `DutyResult(ok=False, ...)` message. Defensible under AD-8 (a missing external tool is arguably an environment failure, not a normal duty-level failure) and low-probability in practice (this story's own pixi.toml change declares `age` as a run-dependency of the env this code runs in), but worth a consistency pass once more duties exist and their failure-mode conventions can be compared side by side.
  evidence: `KeysDuty.run`'s `except subprocess.CalledProcessError` clause in `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` does not catch `FileNotFoundError`. Flagged by Story 1.3's edge-case review pass 2026-07-30 (not independently executed against a PATH with `age` removed, but the code path is unambiguous by inspection).
  status: open

### DW-1-3-6

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `encrypt_file`/`decrypt_file`'s `subprocess.run` calls carry no `timeout`, so a hung/stalled `age` process (unexpected prompt, unresponsive I/O) would block `steward keys encrypt`/`decrypt` indefinitely with no way to abort short of an external kill. Low practical risk — `age` is invoked here only in its non-interactive, fully-flagged form (never passphrase mode) — but worth a blanket timeout policy if adopted uniformly across duties later.
  evidence: Neither `subprocess.run` call in `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `encrypt_file`/`decrypt_file` passes `timeout=`. Flagged by Story 1.3's edge-case review pass 2026-07-30.
  status: open

### DW-1-3-7

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_file_for_secrets` matches each pattern with `.search()` (first match only) per line, so two occurrences of the *same* pattern on one line produce one finding, not two — an undercount. The actionable signal (this line needs inspection) is preserved either way, so this doesn't affect correctness of "is this file clean," only the reported count.
  evidence: Confirmed by execution 2026-07-30 (Story 1.3 edge-case review pass): a line with two distinct `sk-ant-...`-shaped substrings yielded exactly one `PlaintextSecretFinding`. Worth fixing (`finditer` instead of `search`) if `keys audit`'s eventual CLI output ever reports finding *counts* to the operator.
  status: open

### DW-1-3-8

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_file_for_secrets`, called directly (not through `scan_directory_for_secrets`, which pre-filters to real files) on a directory or a nonexistent path, raises an unhandled `IsADirectoryError`/`FileNotFoundError` rather than a clear, documented error. Not reachable today — the only current caller (`scan_directory_for_secrets`) always passes real, already-`is_file()`-checked paths — but Story 1.6's CLI verb will likely accept an arbitrary user-supplied single-file path and should validate it before calling this primitive.
  evidence: `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `scan_file_for_secrets` does `path.read_bytes()` with no existence/type check. Flagged by Story 1.3's edge-case review pass 2026-07-30.
  status: open

### DW-1-3-9

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: Epics.md Story 1.3's AC2 literally reads "When `steward keys audit` … is run against a directory" — unlike Story 1.2's own AC1, which explicitly hedged ("`steward keys audit --drift`-equivalent logic … the underlying detection primitive Story 1.6 later exposes as a full CLI verb"), 1.3's AC2 carries no such explicit hedge. This story's spec resolved the ambiguity as primitive-only (no CLI verb), reasoned from Cross-Story Dependencies' inventory-writer list (which names 1.4/1.6/1.7, not 1.3) and 1.2's identical framing precedent — but the epics.md text itself is more ambiguous here than in 1.2, so this is a real interpretive judgment call, not a certainty.
  evidence: `_bmad-output/planning-artifacts/epics.md` Story 1.3 AC2 vs. Story 1.2 AC1 wording, compared directly 2026-07-30. Flagged by Story 1.3's adversarial review pass. Story 1.6 should explicitly confirm its `steward keys audit` CLI verb exposes both `DriftFinding` and `PlaintextSecretFinding`, closing the loop this interpretation opened.
  status: open

### DW-1-3-10

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `planning-artifacts/epics.md` Story 1.3's ACs still promise a `steward keys audit` verb in this story and `age`/`age-keygen` declared in repo-root `[feature.pyforge-steward.dependencies]`, but the shipped story (deliberately, per its spec's Always/Never clauses) defers the audit verb to Story 1.6 and declares `age` in the package's own `[package.run-dependencies]` — the tracked Tier-2 epic contract now contradicts the shipped code and needs reconciling.
  evidence: `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` § Story 1.3 vs `src/shared/packages/pyforge-steward/pixi.toml` and `cli.py`; verified 2026-07-30 (Story 1.3 follow-up review) that `steward keys audit` is rejected by argparse (exit 2). Both narrowings are recorded in the story spec's intent contract; the epic was never updated to match.
  status: open

### DW-1-3-11

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_file_for_secrets` decodes raw bytes as UTF-8-with-replacement only, so a secret sitting in a UTF-16/UTF-32-encoded file (a routine Windows-tooling artifact) is invisible — the interleaved NUL bytes break every pattern and the file silently reads as clean.
  evidence: Confirmed by execution during Story 1.3's follow-up review 2026-07-30: the fixture's `sk-ant-` line re-encoded as UTF-16 produced zero findings. A BOM sniff before decode would close the common case; deliberately not added this story (fixed-pattern-table restraint), revisit when Story 1.6 wires `steward keys audit`.
  status: open

### DW-1-3-12

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: The plaintext-secret scan has no deliberate symlink policy — directory symlinks are never traversed (a committed dir-symlink hides an entire subtree from the audit) while file symlinks ARE followed (the scan reads content outside the requested directory); both directions need an explicit decision when Story 1.6 wires the audit verb.
  evidence: `scan_directory_for_secrets` walks with `Path.walk(follow_symlinks=False)` (made uniform during the 2026-07-30 follow-up review; previously 3.12-vs-3.13 `rglob` divergence) but the per-file `is_file()` check follows file symlinks. Dir-symlink invisibility confirmed by execution during the same review.
  status: open

### DW-1-3-13

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: Steward's own test tree deliberately contains pattern-matching literals (the `plaintext_secret_candidate` fixture plus inline word-marked `sk-ant-`/`AGE-SECRET-KEY-`/PEM strings in `test_keys_plaintext_secret_scan.py`), so pointing the future `steward keys audit` at the repo or the package itself reds on its own tests — Story 1.6 needs a fixture/allowlist policy before the audit verb can gate anything.
  evidence: Self-scan executed during Story 1.3's follow-up review 2026-07-30: 4 findings inside `src/shared/packages/pyforge-steward/`, all synthetic/word-marked by design. `scan_directory_for_secrets`'s signature has no exclusion hook.
  status: open

### DW-1-3-14

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `keys.py` (Story 1.2) resolves its `_http.py` bridge at module import time — ancestor marker-walk, `sys.path` mutation, `from _http import ...` — and raises `RuntimeError` outside a local-recipes checkout; the CLI now lazy-imports `KeysDuty` (patched this review) so `steward --help`/`--version`/other duties survive, but `steward keys <verb>` still fails at duty-resolution time in a package installed outside a checkout, and `pyproject.toml`'s "imports only the standard library" comment is stale. Making the bridge lazy (resolve at first `resolve_headers`/`scan_source` call) is a Story-1.2-scoped refactor.
  evidence: Confirmed by execution 2026-07-30 (Story 1.3 follow-up review): importing a copy of the package from outside the repo raised `RuntimeError: keys.py: could not locate .claude/skills/conda-forge-expert/scripts/_http.py ...` at `import pyforge.steward.keys`; after the CLI lazy-import patch, `main(["--version"])` works outside a checkout but the keys duty cannot.
  status: open

### DW-1-3-15

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `decrypt_file` writes plaintext with default umask permissions (observed mode 664 — group/world-readable) — inherited thin-wrap `age -o` behavior, acceptable while the caller picks the output path, but once Stories 1.4/1.5 have Steward itself materialize decrypted secrets it should tighten output modes (0600) or record why not.
  evidence: Observed by execution during Story 1.3's follow-up review 2026-07-30: a fresh decrypt output file was created mode 664 under umask 0002. No test or doc covers output permissions; AD-1 thin-wrap means `age`'s defaults rule today.
  status: open

### DW-1-3-16

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_file_for_secrets` slurps each file whole (`read_bytes()` + full-text decode, up to ~2-4x memory expansion) with no size cap or streaming, so a single multi-GB file anywhere in the scanned tree (build artifact, packfile, database dump) exhausts memory and can OOM-kill the audit mid-scan — and a SIGKILL bypasses even the primitive's fail-loud posture, since no Python exception reaches the caller. Harmless at this story's fixture scale; needs a size gate or chunked/streaming read before Story 1.6 points the scan at real repo trees. Distinct from the existing `.git`/`.pixi`-walk entry, which is about scan scope/speed/false positives, not memory exhaustion.
  evidence: Flagged independently by both review agents in Story 1.3's second follow-up review pass 2026-07-30; code-certain from `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` — `path.read_bytes()` materializes the full file and `scan_directory_for_secrets` feeds it every regular file in the walk with no size check.
  status: open

### DW-7-1-1

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: A follow-up review was still RECOMMENDED for Story 7.1 when the damping cap (`limits.max_followup_reviews = 2`) was spent. The story finalized anyway — `status: done`, verify green, work committed by bmad-loop run `20260809-114839-7af9` — so the lingering recommendation has no owner unless it is recorded here. The story consumed both dev attempts and all three review cycles, and the third review pass was still finding substantive issues (build-context fidelity, wrong comments, arg symmetry), which is the reason the reviewer wanted another look rather than a generic caution.
  evidence: bmad-loop damping output, promoted from Tier-3 `implementation-artifacts/deferred-work.md` where it was written as the generic id `DW-1`. Renamed to this ledger's `DW-<epic>-<story>-<n>` convention on promotion — `deferred_work_check` warns that the generic id collides with the next damped story, since bmad-loop emits `DW-1` every time.
  status: open

### DW-7-1-2

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: NINE sites carry a pixi version and they are NOT all equal — feature pins + `environment.yaml` + the new Containerfile builder image sit at `0.76.1`; `pixi.toml`'s own `requires-pixi` floor, the `"$schema"` URL, and the dashboard.yml / kedro-viz-publish.yml pins sit at `0.75.0`; and `.github/actions/sync-pypi-mappings/action.yml` sits at `0.73.0`. The four EXACT pins are the sharp ones: any below the floor installs a pixi that REFUSES to parse this manifest. `sync-pypi-mappings` IS below it today, so a `workflow_dispatch` of "Sync PyPI-Conda Mappings" installs a pixi that cannot read `pixi.toml`. Pre-existing drift, not introduced by 7.1; no detector enforces cross-site pixi-version equality, which is why it accumulated silently.
  evidence: Enumerated by Story 7.1's review pass while rewriting `requires-pixi`'s comment (see the comment itself in `pixi.toml`, which now lists all nine sites). Recorded rather than fixed: correcting a version pin inside a container story would be unrelated scope, and the real remedy is a detector, not nine hand edits.
  resolution: RESOLVED 2026-08-09 at the operator's direction. All nine aligned to **0.76.1**, chosen because it is the LOCK'S PRODUCER — the rule `dashboard.yml` states for itself ("pixi-version stays pinned to the lock's producer... Bump it in step with pixi.lock"). Aligning merely to the old 0.75.0 floor would have closed the break while leaving the dashboard and kedro-viz pins stale against their own invariant. Changed: `pixi.toml`'s `$schema` URL + `requires-pixi`, `dashboard.yml`, `kedro-viz-publish.yml`, `sync-pypi-mappings/action.yml` (the broken one, v0.73.0), `staged-recipes-linter.yml`. Already at 0.76.1 and untouched: the three feature pins, `environment.yaml` (derived), the Containerfile image tag. Verified: the v0.76.1 schema URL resolves to a real schema (`$id` matches, HTTP 200 after redirect — a 301 alone proves nothing); `pixi info` accepts the manifest under the raised floor; `pixi lock --check` reports already-up-to-date; `environment.yaml` regenerates byte-identical.
  residual: The equality is still COMMENT-MAINTAINED — nothing enforces it, which is exactly how it drifted three ways. A cross-site pixi-version detector remains the durable fix and is NOT delivered here; this entry stays as the record of why one is wanted.
  status: resolved

### DW-9-1-1

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: follow-up review still recommended for 9-1 after the damping cap was spent — an independent pass is owed on the ASGI identity boundary, declared isolation, and cache invariant work.
  evidence: the follow-up-review damping cap (`limits.max_followup_reviews = 2`) was spent with the story finalized (status `done`, verify green) while the review pass still recommended an independent follow-up. Committed by bmad-loop run `20260810-193158-7f2b`. The story's own review pass 2 closed a duplicate-header identity spoof, which is the profile where an independent pass is worth spending.
  promoted: 2026-08-11 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-8` there) under this ledger's own `DW-<epic>-<story>-<n>` convention, renamed to avoid colliding with the next damped story (bmad-loop always emits a generic id).
  status: open


### DW-10: Follow-up review still recommended for 10-3-one-image-both-engines after the damping cap was spent
origin: review-budget-followup
source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260814-202735-e909; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

### DW-9: Follow-up review still recommended for 9-3-the-audit-trail-records-what-was-seen after the damping cap was spent
origin: review-budget-followup
source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260812-191714-167d; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

### DW-10-1-1: spec-python-agent-platform's `environment.yaml` surface declaration has no counterpart in sibling specs that also declare `pixi.toml`
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-1-the-host-renders-into-src-platform.md`
  summary: `spec-python-agent-platform`'s frontmatter `surface:` list already declared `environment.yaml` (predating this story) while several sibling specs that also declare `pixi.toml` (`spec-bmad-loop-baseline-drift`, `spec-unified-container`, `spec-pyforge-core`, `spec-pyforge-warden`, `spec-pyforge-marshal`, `spec-pr-lifecycle`, `spec-bmad-output-hygiene`) do not declare `environment.yaml` alongside it, so a future `pixi.toml` change under any of those specs (which per `CLAUDE.md`'s own always-on rule must regenerate+commit `environment.yaml` in the same change) will register `environment.yaml`'s drift against `spec-python-agent-platform` instead of the spec that actually caused it.
  evidence: Raised independently by both this repair session's Blind Hunter and Edge Case Hunter reviewers, framed as caused by this session's removal of `scripts/spec_surface_allowlist.txt`'s `environment.yaml` exemption line. Verified that framing is incomplete: `spec-python-agent-platform`'s surface already listed `environment.yaml` before this story's `baseline_revision` (`c83924d3563e0aa7c78f6b6798ef41c9e64636be`, from the prior `steward: decompose spec-python-agent-platform into Epics 10-12` commit) -- confirmed the removed allowlist line was already dead for this file regardless (the allowlist is only consulted when zero spec's surface matches; `environment.yaml` already matched before this repair touched the allowlist), so the underlying multi-owner conflict predates this story and this session's own change. Not this story's to fix: resolving it means editing the `surface:` list of several specs this story does not own (all outside `pyforge-steward`, several in other BMAD projects entirely), which is out of a single story's scope. Whoever next touches one of the listed sibling specs' `pixi.toml` surface entry should either add `environment.yaml` alongside it or have `spec-python-agent-platform` drop its own `environment.yaml` claim in favor of a single canonical owner.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-1` there) during the pre-shutdown deferred-work audit.

### DW-10-2-1: `python-agent-platform`'s `platforms = ["linux-64", "osx-arm64-min"]` excludes win-64 with no stated rationale
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md`
  summary: The new `[feature.python-agent-platform]` block (and every other new comment/doc surface this story touched) never states whether win-64 is excluded because `langflow`/`dbgpt`/`dbgpt-serve` genuinely lack conda-forge win-64 builds, or because the platform list was simply copied from the spec's literal Task-1 instruction without independently checking — every other platform-restricted feature in this file (`shellcheck`, `gcloud-sdk`, `ocrmypdf`, `mlx`) documents the specific constraint forcing the restriction inline.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this story's review pass (corroborated). The `platforms = ["linux-64", "osx-arm64-min"]` value is spec-mandated verbatim (Tasks & Acceptance, Task 1) so implementing it as spec'd was correct; the gap is in the spec/doc layer, not the code. Not this story's to fix unilaterally (the intent-contract's package/platform list is frozen); whoever next touches this feature (likely Story 10.3, which also evaluates container platform support) should confirm via `lookup_feedstock` whether any of the three engines is win-64-absent on conda-forge and record the finding in the feature's own comment block.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-2` there) during the pre-shutdown deferred-work audit.

### DW-10-2-2: `channel-priority = "flexible"` on `[feature.python-agent-platform]` widens cross-channel resolution eligibility to every dependency in the feature, not just the one package (`slowapi`) it was added for
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md`
  summary: The feature-scoped `channel-priority = "flexible"` override (added because pixi 0.76.2's workspace-default `"strict"` mode hard-excludes `SelfExplainML`'s relaxed `slowapi` build the instant conda-forge has any build of the same name, even an infeasible one) is a whole-feature solver setting: any future dependency added to `python-agent-platform` that happens to have builds on both `conda-forge` and `SelfExplainML` becomes eligible for cross-channel resolution too, not only `slowapi`. In a factory whose entire premise is "factory-sourced" (this story's own title, CAP-5), that is a wider trust-boundary loosening than the single-package problem it solves.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this story's review pass (corroborated). The override is already transparently documented (this spec's own Spec Change Log, 2026-08-14 "implementation, deviations from literal instructions" entry) as scoped to this one feature only, with a known, tracked upstream retirement path (`conda-forge/slowapi-feedstock#4`, open, would let this override be dropped once merged) -- so the risk is bounded in both scope and time, not indefinite. A more surgical alternative (an explicit per-dependency `channel = "SelfExplainML"` override on `slowapi` alone, leaving the feature's channel-priority at the workspace default) was not attempted because `slowapi` is a transitive-only dependency and declaring it explicitly would itself read as a "speculative addition" beyond the intent-contract's frozen eight-package list. Whoever next revisits this feature (or when `conda-forge/slowapi-feedstock#4` merges) should re-evaluate whether `channel-priority = "flexible"` can be narrowed or removed entirely.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-2-2` there) during the pre-shutdown deferred-work audit.

### DW-10-2-3: two other specs that also declare `pixi.toml` in their `surface:` (`pyforge-marshal/spec-pyforge-core`, `pyforge-steward/spec-unified-container`) already carry a stale `pixi.toml` baseline hash, predating this story, silently absorbed instead of reported
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md`
  summary: `scripts/.spec-surface-baseline.json` governs `pixi.toml` under four specs, not just the two this repair pass reconciled (`pyforge-marshal/spec-bmad-loop-baseline-drift`, `pyforge-steward/spec-python-agent-platform`). `pyforge-marshal/spec-pyforge-core`'s stored `pixi.toml` hash (`449b3179...`) and `pyforge-steward/spec-unified-container`'s (`f3e313fe...`) both predate this story's own `pixi.toml` edit (neither matches the pre-story hash `0f9455fd...` either) -- these two specs' baselines were already stale before Story 10.2 touched anything. `python -m pyforge.doctor.sources spec-surface` does not report either as a finding (gating or WARN) today: `chain.py::_drift_findings` only escalates to gating `drift` when the spec's memlog is unchanged since baseline, and both specs' memlogs happen to already contain the literal substring `pixi.toml` somewhere in their historical text (unrelated entries), which silently satisfies the `f not in named` check and suppresses even a `drift-presumed` WARN. The multi-owner gap is a known, already-deferred class (`DW-FU-10-1`, about `environment.yaml`'s multi-owner conflict across the same sibling-spec set) -- this is the `pixi.toml`-side instance of the same underlying problem, but concretely already-drifted rather than merely structurally possible.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this repair pass's review. Verified directly: `python3 -c "import json; d=json.load(open('scripts/.spec-surface-baseline.json')); print(d['pyforge-marshal/spec-pyforge-core']['files']['pixi.toml'], d['pyforge-steward/spec-unified-container']['files']['pixi.toml'])"` against `git show 4febffd7bf:pixi.toml | sha1sum` (the pre-story hash) and the current `sha1sum pixi.toml` -- neither of the two stored hashes matches either. `pixi run -e local-recipes python -m pyforge.doctor.sources spec-surface` run against the working tree confirms exit 0 with neither spec named in its output. Not this story's to fix: reconciling either spec's `pixi.toml` surface means attributing and dating whatever change actually caused each drift (unknown without git-archaeology per spec, out of a repair pass's scope) and touches a spec this story does not own (`spec-pyforge-core` is in a different BMAD project entirely). Whoever next reconciles `pixi.toml` drift for either spec should also `--write-baseline` this one, and consider whether the substring-match suppression in `chain.py::_drift_findings` (a repo-wide gate, not story-owned) should require the named path to appear in the memlog entry's own dated section rather than anywhere in the file's full text.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-2-3` there) during the pre-shutdown deferred-work audit.

### DW-10-2-4: `gather_spec_surface`'s file-drift hash reads raw on-disk bytes, not git's blob content, so a `text eol=...`-normalized file reports false drift in any worktree whose checkout applied a different line-ending conversion than the one active when its spec's baseline was stamped
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md`
  summary: `src/platform/docs/make.bat` (`.gitattributes`: `*.bat text eol=crlf`) reported as "changed" against `pyforge-steward/spec-python-agent-platform`'s committed baseline in this bmad-loop worktree even though no content changed since Story 10.1 landed. `chain.py::_sha1` (and the mutation-side `scripts/spec_surface_check.py::sha1`) both hash `path.read_bytes()` -- the working-tree bytes after git's smudge filter -- not `git show HEAD:<path>` (the blob as committed, always LF-normalized for a `text` attribute). The original baseline was apparently stamped in a working tree where the file's on-disk bytes were still LF (matching the blob, likely because the file had just been written/staged and never round-tripped through a fresh checkout's smudge filter); this worktree's own checkout applied the `eol=crlf` smudge, producing CRLF bytes that hash differently. This repair pass's fix re-stamped the baseline against THIS worktree's CRLF bytes, which resolves the immediate gating FAIL but does not fix the underlying mismatch: any other worktree/CI runner/`git archive` export that materializes different on-disk bytes for an `eol=`-attributed file will reproduce the identical false-positive drift, requiring another one-off reconciliation cycle.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this repair pass's review. Verified directly: `git show HEAD:src/platform/docs/make.bat | sha1sum` (LF, `6a946df1...`, matches the original baseline) vs. the live working-tree file (CRLF via `git check-attr eol -- src/platform/docs/make.bat` confirming `eol: crlf`, hashing to `2d4b4a05...`) -- `git diff HEAD` for the path is empty, confirming git itself sees no change; only the raw-byte hash differs. Not this story's to fix: the hashing approach lives in `pyforge.doctor.sources.chain::_sha1` / `scripts/spec_surface_check.py::sha1`, shared infrastructure this story does not own, and any fix (hash via `git show`/`git hash-object` instead of `path.read_bytes()`, or exclude `eol=`-attributed files from content-hash comparison) is a design change to the S-13.7 reconciliation gate itself, not a `python-agent-platform` concern. Whoever next owns `pyforge.doctor.sources.chain` should consider hashing tracked files via git's own blob content (`git show HEAD:<path>` or `git hash-object`) rather than raw disk bytes, so the drift signal is checkout-environment-independent.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-2-4` there) during the pre-shutdown deferred-work audit.

### DW-10-3-1: `src/platform/Containerfile`'s pip layer swaps the app's Postgres driver from psycopg 3 to conda's psycopg2, with no ORM-level test exercising the container's actual driver
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: The Containerfile's `--no-deps` pip layer deliberately excludes `psycopg[c]` (psycopg 3, `requirements/production.txt`'s pin) in favor of the `python-agent-platform` conda env's `psycopg2` (psycopg 2) — an explicit, justified Boundaries & Constraints decision (avoiding a shadowed/duplicate driver), but a genuine major-version driver substitution, not merely a duplicate-avoidance. Django's `postgresql` backend fully supports both drivers, so this is not a known defect, but no test anywhere exercises real ORM behavior against the container's actual `psycopg2` driver — the real pytest suite (`platform-ci.yml`'s `test` job) only ever runs against psycopg 3 via `requirements/local.txt`; the container job's own checks (`manage.py check`, a health-check `SELECT 1` probe) never touch the ORM.
  evidence: Raised independently by Blind Hunter during this story's review pass. Verified live: `psycopg[c]` (psycopg 3) and `psycopg2` (psycopg 2) are genuinely different packages with different import names; the Containerfile's exclusion regex correctly keeps `psycopg2` conda-sourced and never pip-installs `psycopg[c]`, confirmed via `pip list` inside the built image. Not this story's to fix: adding real container-path ORM test coverage (or reconsidering whether the two drivers' behavior is provably equivalent for this app's usage) is a non-trivial testing-infrastructure addition, out of this L-effort infra story's own Tasks & Acceptance. Whoever next touches the container's environment layer or adds real database-backed tests should exercise them against the conda-sourced `psycopg2` driver specifically, not assume parity with the pip-tested psycopg 3 path.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3` there) during the pre-shutdown deferred-work audit.

### DW-10-3-10: Platform CI's two path filters are duplicated by hand with nothing enforcing they stay equal, so a one-sided edit silently stops gating either PRs or main.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: Platform CI's two path filters are duplicated by hand with nothing enforcing they stay equal, so a one-sided edit silently stops gating either PRs or main.
  evidence: `.github/workflows/platform-ci.yml` declares the same nine-entry `paths:` list twice — once under `on.pull_request` and once under `on.push` — and its own comment concedes the situation: "duplicated verbatim rather than shared via a YAML anchor: GitHub Actions does not support YAML anchors/aliases in workflow files. Keep them in step by hand." The failure is asymmetric and silent in both directions: a path added only to `pull_request` means the gate runs on the PR and then never re-runs on the merge commit to `main`, so a `push`-only regression (or a merge that combines two independently-green PRs) lands ungated; a path added only to `push` means main is gated on something no PR ever exercised. Nothing reports either state — a diverged pair is still valid YAML and still a passing workflow. This is not hypothetical drift in the abstract: this list was `['src/platform/**']` alone until Story 10.3's second review pass widened it to six more paths, and a third pass added a ninth (`.pixi/config.toml`), so it has changed in three of the four passes this story has had, each time by hand, in two places. The same file's sibling `pixi.toml` carries a comment-maintained pin-site enumeration whose headline total has now been wrong three consecutive times, which is the empirical case for not trusting hand-kept equality here either. Deferred rather than patched because the remedy is an architecture choice, not a mechanic: a lint step asserting the two lists match needs a home (this workflow's own `test` job only runs when the filter already matched, so it cannot police the filter that gates it), and the same unenforced-duplication shape exists in other workflows in this repo, so a one-file fix would leave the class open. A repo-wide workflow-lint detector is the durable form, and it is adjacent to the cross-site pixi-version detector `DW-FU-10-3-8` already asks for.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-10` there) during the pre-shutdown deferred-work audit.

### DW-10-3-2: `src/platform/Containerfile`'s 8 manually-added transitive pip packages have no automated drift guard against future `requirements/production.txt` changes
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: `django-timezone-field`, `python-crontab`, `cron-descriptor`, `django-appconf`, `rjsmin`, `text-unidecode`, `fido2`, `qrcode` were hand-added to the Containerfile's `pip install --no-deps` layer after a one-time `pip install --dry-run --report=-` closure diff against `requirements/production.txt`. `--no-deps` never resolves transitive dependencies automatically, so nothing re-checks this closure — a future change to `requirements/production.txt` (a new Django extra, a version bump that adds a new required transitive dependency) can silently reopen the exact class of `ModuleNotFoundError` this story spent most of its implementation investigation chasing, recoverable only by someone re-running the same manual closure-diff process by hand.
  evidence: Raised independently by Blind Hunter during this story's review pass. Verified the list is complete for the CURRENT `requirements/production.txt` (a real `docker build` + `manage.py check` + a real home-page render all succeed with exactly these 8 additions, no more, no fewer — see this spec's own Verification section). Not this story's to fix: automating the closure-diff as a CI check or build-time assertion is a real feature addition (new tooling, not a mechanical patch), and matches Story 7.3's own precedent for an identically-shaped finding (its hardcoded three-root secrets-scan list), deferred there for the same forward-looking-maintenance reasoning. Whoever next touches `requirements/production.txt` or this Containerfile's pip layer should re-run the closure diff (`pip install --dry-run --ignore-installed --report=- -r requirements/production.txt` inside the built image, diffed against what the conda env + pip layer already provide) rather than assuming the 8-package list stays complete.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-2` there) during the pre-shutdown deferred-work audit.

### DW-10-3-3: `production.py`'s hardcoded `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` silently break login and every CSRF-protected form on the plain-HTTP local compose stack
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: `config/settings/production.py` hardcodes `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True` with no env override, while this story's `src/platform/compose/compose.yml` sets `DJANGO_SECURE_SSL_REDIRECT=False` (documented inline as necessary because the local stack serves plain HTTP with no TLS terminator) — a browser drops `Secure`-flagged cookies over plain HTTP, so any session-based flow (login, the Django admin, any CSRF-protected POST) silently fails against a freshly-`docker compose up`'d stack even though `/ht/`, `/api/health`, and the static home page all return 200.
  evidence: Raised by Edge Case Hunter during this repair pass's review. Confirmed by reading `config/settings/production.py:39-45` directly: `SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)` is env-overridable (and is the exact variable this story's compose file overrides), but the two sibling cookie-security settings one/five lines below it are plain `True` literals with no `env.bool(...)` wrapper at all — the same "no TLS locally" boundary was handled for one setting and not the other two. Not this story's to fix: `production.py` predates this story (Story 10.1's own render) and is outside spec-10-3's Code Map; this story's own Acceptance Criteria for the compose stack name only a 200 health response, not a working login/CSRF flow, so nothing in this story's frozen intent-contract required exercising that path. Whoever next touches `config/settings/production.py` (or adds real browser/form-level tests against the compose stack) should wrap `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` in the same `env.bool(..., default=True)` pattern already used for `SECURE_SSL_REDIRECT` immediately above them, and set both `False` in `compose.yml` alongside `DJANGO_SECURE_SSL_REDIRECT`.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-3` there) during the pre-shutdown deferred-work audit.

### DW-10-3-4: Nothing tests the platform image's actual runtime stack — every automated test runs a different set of package versions than the image ships.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: Nothing tests the platform image's actual runtime stack — every automated test runs a different set of package versions than the image ships.
  evidence: `platform-ci.yml`'s `test` job (ruff, mypy, the full pytest suite) installs `requirements/local.txt`, i.e. the pip universe: Django 5.1.11, django-health-check 3.24.0, celery 5.5.3, uvicorn 0.35.0, gunicorn 23.0.0, pillow 11.3.0, psycopg 3. The image resolves its interpreter from the `python-agent-platform` conda env and ships Django 5.2.15, django-health-check 4.5.0, celery 5.6.3, uvicorn 0.52.3, gunicorn 26.0.0, pillow 12.3.0, psycopg2 — verified live with `pip list` inside the built image. The two sets are mutually exclusive by construction, not by accident: `requirements/base.txt`'s own comment records that `django-health-check>=4.0 requires Django>=5.2, which this file's own django==5.1.11 pin does not satisfy`. So every Django extra the app depends on (django-allauth[mfa] 65.10.0, django-redis 6.0.0, django-celery-beat 2.8.1, django-compressor 4.5.1, django-crispy-forms, django-model-utils, django-anymail) is pytest-verified against Django 5.1 only and then shipped on 5.2, and the image's own automated coverage is four smoke requests plus `manage.py check`. This is real, not theoretical: this same review pass found `uvicorn-worker==0.3.0` calling `uvicorn.Config.setup_event_loop()`, removed in uvicorn 0.36.0 — a hard gunicorn worker-boot failure that no test in the repo could have caught, found only by booting the image by hand. Deferred rather than fixed because closing it means a real testing-infrastructure decision (run the pytest suite a second time inside the container against the conda env, or converge the two universes onto one Django pin), not a mechanical patch, and it spans Story 10.1's requirements files and Story 10.2's pixi feature as much as this story's Containerfile. Related to but distinct from DW-FU-10-3, which covers only the psycopg driver substitution.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-4` there) during the pre-shutdown deferred-work audit.

### DW-10-3-5: The platform image ships its own source tree writable by the runtime user, and whether it does depends on the umask of the machine that built it.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: The platform image ships its own source tree writable by the runtime user, and whether it does depends on the umask of the machine that built it.
  evidence: `COPY src/platform/ /app/` preserves the build context's file modes verbatim. On a host with a 002 umask (the default on this development machine) the checkout is mode 775/664, so every file the runtime stage ships is group-writable, and the image's `USER 1001:0` runs in GID 0 — meaning the application process can rewrite its own code. Confirmed live under an arbitrary UID: `docker run --user 24680:0 ... bash -c 'echo x >> /app/manage.py'` succeeds. Reproduced on the pre-review image too, so this predates this review pass and is a property of the COPY pattern rather than of any fix applied here; the same pattern is used by the repo-root Containerfile (Story 7.1), so a fix should probably cover both. Two consequences: the defense-in-depth one (a compromised request handler can persist changes into the running container's own code, which a read-only source tree would prevent), and a reproducibility one (the shipped modes differ between a 002-umask developer machine and an 022-umask CI runner, so two builds of the same commit are not byte-identical). Not patched in this pass because both candidate fixes are decisions rather than mechanics: `COPY --chmod=` is a BuildKit/buildah extension and this story's own Boundaries & Constraints deliberately cap the build at exactly one such extension (`--mount=type=secret`), while a blanket `RUN chmod -R g-w /app` has to carve out `staticfiles`, `platformapp/media`, and `$HOME` itself (gunicorn 26 creates `$HOME/.gunicorn/gunicorn.ctl` at boot) and would silently break the arbitrary-UID contract if it got the carve-outs wrong.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-5` there) during the pre-shutdown deferred-work audit.

### DW-10-3-6: User-uploaded media under `src/platform/` is not gitignored, because the pattern meant to cover it names a directory that does not exist.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: User-uploaded media under `src/platform/` is not gitignored, because the pattern meant to cover it names a directory that does not exist.
  evidence: `src/platform/.gitignore:272` carries `platform/media/`, a cookiecutter-django default that assumes the Django app package is named `platform`. Story 10.1 rendered this project with the package named `platformapp`, so `MEDIA_ROOT` is `src/platform/platformapp/media/` and the pattern matches nothing. Verified directly: `git check-ignore -v src/platform/platformapp/media/foo.png` exits 1 (not ignored), while the sibling `git check-ignore -v src/platform/staticfiles/x.css` exits 0 via `.gitignore:54`. Consequence: the first developer who exercises a real upload locally and runs `git add -A` commits user content into the repository, and nothing warns them — the file that is supposed to prevent it looks like it does. Pre-existing in Story 10.1's own tree, surfaced only because Story 10.3's follow-up review checked a `.dockerignore` comment that asserted both output directories were already gitignored (that comment has been corrected; the image side is fully covered by the two `.dockerignore` entries Story 10.3 added, so this is a repo-hygiene gap, not an image defect). Not fixed here: `src/platform/.gitignore` is Story 10.1's surface and sits inside two governed spec surfaces, so a one-line fix drags a memlog entry and a baseline stamp for each behind it — cheap work, but work that belongs to whoever owns that tree rather than to a container story's review pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-6` there) during the pre-shutdown deferred-work audit.

### DW-10-3-7: Platform CI's path filter now bills the repo's highest-traffic source trees for a two-engine container matrix plus an unrelated pip test job.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: Platform CI's path filter now bills the repo's highest-traffic source trees for a two-engine container matrix plus an unrelated pip test job.
  evidence: Story 10.3's review pass widened `.github/workflows/platform-ci.yml`'s `paths:` from `src/platform/**` to also include `pixi.toml`, `pixi.lock`, `.dockerignore`, `scripts/container-gates`, `src/shared/packages/pyforge-steward/**`, and `src/shared/packages/pyforge-core/**`. That widening is correct on its own terms — every one of those is a real input to the image build (the builder stage materializes a `pyforge-steward` env for the secrets-scan gate), and the narrow filter demonstrably missed a `requires-pixi` bump that broke the build. The cost was not weighed at the same time. `paths:` is WORKFLOW-scoped, not job-scoped, so any hit runs BOTH jobs: the `container` job's `[docker, podman]` matrix (two cold builds, each solving and downloading a 395-package env plus a second build-time env, with `timeout-minutes: 45`) AND the pip-based `test` job, which shares nothing with the image at all. `src/shared/packages/pyforge-steward/**` is where most fleet work in this repo lands, so a one-line docstring edit there now pays for two container builds. Deferred rather than decided here because both directions are defensible and neither is mechanical: narrowing the filter reopens the miss it was added to close, while keeping it means splitting this workflow per job (or gating the `container` job on a `paths-filter` action inside the job) — a workflow-architecture choice, not a patch. The contradictory comment claiming this workflow "never triggers on a factory-only change" was corrected in the same pass, so the current state is at least accurately described.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-7` there) during the pre-shutdown deferred-work audit.

### DW-10-3-8: The repo-root Containerfile pins a pixi below the floor its own manifest declares, so that image's builder stage cannot install at all.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: The repo-root Containerfile pins a pixi below the floor its own manifest declares, so that image's builder stage cannot install at all.
  evidence: `Containerfile:58` (Story 7.1, the Guild's unified image, governed by `pyforge-steward/spec-unified-container` CAP-1) is `FROM ghcr.io/prefix-dev/pixi:0.76.1`, while `pixi.toml`'s `requires-pixi` is `>=0.76.2`. Pixi enforces that floor, so the builder stage's `pixi install` aborts with `this project requires pixi '>=0.76.2', but you have pixi 0.76.1`. Not inferred — Story 10.3 hit this exact error live when its own Containerfile first reused Story 7.1's tag, which is why `src/platform/Containerfile` is on 0.76.2. Live inventory taken during the follow-up review: thirteen sites carry a pixi version and TWELVE are at 0.76.2 (`requires-pixi`, the `$schema` URL, three `feature.*` floors, `environment.yaml`, `dashboard.yml`, `kedro-viz-publish.yml`, three pins in `herald-live-demo.yml`, `sync-pypi-mappings/action.yml`, `staged-recipes-linter.yml`, and `src/platform/Containerfile`); the root Containerfile is the only holdout. This is NOT covered by DW-7-1-2, which is `status: resolved` (2026-08-09, when all sites were aligned at 0.76.1) — everything except the root Containerfile has since moved up and left it behind, which is that entry's own residual ("the equality is still COMMENT-MAINTAINED — nothing enforces it") coming true a second time. Two pieces of work, neither this story's: raise the tag to 0.76.2 (one line, but it belongs to the spec that owns that image, and the fix should be verified with a real build), and build the cross-site pixi-version detector DW-7-1-2 named as the durable remedy. Note also that `herald-live-demo.yml`'s three pins were absent from the enumeration entirely until this pass; a hand-maintained list that has now been wrong about both its count and its contents is the argument for the detector.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-8` there) during the pre-shutdown deferred-work audit.

### DW-10-3-9: Two marshal specs carry stale pixi.toml baselines that the spec-surface gate cannot report, because a moved memlog downgrades their drift to informational.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: Two marshal specs carry stale pixi.toml baselines that the spec-surface gate cannot report, because a moved memlog downgrades their drift to informational.
  evidence: `scripts/.spec-surface-baseline.json` records `pixi.toml` for `pyforge-marshal/spec-pyforge-core` at sha1 `449b3179` and for `pyforge-marshal/spec-bmad-loop-baseline-drift` at `0f9455fd`. Neither matches the live file, and — the part that dates it — neither matches `pixi.toml` as of Story 10.3's own baseline commit `64e717d135` (`0ae029cc`), so both were already unreconciled before this story touched anything. `python scripts/spec_surface_reconcile.py` nevertheless exits 0 with `OK: every tracked file governed or allowlisted; no drift.`: once a spec's `.memlog.md` hash has moved for any reason, its findings degrade from gating `[drift]` to informational `[drift-presumed]`, and the residual check for whether a changed path is NAMED in the memlog is a substring test against the whole file, which a long historical memlog mentioning `pixi.toml` satisfies incidentally. This is the same silence that let Story 10.3 change `src/platform/**` without reconciling its own owning spec — caught only because a reviewer compared baseline digests by hand. Deferred rather than fixed: the mechanical part (name the changes, re-stamp) belongs to whoever owns those marshal specs and requires knowing what actually moved `pixi.toml` between those digests, and the structural part (a memlog that moved for an unrelated reason should not blanket-downgrade every governed path, and "named" should mean named in the current entry rather than anywhere in the file) is a change to the reconciler's own semantics, owned by `pyforge-marshal/spec-surface-drift-reconciliation`.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-9` there) during the pre-shutdown deferred-work audit.

### DW-8-4-1: `sync reconcile --schedule`'s per-candidate failure detail is computed but never reaches the operator through the CLI
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-4-the-schedule-trigger-enumerates-real-candidates.md`
  summary: `reconcile_schedule_batch` builds a rich `details["candidates"]` list (each entry carrying `github_item_id`, `updated_at`, `ok`, `summary`), but `cli.py`'s `main()` prints only `result.summary` — a single aggregate string like "3 candidates, 2 ok, 1 failed" — and `sync reconcile` defines no `--json` flag, unlike `provision`/`list`/`show`. When a `--schedule` batch reports a partial failure, an operator running the CLI has no way to learn which candidate failed or why; the diagnostic data this story's own frozen contract requires (`details["candidates"]`) is computed and then discarded at the CLI boundary.
  evidence: Raised by Blind Hunter during this story's review pass 2, confirmed by reading `cli.py:361` (`print(result.summary, ...)`, the sole output line for every duty, not just `sync`) and `_add_sync_subparsers` (no `--json` argument anywhere on the `reconcile` verb, unlike `provision --list-modules [--json]`/`provision --module <name> [--json]`). Pre-existing whole-CLI convention — every duty's `main()` output is this same one-line `result.summary`, not caused by this story's own logic — but this story's batch mode is the first `sync` invocation shape where the discarded detail is genuinely load-bearing (a single-pair `--github-item` failure's cause IS the one-line summary; a `--schedule` batch's per-candidate cause is not). Not a trivial patch: adding a `--json` flag to `sync reconcile` is a real CLI-surface/API decision (naming, help text, interaction with `--dry-run`), not a mechanical fix. Whoever next needs `--schedule` batch failures to be operator-diagnosable from the CLI (rather than only from a direct Python call to `reconcile_schedule_batch`) should settle this then.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-4` there) during the pre-shutdown deferred-work audit.

### DW-8-4-2: `_LIST_PROJECT_ITEMS_QUERY`'s `fieldValues(first: 50)` cap now runs board-wide, automatically, on every scheduled tick
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-4-the-schedule-trigger-enumerates-real-candidates.md`
  summary: The new bulk-listing query's `fieldValues(first: 50)` cap is copy-pasted unchanged from the pre-existing `_GET_PROJECT_ITEM_QUERY` (already a known, already-deferred pagination gap for the single-item path — see this ledger's Story 8.1 entry, `DW-FU` prefix predates the current id-minting convention), but this story is the first to exercise it board-wide and automatically rather than only for a manually-targeted single item: a board with more than 50 custom fields could have a genuinely-linked candidate's link field silently fall outside the first page and be excluded from candidacy entirely on every `trigger=schedule` tick.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this story's review pass 2 (corroborated), confirmed by reading `_LIST_PROJECT_ITEMS_QUERY` in `sync.py` — the same `fieldValues(first: 50)` block as `_GET_PROJECT_ITEM_QUERY`, no `pageInfo`/`after` inner-cursor handling for the per-node field connection. This is materially different in consequence from the Story 8.1 entry it shares a root cause with: that entry describes a single manually-invoked `--github-item` call silently misreading one targeted item's field; this story's automatic board-wide enumeration means the SAME truncation, on the SAME kind of item, silently and permanently drops that item from every future scheduled batch with no operator awareness — exactly the false-negative failure mode this story's own Design Notes call "strictly worse" than a false positive (AD-5). Not a trivial patch: needs real per-item `fieldValues` pagination inside a bulk query already paginating at the outer `items` level (a nested-pagination GraphQL shape with no existing precedent in this module), not a mechanical fix. Whoever next revisits either query's field-parsing, or onboards a board with 50+ custom fields, should settle both entries together.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-4-2` there) during the pre-shutdown deferred-work audit.

### DW-8-5-1: the loop-home worktree's local `epics.md` and tracked `sprint-status-ledger.yaml` are 60 commits stale, still carrying pre-correct-course Epic 8 story numbers
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-5-fail-loud-fail-alone.md`
  summary: This worktree's local copy of `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` and the checked-in `sprint-status-ledger.yaml` still show the pre-`bmad-correct-course` Epic 8 numbering (`8.4` = "Fail loud, fail alone", `8.5` = "Explicit status-vocabulary translation", no producer story for `trigger=schedule` batching) even though `main` landed the 2026-08-13 correct-course renumbering 60 commits ago (`8.4` = "The schedule trigger enumerates real candidates", `8.5` = "Fail loud, fail alone", `8.6` = "Explicit status-vocabulary translation" — `sprint-change-proposal-2026-08-13.md`). This story's own diff is correctly labeled against the CURRENT (post-correct-course) numbering — confirmed against the Tier-3 `implementation-artifacts/sprint-status.yaml` (which backlinks straight to the main checkout and already shows `8-4-the-schedule-trigger-...: done` / `8-5-fail-loud-fail-alone: backlog`), the correct-course proposal document itself, and the git history of the already-landed `8-4-the-schedule-trigger-enumerates-real-candidates` story — but the two stale worktree-local files remain a live trap for anyone (human or agent) who trusts them instead.
  evidence: Discovered independently during this story's own step-01 planning (this worktree's `epics.md` diffed 35 lines against `main`'s copy; `git merge-base --is-ancestor` confirmed the correct-course commit `073dfe0fd2` is not an ancestor of this loop-home branch) and then reproduced live during this story's own review pass: Blind Hunter, working from a fresh context with no access to that prior investigation, read this worktree's stale `epics.md`/`sprint-status-ledger.yaml`, concluded this diff was mislabeled as "Story 8.5" when it should be "Story 8.4", and rated it the review's highest-severity finding — a false positive triggered by exactly the drift this entry describes. Root cause is mechanical, not this story's to fix: `loop/pyforge-steward`'s squash-merge-per-story pattern only carries a landed branch's own file diffs, so a correct-course session that edited `epics.md`/the ledger directly on `main` (rather than through a dispatched loop story) never reaches the loop branch's tracked copies. Whoever next syncs this loop-home branch against `main` (or runs `pixi run -e local-recipes sprint-ledger-sync` / `bmad-drift-check`) should reconcile both files; until then, any reviewer or planning session working inside this loop-home's worktrees should prefer the Tier-3 `sprint-status.yaml` backlink and `sprint-change-proposal-2026-08-13.md` over the worktree-local `epics.md`/`sprint-status-ledger.yaml` for Epic 8 story identity.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-5` there) during the pre-shutdown deferred-work audit.

### DW-8-5-2: a GitHub Projects V2 board item deliberately never meant to link to Jira fails loudly on every scheduled tick forever, with no way to mark it out-of-scope
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-5-fail-loud-fail-alone.md`
  summary: CAP-4 ("fail loud, fail alone on broken links") and this story's landed code both treat every unlinked board item as a candidate that must fail by name on every `--schedule` run, with no distinction between "not yet linked" (a real gap worth surfacing) and "never going to be linked" (a card that was always meant to stay GitHub-only). A real board mixing synced and GitHub-only work items would see the GitHub-only ones fail, by name, on every single scheduled tick, forever, with no way to silence them short of removing them from the board or giving them a link they don't need.
  evidence: Raised by Blind Hunter during this story's review pass as an operability concern, and confirmed against CAP-4's own frozen intent text (`spec-jira-github-projects-sync/SPEC.md`: "An item missing its cross-system link fails loudly in a log -- never silently skipped") and this story's own frozen `<intent-contract>`, neither of which carries any opt-out/allowlist concept. Not this story's to fix: the frozen AC and the ratified architecture (AD-6) are unambiguous that every unlinked item must fail loudly, and this story's own "Never" boundary forbids inventing a new filtering mechanism inside `list_linked_github_items`/`reconcile_schedule_batch`. An opt-out (e.g. a per-item "excluded from sync" marker, or a config-level allowlist of fields/labels that mark an item as GitHub-only) is a real product/architecture decision, not a mechanical patch, and belongs with whoever next operates a real mixed board against `trigger=schedule` and hits the noise in practice.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-5-2` there) during the pre-shutdown deferred-work audit.

### DW-8-6-1: `load_config`'s `document.get(...) or {}` idiom silently coerces a falsy-but-malformed `status_mapping`/`field_overrides`/`user_mapping` value to an empty mapping
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md`
  summary: `status_mapping = document.get("status_mapping") or {}` (and the identical pre-existing idiom for `field_overrides`/`user_mapping`) coerces any falsy value -- `status_mapping: false`, `status_mapping: 0`, `status_mapping: ""` -- to `{}` before the subsequent `isinstance(status_mapping, dict)` check ever runs, so a config author's typo silently loads as "no mapping configured" instead of raising a named `SyncConfigError`. For `status_mapping` specifically this defeats part of the very guarantee this story exists to build (AD-6: an unmapped status is a hard, named, logged failure) -- an operator who typos `status_mapping: false` gets silent full-passthrough-becomes-always-unmapped behavior with no config-time signal that their file is wrong.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter (corroborated) during this story's review pass, confirmed by reading `load_config` in `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- all three config-dict loads (`field_overrides`, `user_mapping`, `status_mapping`) use the identical `document.get(name) or {}` pattern with no explicit `is None` check. Not this story's to fix alone: the pattern is copy-pasted verbatim from the pre-existing `field_overrides`/`user_mapping` code this story's own spec instructed it to mirror ("load and validate it in `load_config` exactly like `user_mapping`"), so fixing only `status_mapping` would be an inconsistent, asymmetric patch leaving the other two fields with the same gap. Whoever next touches `load_config` should replace `or {}` with an explicit `is None` check across all three fields in one pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-6` there) during the pre-shutdown deferred-work audit.

### DW-8-6-2: no operator-facing documentation page covers `status_mapping`/`user_mapping`/`field_overrides` outside the example YAML's own comments
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md`
  summary: `pyforge-steward/README.md` has zero mentions of `status_mapping`, `user_mapping`, or `field_overrides` -- the entire config surface for these three `SyncConfig` fields is documented only as inline comments in `.steward/sync-config.example.yaml`, with no single doc page an operator can read end-to-end (module docstring, README, or a guide) to learn what the sync duty's config surface supports.
  evidence: Raised by Blind Hunter during this story's review pass, confirmed by grepping `pyforge-steward/README.md` for all three field names (zero hits). Pre-existing gap for `field_overrides`/`user_mapping` since Story 8.1; this story adds a third field to the same undocumented surface rather than introducing the gap. Not this story's to fix alone: a proper fix is a dedicated config-reference doc section covering all three fields together, not a one-field patch that leaves the other two still undocumented. Whoever next writes or expands `pyforge-steward/README.md`'s config section should cover all three.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-6-2` there) during the pre-shutdown deferred-work audit.

### DW-8-6-3: `sprint-change-proposal-2026-08-13.md`'s root-cause rationale for the Jira↔GitHub write direction is backwards
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md`
  summary: The correct-course proposal's §2 explanation of which sync direction already hard-fails and which was the raw passthrough is reversed relative to both the original `epics.md` audit note and the actual shipped code.
  evidence: `sprint-change-proposal-2026-08-13.md` §2 states "the Jira→GitHub direction already hard-fails on an unmapped status ... but the GitHub→Jira direction is still 8.1's raw 1:1 passthrough ... exactly what 8.5 exists to replace." In reality `push_to_github` (writing a Jira status into GitHub) was the unvalidated passthrough this story fixed -- confirmed against pre-story `sync.py`, which called `update_project_item_field` with the raw `target_value` and zero validation -- while `push_to_jira` (writing a GitHub status into Jira, via `transition_jira_issue`) already hard-fails when no transition matches, unchanged by this story. That is the reverse of the proposal's claim; the original `epics.md` audit note the proposal was resolving states it correctly ("its GitHub direction is today a raw 1:1 pass-through"). No functional impact -- this story's own frozen intent-contract and the shipped code both correctly target `push_to_github` -- this is a prose-only error in a decision record inherited verbatim from `main`'s `073dfe0fd2` correct-course commit (authored outside this story's own scope), which could mislead a future reader auditing the RESPEC rationale. Not this story's to fix: editing another station's/process's already-ratified correct-course record is out of this story's code-focused intent-contract.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-6-3` there) during the pre-shutdown deferred-work audit.

### DW-8-6-4: `status_mapping`'s `or {}` idiom independently reconfirmed to swallow an explicit falsy top-level value (`false`/`0`/`""`) before the mapping-type check runs
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md`
  summary: `status_mapping = document.get("status_mapping") or {}` (`sync.py:196`) coerces a falsy but present top-level value straight to `{}` before `isinstance(status_mapping, dict)` ever inspects it, so `status_mapping: false` loads silently as "no mapping configured" instead of raising `SyncConfigError`.
  evidence: This is the same root cause already recorded as `DW-FU-8-6` (shared `or {}` idiom across `field_overrides`/`user_mapping`/`status_mapping`, including this exact falsy-scalar example) -- both Blind Hunter and Edge Case Hunter independently re-surfaced it during this story's fresh review pass on the restored implementation, corroborating that assessment. Recorded as its own entry per this workflow's defer procedure (fresh entries are always minted, not merged into prior ones). No new remediation beyond what `DW-FU-8-6` already describes: whoever next touches `load_config` should replace `or {}` with an explicit `is None` check across all three fields in one pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-6-4` there) during the pre-shutdown deferred-work audit.

### DW-9-2-1: `dashboard_role` is a hardcoded scope-key string duplicated independently in the writer (`middleware.py`) and the reader (`views.py`), with no shared constant and no test that drives a real request through both together
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-2-an-unauthorized-page-is-absent-not-hidden.md`
  summary: `middleware.py`'s `DashboardIdentityMiddleware.__call__` writes `scope["dashboard_role"] = ...` and `views.py`'s `navigation_view` independently reads `getattr(request, "scope", {}).get("dashboard_role")` — the string literal is typed out separately in both places with nothing tying them together, and every existing test for `build_navigation_view` hand-constructs the scope dict directly rather than running it through the real middleware.
  evidence: Raised by Blind Hunter in this story's review pass. Not patched here: `middleware.py` is Story 9.1's already-shipped file and is outside this story's frozen Code Map (`navigation.py`/`filtering.py`/`views.py`/tests only), so introducing a shared constant module or an integration test spanning both stories' files is a cross-story change, not a same-pass fix. The failure mode is fail-closed (a typo or rename in either module silently degrades to "no pages visible," never to over-exposure), so this is a maintainability/observability gap, not a security hole -- but it is a real one: nothing in the current suite would catch the drift.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-2` there) during the pre-shutdown deferred-work audit.

### DW-9-2-2: `build_navigation_view`'s duplicate-path guard only rejects byte-identical strings, so `/reports` and `/reports/` (or differently-cased paths) can still collide once wired into a real router
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-2-an-unauthorized-page-is-absent-not-hidden.md`
  summary: The wiring-time uniqueness check in `views.py` (`if page.path in seen_paths`) compares declared `Page.path` values as exact strings, so two pages differing only by a trailing slash or letter case pass as "distinct" even though many adopter routers would treat them as the same route, reopening the ambiguous-duplicate-entry hazard the guard exists to prevent, just one layer up.
  evidence: Raised by Blind Hunter in this story's review pass. Not patched here: fixing this requires choosing a path-canonicalization policy (trailing-slash handling, case sensitivity) that nothing in the spec's Boundaries & Constraints or I/O matrix specifies, and guessing one risks introducing behavior inconsistent with whatever router an adopter actually wires this into (AD-1 explicitly leaves routing to the adopter). Belongs with a future story or an explicit spec decision, not an unprompted guess in this pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-2-2` there) during the pre-shutdown deferred-work audit.

### DW-9-2-3: A whitespace-padded role reaching `filter_by_role` and `build_navigation` from the same request is refused loudly by one and silently emptied by the other
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-2-an-unauthorized-page-is-absent-not-hidden.md`
  summary: Story 9.1's `DashboardIdentityMiddleware` stores `scope["dashboard_role"]` verbatim whenever `role.strip()` is truthy (only blank/whitespace-only values are rejected), so a role like `" east"` from a misbehaving proxy reaches both of this story's new consumers unstripped. `filter_by_role` then raises `ValueError` for it (per this story's own "unrecognized role is a configuration defect" rule, since `" east"` is not in `declaration.roles`), while `build_navigation` silently returns an empty tuple for the same value (`Page.roles` has no closed vocabulary to validate an "unrecognized" role against, by design — see the Design Notes' "two independent declared vocabularies"). The same artifact on the same request therefore 500s one dashboard surface and quietly shows nothing on the other.
  evidence: Raised by Blind Hunter in this story's review pass; confirmed by reading `middleware.py`'s `role = roles[0] if roles else ""` / `scope["dashboard_role"] = role if role.strip() else None` directly. Not patched here: the root cause is Story 9.1's already-reviewed, deliberate decision not to normalize role values, which that story's own review pass 3 explicitly deferred to Story 9.3's audit-row work ("trimming/normalizing a real identity is the identity-model decision deferred to Story 9.3"), and this story's spec explicitly inherits that deferral rather than re-deciding it. Each of `filter_by_role`'s raise and `build_navigation`'s silent-empty is independently correct against its own module's stated contract; only the cross-module asymmetry is new, and reconciling it means picking a normalization policy that belongs with Story 9.3, not an unprompted guess here.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-2-3` there) during the pre-shutdown deferred-work audit.

### DW-9-3-1: AD-14's PostgreSQL contention proof is not delivered for the new audit store — every test runs against in-memory SQLite only
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: AD-14 states "Contention behaviour is proven against PostgreSQL in CI, never inferred from a green SQLite run," and explicitly names the audit store and AD-12's per-message hot-path write as the reason this binds here. This story's entire test suite (`test_dashboard_audit.py`) runs against a single in-process SQLite `:memory:` database with no concurrent-write test — unlike `test_dashboard_cache.py`'s threaded race test for the analogous cache invariant, nothing here exercises concurrent `record_audit_entry` calls at all, against SQLite or otherwise.
  evidence: Raised by Blind Hunter in this story's review pass. Not patched: the spec's own Boundaries explicitly ruled this out of scope ("Prove AD-14's PostgreSQL contention claim — no PostgreSQL CI service exists in this repo's pixi environments yet... the contention proof is a new deferred-work entry, not attempted here"), because no `psycopg2`/PostgreSQL service is provisioned in the `pyforge-steward` pixi feature or anywhere in this repo's CI today — standing one up is an environment/CI-topology decision beyond one story's Code Map, the same class of decision Story 9.1/9.5 repeatedly deferred for the cache backend. Whoever adds PostgreSQL CI coverage (most naturally Story 9.5's deployment-perimeter surface, which already owns the estate's other backend/infra decisions on this ledger, or Story 9.6's proof suite) should add a concurrent-write contention test for `record_audit_entry` at the same time.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3` there) during the pre-shutdown deferred-work audit.

### DW-9-3-10: every AUDIT_READ row records the same constant "of what", so CAP-4's read-side provenance is unrecoverable from the trail
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `query_audit_entries` hardcodes `target="audit_trail"` on the entry it writes for its own invocation and persists nothing about the `**filters` that scoped the read, so two materially different reads of the trail — a targeted lookup of one high-value export row and an unfiltered sweep of a whole action class — produce byte-identical audit rows. CAP-4 requires "who saw how many rows of what"; on the read path the "of what" is a constant, so the trail cannot answer which rows a reader actually saw.
  evidence: Raised by Blind Hunter in this story's review pass 4 and reproduced by execution: `query_audit_entries(reader_actor="mallory", reader_role=None, actor="alice")` against a 500,000-row EXPORT entry and `query_audit_entries(reader_actor="mallory", reader_role=None, action=LOAD)` both wrote `actor=mallory role=None action=audit_read target='audit_trail' row_count=1`, so a reader walking the trail one primary key at a time leaves N indistinguishable one-row reads behind. Distinct from `DW-FU-9-3-2` (the reader's role is recorded but not enforced) and `DW-FU-9-3-4` (the result set is unbounded); this is about what the recorded act says it was. Not patched, because the fix is a design choice this story's spec does not make: `**filters` is an open surface accepting arbitrary keyword lookups (deliberately, per pass 1's `reject` of a field allowlist), so serializing it into the 255-character `target` column risks both truncation and writing caller-supplied values — potentially identifying ones — into the very table being audited, and the alternatives (a separate JSON column, a normalized read-scope table, an allowlisted filter vocabulary) all change the shipped schema. It should be settled together with `DW-FU-9-3-2`, since deciding what a read is scoped to is the same question as deciding what a reader is allowed to see.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-10` there) during the pre-shutdown deferred-work audit.

### DW-9-3-2: `query_audit_entries` does not filter its results by the reader's role — AD-7's "the trail is itself role-isolated data" is only half-implemented
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: AD-7 reads "the trail is itself role-isolated data — any surface that displays it passes through the same filtering and audit path as any other dataset, so reading the audit trail is a recorded act." This story implements the second half only (every read writes an `AUDIT_READ` entry) — `query_audit_entries` forwards arbitrary caller-supplied `**filters` straight into `AuditEntry.objects.filter()` with no connection to `AccessDeclaration`/CAP-2's row-isolation pattern and no restriction on which rows a given `reader_role` may see.
  evidence: Raised by Blind Hunter in this story's review pass. Not patched: the row-isolation half depends on `filter_by_role`/`AccessDeclaration`-style filtering (Story 9.2's `filtering.py`), which does not exist in this worktree (Story 9.2 is in-flight in a sibling worktree of this same bmad-loop run, and this story's own spec explicitly rules out wiring into files that don't exist here). Nothing in Epic 9's current story list (9.1-9.7 per `epics.md`) obviously owns retrofitting role-based filtering onto the audit-read surface itself, so this may be a permanently under-specified clause of AD-7 rather than a deferral with an obvious future owner — flagging it here rather than silently dropping it is the point of this entry.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-2` there) during the pre-shutdown deferred-work audit.

### DW-9-3-3: `purge_expired_entries` destroys audit rows without recording that anyone destroyed them, while `query_audit_entries` records every read
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: AD-7's rationale for auditing reads of the trail — that the record of who saw what is the one dataset whose own access is otherwise ungoverned — applies at least as strongly to deletion, but the only destructive operation on the trail writes no entry at all: `purge_expired_entries(AuditRetention(days=30))` returns the deleted count and leaves nothing behind naming who ran it or how many rows of evidence went away.
  evidence: Raised by Blind Hunter in this story's review pass 2 and reproduced by execution (a trail with one expired row: purge returns 1, `AuditEntry.objects.count()` is 0, and no entry of any action records the deletion). Not patched: closing it is a design change beyond this spec rather than a fix to it. The spec's I/O matrix specifies purge's contract with no audit requirement, its Code Map enumerates the action vocabulary as exactly load/filter/navigate/export/audit_read, and `purge_expired_entries`'s signature carries no actor — so recording the purge needs a sixth `AuditAction` value, a migration change, and a new required actor parameter, i.e. a decision about whether retention is an operator-level batch act with its own identity or a request-time act like the other five. Review pass 2 did harden the destructive path in the ways that were in scope (a future `now` is now refused, so a purge can no longer silently exceed its declared retention), but the who-purged question is left to whoever owns the retention runner — most naturally Story 9.5's deployment-perimeter surface, which already owns this ledger's other operational-surface deferrals.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-3` there) during the pre-shutdown deferred-work audit.

### DW-9-3-4: `query_audit_entries` materializes the whole matching set with no limit, and each read appends a row the next read returns
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `query_audit_entries` calls `list(AuditEntry.objects.filter(**filters))` and exposes no limit or pagination surface, against a table `models.py`'s own docstring describes as "expected to accumulate unboundedly between retention purges" — and because every read writes an `audit_read` row, the trail feeds itself: a compliance job polling once a minute adds 1,440 rows a day of pure self-reference, each read returning and counting all the previous ones.
  evidence: Raised independently by both reviewers in this story's review pass 2. Real but not patched: the spec's Code Map fixes this function's signature as reader identity plus arbitrary `**filters`, so adding a `limit` (and choosing its default, and deciding whether an unbounded read stays available at all) changes the published API rather than correcting it, and the compounding-self-noise half is a question about what the trail should record about itself, not a bug in what it currently does. Nothing here is load-bearing yet — the function has no callers in this worktree — so the cost of deferring is bounded, but the first surface that puts a real operator in front of the trail (an audit view, an export, or the retention runner) should not inherit an unbounded read.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-4` there) during the pre-shutdown deferred-work audit.

### DW-9-3-5: an actor made only of zero-width characters passes the non-blank check, so CAP-4's "who saw" can still be recorded as an invisible string
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `record_audit_entry` rejects a blank actor with `not actor.strip()`, but `str.strip()` removes only Unicode whitespace — a zero-width space, zero-width joiner, or byte-order mark is none of those, so `record_audit_entry("​", ...)` writes a row whose actor renders as nothing at all in every report that displays it, which is the state the blank check exists to make impossible.
  evidence: Raised by Edge Case Hunter in this story's review pass 2 and reproduced by execution (the row is created and reads back as `'​'`). Not patched: the right rule is a policy decision adjacent to the identity-normalization question this story deliberately answered with "store verbatim." Rejecting a hand-picked set of zero-width code points is arbitrary; rejecting by Unicode category (everything in `Cf`/`Zs`/`Cc`) is defensible but is a normalization policy applied at the boundary, which is exactly the kind of reinterpretation the spec's Boundaries argue the trail should not be making on its own. Whoever owns the identity model at the boundary — the first story that resolves where actor strings actually come from — should decide this alongside it, not this primitive in isolation.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-5` there) during the pre-shutdown deferred-work audit.

### DW-9-3-6: a future-dated `occurred_at` is never older than any cutoff, so a caller can write audit rows that no retention policy can ever expire
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `record_audit_entry` accepts any caller-supplied `occurred_at` whose awareness matches the deployment's, with no bound in either direction. A row stamped in the future never satisfies `occurred_at < cutoff`, so it survives every purge forever — AD-7's bounded trail quietly stops being bounded, one row at a time; a row stamped far in the past is conversely expired on the next cycle regardless of when the action really happened.
  evidence: Raised by Edge Case Hunter in this story's review pass 2 and reproduced by execution (a row stamped 100 years ahead survives `purge_expired_entries(AuditRetention(days=1))`). Deliberately not patched, unlike the structurally similar future-`now` guard added to `purge_expired_entries` in the same pass. The two differ in cost: `now` is a batch job's reference clock, where a future value is never meaningful and always over-deletes, so refusing it has no legitimate caller. `occurred_at` is on the request path — this is the primitive every load, filter, navigate and export calls — and in a multi-process deployment a caller stamping its own clock can be a few milliseconds ahead of the process running the check, so a strict refusal would turn ordinary NTP skew into a failed audit write and a failed request. Choosing between a strict bound, a skew tolerance, and clamping is a policy call the spec does not make; whoever owns the retention runner should make it against a real deployment's clock behaviour.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-6` there) during the pre-shutdown deferred-work audit.

### DW-9-3-7: `query_audit_entries`' `transaction.atomic()` is a savepoint inside a caller's transaction, so an outer rollback discards the `AUDIT_READ` row while the caller keeps the rows it read
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: Review pass 2 wrapped the read and its `AUDIT_READ` write in one `transaction.atomic()` block and documented it as closing AD-7's unrecorded-read hole, but Django's `atomic()` nested inside an already-open transaction is a savepoint, not an independent transaction — so under `ATOMIC_REQUESTS=True` (an ordinary Django production setting) or any service-level `@transaction.atomic`, a rollback removes the audit record of a read whose rows the caller has already received, leaving an unrecorded read that is repeatable on demand.
  evidence: Raised independently by both reviewers in this story's review pass 3 and reproduced by execution twice — once by wrapping the call in `transaction.atomic()` plus `transaction.set_rollback(True)`, once by raising inside the outer block; both left the caller holding the returned rows with zero `audit_read` rows surviving. Not patched: the two available fixes each change what deployments may call this function. `transaction.atomic(durable=True)` converts the silent hole into a loud `RuntimeError`, which is the module's own "refused rather than run unrecorded" idiom but makes `query_audit_entries` uncallable from any view running under `ATOMIC_REQUESTS=True`; writing the `AUDIT_READ` row on a separate connection so it commits independently sidesteps that but puts the audit write outside the caller's transaction entirely, which is a durability model the spec does not choose between. Pass 3 patched the docstring's overclaim so the guarantee is stated accurately (scope, not durability) and named the caller's responsibility; the substantive choice belongs with whichever story first puts a real request-path caller in front of the trail — Story 9.2's `filtering.py` or the export surface — since only a real caller settles which of the two costs is acceptable.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-7` there) during the pre-shutdown deferred-work audit.

### DW-9-3-8: nothing makes the audit trail append-only, so a single ORM call rewrites or erases CAP-4 evidence leaving no record that it happened
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `AuditEntry` is an ordinary Django model with no `save()`/`delete()` restriction and no deployment-level constraint, so any code in the process can call `AuditEntry.objects.filter(pk=...).update(...)` or `.delete()` and silently rewrite the record of what was seen. Every guard this story invests in is a *write-time* guard on `record_audit_entry`; none of them constrains what happens to a row afterwards, so CAP-4's "durable record" is durable only against accidental misuse of the sanctioned API.
  evidence: Raised by Blind Hunter in this story's review pass 3 and reproduced by execution — a `mallory / export / 500000 rows / salaries` row was rewritten to `bob / 1 / ""` by one `.update()` call, with zero entries recording the rewrite. Distinct from `DW-FU-9-3-3`, which covers the *sanctioned* purge going unrecorded; this is the unsanctioned-rewrite path. Not patched, and deliberately not patchable in this module alone: a `save()`/`delete()` override does not constrain `.update()` or raw SQL, so any in-process guard is advisory at best, and the real mechanisms — an INSERT-only database grant for the application role, an append-only table, or a hash chain over the rows — are deployment and schema decisions this story's spec neither makes nor scopes. It belongs with Story 9.5's deployment perimeter, which already owns this ledger's other operational-surface deferrals, and should be settled before any adopter relies on the trail as evidence rather than as telemetry.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-8` there) during the pre-shutdown deferred-work audit.

### DW-9-3-9: the identity perimeter admits an actor longer than the audit column's cap, so such a user can neither use the dashboard nor have the attempt recorded
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `DashboardIdentityMiddleware` imposes no length bound on the identity it extracts — its own comment names an LDAP DN as a legitimate value shape and defers any normalization to this story — while `record_audit_entry` rejects any actor over `AuditEntry.actor`'s 255-character cap rather than truncating it, so once Story 9.2/9.4's call sites are wired in, an identity longer than the cap makes every load, filter, navigate and export raise on the audit primitive, and none of those refused attempts is recorded either.
  evidence: Raised by Blind Hunter in this story's review pass 4 and reproduced by execution: a 330-character DN (`CN=<300 a's>,OU=Users,DC=example,DC=com`) passed through `DashboardIdentityMiddleware` onto `scope["dashboard_identity"]` intact, then `record_audit_entry` raised `ValueError: actor exceeds the 255-character audit field cap (got 330 characters)` with `AuditEntry.objects.count() == 0`. Real but not this story's to settle: the cap and the reject-rather-than-truncate rule are both explicit spec decisions ("cap length only as a robustness bound, and reject rather than truncate an overlong value so evidence is never silently corrupted"), and the spec's Boundaries forbid wiring this primitive into any call site here, so nothing in this worktree can exercise or fix the interaction. Closing it means choosing among widening the column, refusing an over-long identity at the perimeter where the caller can be told why, or recording a documented digest — a cross-story identity-model decision that belongs with whichever story first puts a real request-path caller in front of `record_audit_entry`, alongside `DW-FU-9-3-5`'s zero-width-actor question, which is the same boundary-normalization policy seen from the other end.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-9` there) during the pre-shutdown deferred-work audit.

### DW-9-4-1: The refusal-webhook POST blocks synchronously for up to 5s with no rate limit, on a path a caller can trigger repeatedly
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: `authorize_export`'s `_post_refusal_webhook` makes a synchronous `urllib.request.urlopen` call (up to a 5s timeout) on every refused export, with no async variant and no rate limit or backoff — if called from an async Channels consumer it stalls that worker's whole event loop for the duration, and a caller who knows they will be refused can trigger repeated 5s blocking calls with no throttle.
  evidence: Raised by Blind Hunter in this story's first review pass (two related findings, combined here: the blocking-call-in-async-context risk and the no-rate-limiting-on-a-refusal-triggered-network-call risk share one root cause). Not patched: this mirrors Story 9.1's own precedent for `get_master_dataset()` ("called from an async Channels consumer it blocks the whole worker's event loop — an async variant belongs with the first story that puts it on an async hot path", still open on this ledger) — no adopter view exists yet in this codebase to demonstrate which calling convention (sync Django view vs. async Channels consumer) actually applies, and CAP-6's deployment perimeter (Story 9.5) is where rate limiting / backpressure at the edge is architecturally scoped. Not addressed in this pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4` there) during the pre-shutdown deferred-work audit.

### DW-9-4-2: `maybe_encrypt_export` never removes the plaintext source after encrypting
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: When `policy.encryption_recipient` is declared, `maybe_encrypt_export` produces an encrypted `output` but leaves the original plaintext `path` untouched — if encryption exists to protect the exported artifact at rest, the plaintext copy sitting next to the ciphertext defeats that purpose unless the caller separately remembers to delete it, and nothing in this module says so.
  evidence: Raised by Blind Hunter in this story's first review pass. Not patched: `keys.encrypt_file` (Story 1.3), which this function wraps, already establishes the "never delete the input" contract, so deleting here would be new, surprising behavior for a caller who might own `path` for other reasons (re-export, a separate secure store) — deciding who owns cleanup of the plaintext source is a caller-lifecycle question best resolved once a real adopter export view exists to define it (Story 9.5/9.6), not invented unilaterally here.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4-2` there) during the pre-shutdown deferred-work audit.

### DW-9-4-3: The export-refusal webhook payload is unsigned, so a receiver cannot verify it actually came from this service
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: `_post_refusal_webhook` POSTs a plain JSON payload with no HMAC or shared-secret header — for a channel explicitly framed as a security-event notifier, a receiver has no way to distinguish a genuine refusal event from one forged by any other actor able to reach the same URL.
  evidence: Raised by Blind Hunter in this story's first review pass. Not patched: this story's own spec Design Notes already scoped the payload to be "intentionally minimal" and the architecture spine's Deferred section states "the webhook contract is fixed" (a plain POST) while naming which downstream SIEM/Slack/Teams sink adapters get built as the open demand question — payload signing is the same class of hardening-not-yet-demanded decision, best made together with Story 9.5's deployment-perimeter work (which already owns TLS/edge policy for this pattern) rather than unilaterally here.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4-3` there) during the pre-shutdown deferred-work audit.

### DW-9-4-4: `ExportPolicy.webhook_url` has no protection against loopback/link-local/internal targets
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: Construction-time validation only checks for an http(s) scheme and a real host — nothing rejects a declared webhook pointed at a loopback, link-local, or cloud-metadata address (e.g. `169.254.169.254`), a defense-in-depth gap for a server-side outbound POST.
  evidence: Raised by Blind Hunter in this story's first review pass. Not patched: `webhook_url` is adopter-declared configuration, the same trust level as `TrustedIngress.addresses`/`AccessDeclaration` elsewhere in this epic, not attacker-controlled per-request input, so this is not a classic SSRF vector today — but Story 9.1 set a precedent of deferring rather than dismissing this class of address-form concern for `TrustedIngress.addresses` (CIDR/hostname/IPv6-mapped forms, still open on this ledger), and this is the same category applied to a new declaration. Belongs with Story 9.5's deployment-perimeter/ingress model, which already owns the estate's other address-form questions.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4-4` there) during the pre-shutdown deferred-work audit.

### DW-9-4-5: `authorize_export` being "the ONLY place the decision is made" is a documented convention, not something enforced at the code level
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: Nothing wires `authorize_export` into an adopter's export view automatically (no decorator, no required call-site check) — an adopter's view that forgets to call it fails OPEN with no automated guard, which is the same "declared, not implemented" gap CAP-5 exists to close for the UI-gate case.
  evidence: Raised by Blind Hunter in this story's first review pass; confirms a gap this story's own spec Design Notes already named when explaining why a `steward deploy` wiring-verification CLI check does not belong in this story (it would need to import from `dashboard/`, which the existing invariant `test_no_module_outside_dashboard_imports_dashboard_django_or_channels` forbids). Story 9.5's deployment-perimeter surface is where that verification can exist without the import-boundary conflict; this entry moves the concern from a spec design note into a tracked follow-up so it is not lost.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4-5` there) during the pre-shutdown deferred-work audit.

### DW-9-5-1: The `perimeter` verb exposes no `--base-port`/`--bind-host` flags, leaving `_worker_ports`'s range check and `bind_host`'s injection guard unreachable in the shipped CLI
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-5-the-perimeter-ships-with-the-pattern.md`
  summary: `render_daphne_unit`/`render_edge_config` accept `base_port`/`bind_host` keyword parameters (defaulted to `8001`/`127.0.0.1`), but `_add_deploy_subparsers`'s `perimeter` parser exposes no `--base-port`/`--bind-host` flag, so `_run_perimeter` always calls them with the hardcoded defaults — an operator whose 8001+ range is already occupied on the target host has no way to override it. The same gap means `bind_host` is interpolated into both rendered manifests (`ExecStart=daphne --bind {bind_host} ...` and the nginx `upstream` block's `server {bind_host}:{p};`) without going through `_validate_nginx_value`'s injection-character guard, and `base_port` has no lower-bound check of its own (only the upper-bound `_worker_ports` overflow check) — both are currently safe only because neither is reachable from any operator-supplied input in the shipped CLI surface.
  evidence: Raised independently by two follow-up review-pass agents (Blind Hunter: missing `--base-port`/`--bind-host` flags; Edge Case Hunter: `bind_host` skips `_validate_nginx_value`, `base_port` has no `>= 1` check) during Story 9.5's follow-up review pass. Adding new CLI flags exceeds this story's frozen Code Map (`--workers`, `--cache-backend`, `--channel-layer-backend`, `--trusted-address`, `--tls-cert`, `--tls-key`, `--output-dir` only), so out of scope for this pass; revisit together if/when a future story exposes either parameter to the CLI.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-5` there) during the pre-shutdown deferred-work audit.

### DW-9-5-2: The rendered systemd unit name and nginx upstream name are hardcoded, so two perimeter deployments to the same host would collide
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-5-the-perimeter-ships-with-the-pattern.md`
  summary: `render_daphne_unit`/`render_edge_config` always name the systemd template unit `pyforge-steward-dashboard@.service` and the nginx upstream block `pyforge_steward_dashboard_workers`, with no `--name`/`--service-name`-style flag. Two independent perimeter deployments to the same host (e.g. staging and prod, or two adopter projects sharing infrastructure) would collide on both names, silently overwriting or conflicting with each other's manifests.
  evidence: Raised by Blind Hunter during Story 9.5's follow-up review pass. This story's own spec scopes exactly one `[dashboard]` extra / one deployment shape per adopter (its "Never" bullet rules out a second, nested extra for the same reason) and names no multi-instance-per-host requirement anywhere in the I/O matrix or Tasks, so a naming/namespacing flag is a scope addition, not a fix for something the current contract promises; revisit if a real adopter needs more than one perimeter deployment on one host.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-5-2` there) during the pre-shutdown deferred-work audit.

### DW-9-6-1: the dashboard test files' hand-duplicated `settings.configure()` guard, now in a fourth file, aborts the whole run when a Django-app-needing file collects behind one that only declares `CACHES`
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-6-isolation-proven-by-tests-that-cannot-pass-vacuously.md`
  summary: `test_dashboard_isolation_proof.py` (this story) declares only `CACHES` in its `settings.configure()` block, matching `test_dashboard_views.py`'s existing minimal pattern — but reproduced by execution: `pytest test_dashboard_isolation_proof.py test_dashboard_audit.py` (this file collected first) aborts the entire run at collection with `AssertionError: INSTALLED_APPS is []`, because whichever file's guard runs first wins Django's one-shot `settings.configure()` and a CACHES-only winner leaves `INSTALLED_APPS`/`DATABASES` unset for every file collected after it that needs them.
  evidence: Raised independently by this story's Blind Hunter review pass, reproduced by execution against both the new file and, identically, against the pre-existing `test_dashboard_views.py` (`pytest test_dashboard_views.py test_dashboard_audit.py` fails the same way) — confirming this is a pre-existing pattern from Story 9.2, not something this story introduced, so it is not this story's to fix. In a full-suite run (`pytest src/shared/packages/pyforge-steward/tests`, the only invocation any pixi task or CI-adjacent command actually uses) alphabetical collection order means `test_dashboard_audit.py` always wins the race with its fuller superset declaration, so the failure mode is real but latent — triggered only by a developer cherry-picking specific files on the command line in an unlucky order. Four files now hand-duplicate this same settings-configuration dance with no shared `conftest.py` (`test_dashboard_audit.py`, `test_dashboard_cache.py`, `test_dashboard_views.py`, and now `test_dashboard_isolation_proof.py`), each reasoning about "mutual superset" compatibility with the others by comment rather than by a single source of truth — the real fix (a `tests/unit/conftest.py` fixture or module doing one settings configuration all four files rely on) touches multiple existing files and is out of this test-only story's scope (its spec's Boundaries forbid modifying the existing `test_dashboard_*.py` files). Whoever next adds a fifth Django-needing dashboard test file, or hits this collection-order failure while iterating, should settle it then.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-6` there) during the pre-shutdown deferred-work audit.

### DW-9-7-1: dashboard_diff() cannot see a file staged (git add) but left uncommitted after a failed git commit
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-7-hosted-or-static-no-fork.md`
  summary: dashboard_diff() reports "nothing to deploy" for a change that is actually staged-but-uncommitted after a prior git commit failure, because it checks git diff (which matches once staged) and, as of this story, git ls-files --others (which excludes anything already staged) — neither surface sees a file in that intermediate state.
  evidence: Raised by Edge Case Hunter during this story's review pass 3, examining the dashboard_diff() extension this story added for untracked-file detection. The gap is pre-existing and not caused by this story: for an already-tracked file (the original data.js update path from Story 2.2), the identical failure mode already existed — if commit_and_push_dashboard's git add succeeds but its subsequent git commit fails (e.g. no git identity configured, a rejecting hook), the working tree now matches the staged index, so a bare git diff (no --cached) already reported empty on the very next invocation, before this story ever touched the function. This story's git ls-files --others addition inherits the same blind spot for newly-created files reaching that same staged-but-uncommitted state. Not this story's to fix: the root cause is dashboard_diff()'s fundamental reliance on git diff (working tree vs index) rather than git diff --cached (index vs HEAD) or git status --porcelain (which would see all three states — untracked, staged, and modified — uniformly), a design choice from Story 2.2 that predates and is orthogonal to whether the affected file is newly created or pre-existing. Whoever next revisits dashboard_diff()'s git plumbing should fold this in.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-7` there) during the pre-shutdown deferred-work audit.

### DW-9-7-2: publishing a static board requires a full dashboard-gen rebuild and a valid Steward sprint ledger, because deploy dashboard runs both unconditionally before it ever computes a diff
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-7-hosted-or-static-no-fork.md`
  summary: publishing a static board requires a full dashboard-gen rebuild and a valid Steward sprint ledger, because deploy dashboard runs both unconditionally before it ever computes a diff, so an adopter whose only goal is CAP-8's zero-infrastructure static export inherits two heavyweight preconditions that neither deploy static's help text nor its docstring mentions.
  evidence: Raised by Blind Hunter during this story's follow-up review pass and confirmed by reading `_run_dashboard` directly: it calls `_tracked_ledger_refusal(cwd=root)` and returns a refusal if Steward's own tracked `sprint-status-ledger.yaml` is missing or malformed (Story 5.2), then calls `build_dashboard(cwd=root)` — which shells out to `pixi run -e local-recipes dashboard-gen`, rebuilding the entire program console in a very large environment — and only afterwards reaches `dashboard_diff(cwd=root)`. Both run on the bare verb, with no flag to skip either. Story 9.7 did not introduce this ordering (it is Story 2.2's build-then-reconcile shape plus Story 5.2's ledger guard, both predating it) and did not change `_run_dashboard` at all; what changed is that 9.7 makes the bare `deploy dashboard` verb the designated publication path for `deploy static`'s output, per its own Approach ("the existing steward deploy dashboard verb then commits/pushes that unchanged — no new git plumbing"). That promise holds for the git plumbing specifically, which is why it is not a defect in this story, but it means a third-party adopter who only wants their own static board published cannot get there without satisfying Steward-internal preconditions unrelated to their board. Deliberately not fixed here: the plausible remedies (a `--skip-build` flag, scoping the ledger guard to the paths that need it, or a dedicated reconcile-only verb) all change the pre-existing `dashboard` verb's contract and its Story 2.2 / 5.2 acceptance criteria, which is outside this story's scope and needs its own decision about that verb's shape. Whoever next revisits `_run_dashboard`'s preconditions, or onboards the first external CAP-8 adopter, should settle it then.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-7-2` there) during the pre-shutdown deferred-work audit.


### DW-7-1-3: Follow-up review still recommended for 7-1-one-build-whole-guild after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-7-1-one-build-whole-guild.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260809-114839-7af9; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-1` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

### DW-9-1-2: Follow-up review still recommended for 9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260810-193158-7f2b; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-8` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

### DW-11-2-1: Story 11-2's original Pattern-A groundwork is superseded, not lost
- source_spec: 2026-08-21 sprint-change-proposal (this dir)
  summary: an earlier attempt at Story 11-2 built real, live-verified groundwork for DB-GPT's
  Pattern A integration (Django app scaffold, `dbgpt_schema` migration, settings wiring) before
  hitting the `fastapi` pin conflict documented in this same proposal. That work was committed
  and pushed to `backup/steward-11-2-blocked-adf57ec5` as an insurance copy, never merged. The
  2026-08-21 correct-course pass moves 11-2 to Pattern B (AD-14/AD-17); the schema-migration and
  settings-wiring pieces are pattern-agnostic and likely reusable, but the ASGI-dispatcher piece
  is Pattern-A-specific and should be discarded, not resurrected, by whoever next implements 11-2.
  evidence: `backup/steward-11-2-blocked-adf57ec5` branch, PR #571 (ledger correction marking
  11-2 blocked, since reopened to `backlog` by this proposal), and this proposal's own Impact
  Analysis § Epic 11.
  status: informational — no action needed unless 11-2's next implementer is unsure whether the
  backup branch represents live work to recover. It does not; recover pattern-agnostic pieces
  selectively, do not merge the branch wholesale.
  promoted: 2026-08-21 — added directly during the sprint-change-proposal correct-course pass.

### DW-11-2-2: DB-GPT's own metadata store cannot be wired to real PostgreSQL — verified upstream limitation, AD-9-blocked
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-11-2-db-gpt-joins-as-a-pluggable-app.md`
  summary: a second attempt at Story 11-2 (this one AD-17/Pattern-B-correct, not the reverted
  Pattern-A attempt DW-11-2-1 describes) built and live-verified the whole registry-driven
  integration — `dbgpt_schema` migration, `config/engine_patterns.py` AD-17 registry, a
  registry-consult touchpoint in `config/asgi.py` proving no ASGI mount is built for `dbgpt`,
  and a real Celery `text_to_sql` task round-tripping through the Story 10.5 sidecar
  (Gemini-backed, live SQL result returned) — but hit a genuine, dual-confirmed upstream wall
  wiring the SIDECAR's OWN metadata store (chat history, gpts apps, flow definitions) to real
  PostgreSQL: DB-GPT's own `dbgpt_app` package hardcodes SQLite/MySQL/OceanBase for
  `[service.web.database]` (`dbgpt_app/base.py`, `dbgpt_app/_cli.py::_get_migration_config`'s
  own `raise ValueError("Only SQLite is supported for migration now.")`), and working around
  that app-layer gate via DB-GPT's own public `db.create_all()` API (not a fork) fails with a
  real PostgreSQL DDL syntax error (`type modifier is not allowed for type "text"`) because
  DB-GPT's own SQLAlchemy models declare MySQL-only `TEXT(length)` columns (69 occurrences
  across the installed package set). AD-9 forbids forking DB-GPT's model classes to fix this.
  The sidecar's metadata store stays on Story 10.5's SQLite volume, now documented as permanent
  rather than interim. This does NOT block CAP-3's actual user-value goal (the text-to-SQL
  round trip, verified working): DB-GPT's metadata store and a queryable "datasource" (what the
  round trip actually uses, pointing at real PostgreSQL) are separate connections in DB-GPT's
  own architecture — only the former is blocked.
  evidence: `backup/steward-11-2-blocked-847ed9ec24` branch (the full registry-driven
  implementation, committed and pushed as an insurance copy, never merged — 14 files, incl.
  `dbgpt_integration/`, `config/engine_patterns.py`, `dbgpt_integration/tasks.py`), the spec's
  own Spec Change Log and Design Notes (full citation of both upstream errors), and
  `sprint-status-ledger.yaml`'s `11-2-db-gpt-joins-as-a-pluggable-app: blocked` entry.
  status: resolved 2026-08-21 (operator decision) — option (a): the sidecar's metadata store
  stays on SQLite+PVC permanently, recorded as a bounded, dated exception to AD-6
  (`ARCHITECTURE-SPINE.md`), with CAP-3's AC corrected to match (`SPEC.md`, `epics.md` Story
  11.2). The operator files the Postgres-support gap upstream with `eosphoros-ai/DB-GPT`
  directly (AD-9), not gated on it landing — real SQLAlchemy dialect-portability work, not a
  quick ask, so treated as independent of unblocking this story. `sprint-status-ledger.yaml`'s
  `11-2` reopened from `blocked` to `backlog`. The story's real, live-verified work (registry,
  schema migration, ASGI non-mount, the real Celery round trip) recovers wholesale from
  `backup/steward-11-2-blocked-847ed9ec24` — nothing in it needs to change for this decision.
  promoted: 2026-08-21 — added directly by the bmad-dev-auto implementation/orchestration pass
  that hit this blocker; resolved the same day via an approved correct-course pass, matching
  how DW-11-2-1's own Pattern-A blocker was resolved.

### DW-FU-11-4

`langflow_integration/tests.py` keeps an unguarded `cursor.fetchone()[0]` — the identical
pattern Story 11.4's gates forced a None-guard for in the story's own file (mypy `[index]`),
latent in the sibling only because it sits outside the `mypy platformapp config tests`
surface. Pre-existing; Story 11.4 treated the file as read-only. Remedy: None-guard it and
consider widening the mypy surface to the integration test modules. Severity: low. Status:
open. Relayed from the story worktree's ephemeral Tier-3 file at landing, 2026-08-21.

### DW-FU-12-2: The "395-package `python-agent-platform` env" figure embedded in timeout-justification comments has no mechanism keeping it accurate.

- source_spec: `planning-artifacts/specs/spec-12-2-gke-as-a-portability-profile.md`
  summary: The "395-package `python-agent-platform` env" figure embedded in timeout-justification comments has no mechanism keeping it accurate.
  evidence: Found by review during this story, but the figure pre-exists in the sibling `container` job's own timeout comment (platform-ci.yml, Story 10.3) — this story's `gke-portability-smoke` job reused the same descriptive phrasing for consistency, it did not introduce the figure. Not this story's regression to fix.
  location: .github/workflows/platform-ci.yml (container job's timeout-minutes comment, and gke-portability-smoke's own by extension)
  origin: spec-deferred a7f2167e2467 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-13-1: Bookkeeping YAML is not locked; concurrent start/clean in one checkout can race.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: Bookkeeping YAML is not locked; concurrent start/clean in one checkout can race.
  evidence: save_bookkeeping uses atomic_write but two processes can still interleaved read-modify-write over .steward/workspaces.yaml.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  origin: spec-deferred 5e5280514e6b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-13-1-2: start does not `git fetch` before branching from origin/main.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: start does not `git fetch` before branching from origin/main.
  evidence: Thin git wrap: if origin/main is stale or missing locally, start fails with a git error rather than refreshing remotes first.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  origin: spec-deferred d2605a4be02d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-13-1-3: A freshly started branch with no unique commits is treated as merged by --merged-only.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: A freshly started branch with no unique commits is treated as merged by --merged-only.
  evidence: merge-base --is-ancestor is true when tip equals source; accurate but surprising immediately after start.
  origin: spec-deferred 1457c9c38154 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-13-1-4: No tracked schema/example for `.steward/workspaces.yaml`.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: No tracked schema/example for `.steward/workspaces.yaml`.
  evidence: Review noted operators only get a gitignore entry; shape is discoverable only from code.
  origin: spec-deferred 3ef3c14440d7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-13-1-5: Distinct slugs that normalize to the same sibling path (e.g. a/b vs a-b) can collide.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: Distinct slugs that normalize to the same sibling path (e.g. a/b vs a-b) can collide.
  evidence: scratch_path_for replaces `/` with `-` without collision detection.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  origin: spec-deferred 8238370bede5 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-13-1-6: Stale bookkeeping entries (missing path / moved checkout) stay listed by ls.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: Stale bookkeeping entries (missing path / moved checkout) stay listed by ls.
  evidence: CAP-2 deliberately avoids per-worktree git; staleness is out of 13.1.
  origin: spec-deferred 490117283b3d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-13-2: status ahead/behind uses local source ref; no fetch of origin before counting.

- source_spec: `planning-artifacts/specs/spec-13-2-status-and-the-feed-mirror-decision.md`
  summary: status ahead/behind uses local source ref; no fetch of origin before counting.
  evidence: Same thin-git posture as 13.1 start (no auto-fetch). Stale origin/main makes behind under-count until the operator fetches.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  origin: spec-deferred 1347f0e476b0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-14-1: skill-manifest.csv parsing is a naive quoted-CSV split; skills with commas in fields would mis-parse.

- source_spec: `planning-artifacts/specs/spec-14-1-the-pre-flight-diff-retrodicts-a-real-upgrade.md`
  summary: skill-manifest.csv parsing is a naive quoted-CSV split; skills with commas in fields would mis-parse.
  evidence: `_read_installed_skill_names` splits on commas rather than using the csv module. Current skill IDs have no commas; review pass noted the fragility.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  origin: spec-deferred 4a363ab1e2e2 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-14-5: Trap 8 (.git/info/exclude stale shield lines) is not automated in prove-landed.

- source_spec: `planning-artifacts/specs/spec-14-5-one-command-proves-the-upgrade-landed.md`
  summary: Trap 8 (.git/info/exclude stale shield lines) is not automated in prove-landed.
  evidence: failure-modes.md lists trap 8 under CAP-5 orbit, but story ACs only require drift integrity + CFE meta + loop-home init/validate. Hand cleanup remains.
  location: upgrade.py CAP-5 gates
  origin: spec-deferred 7d9ac02dba5f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-1: Live (non-baseline) probe implementations are only exercised via stubs; no temp-repo / urllib-monkeypatch coverage for recipe/installed/HTTP paths.

- source_spec: `planning-artifacts/specs/spec-15-1-one-command-reports-the-whole-pipelines-truth.md`
  summary: Live (non-baseline) probe implementations are only exercised via stubs; no temp-repo / urllib-monkeypatch coverage for recipe/installed/HTTP paths.
  evidence: verification-gap review: default ProbeHooks paths never run in tests; operators' live `steward suite pipeline-truth` can diverge while --baseline stays green.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
  origin: spec-deferred 6e252fd00cd7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-1-2: Dashboard wired census uses loose fleet surfaces (docs/dashboard, presentations) rather than package-specific wire state.

- source_spec: `planning-artifacts/specs/spec-15-1-one-command-reports-the-whole-pipelines-truth.md`
  summary: Dashboard wired census uses loose fleet surfaces (docs/dashboard, presentations) rather than package-specific wire state.
  evidence: blind-hunter: both dashboards can read wired whenever those docs exist; baseline still encodes the 2026-08-22 research column.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
  origin: spec-deferred 00dbb10c84c7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-3: Conda installer subprocess has no timeout; a hung *-install can block the provision duty indefinitely.

- source_spec: `planning-artifacts/specs/spec-15-3-five-modules-wire-through-the-provisioning-verb.md`
  summary: Conda installer subprocess has no timeout; a hung *-install can block the provision duty indefinitely.
  evidence: Review edge-case finding: subprocess.run for CondaInstallBackend has no timeout= argument. Pre-existing pattern also applies to bmb setup-skill uv run calls; not uniquely introduced by 15.3 wiring.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  origin: spec-deferred 6daa4503bfc4 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-3-2: No rollback of copied skill dirs when post-install verification or manifest write fails after installer exit 0.

- source_spec: `planning-artifacts/specs/spec-15-3-five-modules-wire-through-the-provisioning-verb.md`
  summary: No rollback of copied skill dirs when post-install verification or manifest write fails after installer exit 0.
  evidence: Skills may be copied before manifest record; a later raise leaves orphan .claude/skills entries without a module key. Collision check then blocks retry until skills are removed manually.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  origin: spec-deferred 66b476615235 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-3-3: --list-modules does not surface _SKIPPED_MODULES (WDS) or skip reasons.

- source_spec: `planning-artifacts/specs/spec-15-3-five-modules-wire-through-the-provisioning-verb.md`
  summary: --list-modules does not surface _SKIPPED_MODULES (WDS) or skip reasons.
  evidence: Operators cannot discover from the list verb that WDS is intentionally unwired versus simply unsupported; skip is only on --module wds.
  origin: spec-deferred 8f88ef20f773 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-3-4: Hard-coded _CIS_SKILL_NAMES allowlist is not asserted against the live bmad-creative-intelligence-suite share tree.

- source_spec: `planning-artifacts/specs/spec-15-3-five-modules-wire-through-the-provisioning-verb.md`
  summary: Hard-coded _CIS_SKILL_NAMES allowlist is not asserted against the live bmad-creative-intelligence-suite share tree.
  evidence: Drift shows up only as post-install skills-missing RuntimeError.
  origin: spec-deferred 9fff87be3e08 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-4: Live prove-landed may still hit the network / warm caches when running cited npx/uv spot-checks even with --help/--dry-run.

- source_spec: `planning-artifacts/specs/spec-15-4-the-upgrade-gate-spot-checks-one-native-path-per-class.md`
  summary: Live prove-landed may still hit the network / warm caches when running cited npx/uv spot-checks even with --help/--dry-run.
  evidence: Story 15.4 deliberately invokes native CLIs; side effects are inherent to the AC. Failures remain advisory.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  origin: spec-deferred b3a8e13b0b34 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-4-2: skip_native_spot_checks exists on build_prove_landed_report but has no CLI flag.

- source_spec: `planning-artifacts/specs/spec-15-4-the-upgrade-gate-spot-checks-one-native-path-per-class.md`
  summary: skip_native_spot_checks exists on build_prove_landed_report but has no CLI flag.
  evidence: Not required by CAP-4 AC.
  origin: spec-deferred 870ab68a8b44 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-15-4-3: _BMAD_LOOP_UV_GIT_SPEC hard-pins v0.11.0 with no regeneration note when the matrix version moves.

- source_spec: `planning-artifacts/specs/spec-15-4-the-upgrade-gate-spot-checks-one-native-path-per-class.md`
  summary: _BMAD_LOOP_UV_GIT_SPEC hard-pins v0.11.0 with no regeneration note when the matrix version moves.
  evidence: Citation substring test catches matrix edit drift after the fact.
  origin: spec-deferred 9d95aae537b3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-16-2: Operator-facing deploy README / NOTES still omit COMPONENT_RUNTIME and the invalid DJANGO_ADMIN_URL set beyond the chart values change.

- source_spec: `planning-artifacts/specs/spec-16-2-startup-refuses-misconfiguration-two-stage-and-named.md`
  summary: Operator-facing deploy README / NOTES still omit COMPONENT_RUNTIME and the invalid DJANGO_ADMIN_URL set beyond the chart values change.
  evidence: Blind-hunter noted docs/NOTES still describe required env without CAP-3 locality or admin-URL validity rules. Chart default was patched; prose docs were not fully rewritten this story.
  location: src/platform/deploy/README.md
  origin: spec-deferred 3d536d29639e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-16-2-2: is_serving_process / COMPONENT_PROCESS locality helpers ship without dedicated tests (unused by CAP-3 stage-2 conditions yet).

- source_spec: `planning-artifacts/specs/spec-16-2-startup-refuses-misconfiguration-two-stage-and-named.md`
  summary: is_serving_process / COMPONENT_PROCESS locality helpers ship without dedicated tests (unused by CAP-3 stage-2 conditions yet).
  evidence: Blind-hunter / verification-gap: PROCESS_ENV_VAR is declared for later stage-2 DB conditions; CAP-3 does not depend on it. Low risk until those conditions land.
  location: src/platform/config/locality.py
  origin: spec-deferred 67f0dccfc906 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

---

## Canopy course correction (2026-08-24)

### DW-CANOPY-2026-08-24

- source_spec: `planning-artifacts/change-history/sprint-change-proposal-2026-08-24-canopy.md`
  summary: Canopy Phase 5 (`spec-pyforge-unifying-strategy`) — reconcile shipped Epic 11 with Epic 27 DDL governance without reopening engine integration stories.
  evidence: Epic 11 Stories 11.1–11.2 provisioned `langflow_schema` / `dbgpt_schema` via Django `RunSQL` under parent AD-5; Canopy CAP-9 / FR-22 / canopy AD-9 moves production DDL to Liquibase (Epic 27). Architecture spine marks this as conflict-not-override — isolation and `search_path` remain; only the DDL producer changes.
  resolution: **11.1 and 11.2 are NOT reopened** — sprint-status stays `done`; isolation shipped. **Epic 27 is the superseding forward work** (S-27.1 operator gate → S-27.2 pre-upgrade Job + DML-only app role → sqlmigrate CI gate). Do not queue rework of 11.1/11.2 when FR-22 lands.
  open_joint: `lane1-serves-dw-h3` — whether Lane 1 (Wagtail) serves atlas data-warehouse H3 surfaces — **remains open**; joint steward/atlas decision; not invented in steward Canopy stories.
  origin: Phase 5 bmad-correct-course, pyforge-steward, 2026-08-24
  severity: medium
  status: open
