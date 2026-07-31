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
