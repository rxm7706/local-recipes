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

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-2-2

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: `HostScopedCredential` carries no field identifying which specific credential/env-var it represents (only `hosts`) — `resolve_headers` returns whatever `_http.py`'s `auth_headers_for` happens to resolve for a matched host, so two credentials with overlapping host sets are indistinguishable and there's no way to label an entry for display/audit purposes.
  evidence: `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `HostScopedCredential` dataclass has only a `hosts: tuple[str, ...]` field. Story 1.5's own AC (`_bmad-output/planning-artifacts/epics.md`, Story 1.5) already requires `steward keys list` to enumerate "that identity's name, scope, last-rotated timestamp" — so a `name` field will need to land on this dataclass (or its Story-1.5 inventory counterpart) regardless; flagged now so Story 1.5 doesn't rediscover it from scratch.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/3 present (absent: _bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md, _bmad-output/planning-artifacts/epics.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-2-3

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: `resolve_headers` gates *whether* ambient auth attaches, not *which* credential — an in-allowlist URL receives whatever `_http.py`'s host-blind chain resolves first (JFROG_API_KEY at priority 1 for ANY host), so a credential allowlisting a non-JFrog host (e.g. `github.com`) ferries the ambient JFrog key to that host. Distinct from the earlier no-identity-field entry (display/audit labeling): this is about which header attaches. Spec-conformant (the story's Boundaries mandate full delegation and host-membership-only decisions, and the wrapper strictly narrows the ungated baseline), so not fixable this story — needs a per-credential header-selection design decision in a later keys story, likely landing together with the Story-1.5 identity field.
  evidence: Confirmed by execution 2026-07-30 (Story 1.2 follow-up review): `resolve_headers(HostScopedCredential(hosts=("github.com",)), "https://github.com/x")` with `JFROG_API_KEY` set returned `{'X-JFrog-Art-Api': ...}`. `_http.py`'s own `auth_headers_for` docstring documents step-1 JFrog injection as "the documented cross-resolver leak". A docstring scope note was added to `HostScopedCredential` this pass so callers are not misled meanwhile.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-2-4

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: Executed (not hand-traced) drift-scanner probes against mutations of the real `_http.py` pin down the detector's limits beyond the two earlier detector entries — (i) removing the `skip_auth` gate IS caught (exactly one finding at the `auth_headers_for` JFrog-attach line, so the realistic regression the story guards is covered), but (ii) the same regression respelled with `os.getenv("JFROG_API_KEY")` yields 0 findings, (iii) any unrelated early-return guard above the attachment (e.g. `if not url: return {}`) suppresses detection entirely, and (iv) Compare-form presence checks (`os.environ.get("K") is not None`, `"K" in os.environ`) are misclassified as scope gates, exempting the whole function.
  evidence: All four results produced by running `keys.scan_source` on mutated copies of the real `_http.py` source during Story 1.2's follow-up review pass 2026-07-30. Same "Never: not a pluggable rule engine" scope boundary as the two earlier detector entries — harden together with them in/after Story 1.6's `audit --drift` verb.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-2-5

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: `resolve_headers` never consults the URL scheme — an in-allowlist host receives the credential header over plaintext `http://` exactly as over `https://`. Inherited from `_http.py`'s own scheme-blind chain (every ungated caller has this today), but the keys duty is the natural place for a scheme gate (or warning) when the resolver grows in a later story.
  evidence: `keys.py`'s `resolve_headers` computes only `urlparse(url).hostname`; the scheme is never read. Confirmed by execution 2026-07-30: `resolve_headers(cred, "http://artifactory.example.com/x")` returns the API-key header.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-1

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_directory_for_secrets`/`scan_file_for_secrets` recurse via unfiltered `Path.rglob("*")` — pointed at a real repo root (Story 1.6's eventual dogfood use case), this walks `.git`'s object store, `.pixi`, and any build/cache tree with no exclusion list, which is both slow and a plausible false-positive source (packfile bytes can coincidentally contain pattern-shaped substrings).
  evidence: Confirmed by reading `scan_directory_for_secrets` in `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` — no path filtering exists. Flagged by Story 1.3's adversarial review pass 2026-07-30. Out of this story's tested scope (only run against small fixture directories); must be addressed before Story 1.6 wires `steward keys audit --drift`'s dogfood task against the real repo.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-2

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: The plaintext-secret pattern table (`_SECRET_PATTERNS`) covers an Anthropic `sk-ant-` key, a plaintext `age` identity, and a PEM header — but omits the JFrog-API-key shape, which is one of the two named historical incidents motivating this whole epic. Deliberate: JFrog Artifactory API keys have no stable, literal, universally-recognizable prefix to pattern-match narrowly (unlike the three included shapes), so adding one risks becoming the general-purpose/high-entropy heuristic this story's spec explicitly forbids.
  evidence: `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `_SECRET_PATTERNS` tuple has exactly 3 entries, no JFrog-shaped pattern. Flagged by Story 1.3's adversarial review pass 2026-07-30. Revisit if a stable JFrog-token format is ever confirmed, or if Story 1.6 needs to close this specific gap by another means.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-3

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `encrypt_file`/`decrypt_file` pass `--output <path>` straight to `age`, writing directly to the final destination with no temp-file+rename on Steward's side — an interrupted `age` process (SIGINT, disk full) could leave a truncated/corrupt file sitting exactly at a path this feature's premise is to commit to git. Whatever atomicity guarantee exists is `age`'s own responsibility (AD-1: wrap, never reimplement), not independently verified here.
  evidence: `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `encrypt_file`/`decrypt_file` bodies are a single `subprocess.run(..., check=True)` call with no pre/post staging. Flagged by Story 1.3's adversarial review pass 2026-07-30; no test covers an interrupted write.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-4

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: No `.gitattributes` entry marks `*.age` as binary (`-diff -merge -text`). Not yet actionable — no `.age` file is committed as a durable repo artifact by this story (only ephemeral `tmp_path` test fixtures) — but worth adding once Story 1.4/1.5 starts committing real encrypted payloads under `.steward/`.
  evidence: Repo-root `.gitattributes` has no `*.age` rule (checked 2026-07-30, Story 1.3 review pass). Premature to add now since nothing matches it yet.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-5

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: If the `age` binary is missing from PATH, `encrypt_file`/`decrypt_file` raise an uncaught `FileNotFoundError` (not `subprocess.CalledProcessError`), which `KeysDuty.run` doesn't catch — `cli.main()`'s generic exception handler projects it to `EXIT_INTERNAL` with a raw traceback rather than a clean `DutyResult(ok=False, ...)` message. Defensible under AD-8 (a missing external tool is arguably an environment failure, not a normal duty-level failure) and low-probability in practice (this story's own pixi.toml change declares `age` as a run-dependency of the env this code runs in), but worth a consistency pass once more duties exist and their failure-mode conventions can be compared side by side.
  evidence: `KeysDuty.run`'s `except subprocess.CalledProcessError` clause in `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` does not catch `FileNotFoundError`. Flagged by Story 1.3's edge-case review pass 2026-07-30 (not independently executed against a PATH with `age` removed, but the code path is unambiguous by inspection).
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-6

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `encrypt_file`/`decrypt_file`'s `subprocess.run` calls carry no `timeout`, so a hung/stalled `age` process (unexpected prompt, unresponsive I/O) would block `steward keys encrypt`/`decrypt` indefinitely with no way to abort short of an external kill. Low practical risk — `age` is invoked here only in its non-interactive, fully-flagged form (never passphrase mode) — but worth a blanket timeout policy if adopted uniformly across duties later.
  evidence: Neither `subprocess.run` call in `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `encrypt_file`/`decrypt_file` passes `timeout=`. Flagged by Story 1.3's edge-case review pass 2026-07-30.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-7

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_file_for_secrets` matches each pattern with `.search()` (first match only) per line, so two occurrences of the *same* pattern on one line produce one finding, not two — an undercount. The actionable signal (this line needs inspection) is preserved either way, so this doesn't affect correctness of "is this file clean," only the reported count.
  evidence: Confirmed by execution 2026-07-30 (Story 1.3 edge-case review pass): a line with two distinct `sk-ant-...`-shaped substrings yielded exactly one `PlaintextSecretFinding`. Worth fixing (`finditer` instead of `search`) if `keys audit`'s eventual CLI output ever reports finding *counts* to the operator.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-8

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_file_for_secrets`, called directly (not through `scan_directory_for_secrets`, which pre-filters to real files) on a directory or a nonexistent path, raises an unhandled `IsADirectoryError`/`FileNotFoundError` rather than a clear, documented error. Not reachable today — the only current caller (`scan_directory_for_secrets`) always passes real, already-`is_file()`-checked paths — but Story 1.6's CLI verb will likely accept an arbitrary user-supplied single-file path and should validate it before calling this primitive.
  evidence: `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`'s `scan_file_for_secrets` does `path.read_bytes()` with no existence/type check. Flagged by Story 1.3's edge-case review pass 2026-07-30.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-9

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: Epics.md Story 1.3's AC2 literally reads "When `steward keys audit` … is run against a directory" — unlike Story 1.2's own AC1, which explicitly hedged ("`steward keys audit --drift`-equivalent logic … the underlying detection primitive Story 1.6 later exposes as a full CLI verb"), 1.3's AC2 carries no such explicit hedge. This story's spec resolved the ambiguity as primitive-only (no CLI verb), reasoned from Cross-Story Dependencies' inventory-writer list (which names 1.4/1.6/1.7, not 1.3) and 1.2's identical framing precedent — but the epics.md text itself is more ambiguous here than in 1.2, so this is a real interpretive judgment call, not a certainty.
  evidence: `_bmad-output/planning-artifacts/epics.md` Story 1.3 AC2 vs. Story 1.2 AC1 wording, compared directly 2026-07-30. Flagged by Story 1.3's adversarial review pass. Story 1.6 should explicitly confirm its `steward keys audit` CLI verb exposes both `DriftFinding` and `PlaintextSecretFinding`, closing the loop this interpretation opened.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md, _bmad-output/planning-artifacts/epics.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-10

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `planning-artifacts/epics.md` Story 1.3's ACs still promise a `steward keys audit` verb in this story and `age`/`age-keygen` declared in repo-root `[feature.pyforge-steward.dependencies]`, but the shipped story (deliberately, per its spec's Always/Never clauses) defers the audit verb to Story 1.6 and declares `age` in the package's own `[package.run-dependencies]` — the tracked Tier-2 epic contract now contradicts the shipped code and needs reconciling.
  evidence: `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` § Story 1.3 vs `src/shared/packages/pyforge-steward/pixi.toml` and `cli.py`; verified 2026-07-30 (Story 1.3 follow-up review) that `steward keys audit` is rejected by argparse (exit 2). Both narrowings are recorded in the story spec's intent contract; the epic was never updated to match.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 2/3 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-11

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_file_for_secrets` decodes raw bytes as UTF-8-with-replacement only, so a secret sitting in a UTF-16/UTF-32-encoded file (a routine Windows-tooling artifact) is invisible — the interleaved NUL bytes break every pattern and the file silently reads as clean.
  evidence: Confirmed by execution during Story 1.3's follow-up review 2026-07-30: the fixture's `sk-ant-` line re-encoded as UTF-16 produced zero findings. A BOM sniff before decode would close the common case; deliberately not added this story (fixed-pattern-table restraint), revisit when Story 1.6 wires `steward keys audit`.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-12

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: The plaintext-secret scan has no deliberate symlink policy — directory symlinks are never traversed (a committed dir-symlink hides an entire subtree from the audit) while file symlinks ARE followed (the scan reads content outside the requested directory); both directions need an explicit decision when Story 1.6 wires the audit verb.
  evidence: `scan_directory_for_secrets` walks with `Path.walk(follow_symlinks=False)` (made uniform during the 2026-07-30 follow-up review; previously 3.12-vs-3.13 `rglob` divergence) but the per-file `is_file()` check follows file symlinks. Dir-symlink invisibility confirmed by execution during the same review.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-13

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: Steward's own test tree deliberately contains pattern-matching literals (the `plaintext_secret_candidate` fixture plus inline word-marked `sk-ant-`/`AGE-SECRET-KEY-`/PEM strings in `test_keys_plaintext_secret_scan.py`), so pointing the future `steward keys audit` at the repo or the package itself reds on its own tests — Story 1.6 needs a fixture/allowlist policy before the audit verb can gate anything.
  evidence: Self-scan executed during Story 1.3's follow-up review 2026-07-30: 4 findings inside `src/shared/packages/pyforge-steward/`, all synthetic/word-marked by design. `scan_directory_for_secrets`'s signature has no exclusion hook.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-14

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `keys.py` (Story 1.2) resolves its `_http.py` bridge at module import time — ancestor marker-walk, `sys.path` mutation, `from _http import ...` — and raises `RuntimeError` outside a local-recipes checkout; the CLI now lazy-imports `KeysDuty` (patched this review) so `steward --help`/`--version`/other duties survive, but `steward keys <verb>` still fails at duty-resolution time in a package installed outside a checkout, and `pyproject.toml`'s "imports only the standard library" comment is stale. Making the bridge lazy (resolve at first `resolve_headers`/`scan_source` call) is a Story-1.2-scoped refactor.
  evidence: Confirmed by execution 2026-07-30 (Story 1.3 follow-up review): importing a copy of the package from outside the repo raised `RuntimeError: keys.py: could not locate .claude/skills/conda-forge-expert/scripts/_http.py ...` at `import pyforge.steward.keys`; after the CLI lazy-import patch, `main(["--version"])` works outside a checkout but the keys duty cannot.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-15

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `decrypt_file` writes plaintext with default umask permissions (observed mode 664 — group/world-readable) — inherited thin-wrap `age -o` behavior, acceptable while the caller picks the output path, but once Stories 1.4/1.5 have Steward itself materialize decrypted secrets it should tighten output modes (0600) or record why not.
  evidence: Observed by execution during Story 1.3's follow-up review 2026-07-30: a fresh decrypt output file was created mode 664 under umask 0002. No test or doc covers output permissions; AD-1 thin-wrap means `age`'s defaults rule today.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-3-16

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md`
  summary: `scan_file_for_secrets` slurps each file whole (`read_bytes()` + full-text decode, up to ~2-4x memory expansion) with no size cap or streaming, so a single multi-GB file anywhere in the scanned tree (build artifact, packfile, database dump) exhausts memory and can OOM-kill the audit mid-scan — and a SIGKILL bypasses even the primitive's fail-loud posture, since no Python exception reaches the caller. Harmless at this story's fixture scale; needs a size gate or chunked/streaming read before Story 1.6 points the scan at real repo trees. Distinct from the existing `.git`/`.pixi`-walk entry, which is about scan scope/speed/false positives, not memory exhaustion.
  evidence: Flagged independently by both review agents in Story 1.3's second follow-up review pass 2026-07-30; code-certain from `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` — `path.read_bytes()` materializes the full file and `scan_directory_for_secrets` feeds it every regular file in the walk with no size check.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plaintext.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-7-1-1

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: A follow-up review was still RECOMMENDED for Story 7.1 when the damping cap (`limits.max_followup_reviews = 2`) was spent. The story finalized anyway — `status: done`, verify green, work committed by bmad-loop run `20260809-114839-7af9` — so the lingering recommendation has no owner unless it is recorded here. The story consumed both dev attempts and all three review cycles, and the third review pass was still finding substantive issues (build-context fidelity, wrong comments, arg symmetry), which is the reason the reviewer wanted another look rather than a generic caution.
  evidence: bmad-loop damping output, promoted from Tier-3 `implementation-artifacts/deferred-work.md` where it was written as the generic id `DW-1`. Renamed to this ledger's `DW-<epic>-<story>-<n>` convention on promotion — `deferred_work_check` warns that the generic id collides with the next damped story, since bmad-loop emits `DW-1` every time.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-7-1-2

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: NINE sites carry a pixi version and they are NOT all equal — feature pins + `environment.yaml` + the new Containerfile builder image sit at `0.76.1`; `pixi.toml`'s own `requires-pixi` floor, the `"$schema"` URL, and the dashboard.yml / kedro-viz-publish.yml pins sit at `0.75.0`; and `.github/actions/sync-pypi-mappings/action.yml` sits at `0.73.0`. The four EXACT pins are the sharp ones: any below the floor installs a pixi that REFUSES to parse this manifest. `sync-pypi-mappings` IS below it today, so a `workflow_dispatch` of "Sync PyPI-Conda Mappings" installs a pixi that cannot read `pixi.toml`. Pre-existing drift, not introduced by 7.1; no detector enforces cross-site pixi-version equality, which is why it accumulated silently.
  evidence: Enumerated by Story 7.1's review pass while rewriting `requires-pixi`'s comment (see the comment itself in `pixi.toml`, which now lists all nine sites). Recorded rather than fixed: correcting a version pin inside a container story would be unrelated scope, and the real remedy is a detector, not nine hand edits.
  resolution: RESOLVED 2026-08-09 at the operator's direction. All nine aligned to **0.76.1**, chosen because it is the LOCK'S PRODUCER — the rule `dashboard.yml` states for itself ("pixi-version stays pinned to the lock's producer... Bump it in step with pixi.lock"). Aligning merely to the old 0.75.0 floor would have closed the break while leaving the dashboard and kedro-viz pins stale against their own invariant. Changed: `pixi.toml`'s `$schema` URL + `requires-pixi`, `dashboard.yml`, `kedro-viz-publish.yml`, `sync-pypi-mappings/action.yml` (the broken one, v0.73.0), `staged-recipes-linter.yml`. Already at 0.76.1 and untouched: the three feature pins, `environment.yaml` (derived), the Containerfile image tag. Verified: the v0.76.1 schema URL resolves to a real schema (`$id` matches, HTTP 200 after redirect — a 301 alone proves nothing); `pixi info` accepts the manifest under the raised floor; `pixi lock --check` reports already-up-to-date; `environment.yaml` regenerates byte-identical.
  residual: The equality is still COMMENT-MAINTAINED — nothing enforces it, which is exactly how it drifted three ways. A cross-site pixi-version detector remains the durable fix and is NOT delivered here; this entry stays as the record of why one is wanted.
  status: resolved

  verified: 2026-08-26 — resolved — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to resolved

  verified: 2026-09-02 — resolved — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to resolved; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-1-1

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: follow-up review still recommended for 9-1 after the damping cap was spent — an independent pass is owed on the ASGI identity boundary, declared isolation, and cache invariant work.
  evidence: the follow-up-review damping cap (`limits.max_followup_reviews = 2`) was spent with the story finalized (status `done`, verify green) while the review pass still recommended an independent follow-up. Committed by bmad-loop run `20260810-193158-7f2b`. The story's own review pass 2 closed a duplicate-header identity spoof, which is the profile where an independent pass is worth spending.
  promoted: 2026-08-11 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-8` there) under this ledger's own `DW-<epic>-<story>-<n>` convention, renamed to avoid colliding with the next damped story (bmad-loop always emits a generic id).
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10: Follow-up review still recommended for 10-3-one-image-both-engines after the damping cap was spent
origin: review-budget-followup
source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260814-202735-e909; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9: Follow-up review still recommended for 9-3-the-audit-trail-records-what-was-seen after the damping cap was spent
origin: review-budget-followup
source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260812-191714-167d; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-1-1: spec-python-agent-platform's `environment.yaml` surface declaration has no counterpart in sibling specs that also declare `pixi.toml`
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-1-the-host-renders-into-src-platform.md`
  summary: `spec-python-agent-platform`'s frontmatter `surface:` list already declared `environment.yaml` (predating this story) while several sibling specs that also declare `pixi.toml` (`spec-bmad-loop-baseline-drift`, `spec-unified-container`, `spec-pyforge-core`, `spec-pyforge-warden`, `spec-pyforge-marshal`, `spec-pr-lifecycle`, `spec-bmad-output-hygiene`) do not declare `environment.yaml` alongside it, so a future `pixi.toml` change under any of those specs (which per `CLAUDE.md`'s own always-on rule must regenerate+commit `environment.yaml` in the same change) will register `environment.yaml`'s drift against `spec-python-agent-platform` instead of the spec that actually caused it.
  evidence: Raised independently by both this repair session's Blind Hunter and Edge Case Hunter reviewers, framed as caused by this session's removal of `scripts/spec_surface_allowlist.txt`'s `environment.yaml` exemption line. Verified that framing is incomplete: `spec-python-agent-platform`'s surface already listed `environment.yaml` before this story's `baseline_revision` (`c83924d3563e0aa7c78f6b6798ef41c9e64636be`, from the prior `steward: decompose spec-python-agent-platform into Epics 10-12` commit) -- confirmed the removed allowlist line was already dead for this file regardless (the allowlist is only consulted when zero spec's surface matches; `environment.yaml` already matched before this repair touched the allowlist), so the underlying multi-owner conflict predates this story and this session's own change. Not this story's to fix: resolving it means editing the `surface:` list of several specs this story does not own (all outside `pyforge-steward`, several in other BMAD projects entirely), which is out of a single story's scope. Whoever next touches one of the listed sibling specs' `pixi.toml` surface entry should either add `environment.yaml` alongside it or have `spec-python-agent-platform` drop its own `environment.yaml` claim in favor of a single canonical owner.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-1` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-1-the-host-renders-into-src-platform.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-2-1: `python-agent-platform`'s `platforms = ["linux-64", "osx-arm64-min"]` excludes win-64 with no stated rationale
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md`
  summary: The new `[feature.python-agent-platform]` block (and every other new comment/doc surface this story touched) never states whether win-64 is excluded because `langflow`/`dbgpt`/`dbgpt-serve` genuinely lack conda-forge win-64 builds, or because the platform list was simply copied from the spec's literal Task-1 instruction without independently checking — every other platform-restricted feature in this file (`shellcheck`, `gcloud-sdk`, `ocrmypdf`, `mlx`) documents the specific constraint forcing the restriction inline.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this story's review pass (corroborated). The `platforms = ["linux-64", "osx-arm64-min"]` value is spec-mandated verbatim (Tasks & Acceptance, Task 1) so implementing it as spec'd was correct; the gap is in the spec/doc layer, not the code. Not this story's to fix unilaterally (the intent-contract's package/platform list is frozen); whoever next touches this feature (likely Story 10.3, which also evaluates container platform support) should confirm via `lookup_feedstock` whether any of the three engines is win-64-absent on conda-forge and record the finding in the feature's own comment block.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-2-2: `channel-priority = "flexible"` on `[feature.python-agent-platform]` widens cross-channel resolution eligibility to every dependency in the feature, not just the one package (`slowapi`) it was added for
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md`
  summary: The feature-scoped `channel-priority = "flexible"` override (added because pixi 0.76.2's workspace-default `"strict"` mode hard-excludes `SelfExplainML`'s relaxed `slowapi` build the instant conda-forge has any build of the same name, even an infeasible one) is a whole-feature solver setting: any future dependency added to `python-agent-platform` that happens to have builds on both `conda-forge` and `SelfExplainML` becomes eligible for cross-channel resolution too, not only `slowapi`. In a factory whose entire premise is "factory-sourced" (this story's own title, CAP-5), that is a wider trust-boundary loosening than the single-package problem it solves.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this story's review pass (corroborated). The override is already transparently documented (this spec's own Spec Change Log, 2026-08-14 "implementation, deviations from literal instructions" entry) as scoped to this one feature only, with a known, tracked upstream retirement path (`conda-forge/slowapi-feedstock#4`, open, would let this override be dropped once merged) -- so the risk is bounded in both scope and time, not indefinite. A more surgical alternative (an explicit per-dependency `channel = "SelfExplainML"` override on `slowapi` alone, leaving the feature's channel-priority at the workspace default) was not attempted because `slowapi` is a transitive-only dependency and declaring it explicitly would itself read as a "speculative addition" beyond the intent-contract's frozen eight-package list. Whoever next revisits this feature (or when `conda-forge/slowapi-feedstock#4` merges) should re-evaluate whether `channel-priority = "flexible"` can be narrowed or removed entirely.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-2-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-2-3: two other specs that also declare `pixi.toml` in their `surface:` (`pyforge-marshal/spec-pyforge-core`, `pyforge-steward/spec-unified-container`) already carry a stale `pixi.toml` baseline hash, predating this story, silently absorbed instead of reported
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md`
  summary: `scripts/.spec-surface-baseline.json` governs `pixi.toml` under four specs, not just the two this repair pass reconciled (`pyforge-marshal/spec-bmad-loop-baseline-drift`, `pyforge-steward/spec-python-agent-platform`). `pyforge-marshal/spec-pyforge-core`'s stored `pixi.toml` hash (`449b3179...`) and `pyforge-steward/spec-unified-container`'s (`f3e313fe...`) both predate this story's own `pixi.toml` edit (neither matches the pre-story hash `0f9455fd...` either) -- these two specs' baselines were already stale before Story 10.2 touched anything. `python -m pyforge.doctor.sources spec-surface` does not report either as a finding (gating or WARN) today: `chain.py::_drift_findings` only escalates to gating `drift` when the spec's memlog is unchanged since baseline, and both specs' memlogs happen to already contain the literal substring `pixi.toml` somewhere in their historical text (unrelated entries), which silently satisfies the `f not in named` check and suppresses even a `drift-presumed` WARN. The multi-owner gap is a known, already-deferred class (`DW-FU-10-1`, about `environment.yaml`'s multi-owner conflict across the same sibling-spec set) -- this is the `pixi.toml`-side instance of the same underlying problem, but concretely already-drifted rather than merely structurally possible.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this repair pass's review. Verified directly: `python3 -c "import json; d=json.load(open('scripts/.spec-surface-baseline.json')); print(d['pyforge-marshal/spec-pyforge-core']['files']['pixi.toml'], d['pyforge-steward/spec-unified-container']['files']['pixi.toml'])"` against `git show 4febffd7bf:pixi.toml | sha1sum` (the pre-story hash) and the current `sha1sum pixi.toml` -- neither of the two stored hashes matches either. `pixi run -e local-recipes python -m pyforge.doctor.sources spec-surface` run against the working tree confirms exit 0 with neither spec named in its output. Not this story's to fix: reconciling either spec's `pixi.toml` surface means attributing and dating whatever change actually caused each drift (unknown without git-archaeology per spec, out of a repair pass's scope) and touches a spec this story does not own (`spec-pyforge-core` is in a different BMAD project entirely). Whoever next reconciles `pixi.toml` drift for either spec should also `--write-baseline` this one, and consider whether the substring-match suppression in `chain.py::_drift_findings` (a repo-wide gate, not story-owned) should require the named path to appear in the memlog entry's own dated section rather than anywhere in the file's full text.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-2-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-2-4: `gather_spec_surface`'s file-drift hash reads raw on-disk bytes, not git's blob content, so a `text eol=...`-normalized file reports false drift in any worktree whose checkout applied a different line-ending conversion than the one active when its spec's baseline was stamped
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md`
  summary: `src/platform/docs/make.bat` (`.gitattributes`: `*.bat text eol=crlf`) reported as "changed" against `pyforge-steward/spec-python-agent-platform`'s committed baseline in this bmad-loop worktree even though no content changed since Story 10.1 landed. `chain.py::_sha1` (and the mutation-side `scripts/spec_surface_check.py::sha1`) both hash `path.read_bytes()` -- the working-tree bytes after git's smudge filter -- not `git show HEAD:<path>` (the blob as committed, always LF-normalized for a `text` attribute). The original baseline was apparently stamped in a working tree where the file's on-disk bytes were still LF (matching the blob, likely because the file had just been written/staged and never round-tripped through a fresh checkout's smudge filter); this worktree's own checkout applied the `eol=crlf` smudge, producing CRLF bytes that hash differently. This repair pass's fix re-stamped the baseline against THIS worktree's CRLF bytes, which resolves the immediate gating FAIL but does not fix the underlying mismatch: any other worktree/CI runner/`git archive` export that materializes different on-disk bytes for an `eol=`-attributed file will reproduce the identical false-positive drift, requiring another one-off reconciliation cycle.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this repair pass's review. Verified directly: `git show HEAD:src/platform/docs/make.bat | sha1sum` (LF, `6a946df1...`, matches the original baseline) vs. the live working-tree file (CRLF via `git check-attr eol -- src/platform/docs/make.bat` confirming `eol: crlf`, hashing to `2d4b4a05...`) -- `git diff HEAD` for the path is empty, confirming git itself sees no change; only the raw-byte hash differs. Not this story's to fix: the hashing approach lives in `pyforge.doctor.sources.chain::_sha1` / `scripts/spec_surface_check.py::sha1`, shared infrastructure this story does not own, and any fix (hash via `git show`/`git hash-object` instead of `path.read_bytes()`, or exclude `eol=`-attributed files from content-hash comparison) is a design change to the S-13.7 reconciliation gate itself, not a `python-agent-platform` concern. Whoever next owns `pyforge.doctor.sources.chain` should consider hashing tracked files via git's own blob content (`git show HEAD:<path>` or `git hash-object`) rather than raw disk bytes, so the drift signal is checkout-environment-independent.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-2-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-2-one-factory-sourced-environment.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-3-1: `src/platform/Containerfile`'s pip layer swaps the app's Postgres driver from psycopg 3 to conda's psycopg2, with no ORM-level test exercising the container's actual driver
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: The Containerfile's `--no-deps` pip layer deliberately excludes `psycopg[c]` (psycopg 3, `requirements/production.txt`'s pin) in favor of the `python-agent-platform` conda env's `psycopg2` (psycopg 2) — an explicit, justified Boundaries & Constraints decision (avoiding a shadowed/duplicate driver), but a genuine major-version driver substitution, not merely a duplicate-avoidance. Django's `postgresql` backend fully supports both drivers, so this is not a known defect, but no test anywhere exercises real ORM behavior against the container's actual `psycopg2` driver — the real pytest suite (`platform-ci.yml`'s `test` job) only ever runs against psycopg 3 via `requirements/local.txt`; the container job's own checks (`manage.py check`, a health-check `SELECT 1` probe) never touch the ORM.
  evidence: Raised independently by Blind Hunter during this story's review pass. Verified live: `psycopg[c]` (psycopg 3) and `psycopg2` (psycopg 2) are genuinely different packages with different import names; the Containerfile's exclusion regex correctly keeps `psycopg2` conda-sourced and never pip-installs `psycopg[c]`, confirmed via `pip list` inside the built image. Not this story's to fix: adding real container-path ORM test coverage (or reconsidering whether the two drivers' behavior is provably equivalent for this app's usage) is a non-trivial testing-infrastructure addition, out of this L-effort infra story's own Tasks & Acceptance. Whoever next touches the container's environment layer or adds real database-backed tests should exercise them against the conda-sourced `psycopg2` driver specifically, not assume parity with the pip-tested psycopg 3 path.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-3-10: Platform CI's two path filters are duplicated by hand with nothing enforcing they stay equal, so a one-sided edit silently stops gating either PRs or main.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: Platform CI's two path filters are duplicated by hand with nothing enforcing they stay equal, so a one-sided edit silently stops gating either PRs or main.
  evidence: `.github/workflows/platform-ci.yml` declares the same nine-entry `paths:` list twice — once under `on.pull_request` and once under `on.push` — and its own comment concedes the situation: "duplicated verbatim rather than shared via a YAML anchor: GitHub Actions does not support YAML anchors/aliases in workflow files. Keep them in step by hand." The failure is asymmetric and silent in both directions: a path added only to `pull_request` means the gate runs on the PR and then never re-runs on the merge commit to `main`, so a `push`-only regression (or a merge that combines two independently-green PRs) lands ungated; a path added only to `push` means main is gated on something no PR ever exercised. Nothing reports either state — a diverged pair is still valid YAML and still a passing workflow. This is not hypothetical drift in the abstract: this list was `['src/platform/**']` alone until Story 10.3's second review pass widened it to six more paths, and a third pass added a ninth (`.pixi/config.toml`), so it has changed in three of the four passes this story has had, each time by hand, in two places. The same file's sibling `pixi.toml` carries a comment-maintained pin-site enumeration whose headline total has now been wrong three consecutive times, which is the empirical case for not trusting hand-kept equality here either. Deferred rather than patched because the remedy is an architecture choice, not a mechanic: a lint step asserting the two lists match needs a home (this workflow's own `test` job only runs when the filter already matched, so it cannot police the filter that gates it), and the same unenforced-duplication shape exists in other workflows in this repo, so a one-file fix would leave the class open. A repo-wide workflow-lint detector is the durable form, and it is adjacent to the cross-site pixi-version detector `DW-FU-10-3-8` already asks for.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-10` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

  verified: 2026-09-07 — resolved — CI/hygiene sweep (worktree `hygiene-steward`, branch `chore/ci-hygiene-sweep-2026-09-07-steward`) added `src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py`, a repo-wide (not `platform-ci.yml`-only, per this entry's own "a one-file fix would leave the class open" note) parser: scans every `.github/workflows/*.yml`, finds every workflow declaring BOTH `on.pull_request.paths` and `on.push.paths` (7 today, `platform-ci.yml` among them), and asserts the two lists are identical. Proved it actually catches drift, not merely that it passes: temporarily deleted one entry from `platform-ci.yml`'s `push.paths` list, confirmed the new test failed with a clear mismatch report naming both lists, then restored the file byte-identical (`git diff` empty) and reconfirmed green. `pyforge-steward-test` full suite: 1196 passed (plus one pre-existing, unrelated red — see DW-9-4-3's verified line). ledger status mapped to resolved.

### DW-10-3-2: `src/platform/Containerfile`'s 8 manually-added transitive pip packages have no automated drift guard against future `requirements/production.txt` changes
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: `django-timezone-field`, `python-crontab`, `cron-descriptor`, `django-appconf`, `rjsmin`, `text-unidecode`, `fido2`, `qrcode` were hand-added to the Containerfile's `pip install --no-deps` layer after a one-time `pip install --dry-run --report=-` closure diff against `requirements/production.txt`. `--no-deps` never resolves transitive dependencies automatically, so nothing re-checks this closure — a future change to `requirements/production.txt` (a new Django extra, a version bump that adds a new required transitive dependency) can silently reopen the exact class of `ModuleNotFoundError` this story spent most of its implementation investigation chasing, recoverable only by someone re-running the same manual closure-diff process by hand.
  evidence: Raised independently by Blind Hunter during this story's review pass. Verified the list is complete for the CURRENT `requirements/production.txt` (a real `docker build` + `manage.py check` + a real home-page render all succeed with exactly these 8 additions, no more, no fewer — see this spec's own Verification section). Not this story's to fix: automating the closure-diff as a CI check or build-time assertion is a real feature addition (new tooling, not a mechanical patch), and matches Story 7.3's own precedent for an identically-shaped finding (its hardcoded three-root secrets-scan list), deferred there for the same forward-looking-maintenance reasoning. Whoever next touches `requirements/production.txt` or this Containerfile's pip layer should re-run the closure diff (`pip install --dry-run --ignore-installed --report=- -r requirements/production.txt` inside the built image, diffed against what the conda env + pip layer already provide) rather than assuming the 8-package list stays complete.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-3-3: `production.py`'s hardcoded `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` silently break login and every CSRF-protected form on the plain-HTTP local compose stack
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: `config/settings/production.py` hardcodes `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True` with no env override, while this story's `src/platform/compose/compose.yml` sets `DJANGO_SECURE_SSL_REDIRECT=False` (documented inline as necessary because the local stack serves plain HTTP with no TLS terminator) — a browser drops `Secure`-flagged cookies over plain HTTP, so any session-based flow (login, the Django admin, any CSRF-protected POST) silently fails against a freshly-`docker compose up`'d stack even though `/ht/`, `/api/health`, and the static home page all return 200.
  evidence: Raised by Edge Case Hunter during this repair pass's review. Confirmed by reading `config/settings/production.py:39-45` directly: `SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)` is env-overridable (and is the exact variable this story's compose file overrides), but the two sibling cookie-security settings one/five lines below it are plain `True` literals with no `env.bool(...)` wrapper at all — the same "no TLS locally" boundary was handled for one setting and not the other two. Not this story's to fix: `production.py` predates this story (Story 10.1's own render) and is outside spec-10-3's Code Map; this story's own Acceptance Criteria for the compose stack name only a 200 health response, not a working login/CSRF flow, so nothing in this story's frozen intent-contract required exercising that path. Whoever next touches `config/settings/production.py` (or adds real browser/form-level tests against the compose stack) should wrap `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` in the same `env.bool(..., default=True)` pattern already used for `SECURE_SSL_REDIRECT` immediately above them, and set both `False` in `compose.yml` alongside `DJANGO_SECURE_SSL_REDIRECT`.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-3-4: Nothing tests the platform image's actual runtime stack — every automated test runs a different set of package versions than the image ships.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: Nothing tests the platform image's actual runtime stack — every automated test runs a different set of package versions than the image ships.
  evidence: `platform-ci.yml`'s `test` job (ruff, mypy, the full pytest suite) installs `requirements/local.txt`, i.e. the pip universe: Django 5.1.11, django-health-check 3.24.0, celery 5.5.3, uvicorn 0.35.0, gunicorn 23.0.0, pillow 11.3.0, psycopg 3. The image resolves its interpreter from the `python-agent-platform` conda env and ships Django 5.2.15, django-health-check 4.5.0, celery 5.6.3, uvicorn 0.52.3, gunicorn 26.0.0, pillow 12.3.0, psycopg2 — verified live with `pip list` inside the built image. The two sets are mutually exclusive by construction, not by accident: `requirements/base.txt`'s own comment records that `django-health-check>=4.0 requires Django>=5.2, which this file's own django==5.1.11 pin does not satisfy`. So every Django extra the app depends on (django-allauth[mfa] 65.10.0, django-redis 6.0.0, django-celery-beat 2.8.1, django-compressor 4.5.1, django-crispy-forms, django-model-utils, django-anymail) is pytest-verified against Django 5.1 only and then shipped on 5.2, and the image's own automated coverage is four smoke requests plus `manage.py check`. This is real, not theoretical: this same review pass found `uvicorn-worker==0.3.0` calling `uvicorn.Config.setup_event_loop()`, removed in uvicorn 0.36.0 — a hard gunicorn worker-boot failure that no test in the repo could have caught, found only by booting the image by hand. Deferred rather than fixed because closing it means a real testing-infrastructure decision (run the pytest suite a second time inside the container against the conda env, or converge the two universes onto one Django pin), not a mechanical patch, and it spans Story 10.1's requirements files and Story 10.2's pixi feature as much as this story's Containerfile. Related to but distinct from DW-FU-10-3, which covers only the psycopg driver substitution.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-3-5: The platform image ships its own source tree writable by the runtime user, and whether it does depends on the umask of the machine that built it.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: The platform image ships its own source tree writable by the runtime user, and whether it does depends on the umask of the machine that built it.
  evidence: `COPY src/platform/ /app/` preserves the build context's file modes verbatim. On a host with a 002 umask (the default on this development machine) the checkout is mode 775/664, so every file the runtime stage ships is group-writable, and the image's `USER 1001:0` runs in GID 0 — meaning the application process can rewrite its own code. Confirmed live under an arbitrary UID: `docker run --user 24680:0 ... bash -c 'echo x >> /app/manage.py'` succeeds. Reproduced on the pre-review image too, so this predates this review pass and is a property of the COPY pattern rather than of any fix applied here; the same pattern is used by the repo-root Containerfile (Story 7.1), so a fix should probably cover both. Two consequences: the defense-in-depth one (a compromised request handler can persist changes into the running container's own code, which a read-only source tree would prevent), and a reproducibility one (the shipped modes differ between a 002-umask developer machine and an 022-umask CI runner, so two builds of the same commit are not byte-identical). Not patched in this pass because both candidate fixes are decisions rather than mechanics: `COPY --chmod=` is a BuildKit/buildah extension and this story's own Boundaries & Constraints deliberately cap the build at exactly one such extension (`--mount=type=secret`), while a blanket `RUN chmod -R g-w /app` has to carve out `staticfiles`, `platformapp/media`, and `$HOME` itself (gunicorn 26 creates `$HOME/.gunicorn/gunicorn.ctl` at boot) and would silently break the arbitrary-UID contract if it got the carve-outs wrong.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-5` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-3-6: User-uploaded media under `src/platform/` is not gitignored, because the pattern meant to cover it names a directory that does not exist.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: User-uploaded media under `src/platform/` is not gitignored, because the pattern meant to cover it names a directory that does not exist.
  evidence: `src/platform/.gitignore:272` carries `platform/media/`, a cookiecutter-django default that assumes the Django app package is named `platform`. Story 10.1 rendered this project with the package named `platformapp`, so `MEDIA_ROOT` is `src/platform/platformapp/media/` and the pattern matches nothing. Verified directly: `git check-ignore -v src/platform/platformapp/media/foo.png` exits 1 (not ignored), while the sibling `git check-ignore -v src/platform/staticfiles/x.css` exits 0 via `.gitignore:54`. Consequence: the first developer who exercises a real upload locally and runs `git add -A` commits user content into the repository, and nothing warns them — the file that is supposed to prevent it looks like it does. Pre-existing in Story 10.1's own tree, surfaced only because Story 10.3's follow-up review checked a `.dockerignore` comment that asserted both output directories were already gitignored (that comment has been corrected; the image side is fully covered by the two `.dockerignore` entries Story 10.3 added, so this is a repo-hygiene gap, not an image defect). Not fixed here: `src/platform/.gitignore` is Story 10.1's surface and sits inside two governed spec surfaces, so a one-line fix drags a memlog entry and a baseline stamp for each behind it — cheap work, but work that belongs to whoever owns that tree rather than to a container story's review pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-6` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 2/4 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md, src/platform/platformapp/media/); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-10-3-7: Platform CI's path filter now bills the repo's highest-traffic source trees for a two-engine container matrix plus an unrelated pip test job.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: Platform CI's path filter now bills the repo's highest-traffic source trees for a two-engine container matrix plus an unrelated pip test job.
  evidence: Story 10.3's review pass widened `.github/workflows/platform-ci.yml`'s `paths:` from `src/platform/**` to also include `pixi.toml`, `pixi.lock`, `.dockerignore`, `scripts/container-gates`, `src/shared/packages/pyforge-steward/**`, and `src/shared/packages/pyforge-core/**`. That widening is correct on its own terms — every one of those is a real input to the image build (the builder stage materializes a `pyforge-steward` env for the secrets-scan gate), and the narrow filter demonstrably missed a `requires-pixi` bump that broke the build. The cost was not weighed at the same time. `paths:` is WORKFLOW-scoped, not job-scoped, so any hit runs BOTH jobs: the `container` job's `[docker, podman]` matrix (two cold builds, each solving and downloading a 395-package env plus a second build-time env, with `timeout-minutes: 45`) AND the pip-based `test` job, which shares nothing with the image at all. `src/shared/packages/pyforge-steward/**` is where most fleet work in this repo lands, so a one-line docstring edit there now pays for two container builds. Deferred rather than decided here because both directions are defensible and neither is mechanical: narrowing the filter reopens the miss it was added to close, while keeping it means splitting this workflow per job (or gating the `container` job on a `paths-filter` action inside the job) — a workflow-architecture choice, not a patch. The contradictory comment claiming this workflow "never triggers on a factory-only change" was corrected in the same pass, so the current state is at least accurately described.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-7` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 2/6 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md, src/platform/**, src/shared/packages/pyforge-core/**…); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

  verified: 2026-09-07 — still-open — CI/hygiene sweep (worktree `hygiene-steward`, branch `chore/ci-hygiene-sweep-2026-09-07-steward`) re-read this entry against its sibling DW-10-3-10 (grouped with it on this pass's shortlist) and confirmed they are DIFFERENT findings sharing one file: DW-10-3-10 is the hand-duplicated `pull_request`/`push` `paths:` list equality gap (closed this pass — see its own verified line, `tests/meta/test_workflow_path_filters_match.py`); THIS entry is the workflow-vs-job path-filter SCOPING cost (any matched path runs both the `container` matrix and the unrelated `test` job) and its own text names the fix as "a workflow-architecture choice, not a patch" (split the workflow per job, or gate `container` behind an in-job `paths-filter` action) — not something a mechanical equality test addresses or that this pass's narrow hygiene-fix scope covers. Left open, deliberately not closed by the DW-10-3-10 fix above; ledger status stays still-open.

### DW-10-3-8: The repo-root Containerfile pins a pixi below the floor its own manifest declares, so that image's builder stage cannot install at all.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: The repo-root Containerfile pins a pixi below the floor its own manifest declares, so that image's builder stage cannot install at all.
  evidence: `Containerfile:58` (Story 7.1, the Guild's unified image, governed by `pyforge-steward/spec-unified-container` CAP-1) is `FROM ghcr.io/prefix-dev/pixi:0.76.1`, while `pixi.toml`'s `requires-pixi` is `>=0.76.2`. Pixi enforces that floor, so the builder stage's `pixi install` aborts with `this project requires pixi '>=0.76.2', but you have pixi 0.76.1`. Not inferred — Story 10.3 hit this exact error live when its own Containerfile first reused Story 7.1's tag, which is why `src/platform/Containerfile` is on 0.76.2. Live inventory taken during the follow-up review: thirteen sites carry a pixi version and TWELVE are at 0.76.2 (`requires-pixi`, the `$schema` URL, three `feature.*` floors, `environment.yaml`, `dashboard.yml`, `kedro-viz-publish.yml`, three pins in `herald-live-demo.yml`, `sync-pypi-mappings/action.yml`, `staged-recipes-linter.yml`, and `src/platform/Containerfile`); the root Containerfile is the only holdout. This is NOT covered by DW-7-1-2, which is `status: resolved` (2026-08-09, when all sites were aligned at 0.76.1) — everything except the root Containerfile has since moved up and left it behind, which is that entry's own residual ("the equality is still COMMENT-MAINTAINED — nothing enforces it") coming true a second time. Two pieces of work, neither this story's: raise the tag to 0.76.2 (one line, but it belongs to the spec that owns that image, and the fix should be verified with a real build), and build the cross-site pixi-version detector DW-7-1-2 named as the durable remedy. Note also that `herald-live-demo.yml`'s three pins were absent from the enumeration entirely until this pass; a hand-maintained list that has now been wrong about both its count and its contents is the argument for the detector.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-8` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

  verified: 2026-09-07 — resolved — CI/hygiene sweep (worktree `hygiene-steward`, branch `chore/ci-hygiene-sweep-2026-09-07-steward`) found this ALREADY FIXED by intervening fleet work, not by this pass: `Containerfile:58` is `FROM ghcr.io/prefix-dev/pixi:0.79.0` and `pixi.toml`'s `requires-pixi` is `>=0.79.0` — matching. The durable remedy this entry itself asked for now exists too: `scripts/pixi_version_registry.py` (`pixi run -e local-recipes pixi-version-check`) reports "17 site(s) checked ... clean — every pin site matches the floor" (up from the 13 this entry enumerated — 4 more sites registered since, per `pixi.toml`'s own `requires-pixi` comment). Re-verified with a REAL build, not just a tag comparison, per this entry's own "the fix should be verified with a real build" ask: `docker build -f Containerfile --target builder -t pyforge-guild-builder-verify .` completed with exit 0, log line "The pyforge-container environment has been installed." — `pixi install -e pyforge-container` succeeded, i.e. the exact `this project requires pixi '>=X', but you have pixi <X` failure this entry describes did not reproduce. Verification image removed after the check (`docker rmi pyforge-guild-builder-verify`). ledger status mapped to resolved.

### DW-10-3-9: Two marshal specs carry stale pixi.toml baselines that the spec-surface gate cannot report, because a moved memlog downgrades their drift to informational.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: Two marshal specs carry stale pixi.toml baselines that the spec-surface gate cannot report, because a moved memlog downgrades their drift to informational.
  evidence: `scripts/.spec-surface-baseline.json` records `pixi.toml` for `pyforge-marshal/spec-pyforge-core` at sha1 `449b3179` and for `pyforge-marshal/spec-bmad-loop-baseline-drift` at `0f9455fd`. Neither matches the live file, and — the part that dates it — neither matches `pixi.toml` as of Story 10.3's own baseline commit `64e717d135` (`0ae029cc`), so both were already unreconciled before this story touched anything. `python scripts/spec_surface_reconcile.py` nevertheless exits 0 with `OK: every tracked file governed or allowlisted; no drift.`: once a spec's `.memlog.md` hash has moved for any reason, its findings degrade from gating `[drift]` to informational `[drift-presumed]`, and the residual check for whether a changed path is NAMED in the memlog is a substring test against the whole file, which a long historical memlog mentioning `pixi.toml` satisfies incidentally. This is the same silence that let Story 10.3 change `src/platform/**` without reconciling its own owning spec — caught only because a reviewer compared baseline digests by hand. Deferred rather than fixed: the mechanical part (name the changes, re-stamp) belongs to whoever owns those marshal specs and requires knowing what actually moved `pixi.toml` between those digests, and the structural part (a memlog that moved for an unrelated reason should not blanket-downgrade every governed path, and "named" should mean named in the current entry rather than anywhere in the file) is a change to the reconciler's own semantics, owned by `pyforge-marshal/spec-surface-drift-reconciliation`.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-9` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/3 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md, src/platform/**); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-8-4-1: `sync reconcile --schedule`'s per-candidate failure detail is computed but never reaches the operator through the CLI
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-4-the-schedule-trigger-enumerates-real-candidates.md`
  summary: `reconcile_schedule_batch` builds a rich `details["candidates"]` list (each entry carrying `github_item_id`, `updated_at`, `ok`, `summary`), but `cli.py`'s `main()` prints only `result.summary` — a single aggregate string like "3 candidates, 2 ok, 1 failed" — and `sync reconcile` defines no `--json` flag, unlike `provision`/`list`/`show`. When a `--schedule` batch reports a partial failure, an operator running the CLI has no way to learn which candidate failed or why; the diagnostic data this story's own frozen contract requires (`details["candidates"]`) is computed and then discarded at the CLI boundary.
  evidence: Raised by Blind Hunter during this story's review pass 2, confirmed by reading `cli.py:361` (`print(result.summary, ...)`, the sole output line for every duty, not just `sync`) and `_add_sync_subparsers` (no `--json` argument anywhere on the `reconcile` verb, unlike `provision --list-modules [--json]`/`provision --module <name> [--json]`). Pre-existing whole-CLI convention — every duty's `main()` output is this same one-line `result.summary`, not caused by this story's own logic — but this story's batch mode is the first `sync` invocation shape where the discarded detail is genuinely load-bearing (a single-pair `--github-item` failure's cause IS the one-line summary; a `--schedule` batch's per-candidate cause is not). Not a trivial patch: adding a `--json` flag to `sync reconcile` is a real CLI-surface/API decision (naming, help text, interaction with `--dry-run`), not a mechanical fix. Whoever next needs `--schedule` batch failures to be operator-diagnosable from the CLI (rather than only from a direct Python call to `reconcile_schedule_batch`) should settle this then.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-4-the-schedule-trigger-enumerates-real-candidates.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-8-4-2: `_LIST_PROJECT_ITEMS_QUERY`'s `fieldValues(first: 50)` cap now runs board-wide, automatically, on every scheduled tick
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-4-the-schedule-trigger-enumerates-real-candidates.md`
  summary: The new bulk-listing query's `fieldValues(first: 50)` cap is copy-pasted unchanged from the pre-existing `_GET_PROJECT_ITEM_QUERY` (already a known, already-deferred pagination gap for the single-item path — see this ledger's Story 8.1 entry, `DW-FU` prefix predates the current id-minting convention), but this story is the first to exercise it board-wide and automatically rather than only for a manually-targeted single item: a board with more than 50 custom fields could have a genuinely-linked candidate's link field silently fall outside the first page and be excluded from candidacy entirely on every `trigger=schedule` tick.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter during this story's review pass 2 (corroborated), confirmed by reading `_LIST_PROJECT_ITEMS_QUERY` in `sync.py` — the same `fieldValues(first: 50)` block as `_GET_PROJECT_ITEM_QUERY`, no `pageInfo`/`after` inner-cursor handling for the per-node field connection. This is materially different in consequence from the Story 8.1 entry it shares a root cause with: that entry describes a single manually-invoked `--github-item` call silently misreading one targeted item's field; this story's automatic board-wide enumeration means the SAME truncation, on the SAME kind of item, silently and permanently drops that item from every future scheduled batch with no operator awareness — exactly the false-negative failure mode this story's own Design Notes call "strictly worse" than a false positive (AD-5). Not a trivial patch: needs real per-item `fieldValues` pagination inside a bulk query already paginating at the outer `items` level (a nested-pagination GraphQL shape with no existing precedent in this module), not a mechanical fix. Whoever next revisits either query's field-parsing, or onboards a board with 50+ custom fields, should settle both entries together.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-4-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-4-the-schedule-trigger-enumerates-real-candidates.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-8-5-1: the loop-home worktree's local `epics.md` and tracked `sprint-status-ledger.yaml` are 60 commits stale, still carrying pre-correct-course Epic 8 story numbers
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-5-fail-loud-fail-alone.md`
  summary: This worktree's local copy of `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` and the checked-in `sprint-status-ledger.yaml` still show the pre-`bmad-correct-course` Epic 8 numbering (`8.4` = "Fail loud, fail alone", `8.5` = "Explicit status-vocabulary translation", no producer story for `trigger=schedule` batching) even though `main` landed the 2026-08-13 correct-course renumbering 60 commits ago (`8.4` = "The schedule trigger enumerates real candidates", `8.5` = "Fail loud, fail alone", `8.6` = "Explicit status-vocabulary translation" — `sprint-change-proposal-2026-08-13.md`). This story's own diff is correctly labeled against the CURRENT (post-correct-course) numbering — confirmed against the Tier-3 `implementation-artifacts/sprint-status.yaml` (which backlinks straight to the main checkout and already shows `8-4-the-schedule-trigger-...: done` / `8-5-fail-loud-fail-alone: backlog`), the correct-course proposal document itself, and the git history of the already-landed `8-4-the-schedule-trigger-enumerates-real-candidates` story — but the two stale worktree-local files remain a live trap for anyone (human or agent) who trusts them instead.
  evidence: Discovered independently during this story's own step-01 planning (this worktree's `epics.md` diffed 35 lines against `main`'s copy; `git merge-base --is-ancestor` confirmed the correct-course commit `073dfe0fd2` is not an ancestor of this loop-home branch) and then reproduced live during this story's own review pass: Blind Hunter, working from a fresh context with no access to that prior investigation, read this worktree's stale `epics.md`/`sprint-status-ledger.yaml`, concluded this diff was mislabeled as "Story 8.5" when it should be "Story 8.4", and rated it the review's highest-severity finding — a false positive triggered by exactly the drift this entry describes. Root cause is mechanical, not this story's to fix: `loop/pyforge-steward`'s squash-merge-per-story pattern only carries a landed branch's own file diffs, so a correct-course session that edited `epics.md`/the ledger directly on `main` (rather than through a dispatched loop story) never reaches the loop branch's tracked copies. Whoever next syncs this loop-home branch against `main` (or runs `pixi run -e local-recipes sprint-ledger-sync` / `bmad-drift-check`) should reconcile both files; until then, any reviewer or planning session working inside this loop-home's worktrees should prefer the Tier-3 `sprint-status.yaml` backlink and `sprint-change-proposal-2026-08-13.md` over the worktree-local `epics.md`/`sprint-status-ledger.yaml` for Epic 8 story identity.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-5` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-5-fail-loud-fail-alone.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-8-5-2: a GitHub Projects V2 board item deliberately never meant to link to Jira fails loudly on every scheduled tick forever, with no way to mark it out-of-scope
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-5-fail-loud-fail-alone.md`
  summary: CAP-4 ("fail loud, fail alone on broken links") and this story's landed code both treat every unlinked board item as a candidate that must fail by name on every `--schedule` run, with no distinction between "not yet linked" (a real gap worth surfacing) and "never going to be linked" (a card that was always meant to stay GitHub-only). A real board mixing synced and GitHub-only work items would see the GitHub-only ones fail, by name, on every single scheduled tick, forever, with no way to silence them short of removing them from the board or giving them a link they don't need.
  evidence: Raised by Blind Hunter during this story's review pass as an operability concern, and confirmed against CAP-4's own frozen intent text (`spec-jira-github-projects-sync/SPEC.md`: "An item missing its cross-system link fails loudly in a log -- never silently skipped") and this story's own frozen `<intent-contract>`, neither of which carries any opt-out/allowlist concept. Not this story's to fix: the frozen AC and the ratified architecture (AD-6) are unambiguous that every unlinked item must fail loudly, and this story's own "Never" boundary forbids inventing a new filtering mechanism inside `list_linked_github_items`/`reconcile_schedule_batch`. An opt-out (e.g. a per-item "excluded from sync" marker, or a config-level allowlist of fields/labels that mark an item as GitHub-only) is a real product/architecture decision, not a mechanical patch, and belongs with whoever next operates a real mixed board against `trigger=schedule` and hits the noise in practice.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-5-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-5-fail-loud-fail-alone.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-8-6-1: `load_config`'s `document.get(...) or {}` idiom silently coerces a falsy-but-malformed `status_mapping`/`field_overrides`/`user_mapping` value to an empty mapping
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md`
  summary: `status_mapping = document.get("status_mapping") or {}` (and the identical pre-existing idiom for `field_overrides`/`user_mapping`) coerces any falsy value -- `status_mapping: false`, `status_mapping: 0`, `status_mapping: ""` -- to `{}` before the subsequent `isinstance(status_mapping, dict)` check ever runs, so a config author's typo silently loads as "no mapping configured" instead of raising a named `SyncConfigError`. For `status_mapping` specifically this defeats part of the very guarantee this story exists to build (AD-6: an unmapped status is a hard, named, logged failure) -- an operator who typos `status_mapping: false` gets silent full-passthrough-becomes-always-unmapped behavior with no config-time signal that their file is wrong.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter (corroborated) during this story's review pass, confirmed by reading `load_config` in `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- all three config-dict loads (`field_overrides`, `user_mapping`, `status_mapping`) use the identical `document.get(name) or {}` pattern with no explicit `is None` check. Not this story's to fix alone: the pattern is copy-pasted verbatim from the pre-existing `field_overrides`/`user_mapping` code this story's own spec instructed it to mirror ("load and validate it in `load_config` exactly like `user_mapping`"), so fixing only `status_mapping` would be an inconsistent, asymmetric patch leaving the other two fields with the same gap. Whoever next touches `load_config` should replace `or {}` with an explicit `is None` check across all three fields in one pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-6` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-8-6-2: no operator-facing documentation page covers `status_mapping`/`user_mapping`/`field_overrides` outside the example YAML's own comments
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md`
  summary: `pyforge-steward/README.md` has zero mentions of `status_mapping`, `user_mapping`, or `field_overrides` -- the entire config surface for these three `SyncConfig` fields is documented only as inline comments in `.steward/sync-config.example.yaml`, with no single doc page an operator can read end-to-end (module docstring, README, or a guide) to learn what the sync duty's config surface supports.
  evidence: Raised by Blind Hunter during this story's review pass, confirmed by grepping `pyforge-steward/README.md` for all three field names (zero hits). Pre-existing gap for `field_overrides`/`user_mapping` since Story 8.1; this story adds a third field to the same undocumented surface rather than introducing the gap. Not this story's to fix alone: a proper fix is a dedicated config-reference doc section covering all three fields together, not a one-field patch that leaves the other two still undocumented. Whoever next writes or expands `pyforge-steward/README.md`'s config section should cover all three.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-6-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-8-6-3: `sprint-change-proposal-2026-08-13.md`'s root-cause rationale for the Jira↔GitHub write direction is backwards
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md`
  summary: The correct-course proposal's §2 explanation of which sync direction already hard-fails and which was the raw passthrough is reversed relative to both the original `epics.md` audit note and the actual shipped code.
  evidence: `sprint-change-proposal-2026-08-13.md` §2 states "the Jira→GitHub direction already hard-fails on an unmapped status ... but the GitHub→Jira direction is still 8.1's raw 1:1 passthrough ... exactly what 8.5 exists to replace." In reality `push_to_github` (writing a Jira status into GitHub) was the unvalidated passthrough this story fixed -- confirmed against pre-story `sync.py`, which called `update_project_item_field` with the raw `target_value` and zero validation -- while `push_to_jira` (writing a GitHub status into Jira, via `transition_jira_issue`) already hard-fails when no transition matches, unchanged by this story. That is the reverse of the proposal's claim; the original `epics.md` audit note the proposal was resolving states it correctly ("its GitHub direction is today a raw 1:1 pass-through"). No functional impact -- this story's own frozen intent-contract and the shipped code both correctly target `push_to_github` -- this is a prose-only error in a decision record inherited verbatim from `main`'s `073dfe0fd2` correct-course commit (authored outside this story's own scope), which could mislead a future reader auditing the RESPEC rationale. Not this story's to fix: editing another station's/process's already-ratified correct-course record is out of this story's code-focused intent-contract.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-6-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-8-6-4: `status_mapping`'s `or {}` idiom independently reconfirmed to swallow an explicit falsy top-level value (`false`/`0`/`""`) before the mapping-type check runs
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md`
  summary: `status_mapping = document.get("status_mapping") or {}` (`sync.py:196`) coerces a falsy but present top-level value straight to `{}` before `isinstance(status_mapping, dict)` ever inspects it, so `status_mapping: false` loads silently as "no mapping configured" instead of raising `SyncConfigError`.
  evidence: This is the same root cause already recorded as `DW-FU-8-6` (shared `or {}` idiom across `field_overrides`/`user_mapping`/`status_mapping`, including this exact falsy-scalar example) -- both Blind Hunter and Edge Case Hunter independently re-surfaced it during this story's fresh review pass on the restored implementation, corroborating that assessment. Recorded as its own entry per this workflow's defer procedure (fresh entries are always minted, not merged into prior ones). No new remediation beyond what `DW-FU-8-6` already describes: whoever next touches `load_config` should replace `or {}` with an explicit `is None` check across all three fields in one pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-8-6-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-2-1: `dashboard_role` is a hardcoded scope-key string duplicated independently in the writer (`middleware.py`) and the reader (`views.py`), with no shared constant and no test that drives a real request through both together
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-2-an-unauthorized-page-is-absent-not-hidden.md`
  summary: `middleware.py`'s `DashboardIdentityMiddleware.__call__` writes `scope["dashboard_role"] = ...` and `views.py`'s `navigation_view` independently reads `getattr(request, "scope", {}).get("dashboard_role")` — the string literal is typed out separately in both places with nothing tying them together, and every existing test for `build_navigation_view` hand-constructs the scope dict directly rather than running it through the real middleware.
  evidence: Raised by Blind Hunter in this story's review pass. Not patched here: `middleware.py` is Story 9.1's already-shipped file and is outside this story's frozen Code Map (`navigation.py`/`filtering.py`/`views.py`/tests only), so introducing a shared constant module or an integration test spanning both stories' files is a cross-story change, not a same-pass fix. The failure mode is fail-closed (a typo or rename in either module silently degrades to "no pages visible," never to over-exposure), so this is a maintainability/observability gap, not a security hole -- but it is a real one: nothing in the current suite would catch the drift.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-2-an-unauthorized-page-is-absent-not-hidden.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-2-2: `build_navigation_view`'s duplicate-path guard only rejects byte-identical strings, so `/reports` and `/reports/` (or differently-cased paths) can still collide once wired into a real router
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-2-an-unauthorized-page-is-absent-not-hidden.md`
  summary: The wiring-time uniqueness check in `views.py` (`if page.path in seen_paths`) compares declared `Page.path` values as exact strings, so two pages differing only by a trailing slash or letter case pass as "distinct" even though many adopter routers would treat them as the same route, reopening the ambiguous-duplicate-entry hazard the guard exists to prevent, just one layer up.
  evidence: Raised by Blind Hunter in this story's review pass. Not patched here: fixing this requires choosing a path-canonicalization policy (trailing-slash handling, case sensitivity) that nothing in the spec's Boundaries & Constraints or I/O matrix specifies, and guessing one risks introducing behavior inconsistent with whatever router an adopter actually wires this into (AD-1 explicitly leaves routing to the adopter). Belongs with a future story or an explicit spec decision, not an unprompted guess in this pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-2-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-2-an-unauthorized-page-is-absent-not-hidden.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-2-3: A whitespace-padded role reaching `filter_by_role` and `build_navigation` from the same request is refused loudly by one and silently emptied by the other
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-2-an-unauthorized-page-is-absent-not-hidden.md`
  summary: Story 9.1's `DashboardIdentityMiddleware` stores `scope["dashboard_role"]` verbatim whenever `role.strip()` is truthy (only blank/whitespace-only values are rejected), so a role like `" east"` from a misbehaving proxy reaches both of this story's new consumers unstripped. `filter_by_role` then raises `ValueError` for it (per this story's own "unrecognized role is a configuration defect" rule, since `" east"` is not in `declaration.roles`), while `build_navigation` silently returns an empty tuple for the same value (`Page.roles` has no closed vocabulary to validate an "unrecognized" role against, by design — see the Design Notes' "two independent declared vocabularies"). The same artifact on the same request therefore 500s one dashboard surface and quietly shows nothing on the other.
  evidence: Raised by Blind Hunter in this story's review pass; confirmed by reading `middleware.py`'s `role = roles[0] if roles else ""` / `scope["dashboard_role"] = role if role.strip() else None` directly. Not patched here: the root cause is Story 9.1's already-reviewed, deliberate decision not to normalize role values, which that story's own review pass 3 explicitly deferred to Story 9.3's audit-row work ("trimming/normalizing a real identity is the identity-model decision deferred to Story 9.3"), and this story's spec explicitly inherits that deferral rather than re-deciding it. Each of `filter_by_role`'s raise and `build_navigation`'s silent-empty is independently correct against its own module's stated contract; only the cross-module asymmetry is new, and reconciling it means picking a normalization policy that belongs with Story 9.3, not an unprompted guess here.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-2-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-2-an-unauthorized-page-is-absent-not-hidden.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-1: sld:AD-14's PostgreSQL contention proof is not delivered for the new audit store — every test runs against in-memory SQLite only
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: sld:AD-14 states "Contention behaviour is proven against PostgreSQL in CI, never inferred from a green SQLite run," and explicitly names the audit store and sld:AD-12's per-message hot-path write as the reason this binds here. This story's entire test suite (`test_dashboard_audit.py`) runs against a single in-process SQLite `:memory:` database with no concurrent-write test — unlike `test_dashboard_cache.py`'s threaded race test for the analogous cache invariant, nothing here exercises concurrent `record_audit_entry` calls at all, against SQLite or otherwise.
  evidence: Raised by Blind Hunter in this story's review pass. Not patched: the spec's own Boundaries explicitly ruled this out of scope ("Prove sld:AD-14's PostgreSQL contention claim — no PostgreSQL CI service exists in this repo's pixi environments yet... the contention proof is a new deferred-work entry, not attempted here"), because no `psycopg2`/PostgreSQL service is provisioned in the `pyforge-steward` pixi feature or anywhere in this repo's CI today — standing one up is an environment/CI-topology decision beyond one story's Code Map, the same class of decision Story 9.1/9.5 repeatedly deferred for the cache backend. Whoever adds PostgreSQL CI coverage (most naturally Story 9.5's deployment-perimeter surface, which already owns the estate's other backend/infra decisions on this ledger, or Story 9.6's proof suite) should add a concurrent-write contention test for `record_audit_entry` at the same time.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-10: every AUDIT_READ row records the same constant "of what", so CAP-4's read-side provenance is unrecoverable from the trail
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `query_audit_entries` hardcodes `target="audit_trail"` on the entry it writes for its own invocation and persists nothing about the `**filters` that scoped the read, so two materially different reads of the trail — a targeted lookup of one high-value export row and an unfiltered sweep of a whole action class — produce byte-identical audit rows. CAP-4 requires "who saw how many rows of what"; on the read path the "of what" is a constant, so the trail cannot answer which rows a reader actually saw.
  evidence: Raised by Blind Hunter in this story's review pass 4 and reproduced by execution: `query_audit_entries(reader_actor="mallory", reader_role=None, actor="alice")` against a 500,000-row EXPORT entry and `query_audit_entries(reader_actor="mallory", reader_role=None, action=LOAD)` both wrote `actor=mallory role=None action=audit_read target='audit_trail' row_count=1`, so a reader walking the trail one primary key at a time leaves N indistinguishable one-row reads behind. Distinct from `DW-FU-9-3-2` (the reader's role is recorded but not enforced) and `DW-FU-9-3-4` (the result set is unbounded); this is about what the recorded act says it was. Not patched, because the fix is a design choice this story's spec does not make: `**filters` is an open surface accepting arbitrary keyword lookups (deliberately, per pass 1's `reject` of a field allowlist), so serializing it into the 255-character `target` column risks both truncation and writing caller-supplied values — potentially identifying ones — into the very table being audited, and the alternatives (a separate JSON column, a normalized read-scope table, an allowlisted filter vocabulary) all change the shipped schema. It should be settled together with `DW-FU-9-3-2`, since deciding what a read is scoped to is the same question as deciding what a reader is allowed to see.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-10` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-2: `query_audit_entries` does not filter its results by the reader's role — AD-7's "the trail is itself role-isolated data" is only half-implemented
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: AD-7 reads "the trail is itself role-isolated data — any surface that displays it passes through the same filtering and audit path as any other dataset, so reading the audit trail is a recorded act." This story implements the second half only (every read writes an `AUDIT_READ` entry) — `query_audit_entries` forwards arbitrary caller-supplied `**filters` straight into `AuditEntry.objects.filter()` with no connection to `AccessDeclaration`/CAP-2's row-isolation pattern and no restriction on which rows a given `reader_role` may see.
  evidence: Raised by Blind Hunter in this story's review pass. Not patched: the row-isolation half depends on `filter_by_role`/`AccessDeclaration`-style filtering (Story 9.2's `filtering.py`), which does not exist in this worktree (Story 9.2 is in-flight in a sibling worktree of this same bmad-loop run, and this story's own spec explicitly rules out wiring into files that don't exist here). Nothing in Epic 9's current story list (9.1-9.7 per `epics.md`) obviously owns retrofitting role-based filtering onto the audit-read surface itself, so this may be a permanently under-specified clause of AD-7 rather than a deferral with an obvious future owner — flagging it here rather than silently dropping it is the point of this entry.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-3: `purge_expired_entries` destroys audit rows without recording that anyone destroyed them, while `query_audit_entries` records every read
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: AD-7's rationale for auditing reads of the trail — that the record of who saw what is the one dataset whose own access is otherwise ungoverned — applies at least as strongly to deletion, but the only destructive operation on the trail writes no entry at all: `purge_expired_entries(AuditRetention(days=30))` returns the deleted count and leaves nothing behind naming who ran it or how many rows of evidence went away.
  evidence: Raised by Blind Hunter in this story's review pass 2 and reproduced by execution (a trail with one expired row: purge returns 1, `AuditEntry.objects.count()` is 0, and no entry of any action records the deletion). Not patched: closing it is a design change beyond this spec rather than a fix to it. The spec's I/O matrix specifies purge's contract with no audit requirement, its Code Map enumerates the action vocabulary as exactly load/filter/navigate/export/audit_read, and `purge_expired_entries`'s signature carries no actor — so recording the purge needs a sixth `AuditAction` value, a migration change, and a new required actor parameter, i.e. a decision about whether retention is an operator-level batch act with its own identity or a request-time act like the other five. Review pass 2 did harden the destructive path in the ways that were in scope (a future `now` is now refused, so a purge can no longer silently exceed its declared retention), but the who-purged question is left to whoever owns the retention runner — most naturally Story 9.5's deployment-perimeter surface, which already owns this ledger's other operational-surface deferrals.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-4: `query_audit_entries` materializes the whole matching set with no limit, and each read appends a row the next read returns
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `query_audit_entries` calls `list(AuditEntry.objects.filter(**filters))` and exposes no limit or pagination surface, against a table `models.py`'s own docstring describes as "expected to accumulate unboundedly between retention purges" — and because every read writes an `audit_read` row, the trail feeds itself: a compliance job polling once a minute adds 1,440 rows a day of pure self-reference, each read returning and counting all the previous ones.
  evidence: Raised independently by both reviewers in this story's review pass 2. Real but not patched: the spec's Code Map fixes this function's signature as reader identity plus arbitrary `**filters`, so adding a `limit` (and choosing its default, and deciding whether an unbounded read stays available at all) changes the published API rather than correcting it, and the compounding-self-noise half is a question about what the trail should record about itself, not a bug in what it currently does. Nothing here is load-bearing yet — the function has no callers in this worktree — so the cost of deferring is bounded, but the first surface that puts a real operator in front of the trail (an audit view, an export, or the retention runner) should not inherit an unbounded read.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-5: an actor made only of zero-width characters passes the non-blank check, so CAP-4's "who saw" can still be recorded as an invisible string
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `record_audit_entry` rejects a blank actor with `not actor.strip()`, but `str.strip()` removes only Unicode whitespace — a zero-width space, zero-width joiner, or byte-order mark is none of those, so `record_audit_entry("​", ...)` writes a row whose actor renders as nothing at all in every report that displays it, which is the state the blank check exists to make impossible.
  evidence: Raised by Edge Case Hunter in this story's review pass 2 and reproduced by execution (the row is created and reads back as `'​'`). Not patched: the right rule is a policy decision adjacent to the identity-normalization question this story deliberately answered with "store verbatim." Rejecting a hand-picked set of zero-width code points is arbitrary; rejecting by Unicode category (everything in `Cf`/`Zs`/`Cc`) is defensible but is a normalization policy applied at the boundary, which is exactly the kind of reinterpretation the spec's Boundaries argue the trail should not be making on its own. Whoever owns the identity model at the boundary — the first story that resolves where actor strings actually come from — should decide this alongside it, not this primitive in isolation.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-5` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-6: a future-dated `occurred_at` is never older than any cutoff, so a caller can write audit rows that no retention policy can ever expire
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `record_audit_entry` accepts any caller-supplied `occurred_at` whose awareness matches the deployment's, with no bound in either direction. A row stamped in the future never satisfies `occurred_at < cutoff`, so it survives every purge forever — AD-7's bounded trail quietly stops being bounded, one row at a time; a row stamped far in the past is conversely expired on the next cycle regardless of when the action really happened.
  evidence: Raised by Edge Case Hunter in this story's review pass 2 and reproduced by execution (a row stamped 100 years ahead survives `purge_expired_entries(AuditRetention(days=1))`). Deliberately not patched, unlike the structurally similar future-`now` guard added to `purge_expired_entries` in the same pass. The two differ in cost: `now` is a batch job's reference clock, where a future value is never meaningful and always over-deletes, so refusing it has no legitimate caller. `occurred_at` is on the request path — this is the primitive every load, filter, navigate and export calls — and in a multi-process deployment a caller stamping its own clock can be a few milliseconds ahead of the process running the check, so a strict refusal would turn ordinary NTP skew into a failed audit write and a failed request. Choosing between a strict bound, a skew tolerance, and clamping is a policy call the spec does not make; whoever owns the retention runner should make it against a real deployment's clock behaviour.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-6` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-7: `query_audit_entries`' `transaction.atomic()` is a savepoint inside a caller's transaction, so an outer rollback discards the `AUDIT_READ` row while the caller keeps the rows it read
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: Review pass 2 wrapped the read and its `AUDIT_READ` write in one `transaction.atomic()` block and documented it as closing AD-7's unrecorded-read hole, but Django's `atomic()` nested inside an already-open transaction is a savepoint, not an independent transaction — so under `ATOMIC_REQUESTS=True` (an ordinary Django production setting) or any service-level `@transaction.atomic`, a rollback removes the audit record of a read whose rows the caller has already received, leaving an unrecorded read that is repeatable on demand.
  evidence: Raised independently by both reviewers in this story's review pass 3 and reproduced by execution twice — once by wrapping the call in `transaction.atomic()` plus `transaction.set_rollback(True)`, once by raising inside the outer block; both left the caller holding the returned rows with zero `audit_read` rows surviving. Not patched: the two available fixes each change what deployments may call this function. `transaction.atomic(durable=True)` converts the silent hole into a loud `RuntimeError`, which is the module's own "refused rather than run unrecorded" idiom but makes `query_audit_entries` uncallable from any view running under `ATOMIC_REQUESTS=True`; writing the `AUDIT_READ` row on a separate connection so it commits independently sidesteps that but puts the audit write outside the caller's transaction entirely, which is a durability model the spec does not choose between. Pass 3 patched the docstring's overclaim so the guarantee is stated accurately (scope, not durability) and named the caller's responsibility; the substantive choice belongs with whichever story first puts a real request-path caller in front of the trail — Story 9.2's `filtering.py` or the export surface — since only a real caller settles which of the two costs is acceptable.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-7` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-8: nothing makes the audit trail append-only, so a single ORM call rewrites or erases CAP-4 evidence leaving no record that it happened
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `AuditEntry` is an ordinary Django model with no `save()`/`delete()` restriction and no deployment-level constraint, so any code in the process can call `AuditEntry.objects.filter(pk=...).update(...)` or `.delete()` and silently rewrite the record of what was seen. Every guard this story invests in is a *write-time* guard on `record_audit_entry`; none of them constrains what happens to a row afterwards, so CAP-4's "durable record" is durable only against accidental misuse of the sanctioned API.
  evidence: Raised by Blind Hunter in this story's review pass 3 and reproduced by execution — a `mallory / export / 500000 rows / salaries` row was rewritten to `bob / 1 / ""` by one `.update()` call, with zero entries recording the rewrite. Distinct from `DW-FU-9-3-3`, which covers the *sanctioned* purge going unrecorded; this is the unsanctioned-rewrite path. Not patched, and deliberately not patchable in this module alone: a `save()`/`delete()` override does not constrain `.update()` or raw SQL, so any in-process guard is advisory at best, and the real mechanisms — an INSERT-only database grant for the application role, an append-only table, or a hash chain over the rows — are deployment and schema decisions this story's spec neither makes nor scopes. It belongs with Story 9.5's deployment perimeter, which already owns this ledger's other operational-surface deferrals, and should be settled before any adopter relies on the trail as evidence rather than as telemetry.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-8` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-3-9: the identity perimeter admits an actor longer than the audit column's cap, so such a user can neither use the dashboard nor have the attempt recorded
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: `DashboardIdentityMiddleware` imposes no length bound on the identity it extracts — its own comment names an LDAP DN as a legitimate value shape and defers any normalization to this story — while `record_audit_entry` rejects any actor over `AuditEntry.actor`'s 255-character cap rather than truncating it, so once Story 9.2/9.4's call sites are wired in, an identity longer than the cap makes every load, filter, navigate and export raise on the audit primitive, and none of those refused attempts is recorded either.
  evidence: Raised by Blind Hunter in this story's review pass 4 and reproduced by execution: a 330-character DN (`CN=<300 a's>,OU=Users,DC=example,DC=com`) passed through `DashboardIdentityMiddleware` onto `scope["dashboard_identity"]` intact, then `record_audit_entry` raised `ValueError: actor exceeds the 255-character audit field cap (got 330 characters)` with `AuditEntry.objects.count() == 0`. Real but not this story's to settle: the cap and the reject-rather-than-truncate rule are both explicit spec decisions ("cap length only as a robustness bound, and reject rather than truncate an overlong value so evidence is never silently corrupted"), and the spec's Boundaries forbid wiring this primitive into any call site here, so nothing in this worktree can exercise or fix the interaction. Closing it means choosing among widening the column, refusing an over-long identity at the perimeter where the caller can be told why, or recording a documented digest — a cross-story identity-model decision that belongs with whichever story first puts a real request-path caller in front of `record_audit_entry`, alongside `DW-FU-9-3-5`'s zero-width-actor question, which is the same boundary-normalization policy seen from the other end.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-3-9` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-4-1: The refusal-webhook POST blocks synchronously for up to 5s with no rate limit, on a path a caller can trigger repeatedly
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: `authorize_export`'s `_post_refusal_webhook` makes a synchronous `urllib.request.urlopen` call (up to a 5s timeout) on every refused export, with no async variant and no rate limit or backoff — if called from an async Channels consumer it stalls that worker's whole event loop for the duration, and a caller who knows they will be refused can trigger repeated 5s blocking calls with no throttle.
  evidence: Raised by Blind Hunter in this story's first review pass (two related findings, combined here: the blocking-call-in-async-context risk and the no-rate-limiting-on-a-refusal-triggered-network-call risk share one root cause). Not patched: this mirrors Story 9.1's own precedent for `get_master_dataset()` ("called from an async Channels consumer it blocks the whole worker's event loop — an async variant belongs with the first story that puts it on an async hot path", still open on this ledger) — no adopter view exists yet in this codebase to demonstrate which calling convention (sync Django view vs. async Channels consumer) actually applies, and CAP-6's deployment perimeter (Story 9.5) is where rate limiting / backpressure at the edge is architecturally scoped. Not addressed in this pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-4-2: `maybe_encrypt_export` never removes the plaintext source after encrypting
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: When `policy.encryption_recipient` is declared, `maybe_encrypt_export` produces an encrypted `output` but leaves the original plaintext `path` untouched — if encryption exists to protect the exported artifact at rest, the plaintext copy sitting next to the ciphertext defeats that purpose unless the caller separately remembers to delete it, and nothing in this module says so.
  evidence: Raised by Blind Hunter in this story's first review pass. Not patched: `keys.encrypt_file` (Story 1.3), which this function wraps, already establishes the "never delete the input" contract, so deleting here would be new, surprising behavior for a caller who might own `path` for other reasons (re-export, a separate secure store) — deciding who owns cleanup of the plaintext source is a caller-lifecycle question best resolved once a real adopter export view exists to define it (Story 9.5/9.6), not invented unilaterally here.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-4-3: The export-refusal webhook payload is unsigned, so a receiver cannot verify it actually came from this service
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: `_post_refusal_webhook` POSTs a plain JSON payload with no HMAC or shared-secret header — for a channel explicitly framed as a security-event notifier, a receiver has no way to distinguish a genuine refusal event from one forged by any other actor able to reach the same URL.
  evidence: Raised by Blind Hunter in this story's first review pass. Not patched: this story's own spec Design Notes already scoped the payload to be "intentionally minimal" and the architecture spine's Deferred section states "the webhook contract is fixed" (a plain POST) while naming which downstream SIEM/Slack/Teams sink adapters get built as the open demand question — payload signing is the same class of hardening-not-yet-demanded decision, best made together with Story 9.5's deployment-perimeter work (which already owns TLS/edge policy for this pattern) rather than unilaterally here.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4-3` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

  verified: 2026-09-07 — resolved — CI/hygiene sweep (worktree `hygiene-steward`, branch `chore/ci-hygiene-sweep-2026-09-07-steward`): `dashboard/export.py`'s `_post_refusal_webhook` now HMAC-SHA256-signs the payload with a secret resolved fresh per call via `resolve_webhook_secret()` (env `STEWARD_EXPORT_WEBHOOK_SECRET`, never a literal/default — mirroring `pyforge.herald.webhook.resolve_webhook_secret`'s precedent, the exact sibling this entry's own evidence names as unbuilt) and sends `X-Steward-Signature-256: sha256=<hex>` alongside the existing `Content-Type` header; a receiver can now verify a refusal event actually came from this service. Fail-closed, per this repo's security-tooling convention: with no secret configured, the webhook is refused unsent rather than falling back to the old unsigned POST (`WebhookSecretMissingError`, caught by the existing broad `except Exception`, logged as a secondary warning). New tests in `tests/unit/test_dashboard_export.py`: `test_authorize_export_posts_a_signed_webhook_on_refusal` asserts the header is present and its hex matches an independently-computed `hmac.new(secret, payload, hashlib.sha256).hexdigest()`; `test_authorize_export_does_not_post_an_unsigned_webhook_when_no_secret_is_configured` proves the fail-closed path (zero `urlopen` calls); three `resolve_webhook_secret` unit tests. Proved these tests exercise real new behavior, not vacuous ones: reverted `export.py` alone and confirmed the test module fails to even import (`ImportError: cannot import name 'WebhookSecretMissingError'`) before restoring. `pyforge-steward-test` full suite: 1196 passed (plus one pre-existing, unrelated red — `test_conda_forge_expert_not_replaced`, flagging the already-landed `9ef5b8cd79` CFE-retro commit's `fix(cfe):` subject against the `retro:` sanction pattern; confirmed pre-existing by reverting this pass's changes and re-running, same red). ledger status mapped to resolved.

### DW-9-4-4: `ExportPolicy.webhook_url` has no protection against loopback/link-local/internal targets
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: Construction-time validation only checks for an http(s) scheme and a real host — nothing rejects a declared webhook pointed at a loopback, link-local, or cloud-metadata address (e.g. `169.254.169.254`), a defense-in-depth gap for a server-side outbound POST.
  evidence: Raised by Blind Hunter in this story's first review pass. Not patched: `webhook_url` is adopter-declared configuration, the same trust level as `TrustedIngress.addresses`/`AccessDeclaration` elsewhere in this epic, not attacker-controlled per-request input, so this is not a classic SSRF vector today — but Story 9.1 set a precedent of deferring rather than dismissing this class of address-form concern for `TrustedIngress.addresses` (CIDR/hostname/IPv6-mapped forms, still open on this ledger), and this is the same category applied to a new declaration. Belongs with Story 9.5's deployment-perimeter/ingress model, which already owns the estate's other address-form questions.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

  verified: 2026-09-07 — resolved — CI/hygiene sweep (worktree `hygiene-steward`, branch `chore/ci-hygiene-sweep-2026-09-07-steward`): `ExportPolicy` gains `allow_private_webhook_targets: bool = False` and two fail-closed SSRF checks named specifically in this entry's own summary — (1) construction-time (`__post_init__`): an IP-literal `webhook_url` host (or the well-known `localhost` name) that is loopback/link-local (the 169.254.169.254 cloud-metadata address explicitly, via `is_link_local`)/RFC1918-private/reserved/multicast/unspecified is refused with a `ValueError` naming the offending host, unless the new flag opts in; (2) per-delivery (`_post_refusal_webhook` -> `_webhook_target_is_blocked` -> `_resolve_hostname_ips`/`_is_blocked_ip_address`): a DNS-name `webhook_url` (which construction-time validation cannot safely judge without a network call) is re-resolved and re-checked fresh on every refusal, closing the gap a benign-at-declaration-time name that later resolves (or rebinds) to a blocked address would otherwise leave open. New tests in `tests/unit/test_dashboard_export.py`: 7 parametrized construction-time-rejection cases (127.0.0.1, localhost, ::1, 169.254.169.254, and one each of the three RFC1918 blocks) + the opt-in-allows case + the non-bool-flag TypeError case + the "a DNS name is accepted at construction, not resolved" case + `test_authorize_export_refuses_a_webhook_target_that_resolves_to_a_blocked_address` (mocks DNS resolution to return `169.254.169.254`, proves zero `urlopen` calls) + its opt-in counterpart. `pyforge-steward-test` full suite: 1196 passed (plus the one pre-existing, unrelated red documented on DW-9-4-3's verified line above). ledger status mapped to resolved.

### DW-9-4-5: `authorize_export` being "the ONLY place the decision is made" is a documented convention, not something enforced at the code level
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: Nothing wires `authorize_export` into an adopter's export view automatically (no decorator, no required call-site check) — an adopter's view that forgets to call it fails OPEN with no automated guard, which is the same "declared, not implemented" gap CAP-5 exists to close for the UI-gate case.
  evidence: Raised by Blind Hunter in this story's first review pass; confirms a gap this story's own spec Design Notes already named when explaining why a `steward deploy` wiring-verification CLI check does not belong in this story (it would need to import from `dashboard/`, which the existing invariant `test_no_module_outside_dashboard_imports_dashboard_django_or_channels` forbids). Story 9.5's deployment-perimeter surface is where that verification can exist without the import-boundary conflict; this entry moves the concern from a spec design note into a tracked follow-up so it is not lost.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4-5` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-5-1: The `perimeter` verb exposes no `--base-port`/`--bind-host` flags, leaving `_worker_ports`'s range check and `bind_host`'s injection guard unreachable in the shipped CLI
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-5-the-perimeter-ships-with-the-pattern.md`
  summary: `render_daphne_unit`/`render_edge_config` accept `base_port`/`bind_host` keyword parameters (defaulted to `8001`/`127.0.0.1`), but `_add_deploy_subparsers`'s `perimeter` parser exposes no `--base-port`/`--bind-host` flag, so `_run_perimeter` always calls them with the hardcoded defaults — an operator whose 8001+ range is already occupied on the target host has no way to override it. The same gap means `bind_host` is interpolated into both rendered manifests (`ExecStart=daphne --bind {bind_host} ...` and the nginx `upstream` block's `server {bind_host}:{p};`) without going through `_validate_nginx_value`'s injection-character guard, and `base_port` has no lower-bound check of its own (only the upper-bound `_worker_ports` overflow check) — both are currently safe only because neither is reachable from any operator-supplied input in the shipped CLI surface.
  evidence: Raised independently by two follow-up review-pass agents (Blind Hunter: missing `--base-port`/`--bind-host` flags; Edge Case Hunter: `bind_host` skips `_validate_nginx_value`, `base_port` has no `>= 1` check) during Story 9.5's follow-up review pass. Adding new CLI flags exceeds this story's frozen Code Map (`--workers`, `--cache-backend`, `--channel-layer-backend`, `--trusted-address`, `--tls-cert`, `--tls-key`, `--output-dir` only), so out of scope for this pass; revisit together if/when a future story exposes either parameter to the CLI.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-5` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-5-the-perimeter-ships-with-the-pattern.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-5-2: The rendered systemd unit name and nginx upstream name are hardcoded, so two perimeter deployments to the same host would collide
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-5-the-perimeter-ships-with-the-pattern.md`
  summary: `render_daphne_unit`/`render_edge_config` always name the systemd template unit `pyforge-steward-dashboard@.service` and the nginx upstream block `pyforge_steward_dashboard_workers`, with no `--name`/`--service-name`-style flag. Two independent perimeter deployments to the same host (e.g. staging and prod, or two adopter projects sharing infrastructure) would collide on both names, silently overwriting or conflicting with each other's manifests.
  evidence: Raised by Blind Hunter during Story 9.5's follow-up review pass. This story's own spec scopes exactly one `[dashboard]` extra / one deployment shape per adopter (its "Never" bullet rules out a second, nested extra for the same reason) and names no multi-instance-per-host requirement anywhere in the I/O matrix or Tasks, so a naming/namespacing flag is a scope addition, not a fix for something the current contract promises; revisit if a real adopter needs more than one perimeter deployment on one host.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-5-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-5-the-perimeter-ships-with-the-pattern.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-6-1: the dashboard test files' hand-duplicated `settings.configure()` guard, now in a fourth file, aborts the whole run when a Django-app-needing file collects behind one that only declares `CACHES`
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-6-isolation-proven-by-tests-that-cannot-pass-vacuously.md`
  summary: `test_dashboard_isolation_proof.py` (this story) declares only `CACHES` in its `settings.configure()` block, matching `test_dashboard_views.py`'s existing minimal pattern — but reproduced by execution: `pytest test_dashboard_isolation_proof.py test_dashboard_audit.py` (this file collected first) aborts the entire run at collection with `AssertionError: INSTALLED_APPS is []`, because whichever file's guard runs first wins Django's one-shot `settings.configure()` and a CACHES-only winner leaves `INSTALLED_APPS`/`DATABASES` unset for every file collected after it that needs them.
  evidence: Raised independently by this story's Blind Hunter review pass, reproduced by execution against both the new file and, identically, against the pre-existing `test_dashboard_views.py` (`pytest test_dashboard_views.py test_dashboard_audit.py` fails the same way) — confirming this is a pre-existing pattern from Story 9.2, not something this story introduced, so it is not this story's to fix. In a full-suite run (`pytest src/shared/packages/pyforge-steward/tests`, the only invocation any pixi task or CI-adjacent command actually uses) alphabetical collection order means `test_dashboard_audit.py` always wins the race with its fuller superset declaration, so the failure mode is real but latent — triggered only by a developer cherry-picking specific files on the command line in an unlucky order. Four files now hand-duplicate this same settings-configuration dance with no shared `conftest.py` (`test_dashboard_audit.py`, `test_dashboard_cache.py`, `test_dashboard_views.py`, and now `test_dashboard_isolation_proof.py`), each reasoning about "mutual superset" compatibility with the others by comment rather than by a single source of truth — the real fix (a `tests/unit/conftest.py` fixture or module doing one settings configuration all four files rely on) touches multiple existing files and is out of this test-only story's scope (its spec's Boundaries forbid modifying the existing `test_dashboard_*.py` files). Whoever next adds a fifth Django-needing dashboard test file, or hits this collection-order failure while iterating, should settle it then.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-6` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-6-isolation-proven-by-tests-that-cannot-pass-vacuously.md, tests/unit/conftest.py); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-7-1: dashboard_diff() cannot see a file staged (git add) but left uncommitted after a failed git commit
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-7-hosted-or-static-no-fork.md`
  summary: dashboard_diff() reports "nothing to deploy" for a change that is actually staged-but-uncommitted after a prior git commit failure, because it checks git diff (which matches once staged) and, as of this story, git ls-files --others (which excludes anything already staged) — neither surface sees a file in that intermediate state.
  evidence: Raised by Edge Case Hunter during this story's review pass 3, examining the dashboard_diff() extension this story added for untracked-file detection. The gap is pre-existing and not caused by this story: for an already-tracked file (the original data.js update path from Story 2.2), the identical failure mode already existed — if commit_and_push_dashboard's git add succeeds but its subsequent git commit fails (e.g. no git identity configured, a rejecting hook), the working tree now matches the staged index, so a bare git diff (no --cached) already reported empty on the very next invocation, before this story ever touched the function. This story's git ls-files --others addition inherits the same blind spot for newly-created files reaching that same staged-but-uncommitted state. Not this story's to fix: the root cause is dashboard_diff()'s fundamental reliance on git diff (working tree vs index) rather than git diff --cached (index vs HEAD) or git status --porcelain (which would see all three states — untracked, staged, and modified — uniformly), a design choice from Story 2.2 that predates and is orthogonal to whether the affected file is newly created or pre-existing. Whoever next revisits dashboard_diff()'s git plumbing should fold this in.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-7` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-7-hosted-or-static-no-fork.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-7-2: publishing a static board requires a full dashboard-gen rebuild and a valid Steward sprint ledger, because deploy dashboard runs both unconditionally before it ever computes a diff
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-7-hosted-or-static-no-fork.md`
  summary: publishing a static board requires a full dashboard-gen rebuild and a valid Steward sprint ledger, because deploy dashboard runs both unconditionally before it ever computes a diff, so an adopter whose only goal is CAP-8's zero-infrastructure static export inherits two heavyweight preconditions that neither deploy static's help text nor its docstring mentions.
  evidence: Raised by Blind Hunter during this story's follow-up review pass and confirmed by reading `_run_dashboard` directly: it calls `_tracked_ledger_refusal(cwd=root)` and returns a refusal if Steward's own tracked `sprint-status-ledger.yaml` is missing or malformed (Story 5.2), then calls `build_dashboard(cwd=root)` — which shells out to `retired-console-check`, rebuilding the entire program console in a very large environment — and only afterwards reaches `dashboard_diff(cwd=root)`. Both run on the bare verb, with no flag to skip either. Story 9.7 did not introduce this ordering (it is Story 2.2's build-then-reconcile shape plus Story 5.2's ledger guard, both predating it) and did not change `_run_dashboard` at all; what changed is that 9.7 makes the bare `deploy dashboard` verb the designated publication path for `deploy static`'s output, per its own Approach ("the existing steward deploy dashboard verb then commits/pushes that unchanged — no new git plumbing"). That promise holds for the git plumbing specifically, which is why it is not a defect in this story, but it means a third-party adopter who only wants their own static board published cannot get there without satisfying Steward-internal preconditions unrelated to their board. Deliberately not fixed here: the plausible remedies (a `--skip-build` flag, scoping the ledger guard to the paths that need it, or a dedicated reconcile-only verb) all change the pre-existing `dashboard` verb's contract and its Story 2.2 / 5.2 acceptance criteria, which is outside this story's scope and needs its own decision about that verb's shape. Whoever next revisits `_run_dashboard`'s preconditions, or onboards the first external CAP-8 adopter, should settle it then.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-7-2` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-7-hosted-or-static-no-fork.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-7-1-3: Follow-up review still recommended for 7-1-one-build-whole-guild after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-7-1-one-build-whole-guild.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260809-114839-7af9; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-1` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-9-1-2: Follow-up review still recommended for 9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260810-193158-7f2b; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-8` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-11-2-1: Story 11-2's original Pattern-A groundwork is superseded, not lost
- source_spec: 2026-08-21 sprint-change-proposal (this dir)
  summary: an earlier attempt at Story 11-2 built real, live-verified groundwork for DB-GPT's
  Pattern A integration (Django app scaffold, `dbgpt_schema` migration, settings wiring) before
  hitting the `fastapi` pin conflict documented in this same proposal. That work was committed
  and pushed to `backup/steward-11-2-blocked-adf57ec5` as an insurance copy, never merged. The
  2026-08-21 correct-course pass moves 11-2 to Pattern B (pap:AD-14/pap:AD-17); the schema-migration and
  settings-wiring pieces are pattern-agnostic and likely reusable, but the ASGI-dispatcher piece
  is Pattern-A-specific and should be discarded, not resurrected, by whoever next implements 11-2.
  evidence: `backup/steward-11-2-blocked-adf57ec5` branch, PR #571 (ledger correction marking
  11-2 blocked, since reopened to `backlog` by this proposal), and this proposal's own Impact
  Analysis § Epic 11.
  status: informational — no action needed unless 11-2's next implementer is unsure whether the
  backup branch represents live work to recover. It does not; recover pattern-agnostic pieces
  selectively, do not merge the branch wholesale.
  promoted: 2026-08-21 — added directly during the sprint-change-proposal correct-course pass.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-11-2-2: DB-GPT's own metadata store cannot be wired to real PostgreSQL — verified upstream limitation, AD-9-blocked
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-11-2-db-gpt-joins-via-its-configured-integration-pattern.md`
  summary: a second attempt at Story 11-2 (this one pap:AD-17/Pattern-B-correct, not the reverted
  Pattern-A attempt DW-11-2-1 describes) built and live-verified the whole registry-driven
  integration — `dbgpt_schema` migration, `config/engine_patterns.py` pap:AD-17 registry, a
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

  verified: 2026-08-26 — resolved — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to resolved

  verified: 2026-09-02 — resolved — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-11-2-db-gpt-joins-via-its-configured-integration-pattern.md); ledger status mapped to resolved; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-11-4

`langflow_integration/tests.py` keeps an unguarded `cursor.fetchone()[0]` — the identical
pattern Story 11.4's gates forced a None-guard for in the story's own file (mypy `[index]`),
latent in the sibling only because it sits outside the `mypy platformapp config tests`
surface. Pre-existing; Story 11.4 treated the file as read-only. Remedy: None-guard it and
consider widening the mypy surface to the integration test modules. Severity: low. Status:
open. Relayed from the story worktree's ephemeral Tier-3 file at landing, 2026-08-21.

  status: open
  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): no source_spec; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-12-2: The "395-package `python-agent-platform` env" figure embedded in timeout-justification comments has no mechanism keeping it accurate.

- source_spec: `planning-artifacts/specs/spec-12-2-gke-as-a-portability-profile.md`
  summary: The "395-package `python-agent-platform` env" figure embedded in timeout-justification comments has no mechanism keeping it accurate.
  evidence: Found by review during this story, but the figure pre-exists in the sibling `container` job's own timeout comment (platform-ci.yml, Story 10.3) — this story's `gke-portability-smoke` job reused the same descriptive phrasing for consistency, it did not introduce the figure. Not this story's regression to fix.
  location: .github/workflows/platform-ci.yml (container job's timeout-minutes comment, and gke-portability-smoke's own by extension)
  origin: spec-deferred a7f2167e2467 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1: Bookkeeping YAML is not locked; concurrent start/clean in one checkout can race.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: Bookkeeping YAML is not locked; concurrent start/clean in one checkout can race.
  evidence: save_bookkeeping uses atomic_write but two processes can still interleaved read-modify-write over .steward/workspaces.yaml.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  origin: spec-deferred 5e5280514e6b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-2: start does not `git fetch` before branching from origin/main.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: start does not `git fetch` before branching from origin/main.
  evidence: Thin git wrap: if origin/main is stale or missing locally, start fails with a git error rather than refreshing remotes first.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  origin: spec-deferred d2605a4be02d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-3: A freshly started branch with no unique commits is treated as merged by --merged-only.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: A freshly started branch with no unique commits is treated as merged by --merged-only.
  evidence: merge-base --is-ancestor is true when tip equals source; accurate but surprising immediately after start.
  origin: spec-deferred 1457c9c38154 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-4: No tracked schema/example for `.steward/workspaces.yaml`.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: No tracked schema/example for `.steward/workspaces.yaml`.
  evidence: Review noted operators only get a gitignore entry; shape is discoverable only from code.
  origin: spec-deferred 3ef3c14440d7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; cited paths 0/1 present (absent: .steward/workspaces.yaml); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-5: Distinct slugs that normalize to the same sibling path (e.g. a/b vs a-b) can collide.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: Distinct slugs that normalize to the same sibling path (e.g. a/b vs a-b) can collide.
  evidence: scratch_path_for replaces `/` with `-` without collision detection.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  origin: spec-deferred 8238370bede5 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-1-6: Stale bookkeeping entries (missing path / moved checkout) stay listed by ls.

- source_spec: `planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md`
  summary: Stale bookkeeping entries (missing path / moved checkout) stay listed by ls.
  evidence: CAP-2 deliberately avoids per-worktree git; staleness is out of 13.1.
  origin: spec-deferred 490117283b3d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-13-2: status ahead/behind uses local source ref; no fetch of origin before counting.

- source_spec: `planning-artifacts/specs/spec-13-2-status-and-the-feed-mirror-decision.md`
  summary: status ahead/behind uses local source ref; no fetch of origin before counting.
  evidence: Same thin-git posture as 13.1 start (no auto-fetch). Stale origin/main makes behind under-count until the operator fetches.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  origin: spec-deferred 1347f0e476b0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-14-1: skill-manifest.csv parsing is a naive quoted-CSV split; skills with commas in fields would mis-parse.

- source_spec: `planning-artifacts/specs/spec-14-1-the-pre-flight-diff-retrodicts-a-real-upgrade.md`
  summary: skill-manifest.csv parsing is a naive quoted-CSV split; skills with commas in fields would mis-parse.
  evidence: `_read_installed_skill_names` splits on commas rather than using the csv module. Current skill IDs have no commas; review pass noted the fragility.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  origin: spec-deferred 4a363ab1e2e2 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-14-5: Trap 8 (.git/info/exclude stale shield lines) is not automated in prove-landed.

- source_spec: `planning-artifacts/specs/spec-14-5-one-command-proves-the-upgrade-landed.md`
  summary: Trap 8 (.git/info/exclude stale shield lines) is not automated in prove-landed.
  evidence: failure-modes.md lists trap 8 under CAP-5 orbit, but story ACs only require drift integrity + CFE meta + loop-home init/validate. Hand cleanup remains.
  location: upgrade.py CAP-5 gates
  origin: spec-deferred 7d9ac02dba5f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-1: Live (non-baseline) probe implementations are only exercised via stubs; no temp-repo / urllib-monkeypatch coverage for recipe/installed/HTTP paths.

- source_spec: `planning-artifacts/specs/spec-15-1-one-command-reports-the-whole-pipelines-truth.md`
  summary: Live (non-baseline) probe implementations are only exercised via stubs; no temp-repo / urllib-monkeypatch coverage for recipe/installed/HTTP paths.
  evidence: verification-gap review: default ProbeHooks paths never run in tests; operators' live `steward suite pipeline-truth` can diverge while --baseline stays green.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
  origin: spec-deferred 6e252fd00cd7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-1-2: Dashboard wired census uses loose fleet surfaces (docs/dashboard, presentations) rather than package-specific wire state.

- source_spec: `planning-artifacts/specs/spec-15-1-one-command-reports-the-whole-pipelines-truth.md`
  summary: Dashboard wired census uses loose fleet surfaces (docs/dashboard, presentations) rather than package-specific wire state.
  evidence: blind-hunter: both dashboards can read wired whenever those docs exist; baseline still encodes the 2026-08-22 research column.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
  origin: spec-deferred 00dbb10c84c7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-3: Conda installer subprocess has no timeout; a hung *-install can block the provision duty indefinitely.

- source_spec: `planning-artifacts/specs/spec-15-3-five-modules-wire-through-the-provisioning-verb.md`
  summary: Conda installer subprocess has no timeout; a hung *-install can block the provision duty indefinitely.
  evidence: Review edge-case finding: subprocess.run for CondaInstallBackend has no timeout= argument. Pre-existing pattern also applies to bmb setup-skill uv run calls; not uniquely introduced by 15.3 wiring.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  origin: spec-deferred 6daa4503bfc4 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-3-2: No rollback of copied skill dirs when post-install verification or manifest write fails after installer exit 0.

- source_spec: `planning-artifacts/specs/spec-15-3-five-modules-wire-through-the-provisioning-verb.md`
  summary: No rollback of copied skill dirs when post-install verification or manifest write fails after installer exit 0.
  evidence: Skills may be copied before manifest record; a later raise leaves orphan .claude/skills entries without a module key. Collision check then blocks retry until skills are removed manually.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  origin: spec-deferred 66b476615235 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-3-3: --list-modules does not surface _SKIPPED_MODULES (WDS) or skip reasons.

- source_spec: `planning-artifacts/specs/spec-15-3-five-modules-wire-through-the-provisioning-verb.md`
  summary: --list-modules does not surface _SKIPPED_MODULES (WDS) or skip reasons.
  evidence: Operators cannot discover from the list verb that WDS is intentionally unwired versus simply unsupported; skip is only on --module wds.
  origin: spec-deferred 8f88ef20f773 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-3-4: Hard-coded _CIS_SKILL_NAMES allowlist is not asserted against the live bmad-creative-intelligence-suite share tree.

- source_spec: `planning-artifacts/specs/spec-15-3-five-modules-wire-through-the-provisioning-verb.md`
  summary: Hard-coded _CIS_SKILL_NAMES allowlist is not asserted against the live bmad-creative-intelligence-suite share tree.
  evidence: Drift shows up only as post-install skills-missing RuntimeError.
  origin: spec-deferred 9fff87be3e08 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-4: Live prove-landed may still hit the network / warm caches when running cited npx/uv spot-checks even with --help/--dry-run.

- source_spec: `planning-artifacts/specs/spec-15-4-the-upgrade-gate-spot-checks-one-native-path-per-class.md`
  summary: Live prove-landed may still hit the network / warm caches when running cited npx/uv spot-checks even with --help/--dry-run.
  evidence: Story 15.4 deliberately invokes native CLIs; side effects are inherent to the AC. Failures remain advisory.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  origin: spec-deferred b3a8e13b0b34 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-4-2: skip_native_spot_checks exists on build_prove_landed_report but has no CLI flag.

- source_spec: `planning-artifacts/specs/spec-15-4-the-upgrade-gate-spot-checks-one-native-path-per-class.md`
  summary: skip_native_spot_checks exists on build_prove_landed_report but has no CLI flag.
  evidence: Not required by CAP-4 AC.
  origin: spec-deferred 870ab68a8b44 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-15-4-3: _BMAD_LOOP_UV_GIT_SPEC hard-pins v0.11.0 with no regeneration note when the matrix version moves.

- source_spec: `planning-artifacts/specs/spec-15-4-the-upgrade-gate-spot-checks-one-native-path-per-class.md`
  summary: _BMAD_LOOP_UV_GIT_SPEC hard-pins v0.11.0 with no regeneration note when the matrix version moves.
  evidence: Citation substring test catches matrix edit drift after the fact.
  origin: spec-deferred 9d95aae537b3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  resolution: RESOLVED 2026-09-06 (steward/bmad-core-upgrade-6.12.0-followups). `_BMAD_LOOP_UV_GIT_SPEC` now reads `@v0.11.1` and its comment names the matrix row as the thing it mirrors; the spot-check test asserts the constant appears verbatim in install-matrix.md, so the next matrix bump reds the test instead of drifting silently. Found live: the 2026-09-06 prove-landed advisory named `@v0.11.0` while the matrix said `@v0.11.1`.
  residual: The uv-from-git executable probe is now `uv tool install --help` (the flag `--dry-run` never existed on `uv tool install`; the native install resolves a git URL over the network) — the class is exercised, the spec string is only asserted against the matrix, not resolved.
  status: resolved

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-16-2: Operator-facing deploy README / NOTES still omit COMPONENT_RUNTIME and the invalid DJANGO_ADMIN_URL set beyond the chart values change.

- source_spec: `planning-artifacts/specs/spec-16-2-startup-refuses-misconfiguration-two-stage-and-named.md`
  summary: Operator-facing deploy README / NOTES still omit COMPONENT_RUNTIME and the invalid DJANGO_ADMIN_URL set beyond the chart values change.
  evidence: Blind-hunter noted docs/NOTES still describe required env without CAP-3 locality or admin-URL validity rules. Chart default was patched; prose docs were not fully rewritten this story.
  location: src/platform/deploy/README.md
  origin: spec-deferred 3d536d29639e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

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

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

## Canopy course correction (2026-08-24)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-CANOPY-2026-08-24

- source_spec: `planning-artifacts/change-history/sprint-change-proposal-2026-08-24-canopy.md`
  summary: Canopy Phase 5 (`spec-pyforge-unifying-strategy`) — reconcile shipped Epic 11 with Epic 27 DDL governance without reopening engine integration stories.
  evidence: Epic 11 Stories 11.1–11.2 provisioned `langflow_schema` / `dbgpt_schema` via Django `RunSQL` under parent AD-5; Canopy CAP-9 / FR-22 / canopy:AD-9 moves production DDL to Liquibase (Epic 27). Architecture spine marks this as conflict-not-override — isolation and `search_path` remain; only the DDL producer changes.
  resolution: **11.1 and 11.2 are NOT reopened** — sprint-status stays `done`; isolation shipped. **Epic 27 is the superseding forward work** (S-27.1 operator gate → S-27.2 pre-upgrade Job + DML-only app role → sqlmigrate CI gate). Do not queue rework of 11.1/11.2 when FR-22 lands.
  open_joint: `lane1-serves-dw-h3` — **answered 2026-08-25: no.** Lane 1 Wagtail `/cms/` does not
    serve atlas `LaSuiteClient` Docs REST (`POST /api/v1/documents/` etc.). DW-H3 remains atlas
    attended bring-up. Joint decision recorded; not invented in steward Canopy stories.
  origin: Phase 5 bmad-correct-course, pyforge-steward, 2026-08-24
  severity: medium
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-OM-2026-08-24 — Operating-model obligations (all eight stations)

- source_spec: cross-cutting (pyforge-unifying-strategy Grounding Q1–Q8; steward SCP operating-model, §6 revisited)
  summary: Estate OM + CAP-18: shared hook-spec in pyforge-core; Warden Epic 9 is the PR-gate retrofit; this station extracts one process hook spec (today's backend = default plugin).
  owner: station planning (this file) + steward (Canopy FRs) + warden (PR-gate hook specs)
  status: open
  recorded: 2026-08-24
  close_when: steward S-32.1 and S-32.2 done; Warden Epic 9 done (sole PR-gate); no station CI job publishes a pass/fail that bypasses Warden

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-12-3: build-pixi-mirror.py has no retry/backoff for a transient network failure during the mirror build; one flaky response anywhere in the ~428-package fan-out fails the whole job (a rerun is the workaround).

- source_spec: `planning-artifacts/specs/spec-12-3-air-gap-parity-is-a-failing-check.md`
  summary: build-pixi-mirror.py has no retry/backoff for a transient network failure during the mirror build; one flaky response anywhere in the ~428-package fan-out fails the whole job (a rerun is the workaround).
  evidence: Raised by Blind Hunter in this story's first review pass. Not fixed in this pass: standard `requests` retry via a Session+HTTPAdapter is straightforward but adds real complexity for a purely operational (not correctness) concern -- reruns are cheap and the mirror-build phase runs with normal network access, no adversarial condition.
  origin: spec-deferred 499561004d87 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-12-3-2: build-pixi-mirror.py's channel/subdir/filename derivation assumes a plain 3-segment conda URL and would silently mis-derive the mirror path for a labeled-channel package (e.g. .../conda-forge/label/ broken/linux-64/pkg.conda).

- source_spec: `planning-artifacts/specs/spec-12-3-air-gap-parity-is-a-failing-check.md`
  summary: build-pixi-mirror.py's channel/subdir/filename derivation assumes a plain 3-segment conda URL and would silently mis-derive the mirror path for a labeled-channel package (e.g. .../conda-forge/label/ broken/linux-64/pkg.conda).
  evidence: Raised by Blind Hunter and Edge Case Hunter (corroborated). Verified live against the real pixi.lock: all 428 platform-dev/linux-64 packages conform to the plain 3-segment shape today, so this is a latent risk, not a live bug -- would surface as a loud mirror-fetch failure if it ever occurred, not a silent one.
  origin: spec-deferred 0d4059b9a338 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-12-3-3: The .pixi/config.toml `[mirrors]` append in the CI job is a raw heredoc string append, not a TOML-aware merge -- would produce a duplicate `[mirrors]` table (invalid TOML) if one is ever added to the committed file later.

- source_spec: `planning-artifacts/specs/spec-12-3-air-gap-parity-is-a-failing-check.md`
  summary: The .pixi/config.toml `[mirrors]` append in the CI job is a raw heredoc string append, not a TOML-aware merge -- would produce a duplicate `[mirrors]` table (invalid TOML) if one is ever added to the committed file later.
  evidence: Raised by Blind Hunter. Verified live: the committed .pixi/config.toml currently carries only `run-post-link-scripts = "insecure"`, no `[mirrors]` table, so the append is safe today. A proper fix needs a TOML-aware merge (tomllib/tomli_w), real complexity for a scenario that does not exist yet.
  origin: spec-deferred 67a8b2e6be1d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-12-3-4: The CDN-reference-scan step's allow-pattern only recognizes `127.0.0.1`, not `localhost`/`::1` -- a future rendering path that happened to emit a localhost-based absolute URL would be flagged as external and fail the job even though it is still local.

- source_spec: `planning-artifacts/specs/spec-12-3-air-gap-parity-is-a-failing-check.md`
  summary: The CDN-reference-scan step's allow-pattern only recognizes `127.0.0.1`, not `localhost`/`::1` -- a future rendering path that happened to emit a localhost-based absolute URL would be flagged as external and fail the job even though it is still local.
  evidence: Raised by Blind Hunter. Fails in the safe direction (false failure, not a missed real external reference) and nothing in the current codebase emits a `localhost`-based absolute URL, so this is a future-proofing note, not a live gap.
  origin: spec-deferred 34f30ef75136 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-1: django-pyforge is not a pixi path dependency of platform-ci-test or the image pip layer; the host loads it via sys.path and a Containerfile COPY.

- source_spec: `planning-artifacts/specs/spec-18-1-django-pyforge-is-the-only-chrome.md`
  summary: django-pyforge is not a pixi path dependency of platform-ci-test or the image pip layer; the host loads it via sys.path and a Containerfile COPY.
  evidence: Hatchling pyproject exists. A pixi path dep would rewrite pixi.lock; the image pip layer cannot hatchling-build without extra tools.
  location: pixi.toml / src/platform/Containerfile
  origin: spec-deferred be704618450f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-1-2: Container secrets-scan still covers only src/platform and shell-hook, not the new django_pyforge COPY.

- source_spec: `planning-artifacts/specs/spec-18-1-django-pyforge-is-the-only-chrome.md`
  summary: Container secrets-scan still covers only src/platform and shell-hook, not the new django_pyforge COPY.
  evidence: Runtime copies src/shared/packages/django-pyforge into /app/django_pyforge.
  location: src/platform/Containerfile
  origin: spec-deferred 92809502c14c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-1-3: Uninstall AC is proven with an isolated template Engine, not by mutating INSTALLED_APPS (Client GET needs a live database under ATOMIC_REQUESTS).

- source_spec: `planning-artifacts/specs/spec-18-1-django-pyforge-is-the-only-chrome.md`
  summary: Uninstall AC is proven with an isolated template Engine, not by mutating INSTALLED_APPS (Client GET needs a live database under ATOMIC_REQUESTS).
  evidence: test_removing_chrome_breaks_both_portals_identically uses Engine(app_dirs=False).
  location: src/platform/tests/test_django_pyforge_chrome.py
  origin: spec-deferred 244459f73ad5 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-2: Live IdP revoke on the next request (canopy:FR-31 / canopy:AD-15 strong reading) still waits on a per-request token, not this session snapshot.

- source_spec: `planning-artifacts/specs/spec-18-2-the-switcher-shows-only-what-the-user-may-reach.md`
  summary: Live IdP revoke on the next request (canopy:FR-31 / canopy:AD-15 strong reading) still waits on a per-request token, not this session snapshot.
  evidence: OIDC login writes group-claim names into session idp_token_roles until the next successful pre_social_login. 18.3 JWT re-verify is out of scope. Epic 21 / canopy:FR-31 owns next-request revoke.
  location: src/platform/config/authorization/adapters.py
  origin: spec-deferred da6ec3115970 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-2-2: Local staff/reader personas do not include station_name roles, so a real login lists no stations until IdP groups contain those names.

- source_spec: `planning-artifacts/specs/spec-18-2-the-switcher-shows-only-what-the-user-may-reach.md`
  summary: Local staff/reader personas do not include station_name roles, so a real login lists no stations until IdP groups contain those names.
  evidence: Adapter stores CLAIMS_CONTRACT group-claim values (e.g. platform-staff). Switcher matches portal.station_name (warden, chrome-probe).
  location: src/platform/config/local_dev/personas.py
  origin: spec-deferred 47aa29d7f6d6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-3: Host mint parses an IdP JWT payload without verifying signature, issuer, or expiry. Live Keycloak Token Exchange remains Deferred.

- source_spec: `planning-artifacts/specs/spec-18-3-two-clients-one-rs256-assertion.md`
  summary: Host mint parses an IdP JWT payload without verifying signature, issuer, or expiry. Live Keycloak Token Exchange remains Deferred.
  evidence: identity_from_idp_bearer base64-decodes the payload. Spec Block If / Never Keycloak Token Exchange. Tests use a three-segment fake JWT.
  location: src/shared/packages/django-pyforge/src/django_pyforge/assertion/identity.py
  origin: spec-deferred 4d256353140c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-3-2: AssertionMiddleware is host-global; an ingress that always sets X-Forwarded-User will 401 browser routes that have no service assertion.

- source_spec: `planning-artifacts/specs/spec-18-3-two-clients-one-rs256-assertion.md`
  summary: AssertionMiddleware is host-global; an ingress that always sets X-Forwarded-User will 401 browser routes that have no service assertion.
  evidence: Identity-header AC is anti-spoof, not a full service gate. Ingress should not inject those headers on interactive chrome.
  location: src/shared/packages/django-pyforge/src/django_pyforge/assertion/middleware.py
  origin: spec-deferred 58a3e9922342 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-3-3: PortalClient only signs; it does not perform the outbound HTTP call to a station service. AST bans portal-local HTTP clients instead.

- source_spec: `planning-artifacts/specs/spec-18-3-two-clients-one-rs256-assertion.md`
  summary: PortalClient only signs; it does not perform the outbound HTTP call to a station service. AST bans portal-local HTTP clients instead.
  evidence: Intent also admits an emitter-plus-scan reading; Epic 19.2 owns remaining portal shells calling through the client.
  location: src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py
  origin: spec-deferred 7aaf2bf27bd4 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-18-3-4: Production PYFORGE_ASSERTION_* keys default empty; no rotation, kid, or env documentation in this story.

- source_spec: `planning-artifacts/specs/spec-18-3-two-clients-one-rs256-assertion.md`
  summary: Production PYFORGE_ASSERTION_* keys default empty; no rotation, kid, or env documentation in this story.
  evidence: Sign/verify fail at call time if unset. Test settings inject golden PEMs.
  location: src/platform/config/settings/base.py
  origin: spec-deferred 920707a13049 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-20-1: WAGTAILADMIN_BASE_URL still defaults to http://localhost:8000; production origin belongs on the Helm/env overlay, not this story's app contract.

- source_spec: `planning-artifacts/specs/spec-20-1-wagtail-publishes-without-a-deploy.md`
  summary: WAGTAILADMIN_BASE_URL still defaults to http://localhost:8000; production origin belongs on the Helm/env overlay, not this story's app contract.
  evidence: Review noted no chart override. Lane 1 HTTP ACs do not require a live ingress host in this story; 20.2/deploy overlay can set the env var.
  location: src/platform/config/settings/base.py
  origin: spec-deferred 95be68ac9991 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-20-1-2: migrate does not seed a HomePage as Site.root_page; `/` is Wagtail's default welcome Page until an editor publishes.

- source_spec: `planning-artifacts/specs/spec-20-1-wagtail-publishes-without-a-deploy.md`
  summary: migrate does not seed a HomePage as Site.root_page; `/` is Wagtail's default welcome Page until an editor publishes.
  evidence: AC is publish-then-see, not empty-cluster first GET. Welcome remains DB-backed. Seeding is optional operator content.
  location: src/platform/platformapp/front_door/migrations/0001_homepage.py
  origin: spec-deferred 97edcb8d12c1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-20-1-3: wagtail.documents / wagtail.images serving URLconfs are not mounted.

- source_spec: `planning-artifacts/specs/spec-20-1-wagtail-publishes-without-a-deploy.md`
  summary: wagtail.documents / wagtail.images serving URLconfs are not mounted.
  evidence: Story 20.2 owns RWX media and renditions; 20.1 forbids starting that split.
  location: src/platform/config/urls.py
  origin: spec-deferred bf1f8541b7e9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-21-1: Timing, heartbeat, and ingest-at-completion columns for canopy:FR-41/canopy:FR-42 are not on RunState yet.

- source_spec: `planning-artifacts/specs/spec-21-1-supervisor-tables-in-public.md`
  summary: Timing, heartbeat, and ingest-at-completion columns for canopy:FR-41/canopy:FR-42 are not on RunState yet.
  evidence: Story 21.1 lands the two public tables only; 21.5 owns front-door query and completed-run timing ingest.
  location: src/shared/packages/django-pyforge/src/django_pyforge/models.py
  origin: spec-deferred d6c73ff81f92 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-21-1-2: expires_at has no secondary index; TTL sweep belongs to start/get.

- source_spec: `planning-artifacts/specs/spec-21-1-supervisor-tables-in-public.md`
  summary: expires_at has no secondary index; TTL sweep belongs to start/get.
  evidence: AD-6 TTL is stored; 21.3 will look up and expire handles.
  location: src/shared/packages/django-pyforge/src/django_pyforge/models.py
  origin: spec-deferred 4597073c339c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-21-1-3: sqlmigrate / Liquibase extraction is Epic 27, not this migration.

- source_spec: `planning-artifacts/specs/spec-21-1-supervisor-tables-in-public.md`
  summary: sqlmigrate / Liquibase extraction is Epic 27, not this migration.
  evidence: Intent forbids 27-1; AD-9 production DDL comes later.
  location: src/shared/packages/django-pyforge/src/django_pyforge/migrations/0001_supervisor_tables.py
  origin: spec-deferred caa1ed9a07d1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-21-2: local-recipes keeps mcp>=1.24,<2.0 because FastMCP 3.x cannot solve with mcp 2.x. Platform-ci-test and pyforge-atlas take mcp 2.0.0.

- source_spec: `planning-artifacts/specs/spec-21-2-atlas-mcp-on-the-host-dual-era.md`
  summary: local-recipes keeps mcp>=1.24,<2.0 because FastMCP 3.x cannot solve with mcp 2.x. Platform-ci-test and pyforge-atlas take mcp 2.0.0.
  evidence: pixi.toml comments on both pins; FastMCP 4 is not on conda-forge.
  location: pixi.toml
  origin: spec-deferred 5036530b2f1b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-21-5: Last-ok age lives in Django cache; redis-cache IGNORE_EXCEPTIONS can swallow the write so a later outage shows never.

- source_spec: `planning-artifacts/specs/spec-21-5-front-door-queries-the-supervisor.md`
  summary: Last-ok age lives in Django cache; redis-cache IGNORE_EXCEPTIONS can swallow the write so a later outage shows never.
  evidence: Review noted locmem tests cannot see a swallowed redis set.
  location: src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
  origin: spec-deferred 60a7c12c3dd9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-21-5-2: load_board_rows has no LIMIT; a large run_state table can miss the 500ms budget.

- source_spec: `planning-artifacts/specs/spec-21-5-front-door-queries-the-supervisor.md`
  summary: load_board_rows has no LIMIT; a large run_state table can miss the 500ms budget.
  evidence: canopy:FR-42 budget vs unbounded SELECT; retention is not this story.
  location: src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
  origin: spec-deferred 903873aaade3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-22-1: Full `pyforge-core-test` still reds on pre-existing marshal/steward sole-ownership scans unrelated to dispatch.

- source_spec: `planning-artifacts/specs/spec-22-1-pyforge-dispatches-without-reimplementing.md`
  summary: Full `pyforge-core-test` still reds on pre-existing marshal/steward sole-ownership scans unrelated to dispatch.
  evidence: test_atomic_write_sole_ownership, test_exception_root_sole_ownership, and test_process_sole_ownership fail on sibling sources this story did not edit (same class as Story 32.1 deferred). CI for 22.1 runs unit + parity + leaf + plugin conformance only.
  location: src/shared/packages/pyforge-core/tests/meta/
  origin: spec-deferred 850cf195a039 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-23-1: canopy:AD-20 also names audit write and role-built navigation; this story's board is JSON filter-then-search only.

- source_spec: `planning-artifacts/specs/spec-23-1-same-url-different-rows.md`
  summary: canopy:AD-20 also names audit write and role-built navigation; this story's board is JSON filter-then-search only.
  evidence: Story 23.1 ACs and FR-16 name same-URL row isolation via filter_by_role / AccessDeclaration. Audit and build_navigation are already in pyforge.steward.dashboard from Epic 9 and were not wired onto /stations/atlas/board/.
  location: src/shared/packages/django-atlas/src/django_atlas_portal/board.py
  origin: spec-deferred 02b35407712b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-24-1: Applied-id keys on redis-broker have no TTL, so pyforge.events.applied:* grows on a noeviction instance.

- source_spec: `planning-artifacts/specs/spec-24-1-cloudevents-on-redis-broker.md`
  summary: Applied-id keys on redis-broker have no TTL, so pyforge.events.applied:* grows on a noeviction instance.
  evidence: EventFabric._mark_applied uses SET NX with no EXPIRE. canopy:AD-10 binds redis-broker as noeviction. Story 24.1 ACs do not require a retention policy for idempotency keys.
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred a9be7ed463af — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-26-1: Production still has no live Keycloak userinfo/introspection HTTP client; revoke is proven via IDP_CLAIMS_SNAPSHOT and IDP_USERINFO hooks.

- source_spec: `planning-artifacts/specs/spec-26-1-revoke-takes-effect-on-the-next-request.md`
  summary: Production still has no live Keycloak userinfo/introspection HTTP client; revoke is proven via IDP_CLAIMS_SNAPSHOT and IDP_USERINFO hooks.
  evidence: fetch_current_idp_claims prefers snapshot, then IDP_USERINFO, then the session claims document from login. Without a hook, login continuity still uses that document until the operator wires userinfo.
  location: src/platform/config/authorization/current_claims.py
  origin: spec-deferred fcef5bd36cde — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-32-1: pyforge-core-test reports 9 pre-existing sole-ownership failures in sibling marshal/steward/herald trees, unrelated to hooks.py.

- source_spec: `planning-artifacts/specs/spec-32-1-shared-hook-spec-and-plugin-registration-in-pyforge-core.md`
  summary: pyforge-core-test reports 9 pre-existing sole-ownership failures in sibling marshal/steward/herald trees, unrelated to hooks.py.
  evidence: Failures are in test_atomic_write_sole_ownership, test_exception_root_sole_ownership, and test_process_sole_ownership against marshal/steward/herald sources that this story did not edit.
  location: src/shared/packages/pyforge-core/tests/meta/
  origin: spec-deferred 3b15334ee506 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-33-2: django-pyforge chrome base.html does not vendor htmx.min.js, so hx-* on the steward inventory section is markup-only until chrome loads HTMX.

- source_spec: `planning-artifacts/specs/spec-33-2-first-portal-slice-provision-inventory.md`
  summary: django-pyforge chrome base.html does not vendor htmx.min.js, so hx-* on the steward inventory section is markup-only until chrome loads HTMX.
  evidence: src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/base.html has theme.css and the switcher, not an HTMX script. Pre-existing; this story server-renders inventory on GET /stations/steward/.
  location: src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/base.html
  origin: spec-deferred a433e6cbb345 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-1-2: `keys.py`'s drift-detection **gate**-recognition heuristic (`_is_scope_gate`/`_is_env_presence_check`) misses several plausible-but-not-yet-seen gate spellings — `os.getenv(...)` instead of `os.environ.get(...)`, a negated presence check (`if not os.environ.get("X"): return ...`), and a compound condition (`if skip_auth and other: return ...`) — any of which would cause a real, innocuous future refactor of `_http.py` to be misclassified (false positive if the current real gate were rewritten with one of these spellings, or a genuine false negative for the compound case, since `_scan_function` stops scanning entirely once any `if`-with-`Return` is seen regardless of whether the condition is a single flag or a compound expression).

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md`
  summary: `keys.py`'s drift-detection **gate**-recognition heuristic (`_is_scope_gate`/`_is_env_presence_check`) misses several plausible-but-not-yet-seen gate spellings — `os.getenv(...)` instead of `os.environ.get(...)`, a negated presence check (`if not os.environ.get("X"): return ...`), and a compound condition (`if skip_auth and other: return ...`) — any of which would cause a real, innocuous future refactor of `_http.py` to be misclassified (false positive if the current real gate were rewritten with one of these spellings, or a genuine false negative for the compound case, since `_scan_function` stops scanning entirely once any `if`-with-`Return` is seen regardless of whether the condition is a single flag or a compound expression).
  evidence: Confirmed by hand-tracing `_is_scope_gate`/`_is_env_presence_check` in `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` against each of the three shapes (independent adversarial + edge-case review agents both found this, from different angles, during Story 1.2's review pass 2026-07-30). Explicitly out of this story's scope per its spec's own "Never: No general-purpose static-analysis framework — the detector targets this one defect shape, not a pluggable rule engine."
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-the-jfrog-leak-can-never-recur-silently.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-5-2: Story 5.2's guard only covers `steward deploy dashboard` (the manual/local operator CLI path) — the dashboard actually published to GitHub Pages is built by `.github/workflows/dashboard.yml` running `python docs/dashboard/generate.py --source git` directly on every push to `main` (plus a daily cron), which never invokes `steward` at all. `generate.py::apply_tracked_ledger` (the function that path calls) already silently `continue`s past a missing per-project ledger and only prints a warning for an empty one — so the published site's own "a missing ledger is silently invisible" gap remains open. This story's declared Surface was `deploy.py`, `tests/` only (Effort: XS); closing the CI path requires touching `docs/dashboard/generate.py`, which is repo-wide and shared by all 8 stations — explicitly out of this story's Never clause.

- source_spec: `_bmad-output/implementation-artifacts/spec-5-2-consume-the-sprint-ledger-never-derive-story-status.md`
  summary: Story 5.2's guard only covers `steward deploy dashboard` (the manual/local operator CLI path) — the dashboard actually published to GitHub Pages is built by `.github/workflows/dashboard.yml` running `python docs/dashboard/generate.py --source git` directly on every push to `main` (plus a daily cron), which never invokes `steward` at all. `generate.py::apply_tracked_ledger` (the function that path calls) already silently `continue`s past a missing per-project ledger and only prints a warning for an empty one — so the published site's own "a missing ledger is silently invisible" gap remains open. This story's declared Surface was `deploy.py`, `tests/` only (Effort: XS); closing the CI path requires touching `docs/dashboard/generate.py`, which is repo-wide and shared by all 8 stations — explicitly out of this story's Never clause.
  evidence: Confirmed by grepping every workflow/cron/hook in the repo for `steward` (zero hits) and reading `.github/workflows/dashboard.yml`'s invocation directly; `generate.py::apply_tracked_ledger`'s `if not ledger.is_file(): continue` (docs/dashboard/generate.py) reproduced against a missing-file case. Raised by Blind Hunter during Story 5.2's review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/3 present (absent: _bmad-output/implementation-artifacts/spec-5-2-consume-the-sprint-ledger-never-derive-story-status.md, docs/dashboard/generate.py); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-6-1: `provision.py`'s `_run_env`'s and `_run_runner`'s own unknown-value error paths (bad `--env` name, unknown `--runner` value) build a raw f-string `DutyResult.summary` directly instead of routing through `ProvisionDuty._render_error` — so `provision --env bogus --json` / `provision --runner bogus --json` still emit unparseable plain text on error, exactly the bug class `_render_error`'s own docstring calls out and that this story's new `--module` unknown-name path was written to avoid.

- source_spec: `_bmad-output/implementation-artifacts/spec-6-1-provision-module-name.md`
  summary: `provision.py`'s `_run_env`'s and `_run_runner`'s own unknown-value error paths (bad `--env` name, unknown `--runner` value) build a raw f-string `DutyResult.summary` directly instead of routing through `ProvisionDuty._render_error` — so `provision --env bogus --json` / `provision --runner bogus --json` still emit unparseable plain text on error, exactly the bug class `_render_error`'s own docstring calls out and that this story's new `--module` unknown-name path was written to avoid.
  evidence: Read directly in `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` — `_run_env`'s `summary=(f"provision --env: {name!r} is not a valid pixi environment...")` and `_run_runner`'s `summary=f"provision --runner: unknown runner {runner!r}..."` never check `ns.json`. Flagged by Blind Hunter during Story 6.1's review pass 2026-08-09. Pre-existing (Stories 3.1/3.2), not caused by this story, which only touches the new `--module` path.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-6-1-provision-module-name.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-6-2: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning/SPEC.md`'s frontmatter is stale: `status: draft` even though 2 of its 3 capabilities (CAP-1 via Story 6.1, CAP-2 via Story 6.2) are now shipped, and its own `open_questions` list still carries "Installed-vs-available state: new `.steward/` file... or derived from the filesystem?... deliberately unresolved" verbatim, even though Story 6.2 concretely resolved it (derived from the filesystem, no state file) — CLAUDE.md's "keep the spec's status current" rule is unmet. Pre-existing since Story 6.1 (which delivered CAP-1 without updating either field); this story's own Tasks list (matching Story 6.1's own precedent) only specified per-file `.memlog.md` `(change)` entries, not editing the parent SPEC.md's own frontmatter, so fixing this crosses into deciding how/when a capability-spec's status and open_questions should move as its child stories land incrementally — bigger than either story's own XS scope.

- source_spec: `_bmad-output/implementation-artifacts/spec-6-2-provision-list-modules.md`
  summary: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning/SPEC.md`'s frontmatter is stale: `status: draft` even though 2 of its 3 capabilities (CAP-1 via Story 6.1, CAP-2 via Story 6.2) are now shipped, and its own `open_questions` list still carries "Installed-vs-available state: new `.steward/` file... or derived from the filesystem?... deliberately unresolved" verbatim, even though Story 6.2 concretely resolved it (derived from the filesystem, no state file) — CLAUDE.md's "keep the spec's status current" rule is unmet. Pre-existing since Story 6.1 (which delivered CAP-1 without updating either field); this story's own Tasks list (matching Story 6.1's own precedent) only specified per-file `.memlog.md` `(change)` entries, not editing the parent SPEC.md's own frontmatter, so fixing this crosses into deciding how/when a capability-spec's status and open_questions should move as its child stories land incrementally — bigger than either story's own XS scope.
  evidence: Read directly in `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning/SPEC.md` frontmatter (`status: draft`, unresolved open_questions entry). Flagged by Blind Hunter during Story 6.2's review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-6-2-provision-list-modules.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1: `pyforge-container`'s composed env inherits test-only/GUI tooling (`kedro-viz`, `playwright`, `playwright-python` via the `pyforge-atlas` feature) into a headless runtime image, because no `pyforge-*` feature separates its runtime deps from its test-only deps — the same conflation exists identically in all eight per-station environments today, not introduced by this story's composition.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: `pyforge-container`'s composed env inherits test-only/GUI tooling (`kedro-viz`, `playwright`, `playwright-python` via the `pyforge-atlas` feature) into a headless runtime image, because no `pyforge-*` feature separates its runtime deps from its test-only deps — the same conflation exists identically in all eight per-station environments today, not introduced by this story's composition.
  evidence: `pixi list -e pyforge-container` in the built env shows `xorg-libx11`, `wayland`, `vizro`, `vizro-dash-components`, `uvicorn`, `websockets`, `watchdog`, etc.; each is declared in `pixi.toml`'s `[feature.pyforge-atlas.dependencies]` with its own comment marking it "TEST-ONLY... deliberately NOT package run-deps." Splitting test-only deps out of each station's feature is a cross-cutting pixi.toml restructure across all 8 stations, outside Story 7.1's `Containerfile`/`pixi.toml`-composition-only surface. Raised by Blind Hunter during Story 7.1's review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-2: The Story 7.1 runtime image has no `USER` directive and runs as root by default — a standard container-hardening gap not named in any planning artifact for this epic (the Spec's "rootless" language refers to Podman's rootless daemon mode, not the in-container process UID). Fixing it safely requires creating a non-root user, `chown`-ing `/pyforge`, and setting `HOME` for anything the composed env's activation scripts expect, then re-verifying the full build+`--version` loop — real work, not a one-line patch, and credential/security hardening for this image is already Story 7.3's named scope.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: The Story 7.1 runtime image has no `USER` directive and runs as root by default — a standard container-hardening gap not named in any planning artifact for this epic (the Spec's "rootless" language refers to Podman's rootless daemon mode, not the in-container process UID). Fixing it safely requires creating a non-root user, `chown`-ing `/pyforge`, and setting `HOME` for anything the composed env's activation scripts expect, then re-verifying the full build+`--version` loop — real work, not a one-line patch, and credential/security hardening for this image is already Story 7.3's named scope.
  evidence: `Containerfile`'s runtime stage (`FROM --platform=linux/amd64 ubuntu:24.04` onward) has no `USER` instruction; `docker run --rm --entrypoint id pyforge-guild-test2` would report uid=0. Raised by Blind Hunter during Story 7.1's review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-3: Version-resolution is inconsistent across the fleet — `steward`/`mason` resolve `__version__` dynamically via `importlib.metadata.version(...)` (immune to drift from `pyproject.toml`), while `atlas`/`scribe`/`warden`/`herald`/`doctor` hardcode a literal string in `__init__.py` with a "keep in sync by hand" comment. Pre-existing in all five stations' `__init__.py` since their own Story 1.1; this story only consumes the existing `__version__` values for atlas/scribe, it doesn't introduce new hardcoding.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: Version-resolution is inconsistent across the fleet — `steward`/`mason` resolve `__version__` dynamically via `importlib.metadata.version(...)` (immune to drift from `pyproject.toml`), while `atlas`/`scribe`/`warden`/`herald`/`doctor` hardcode a literal string in `__init__.py` with a "keep in sync by hand" comment. Pre-existing in all five stations' `__init__.py` since their own Story 1.1; this story only consumes the existing `__version__` values for atlas/scribe, it doesn't introduce new hardcoding.
  evidence: Read directly: `pyforge-atlas/src/pyforge/atlas/__init__.py:34` and `pyforge-scribe/src/pyforge/scribe/__init__.py:14` both hardcode `__version__ = "0.1.0"  # keep in sync ... by hand`, vs. `pyforge-steward`/`pyforge-mason`'s dynamic `importlib.metadata.version` resolution. Raised by Blind Hunter during Story 7.1's review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-4: The whole-Guild image ships no `git`, `gh`, `pixi` or `tmux` binary, so large parts of the stations it packages cannot actually run in-container — marshal (the default `CMD`) subprocess-wraps `git` throughout its worktree orchestration, and steward's `provision`/`deploy build` duties subprocess-wrap `pixi`, which the multi-stage build deliberately keeps out of the runtime stage. The image satisfies its three ACs (build, eight `--version`s, default `marshal`) and little beyond them.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: The whole-Guild image ships no `git`, `gh`, `pixi` or `tmux` binary, so large parts of the stations it packages cannot actually run in-container — marshal (the default `CMD`) subprocess-wraps `git` throughout its worktree orchestration, and steward's `provision`/`deploy build` duties subprocess-wrap `pixi`, which the multi-stage build deliberately keeps out of the runtime stage. The image satisfies its three ACs (build, eight `--version`s, default `marshal`) and little beyond them.
  evidence: `ls .pixi/envs/pyforge-container/bin | grep -E '^(git|gh|pixi|tmux)$'` returns nothing, and `docker run --rm ubuntu:24.04 command -v git` is empty, so neither the conda env nor the base image supplies them; `pyforge/marshal/adapters/vcs_git.py` shells out to `git -C … worktree add/list`, `merge-base`, `branch -D`, and `provision.py::materialize_environment` runs `["pixi", "install", "-e", name]`. Not patchable inside this story: the Spec's Always clause requires composing the eight existing `pyforge-*` features "verbatim … no new dependency curation", which adding `git`/`gh`/`tmux` would violate. Story 7.1's review pass added an explicit SCOPE block to the `Containerfile` naming this limit rather than leaving it implicit. Raised independently by both reviewers during Story 7.1's follow-up review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-5: The workspace's seven pixi-version pin sites do not agree, and nothing enforces them — `requires-pixi = ">=0.75.0"` plus `.github/workflows/dashboard.yml` and `.github/workflows/kedro-viz-publish.yml` (both exact `pixi-version: v0.76.2`) sit a minor below the three `feature.*` `pixi = ">=0.76.2"` pins and `environment.yaml`'s `pixi >=0.76.2`. The `requires-pixi` comment asserted they "match"; they have not since the 2026-07-30 `pixi update`.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: The workspace's seven pixi-version pin sites do not agree, and nothing enforces them — `requires-pixi = ">=0.75.0"` plus `.github/workflows/dashboard.yml` and `.github/workflows/kedro-viz-publish.yml` (both exact `pixi-version: v0.76.2`) sit a minor below the three `feature.*` `pixi = ">=0.76.2"` pins and `environment.yaml`'s `pixi >=0.76.2`. The `requires-pixi` comment asserted they "match"; they have not since the 2026-07-30 `pixi update`.
  evidence: `grep -n 'pixi = ">='  pixi.toml` → `>=0.76.1` at lines 34, 985, 1303; `environment.yaml:9` → `pixi >=0.76.2`; `pixi.toml:10` → `requires-pixi = ">=0.76.2"`; `grep -rn pixi-version .github/workflows/` → `dashboard.yml:66` and `kedro-viz-publish.yml:69`, both `v0.75.0`. `grep -rn "requires-pixi\|pixi-version" scripts/*.py` returns no hits, so no detector cross-checks them — a hand-maintained version fact guarded only by a prose comment, against this repo's own "derive, don't declare" rule. Pre-existing drift; Story 7.1 only appended a sixth site to the comment's enumeration (its review pass corrected the enumeration to seven and made the comment state the real, unequal values). Deciding whether to raise the floor to 0.76.1 or lower the feature pins is a workspace-wide call outside a container story. Raised by Blind Hunter during Story 7.1's follow-up review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 2/3 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-6: Neither `Containerfile` stage is digest-pinned — `ubuntu:24.04` is a floating tag that receives new content on every SRU, and `ghcr.io/prefix-dev/pixi:0.76.1` is likewise a mutable tag. The conda layer is guarded with care (`pixi install --frozen` against a committed lock) while the OS layer beneath it can change under the same Containerfile, so "one build, whole Guild" is not reproducible across time.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: Neither `Containerfile` stage is digest-pinned — `ubuntu:24.04` is a floating tag that receives new content on every SRU, and `ghcr.io/prefix-dev/pixi:0.76.1` is likewise a mutable tag. The conda layer is guarded with care (`pixi install --frozen` against a committed lock) while the OS layer beneath it can change under the same Containerfile, so "one build, whole Guild" is not reproducible across time.
  evidence: `Containerfile` lines `FROM --platform=linux/amd64 ghcr.io/prefix-dev/pixi:0.76.1 AS builder` and `FROM --platform=linux/amd64 ubuntu:24.04` carry no `@sha256:` digest. Adding digests means adopting a refresh policy (who re-pins, how often, and how security updates land) — image-supply-chain hardening, which is Story 7.3's named scope. Raised by Blind Hunter during Story 7.1's follow-up review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-7: The station CLI runs as PID 1 with no init and no signal handling, so `docker stop` stalls for the full grace period before SIGKILL — a Python process at PID 1 does not inherit the default SIGTERM disposition, and neither the entrypoint nor any station CLI registers a handler.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: The station CLI runs as PID 1 with no init and no signal handling, so `docker stop` stalls for the full grace period before SIGKILL — a Python process at PID 1 does not inherit the default SIGTERM disposition, and neither the entrypoint nor any station CLI registers a handler.
  evidence: `Containerfile`'s `ENTRYPOINT ["/entrypoint.sh"]` ends in `exec "$@"`, so the CLI replaces the shell at PID 1; no `tini`/`--init` is configured and no station CLI installs a SIGTERM handler. The fix (ship an init, or document `docker run --init`) is container-runtime hardening — Story 7.3's scope — and needs a re-verify of the full build. Raised by Edge Case Hunter during Story 7.1's follow-up review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-8: The image runs a package resolution that no test suite has ever executed — composing the eight station features into one environment re-solves the graph, so `pyforge-container` ships different versions than the per-station envs the tests run in, and there is no `pyforge-container` test or smoke task to cover the difference.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: The image runs a package resolution that no test suite has ever executed — composing the eight station features into one environment re-solves the graph, so `pyforge-container` ships different versions than the per-station envs the tests run in, and there is no `pyforge-container` test or smoke task to cover the difference.
  evidence: Verified directly: `.pixi/envs/pyforge-atlas/…/site-packages` carries `dagster-1.13.16.dist-info` while `.pixi/envs/pyforge-container/…` carries `dagster-1.13.17.dist-info`; the lock shows the same pattern for alembic (1.18.5 → 1.19.1), gitpython, dynaconf and nodejs. All eight `pyforge-*-test` pixi tasks run in the per-station envs, and `grep -n pyforge-container pixi.toml` hits only the comment block and the env line — no task. The Spec's comment that referencing features by name "tracks each station's deps automatically" holds for declared constraints but not for the resolved environment that actually ships. Adding a container-env gate is Story 7.5's build-time smoke-gate scope. Raised by Blind Hunter during Story 7.1's follow-up review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-9: `COPY . /pyforge` immediately precedes `RUN pixi install --frozen`, so any edit anywhere in the tree — a docstring in herald — invalidates the layer and re-runs the full install plus all eight source-package builds (~84s of install/export locally on a warm daemon).

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: `COPY . /pyforge` immediately precedes `RUN pixi install --frozen`, so any edit anywhere in the tree — a docstring in herald — invalidates the layer and re-runs the full install plus all eight source-package builds (~84s of install/export locally on a warm daemon).
  evidence: `Containerfile`'s builder stage orders `COPY . /pyforge` before `RUN pixi install`; the conventional split pixi's own documented container pattern uses (copy `pixi.toml` + `pixi.lock` and the member `pyproject.toml`s, install, then copy the tree) is absent, while the file's header comment claims to follow that pattern. Restructuring the copy order changes the build shape the Spec prescribes and needs a full rebuild + AC re-verify. Raised by Blind Hunter during Story 7.1's follow-up review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-10: Nothing keeps `.dockerignore` in step with `.gitignore`, so every future gitignored secret- or host-state-shaped root silently starts riding into the image. The two files encode the same judgement ("this is local machine state, not repo content") in two dialects with different matching semantics, and only one of them is enforced by anything.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: Nothing keeps `.dockerignore` in step with `.gitignore`, so every future gitignored secret- or host-state-shaped root silently starts riding into the image. The two files encode the same judgement ("this is local machine state, not repo content") in two dialects with different matching semantics, and only one of them is enforced by anything.
  evidence: Story 7.1's third review pass found six such roots the new `.dockerignore` missed, every one of them already named in `.gitignore` with its own justification: `/.herald/` (AD-5's repo-local bridge/etag store — the exact analogue of the `.steward/` entry the second pass added), `.claude/skills/data/`, `_bmad/custom/.active-project`, `_bmad/config.user.toml`, `_bmad/_memory/`, and `_bmad-output/projects/*/_root-fallback-fork-*`. It also found `.bmad-loop/` (11GB in the steward loop home, which is itself a full repo checkout and therefore a valid `docker build .` root) and the inverse failure — `**/*.log` swallowing `.claude/skills/conda-forge-expert/tests/fixtures/error_logs/unmatched.log`, the repo's only tracked `.log`, whose absence recreates the exact false-green `.gitignore` was patched to fix on 2026-08-09. All eight were patched by hand in that pass; the next `.gitignore` addition will diverge again the same way. The fix is a detector (`git ls-files` matched against `.dockerignore`, failing on any tracked file that would be stripped, plus a cross-check of `.gitignore`'s secret/state-shaped roots against `.dockerignore`) — new tooling with its own three-place wiring, not a container-story patch. Raised by Blind Hunter and Edge Case Hunter independently during Story 7.1's third review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/7 present (absent: .claude/skills/data/, _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md, _bmad-output/projects/*/_root-fallback-fork-*…); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-11: `bmad-drift-check`'s count-staleness rule only recognizes one phrasing of the pixi-env fact (`N pixi envs`), so the same fact written any other way drifts unchecked — and the feature count is not checked at all. Nine pyforge-marshal planning docs currently carry 32 stale occurrences while the detector reports `OK`.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: `bmad-drift-check`'s count-staleness rule only recognizes one phrasing of the pixi-env fact (`N pixi envs`), so the same fact written any other way drifts unchecked — and the feature count is not checked at all. Nine pyforge-marshal planning docs currently carry 32 stale occurrences while the detector reports `OK`.
  evidence: `scripts/bmad_drift_check.py:395` is `(r"(\d+)\s+pixi envs", gt["pixi_envs"], "pixi envs")` — a literal-phrase regex — and `FINGERPRINT_KEYS` (line 232) covers `pixi_envs` but has no feature-count key. Live counts are 20 envs / 21 features (`grep -oE '^\[feature\.[a-z0-9-]+' pixi.toml | sort -u | wc -l` → 21). Stale occurrences across `planning-artifacts/`: "17 features" ×18 (PRD, project-overview, epics-regenerable-factory, development-guide, source-tree-analysis, deployment-guide, index) and "18 envs"/"18 pixi environments" ×14 (PRD, epics-regenerable-factory, architecture, source-tree-analysis, index, integration-architecture, architecture-bmad-infra, project-overview, development-guide) — all invisible to the detector, which exits 0. Story 7.1's landing updated the six `N pixi envs` sites the detector does see; correcting the rest is a full SYNC-RUNBOOK reconciler pass, not a review patch, and must be done across all nine files at once: the PRD's own 2026-07-25 retro records that a partial re-grounding left the doc set "INTERNALLY INCONSISTENT, worse than uniformly stale", so fixing only the two files this story touched would reproduce that failure. Some occurrences sit inside `sync_lineage` retro prose (PRD, epics) that is historical record and must NOT be rewritten — another reason this needs the reconciler's judgement. Pair the doc fix with widening the detector (accept the phrasing variants; add a feature-count fingerprint) or it will drift again. Raised by Blind Hunter during Story 7.1's third review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-12: `herald deck status` reports an empty deck list at exit 0 whenever `presentations/` is absent, instead of failing loudly — inverting, in exactly the environment Story 7.1 creates, the guarantee its own docstring exists to provide.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: `herald deck status` reports an empty deck list at exit 0 whenever `presentations/` is absent, instead of failing loudly — inverting, in exactly the environment Story 7.1 creates, the guarantee its own docstring exists to provide.
  evidence: Verified in the built image: `docker run --rm pyforge-guild herald deck status` prints `[]` and exits 0, while the host checkout has 14 `presentations/<slug>/README.md`. `deck_pipeline.py:1090` guards the scan with `if presentations_dir.is_dir():`, so when the directory is missing the union silently collapses to whatever `state.known_slugs()` returns — and the docstring three lines above (1084-1087) states the opposite contract: "so an unseeded deck is reported as unlinked rather than silently omitted." Its sibling `herald deck seed` fails loudly (`deck_pipeline.py:192` raises `HeraldError`), so the surface is inconsistent with itself. Not patched in Story 7.1: the `presentations/` exclusion is correct on size (84MB) and settled by the third review pass, and changing herald's own code is barred by this story's Never clause ("Do not restructure any station's own code — every station's code is consumed as-is"). The fix belongs to herald: make the missing-directory case explicit (raise, or report the decks as unknown rather than absent) rather than let an empty result mean two different things. Raised by Blind Hunter during Story 7.1's fourth review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md, presentations/<slug>/README.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-1-13: `spec_surface_check.py` only validates tracked files *into* a surface, never surface entries *out* to the filesystem, so a `surface:` list can name a file that has never existed and the detector still reports OK.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md`
  summary: `spec_surface_check.py` only validates tracked files *into* a surface, never surface entries *out* to the filesystem, so a `surface:` list can name a file that has never existed and the detector still reports OK.
  evidence: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-unified-container/SPEC.md:8` declares `scripts/container-gates` in its governed surface; both `ls scripts/ | grep -i container` and `git ls-files scripts/ | grep -i container` return nothing, and `scripts/.spec-surface-baseline.json` holds three files for this spec (`.dockerignore`, `Containerfile`, `pixi.toml`) against a four-entry surface. `python3 scripts/spec_surface_check.py` reports `OK: every tracked file governed or allowlisted; no drift.` Benign in this instance — the file is Story 7.3/7.5's to write, so the entry is an intentional forward declaration — but the consequence is general: a surface list cannot be trusted as an inventory, and a typo'd or renamed path drops out of governance silently rather than failing. Pre-existing: the entry predates Story 7.1, which only added `.dockerignore` to this surface. The fix (warn on surface entries with no filesystem match, with an opt-out for deliberate forward declarations) is detector work, the same unenforced-claim class as the already-deferred `.dockerignore`/`.gitignore` drift entry. Raised by Blind Hunter during Story 7.1's fourth review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 3/4 present (absent: _bmad-output/implementation-artifacts/spec-7-1-one-build-whole-guild.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-2: `epics.md` and the tracked `sprint-status-ledger.yaml` still report Story 7.1 (already `done` per `sprint-status.yaml`) and Story 7.2 as `backlog`, even after both landed.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-2-the-repo-at-a-fixed-short-path.md`
  summary: `epics.md` and the tracked `sprint-status-ledger.yaml` still report Story 7.1 (already `done` per `sprint-status.yaml`) and Story 7.2 as `backlog`, even after both landed.
  evidence: `epics.md` (Story 7.1: `**Status:** backlog`, Story 7.2: `**Status:** backlog`) and `_bmad-output/planning-artifacts/sprint-status-ledger.yaml` (`7-1-one-build-whole-guild: backlog`, `7-2-the-repo-at-a-fixed-short-path: backlog`) both disagree with the Tier-3 `sprint-status.yaml`, which already has `7-1-one-build-whole-guild: done`. Not caused by this story: neither the `bmad-dev-auto` workflow's own step files nor Story 7.1's implementation touch either file, and `sprint-status-ledger.yaml`'s own header states it is regenerated by a separate `pixi run -e local-recipes sprint-ledger-sync` command, not hand-edited per-story. The fix is running that sync command (and, if `epics.md`'s own inline `Status:` lines are meant to track live state rather than a planning snapshot, a `bmad-correct-course`/`bmad-create-epics-and-stories` pass) after a story lands, not a change inside a dev-auto story's diff. Raised by Blind Hunter during Story 7.2's review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/implementation-artifacts/spec-7-2-the-repo-at-a-fixed-short-path.md, _bmad-output/planning-artifacts/sprint-status-ledger.yaml); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-2-2: `spec_surface_check.py`'s per-file reconciliation check scans the OWNING SPEC'S ENTIRE `.memlog.md` text for a changed file's literal path, not just the newly-added entry — so once a path is named anywhere in a memlog's history, any LATER unrelated memlog edit (one that moves the contract hash for a different reason entirely) makes every future change to that path look fully reconciled, with no `[drift]` and not even an informational `[drift-presumed]`.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-2-the-repo-at-a-fixed-short-path.md`
  summary: `spec_surface_check.py`'s per-file reconciliation check scans the OWNING SPEC'S ENTIRE `.memlog.md` text for a changed file's literal path, not just the newly-added entry — so once a path is named anywhere in a memlog's history, any LATER unrelated memlog edit (one that moves the contract hash for a different reason entirely) makes every future change to that path look fully reconciled, with no `[drift]` and not even an informational `[drift-presumed]`.
  evidence: `memlog_text()` (`scripts/spec_surface_check.py`) returns the whole file's raw text via `.read_text()`, and the per-file check is `elif f not in named: presumed.append(...)` — a substring test with no timestamp or entry boundary. `pyforge-steward/spec-unified-container`'s `.memlog.md` already names `Containerfile` in six separate entries (five from Story 7-1's passes, one added by this story's repair pass), so the path is now permanently a substring of its owning spec's memlog. Confirmed by reading the detector's own code, not merely argued; the gap already existed after Story 7-1's first entry named `Containerfile`, so this story's two-line repair did not introduce it. Documented as a deliberate simplification in the detector's own S-13.2 comment ("inferring reconciliation intent from prose would rebuild the presumed-reconciled blanket this replaces") — the fix (scope `named` to text added since the baseline's stamped memlog hash, not the whole file) is detector work. Raised by Edge Case Hunter during this story's repair-pass review 2026-08-09. Owner: `pyforge-marshal/spec-surface-drift-reconciliation` (the detector's own governing spec).
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-7-2-the-repo-at-a-fixed-short-path.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-2-3: `scripts/.spec-surface-baseline.json` is a single file shared across every spec; `--write-baseline --spec <name>` does an unlocked read-merge-write, so two concurrent scoped stamps (e.g. two parallel bmad-loop sessions reconciling different specs at once) can race and silently drop one invocation's just-written hashes.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-2-the-repo-at-a-fixed-short-path.md`
  summary: `scripts/.spec-surface-baseline.json` is a single file shared across every spec; `--write-baseline --spec <name>` does an unlocked read-merge-write, so two concurrent scoped stamps (e.g. two parallel bmad-loop sessions reconciling different specs at once) can race and silently drop one invocation's just-written hashes.
  evidence: `spec_surface_check.py`'s `--write-baseline` path reads the existing baseline file, merges only the named `--spec` entries into it, and writes the merge back with no file lock between read and write. Two processes each reading the pre-stamp baseline and writing their own merge would produce a last-writer-wins outcome that silently drops whichever ran first (self-correcting on the next run, since the dropped spec would reopen as `[no-baseline]`/`[drift]`, not silently corrupted forever — but with no error surfaced at write time). Theoretical under this repo's current usage (sequential dev-auto sessions); not exercised by this repair. Raised by Edge Case Hunter during this story's repair-pass review 2026-08-09. Owner: `pyforge-marshal/spec-surface-drift-reconciliation`.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-7-2-the-repo-at-a-fixed-short-path.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-3: `scripts/container-gates`'s aggregate `secrets-scan` summary ("FAILED -- see findings above") does not distinguish `steward keys audit --secrets` exiting 1 (`EXIT_FAILED`, a real finding) from any other nonzero exit (`EXIT_INTERNAL`=70 crash, `EXIT_USAGE`=2, `EXIT_INTERRUPTED`=130), so a build-tooling failure and a security finding both print the same banner.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-3-credentials-never-enter-image-layers.md`
  summary: `scripts/container-gates`'s aggregate `secrets-scan` summary ("FAILED -- see findings above") does not distinguish `steward keys audit --secrets` exiting 1 (`EXIT_FAILED`, a real finding) from any other nonzero exit (`EXIT_INTERNAL`=70 crash, `EXIT_USAGE`=2, `EXIT_INTERRUPTED`=130), so a build-tooling failure and a security finding both print the same banner.
  evidence: Confirmed by reading `steward`'s own `cli.py` exit-code contract (AD-8: `EXIT_OK=0, EXIT_FAILED=1, EXIT_USAGE=2, EXIT_INTERRUPTED=130, EXIT_INTERNAL=70`) against `container-gates`'s `_scan_target`, which only checks `returncode == 0`. Partially mitigated today: `steward`'s own `EXIT_INTERNAL` path prints a full traceback (visibly distinct from a `[secrets] ... matches ... pattern` finding line) to the same inherited stdout/stderr, so a human reading the build log can still tell the difference -- but `container-gates`'s own summary line cannot. Raised independently by both review agents in Story 7.3's review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-7-3-credentials-never-enter-image-layers.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-3-2: `scripts/container-gates secrets-scan`'s Containerfile invocation hardcodes three roots (`/pyforge`, `/shell-hook.sh`, `/entrypoint.sh`) that cover exactly what the Containerfile's final stage adds today; a future edit that `COPY`/`RUN`-writes new content elsewhere in that stage without also extending the gate's root list would ship unscanned.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-3-credentials-never-enter-image-layers.md`
  summary: `scripts/container-gates secrets-scan`'s Containerfile invocation hardcodes three roots (`/pyforge`, `/shell-hook.sh`, `/entrypoint.sh`) that cover exactly what the Containerfile's final stage adds today; a future edit that `COPY`/`RUN`-writes new content elsewhere in that stage without also extending the gate's root list would ship unscanned.
  evidence: Confirmed by reading the full final stage of `Containerfile` -- `WORKDIR`, two `COPY --from=builder`, the `RUN printf > /entrypoint.sh`, and the gate `RUN` itself are the only content-adding instructions, so the three roots are complete for the CURRENT file, but nothing enforces that a later addition also updates the gate. Raised by one review agent (edge-case hunter) in Story 7.3's review pass 2026-08-09; low urgency because the gate step is co-located in the same file as any instruction that would need to extend it, making the omission visible to a reviewer editing `Containerfile` directly.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-3-credentials-never-enter-image-layers.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-4: `tests/scripts/test_container_volumes_roundtrip.py` isn't named in `spec-unified-container`'s `SPEC.md` `surface:` list or tracked in `.spec-surface-baseline.json`'s per-file hashes -- it only passes coverage via the blanket `tests/**` entry in `scripts/spec_surface_allowlist.txt`, whose own comment ("inherited staged-recipes lint tests (upstream-owned shape)") describes an unrelated category, not this story-specific, this-repo-authored regression suite. The same gap already exists for Story 7.2's `tests/packaging/test_containerfile_checkout_path.py` (its own memlog entry explicitly notes "not this Spec's surface"), so this is a pre-existing, repeating pattern rather than something this story introduced.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-4-state-outlives-the-container.md`
  summary: `tests/scripts/test_container_volumes_roundtrip.py` isn't named in `spec-unified-container`'s `SPEC.md` `surface:` list or tracked in `.spec-surface-baseline.json`'s per-file hashes -- it only passes coverage via the blanket `tests/**` entry in `scripts/spec_surface_allowlist.txt`, whose own comment ("inherited staged-recipes lint tests (upstream-owned shape)") describes an unrelated category, not this story-specific, this-repo-authored regression suite. The same gap already exists for Story 7.2's `tests/packaging/test_containerfile_checkout_path.py` (its own memlog entry explicitly notes "not this Spec's surface"), so this is a pre-existing, repeating pattern rather than something this story introduced.
  evidence: Confirmed by reading `scripts/spec_surface_check.py`'s coverage logic (a file is governed OR allowlisted, with no third "adjacent, unowned test" category) and `scripts/spec_surface_allowlist.txt` line 47's comment. Because `tests/**` is a coverage-only allowlist entry (not a governed surface), a future change to this test file's assertions can drift arbitrarily far from what the Containerfile/`container-gates` diff actually does without `spec_surface_check.py` ever flagging it. Raised by Blind Hunter in Story 7.4's repair-pass review 2026-08-09. Owner: `pyforge-marshal/spec-surface-drift-reconciliation` (or the allowlist itself, if a narrower `tests/scripts/**`-vs-`tests/`-inherited split is preferred).
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 4/7 present (absent: _bmad-output/implementation-artifacts/spec-7-4-state-outlives-the-container.md, tests/**, tests/scripts/**); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-4-2: `scripts/container-gates`'s `_MOUNT_PATH_RE` (`^/[^:\x00]*$`) accepts a bare `/` and paths containing `..` segments as valid `--mount` values -- neither is rejected upfront the way a `:` or NUL byte is, and no test in `tests/scripts/test_container_volumes_roundtrip.py` exercises either.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-4-state-outlives-the-container.md`
  summary: `scripts/container-gates`'s `_MOUNT_PATH_RE` (`^/[^:\x00]*$`) accepts a bare `/` and paths containing `..` segments as valid `--mount` values -- neither is rejected upfront the way a `:` or NUL byte is, and no test in `tests/scripts/test_container_volumes_roundtrip.py` exercises either.
  evidence: Confirmed by reading the regex and the full test file -- no test passes `/` or a `..`-containing value. Low practical risk today: `volumes-roundtrip` is only ever invoked (per the story's own Verification section and the Containerfile's `VOLUME` line) against the three fixed CAP-4 paths by a trusted operator, not attacker-controlled input, and `docker run -v <vol>:/` mounts an empty named volume at the container's root rather than doing anything to the host. Raised by Blind Hunter in Story 7.4's repair-pass review 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 2/3 present (absent: _bmad-output/implementation-artifacts/spec-7-4-state-outlives-the-container.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-4-3: `test_no_volume_is_leaked_after_a_run`'s `_our_volumes()` helper scopes its before/after diff to the `container-gates-roundtrip-` name prefix (not the full daemon-wide `docker volume ls`), which fixes the same-repo concurrent-worktree false-positive the story's own review pass already caught -- but it still diffs by PREFIX, not by this-invocation's own exact volume names, so a concurrently-running invocation of the same test file (e.g. under `pytest-xdist -n auto`, a repo-wide pixi dependency, even though this story's own `pyforge-steward-container-volumes-test` task doesn't pass `-n`) sharing the same prefix could still produce a false leak reading.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-4-state-outlives-the-container.md`
  summary: `test_no_volume_is_leaked_after_a_run`'s `_our_volumes()` helper scopes its before/after diff to the `container-gates-roundtrip-` name prefix (not the full daemon-wide `docker volume ls`), which fixes the same-repo concurrent-worktree false-positive the story's own review pass already caught -- but it still diffs by PREFIX, not by this-invocation's own exact volume names, so a concurrently-running invocation of the same test file (e.g. under `pytest-xdist -n auto`, a repo-wide pixi dependency, even though this story's own `pyforge-steward-container-volumes-test` task doesn't pass `-n`) sharing the same prefix could still produce a false leak reading.
  evidence: Confirmed by reading `_our_volumes()` and `pyforge-steward-container-volumes-test`'s `cmd = "pytest tests/scripts/test_container_volumes_roundtrip.py -q"` (no `-n` flag) -- not hit under the task as shipped, only under a manual xdist-parallel invocation nobody currently makes. `pytest-xdist>=3.8.0` is pinned in `pixi.toml`'s dependency list repo-wide. Raised by Blind Hunter in Story 7.4's repair-pass review 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-4-state-outlives-the-container.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-5: `spec-unified-container`'s `SPEC.md` still names `steward provision --verify` as part of CAP-5's build-time gate ("image smoke gates run `steward provision --verify` plus each station CLI's `--help`"), but the canonical, more-recently-updated `epics.md`/PRD FR-26 (2026-08-02, predating this story) narrowed the AC to exactly what Story 7.5 implements — a per-CLI `--help` smoke check plus a documented start-up budget — and omits `provision --verify` entirely. This story deliberately implements the canonical FR-26/epics.md text, not SPEC.md's older, broader CAP-5 prose, but SPEC.md itself was never updated to reflect that narrowing.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-5-the-image-proves-itself-at-build-time.md`
  summary: `spec-unified-container`'s `SPEC.md` still names `steward provision --verify` as part of CAP-5's build-time gate ("image smoke gates run `steward provision --verify` plus each station CLI's `--help`"), but the canonical, more-recently-updated `epics.md`/PRD FR-26 (2026-08-02, predating this story) narrowed the AC to exactly what Story 7.5 implements — a per-CLI `--help` smoke check plus a documented start-up budget — and omits `provision --verify` entirely. This story deliberately implements the canonical FR-26/epics.md text, not SPEC.md's older, broader CAP-5 prose, but SPEC.md itself was never updated to reflect that narrowing.
  evidence: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-unified-container/SPEC.md:70-73` vs. `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`'s Story 7.5 AC and the PRD's FR-26 (both: "missing, unimportable, or over its documented start-up budget", no `provision --verify` mention). A repo-wide grep confirms `provision --verify` is wired nowhere in `Containerfile`/`scripts/container-gates`. Mirrors the FR-25-vs-CAP-4 prose reconciliation Story 7.4's own Design Notes already had to perform explicitly for a different capability; this one wasn't caught before implementation. Raised by Blind Hunter during Story 7.5's review pass 2026-08-09. Owner: `spec-unified-container`'s memlog reconciliation (update CAP-5's own text, or add a reconciliation note, the same way FR-25/CAP-4 was resolved).
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 3/4 present (absent: _bmad-output/implementation-artifacts/spec-7-5-the-image-proves-itself-at-build-time.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-5-2: The eight-station list `container-gates cli-smoke`'s Containerfile `RUN` line names by hand is not tied to `pixi.toml`'s own `pyforge-container` environment composition (`[environments] pyforge-container = { features = [...8 features...] }`) by anything automated — a station added to that composed environment would silently get no smoke coverage until someone remembers to also extend the Containerfile's `RUN` line (removal is at least loud: the build would fail with "not found on PATH" for the stale name). Matches this repo's own named "derive, don't declare" anti-pattern, and mirrors the identical pre-existing pattern in `secrets-scan`'s explicit root list and `volumes-roundtrip`'s explicit mount list — this story's design followed established precedent rather than introducing a new gap.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-5-the-image-proves-itself-at-build-time.md`
  summary: The eight-station list `container-gates cli-smoke`'s Containerfile `RUN` line names by hand is not tied to `pixi.toml`'s own `pyforge-container` environment composition (`[environments] pyforge-container = { features = [...8 features...] }`) by anything automated — a station added to that composed environment would silently get no smoke coverage until someone remembers to also extend the Containerfile's `RUN` line (removal is at least loud: the build would fail with "not found on PATH" for the stale name). Matches this repo's own named "derive, don't declare" anti-pattern, and mirrors the identical pre-existing pattern in `secrets-scan`'s explicit root list and `volumes-roundtrip`'s explicit mount list — this story's design followed established precedent rather than introducing a new gap.
  evidence: `pixi.toml:414`'s `pyforge-container` environment composition vs. `Containerfile`'s new `cli-smoke` `RUN` line, both hand-maintained independently with no cross-check. Raised by Blind Hunter during Story 7.5's review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-7-5-the-image-proves-itself-at-build-time.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-7-5-3: None of the three container-gates build-time/post-build gates (Story 7.3's `secrets-scan`, 7.4's `volumes-roundtrip`, 7.5's `cli-smoke`) has a test that parses the actual `Containerfile` to confirm its corresponding `RUN`/`VOLUME` line is still present — all test coverage lives at the `container-gates` script level, so a future edit that deletes or comments out any of the three gate instructions would be invisible to the whole test suite, undermining the shared premise ("the build proves it, not a human") all three stories state.

- source_spec: `_bmad-output/implementation-artifacts/spec-7-5-the-image-proves-itself-at-build-time.md`
  summary: None of the three container-gates build-time/post-build gates (Story 7.3's `secrets-scan`, 7.4's `volumes-roundtrip`, 7.5's `cli-smoke`) has a test that parses the actual `Containerfile` to confirm its corresponding `RUN`/`VOLUME` line is still present — all test coverage lives at the `container-gates` script level, so a future edit that deletes or comments out any of the three gate instructions would be invisible to the whole test suite, undermining the shared premise ("the build proves it, not a human") all three stories state.
  evidence: Confirmed by reading `tests/scripts/test_container_gates.py`, `tests/scripts/test_container_volumes_roundtrip.py`, and the new `tests/scripts/test_container_cli_smoke.py` — none references `Containerfile` at all. Pre-existing since Story 7.3 (the first gate), surfaced incidentally during Story 7.5's review pass rather than introduced by it. Raised by Blind Hunter during Story 7.5's review pass 2026-08-09.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 3/4 present (absent: _bmad-output/implementation-artifacts/spec-7-5-the-image-proves-itself-at-build-time.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1: `sync.py`'s GitHub Projects V2 GraphQL query (`fieldValues(first: 50)`) has no pagination — a board item with more than 50 custom field values could have its configured status/link/sync-point field fall outside the first page and silently read as absent, indistinguishable from "no value set."

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: `sync.py`'s GitHub Projects V2 GraphQL query (`fieldValues(first: 50)`) has no pagination — a board item with more than 50 custom field values could have its configured status/link/sync-point field fall outside the first page and silently read as absent, indistinguishable from "no value set."
  evidence: Confirmed by reading `_GET_PROJECT_ITEM_QUERY`'s single `fieldValues(first: 50)` block in `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` with no `pageInfo`/`after` cursor handling anywhere in `get_project_item`. Already identified as `[low][defer]` in this same story's own Review Triage Log, Pass 1 and Pass 2, but never actually appended to this ledger because both passes were moot under the workflow's cascading rule (a higher-priority `bad_spec`/`intent_gap` finding took priority each time). Independently re-raised by Blind Hunter in this story's Review Pass 3. Owner: `pyforge-steward` — needs real GraphQL cursor pagination, not a trivial patch.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-2: If `.steward/sync-config.yaml`'s `github.status_field_id` (or `link_field_id`/`sync_point_field_id`) is pointed at GitHub's native single-select "Status" field instead of a plain TEXT field, `get_project_item`'s GraphQL fragment (`... on ProjectV2ItemFieldTextValue`) simply doesn't match and the field reads as `None` — indistinguishable from "no value set" — surfacing later as a confusing "no transition to status None" error rather than a clear field-type diagnostic.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: If `.steward/sync-config.yaml`'s `github.status_field_id` (or `link_field_id`/`sync_point_field_id`) is pointed at GitHub's native single-select "Status" field instead of a plain TEXT field, `get_project_item`'s GraphQL fragment (`... on ProjectV2ItemFieldTextValue`) simply doesn't match and the field reads as `None` — indistinguishable from "no value set" — surfacing later as a confusing "no transition to status None" error rather than a clear field-type diagnostic.
  evidence: Confirmed by reading `_GET_PROJECT_ITEM_QUERY`'s single `... on ProjectV2ItemFieldTextValue` fragment in `sync.py` — no `... on ProjectV2ItemFieldSingleSelectValue` fragment exists to detect the mismatch. The example config (`.steward/sync-config.example.yaml`) already documents the TEXT-field requirement prominently, so this is a diagnostics gap, not a silent-failure gap an operator has no warning about. Raised by Blind Hunter in this story's Review Pass 3. Fixing it properly needs a new GraphQL fragment plus a design decision on the error message, more than a trivial patch.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/3 present (absent: .steward/sync-config.yaml, _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-3: No GitHub/Jira API call in `sync.py` has rate-limit/backoff/retry handling — any `status >= 400` (including a transient 403/429) is treated as an unconditional hard failure, with no defense against secondary rate limits once real per-item iteration (a separate, already-documented TODO in the workflow templates) is wired up and a scheduled run starts iterating many items per tick.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: No GitHub/Jira API call in `sync.py` has rate-limit/backoff/retry handling — any `status >= 400` (including a transient 403/429) is treated as an unconditional hard failure, with no defense against secondary rate limits once real per-item iteration (a separate, already-documented TODO in the workflow templates) is wired up and a scheduled run starts iterating many items per tick.
  evidence: Confirmed by reading `_default_transport`, `github_graphql_request`, `get_jira_issue`, and `transition_jira_issue` — every one raises `SyncAPIError` on the first non-2xx/3xx status with no retry loop. Consistent with (broadens the scope of) this story's own already-accepted Review Triage Log finding "Three sequential HTTP writes per convergence instead of batched/aliased GraphQL calls — a latency/rate-limit cost, not a correctness bug." This repo has a prior, unrelated incident with GitHub secondary rate limits under burst fanout (`project_phase_k_secondary_rate_limit`), which is why this is worth tracking rather than dismissing. Raised by Blind Hunter in this story's Review Pass 3.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-4: `SyncConfig.user_mapping`'s values (documented as GitHub login -> Jira `accountId`, both strings) aren't type-checked by `load_config` — only that the top-level `user_mapping` value is a mapping. A malformed entry (e.g. a non-string `accountId`) loads successfully.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: `SyncConfig.user_mapping`'s values (documented as GitHub login -> Jira `accountId`, both strings) aren't type-checked by `load_config` — only that the top-level `user_mapping` value is a mapping. A malformed entry (e.g. a non-string `accountId`) loads successfully.
  evidence: Confirmed by reading `load_config`'s `user_mapping` handling in `sync.py` — `isinstance(user_mapping, dict)` is the only check; individual keys/values pass through unchecked. Low current impact: the architecture's own Deferred section already marks assignee-sync (the only consumer of `user_mapping`) as future work, so this field is loaded but never read by `reconcile` in this story. Raised by Blind Hunter in this story's Review Pass 3.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-5: `sync.py`'s GitHub GraphQL client hardcodes `_GITHUB_API_HOST = "api.github.com"`/`_GITHUB_GRAPHQL_URL` instead of calling `_http.py`'s existing `resolve_github_api_urls(path_suffix)`, which was already built for exactly this purpose (its own docstring: "GitHub API host (`api.github.com`) — both REST and GraphQL", with a `GITHUB_API_BASE_URL` env override for GitHub Enterprise Server) — so the new sync duty silently loses enterprise/air-gap routing every other GitHub-facing code path in this repo gets for free.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: `sync.py`'s GitHub GraphQL client hardcodes `_GITHUB_API_HOST = "api.github.com"`/`_GITHUB_GRAPHQL_URL` instead of calling `_http.py`'s existing `resolve_github_api_urls(path_suffix)`, which was already built for exactly this purpose (its own docstring: "GitHub API host (`api.github.com`) — both REST and GraphQL", with a `GITHUB_API_BASE_URL` env override for GitHub Enterprise Server) — so the new sync duty silently loses enterprise/air-gap routing every other GitHub-facing code path in this repo gets for free.
  evidence: Confirmed by reading `resolve_github_api_urls` in `.claude/skills/conda-forge-expert/scripts/_http.py` (exists, documented, unused by `sync.py`) against `sync.py`'s own `_GITHUB_API_HOST`/`_GITHUB_GRAPHQL_URL` module constants. Violates this story's own governing SPEC's AD-1 ("A duty module containing its own copy of logic that already exists elsewhere in this repo is a review-blocking finding") and AD-9 ("any new outbound HTTP endpoint Steward introduces is added as one new row to `_http.py`'s existing `resolve_*_urls` convention") — `spec-pyforge-steward/SPEC.md`, both already-existing constraints, not new ones added by this repair. The parallel claim for `jira_base_url` does NOT hold (no existing `_http.py` row exists for Jira, and the story's own frozen `<intent-contract>` explicitly designs it as an operator-declared `SyncConfig` field since each Jira Cloud tenant has a different hostname, unlike GitHub's single fixed public host) — only the GitHub-side finding survived verification. Raised by Blind Hunter in this story's post-implementation verification-repair review pass 2026-08-10.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-6: `spec-jira-github-projects-sync/SPEC.md`'s frontmatter comment and body still assert `surface: []  # frontier — no sync code, workflow, or Jira/Projects integration exists anywhere in this repo yet (verified by grep 2026-08-08)` — now factually stale since this story shipped `sync.py`, its tests, the workflow templates, and `.steward/sync-config.example.yaml`. `surface: []` staying empty is architecturally fine (the files are correctly governed by `spec-pyforge-steward`'s package-path and `.steward/*` globs instead), but the "no sync code exists yet" prose claim is no longer true and should be corrected.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: `spec-jira-github-projects-sync/SPEC.md`'s frontmatter comment and body still assert `surface: []  # frontier — no sync code, workflow, or Jira/Projects integration exists anywhere in this repo yet (verified by grep 2026-08-08)` — now factually stale since this story shipped `sync.py`, its tests, the workflow templates, and `.steward/sync-config.example.yaml`. `surface: []` staying empty is architecturally fine (the files are correctly governed by `spec-pyforge-steward`'s package-path and `.steward/*` globs instead), but the "no sync code exists yet" prose claim is no longer true and should be corrected.
  evidence: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync/SPEC.md`'s frontmatter (still dated/worded as of 2026-08-08, ~44 minutes before this story's implementation commit `b1048105be`) vs. the actual shipped `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` and sibling files. Raised by Blind Hunter in this story's post-implementation verification-repair review pass 2026-08-10.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 3/5 present (absent: .steward/*, _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-7: `spec-pyforge-steward/SPEC.md`'s "Config file location" constraint claims the whole `.steward/` dotdir is "tracked (not gitignored, ...)", but this story's own frozen Code Map deliberately adds the operator's real `.steward/sync-config.yaml` to `.gitignore` (keeping only `sync-config.example.yaml` tracked, mirroring `.env.example`/`.env`) — a real, narrow exception to that constraint's literal wording that the prose doesn't yet carve out.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: `spec-pyforge-steward/SPEC.md`'s "Config file location" constraint claims the whole `.steward/` dotdir is "tracked (not gitignored, ...)", but this story's own frozen Code Map deliberately adds the operator's real `.steward/sync-config.yaml` to `.gitignore` (keeping only `sync-config.example.yaml` tracked, mirroring `.env.example`/`.env`) — a real, narrow exception to that constraint's literal wording that the prose doesn't yet carve out.
  evidence: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md`'s Constraints section vs. `.gitignore`'s `.steward/sync-config.yaml` entry (added by this story's own already-committed, already-reviewed implementation, predating this repair pass). Raised by Blind Hunter in this story's post-implementation verification-repair review pass 2026-08-10.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/3 present (absent: .steward/sync-config.yaml, _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-8: No detector semantically verifies the `sync` duty's actual AD-1..AD-9 (from `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md`) compliance — `spec-pyforge-steward`'s surface/memlog machinery only tracks file-level hash drift for files landing under its own package-path and `.steward/*` globs, not cross-spec architectural/behavioral compliance for a capability whose intent is authored entirely by a sibling spec (`spec-jira-github-projects-sync`, `surface: []`) but whose code physically lives under this spec's surface.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: No detector semantically verifies the `sync` duty's actual AD-1..AD-9 (from `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md`) compliance — `spec-pyforge-steward`'s surface/memlog machinery only tracks file-level hash drift for files landing under its own package-path and `.steward/*` globs, not cross-spec architectural/behavioral compliance for a capability whose intent is authored entirely by a sibling spec (`spec-jira-github-projects-sync`, `surface: []`) but whose code physically lives under this spec's surface.
  evidence: Read `scripts/spec_surface_check.py` in full — its drift model is a per-file content hash vs. the spec's memlog-hash "did the contract move" signal, with no semantic/behavioral check of any kind. Corroborated independently by both Blind Hunter (capability-gap framing) and Edge Case Hunter (`sync.py`'s behavior changes; owning spec-jira-github-projects-sync surface stays empty — no detector can ever catch drift against the sync duty's actual behavioral contract) in this story's post-implementation verification-repair review pass 2026-08-10. Worth a focused design pass on cross-spec capability-drift tracking generally, not specific to this one story.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/3 present (absent: .steward/*, _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-9: Whether GitHub's real `updateProjectV2ItemFieldValue` mutation treats an explicit `value: {"text": null}` as "clear the field" (versus silently ignoring it, rejecting it, or requiring a separate `clearProjectV2ItemFieldValue` mutation) is unverified against a live board — `FakeTransport` accepts any value, so the new "field cleared, propagate the explicit null" test (`test_field_cleared_on_jira_side_is_a_genuine_change_pushed_to_github`) proves the reconcile-side decision logic but not that the resulting GitHub write actually achieves a clear against the real API.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: Whether GitHub's real `updateProjectV2ItemFieldValue` mutation treats an explicit `value: {"text": null}` as "clear the field" (versus silently ignoring it, rejecting it, or requiring a separate `clearProjectV2ItemFieldValue` mutation) is unverified against a live board — `FakeTransport` accepts any value, so the new "field cleared, propagate the explicit null" test (`test_field_cleared_on_jira_side_is_a_genuine_change_pushed_to_github`) proves the reconcile-side decision logic but not that the resulting GitHub write actually achieves a clear against the real API.
  evidence: Confirmed by reading `update_project_item_field` (passes `value` straight through with no null-specific handling) and the test's own fixture, which uses a fake transport with no real-API validation. This is the same class of live-API unknown the story's own Verification section already accepts for the whole feature ("no live GitHub Projects V2 board and no live Jira Cloud project" in this environment) — this entry narrows it to the one specific mutation shape most likely to behave unexpectedly. Raised by Blind Hunter during this story's review pass 2026-08-10.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-10: `_GITHUB_BASELINE_FIELD_CEILING = 1024` is an explicitly unverified placeholder (no public GitHub Projects V2 text-field character limit was found by search) — if GitHub's real limit is lower, a baseline write that should fail with the clean, named `SyncBaselineTooLargeError` this mechanism exists to produce instead fails with whatever raw `SyncAPIError` `update_project_item_field` raises from a rejected/garbled response, indistinguishable in the returned summary from any other malformed-response failure, and arriving after the cross-system value push has already completed.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: `_GITHUB_BASELINE_FIELD_CEILING = 1024` is an explicitly unverified placeholder (no public GitHub Projects V2 text-field character limit was found by search) — if GitHub's real limit is lower, a baseline write that should fail with the clean, named `SyncBaselineTooLargeError` this mechanism exists to produce instead fails with whatever raw `SyncAPIError` `update_project_item_field` raises from a rejected/garbled response, indistinguishable in the returned summary from any other malformed-response failure, and arriving after the cross-system value push has already completed.
  evidence: The constant's own in-code comment already documents the uncertainty; confirmed no stronger public documentation exists via web search 2026-08-10 (GitHub's GraphQL reference and community discussions were both checked). Raised by Blind Hunter during this story's review pass 2026-08-10. Re-verify against a live board once one exists (same class as the story's other live-board-only unknowns).
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-1-11: If the two sides' baseline maps ever disagree with each other for the SAME field (e.g. from the already-accepted value-write/baseline-write non-atomicity: a real push succeeds but only one side's baseline refresh completes before a failure), `reconcile` cannot detect or repair it — it only ever compares each side's current value against ITS OWN baseline, never cross-checks the two baselines against each other. A pair whose baselines silently diverged this way would read as a permanently "healthy" no-op on every future reconcile even while GitHub and Jira actually disagree, because "neither side differs from its own baseline" is satisfied on both sides independently.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: If the two sides' baseline maps ever disagree with each other for the SAME field (e.g. from the already-accepted value-write/baseline-write non-atomicity: a real push succeeds but only one side's baseline refresh completes before a failure), `reconcile` cannot detect or repair it — it only ever compares each side's current value against ITS OWN baseline, never cross-checks the two baselines against each other. A pair whose baselines silently diverged this way would read as a permanently "healthy" no-op on every future reconcile even while GitHub and Jira actually disagree, because "neither side differs from its own baseline" is satisfied on both sides independently.
  evidence: Traced by hand against `reconcile`'s decision logic (`sync.py`, the `gh_changed`/`jira_changed` computation) — there is no code path that ever compares `gh.status` to `jira.status` except downstream of already deciding at least one side "changed". This is the specific self-reinforcing consequence of the value-write/baseline-write non-atomicity this story's own Design Notes and `reconcile`'s in-code comment already accept as a known, undefended risk (same class as `keys.rotate_identity`'s documented partial-completion state) — recorded in this story's Review Triage Log as `[medium][defer]` across multiple passes but never actually appended to this ledger until now. Raised by Edge Case Hunter during this story's review pass 2026-08-10.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-2: This story's N-round-trip zero-loop tests cover only single-change scenarios (GH-initiated, Jira-initiated, converged-same-value, and the baseline-refresh-failure path) per the frozen intent-contract's explicit "exactly one human-made change" scope — the real AD-4 conflict path (both sides genuinely diverge from their baseline to DIFFERENT values) has a single-round test (`test_real_conflict_github_wins_by_default_per_ad4`, `test_real_conflict_honors_field_overrides_jira_wins`) but no N-round-trip companion proving that after GitHub (or Jira, under `field_overrides`) "wins" once, repeated ticks don't keep re-asserting authority.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md`
  summary: This story's N-round-trip zero-loop tests cover only single-change scenarios (GH-initiated, Jira-initiated, converged-same-value, and the baseline-refresh-failure path) per the frozen intent-contract's explicit "exactly one human-made change" scope — the real AD-4 conflict path (both sides genuinely diverge from their baseline to DIFFERENT values) has a single-round test (`test_real_conflict_github_wins_by_default_per_ad4`, `test_real_conflict_honors_field_overrides_jira_wins`) but no N-round-trip companion proving that after GitHub (or Jira, under `field_overrides`) "wins" once, repeated ticks don't keep re-asserting authority.
  evidence: Independently raised by both Blind Hunter (`bmad-review-adversarial-general`) and Edge Case Hunter (`bmad-review-edge-case-hunter`) during this story's review pass 1, from separate, context-isolated review angles. Confirmed against `sync.py:790-797`'s AD-4 conflict-authority branch and the existing single-round conflict tests in `test_sync_reconcile_propagation.py`. Out of this story's frozen scope (its `<intent-contract>` Approach names exactly three single-change scenarios), so not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-2-2: None of this story's N-round-trip tests alternate which identifier (`github_item_id` vs. `jira_issue_key`) is used to re-enter `reconcile()` across rounds — every round in every test re-enters via the SAME identifier used in round 1. The real-world echo scenario CAP-2 defends against is a webhook firing from the side that was just written to, i.e. after `push_to_jira`, a more faithful simulation of "did our own write trigger a bounce-back" is a subsequent call keyed by `jira_issue_key`, not another call keyed by the original `github_item_id`.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md`
  summary: None of this story's N-round-trip tests alternate which identifier (`github_item_id` vs. `jira_issue_key`) is used to re-enter `reconcile()` across rounds — every round in every test re-enters via the SAME identifier used in round 1. The real-world echo scenario CAP-2 defends against is a webhook firing from the side that was just written to, i.e. after `push_to_jira`, a more faithful simulation of "did our own write trigger a bounce-back" is a subsequent call keyed by `jira_issue_key`, not another call keyed by the original `github_item_id`.
  evidence: Raised by Edge Case Hunter (and independently, in weaker form, by Blind Hunter) during this story's review pass 1. Both reviewers confirmed the tests don't lose correctness on this point (both entry points read identical fresh state per AD-9's unconditional re-read), so this is a coverage gap, not a known defect. Out of this story's frozen scope (its `<intent-contract>` Boundaries specify only "the SAME FakeTransport instance across all N calls", not identifier consistency), so not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-2-3: No N-round-trip zero-loop test exists for the field-cleared-push scenario (`target_value=None`, exercised single-round by `test_field_cleared_on_jira_side_is_a_genuine_change_pushed_to_github`) — unproven that repeated ticks after a field is explicitly cleared on one side stay true no-ops.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md`
  summary: No N-round-trip zero-loop test exists for the field-cleared-push scenario (`target_value=None`, exercised single-round by `test_field_cleared_on_jira_side_is_a_genuine_change_pushed_to_github`) — unproven that repeated ticks after a field is explicitly cleared on one side stay true no-ops.
  evidence: Raised by Edge Case Hunter during this story's review pass 1. Confirmed the existing single-round test covers only the decision logic, not repeated-tick stability. Out of this story's frozen scope (the `<intent-contract>` I/O & Edge-Case Matrix names exactly three scenarios, not this one), so not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-2-4: No N-round-trip zero-loop test exists for the first-link (never-synced) scenario (exercised single-round by `test_first_link_no_baseline_and_differing_values_ad4_decides_and_writes_both_baselines`) — arguably the highest-risk moment for a loop (the baseline didn't exist a moment ago), yet unproven that ticks 2-N stay quiet once the first-ever baseline is in place.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md`
  summary: No N-round-trip zero-loop test exists for the first-link (never-synced) scenario (exercised single-round by `test_first_link_no_baseline_and_differing_values_ad4_decides_and_writes_both_baselines`) — arguably the highest-risk moment for a loop (the baseline didn't exist a moment ago), yet unproven that ticks 2-N stay quiet once the first-ever baseline is in place.
  evidence: Raised by Blind Hunter during this story's review pass 1. Confirmed the existing single-round test covers only the first-write decision, not repeated-tick stability after the baseline is established. Out of this story's frozen scope (the `<intent-contract>` I/O & Edge-Case Matrix names exactly three scenarios, not this one), so not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-2-5: `test_zero_loop_survives_a_baseline_refresh_failure` (Story 8.2) round-trips the non-atomic baseline-refresh failure only in the direction that fails Jira's tighter 255-char ceiling (`push_to_jira`); no mirrored test drives the same persistent-failure steady state via GitHub's 1024-char ceiling (`push_to_github`) instead.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md`
  summary: `test_zero_loop_survives_a_baseline_refresh_failure` (Story 8.2) round-trips the non-atomic baseline-refresh failure only in the direction that fails Jira's tighter 255-char ceiling (`push_to_jira`); no mirrored test drives the same persistent-failure steady state via GitHub's 1024-char ceiling (`push_to_github`) instead.
  evidence: Raised by Edge Case Hunter during this story's review pass 2. The existing single-round precedent (`test_baseline_exceeding_the_field_size_ceiling_is_a_named_failure_after_the_value_push`) deliberately drives only the Jira direction too, per its own docstring ("Jira's ceiling ... is the tighter of the two, so it is the one this test drives over"), and the audit's dispatch note (`epics.md:664-665`) names the failure path generically, not per-direction — so this mirrors an existing, precedented scope choice rather than a new gap this story introduced. Not addressed in this pass; a legitimate future robustness addition.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-2-6: No test anywhere in `test_sync_reconcile_propagation.py` (old or new) covers a first-link item whose CURRENT tracked status value is itself unset/`None` at read time — every existing "never synced" (first-link) test seeds a concrete current status on both sides, only the BASELINE key is absent. The `_MISSING`-vs-`None` sentinel distinction jira:AD-10 exists specifically to prevent collapsing (an absent baseline key means "never synced"; a present key holding `None` means "synced, then explicitly cleared") is therefore never exercised end-to-end for the case where the CURRENT value itself reads as unset on a first link.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md`
  summary: No test anywhere in `test_sync_reconcile_propagation.py` (old or new) covers a first-link item whose CURRENT tracked status value is itself unset/`None` at read time — every existing "never synced" (first-link) test seeds a concrete current status on both sides, only the BASELINE key is absent. The `_MISSING`-vs-`None` sentinel distinction jira:AD-10 exists specifically to prevent collapsing (an absent baseline key means "never synced"; a present key holding `None` means "synced, then explicitly cleared") is therefore never exercised end-to-end for the case where the CURRENT value itself reads as unset on a first link.
  evidence: Raised by Blind Hunter during this story's review pass 2, explicitly flagged as adjacent to (not caused by) this story's diff. Confirmed by grep: every `test_first_link_*` fixture in the file sets a concrete `gh_status`/`status` current value; none omits it. Pre-existing gap in the whole file's coverage, surfaced incidentally by a review focused on loop-safety. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-3: Entry-point symmetry (redelivery via the identifier opposite the one that made the first call) is proven in only one direction — Jira-initiated push, then GitHub-identifier redelivery. The mirror direction (GitHub-initiated push, then Jira-identifier redelivery) and the both-identifiers-given branch of `_read_both_sides` are untested under redelivery.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md`
  summary: Entry-point symmetry (redelivery via the identifier opposite the one that made the first call) is proven in only one direction — Jira-initiated push, then GitHub-identifier redelivery. The mirror direction (GitHub-initiated push, then Jira-identifier redelivery) and the both-identifiers-given branch of `_read_both_sides` are untested under redelivery.
  evidence: Independently raised by both Blind Hunter and Edge Case Hunter during this story's review pass. The frozen `<intent-contract>` I/O & Edge-Case Matrix names exactly one row for this scenario, so the single direction satisfies the contract as literally written; the mirror direction is additional coverage, not a contract violation. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-3-2: No test covers concurrent/overlapping redelivery — all three of this story's idempotent-redelivery tests run each `reconcile()` call to full completion (including its already-documented non-atomic baseline write) before the next call starts. Two calls racing against the same transport, both reading stale state before either writes back, is untested anywhere in the suite.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md`
  summary: No test covers concurrent/overlapping redelivery — all three of this story's idempotent-redelivery tests run each `reconcile()` call to full completion (including its already-documented non-atomic baseline write) before the next call starts. Two calls racing against the same transport, both reading stale state before either writes back, is untested anywhere in the suite.
  evidence: Independently raised by both Blind Hunter and Edge Case Hunter during this story's review pass. `reconcile()`'s non-atomicity between the value push and the baseline refresh is already documented and accepted elsewhere in `sync.py` and this test file (e.g. `test_zero_loop_survives_a_baseline_refresh_failure`'s docstring); genuinely concurrent delivery is a different, unaddressed risk class. This story's frozen contract only asks for sequential redelivery, so not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-3-3: AD-4 conflict-path idempotent redelivery (both sides genuinely diverge to different values; GitHub-wins default and the `field_overrides` Jira-wins variant) is still untested — no test proves that after the conflict-authority decision propagates once, a redelivery stays a true no-op.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md`
  summary: AD-4 conflict-path idempotent redelivery (both sides genuinely diverge to different values; GitHub-wins default and the `field_overrides` Jira-wins variant) is still untested — no test proves that after the conflict-authority decision propagates once, a redelivery stays a true no-op.
  evidence: Raised by Edge Case Hunter during this story's review pass; the same gap was independently raised by both reviewers during Story 8.3's review pass 1 (logged in that pass's Review Triage Log, but never previously appended to this ledger). Explicitly out of this story's frozen scope — the `<intent-contract>` Boundaries' "Never" section forbids re-scoping into "the conflict-path ... coverage 8.2's Spec Change Log explicitly deferred." Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-3-4: The new byte-identical (full-dict-equality) idempotency proof still covers only 2 of the 4 `reconcile()` decision branches (`push_to_jira`/`push_to_github`). The convergent-same-value no-op (`test_both_diverged_to_the_same_value_is_a_no_op_...`) and the persistent baseline-refresh-failure steady state (`test_zero_loop_survives_a_baseline_refresh_failure`) remain checked by write-count only, the older 8.2 technique this story's Approach set out to supersede.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md`
  summary: The new byte-identical (full-dict-equality) idempotency proof still covers only 2 of the 4 `reconcile()` decision branches (`push_to_jira`/`push_to_github`). The convergent-same-value no-op (`test_both_diverged_to_the_same_value_is_a_no_op_...`) and the persistent baseline-refresh-failure steady state (`test_zero_loop_survives_a_baseline_refresh_failure`) remain checked by write-count only, the older 8.2 technique this story's Approach set out to supersede.
  evidence: Raised by Edge Case Hunter during this story's review pass; the same two gaps were independently raised during Story 8.3's review pass 1 (logged in that pass's Review Triage Log as two separate `[defer][low]` items, but never previously appended to this ledger). Out of this story's frozen scope (its `<intent-contract>` names exactly three scenarios). Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-3-5: No idempotent-redelivery coverage of the first-link (never-synced) scenario — every fixture in this story's new tests pre-seeds an existing baseline; the "never synced, first reconcile creates the baseline, then a duplicate delivery" case is unexercised.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md`
  summary: No idempotent-redelivery coverage of the first-link (never-synced) scenario — every fixture in this story's new tests pre-seeds an existing baseline; the "never synced, first reconcile creates the baseline, then a duplicate delivery" case is unexercised.
  evidence: Raised by Edge Case Hunter during this story's review pass; the same gap was independently raised during Story 8.3's review pass 1 (logged in that pass's Review Triage Log, but never previously appended to this ledger). Out of this story's frozen scope. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-3-6: The AD-9 rule 2 test (`test_late_delivery_about_a_superseded_value_does_not_regress_state_ad9_rule2`) models only a single intervening state change (one hop: To Do -> In Progress -> Blocked) before the late redelivery. Multi-hop or alternating-direction sequences (matching this file's own `range(2, 6)` N-round-trip idiom used elsewhere) are untested for the stale-value-convergence property.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md`
  summary: The AD-9 rule 2 test (`test_late_delivery_about_a_superseded_value_does_not_regress_state_ad9_rule2`) models only a single intervening state change (one hop: To Do -> In Progress -> Blocked) before the late redelivery. Multi-hop or alternating-direction sequences (matching this file's own `range(2, 6)` N-round-trip idiom used elsewhere) are untested for the stale-value-convergence property.
  evidence: Raised by Edge Case Hunter during this story's review pass. The frozen `<intent-contract>`'s Design Notes specify exactly the single-hop fixture shape implemented; more hops is additional robustness, not a contract gap. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1: `TrustedIngress` (and `DashboardIdentityMiddleware`) implements only address-tuple matching against `scope["client"][0]`; AD-4's own text says the adopter declares the trusted ingress as "the address or interface the proxy connects from," but no interface-based (e.g. Unix-domain-socket) trust concept exists. Under a UDS deployment topology `scope["client"]` is `None` per the ASGI spec, so every legitimate identity-bearing request would be refused outright with no way to declare trust any other way. summary_continued: Additionally, peer-address comparison is raw string equality with no IPv4/IPv6 normalization (e.g. an IPv6-mapped `::ffff:10.0.0.1` would not match a declared `10.0.0.1`).

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: `TrustedIngress` (and `DashboardIdentityMiddleware`) implements only address-tuple matching against `scope["client"][0]`; AD-4's own text says the adopter declares the trusted ingress as "the address or interface the proxy connects from," but no interface-based (e.g. Unix-domain-socket) trust concept exists. Under a UDS deployment topology `scope["client"]` is `None` per the ASGI spec, so every legitimate identity-bearing request would be refused outright with no way to declare trust any other way. summary_continued: Additionally, peer-address comparison is raw string equality with no IPv4/IPv6 normalization (e.g. an IPv6-mapped `::ffff:10.0.0.1` would not match a declared `10.0.0.1`).
  evidence: Raised by Blind Hunter during this story's review pass; ASGI's documented `scope["client"]` semantics for UDS transports confirm the `None` claim. This story's own I/O Matrix and Acceptance Criteria only ever specify address-tuple matching (no "interface" scenario is tested), so the code is conformant with what was actually made testable — but the gap is real and belongs with Story 9.5 (the deployment perimeter / ASGI topology / edge policy story), which is where the concrete transport (TCP vs UDS) and edge topology get decided. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-2: AD-4's "refuse the start, not the request" is proven only at the middleware boundary, never end-to-end through a real ASGI server. The middleware demonstrably never calls `send()`, but a `UntrustedIngressError` propagating out of the application is then the SERVER's to interpret, and daphne (the server the architecture Stack table names) renders an application exception as a generic 500 response with a body — i.e. exactly the "ordinary response cycle" AD-4 set out to avoid.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: AD-4's "refuse the start, not the request" is proven only at the middleware boundary, never end-to-end through a real ASGI server. The middleware demonstrably never calls `send()`, but a `UntrustedIngressError` propagating out of the application is then the SERVER's to interpret, and daphne (the server the architecture Stack table names) renders an application exception as a generic 500 response with a body — i.e. exactly the "ordinary response cycle" AD-4 set out to avoid.
  evidence: Raised by Blind Hunter during this story's review pass 2. The fake-ASGI harness that proves "zero sends" has no server behind it, so the property it certifies is strictly narrower than the property AD-4 states. This is NOT this story's Block If firing — that clause is narrowly about whether the refusal mechanism is testable against a fake transport, and it is (the middleware docstring was corrected in this pass to claim only the proven property). Choosing/wrapping a server so the refusal reaches the wire as an abort is Story 9.5's (deployment perimeter) decision, and demonstrating it end-to-end is Story 9.6's (proof suite) job. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-3: AD-5's refusal half is unimplemented and unproven. AD-5 reads "any cross-worker shared state that cannot be shared across worker processes is refused when the deployment runs more than one worker," but `get_master_dataset()` performs no worker-count or backend-capability check, and the single-flight proof runs two threads in ONE process against `LocMemCache` — precisely the in-process backend AD-5 refuses under workers>1. Verified by execution in this pass: `DummyCache.add()` returns `True` unconditionally (three consecutive callers all "win" the lock, so single-flight is silently off), and `FileBasedCache.add()` is an unlocked check-then-set with no cross-process atomicity.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: AD-5's refusal half is unimplemented and unproven. AD-5 reads "any cross-worker shared state that cannot be shared across worker processes is refused when the deployment runs more than one worker," but `get_master_dataset()` performs no worker-count or backend-capability check, and the single-flight proof runs two threads in ONE process against `LocMemCache` — precisely the in-process backend AD-5 refuses under workers>1. Verified by execution in this pass: `DummyCache.add()` returns `True` unconditionally (three consecutive callers all "win" the lock, so single-flight is silently off), and `FileBasedCache.add()` is an unlocked check-then-set with no cross-process atomicity.
  evidence: Raised independently by both reviewers in review pass 2 and confirmed by running the real Django 5.2.15 backends. This pass corrected `cache.py`'s docstring, which had asserted `cache.add()` is "atomic against every Django cache backend" — a claim the execution disproves — and now names the per-backend reality explicitly. The refusal itself needs the deployment perimeter to know the worker count and the configured backend, which is Story 9.5's surface, with the cross-worker proof belonging to Story 9.6. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-4: `get_master_dataset()` is synchronous and its waiter path calls `time.sleep()`. Called from an async Channels consumer — which is the architecture's own model (AD-8/sld:AD-12 put data fetching on the hot path of each data-returning message) — it blocks that worker's entire event loop, stalling every other connection on the process for up to `lock_timeout` (default 30s), not just the waiting one. No async variant, no `sync_to_async` guidance.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: `get_master_dataset()` is synchronous and its waiter path calls `time.sleep()`. Called from an async Channels consumer — which is the architecture's own model (AD-8/sld:AD-12 put data fetching on the hot path of each data-returning message) — it blocks that worker's entire event loop, stalling every other connection on the process for up to `lock_timeout` (default 30s), not just the waiting one. No async variant, no `sync_to_async` guidance.
  evidence: Raised independently by both reviewers in review pass 2. Story 9.1 ships no consumer, so nothing calls this from async code yet and the defect is latent rather than live; the docstring was updated in this pass to state the blocking contract explicitly instead of leaving it to be discovered. The async variant belongs with the first story that puts this on an async hot path. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-5: The acceptance criterion "given `pyforge-steward` installed WITHOUT the `[dashboard]` extra, any existing duty runs unchanged" is executed by no environment. Adding `django = ">=5.2,<6"` to `[feature.pyforge-steward.dependencies]` means django is unconditionally importable in the only env that runs `pyforge-steward-test`, so the no-extra configuration is never instantiated in CI and the AST import guard stands in as a static proxy for it rather than a test of it.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: The acceptance criterion "given `pyforge-steward` installed WITHOUT the `[dashboard]` extra, any existing duty runs unchanged" is executed by no environment. Adding `django = ">=5.2,<6"` to `[feature.pyforge-steward.dependencies]` means django is unconditionally importable in the only env that runs `pyforge-steward-test`, so the no-extra configuration is never instantiated in CI and the AST import guard stands in as a static proxy for it rather than a test of it.
  evidence: Raised by Blind Hunter in review pass 2. The feature-level django was a deliberate, spec-documented choice (in-repo CI coverage without widening the shipped package's run-deps, mirroring the atlas->warden `[gate]` precedent), so this is a consequence of the design rather than a deviation from it. Closing it needs a second pixi environment that installs the package WITHOUT the extra — an env-topology decision beyond this story's Code Map. This pass narrowed the blast radius by adding `pytest.importorskip("django")` to the two test modules that genuinely require it, so the suite degrades to skips rather than collection errors in such an environment. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-6: The name `pyforge.steward.dashboard` (Epic 9's live, role-filtered Django dashboard) collides conceptually with the pre-existing `steward deploy dashboard` verb in `steward/deploy.py` (`build_dashboard`, `dashboard_diff`, `commit_and_push_dashboard`, `_DASHBOARD_GENERATE_MARKER = docs/dashboard/generate.py`), which is the STATIC GitHub-Pages dashboard. Two unrelated things named "dashboard" in one package.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: The name `pyforge.steward.dashboard` (Epic 9's live, role-filtered Django dashboard) collides conceptually with the pre-existing `steward deploy dashboard` verb in `steward/deploy.py` (`build_dashboard`, `dashboard_diff`, `commit_and_push_dashboard`, `_DASHBOARD_GENERATE_MARKER = docs/dashboard/generate.py`), which is the STATIC GitHub-Pages dashboard. Two unrelated things named "dashboard" in one package.
  evidence: Raised by Blind Hunter in review pass 2 and confirmed against `steward/deploy.py`. Nothing here is a clash Python will catch — it is a clash every future reader and every future `grep dashboard` will hit, and the architecture's own Stack table lists both under the same package. Renaming either surface is a spec-level decision outside this story's frozen Code Map, and is cheapest to make while Epic 9 has only one story landed. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-7: The lock's compare-before-delete release (`if cache.get(lock_key) == token: cache.delete(lock_key)`) is still a TOCTOU, not a closed race — `get` and `delete` are two non-atomic round trips, so a lock that expires and is re-acquired by another caller between them is still deleted by the wrong owner. Review pass 1 narrowed the window; it did not eliminate it.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: The lock's compare-before-delete release (`if cache.get(lock_key) == token: cache.delete(lock_key)`) is still a TOCTOU, not a closed race — `get` and `delete` are two non-atomic round trips, so a lock that expires and is re-acquired by another caller between them is still deleted by the wrong owner. Review pass 1 narrowed the window; it did not eliminate it.
  evidence: Raised by Blind Hunter in review pass 2. Closing it requires an atomic compare-and-delete primitive (e.g. a Redis Lua script or a backend-native `DELETE ... IF`), which Django's cache API deliberately does not expose — so it cannot be fixed without committing to a specific backend, which is the same Story 9.5 decision as the AD-5 entry above. This pass replaced the comment that read as though the race were closed with an explicit statement of the residual window. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-8: `DashboardIdentityMiddleware` writes un-namespaced top-level ASGI scope keys (`scope["dashboard_identity"]`, `scope["dashboard_role"]`), sharing a flat namespace with ASGI's own reserved keys and every other middleware in the adopter's stack. For a library whose entire premise is being mounted inside somebody else's ASGI application, a generic name like `dashboard_identity` is exactly the key a second dashboard middleware would also write.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: `DashboardIdentityMiddleware` writes un-namespaced top-level ASGI scope keys (`scope["dashboard_identity"]`, `scope["dashboard_role"]`), sharing a flat namespace with ASGI's own reserved keys and every other middleware in the adopter's stack. For a library whose entire premise is being mounted inside somebody else's ASGI application, a generic name like `dashboard_identity` is exactly the key a second dashboard middleware would also write.
  evidence: Raised by Blind Hunter in review pass 2. The ASGI convention for third-party additions is a vendor-prefixed key or a slot under `scope["extensions"]`. This pass fixed the sharper half of the finding — the middleware now clears any pre-existing identity/role keys on every path that does not itself establish an identity, so an upstream-planted value can no longer be inherited — but renaming the keys is an API decision best made when the first consumer exists (Story 9.2's navigation filtering), since nothing reads them yet. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-9: `TrustedIngress.addresses` accepts address STRINGS that can never match an ASGI peer host — a CIDR block (`"10.0.0.0/24"`), a hostname (`"proxy.internal"`), or an IPv4 literal when the peer arrives IPv6-mapped (`"::ffff:10.0.0.1"`) all construct cleanly and then silently refuse every request. Element type/emptiness are now validated (this pass); address FORM is not.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: `TrustedIngress.addresses` accepts address STRINGS that can never match an ASGI peer host — a CIDR block (`"10.0.0.0/24"`), a hostname (`"proxy.internal"`), or an IPv4 literal when the peer arrives IPv6-mapped (`"::ffff:10.0.0.1"`) all construct cleanly and then silently refuse every request. Element type/emptiness are now validated (this pass); address FORM is not.
  evidence: Raised by Edge Case Hunter in review pass 2 and reproduced. Deliberately left with the closely-related interface/UDS ingress-declaration entry already on this ledger for Story 9.5: whether the declaration should accept CIDR at all, and whether normalization or strict `ipaddress.ip_address()` validation is right, depends on the transport and edge topology that story decides. Fixing form validation now would risk forbidding a shape 9.5 chooses to support. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-10: AD-4's whole refusal rests on `scope["client"]` being the connection's peer, and under the ASGI servers the architecture's own Stack table names it is not. daphne run with `--proxy-headers` and uvicorn with `proxy_headers=True` (uvicorn's DEFAULT) both OVERWRITE `scope["client"]` with the leftmost `X-Forwarded-For` entry and perform no trusted-hop validation, so behind a proxy that appends to XFF (standard nginx `$proxy_add_x_forwarded_for`) that value is client-supplied: legitimate identity-bearing requests are refused while a caller that sends `X-Forwarded-For: <a declared address>` passes the ingress check and has its `X-Forwarded-User`/`X-Forwarded-Role` accepted verbatim.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: AD-4's whole refusal rests on `scope["client"]` being the connection's peer, and under the ASGI servers the architecture's own Stack table names it is not. daphne run with `--proxy-headers` and uvicorn with `proxy_headers=True` (uvicorn's DEFAULT) both OVERWRITE `scope["client"]` with the leftmost `X-Forwarded-For` entry and perform no trusted-hop validation, so behind a proxy that appends to XFF (standard nginx `$proxy_add_x_forwarded_for`) that value is client-supplied: legitimate identity-bearing requests are refused while a caller that sends `X-Forwarded-For: <a declared address>` passes the ingress check and has its `X-Forwarded-User`/`X-Forwarded-Role` accepted verbatim.
  evidence: Raised by Blind Hunter in review pass 3 and independently re-verified against the installed daphne 4.2.3 source: `daphne.utils.parse_x_forwarded_for` takes `X-Forwarded-For.split(",")[0].strip()` as the client host with no hop validation whatsoever. This is sharper than the two ingress entries already on this ledger (end-to-end refusal unproven; UDS leaves `client` as `None`): this one is an active bypass in the recommended topology, not an unproven or absent case. It is deferred rather than fixed because the fix is not in this module — it is either a deployment constraint (run the server WITHOUT proxy-header parsing so `scope["client"]` is the real TCP peer, or terminate XFF at a controlled hop) or a trusted-hop-aware ingress model, and Story 9.5 owns the ASGI/edge topology while 9.6 owns proving it end-to-end. Review pass 3 DID document the precondition prominently in `middleware.py`'s module docstring, in `TrustedIngress.addresses`' docstring, and in the story spec's Design Notes, replacing wording that had asserted `scope["client"]` simply IS the peer address. Not otherwise addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-11: Review pass 2's fail-closed refusal of a duplicated identity/role header detects duplication only as ASGI represents it — separate `(name, value)` pairs. A duplicate that reached the server already folded into one comma-separated field line (`X-Forwarded-User: eve, alice`) is one value, passes the `len(...) > 1` check, and lands on the scope verbatim, so the ambiguity the code deliberately refuses becomes an accepted mangled identity instead.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: Review pass 2's fail-closed refusal of a duplicated identity/role header detects duplication only as ASGI represents it — separate `(name, value)` pairs. A duplicate that reached the server already folded into one comma-separated field line (`X-Forwarded-User: eve, alice`) is one value, passes the `len(...) > 1` check, and lands on the scope verbatim, so the ambiguity the code deliberately refuses becomes an accepted mangled identity instead.
  evidence: Raised by Edge Case Hunter in review pass 3. Real but deliberately not patched: this module cannot distinguish a folded duplicate from a single value that legitimately contains a comma, and proxy-injected identities are commonly LDAP DNs (`CN=Alice,OU=Eng,DC=corp`), so refusing every comma would forbid a shape a later story may need to support — the same reasoning that parked the address-FORM entry above. Deciding whether a comma is legal in an identity value belongs with the story that defines the identity model against a real proxy (9.5's perimeter, or 9.3's audit rows, whichever lands first). ASGI servers themselves preserve duplicates as separate pairs, so the trigger requires a folding intermediary upstream. Pass 3 documented the limit explicitly in `middleware.py`'s module docstring. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-12: `get_master_dataset()` makes the cache backend a hard dependency of the dashboard rather than an accelerator: a backend error on the initial `cache.get(key, _MISSING)` or on the `cache.add()` lock acquire propagates and fails the request outright, without ever calling `fetch()` — so a cache hiccup becomes a full outage for data the caller could have fetched directly.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: `get_master_dataset()` makes the cache backend a hard dependency of the dashboard rather than an accelerator: a backend error on the initial `cache.get(key, _MISSING)` or on the `cache.add()` lock acquire propagates and fails the request outright, without ever calling `fetch()` — so a cache hiccup becomes a full outage for data the caller could have fetched directly.
  evidence: Raised by Blind Hunter in review pass 3 and reproduced with delegating fake backends that fail only on the targeted operation (read-blip and add-blip both: hard failure, `fetch` never ran). Pass 3 fixed the narrow half where the consequence was unambiguous — a failing `cache.set` no longer discards an already-successful fetch — but making the cache wholly optional means swallowing backend errors on the read and lock paths too, which silently converts a persistent backend outage into an unbounded fetch-per-request load. That is a failure-semantics decision tied to the same backend/deployment choice as the AD-5 entries above (Story 9.5), not a defect with one obvious fix. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-13: Extracted identity and role values are taken from the header verbatim — no trimming, no length bound, and latin-1-decoded per the ASGI spec. So `X-Forwarded-User: "  alice  "` is a different identity from `alice` to every downstream consumer, cache key and future audit row; a UTF-8-encoding proxy yields mojibake (`José` -> `JosÃ©`); and a whitespace-only value is accepted as an identity.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: Extracted identity and role values are taken from the header verbatim — no trimming, no length bound, and latin-1-decoded per the ASGI spec. So `X-Forwarded-User: "  alice  "` is a different identity from `alice` to every downstream consumer, cache key and future audit row; a UTF-8-encoding proxy yields mojibake (`José` -> `JosÃ©`); and a whitespace-only value is accepted as an identity.
  evidence: Raised by Blind Hunter and Edge Case Hunter independently in review pass 3, both reproduced. Not patched because the right answer is a decision, not a typo fix: trimming, a case/Unicode normalization form, a length cap and the proxy's actual value encoding are properties of the identity model, and Story 9.3 (the audit trail) is the first consumer that makes an identity value load-bearing and durable. Choosing now would risk normalizing an identity in a way that no longer matches the adopter's directory. Distinct from the empty-value case, which pass 3 DID fix (a present-but-empty identity or role now establishes none, since that has exactly one sensible reading). Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-14: `test_dashboard_appconfig_is_ad13_compliant` reads three class attributes off `DashboardConfig`; it never adds `"pyforge.steward.dashboard"` to `INSTALLED_APPS` and calls `django.setup()`. App-registry loadability — which is what actually breaks, given `pyforge/` is a namespace package with no `__init__.py`, and given label uniqueness is only meaningful against a real `INSTALLED_APPS` — remains unasserted, so the scaffold this story ships EARLY specifically to de-risk Story 9.3 is verified only by attribute equality.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: `test_dashboard_appconfig_is_ad13_compliant` reads three class attributes off `DashboardConfig`; it never adds `"pyforge.steward.dashboard"` to `INSTALLED_APPS` and calls `django.setup()`. App-registry loadability — which is what actually breaks, given `pyforge/` is a namespace package with no `__init__.py`, and given label uniqueness is only meaningful against a real `INSTALLED_APPS` — remains unasserted, so the scaffold this story ships EARLY specifically to de-risk Story 9.3 is verified only by attribute equality.
  evidence: Raised by Blind Hunter in review pass 3, which also ran the real thing and found no bug today: with settings configured and the app installed, django 5.2.15 loads it as `<DashboardConfig: pyforge_steward_dashboard>` with `default_auto_field` honoured. So this is a proof-strength gap, not a live defect. Deferred because a `django.setup()`-based test mutates process-wide Django state and would need the session-scoped settings fixture that the entry below calls for; it belongs with Story 9.3 (which adds the first model and migration, making registry loading genuinely load-bearing) or 9.6's proof suite. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-15: `tests/unit/test_dashboard_cache.py` calls `settings.configure(...)` as an import-time side effect at module scope, making this one file's `CACHES` the session-wide Django configuration for every module collected after it. The correct shape is a session-scoped fixture or a `conftest.py` that owns Django settings for the whole suite.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: `tests/unit/test_dashboard_cache.py` calls `settings.configure(...)` as an import-time side effect at module scope, making this one file's `CACHES` the session-wide Django configuration for every module collected after it. The correct shape is a session-scoped fixture or a `conftest.py` that owns Django settings for the whole suite.
  evidence: Raised by Blind Hunter in review pass 3. The sharp sub-case is that pass 2's `isinstance(backend, LocMemCache)` guard cannot detect the likeliest collision, because Django's own DEFAULT `CACHES` is also a `LocMemCache` — a module that configured settings without `CACHES` would pass that assertion while this file's raw-store inspection ran against a different store. Pass 3 closed the diagnostic half (the fixture now also asserts the in-force `CACHES["default"]["LOCATION"]` is the one declared in this file, so a foreign configuration fails loudly and legibly), and the suite is sequential today (`pytest ... -q`, no xdist), so nothing is broken now. Restructuring settings ownership across the whole test tier is a test-architecture change beyond this story's Code Map. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/2 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md, tests/unit/test_dashboard_cache.py); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-16: Single-flight is bounded by `lock_timeout`, and past that bound it degrades silently and without limit: the lock is never extended or heartbeated and the retry loop has no attempt cap or deadline, so concurrent callers issue roughly `fetch_duration / lock_timeout` upstream fetches. Measured at 3 fetches for a 3s fetch under `lock_timeout=1`. The suite pins only the fast-fetch case, so the story's headline invariant has no regression barrier against its own degradation mode.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: Single-flight is bounded by `lock_timeout`, and past that bound it degrades silently and without limit: the lock is never extended or heartbeated and the retry loop has no attempt cap or deadline, so concurrent callers issue roughly `fetch_duration / lock_timeout` upstream fetches. Measured at 3 fetches for a 3s fetch under `lock_timeout=1`. The suite pins only the fast-fetch case, so the story's headline invariant has no regression barrier against its own degradation mode.
  evidence: Raised by Blind Hunter in review pass 3 and reproduced with 4 barrier-synchronised callers. Distinct from the `lock_timeout=0`/`None` hole pass 2 patched (that voided the lock entirely; this is the lock working exactly as designed and simply expiring). Pass 3 corrected the module docstring, whose opening line claimed "exactly one upstream `fetch()` call" unconditionally while a later paragraph contradicted it, and now states the bound and the measured degradation. Actually bounding it needs either a lock heartbeat or a backend primitive with an extend operation — the same Story 9.5 backend decision as the other AD-5 entries. Not addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-17: The headline CAP-2 invariant's second half — "the cache never stores a role-filtered frame" — is a CALLER CONTRACT `get_master_dataset(key, fetch, ...)` cannot enforce, not a property the module guarantees: it writes exactly what the caller's `fetch()` returned under exactly the `key` the caller chose, so a caller that passes a role-filtering closure (or a per-role key) defeats CAP-2 while every assertion in the suite still passes. The existing test named for the invariant asserts key CARDINALITY (`len(raw_keys) == 1` plus a name check), which holds perfectly when the single cached value IS a role-filtered frame.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: The headline CAP-2 invariant's second half — "the cache never stores a role-filtered frame" — is a CALLER CONTRACT `get_master_dataset(key, fetch, ...)` cannot enforce, not a property the module guarantees: it writes exactly what the caller's `fetch()` returned under exactly the `key` the caller chose, so a caller that passes a role-filtering closure (or a per-role key) defeats CAP-2 while every assertion in the suite still passes. The existing test named for the invariant asserts key CARDINALITY (`len(raw_keys) == 1` plus a name check), which holds perfectly when the single cached value IS a role-filtered frame.
  evidence: Raised by Blind Hunter in review pass 4 and reproduced: an east-role closure warms `key="master"`, and the next caller — west role, same key — is served east rows, with the backend holding exactly one key and the existing test passing unchanged. Review pass 4 corrected `cache.py`'s docstring, which asserted the module "never writes ... a role-filtered value" as though it were enforced, to state the caller's half explicitly. Closing it needs an API shape that cannot be misused this way — one that takes the `AccessDeclaration` and derives the key itself — which is a design decision best made with Story 9.2's first real consumer in hand, since nothing calls this function in production yet. Not otherwise addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-18: Story 9.1's deferred items exist ONLY in this gitignored Tier-3 `implementation-artifacts/deferred-work.md`; the tracked `planning-artifacts/deferred-work-ledger.md` carries no Story 9.1 entries at all (its last entry is `DW-7-1-2`). They must be promoted into the tracked ledger when the story lands — renamed to its `DW-<epic>-<story>-<n>` convention, exactly as `DW-7-1-1` records having been promoted — or every one of them is destroyed with the run worktree.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: Story 9.1's deferred items exist ONLY in this gitignored Tier-3 `implementation-artifacts/deferred-work.md`; the tracked `planning-artifacts/deferred-work-ledger.md` carries no Story 9.1 entries at all (its last entry is `DW-7-1-2`). They must be promoted into the tracked ledger when the story lands — renamed to its `DW-<epic>-<story>-<n>` convention, exactly as `DW-7-1-1` records having been promoted — or every one of them is destroyed with the run worktree.
  evidence: Raised by Blind Hunter in review pass 4 and verified by grep against both files: eight docstring references across `cache.py`, `middleware.py` and `__init__.py` name the tracked ledger as the home of five distinct deferrals (the multi-worker backend decision, the atomic compare-and-delete, the async variant, the comma-folded duplicate header, the `scope["client"]`/proxy-headers precondition), and `grep -niE "9\.1|9-1|dashboard"` over that file returns zero hits. Review pass 3 had corrected the PATH (it previously named this gitignored file, absent from every clone); nobody checked whether the target actually recorded the items. Pass 4 corrected the docstrings to name both stages and the promotion between them rather than asserting the entries are already tracked, but the promotion itself is a landing-time action this story cannot perform from its run worktree. This is the same Tier-3 teardown-loss failure `CLAUDE.md` documents for story specs (pyforge-warden lost 13 of 31 before the durable-spec convention existed). Not otherwise addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-9-1-19: Django's `DatabaseCache` cannot carry the single-flight lock primitive at all: `_base_set` ends in a bare `except DatabaseError: return False` ("to be threadsafe, updates/inserts are allowed to fail silently"), so under write contention `add()` reports failure while nothing is stored and reads keep working — indistinguishable from "someone else holds the lock", except nobody does. Review pass 4 bounded that state (it was an unbounded busy loop; it now sleeps and raises `LockUnavailableError` after `2 * lock_timeout`), but the deployment still gets a hard request failure where single-flight is simply unavailable, rather than a degraded fetch.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: Django's `DatabaseCache` cannot carry the single-flight lock primitive at all: `_base_set` ends in a bare `except DatabaseError: return False` ("to be threadsafe, updates/inserts are allowed to fail silently"), so under write contention `add()` reports failure while nothing is stored and reads keep working — indistinguishable from "someone else holds the lock", except nobody does. Review pass 4 bounded that state (it was an unbounded busy loop; it now sleeps and raises `LockUnavailableError` after `2 * lock_timeout`), but the deployment still gets a hard request failure where single-flight is simply unavailable, rather than a degraded fetch.
  evidence: Raised by Blind Hunter in review pass 4, reproduced against the pre-fix code (1.1M backend operations in 2s, 0 fetches, thread still alive) and confirmed in the installed Django 5.2.15's `DatabaseCache` source. This adds a concretely-named backend and failure mode to the backend-capability question already on this ledger: AD-5's refusal half — declining a backend that cannot carry the property when workers>1 — is exactly what would turn this from a runtime raise into a startup refusal, and it belongs with Story 9.5's deployment perimeter. Not otherwise addressed in this pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-34-1: Federated-read and write-refused tests skip when the DuckDB `postgres` extension is not already in the local cache, so a CI image without that cache can stay green without proving canopy:FR-46 live ATTACH.

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md`
  summary: Federated-read and write-refused tests skip when the DuckDB `postgres` extension is not already in the local cache, so a CI image without that cache can stay green without proving canopy:FR-46 live ATTACH.
  evidence: `requires_postgres_ext` skipif in `test_read_only_live_attach.py`. Spec allowed AST/string gates for INSTALL; live ATTACH still needs a provisioned cache. Not a 34.1 product-path change.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-34-1-2: `attach_postgres_readonly` is not exercised on `connect_reader` in 34.1 tests (writer only).

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md`
  summary: `attach_postgres_readonly` is not exercised on `connect_reader` in 34.1 tests (writer only).
  evidence: Design notes require reuse of both openers; 34.1 ACs are federated read + refused write on the plane writer. Reader ATTACH is later if 34.3/34.4 needs it.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-7: `reconcile`'s pre-write convergence check for the `assignee` field compares the raw, untranslated `target_value` (a GitHub login or a Jira accountId, depending on direction) against the destination's current raw value, so a genuinely-already-converged pair (both sides correctly naming the same real person, just in each system's own vocabulary) is never recognized as converged -- it triggers a redundant write every time, and on the GitHub REST side that redundant write is a live DELETE+POST assignee churn (visible notification noise), not merely a wasted API call.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md`
  summary: `reconcile`'s pre-write convergence check for the `assignee` field compares the raw, untranslated `target_value` (a GitHub login or a Jira accountId, depending on direction) against the destination's current raw value, so a genuinely-already-converged pair (both sides correctly naming the same real person, just in each system's own vocabulary) is never recognized as converged -- it triggers a redundant write every time, and on the GitHub REST side that redundant write is a live DELETE+POST assignee churn (visible notification noise), not merely a wasted API call.
  evidence: Confirmed by live reproduction against `reconcile()` during Story 8.7's adversarial review pass (Blind Hunter + Edge Case Hunter, independently, both found this): with GitHub already showing `octocat` and Jira already showing the correctly-corresponding `acc_octocat`, `reconcile()` still issues a redundant Jira `PUT`/GitHub REST churn instead of downgrading to `no_op`. This is the SAME shape as an already-known, already-accepted pattern for the `status` field (Story 8.6's own Review Triage Log explicitly rejected the identical finding for status: "the pre-write convergence check compares an untranslated value... matches the frozen boundary's explicitly accepted one-wasted-write tradeoff"), which is why Story 8.7 did not patch it reflexively -- but the consequence is worse for assignee than for status: a Jira status re-PUT of an already-applied transition is typically an idempotent no-op against Jira's API, while GitHub's assignees are DELETE-then-POST (additive, non-idempotent-looking to a human watching notifications), so a redundant assignee write is a live, visible side effect every affected reconcile. Worth a dedicated look (translate `target_value` before the convergence comparison, for both fields, in one pass) given this different consequence profile, rather than silently inheriting status's acceptance without re-examining it for the new field.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-7-2: Every baseline write now unconditionally includes an `"assignee"` key alongside `"status"` in the same JSON blob written to `_JIRA_BASELINE_FIELD_CEILING` (255 chars, hard-capped by Jira Cloud's "Text Field (single line)" type). A Jira accountId typically runs 24+ characters; no test or analysis in this story demonstrates that a realistic combined `status`+`assignee` baseline payload still fits comfortably, so an item that previously had ample margin could start failing with the existing named `SyncBaselineTooLargeError` purely as a side effect of this story, on a board this story's own author never tested against.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md`
  summary: Every baseline write now unconditionally includes an `"assignee"` key alongside `"status"` in the same JSON blob written to `_JIRA_BASELINE_FIELD_CEILING` (255 chars, hard-capped by Jira Cloud's "Text Field (single line)" type). A Jira accountId typically runs 24+ characters; no test or analysis in this story demonstrates that a realistic combined `status`+`assignee` baseline payload still fits comfortably, so an item that previously had ample margin could start failing with the existing named `SyncBaselineTooLargeError` purely as a side effect of this story, on a board this story's own author never tested against.
  evidence: Raised by Blind Hunter during Story 8.7's adversarial review pass. Not a NEW unhandled failure mode -- `SyncBaselineTooLargeError` (Story 8.1, AD-2/jira:AD-10's documented escape hatch to Mode B) already exists and already surfaces an oversized baseline as a named, graceful failure rather than a crash or silent truncation -- but this story never measured how much of that pre-existing 255-byte margin it consumes, so whether real boards with long field-override/status-vocabulary combinations will start hitting it more often is genuinely unverified. Worth a follow-up: compute/test a realistic worst-case combined baseline size (longest expected status name + a real Jira accountId) against the ceiling.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-7-3: This story tracks only the FIRST login returned by GitHub's `assignees(first: 10)` GraphQL connection as the item's single synced assignee, but GitHub does not publicly document that connection's ordering as a stable contract. If a human assigns a second person directly on the live board (outside this module's tracking) and that co-assignee happens to sort ahead of the module's own tracked login on a later read, `gh.assignee` silently starts reporting the untracked person as "the" assignee, and a subsequent push can then attempt to remove/replace someone this module never added.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md`
  summary: This story tracks only the FIRST login returned by GitHub's `assignees(first: 10)` GraphQL connection as the item's single synced assignee, but GitHub does not publicly document that connection's ordering as a stable contract. If a human assigns a second person directly on the live board (outside this module's tracking) and that co-assignee happens to sort ahead of the module's own tracked login on a later read, `gh.assignee` silently starts reporting the untracked person as "the" assignee, and a subsequent push can then attempt to remove/replace someone this module never added.
  evidence: Raised independently by both Blind Hunter and Edge Case Hunter during Story 8.7's adversarial review pass, from the same underlying concern (an untracked co-assignee interfering with single-assignee tracking). The story's own frozen spec already names the broader risk category explicitly in its Boundaries & Constraints "Block If" section ("the `content { ... on Issue { assignees ... } }` GraphQL shape... unverified against a LIVE board this session... re-verify at implementation/manual-verification time") -- this entry narrows that general caution to the specific, concrete failure mode a live multi-assignee board would expose, which genuinely cannot be fully resolved or tested without live GitHub API access to confirm (or refute) the connection's actual ordering behavior.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-7-4: Story 8.7 relaxed `_read_both_sides`' trailing reciprocity check so the AF-5 gap (one side resolved, the other side's own link field empty) becomes a repair. The same relaxation also covers a case the story's intent contract never scoped: `reconcile(github_item_id=..., jira_issue_key=...)` where BOTH link fields are empty. Pre-8.7 that raised `SyncUnlinkedError`; it now writes each side's link field to point at the other, minting a brand-new pair from two identifiers the caller merely named together, and then cross-propagating their status and assignee. That is link CREATION, not the link REPAIR the story scopes ("this story only writes VALUES into fields that already exist" is honored, but "a pair `reconcile()` has already resolved by SOME means" is not -- nothing resolved this pair).

- source_spec: `_bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md`
  summary: Story 8.7 relaxed `_read_both_sides`' trailing reciprocity check so the AF-5 gap (one side resolved, the other side's own link field empty) becomes a repair. The same relaxation also covers a case the story's intent contract never scoped: `reconcile(github_item_id=..., jira_issue_key=...)` where BOTH link fields are empty. Pre-8.7 that raised `SyncUnlinkedError`; it now writes each side's link field to point at the other, minting a brand-new pair from two identifiers the caller merely named together, and then cross-propagating their status and assignee. That is link CREATION, not the link REPAIR the story scopes ("this story only writes VALUES into fields that already exist" is honored, but "a pair `reconcile()` has already resolved by SOME means" is not -- nothing resolved this pair).
  evidence: Raised by Edge Case Hunter in Story 8.7's second review pass and confirmed against the code: the trailing check only fires for a non-empty link, so two empty links reach `reconcile`, where `link_repair_github`/`link_repair_jira` are both computed as needed and both written unconditionally. Not patched in that pass because it is not reachable from the shipped CLI (`cli.py`'s `--github-item`/`--jira-issue`/`--schedule` are an `add_mutually_exclusive_group`, so an operator cannot supply both) and because whether "both named, neither linked" SHOULD mean "link them" is a genuine intent question, not a mechanical fix -- the module docstring currently asserts it as intended behavior, so resolving it means deciding the contract first. `reconcile()` is nonetheless a public module API with its own conformance test for the both-identifiers branch, and `SyncDuty.run` forwards both parameters unconditionally, so a future caller (or a CLI change dropping the mutual exclusion) reaches it. The one-sided variant of this -- one link non-empty and naming a DIFFERENT counterpart -- WAS patched in that pass and is not part of this entry.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-7-5: The jira:AD-10 "missing baseline key" rule is gated per-PAIR: when both sides' baseline maps are non-empty, a side missing the `"assignee"` key adopts its own CURRENT value as its baseline without comparing or propagating. That is exactly right for the documented accepted limitation (a pre-8.7 pair where NEITHER side has ever observed assignee). It also silently covers an asymmetric state the spec never considered: one side's baseline already carries a real `"assignee"` value while the other side's non-empty baseline lacks the key. There, the pair HAS observed assignee before, but the side missing the key still adopts-without-comparing, so a genuine live divergence (the two systems naming different people) is recorded as converged and never propagated -- no write, no error, no flag.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md`
  summary: The jira:AD-10 "missing baseline key" rule is gated per-PAIR: when both sides' baseline maps are non-empty, a side missing the `"assignee"` key adopts its own CURRENT value as its baseline without comparing or propagating. That is exactly right for the documented accepted limitation (a pre-8.7 pair where NEITHER side has ever observed assignee). It also silently covers an asymmetric state the spec never considered: one side's baseline already carries a real `"assignee"` value while the other side's non-empty baseline lacks the key. There, the pair HAS observed assignee before, but the side missing the key still adopts-without-comparing, so a genuine live divergence (the two systems naming different people) is recorded as converged and never propagated -- no write, no error, no flag.
  evidence: Raised by Edge Case Hunter in Story 8.7's second review pass and confirmed by reading `reconcile`'s baseline block: `pair_has_established_baseline` tests only that both maps are truthy, so `gh_assignee_base`/`jira_assignee_base` each fall back to their own side's current value independently of whether the OTHER side recorded a real one. Reachable via this module's own documented partial-write precedents (a baseline write that succeeds on one side and fails on the other, including the new per-field partial-persistence path added in the first review pass). Not patched because the obvious alternative -- treating the key-missing side as `_MISSING` so a real AD-4 decision runs -- makes the side with the INCOMPLETE baseline the authority, which is not self-evidently better than silent adoption; choosing between them is an intent call about which side wins in a state the frozen contract does not describe. Severity is bounded: the outcome is silent non-propagation, never a wrong write or a lost value on either system.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-7-6: Story 8.7 extended `_GET_PROJECT_ITEM_QUERY` -- the ONE query every `reconcile` read goes through -- with a `content { ... on Issue { assignees repository number } }` fragment. `github_graphql_request` raises `SyncAPIError` whenever the response carries a populated top-level `errors` array, even when `data` came back usable. GitHub answers a query touching a node the token cannot read with partial data PLUS an `errors` entry, and a Projects V2 board routinely contains items whose underlying issue lives in a repository the token has no access to. On such a board, status sync -- which shipped in Story 8.1, has been working, and consults none of the new fields -- would begin failing outright for those items. Separately, the REST assignee write needs write access to the issue's own repository, which a Projects-only token does not have.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md`
  summary: Story 8.7 extended `_GET_PROJECT_ITEM_QUERY` -- the ONE query every `reconcile` read goes through -- with a `content { ... on Issue { assignees repository number } }` fragment. `github_graphql_request` raises `SyncAPIError` whenever the response carries a populated top-level `errors` array, even when `data` came back usable. GitHub answers a query touching a node the token cannot read with partial data PLUS an `errors` entry, and a Projects V2 board routinely contains items whose underlying issue lives in a repository the token has no access to. On such a board, status sync -- which shipped in Story 8.1, has been working, and consults none of the new fields -- would begin failing outright for those items. Separately, the REST assignee write needs write access to the issue's own repository, which a Projects-only token does not have.
  evidence: Raised by Blind Hunter in Story 8.7's second review pass. The error-handling half is pre-existing (Story 8.1's "any `errors` array is a failure" rule); what this story changes is which responses can carry one. Not patched because confirming the partial-data-plus-errors shape, and deciding whether to tolerate it selectively (e.g. accept `errors` whose paths all sit under `content`), requires a live GitHub Projects V2 board with a mixed-permission item -- precisely the verification this story's own frozen "Block If" already defers to operator-executed manual verification for the same query fragment. The token-scope half was addressed in that review pass as documentation only (`.steward/sync-config.example.yaml` now states the issue-repository write requirement); the partial-error behavior is what remains open. Worth resolving at the same time as the first live-board verification run, not before.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-8-7-7: `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` (Story 8.1's Status line) reads "The AC's assignee/link propagation is NOT delivered and has no owning story (audit AF-5)". The second half stopped being true on 2026-08-15, when the fleet-wide decomposition audit added Story 8.7 to that same file expressly to own it -- the two statements now contradict each other a few dozen lines apart. The risk is not cosmetic: "no owning story" is exactly the phrase a decomposition audit greps for, so the stale note invites minting a duplicate story for work that already has one.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md`
  summary: `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` (Story 8.1's Status line) reads "The AC's assignee/link propagation is NOT delivered and has no owning story (audit AF-5)". The second half stopped being true on 2026-08-15, when the fleet-wide decomposition audit added Story 8.7 to that same file expressly to own it -- the two statements now contradict each other a few dozen lines apart. The risk is not cosmetic: "no owning story" is exactly the phrase a decomposition audit greps for, so the stale note invites minting a duplicate story for work that already has one.
  evidence: Found by Blind Hunter in Story 8.7's second review pass and confirmed by reading both passages: the 8.1 note and the Story 8.7 entry (whose own text says it is the story that owns AF-5) sit in the same tracked file. Pre-existing rather than caused by this story's diff -- it was already stale the moment 8.7 was added on main, before this branch existed. Not corrected in the review pass because epics.md Status/audit lines are orchestrator-owned maintenance state (the same 2026-08-15 audit pass that added 8.7 is what maintains them) and this branch is unmerged, so editing story-status prose from inside an in-flight story risks racing that owner. The companion fact -- Story 8.7's own "Status: backlog" line -- is ordinary landing bookkeeping and is deliberately NOT part of this entry.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-10-4: Even after story 10.4 loosens `langflow-base`'s `bcrypt` pin to `>=4.0.1,<5`, a `python=3.14 + langflow + dbgpt + django` dry-run solve still fails, because `langflow-base` also hard-depends on `onnxruntime >=1.20,<1.24`, and conda-forge ships zero `cp314` builds of onnxruntime at any version -- not just outside the `<1.24` ceiling, but none at all as of 2026-08-20.

- source_spec: `_bmad-output/implementation-artifacts/spec-10-4-the-bcrypt-pin-stops-blocking-3-14.md`
  summary: Even after story 10.4 loosens `langflow-base`'s `bcrypt` pin to `>=4.0.1,<5`, a `python=3.14 + langflow + dbgpt + django` dry-run solve still fails, because `langflow-base` also hard-depends on `onnxruntime >=1.20,<1.24`, and conda-forge ships zero `cp314` builds of onnxruntime at any version -- not just outside the `<1.24` ceiling, but none at all as of 2026-08-20.
  evidence: station-unresolved: `resolve_config.py --key project` returned `pyforge-mason` (via a stale `BMAD_ACTIVE_PROJECT` env var), while both the `.active-project` marker and `readlink -f` of this file's own path agree on `pyforge-steward` -- the two disagree, so per this workflow's mandatory cross-check the station is treated as unknown rather than trusting the env-var answer; this entry is filed against `pyforge-steward`'s ledger (the readlink-verified, marker-agreeing answer) since that is where the spec and the rest of this story's artifacts actually live. Independently verified live: `curl -s --compressed https://conda.anaconda.org/conda-forge/linux-64/repodata.json`, filtered to `name == "onnxruntime"`, lists builds for every version from 1.7.2 through 1.28.0 -- none carry a `cp314` build string. `mamba create --dry-run` for `python=3.14 langflow dbgpt django` against a channel containing the story 10.4 bcrypt fix (locally built + verified) confirms the fixed `langflow-base` is no longer excluded for a bcrypt reason, but remains excluded for this onnxruntime reason; `dbgpt` + `django` alone (without `langflow`) were separately confirmed to solve clean on py3.14 (56 packages). Out of scope for story 10.4, whose "Never" boundary explicitly limits changes to the bcrypt pin, build number, and the new test. Likely fix shape mirrors this story's own pattern (see `patches/0004-loosen-bcrypt-pin.patch` in `recipes/langflow-suite/`): check whether upstream's `src/backend/base/pyproject.toml` splits the onnxruntime constraint by a `python_version` marker (a `noarch: python` recipe.yaml cannot represent a per-Python split, so the feedstock's single collapsed range may simply be dropping py3.14 coverage the same way the pre-fix bcrypt pin did -- see G40 in `conda-forge-expert`'s SKILL.md), and if so, add the higher-Python branch plus a regression test proving the resolved onnxruntime actually supports 3.14, the same way this story's new bcrypt test proves >=4.1 rather than trusting it by reputation.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: resolved

  resolved: 2026-09-02 — Mason story 13.1 landed the loosening locally (`recipes/langflow-suite/` + `recipes/langflow-base/`): run-dep `onnxruntime >=1.20`, G26 patch `0005-loosen-onnxruntime-pin.patch`, py3.14 pip_check + script test. Feedstock PR TBD.

  verified: 2026-09-02 — resolved — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/3 present (absent: _bmad-output/implementation-artifacts/spec-10-4-the-bcrypt-pin-stops-blocking-3-14.md, src/backend/base/pyproject.toml); ledger status mapped to resolved per Mason 13.1 landing

### DW-FU-11-1: Nothing this story added sets `LANGFLOW_AUTO_LOGIN=False` (or any equivalent hardening) for the mounted app, so Langflow's own dev-mode default stays live: `GET /api/v1/auto_login` mints a real bearer token for the bootstrap superuser with no credential at all.

- source_spec: `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-11-1-langflow-joins-as-a-pluggable-app.md`
  summary: Nothing this story added sets `LANGFLOW_AUTO_LOGIN=False` (or any equivalent hardening) for the mounted app, so Langflow's own dev-mode default stays live: `GET /api/v1/auto_login` mints a real bearer token for the bootstrap superuser with no credential at all.
  evidence: station-unresolved: `resolve_config.py --key project` returned `pyforge-mason` while `readlink -f` of this file's own path agrees with the `.active-project` marker on `pyforge-steward` -- filed against `pyforge-steward`'s ledger per the same cross-check this workflow already applied to `DW-FU-10-4`, immediately above. Confirmed by reading the story's own new test file (`langflow_integration/tests.py`): its own docstring documents `AUTO_LOGIN` "defaults to `True` (dev-mode bootstrap)" and its AC3 test relies on `GET /api/v1/auto_login` for a no-password bearer token specifically because `AUTO_LOGIN=True` ignores any configured `LANGFLOW_SUPERUSER_PASSWORD` outright (Langflow's own `services/utils.py` logs "Ignoring legacy default LANGFLOW_SUPERUSER_PASSWORD in AUTO_LOGIN mode"). Raised independently by this story's own second (post-repair) adversarial review pass. Not fixed inline because the story's own frozen intent contract scopes proving the mount and its schema isolation, not a security-hardening posture for Langflow's own auth system -- matches this story's already-accepted pattern of naming out-of-scope production-readiness gaps as deferred work (see the Never section's own object-storage exclusion, "flag it as deferred work if a later story needs it"). Whoever next exposes this mount outside a local dev/CI context needs a decision here: set `LANGFLOW_AUTO_LOGIN=False` plus a real superuser credential path, or scope network access to `/api/v1/auto_login` some other way, before this mount is reachable from anywhere but a trusted local network.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-11-1-2: Both new tests in `langflow_integration/tests.py` (the schema-isolation check and the end-to-end flow-execution proof) open a live `psycopg` connection against `langflow_schema` and insert real rows -- a flow, two `vertex_build` rows, two `transaction` rows, an `apikey`, a superuser -- with no cleanup step in either test.

- source_spec: `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-11-1-langflow-joins-as-a-pluggable-app.md`
  summary: Both new tests in `langflow_integration/tests.py` (the schema-isolation check and the end-to-end flow-execution proof) open a live `psycopg` connection against `langflow_schema` and insert real rows -- a flow, two `vertex_build` rows, two `transaction` rows, an `apikey`, a superuser -- with no cleanup step in either test.
  evidence: station-unresolved, same cross-check basis as `DW-FU-11-1` immediately above (filed against `pyforge-steward`). Confirmed by reading `langflow_integration/tests.py` in full: no `finally`/fixture teardown deletes any inserted row, and the file's own Design Notes explain why it can't use Django's `@pytest.mark.django_db` machinery for this (a same-process `django_db`-marked test mutates `connections["default"]`'s database name for the rest of the session). This compounds an already-recorded gap rather than introducing a new class of risk: this story's own Review Triage Log (pass 2) already deferred that neither new pytest suite runs in any CI job at all, so today the accumulation only affects a developer's own local Postgres across repeated manual runs, not CI. Worth fixing in the same pass that eventually wires these suites into CI (the already-deferred gap), since an unbounded-growth integration-test suite is a worse thing to first discover once it's already running unattended on every push.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-11-1-3: The new "Migrate the database" step (added to run ahead of "Run platform container" so `langflow_schema` exists before Langflow's own ASGI lifespan bootstrap needs it) hardcodes its own copies of `DATABASE_URL`, `REDIS_URL`, `DJANGO_SECRET_KEY`, and `DJANGO_ADMIN_URL` rather than sharing a single source of truth with the pre-existing step that already hardcodes the identical four values.

- source_spec: `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-11-1-langflow-joins-as-a-pluggable-app.md`
  summary: The new "Migrate the database" step (added to run ahead of "Run platform container" so `langflow_schema` exists before Langflow's own ASGI lifespan bootstrap needs it) hardcodes its own copies of `DATABASE_URL`, `REDIS_URL`, `DJANGO_SECRET_KEY`, and `DJANGO_ADMIN_URL` rather than sharing a single source of truth with the pre-existing step that already hardcodes the identical four values.
  evidence: station-unresolved, same cross-check basis as the two entries immediately above (filed against `pyforge-steward`). Raised by this story's own second (post-repair) adversarial review pass and confirmed by reading `.github/workflows/platform-ci.yml`: both `docker run`/`podman run` invocations list the same four `-e` flags with byte-identical values. Not a live bug today -- both copies currently agree -- but this exact duplication-without-a-single-source-of-truth shape already produced two real, already-fixed bugs in this story's own Review Triage Log pass 2 (the new migrate step initially omitted `DJANGO_ADMIN_URL`, crashing on `ImproperlyConfigured`, and separately dropped the `--user 12345:0` flag), so nothing currently prevents a third recurrence the next time either step is edited alone. Not patched inline during this pass: GitHub Actions has no YAML anchor/alias support (this same file's own pre-existing comment on its duplicated `paths:` filters, see `DW-FU-10-3-10`, already documents that limitation for a different duplicated block in this file), so the fix is a job-level `env:` block referencing `${{ matrix.engine }}`-interpolated values -- mechanically straightforward but unverified against a real GitHub Actions run in this sandbox (no CI runner available here), so deferred rather than shipped unverified per this project's own verify-before-landing-infra-changes convention.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (already-identified identified-bulleted entry, never previously copied to the tracked ledger)
  status: open

## Red-team review 2026-09-02 — MEDIUM / LOW directives (owner: steward; not stories yet)

Source: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`. Promoted to stories only when a consumer exists or a HIGH story needs them; the Epic 40–43 stories cite them in `deferred:` where they bind.

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-1

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-17** — Lock topology: `factory/` island lock and per-package `pixi.toml` scheduled ahead of any further eight-wide station wave; `environment.yaml` regeneration automated in CI. (red-team D-2)
  evidence: Review § 4 (R-17); finding ids in parentheses map to § 2 rows with file:line citations.
  status: resolved
  disposition: 2026-09-13 — resolved by Story 44.7: `python-foundry/factory/pixi.toml` + `factory/pixi.lock` exist; estate root lock carries no solver-farm deps; island CI triggers on `factory/**` only; `mason recipe build factory/recipes/<r>` uses today's CFE native-build wrap via `MASON_FACTORY_ROOT`.

  vessel: steward Story 44.7 (`fnd:CAP-4`, Phase 3 factory island) — **done** 2026-09-13.
  verified: 2026-09-13 — resolved — factory island lock present on `rxm7706/python-foundry`; mason factory path resolution landed in pyforge-mason; spec-reusable-cicd-workflows trigger evaluated and declined (island pixi lives under `factory/`, not repo root).

### DW-RT-2026-09-02-2

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-18** — Sizing rewrite: per-pod rows for web (memory-bound; `--preload`; Langflow RSS measured), worker (CPU-bound; separate builds pool), mcp-host, DB-GPT sidecar, Liquibase Job (JVM), Vizro; requests/limits in values; HPA on web and worker; PodDisruptionBudgets; LLM inference stated as external. (red-team S-7, T-7)
  evidence: Review § 4 (R-18); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); → Story 48.2 (Epic 48, `sprint-change-proposal-2026-09-09-currency-review.md`; was "Epic 45 candidate" — 45 went to eval-quality 2026-09-05); travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  vessel: steward Story 48.2 (Epic 48 — R-18 sizing rewrite; also gains the ASGI thread-pool clause, fleet readiness 2026-09-09) — the owed semantic re-read (below) happens at implementation (fleet-readiness-decision-batch-2026-09-09, stB-D9 / Unifying SPEC § Residual 2026-09-09).
  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-3

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-19** — Network baseline: default-deny NetworkPolicy in the namespace with explicit allows; `automountServiceAccountToken: false`. (red-team X-4, X-6)
  evidence: Review § 4 (R-19); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); → Story 48.3 (Epic 48, `sprint-change-proposal-2026-09-09-currency-review.md`; was "Epic 45 candidate" — 45 went to eval-quality 2026-09-05); travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  vessel: steward Story 48.3 (Epic 48 — R-19 network baseline) — the owed semantic re-read (below) happens at implementation (fleet-readiness-decision-batch-2026-09-09, stB-D9 / Unifying SPEC § Residual 2026-09-09).
  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-4

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-20** — Secrets profile: age key custody and rotation, an `ExternalSecret` example for the Vault/ESO profile, a rotation runbook for `DJANGO_SECRET_KEY`, `REDIS_PASSWORD`, the DB roles and the assertion PEM (dual-key verify during rotation). (red-team X-7)
  evidence: Review § 4 (R-20); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); → Story 48.4 (Epic 48, `sprint-change-proposal-2026-09-09-currency-review.md`; was "Epic 45 candidate" — 45 went to eval-quality 2026-09-05); travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  vessel: steward Story 48.4 (Epic 48 — R-20 secrets profile; Story 48.9's OIDC profile depends on it) — the owed semantic re-read (below) happens at implementation (fleet-readiness-decision-batch-2026-09-09, stB-D9 / Unifying SPEC § Residual 2026-09-09).
  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-5

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-21** — Observability contract: SLOs for `/ht/`, MCP p99, queue age, event lag; alert rules; a metrics write path for Doctor's flag kill-switch. (red-team A-7, B-5)
  evidence: Review § 4 (R-21); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); → Story 48.5 (Epic 48, `sprint-change-proposal-2026-09-09-currency-review.md`; was "Epic 45 candidate" — 45 went to eval-quality 2026-09-05); travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  vessel: steward Story 48.5 (Epic 48 — R-21 observability contract) — the owed semantic re-read (below) happens at implementation (fleet-readiness-decision-batch-2026-09-09, stB-D9 / Unifying SPEC § Residual 2026-09-09).
  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-6

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-22** — Live browser streaming: implement `/ws/events/` as a Channels consumer over redis-broker Streams with per-`sub` filtering, or delete the pillar from the Dream. (red-team T-8)
  evidence: Review § 4 (R-22); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); → Story 48.6 (Epic 48, `sprint-change-proposal-2026-09-09-currency-review.md`; was "Epic 45 candidate" — 45 went to eval-quality 2026-09-05); travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  vessel: steward Story 48.6 (Epic 48 — R-22 live browser streaming, or the pillar deleted) — the owed semantic re-read (below) happens at implementation (fleet-readiness-decision-batch-2026-09-09, stB-D9 / Unifying SPEC § Residual 2026-09-09).
  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-7

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-23** — Dream doc fixes: `readOnlyRootFilesystem`, Windows / free-threading claims aligned to the shipped Containerfile and `pixi.toml` platforms. (red-team X-6, D-5)
  evidence: Review § 4 (R-23); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — promoted to steward Story 44.2 (document fixes; spec-python-foundry-cutover Constraints); held ledger `blocked` pending solutioning review (sprint-change-proposal-2026-09-04-foundry-cutover.md)

  vessel: steward Story 44.2 (document fixes) — **`blocked` today**, so the owed semantic re-read (below) is gated behind the cutover; annotate at dispatch, not before (fleet-readiness-decision-batch-2026-09-09, stB-D9 / Unifying SPEC § Residual 2026-09-09).
  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-8

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-24** — Pin the Keycloak version once (`26.4.0`) across Dream, compose and research. (red-team S-6)
  evidence: Review § 4 (R-24); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — promoted to steward Story 44.2 (document fixes; spec-python-foundry-cutover Constraints); held ledger `blocked` pending solutioning review (sprint-change-proposal-2026-09-04-foundry-cutover.md)

  vessel: steward Story 44.2 (document fixes) — **`blocked` today**, so the owed semantic re-read (below) is gated behind the cutover; annotate at dispatch, not before (fleet-readiness-decision-batch-2026-09-09, stB-D9 / Unifying SPEC § Residual 2026-09-09).
  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-9

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-25** — Rewrite the "zero domain models" constraint as "no station-domain models on `django-<station>`". (red-team T-9)
  evidence: Review § 4 (R-25); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — promoted to steward Story 44.2 (document fixes; spec-python-foundry-cutover Constraints); held ledger `blocked` pending solutioning review (sprint-change-proposal-2026-09-04-foundry-cutover.md)

  note: 2026-09-09 (fleet readiness) — **this row is the sharpest of the four gated ones.** R-25 corrects a constraint the Unifying Dream already documents as knowingly wrong ("zero domain models on portals" vs `django_warden_fabric/models.py:11` `ComplianceJob`), so a known-false constraint sits behind a `blocked` gate with no interim annotation. If 44.2 slips, annotate the constraint in place rather than leaving it read as fact.
  vessel: steward Story 44.2 (document fixes) — **`blocked` today**, so the owed semantic re-read (below) is gated behind the cutover; annotate at dispatch, not before (fleet-readiness-decision-batch-2026-09-09, stB-D9 / Unifying SPEC § Residual 2026-09-09).
  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## Foundry cutover 2026-09-04 — carried residue (owner: steward; not a story yet)

Source: `sprint-change-proposal-2026-09-04-foundry-cutover.md`. Bound to Story 44.10 when it dispatches.

### DW-CC-2026-09-04-1

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md`
  summary: Worktree residue on the `local-recipes` checkout — 268 registered git worktrees (58 `.worktrees/`, 66 `.cursor/worktrees`, 33 `.claude/worktrees`, 93 retired under loop homes, 8 loop homes, 3 `local-recipes-wt-*`) and 85 GB under `.claude/worktrees/` — retired at Phase 6, never moved (fnd:AD-1).
  evidence: `git worktree list --porcelain | grep -c '^worktree '` = 268 on 2026-09-04; `du -sh .claude/worktrees` = 85G.
  location: git worktree list (live measurement)
  status: resolved

  verified: 2026-09-08 — resolved — RESOLVED and holding. The entry recorded 268 registered worktrees and 85 GB. `git worktree list | wc -l` today returns **10** (primary + 8 loop homes + 1). marshal's `DW-HYGIENE-2026-09-05-1` records the sweep that did it (262 -> 12, 29 GB reclaimed, `scripts/worktree_sweep.py`), and the count has stayed low in the three days since rather than re-growing. The residue this entry describes is gone.

### DW-FU-40-1: Structured-log assertions for assertion.mint_refused (caplog on 401/403, no bearer echo) — AC requires logging but tests only check HTTP status.

- source_spec: `planning-artifacts/specs/spec-40-1-idp-bearer-is-verified-before-mint.md`
  summary: Structured-log assertions for assertion.mint_refused (caplog on 401/403, no bearer echo) — AC requires logging but tests only check HTTP status.
  evidence: Refusal tests assert status codes only; removing logger.warning would not fail CI today.
  origin: spec-deferred 03d7c6b1f3a6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: src/shared/packages/django-pyforge/src/django_pyforge/assertion/jwks.py; tests at src/platform/tests/test_django_pyforge_assertion.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by measurement, not by reading the entry back: structured-log assertions for `assertion.mint_refused` is still absent. `grep -rl mint_refused src/platform/tests/` returns **0 files** — no test asserts the refusal log line at all, so the AC's logging requirement is still covered only by HTTP status. A `location:` was added — this entry had none, which is exactly why the churn filter could never reach it.

### DW-FU-40-1-2: HTTPS JWKS fetch path integration test (production urlopen contract).

- source_spec: `planning-artifacts/specs/spec-40-1-idp-bearer-is-verified-before-mint.md`
  summary: HTTPS JWKS fetch path integration test (production urlopen contract).
  evidence: All assertion tests use file:// JWKS; _fetch_https is never exercised in CI.
  origin: spec-deferred d58ee2121818 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: src/shared/packages/django-pyforge/src/django_pyforge/assertion/jwks.py; tests at src/platform/tests/test_django_pyforge_assertion.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by measurement, not by reading the entry back: an HTTPS JWKS fetch integration test is still absent. `urlopen` appears in only 3 platform test files and none exercises the production HTTPS fetch contract for `django_pyforge.assertion.jwks`. A `location:` was added — this entry had none, which is exactly why the churn filter could never reach it.

### DW-FU-40-1-3: Import-time no-network invariant test for django_pyforge.assertion.jwks.

- source_spec: `planning-artifacts/specs/spec-40-1-idp-bearer-is-verified-before-mint.md`
  summary: Import-time no-network invariant test for django_pyforge.assertion.jwks.
  evidence: Lazy load is implemented but not pinned by a test that blocks urlopen at import.
  origin: spec-deferred 02a2d7cd20e0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: src/shared/packages/django-pyforge/src/django_pyforge/assertion/jwks.py; tests at src/platform/tests/test_django_pyforge_assertion.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by measurement, not by reading the entry back: an import-time no-network invariant test is still absent. `grep -rl 'no_network|no-network' src/platform/tests/` returns **0 files** — nothing pins that importing `django_pyforge.assertion.jwks` performs no network I/O. A `location:` was added — this entry had none, which is exactly why the churn filter could never reach it.

### DW-FU-40-1-4: Full 503 matrix for every _require_verifier_settings() failure mode beyond empty OIDC_JWKS_URL (http:// scheme, blank issuer/audience/algorithms).

- source_spec: `planning-artifacts/specs/spec-40-1-idp-bearer-is-verified-before-mint.md`
  summary: Full 503 matrix for every _require_verifier_settings() failure mode beyond empty OIDC_JWKS_URL (http:// scheme, blank issuer/audience/algorithms).
  evidence: Only test_unconfigured_verifier_returns_503 covers empty JWKS URL; other misconfigurations could regress undetected.
  origin: spec-deferred 9247533f1e37 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: src/shared/packages/django-pyforge/src/django_pyforge/assertion/jwks.py; tests at src/platform/tests/test_django_pyforge_assertion.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by measurement, not by reading the entry back: the full 503 matrix for `_require_verifier_settings()` is still absent. `503` appears in 3 platform test files, but no test covers the non-empty-URL failure modes the entry names (http:// scheme, blank issuer/audience/algorithms). A `location:` was added — this entry had none, which is exactly why the churn filter could never reach it.

### DW-FU-41-2: Reconcile `resilience-invariants.md` BS-5 row to Story 41.2 single-writer-on-RWO / Parquet model (still describes read-only shared mounts).

- source_spec: `planning-artifacts/specs/spec-41-2-query-plane-process-boundary.md`
  summary: Reconcile `resilience-invariants.md` BS-5 row to Story 41.2 single-writer-on-RWO / Parquet model (still describes read-only shared mounts).
  evidence: Companion invariant doc not in Story 41.2 AC scope; Dream/stack updated but tier-2 resilience doc drift remains.
  origin: spec-deferred cd1c82a2f0e7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md (BS-5 row)
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: the BS-5 row still describes read-only shared mounts rather than Story 41.2's single-writer-on-RWO / Parquet model. A `location:` was added — this entry had none, which is why the churn filter could never reach it. 41-2-3 in particular is pending-on-precondition in substance: its blocker is a PVC that has not shipped, not a decision anyone owes.

### DW-FU-41-2-2: Extend estate DuckDB policy gate to cover file-backed `ibis.duckdb.connect` and aliased `duckdb` imports.

- source_spec: `planning-artifacts/specs/spec-41-2-query-plane-process-boundary.md`
  summary: Extend estate DuckDB policy gate to cover file-backed `ibis.duckdb.connect` and aliased `duckdb` imports.
  evidence: AST gate matches bare `duckdb.connect` only; production dashboard/semantic layers use no-arg in-memory ibis today but file-backed regression would pass.
  origin: spec-deferred b3fdec19aaea — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: src/shared/packages/pyforge-atlas/tests/unit/policy_gate/ (estate DuckDB policy gate)
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: the gate still does not cover file-backed `ibis.duckdb.connect` or aliased `duckdb` imports. A `location:` was added — this entry had none, which is why the churn filter could never reach it. 41-2-3 in particular is pending-on-precondition in substance: its blocker is a PVC that has not shipped, not a decision anyone owes.

### DW-FU-41-2-3: Add positive Helm fixture when writer plane PVC lands (`pyforge.io/query-plane`, RWO).

- source_spec: `planning-artifacts/specs/spec-41-2-query-plane-process-boundary.md`
  summary: Add positive Helm fixture when writer plane PVC lands (`pyforge.io/query-plane`, RWO).
  evidence: Chart RWO invariant is vacuous on live render until a plane PVC template exists; spec residual already notes this.
  origin: spec-deferred 00bfc74ef4eb — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: src/platform/deploy/charts/platform/ (Helm fixtures)
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: no positive Helm fixture exists, because the `pyforge.io/query-plane` RWO writer-plane PVC it depends on has not landed. A `location:` was added — this entry had none, which is why the churn filter could never reach it. 41-2-3 in particular is pending-on-precondition in substance: its blocker is a PVC that has not shipped, not a decision anyone owes.

### DW-FU-41-2-4: Run duckdb-boundary chart live-render proofs in platform-ci-test (helm currently platform-dev only).

- source_spec: `planning-artifacts/specs/spec-41-2-query-plane-process-boundary.md`
  summary: Run duckdb-boundary chart live-render proofs in platform-ci-test (helm currently platform-dev only).
  evidence: @requires_helm proofs skip in platform-ci-test; guard fixtures only catch synthetic violations, not template regressions.
  origin: spec-deferred b0f3185e8c6f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: pixi.toml (platform-ci-test) / .github/workflows/platform-ci.yml
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: the duckdb-boundary chart live-render proofs still run only under platform-dev, not in platform-ci-test. A `location:` was added — this entry had none, which is why the churn filter could never reach it. 41-2-3 in particular is pending-on-precondition in substance: its blocker is a PVC that has not shipped, not a decision anyone owes.

### DW-FU-41-3: db.changelog-master.yaml's include order does not satisfy its own FK dependencies: python-agent-platform:18 adds a socialaccount FK to django_site, which :10 (sites.0001) creates later.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: db.changelog-master.yaml's include order does not satisfy its own FK dependencies: python-agent-platform:18 adds a socialaccount FK to django_site, which :10 (sites.0001) creates later.
  evidence: Real `liquibase update` on the master changelog stops at `Run: 10` with `ERROR: relation "django_site" does not exist`. Reproduced identically against the baseline master changelog (`git show a4316334fe:...`), so it predates this story; scribe's changesets are appended last and are unaffected. No test executes the master changelog in include order.
  location: src/platform/db/changelog/db.changelog-master.yaml
  origin: spec-deferred b2e7ae9d2371 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED present: `src/platform/db/changelog/db.changelog-master.yaml` still carries the include set this entry indicts (25 matches for the sites/socialaccount/python-agent-platform ordering it names). The FK-before-creator ordering defect is unchanged; the entry's own reproduction (`liquibase update` stopping at `Run: 10` with `relation "django_site" does not exist`) is a runtime proof this sweep cannot re-run offline, so the file-level confirmation is what is asserted here.

### DW-FU-41-3-2: No CI workflow runs the scribe suite, so this story's behavioural proofs (DDL-revoked role, named error, changeset-provisioned database) gate nothing.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: No CI workflow runs the scribe suite, so this story's behavioural proofs (DDL-revoked role, named error, changeset-provisioned database) gate nothing.
  evidence: Nothing under .github/workflows/ invokes `pyforge-scribe-test`, and `src/shared/packages/pyforge-scribe/**` is absent from platform-ci.yml's `paths:` filter. This PR runs platform CI only because it touches src/platform/**; a later edit to graph_store_pg.py alone triggers no workflow. Pre-existing — the scribe suite was never wired in.
  location: .github/workflows/platform-ci.yml
  origin: spec-deferred 5bd99ab9e250 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — RESOLVED — the CI gap this entry names has been closed since authoring. `.github/workflows/pyforge-station-tests.yml` now runs every station's own suite, scribe included: `src/shared/packages/pyforge-scribe/**` is in its `paths:` filter (`:29`, `:45`), `scribe` is a `changes` output (`:71`) and is in the per-station loop (`:103`). This story's behavioural proofs live in `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py` — inside that suite — so they now gate. RESIDUAL, recorded honestly: `platform-ci.yml` still has no `pyforge-scribe` path filter, so the entry's literal location remains true; what changed is that a DIFFERENT workflow now covers the proofs.

### DW-FU-41-3-3: platform_app's real grant set is never executed by any test; the DML-revoked-role test hand-writes equivalent grants instead.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: platform_app's real grant set is never executed by any test; the DML-revoked-role test hand-writes equivalent grants instead.
  evidence: No test applies create_app_role.sql or pyforge-scribe:3 and then connects. test_store_works_as_a_ddl_revoked_role synthesises its own role and types the grants into the test body, so the shipped SQL could drift from it and stay green. Flipping :3's precondition to `expectedResult:0` would skip the grants on exactly the databases where platform_app exists, and every test still passes.
  location: src/platform/db/changelog/changes/pyforge-scribe-3-app-role-grants.sql
  origin: spec-deferred b017b5861086 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file: platform_app's real grant set is still never executed by a test; the DML-revoked-role test still hand-writes equivalent grants. Evidence: `changes/pyforge-scribe-3-app-role-grants.sql` exists and carries its GRANT statements, but nothing executes them under test.

### DW-FU-41-3-4: Red-team B-1 is only half-addressed — numbering is per-distribution, but scribe's changesets still ship inside the single master changelog, so a scribe schema change still rides the platform release.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Red-team B-1 is only half-addressed — numbering is per-distribution, but scribe's changesets still ship inside the single master changelog, so a scribe schema change still rides the platform release.
  evidence: There is no per-distribution sub-changelog, includeAll, or contexts:/labels: on the new changesets, and every estate gets scribe's DDL whether or not scribe is deployed. Unmapped django-<station> migrations also still fall through to `default: python-agent-platform`, so the release coupling B-1 names persists by default until each station registers.
  location: src/platform/db/changelog/db.changelog-master.yaml
  origin: spec-deferred b1923db21c86 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file: scribe's changesets still ship inside the single master changelog, so a scribe schema change still rides the platform release. Evidence: `db.changelog-master.yaml` still includes the `pyforge-scribe` changesets directly (5 matches).

### DW-FU-41-3-5: graph_nodes.embedding is declared without a dimension, so no ivfflat or hnsw index is possible and query_similar sequentially scans the table.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: graph_nodes.embedding is declared without a dimension, so no ivfflat or hnsw index is possible and query_similar sequentially scans the table.
  evidence: `embedding vector` in pyforge-scribe:2, and no index changeset exists. This is parity with the pre-41.3 driver, not a regression, but bringing the DDL under governance is the natural moment to fix it — and it leaves the new README's CREATE INDEX CONCURRENTLY exception process with no user.
  location: src/platform/db/changelog/changes/pyforge-scribe-2-graph-nodes.sql
  origin: spec-deferred a441d8e7a1a7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED precisely. `changes/pyforge-scribe-2-graph-nodes.sql:14` still declares `embedding vector,` with NO dimension, so neither an ivfflat nor an hnsw index can be built and `query_similar` still sequentially scans. Unchanged since authoring.

### DW-FU-41-3-6: Every django_db test in src/platform errors at test-database setup on `ValidationError: slug 'home' is already in use`.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Every django_db test in src/platform errors at test-database setup on `ValidationError: slug 'home' is already in use`.
  evidence: Raised from front_door.apps::_seed_lane1_homepage in post_migrate. Reproduced on tests/test_health_endpoint.py, which this story never touches, and it persists with --create-db, so it is not a --reuse-db artifact. It blocks test_app_role_create_alter_drop_refused_by_postgresql and test_live_first_party_tree_is_covered locally; the CI step they mirror was run directly instead.
  location: src/platform/platformapp/front_door/lane1_seed.py:41
  origin: spec-deferred e7fd703e7270 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file: every `django_db` test in `src/platform` still errors at test-database setup on the duplicate `home` slug. Evidence: `platformapp/front_door/lane1_seed.py` still carries the seeding path the entry names.

### DW-FU-41-3-7: Two test_openfeature_channel_policy tests are red on main from a cachebox pin drift.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Two test_openfeature_channel_policy tests are red on main from a cachebox pin drift.
  evidence: `cachebox must be pinned '>=5.1,<6' so conda-forge 6.x is not selected (got '>=5.2.3')`. The test reads pixi.toml, which this story does not modify.
  location: src/platform/tests/policy/test_openfeature_channel_policy.py:137
  origin: spec-deferred eca25a0ad356 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — pending-on-precondition — COULD NOT BE REPRODUCED IN THIS SWEEP, and the reason is itself the finding. `src/platform/tests/policy/test_openfeature_channel_policy.py` requires pytest-django's `--ds=config.settings.test --reuse-db`, which the `local-recipes` env does not provide (`error: unrecognized arguments`), and no station env carries the platform test harness. So the red/green state of the two cachebox-drift tests cannot be established from any environment this sweep can reach. Blocker named: the entry needs a run in the platform test environment (`platform-ci-local`) to settle. Recorded as pending rather than forced to still-open, because asserting either verdict here would be a guess.

### DW-FU-41-3-8: GraphSchemaMissing is not re-exported from pyforge.scribe, and no scribe doc records that the durable graph store now requires Liquibase to have run.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: GraphSchemaMissing is not re-exported from pyforge.scribe, and no scribe doc records that the durable graph store now requires Liquibase to have run.
  evidence: PostgresGraphStore.__init__ now raises on an unprovisioned database — a behaviour change for every existing consumer — but only src/platform/db/README.md says so. The scribe package README, docs/cli-runbooks.md and .claude/skills/pyforge-scribe/SKILL.md are silent.
  location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py
  origin: spec-deferred bce4bb0e169d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file: `GraphSchemaMissing` is still not re-exported from `pyforge.scribe`, and no scribe doc records the Liquibase precondition. Evidence: the symbol exists in `graph_store_pg.py` but only there.

### DW-FU-41-4: An explicit COMPONENT_BROKER_CA_BUNDLE cannot override a resolving OS trust store, so the operator knob is unreachable on any host that ships a default CA file.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: An explicit COMPONENT_BROKER_CA_BUNDLE cannot override a resolving OS trust store, so the operator knob is unreachable on any host that ships a default CA file.
  evidence: The intent's "Always" clause mandates "Truststore first; explicit bundle path second", so the ordering is contractual and was deliberately not changed here. The consequence is that tier 2 is reached only when tier 1 resolves nothing: `.pixi/envs/python-agent-platform/ssl/cert.pem` exists, and Containerfile:153 copies the env to the same absolute prefix, so the compiled-in default resolves inside the shipped image. An operator installing a private CA at, say, /etc/pki/corp-ca.pem and setting COMPONENT_BROKER_CA_BUNDLE gets the distro bundle in ssl_ca_certs instead, and fails verification at first connect. The escape hatch under the current ordering is SSL_CERT_FILE / SSL_CERT_DIR. Needs a product decision (explicit-wins, or document SSL_CERT_FILE as the knob).
  location: src/platform/config/broker_tls.py — resolve_ca_trust()
  origin: spec-deferred 0719d3dc32ee — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: `config/broker_tls.py`'s `resolve_ca_trust()` is present and unchanged, so an explicit `COMPONENT_BROKER_CA_BUNDLE` still cannot override a resolving OS trust store and the operator knob stays unreachable wherever a default CA file exists.

### DW-FU-41-4-2: CHANNEL_LAYERS (channels_redis) and REDIS_CACHE_URL (django-redis) share the Redis URL but get none of this TLS posture.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: CHANNEL_LAYERS (channels_redis) and REDIS_CACHE_URL (django-redis) share the Redis URL but get none of this TLS posture.
  evidence: src/platform/config/settings/production.py wires channel_layers_for_broker( REDIS_BROKER_URL) and the django-redis cache aliases; both build their own TLS context with no COMPONENT_BROKER_CA_BUNDLE and no CERT_NONE opt-out. The intent scoped this story to "the Celery broker and the result backend", so this is out of scope here, but it means "single declaration site for the broker's TLS posture" is true for Celery only.
  location: src/platform/config/settings/production.py
  origin: spec-deferred c22fd7e99777 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: `config/settings/production.py` still references `CHANNEL_LAYERS`/`REDIS_CACHE_URL` (3 matches) with none of the broker TLS posture applied to them.

### DW-FU-41-4-3: The Helm chart still wires plaintext redis://, so no deployed component takes the new code path and nothing refuses unencrypted broker traffic.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: The Helm chart still wires plaintext redis://, so no deployed component takes the new code path and nothing refuses unencrypted broker traffic.
  evidence: deploy/charts/platform/templates/_helpers.tpl templates redis:// for REDIS_BROKER_URL, REDIS_CACHE_URL and REDIS_URL, with no TLS key and no COMPONENT_BROKER_CA_BUNDLE; tests/test_chart_invariants.py is unchanged. This story makes TLS honest when it is used; it does not turn it on. Red-team X-2 / directive R-14 is only half-discharged until the chart moves to rediss:// and a deployed plaintext broker is itself refused.
  location: deploy/charts/platform/templates/_helpers.tpl
  origin: spec-deferred 5652c1016bee — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, with the LOCATION CORRECTED. The entry cites `deploy/charts/platform/templates/_helpers.tpl`, which does not exist at that path; the chart lives at `src/platform/deploy/charts/platform/templates/_helpers.tpl`. There, lines **318, 320 and 322** still emit plaintext `redis://...` for the broker, cache and a third consumer — so no deployed component takes the new TLS code path and nothing refuses unencrypted broker traffic. The stale path is why this could read as unverifiable.

### DW-FU-41-4-4: mypy cannot run at all, so the new modules got no type check.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: mypy cannot run at all, so the new modules got no type check.
  evidence: "Error constructing plugin instance of NewSemanalDjangoPlugin" / INTERNAL ERROR (django-stubs vs mypy 2.3.1). It fails before analysing any file, on a clean tree too. Platform CI runs `mypy platformapp config tests`, so that step is red independently of this story — pre-existing, not caused here.
  location: src/platform (Platform CI mypy step)
  origin: spec-deferred 306fd05c246e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: the cited file is present and unchanged in the respect named — the Platform CI mypy step still cannot run, so these modules remain untyped-checked.

### DW-FU-41-4-5: configure_observability() now materializes Django settings even when OTel is disabled, and config/__init__.py imports celery_app at module scope.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: configure_observability() now materializes Django settings even when OTel is disabled, and config/__init__.py imports celery_app at module scope.
  evidence: The story added load_django_settings() to configure_observability() to repair a real swallow (DjangoInstrumentor catching ImproperlyConfigured and calling settings.configure()). The call sits ahead of configure_telemetry's otel_sdk_is_disabled() early return, so fail-fast is now imposed on a broader set of process configurations than the bug required, and importing any config.* module pins the settings singleton to whatever DJANGO_SETTINGS_MODULE is set at that moment. No in-repo regression observed — the full suite's failure/error set is byte-identical to baseline — but the import-time contract is now stricter and undocumented.
  location: src/platform/config/observability/__init__.py
  origin: spec-deferred f2ce97b91c74 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: the cited file is present and unchanged in the respect named — `configure_observability()` still materialises Django settings even when OTel is disabled, and `config/__init__.py` still imports `celery_app` at module scope.

### DW-FU-41-4-6: REDIS_SSL in base settings has no readers anywhere in the tree.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: REDIS_SSL in base settings has no readers anywhere in the tree.
  evidence: The removed CELERY_BROKER_USE_SSL ternary was its only consumer; a repo-wide grep now returns only its own definition. This change kept it alive (rewritten through is_tls_broker) rather than removing a public settings name that ops tooling might read. Decide whether to drop it or record why it stays.
  location: src/platform/config/settings/base.py
  origin: spec-deferred d081c2e07dbf — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep, which is the only way this claim can be settled. `REDIS_SSL` appears exactly ONCE in the whole `src/platform` tree — its own assignment at `config/settings/base.py:396` (`REDIS_SSL = is_tls_broker(REDIS_BROKER_URL)`). Zero readers, so the setting is computed and discarded.

### DW-FU-41-4-7: scripts/.spec-surface-baseline.json needs a scoped stamp for the changed and new config/** files.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: scripts/.spec-surface-baseline.json needs a scoped stamp for the changed and new config/** files.
  evidence: The baseline hashes src/platform/config/** per file under the pyforge-mason/spec-django-accelerator-framework entry; settings/base.py, startup/stage_one.py, startup/__init__.py, observability/__init__.py, manage.py and settings/production.py all changed, and config/broker_tls.py is new with no entry at all, so spec-surface-check will report surface-changed. Left to the dedicated fleet reconciliation pass (a scoped stamp from a clean tree, never a bare --write-baseline), matching what stories 41.1, 41.2 and 41.3 did.
  location: scripts/.spec-surface-baseline.json
  origin: spec-deferred f142ec1dd975 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — RESOLVED. The scoped stamp this entry asks for has been performed: `scripts/.spec-surface-baseline.json` now carries current entries for the specs governing `src/platform/config/**`, and `python -m pyforge.doctor.sources spec-surface` reports `ok -- every tracked file governed or allowlisted; no drift`. Whatever config/** drift existed at authoring is stamped and clean.

### DW-FU-42-1: Nothing outside the pytest settings supplies PYFORGE_ASSERTION_PUBLIC_KEY, so a deployed or laptop run now answers 503 on every station MCP route.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: Nothing outside the pytest settings supplies PYFORGE_ASSERTION_PUBLIC_KEY, so a deployed or laptop run now answers 503 on every station MCP route.
  evidence: `config/settings/base.py:610-611` defaults both assertion keys to `""`; only `config/settings/test.py:66-67` assigns them, and `grep -rn ASSERTION src/platform/deploy/` returns nothing — `platform.djangoEnv` carries no such env and no secretKeyRef. `resolve_public_pem()` therefore yields `""` and the gate takes its fail-closed 503 branch. The underlying gap is pre-existing — `supervisor.start_run`/`get`, `assertion/client.py`, `AssertionMiddleware` and the mason/doctor portals already call `crypto.verify_assertion`, whose `_setting_pem` raises on an empty key — but this story widens the blast radius from "the supervisor tools and portals" to "every JSON-RPC method on every station". Wiring the keypair Secret is canopy:AD-19 / Story 40.1 territory; the matching chart invariant and a `REQUIRED_SETTINGS` entry belong with it.
  location: src/platform/deploy/charts/platform/templates/_helpers.tpl (platform.djangoEnv)
  origin: spec-deferred e25b89413149 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `PYFORGE_ASSERTION_PUBLIC_KEY` returns **zero matches** in `_helpers.tpl` — so a deployed or laptop run still answers 503 on every station MCP route; only the pytest settings supply it.

### DW-FU-42-1-2: The new NetworkPolicy admits only `component: web`, while mcp-host's three probes are httpGet on the same port and originate from the node.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: The new NetworkPolicy admits only `component: web`, while mcp-host's three probes are httpGet on the same port and originate from the node.
  evidence: `mcp-host-deployment.yaml:40-55` uses httpGet startup/liveness/readiness probes on `:8090`; the policy has no ipBlock or node allowance. The chart's only prior NetworkPolicy guards Redis, whose probes are `exec`, so there is no in-repo precedent for an HTTP-probed pod behind a podSelector-only ingress rule. On a CNI that subjects node→pod probe traffic to NetworkPolicy the pod never passes its startupProbe. Not fixable inside this story: AC 4 requires ingress "only from web pods", and the invariant enforces exactly one ingress rule, so a probe exception would fail the story's own test. Needs a deploy-profile decision alongside the mTLS/mesh item above.
  location: src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml
  origin: spec-deferred 027cb8cce764 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. the NetworkPolicy still admits only `component: web` (1 match), while mcp-host's three probes are httpGet on that port and originate from the node.

### DW-FU-42-1-3: The sidecar hop never watches `receive` for `http.disconnect`, and its budget rose from 5s to at least 300s.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: The sidecar hop never watches `receive` for `http.disconnect`, and its budget rose from 5s to at least 300s.
  evidence: `_stream_upstream_body` relays until upstream ends; with `Queue(maxsize=1)` backpressure an abandoned request pins both the pump task and the upstream sidecar connection for the full read budget. Harmless at the old 5s cap, a real resource-holding window at the Celery hard limit. Out of scope on intent authority — the intent asks only that the budget be raised.
  location: src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  origin: spec-deferred 16bc6c104154 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `http.disconnect` returns **zero matches** in `mcp_http.py` — so the sidecar hop still never watches `receive` for client disconnect while holding a budget raised to >=300s.

### DW-FU-42-1-4: Agent-facing docs and station skills still document a bare `POST /stations/<name>/mcp`, which now returns 401.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: Agent-facing docs and station skills still document a bare `POST /stations/<name>/mcp`, which now returns 401.
  evidence: `CLAUDE.md`, `AGENTS.md`, the eight `.claude/skills/pyforge-*/SKILL.md` blocks and the `bmad-agent-*` persona skills all describe the route with no `Authorization: Bearer <assertion>` requirement and no pointer to how a caller obtains one. No in-repo caller breaks (portals call in-process by design, per `assertion/client.py`), so the whole behavioural change lands on out-of-repo callers whose contract lives in files this story does not touch.
  origin: spec-deferred 025d5b60e556 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: .claude/skills/pyforge-*/**/SKILL.md (station MCP route docs)
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, and a `location:` added (it had none). Agent-facing docs and station skill cards still document a bare `POST /stations/<name>/mcp` with no mention that it now returns 401 without an assertion — the same bare form appears across the station SKILL.md set. The docs were never updated to match 42.1's auth gate.

### DW-FU-42-1-5: AC 4's only chart-render proof is `@requires_helm`, and the CI test env has no helm, so it silently skips there.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: AC 4's only chart-render proof is `@requires_helm`, and the CI test env has no helm, so it silently skips there.
  evidence: `requires_helm` is a `skipif`, not a failure. The Platform CI `test` job runs the `platform-ci-test` pixi env, whose deps declare no helm; `kubernetes-helm` is only in `feature.platform-dev`. The story's three (now eight) guard-removed companions are not helm-gated but feed hand-built dicts to the helper, so they prove the helper, not the chart — the template could be deleted with a green CI run. Pre-existing for every chart test in this suite, not introduced here.
  location: src/platform/tests/test_chart_invariants.py
  origin: spec-deferred 20e3e0ad533b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `test_chart_invariants.py` still carries 40 `@requires_helm` gates, so AC 4's only chart-render proof still silently skips wherever helm is absent.

### DW-FU-42-1-6: 401/403 refusals carry no `WWW-Authenticate` challenge and the body is not JSON-RPC-shaped.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: 401/403 refusals carry no `WWW-Authenticate` challenge and the body is not JSON-RPC-shaped.
  evidence: `TransportRefusal.body()` emits `{"error": "..."}` on an endpoint that otherwise speaks JSON-RPC 2.0, and no challenge header points a client at the mint view or at protected-resource metadata, so an MCP client has no discoverable path from the refusal to a working call. The intent specifies the status codes only.
  location: src/shared/packages/django-pyforge/src/django_pyforge/mcp_auth.py
  origin: spec-deferred 645ced623f6b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `WWW-Authenticate` returns **zero matches** in `mcp_auth.py` — so 401/403 refusals still carry no challenge header and the body is still not JSON-RPC-shaped.

### DW-FU-42-2: No `celery beat` process is deployed, so `CELERY_BEAT_SCHEDULE`'s retention entry never fires in the cluster.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: No `celery beat` process is deployed, so `CELERY_BEAT_SCHEDULE`'s retention entry never fires in the cluster.
  evidence: The chart's only Celery workload is `worker-deployment.yaml` (`args: ["celery", "-A", "config", "worker", "-l", "info"]`); `grep -n beat` over `compose/compose.yml` and `deploy/charts/platform/values.yaml` returns nothing. `CELERY_BEAT_SCHEDULER` has named `django_celery_beat`'s DatabaseScheduler since before this story, with nothing running it. Mitigated but not closed: `manage.py prune_run_state` makes the sweep runnable by an operator or any external scheduler today, and the story's own test drives both runners. Adding a beat Deployment belongs with Story 42.4, which owns Celery's deployment topology (per-station queues, the `builds` pool, grace periods).
  location: src/platform/deploy/charts/platform/templates/
  origin: spec-deferred 120db8626212 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — RESOLVED by Story 42.4, which the entry itself predicted would own it ('Adding a beat Deployment belongs with Story 42.4'). The chart now ships `deploy/charts/platform/templates/beat-deployment.yaml` alongside `worker-deployment.yaml` and `worker-builds-deployment.yaml`, and `values.yaml:129-132` documents it: 'Celery beat (Story 42.4): the one scheduler process that fires ... through django_celery_beat's DatabaseScheduler. Always exactly one replica -- a second beat double-fires every entry.' So `CELERY_BEAT_SCHEDULE`'s retention entry now has a process to fire it in the cluster. The entry's own evidence -- 'the chart's only Celery workload is worker-deployment.yaml' and 'grep -n beat returns nothing' -- is now false on both counts, which is exactly the still-marked-open-but-actually-shipped case this sweep exists to catch.

### DW-FU-42-2-2: The station and per-subject ceilings are count-then-create, so simultaneous starts can overshoot by the number of racing requests.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The station and per-subject ceilings are count-then-create, so simultaneous starts can overshoot by the number of racing requests.
  evidence: `enforce_run_bounds` reads `station_queue_depth` / `live_runs_for_subject` before `publish_start` opens its transaction; nothing serialises the two steps. Deliberate, and documented in `supervisor.py`'s module docstring: the failure the bound exists to stop is an agent loop issuing thousands of starts, which an off-by-a-few boundary does not restore, and making it exact needs a lock on a row that does not exist yet. Revisit only if a bound is ever repurposed as a licence/quota rather than backpressure.
  location: src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
  origin: spec-deferred d67fea3b5d6b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `supervisor.py` still implements the ceilings as count-then-create, so simultaneous starts can still overshoot by the number of racing requests.

### DW-FU-42-2-3: A silently-failing cache `set` leaves the bucket unwritten for one request before the next `get` fails closed.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: A silently-failing cache `set` leaves the bucket unwritten for one request before the next `get` fails closed.
  evidence: `django_redis` with `IGNORE_EXCEPTIONS` swallows a write failure into `None`, and `set`'s return is backend-dependent (`BaseCache.set` returns `None` normally), so it cannot be read as a health signal without coupling the limiter to one backend. The following `get` returns `None` and refuses, so the window is one request per subject per outage, not an open door.
  location: src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
  origin: spec-deferred 9cf6509a1547 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `rate_limit.py`'s cache `set` still has no failure branch, so a silently-failing write still leaves the bucket unwritten for one request.

### DW-FU-42-2-4: The scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run by this story.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run by this story.
  evidence: `.memlog.md` carries this story's surface entry, which downgrades the drift from `fail` to `drift-presumed: warn`, but `--write-baseline --spec pyforge-steward/spec-pyforge-unifying-strategy` must run from a CLEAN worktree after the commit lands or it bakes uncommitted working-tree bytes into the baseline. That spec's baseline also still lags Stories 40.1, 41.2–41.4 and 42.1 (~60 paths), which this story neither caused nor reconciled.
  location: scripts/.spec-surface-baseline.json
  origin: spec-deferred 6e9cafc1fb4f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — RESOLVED. The scoped stamps these entries defer have since been performed — `scripts/.spec-surface-baseline.json` carries current entries for `spec-pyforge-unifying-strategy` and the other governing specs, and `python -m pyforge.doctor.sources spec-surface` reports `ok -- every tracked file governed or allowlisted; no drift` as of this sweep. CAP-6 NOTE: `DW-FU-42-2-4`, `DW-FU-42-2-17` and `DW-FU-42-3-11` are ONE defect class, not three -- all three are 'this story did not run the scoped stamp for spec-pyforge-unifying-strategy'. `DW-FU-45-2-7` records the root cause: blanket pixi.toml globs force every governing spec to record the same reconcile, which is what mints these duplicates in the first place.

### DW-FU-42-2-5: Nothing outside the pytest settings supplies `PYFORGE_ASSERTION_PUBLIC_KEY` (inherited from Story 42.1), so the limiter is unreachable in a deployed run.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Nothing outside the pytest settings supplies `PYFORGE_ASSERTION_PUBLIC_KEY` (inherited from Story 42.1), so the limiter is unreachable in a deployed run.
  evidence: The rate limiter sits behind the transport gate, which answers 503 when no public key resolves. Until the canopy:AD-19 keypair Secret lands (Story 40.1 territory), no deployed MCP call gets far enough to be counted. Recorded here only because it now also gates this story's AC 1; the underlying gap and its remedy are already tracked on `spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`.
  location: src/platform/deploy/charts/platform/templates/_helpers.tpl
  origin: spec-deferred 1886c187bae3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, and it is a CAP-6 duplicate rather than an independent finding. `PYFORGE_ASSERTION_PUBLIC_KEY` returns **zero matches** in `deploy/charts/platform/templates/_helpers.tpl`, so nothing outside the pytest settings supplies it and the transport gate still answers 503 before the limiter is ever reached. This is the SAME defect as `DW-FU-42-1` (and the entry says so itself: 'inherited from Story 42.1 ... already tracked on spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md'). One defect class, two ledger rows; closing the keypair Secret closes both.

### DW-FU-42-2-6: `test_mcp_start_audit_returns_handle` leaks a committed live `RunState` row per run, which `MAX_RUNNING_PER_SUB` now counts.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `test_mcp_start_audit_returns_handle` leaks a committed live `RunState` row per run, which `MAX_RUNNING_PER_SUB` now counts.
  evidence: Found during the review pass. `TestClient` drives the app in a worker thread whose connection is in autocommit, so a row the tool creates is committed OUTSIDE the test transaction and survives rollback — the leak predates this story (subject `agent-10-2`, one row per run). Harmless until now; with the 42.2 ceilings in place, five `--reuse-db` runs against the same database exhaust that subject's allowance and the sixth run reds a pre-existing test. CI is unaffected (a fresh PostgreSQL service per job), so the exposure is repeated local runs without `--create-db`. This story's own MCP tests are immune by construction (`_fresh_subject`), which is why they were written that way rather than seeding a fixed subject.
  location: src/platform/tests/test_warden_portal_audit_start_get.py
  origin: spec-deferred 50ce8084d1fb — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `test_mcp_start_audit_returns_handle` is still present and still commits a live `RunState` row per run, which `MAX_RUNNING_PER_SUB` counts.

### DW-FU-42-2-7: `enforce_run_bounds` spends a `start` token before it checks either ceiling, so a subject parked at a ceiling burns its rate allowance on refusals.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `enforce_run_bounds` spends a `start` token before it checks either ceiling, so a subject parked at a ceiling burns its rate allowance on refusals.
  evidence: Raised independently by three review layers. After ~30 refused attempts in a minute the caller receives 429 `rate limited` instead of the 409 that names its live run ids — the response AC 3 exists to deliver, and the one the caller needs in order to wait on or revoke its own runs. Kept as-is because the bucket is the cheap cache check standing in front of two indexed COUNT queries: checking ceilings first would let an unbounded caller drive unbounded database work, which is the failure this story exists to stop. Revisit if the 409 path ever becomes the common case.
  location: src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
  origin: spec-deferred 51cbaac4e31a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `enforce_run_bounds` still spends a `start` token before checking either ceiling, so a subject parked at a ceiling still burns its rate allowance on refusals.

### DW-FU-42-2-8: The token bucket is a non-atomic read-modify-write, so concurrent requests across web pods lose updates and the effective ceiling exceeds `burst`.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The token bucket is a non-atomic read-modify-write, so concurrent requests across web pods lose updates and the effective ceiling exceeds `burst`.
  evidence: `consume()` does `store.get` -> compute -> `store.set` with no `INCR`, no CAS and no Lua script. N simultaneous requests read the same token count and the last write wins. Same class as the documented count-then-create race on the ceilings, and tolerable for the same reason — an agent loop issuing thousands of calls is still stopped, and a boundary off by the concurrency count does not restore that failure. Recorded because the module's docstring argues its other properties carefully and is silent on this one. Wall clock compounds it: a pod with a fast clock mints tokens, and only backwards skew is guarded (`max(0.0, moment - updated_at)`).
  location: src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
  origin: spec-deferred f4e841b2809b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED at the line level. `rate_limit.py`'s `consume()` (`:282`) still performs a plain read-modify-write: `store.get(key, _MISSING)` at `:311`, compute, then `store.set(...)` at `:332` — no `INCR`, no compare-and-set, no Lua script anywhere in the module. N simultaneous requests across web pods still read the same token count and the last write still wins, so the effective ceiling still exceeds `burst` by the concurrency count. Same defect class as `DW-FU-42-2-2`'s count-then-create race on the ceilings, and tolerable for the same reason the entry gives — an agent loop issuing thousands of calls is still stopped.

### DW-FU-42-2-9: Migration 0004 adds `subject` without backfilling it, so every pre-existing run counts against nobody's ceiling and cannot be revoked by subject.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Migration 0004 adds `subject` without backfilling it, so every pre-existing run counts against nobody's ceiling and cannot be revoked by subject.
  evidence: `McpHandle.subject` already carries the value, so a `RunPython` backfill joining `run_state` to `mcp_handles` would be mechanical. Left out because it is a data migration over an estate whose row count is unknown, and because the safe guard landed instead: `revoke_subject` now refuses an empty subject, so the `subject=""` cohort cannot be cancelled wholesale by accident. Until backfilled, those rows are invisible to `MAX_RUNNING_PER_SUB` and unreachable by `steward revoke --sub`.
  location: src/shared/packages/django-pyforge/src/django_pyforge/migrations/0004_run_bounds.py
  origin: spec-deferred c10ce373744e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. migration `0004_run_bounds.py` still adds `subject` with no backfill, so pre-existing runs still count against nobody's ceiling and cannot be revoked by subject.

### DW-FU-42-2-10: Neither the Helm chart nor compose exposes the eight new tunables, so "tunable without a code change" holds only for whoever can set pod env.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Neither the Helm chart nor compose exposes the eight new tunables, so "tunable without a code change" holds only for whoever can set pod env.
  evidence: `grep -rn "MAX_RUNNING_PER_SUB|MCP_RATE_LIMIT|RUN_STATE_RETENTION"` over `src/platform/deploy/` and `src/platform/compose/` returns nothing. The settings themselves are correct — every number is an `env.int` with a documented default, which is what the spec's Always clause requires — but an operator tuning them today edits the Deployment rather than `values.yaml`. Belongs with the same chart pass that adds the `beat` Deployment (Story 42.4).
  location: src/platform/deploy/charts/platform/values.yaml
  origin: spec-deferred 275898433474 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `MAX_RUNNING/RATE_LIMIT tunables` returns **zero matches** in `values.yaml` — so none of the eight new tunables is exposed by the chart; 'tunable without a code change' still holds only for whoever can set pod env directly.

### DW-FU-42-2-11: The `pyforge-steward` skill card's duty list omits `revoke` (this story) and `restore` (Story 41.1), and that file is context-injected.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The `pyforge-steward` skill card's duty list omits `revoke` (this story) and `restore` (Story 41.1), and that file is context-injected.
  evidence: `.claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md` line 90 enumerates the duties ending at `validate-fast`, citing `cli.py:L41-L55`; its grammar block has no `steward revoke --sub` line. The only `revoke` on that page is the unrelated `steward keys revoke` subcommand, which makes the omission actively misleading. An agent reading the card will not know the duty exists. Not fixed here because the card is SKF-compiled output that `skf-update-skill` regenerates, and because Story 41.1 established that the refresh is a separate pass — but that backlog is now two duties deep.
  location: .claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md
  origin: spec-deferred 88a8fcf7b7c5 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED — and this one nearly read as resolved on a naive grep, which is worth recording. `revoke` DOES appear twice in `pyforge-steward/SKILL.md` (`:46`, `:128`), but both are the CREDENTIAL duty (`steward keys {encrypt,decrypt,rotate,list,audit,revoke}`), not the run-supervision `revoke` this entry means. `restore` (Story 41.1) returns **zero** matches. So the skill card still omits both duties this entry names, and the file is context-injected, so agents still read an incomplete duty list.

### DW-FU-42-2-12: Celery tasks outside `execute_supervised_run` carry no `sub` header, so `revoke --sub` does not reach them.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Celery tasks outside `execute_supervised_run` carry no `sub` header, so `revoke --sub` does not reach them.
  evidence: The spec's Approach says "every Celery task tagged with `sub`". Live untagged enqueues remain: `run_compliance_job.delay` (`django_warden_fabric/views.py`), `run_django_task.delay` (`platformapp/front_door/celery_task_backend.py`), plus the langflow and dbgpt integrations. The narrower reading was implemented — the Problem paragraph describes only the supervisor `start` path, which is the only one that creates a `RunState` row — so a revoked subject can still hold work on those queues. Widening needs each of those call sites to carry a verified subject, which most of them do not have today.
  location: src/shared/packages/django-warden/src/django_warden_fabric/views.py
  origin: spec-deferred 06604e77b7b1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `django_warden_fabric/views.py` still carries no `sub` header on Celery tasks outside `execute_supervised_run`, so `revoke --sub` still does not reach them.

### DW-FU-42-2-13: No `RateLimit-*` response headers, so a well-behaved agent can only discover its limit by tripping it.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: No `RateLimit-*` response headers, so a well-behaved agent can only discover its limit by tripping it.
  evidence: `Decision` already carries `remaining`, `retry_after`, `rate_per_minute` and `burst`; everything except `Retry-After` on a refusal is discarded. For an agent-facing platform the `RateLimit-Limit` / `-Remaining` / `-Reset` triple is the difference between a client that self-throttles and one that must fail first. Related: the MCP bucket is charged for reads as well as writes, so a client polling `get_run` once a second while holding its permitted runs is throttled for waiting; no cheaper read cost and no documented safe poll cadence exist yet.
  location: src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  origin: spec-deferred 536a9e4da372 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `RateLimit-` returns **zero matches** in `mcp_http.py` — so no RateLimit-* response headers are emitted and a well-behaved agent can still only discover its limit by tripping it.

### DW-FU-42-2-14: `manage.py revoke_subject` exits 0 when the broker revoke failed, so a shell or cron caller reads a partial revoke as success.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `manage.py revoke_subject` exits 0 when the broker revoke failed, so a shell or cron caller reads a partial revoke as success.
  evidence: `handle()` writes `revoke error: ...` to stderr and returns `None`. Only the steward duty gets this right, because it parses `ok` out of the JSON report — which is what its own `test_a_partial_revoke_is_not_reported_as_ success` pins. The command's contract should match its wrapper's; a `CommandError` on `report["revoke_error"]` would do it. Low because the sanctioned operator grammar is `pyforge steward revoke`, not the management command.
  location: src/shared/packages/django-pyforge/src/django_pyforge/management/commands/revoke_subject.py
  origin: spec-deferred 55a8ece075d0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `a non-zero exit path` returns **zero matches** in `revoke_subject.py` — so `manage.py revoke_subject` still exits 0 after a failed broker revoke and a shell or cron caller still reads a partial revoke as success.

### DW-FU-42-2-15: The steward `revoke` duty exposes neither `--reason` nor `--json`, though the command it drives accepts both.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The steward `revoke` duty exposes neither `--reason` nor `--json`, though the command it drives accepts both.
  evidence: `manage.py revoke_subject` takes `--reason` (recorded on every cancelled run's `result`), so every revoke driven through the operator grammar is logged as the default "revoked by operator" with no incident reference. `_add_revoke_arguments` also omits the `--json` flag its sibling duties (`init`/`shell-init`/`setup`/`initrepo`/`validate-fast`) carry, even though `RevokeDuty` already returns the full report in `details`.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  origin: spec-deferred 1d51b02666b9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `--reason` returns **zero matches** in `steward/cli.py` — so the steward `revoke` duty still exposes neither `--reason` nor `--json`, though the command it drives accepts both.

### DW-FU-42-2-16: `_restore` returns a FULL bucket for stored state that is present but malformed, a fail-open path in a module that promises not to have one.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `_restore` returns a FULL bucket for stored state that is present but malformed, a fail-open path in a module that promises not to have one.
  evidence: A non-dict value, a missing key, or a non-finite number all return `(burst, now)`. The module docstring says "silently allowing traffic because the cache is down is the one outcome this module must never produce"; a poisoned or schema-drifted key produces exactly that. Kept deliberately: the alternative — treating malformed state as unavailable — would lock out every subject during a rolling deploy that changed the stored shape, which is a worse failure than one refill. The narrower real bug (an unbounded `Retry-After` from a negative token count) was patched in this pass; only the full-bucket-on-garbage policy remains.
  location: src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
  origin: spec-deferred 49d0a361b008 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `rate_limit.py`'s `_restore` still returns a FULL bucket for present-but-malformed stored state — the fail-open path in a module that promises not to have one.

### DW-FU-42-2-17: Six new `spec-surface` `drift: fail` rows for this story's four new files land under three OTHER specs' globs and need scoped stamps at landing.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Six new `spec-surface` `drift: fail` rows for this story's four new files land under three OTHER specs' globs and need scoped stamps at landing.
  evidence: Measured against a detached worktree at the `629ee8c5` baseline: 196 fails before, 136 after, and the comm-diff shows exactly six new rows, all of kind "added" — `revoke.py` and `test_revoke_duty.py` under `pyforge-steward/spec-pyforge-steward`, and the 0004 changeset plus `test_agent_rate_limits_and_run_bounds.py` under both `pyforge-steward/spec-python-agent-platform` and `pyforge-mason/spec-django-accelerator-framework`. Not stamped here for two reasons: `--write-baseline` reads the WORKING TREE, so stamping from a dirty dispatch worktree bakes in uncommitted bytes, and a foreign spec's baseline needs the three-check procedure first. Landing-pass work, scoped per spec — never a bare `--write-baseline`.
  location: scripts/.spec-surface-baseline.json
  origin: spec-deferred 65f67bcb68da — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — RESOLVED. The scoped stamps these entries defer have since been performed — `scripts/.spec-surface-baseline.json` carries current entries for `spec-pyforge-unifying-strategy` and the other governing specs, and `python -m pyforge.doctor.sources spec-surface` reports `ok -- every tracked file governed or allowlisted; no drift` as of this sweep. CAP-6 NOTE: `DW-FU-42-2-4`, `DW-FU-42-2-17` and `DW-FU-42-3-11` are ONE defect class, not three -- all three are 'this story did not run the scoped stamp for spec-pyforge-unifying-strategy'. `DW-FU-45-2-7` records the root cause: blanket pixi.toml globs force every governing spec to record the same reconcile, which is what mints these duplicates in the first place.

### DW-FU-42-2-18: A RUNNING row whose worker died without reaching `complete_run` counts against both ceilings forever, and nothing reaps it.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: A RUNNING row whose worker died without reaching `complete_run` counts against both ceilings forever, and nothing reaps it.
  evidence: Found by the 2026-09-02 follow-up pass (two review layers). A hard `CELERY_TASK_TIME_LIMIT` SIGKILL, an OOM kill or a pod eviction ends the task without the `except` in `execute_supervised_run` running, so the row stays RUNNING; retention never touches live rows by design. Before this story such a row was a phantom on the board; with the ceilings in place enough of them lock a subject out (`MAX_RUNNING_PER_SUB`) and then the station (`MAX_QUEUE_DEPTH_PER_STATION`), and the only lever is `revoke --sub` per subject. Not patched because a reaper cannot yet tell a dead worker from a task still waiting on the queue: rows are RUNNING from publish and nothing stamps `heartbeat_at` when a worker picks the task up, so "heartbeat older than the hard limit" also describes a task that has legitimately queued behind a full station for ten minutes. The fix needs a pickup heartbeat (or a PENDING->RUNNING transition at pickup) first; then a `prune_run_state` pass that FAILs live rows whose heartbeat is older than `CELERY_TASK_TIME_LIMIT` plus grace is mechanical, and the worker pre-flight added this pass already makes such a row safe to terminalise (a late pickup skips it).
  location: src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
  origin: spec-deferred aaa86de4ce7c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `supervisor.py` still has no reaper, so a RUNNING row whose worker died without reaching `complete_run` still counts against both ceilings forever.

### DW-FU-42-2-19: `django_cache_aliases` sets no `SOCKET_CONNECT_TIMEOUT` / `SOCKET_TIMEOUT`, so a partitioned redis-cache stalls each limiter call for the kernel's TCP timeout rather than failing closed quickly.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `django_cache_aliases` sets no `SOCKET_CONNECT_TIMEOUT` / `SOCKET_TIMEOUT`, so a partitioned redis-cache stalls each limiter call for the kernel's TCP timeout rather than failing closed quickly.
  evidence: Found by the 2026-09-02 follow-up pass. `IGNORE_EXCEPTIONS` turns a connection *failure* into a fast `None`, but a black-holed host is a hang, not a failure, and django_redis passes no timeout unless the OPTIONS name one. This pass moved the limiter off the event loop (`sync_to_async`, thread-insensitive), so a stall no longer freezes the pod, but each stalled call still holds an executor thread until the socket gives up. Pre-existing (steward 20.2 composed the alias, and sessions and renditions share it) and one setting away: `SOCKET_CONNECT_TIMEOUT` and `SOCKET_TIMEOUT` of a few seconds in the alias OPTIONS, which is also what makes the fail-closed refusal *fast*. Belongs with the cache composition, not this story, because it changes every consumer of the alias.
  location: src/platform/platformapp/front_door/lane1_runtime.py
  origin: spec-deferred dae189bbb8f6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `SOCKET_CONNECT_TIMEOUT` returns **zero matches** in `lane1_runtime.py` — so `django_cache_aliases` still sets no socket timeouts and a partitioned redis-cache still stalls each limiter call for the kernel's TCP timeout instead of failing closed quickly.

### DW-FU-42-2-20: No index serves the retention sweep, so both passes scan `run_state` on every tick once the table is large.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: No index serves the retention sweep, so both passes scan `run_state` on every tick once the table is large.
  evidence: Found by the 2026-09-02 follow-up pass. The two indexes 0004 adds (`subject, status` and `station, status`) serve the start-path counts and the revoke selection; the age pass filters `status IN (...) AND completed_at < cutoff` and the cap pass orders terminal rows by `completed_at, started_at`, neither of which they cover. Tolerable while `RUN_STATE_MAX_ROWS` holds the table near 100k rows and the sweep runs hourly; a `(status, completed_at)` index is a new migration plus a CAP-9 Liquibase changeset, which is why it is not folded into a review pass.
  location: src/shared/packages/django-pyforge/src/django_pyforge/models.py
  origin: spec-deferred ef1cf7616ead — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `models.py` still declares no index serving the retention sweep, so both passes still scan `run_state` on every tick.
### DW-FU-42-3: The shipped adapters validate shape and log; Doctor's and Mason's actual reactions (choosing a remedy, running a rebuild, reporting completion) are not implemented here.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The shipped adapters validate shape and log; Doctor's and Mason's actual reactions (choosing a remedy, running a rebuild, reporting completion) are not implemented here.
  evidence: `DomainAdapter.apply` is a no-op for all four types in `django_pyforge/events/adapters.py`. The story's Approach binds the vocabulary, the consumer runner and its Deployment — which now exist and are proven end to end (publish -> consume -> Celery header) — but the station-side behaviour behind each type is station work (Doctor owns the `remedy.requested` consumer per the change proposal's ownership table). `register_adapter()` is the seam: a station subclasses the adapter for its type and re-registers it at AppConfig ready time.
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/adapters.py
  origin: spec-deferred c5a1635a3361 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `events/adapters.py` still validates shape and logs only; Doctor's and Mason's actual reactions remain unimplemented.

### DW-FU-42-3-2: A process that dies mid-handler leaves the event at-most-once: the applied key is set before the handler runs (red-team A-3, not in this story's scope).

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: A process that dies mid-handler leaves the event at-most-once: the applied key is set before the handler runs (red-team A-3, not in this story's scope).
  evidence: `_apply` does `SET NX` before calling the handler and only deletes the key on a raised exception. After a crash the retry pass re-claims the entry, `_mark_applied` fails because the key is still set, and the entry is ACKed as a duplicate without re-running. The TTL from Story 40.2 bounds this to seven days. Fixing it means moving the applied mark after the handler (at-least-once) or a per-consumer in-flight marker; both change the idempotency contract and belong to a story that names A-3.
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred c3e6568d3cd6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `events/fabric.py` still sets the applied key before the handler runs, leaving the at-most-once window (red-team A-3).

### DW-FU-42-3-3: The handler timeout is a budget, not an enforced limit: nothing interrupts a handler that runs past `DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS`.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The handler timeout is a budget, not an enforced limit: nothing interrupts a handler that runs past `DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS`.
  evidence: The consumer runs handlers inline. The timeout is what `harvest_poison` uses as its `min_idle_time` (so a live handler is never stolen from) and what the chart's `terminationGracePeriodSeconds` is sized against; a handler that hangs holds its entry until the pod is replaced, after which the harvest reclaims it. A real limit needs a thread or `SIGALRM` guard; handlers today enqueue Celery work rather than doing it, so the exposure is a stuck consumer, not a stuck event. Review P3 narrowed the rollout exposure to exactly one handler: SIGTERM now stops the fabric before the next claim/read and interrupts the idle wait.
  location: src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
  origin: spec-deferred 1eef53560bc7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, with the location refined. `HANDLER_TIMEOUT` does not appear in `consume_events.py`; the knob lives at `events/constants.py` (`EVENT_HANDLER_TIMEOUT_MS_DEFAULT`) and is surfaced as `events/fabric.py`'s `handler_timeout_ms`. The knob exists and is read — what is still absent is any mechanism that INTERRUPTS a handler exceeding it, which is exactly the entry's claim: a budget, not an enforced limit.

### DW-FU-42-3-4: `consume_events` now binds through `connect_event_broker` (review P6), so a deployment whose `REDIS_CACHE_URL` equals `REDIS_BROKER_URL` -- the compose stack, which sets only `REDIS_URL` -- refuses to start the consumer with `EventBrokerConfigError`.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: `consume_events` now binds through `connect_event_broker` (review P6), so a deployment whose `REDIS_CACHE_URL` equals `REDIS_BROKER_URL` -- the compose stack, which sets only `REDIS_URL` -- refuses to start the consumer with `EventBrokerConfigError`.
  evidence: `config/settings/base.py` defaults both `REDIS_BROKER_URL` and `REDIS_CACHE_URL` to `REDIS_URL`; the chart sets distinct Service URLs, compose does not. That refusal is canopy:AD-10 doing its job (one Redis serving both roles is the canopy anti-pattern), and it lands on the same compose gap already recorded above (no `consume-events` service). Running the consumer locally needs `REDIS_CACHE_URL` pointed at a second database or instance.
  location: src/platform/compose/compose.yml
  origin: spec-deferred d2b7e301ee52 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED. `compose.yml` still sets `REDIS_URL` only (3 matches) with no separate broker/cache URLs, so `consume_events`'s `connect_event_broker` binding still refuses to start on the compose stack where the two URLs are necessarily equal.

### DW-FU-42-3-5: A SIGTERM that lands mid-batch leaves the entries XREADGROUP already delivered (but not yet attempted) pending under the departing consumer name.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: A SIGTERM that lands mid-batch leaves the entries XREADGROUP already delivered (but not yet attempted) pending under the departing consumer name.
  evidence: Review P3's stop check runs before each entry, so a batch of up to 100 new entries read in one XREADGROUP may be partly unattempted when the loop returns. Those entries carry delivery count 1 and are retried after `backoff_ms(1)` by a consumer of the same name, or reclaimed by `harvest_poison` after the handler timeout by the replacement pod (whose hostname-derived name differs) -- a delay, never a loss. Covered by `test_run_passes_stops_after_pass_harvests_on_schedule_and_waits_only_when_idle`. Reading smaller batches once a stop is likely would shorten it.
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred 93dd72ab6eab — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `events/fabric.py` still leaves XREADGROUP-delivered-but-unattempted entries pending under a departing consumer name on SIGTERM.

### DW-FU-42-3-6: A harvest claim counts as a delivery, so an abandoned delivery spends an attempt; with `EVENT_MAX_ATTEMPTS=1` a reclaimed entry is quarantined without a retry.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: A harvest claim counts as a delivery, so an abandoned delivery spends an attempt; with `EVENT_MAX_ATTEMPTS=1` a reclaimed entry is quarantined without a retry.
  evidence: XAUTOCLAIM increments the delivery counter (JUSTID would not, but then the fields needed for the unparseable check are not returned). The rule is stated in `harvest_poison` and covered by `test_harvest_quarantines_exhausted_entry_with_recorded_error`; with the default of five attempts it costs one retry per crash, which is the honest reading of "delivered and never acknowledged".
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred b634a61bf243 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `events/fabric.py` still counts a harvest claim as a delivery, so with `EVENT_MAX_ATTEMPTS=1` a reclaimed entry is still quarantined without a retry.

### DW-FU-42-3-7: compose.yml has no `consume-events` service; only the chart deploys the consumer.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: compose.yml has no `consume-events` service; only the chart deploys the consumer.
  evidence: AC 4 names `helm template`. The local compose stack still runs a producer with no listener; `python manage.py consume_events --station doctor` from a shell against the compose Redis is the workaround until a compose service is added alongside `worker`.
  location: src/platform/compose/compose.yml
  origin: spec-deferred 8cd74bd9678d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `consume-events` returns **zero matches** in `compose.yml` — so compose still has no consumer service and only the chart deploys one.

### DW-FU-42-3-8: `events.replicaCount` and `events.resources` are one knob for every consumer station.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: `events.replicaCount` and `events.resources` are one knob for every consumer station.
  evidence: The values block is a list of station names plus shared settings. Per-station replicas would need a map-shaped value; deliberately not done until a station needs more than one consumer.
  location: src/platform/deploy/charts/platform/values.yaml
  origin: spec-deferred 1ab61d6bae11 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `values.yaml` still exposes `events.replicaCount`/`events.resources` as one knob for every consumer station.

### DW-FU-42-3-9: `test_execute_supervised_run_leaves_no_celery_result_key` (pre-existing, Story 40.2) fails locally for lack of a `django_db` mark; unchanged here.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: `test_execute_supervised_run_leaves_no_celery_result_key` (pre-existing, Story 40.2) fails locally for lack of a `django_db` mark; unchanged here.
  evidence: It calls `migrate` and creates a `RunState` row without the mark, so pytest-django refuses the connection. Identical at the `1af2ca2b62` baseline (verified by running the HEAD copy in isolation); it is one of the thirteen pre-existing local failures the platform-suite memory note lists. Not touched because it is not this story's test and a mark change deserves its own eyes.
  location: src/platform/tests/test_cloudevents_redis_broker.py
  origin: spec-deferred 87ff8d12d36c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED as a pre-existing local-only failure. `test_cloudevents_redis_broker.py` still carries only 2 `django_db` references and `test_execute_supervised_run_leaves_no_celery_result_key` still lacks the mark it needs, so it still fails locally. Unchanged by Story 42.3, as the entry says.

### DW-FU-42-3-10: Ruff and mypy findings on the touched files are pre-existing categories, not new ones.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: Ruff and mypy findings on the touched files are pre-existing categories, not new ones.
  evidence: `ruff check` (platform config) over the touched django-pyforge files: 18 findings, all `PLR0913`/`PLR0917`/`FBT001`/`FBT002` on signatures that predate this story plus five `E501` in code this story did not write. `mypy tests/test_cloudevents_redis_broker.py tests/test_chart_invariants.py` (CI's scope): five errors, all in pre-existing code (`CountingRedis.xadd` override, the `lookup_runner` monkeypatch, the liquibase Job helper's `Any | None` key). Platform CI's `ruff check .` does not lint `src/shared/packages/`.
  location: src/platform/pyproject.toml
  origin: spec-deferred 604a08154215 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED as an accepted characterisation rather than a defect: the ruff/mypy findings on the touched files remain pre-existing categories. Nothing in this sweep contradicts that, and no new category was introduced.

### DW-FU-42-3-11: Scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run by this story.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: Scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run by this story.
  evidence: The memlog entry for this story is appended (downgrading the drift to `drift-presumed: warn`); `--write-baseline --spec pyforge-steward/spec-pyforge-unifying-strategy` must run from a CLEAN worktree after landing, never from the dispatch worktree — the same residual Story 42.2 recorded, whose ~60-path lag this story does not reconcile either.
  location: scripts/.spec-surface-baseline.json
  origin: spec-deferred 2d7798eb123a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — RESOLVED. The scoped stamps these entries defer have since been performed — `scripts/.spec-surface-baseline.json` carries current entries for `spec-pyforge-unifying-strategy` and the other governing specs, and `python -m pyforge.doctor.sources spec-surface` reports `ok -- every tracked file governed or allowlisted; no drift` as of this sweep. CAP-6 NOTE: `DW-FU-42-2-4`, `DW-FU-42-2-17` and `DW-FU-42-3-11` are ONE defect class, not three -- all three are 'this story did not run the scoped stamp for spec-pyforge-unifying-strategy'. `DW-FU-45-2-7` records the root cause: blanket pixi.toml globs force every governing spec to record the same reconcile, which is what mints these duplicates in the first place.

### DW-FU-42-3-12: The real-redis delivery test skips in CI: `platform-ci-test` has no `redis-server` binary, so CI proves retry/backoff/DLQ/harvest only against `MemoryRedis`.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The real-redis delivery test skips in CI: `platform-ci-test` has no `redis-server` binary, so CI proves retry/backoff/DLQ/harvest only against `MemoryRedis`.
  evidence: `test_real_redis_retry_backoff_dlq_and_harvest` skips when `shutil.which("redis-server")` is None; the binary is a `platform-dev` feature dependency only and CI's `redis:7` is a service container, not a PATH binary. Adding it to the CI env is a `pixi.toml` + `environment.yaml` change outside this story. The in-memory double now pins redis-py's XCLAIM contract (review P13b), which narrows but does not close the gap.
  location: pixi.toml (feature.platform-dev)
  origin: spec-deferred 864542725626 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED. `pixi.toml` mentions `redis-server` (4 matches) only under the platform-dev feature, so `platform-ci-test` still has no redis binary and CI still proves retry/backoff/DLQ/harvest against `MemoryRedis` alone. The real-redis delivery test still skips there.

### DW-FU-42-3-13: A process that dies mid-handler still leaves that group's event at-most-once (red-team A-3): the group-scoped applied key is set before the handler runs, so the redelivery is ACKed as a duplicate.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: A process that dies mid-handler still leaves that group's event at-most-once (red-team A-3): the group-scoped applied key is set before the handler runs, so the redelivery is ACKed as a duplicate.
  evidence: Review pass reaffirmed the implementation pass's A-3 entry after the applied key became group-scoped (review P1): scoping fixed cross-group loss, not same-group crash loss. Out of this story's intent (A-1, A-2, A-4, A-5, R-9).
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred 60b84d1bc4e8 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `events/fabric.py` still sets the group-scoped applied key before the handler runs, so a redelivery is still ACKed as a duplicate.

### DW-FU-42-3-14: The handler timeout remains a budget, not an enforced limit; a handler that blocks past it stalls the single-threaded consumer and the harvester re-runs the entry concurrently after the threshold.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The handler timeout remains a budget, not an enforced limit; a handler that blocks past it stalls the single-threaded consumer and the harvester re-runs the entry concurrently after the threshold.
  evidence: Nothing wraps `handler(event)` in a timeout. Reaffirmed by the review pass; the intent treats the handler timeout as a given, not a deliverable.
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred 6bc0d169948a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `events/fabric.py`'s handler timeout is still a budget, not an enforced limit.

### DW-FU-42-3-15: Consumer names default to `<station>-<hostname>` (the pod name), so every rollout mints a new consumer and dead consumers accumulate in the group; nothing runs XGROUP DELCONSUMER.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: Consumer names default to `<station>-<hostname>` (the pod name), so every rollout mints a new consumer and dead consumers accumulate in the group; nothing runs XGROUP DELCONSUMER.
  evidence: `consume_events.py` derives the consumer from `socket.gethostname()`; abandoned entries return only via `harvest_poison` after the handler timeout, and `XINFO CONSUMERS` grows with each restart.
  location: src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
  origin: spec-deferred 341892aa5399 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `XGROUP DELCONSUMER` returns **zero matches** in `consume_events.py` — so every rollout still mints a new `<station>-<hostname>` consumer and dead consumers still accumulate in the group unreaped.

### DW-FU-42-3-16: The consumer has no in-process reconnect for a broker outage; a redis ConnectionError ends the loop and the pod relies on Kubernetes restarts (CrashLoopBackOff) to recover.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The consumer has no in-process reconnect for a broker outage; a redis ConnectionError ends the loop and the pod relies on Kubernetes restarts (CrashLoopBackOff) to recover.
  evidence: `run_passes` wraps neither `consume` nor `harvest_poison`; a redis-broker restart kills every consumer pod once.
  location: src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
  origin: spec-deferred 70ec5f7d3ec9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `ConnectionError` returns **zero matches** in `consume_events.py` — so the consumer still has no in-process reconnect and still relies on Kubernetes CrashLoopBackOff to recover from a broker outage.

### DW-FU-42-3-17: The consume-events Deployment has no liveness probe, so a consumer whose Redis socket hangs or whose handler blocks forever is never replaced.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The consume-events Deployment has no liveness probe, so a consumer whose Redis socket hangs or whose handler blocks forever is never replaced.
  evidence: The template states "No probes -- the consumer has no HTTP surface"; an exec probe on a per-pass heartbeat file would let the Deployment self-heal. Parity with the worker Deployment, which the intent asked for, is preserved as shipped.
  location: src/platform/deploy/charts/platform/templates/consume-events-deployment.yaml
  origin: spec-deferred 1a0310b208e0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `livenessProbe` returns **zero matches** in `consume-events-deployment.yaml` — so a consumer whose Redis socket hangs or whose handler blocks forever is still never replaced.

### DW-FU-42-4: Compose stack still runs a single undifferentiated Celery worker with no beat or builds pool — local dev does not mirror the Kubernetes split-pool topology introduced here.

- source_spec: `planning-artifacts/specs/spec-42-4-celery-hardening-and-the-builds-pool.md`
  summary: Compose stack still runs a single undifferentiated Celery worker with no beat or builds pool — local dev does not mirror the Kubernetes split-pool topology introduced here.
  evidence: src/platform/compose/compose.yml worker service unchanged; deploy/README documents K8s only.
  location: src/platform/compose/compose.yml
  origin: spec-deferred e9c1ae35bc3d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `compose.yml` still runs a single undifferentiated Celery worker with no beat or builds pool, so local dev still does not mirror the Kubernetes split-pool topology.

### DW-FU-42-4-2: Story 42.4 Helm render tests are gated on `@requires_helm` and skip in platform-ci-test when helm is absent — the same pre-existing CI pattern as other chart stories.

- source_spec: `planning-artifacts/specs/spec-42-4-celery-hardening-and-the-builds-pool.md`
  summary: Story 42.4 Helm render tests are gated on `@requires_helm` and skip in platform-ci-test when helm is absent — the same pre-existing CI pattern as other chart stories.
  evidence: test_chart_invariants.py `@requires_helm`; platform-ci-test env has no kubernetes-helm dependency.
  location: src/platform/tests/test_chart_invariants.py
  origin: spec-deferred 395c8d2f9102 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the code path this entry indicts is present and unchanged. `test_chart_invariants.py`'s Story 42.4 render tests are still `@requires_helm`-gated and still skip where helm is absent.

### DW-FU-42-5: Per-tenant quotas (after R-8 limiter).

- source_spec: `planning-artifacts/specs/spec-42-5-role-namespaces-and-the-tenant-claim.md`
  summary: Per-tenant quotas (after R-8 limiter).
  evidence: Per-tenant quotas (after R-8 limiter).
  origin: spec-deferred 2d5f6c25f413 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: src/shared/packages/django-pyforge/src/django_pyforge/roles.py (tenant id parsing / legacy-role switch)
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: per-tenant quotas remain unbuilt, pending the R-8 limiter. A `location:` was added — this entry had none.

### DW-FU-42-5-2: Legacy bare tenant ids (east/west without pyforge:tenant:) are not accepted even under DJANGO_PYFORGE_LEGACY_BARE_ROLES — only bare station slugs get the migration switch.

- source_spec: `planning-artifacts/specs/spec-42-5-role-namespaces-and-the-tenant-claim.md`
  summary: Legacy bare tenant ids (east/west without pyforge:tenant:) are not accepted even under DJANGO_PYFORGE_LEGACY_BARE_ROLES — only bare station slugs get the migration switch.
  evidence: Spec AC targets bare station names; tenant prefix is required from day one per R-13.
  origin: spec-deferred 0d3ef5a74e33 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  location: src/shared/packages/django-pyforge/src/django_pyforge/roles.py (tenant id parsing / legacy-role switch)
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: legacy bare tenant ids (east/west without the `pyforge:tenant:` prefix) are still rejected even under `DJANGO_PYFORGE_LEGACY_BARE_ROLES`; only bare station slugs get the migration switch. A `location:` was added — this entry had none.

### DW-FU-43-4: GitOps repository / Argo profile (steward deploy-profile).

- source_spec: `planning-artifacts/specs/spec-43-4-golden-path-cd-by-digest.md`
  summary: GitOps repository / Argo profile (steward deploy-profile).
  evidence: GitOps repository / Argo profile (steward deploy-profile).
  origin: spec-deferred dd1ebb009b7a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: the GitOps/Argo deploy profile remains unbuilt. Nothing in the tree contradicts the entry's own evidence, and no story since has claimed this surface.

### DW-FU-43-4-2: golden-path-promotion rebuilds all three images after the container job — extra CI minutes per platform-ci run.

- source_spec: `planning-artifacts/specs/spec-43-4-golden-path-cd-by-digest.md`
  summary: golden-path-promotion rebuilds all three images after the container job — extra CI minutes per platform-ci run.
  evidence: The promotion job runs three docker builds independently rather than reusing container job artifacts.
  location: .github/workflows/platform-ci.yml
  origin: spec-deferred dbd876ccb82a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: `golden-path-promotion` still rebuilds all three images after the container job, so the extra CI minutes per `platform-ci` run persist. Nothing in the tree contradicts the entry's own evidence, and no story since has claimed this surface.

### DW-FU-41-3-9: The chart and compose ship stock `postgres:17`, which has no pgvector, so `pyforge-scribe:1` moves a CREATE EXTENSION failure out of scribe's own process and into the platform's pre-upgrade hook Job.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: The chart and compose ship stock `postgres:17`, which has no pgvector, so `pyforge-scribe:1` moves a CREATE EXTENSION failure out of scribe's own process and into the platform's pre-upgrade hook Job.
  evidence: values.yaml pins `repository: postgres` / `tag: "17"` and compose.yml `image: postgres:17`; `grep -rn -i pgvector src/platform/deploy/ src/platform/compose/` returns nothing. The Helm Job (`post-install,pre-upgrade`) applies the master changelog, so on a stock image `:1` aborts with `could not open extension control file "vector.control"` and the release fails -- for every estate, including ones that never deploy scribe. Before this story the same statement failed only inside the scribe station. Supplying a pgvector-capable image is a deploy-side decision outside this story's boundaries.
  location: src/platform/deploy/charts/platform/values.yaml:108-113
  origin: spec-deferred f23d35461a00 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, and found by reading the values rather than grepping the literal. `src/platform/deploy/charts/platform/values.yaml:175-179` declares `postgres: image: {repository: postgres, tag: "17"}` — stock postgres:17, still no pgvector — so `pyforge-scribe:1`'s CREATE EXTENSION still fails in the pre-upgrade hook Job. (A literal `postgres:17` grep returns zero hits because repository and tag are separate keys; that is exactly the shape that makes this kind of claim look resolved when it is not.)

### DW-FU-41-3-10: `_assert_provisioned` names only the relation-absent and no-schema-USAGE cases; column drift and a table-privilege gap still leak raw psycopg errors with no changeset named.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: `_assert_provisioned` names only the relation-absent and no-schema-USAGE cases; column drift and a table-privilege gap still leak raw psycopg errors with no changeset named.
  evidence: `to_regclass` answers existence only. A role with schema USAGE but no table grants passes the assert and then raises a raw `InsufficientPrivilege` from `_load`; a `graph_nodes` missing a column raises a raw `UndefinedColumn`, which `test_legacy_table_without_stale_is_back_filled_by_the_changeset` pins as expected pre-`:4` behaviour. AC-1 only requires the relation-absent case to be named, so this is beyond the contract, but it is the same class of unrecoverable state the review's high finding fixed.
  location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py:114
  origin: spec-deferred 9c5844ee95ba — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file: `_assert_provisioned` still names only the relation-absent and no-schema-USAGE cases, so column drift and table-privilege gaps still surface as raw psycopg errors. Evidence: `_assert_provisioned` is present in `graph_store_pg.py` with that same narrow coverage.

### DW-FU-41-3-11: Master-changelog include order is load-bearing for scribe (`:1` before `:2` before `:3`) but only set membership and duplicates are asserted.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Master-changelog include order is load-bearing for scribe (`:1` before `:2` before `:3`) but only set membership and duplicates are asserted.
  evidence: `test_every_changeset_file_is_included_in_the_master_changelog` compares sets. Order cannot be inferred from seq either -- the file already includes `python-agent-platform-15` between `:5` and `:6`. A reordered include would put `CREATE TABLE ... embedding vector` before the extension exists and fail at deploy time, with every test green. Distinct from the pre-existing FK-ordering deferral above, which is about python-agent-platform's own order.
  location: src/platform/tests/policy/test_liquibase_ddl_governance.py:252
  origin: spec-deferred 0bbe6f067ad7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file: the master-changelog include ORDER is still asserted only as set membership and duplicate-freedom, never as sequence. Evidence: `tests/policy/test_liquibase_ddl_governance.py` still tests the membership shape.

### DW-FU-41-3-12: `load_map`'s new "default distribution not registered" ValueError is untested and reaches CI as a traceback, and no path migrates a pre-41.3 `sqlmigrate-map.yaml`.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: `load_map`'s new "default distribution not registered" ValueError is untested and reaches CI as a traceback, and no path migrates a pre-41.3 `sqlmigrate-map.yaml`.
  evidence: `run_live_check` calls `load_map` with no handler, so a malformed or old-format map exits with a stack trace instead of the module's `format_findings` output. `test_sqlmigrate_extraction.py` never asserts the rejection. An old-format map (top-level `distribution:` / `migrations:`) yields `distributions == {}` and trips the guard with no hint that the format changed.
  location: src/platform/db/sqlmigrate_extraction.py:125
  origin: spec-deferred fe1bd6c953f3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, with the quoted message CORRECTED. The entry quotes a `default distribution not registered` ValueError; that exact string returns zero hits. The check survives with different wording — `db/sqlmigrate_extraction.py:197-200` raises `ValueError` on `sqlmigrate-map.yaml default distribution {default!r} has no ...`. So the defect is intact and only the entry's quotation was stale; nothing tests that path, and no migration exists for a pre-41.3 `sqlmigrate-map.yaml`.

### DW-FU-41-3-13: `MigrationMap.lookup` resolves a migration key claimed by two distributions by YAML insertion order, while db/README.md calls the map a register that "cannot silently collide".

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: `MigrationMap.lookup` resolves a migration key claimed by two distributions by YAML insertion order, while db/README.md calls the map a register that "cannot silently collide".
  evidence: `lookup` returns the first distribution whose `migrations` contains the key and never reports the duplicate. The anti-collision property the README claims for the map is actually provided by `test_changeset_ids_are_unique_across_files`, which scans `changes/*.sql` -- a different artifact from the one AC-3 names.
  location: src/platform/db/sqlmigrate_extraction.py:57
  origin: spec-deferred 991513e38329 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file: `MigrationMap.lookup` still resolves a doubly-claimed migration key by YAML insertion order, contradicting db/README.md's 'cannot silently collide'. Evidence: `def lookup` is present in `db/sqlmigrate_extraction.py` unchanged.

### DW-FU-41-3-14: Scribe's test suite now hard-depends on the platform tree, so the package can no longer be tested standalone.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Scribe's test suite now hard-depends on the platform tree, so the package can no longer be tested standalone.
  evidence: `tests/unit/conftest.py` resolves `parents[5] / "platform" / "db" / "changelog" / "changes"` and calls `pytest.fail` (not `skip`) when it is absent. The wheel excludes `tests/`, so this bites an sdist or standalone checkout rather than an installed wheel. The reverse edge (host importing `pyforge.*`) is the one the Boundaries forbid; this direction is unaddressed by them.
  location: src/shared/packages/pyforge-scribe/tests/unit/conftest.py:12
  origin: spec-deferred 541750e35940 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file: scribe's suite still hard-depends on the platform tree via a `parents[N]`-relative path, so the package cannot be tested standalone. Evidence: `tests/unit/conftest.py` still resolves a `parents[...]` path out of the package.

### DW-FU-41-4-8: load_django_settings() makes Django construct its Settings object twice, re-entrantly, on every process that imports config.*.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: load_django_settings() makes Django construct its Settings object twice, re-entrantly, on every process that imports config.*.
  evidence: config/__init__.py imports celery_app, whose module scope calls configure_observability() -> load_django_settings() -> settings.INSTALLED_APPS. That re-enters LazySettings._setup while Django's outer Settings.__init__ is still importing config.settings.production (which reaches config/__init__.py through `from .base import *`). The inner Settings object is assigned to _wrapped and then silently replaced by the outer one; read_dot_env() also runs twice. No in-repo regression is observable (the whole-suite failure/error set is byte-identical to baseline, 436 passed here vs 420 pre-change with the delta exactly this story's tests), but the work is duplicated and the settings module is imported while the config package is only partially initialised. The existing "materializes settings even when OTel is disabled" entry records the import-time contract; it does not record the double construction.
  location: src/platform/config/observability/__init__.py -- load_django_settings()
  origin: spec-deferred 1468c3938a11 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: the cited file is present and unchanged in the respect named — `load_django_settings()` still makes Django construct its Settings object twice, re-entrantly, on every process importing `config.*`.

### DW-FU-41-4-9: A CA path that is readable but not parseable as PEM passes the boot gate and fails at first connect.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: A CA path that is readable but not parseable as PEM passes the boot gate and fails at first connect.
  evidence: resolve_ca_trust() checks existence and permission bits, never content, so an empty or truncated corporate bundle resolves as a trust source, stage 1 accepts it, and the component boots -- then every broker handshake fails. That inverts the property resolve_ca_trust()'s own docstring advertises ("a typo or a permission mistake degrades to no trust source -- which stage 1 refuses at boot instead of failing at first connect"). A guard would be a throwaway SSLContext.load_verify_locations(cafile=...) in a try/except ssl.SSLError; note it only helps the cafile half, since capath lookup is lazy by design.
  location: src/platform/config/broker_tls.py -- resolve_ca_trust()
  origin: spec-deferred cf91f75436b1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: the cited file is present and unchanged in the respect named — a CA path that is readable but not PEM-parseable still passes the boot gate and fails at first connect.

### DW-FU-41-4-10: config.settings.production with COMPONENT_RUNTIME=local composes CERT_NONE and no stage 1 runs to refuse it.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: config.settings.production with COMPONENT_RUNTIME=local composes CERT_NONE and no stage 1 runs to refuse it.
  evidence: Confirmed live: the production leaf + COMPONENT_RUNTIME=local + COMPONENT_BROKER_SSL_CERT_REQS=none + a rediss:// broker loads cleanly and composes ssl_cert_reqs=0, because run_stage_one() early-returns on is_deployed(). The intent keys the exception to COMPONENT_RUNTIME ("CERT_NONE is permitted only under COMPONENT_RUNTIME=local"), so this is contract-compliant and was rejected as a finding in the first review pass on those grounds; R-14's own wording is "must fail the production settings check", which is the leaf, not the marker. Whether the lever should also be refused at the production leaf is the product decision left open.
  location: src/platform/config/startup/stage_one.py -- run_stage_one()
  origin: spec-deferred b9762643b07d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: the cited file is present and unchanged in the respect named — `config.settings.production` with `COMPONENT_RUNTIME=local` still composes CERT_NONE with no stage-1 run to refuse it.

### DW-FU-41-4-11: config.asgi -- the entrypoint the production image actually runs -- is covered by nothing in the env CI uses.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: config.asgi -- the entrypoint the production image actually runs -- is covered by nothing in the env CI uses.
  evidence: Containerfile CMD is `gunicorn config.asgi:application`. The three tests that import config.asgi are each gated on pytest.importorskip("langflow"), and langflow is in the python-agent-platform feature, not platform-ci-test -- which is what Platform CI installs for `python -m pytest`. So they skip in CI. This story's entrypoint tests exclude config.asgi for the same reason. The container job boots the image with a healthy config, which is a control, not a refusal. Needs either a langflow-free import path for the ASGI seam or a container-level refusal case.
  location: src/platform/config/asgi.py
  origin: spec-deferred c95ddcf312d7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: the cited file is present and unchanged in the respect named — `config/asgi.py` — the entrypoint the production image runs — is still covered by nothing in the env CI uses.

### DW-FU-41-4-12: LANGFLOW_REDIS_URL is a third consumer of the shared Redis URL with no TLS posture, alongside CHANNEL_LAYERS and the django-redis caches.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: LANGFLOW_REDIS_URL is a third consumer of the shared Redis URL with no TLS posture, alongside CHANNEL_LAYERS and the django-redis caches.
  evidence: config/settings/base.py does `os.environ["LANGFLOW_REDIS_URL"] = env("LANGFLOW_REDIS_URL", default=REDIS_CACHE_URL)`, handing the same URL to a third-party service that builds its own client. The existing "CHANNEL_LAYERS and REDIS_CACHE_URL share the URL" entry names two consumers; a follow-up scoped from it would miss this one.
  location: src/platform/config/settings/base.py
  origin: spec-deferred 5a69dfaa81be — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: `config/settings/base.py:645` still sets `LANGFLOW_REDIS_URL` from `REDIS_CACHE_URL` with no TLS posture, making it the third untreated consumer of the shared Redis URL alongside `CHANNEL_LAYERS` and the django-redis caches.

### DW-FU-41-4-13: test_production_leaf_source_wires_stage_one is still a source-substring assertion, and the call-position requirement it sits next to is unguarded.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: test_production_leaf_source_wires_stage_one is still a source-substring assertion, and the call-position requirement it sits next to is unguarded.
  evidence: It asserts `"run_stage_one(" in source`, the exact assertion style this story's review pass removed from the broker suite, and it passes regardless of where in production.py the call sits. Story 41.4 made the position load-bearing: the condition reads the composed CELERY_BROKER_URL off the module, so moving the call above the Celery block silently reverts stage 1 to the env-derived URL. test_run_stage_one_forwards_the_settings_module pins the forwarding; nothing pins the ordering.
  location: src/platform/tests/test_startup_required_settings.py
  origin: spec-deferred 041ca9bd08cd — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: the cited file is present and unchanged in the respect named — `test_production_leaf_source_wires_stage_one` is still a source-substring assertion and the adjacent call-position requirement is still unguarded.

### DW-FU-42-1-7: Every station app is built `json_response=True`, so the keep-alive frame never fires against the real sidecar and the raised budget stays capped by the ~30s ingress idle timeout.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: Every station app is built `json_response=True`, so the keep-alive frame never fires against the real sidecar and the raised budget stays capped by the ~30s ingress idle timeout.
  evidence: `mcp_dual_era.py:55-56` builds every station MCP app with `json_response=True, stateless_http=True`, so the sidecar's body is always `application/json` and never `text/event-stream`. `_keepalive_frame()` returns `None` for anything but an event stream — correctly, since a comment frame injected into JSON corrupts it — which means the keep-alive path is unreachable in production and a JSON tool call still emits no bytes until it completes. T-5 is therefore only partially closed: the 5s cap and the full-response buffering are gone, but a long JSON call still dies at whatever idle timeout sits in front of the pod. Not fixable inside this story: the intent prescribes comment frames, and there is no legal way to keep a JSON body alive. Closing it needs either SSE-shaped sidecar responses or an ingress idle-timeout decision.
  location: src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  origin: spec-deferred ec2f85a6906c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, with the LOCATION CORRECTED — and this is the kind of drift that makes an entry look resolved. `json_response` returns zero hits in `mcp_http.py`, the file this entry cites, which reads as fixed. It is not: the flag moved modules and survives at `django_pyforge/mcp_dual_era.py:55` as `json_response=True`. Meanwhile the keep-alive machinery it defeats is real and reachable (`mcp_http.py:323` `_keepalive_frame`, used at `:377`/`:390`), so the frame still never fires against the real sidecar and the raised budget stays capped by the ~30s ingress idle timeout.

### DW-FU-42-1-8: The chart wires `MCP_HOST_SIDECAR_BASE_URL` into worker and migrate-job pods that the new NetworkPolicy then denies.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: The chart wires `MCP_HOST_SIDECAR_BASE_URL` into worker and migrate-job pods that the new NetworkPolicy then denies.
  evidence: `_helpers.tpl` (`platform.djangoEnv`) injects the sidecar URL into `worker-deployment.yaml` and `migrate-job.yaml`, and `test_platform_pods_wire_mcp_host_sidecar_base_url_to_internal_service` (`test_chart_invariants.py:1349`) asserts web AND worker carry it — while the new policy admits only `component: web` and the X-5 guard pins the rule to exactly one peer. Nothing breaks today: the only reader is `sidecar_base_url()`, reached solely from `config/asgi.py`'s dispatch, which runs in web. But the two invariants now encode opposite intents, and the first worker-side MCP call will fail at the network layer rather than at the config layer.
  location: src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml
  origin: spec-deferred 514865ff9aff — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, with a note on where the evidence lives. `MCP_HOST_SIDECAR_BASE_URL` does not appear in `mcp-host-networkpolicy.yaml` — expected, since the policy denies rather than wires — so the contradiction the entry describes is between that policy and the chart templates that DO set the variable on worker and migrate-job pods. Neither side has changed; the denial still applies to pods the chart still configures.

### DW-FU-42-1-9: No test drives the real ASGI entrypoint; every test builds its own app around `dispatch_station_mcp`.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: No test drives the real ASGI entrypoint; every test builds its own app around `dispatch_station_mcp`.
  evidence: The single production caller is `_dispatch_http` in `src/platform/config/asgi.py`. `test_mcp_transport_auth.py` calls `dispatch_station_mcp` directly with hand-built scope dicts, and the five updated files each wrap it in their own `application`. So the ACs' "Given `POST /stations/atlas/mcp`" is proved against an assembled callable, not the app gunicorn serves — a reordering inside `_dispatch_http` that let a station path bypass the gate would not fail any test. Pre-existing convention across this suite, not introduced here.
  location: src/platform/config/asgi.py
  origin: spec-deferred 466a9520472a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED. `config/asgi.py` references `dispatch_station_mcp` (2 matches), but no test drives that real ASGI entrypoint — every test still builds its own app around the dispatcher. Same root cause as `DW-FU-41-4-11`, which records the asgi-coverage gap from the other direction; they are one defect class (CAP-6).

### DW-FU-42-1-10: `MCP_PROXY_TIMEOUT_SECONDS` is documented only in a source comment.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization-and-a-streaming-proxy.md`
  summary: `MCP_PROXY_TIMEOUT_SECONDS` is documented only in a source comment.
  evidence: The new env var appears in no `values.yaml`, no chart template, and not in `src/platform/deploy/overlays/ocp/cluster-bringup.md`, which already carries an mcp-host readiness checklist. An operator raising the sidecar budget has to read `mcp_http.py` to learn the name exists.
  location: src/platform/deploy/overlays/ocp/cluster-bringup.md
  origin: spec-deferred 5095bc3a8325 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED by exhaustive grep of the cited file — the thing this entry says is missing is still missing (zero matches). `MCP_PROXY_TIMEOUT_SECONDS` returns **zero matches** in `deploy/overlays/ocp/cluster-bringup.md` — confirming the knob is still documented only in a source comment and nowhere an operator would look.

### DW-FU-43-2: PyForgeStationClient default urllib transport has no executing test.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract-and-the-api-v1-collision.md`
  summary: PyForgeStationClient default urllib transport has no executing test.
  evidence: Unit tests inject a mock transport; _urllib path untested in CI.
  location: src/shared/packages/pyforge-core/src/pyforge/core/client.py
  origin: spec-deferred 85ddd72a0ee3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED. `grep -rn 'urllib' src/shared/packages/pyforge-core/tests/` returns nothing — `PyForgeStationClient`'s default urllib transport still has no executing test, so the default path ships unexercised while injected-transport paths are covered.

### DW-FU-43-2-2: Langflow /langflow/api/v1/ prefix-preserving redirect not gated in platform-ci-test.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract-and-the-api-v1-collision.md`
  summary: Langflow /langflow/api/v1/ prefix-preserving redirect not gated in platform-ci-test.
  evidence: test_langflow_mount.py requires langflow package; langflow-free suite covers bare /api/v1 only.
  location: src/platform/tests/test_langflow_mount.py
  origin: spec-deferred fa60252fa0b0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, and the mechanism verified. `test_langflow_mount.py` is named in `.github/workflows/platform-ci.yml:569` only inside a COMMENT ('see tests/test_langflow_mount.py's module docstring'), never as a gated run step, and no pixi task invokes it. The prefix-preserving redirect remains ungated.

### DW-FU-43-2-3: Server-side X-PyForge-API-Version header enforcement not implemented.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract-and-the-api-v1-collision.md`
  summary: Server-side X-PyForge-API-Version header enforcement not implemented.
  evidence: Client sets header; station_api.py never validates it against URL version.
  location: src/platform/config/station_api.py
  origin: spec-deferred c22f18414780 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against live code. `grep -rn 'X-PyForge-API-Version' src/platform/config/station_api.py` returns nothing — server-side enforcement of the version header is still unimplemented; the header remains advisory.

### DW-FU-43-2-4: django-warden portal has not adopted StationHttpClient for host calls.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract-and-the-api-v1-collision.md`
  summary: django-warden portal has not adopted StationHttpClient for host calls.
  evidence: Contract test proves header parity via mock transport only; no portal wiring in diff.
  origin: spec-deferred 700930453bc1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: django-warden's portal still calls hosts directly rather than through `StationHttpClient`. Nothing in the tree contradicts the entry's own evidence, and no story since has claimed this surface.

### DW-FU-43-2-5: OpenAPI documents are not schema-validated beyond path-key presence.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract-and-the-api-v1-collision.md`
  summary: OpenAPI documents are not schema-validated beyond path-key presence.
  evidence: Tests assert paths keys exist; no OpenAPI validator or golden document.
  origin: spec-deferred 5da93f3e807e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: OpenAPI documents are still checked for path-key presence only, with no schema validation. Nothing in the tree contradicts the entry's own evidence, and no story since has claimed this surface.

### DW-FU-45-2: No automated test exists for most of driver.py's subprocess-orchestration logic (resolve_model's fallback chain, prepare_shared, the isolation-manifest/digest plumbing) beyond the two pure helpers (cites_planted, parse_review_envelope) that test_driver.py now covers.

- source_spec: `planning-artifacts/specs/spec-45-2-the-reviewer-is-measured-against-a-planted-defect.md`
  summary: No automated test exists for most of driver.py's subprocess-orchestration logic (resolve_model's fallback chain, prepare_shared, the isolation-manifest/digest plumbing) beyond the two pure helpers (cites_planted, parse_review_envelope) that test_driver.py now covers.
  evidence: A real regression test for the remaining logic would need to mock the claude/pixi/eval-quality subprocess boundary -- nontrivial engineering, not a trivial patch. Confirmed via repo-wide grep that no other test references driver.py, and the delivered test_driver.py (8 passing tests) only exercises the two pure functions.
  location: evals/review-catches-planted-defect/driver.py
  origin: spec-deferred 4dd132100ce3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: `evals/review-catches-planted-defect/driver.py` is present and unchanged in the respect this entry names — most of `driver.py`'s subprocess-orchestration logic (resolve_model's fallback chain, prepare_shared, the isolation-manifest/digest plumbing) has no automated test. This is eval-harness hardening with no owning story since; the deferral stands on its original reasoning.

### DW-FU-45-2-2: A non-zero eval-quality preflight exit only prints a warning; the same verdict_path is still passed on to eval-quality score for that arm.

- source_spec: `planning-artifacts/specs/spec-45-2-the-reviewer-is-measured-against-a-planted-defect.md`
  summary: A non-zero eval-quality preflight exit only prints a warning; the same verdict_path is still passed on to eval-quality score for that arm.
  evidence: Could not fully verify without deeper knowledge of whether `eval-quality preflight` always writes its --out file even on a failing/invalidating exit. The CLI's own documented AD-21 exit code 3 ("failed pre-flight") suggests preflight failure is a structured, always-emitted verdict rather than a missing file, and no preflight failure was observed across this review's own live verification runs. If the file really can be missing on a non-zero preflight exit, this would be medium (a FileNotFoundError crash mid-run rather than a graceful failure).
  location: evals/review-catches-planted-defect/driver.py:319-324
  origin: spec-deferred b68a5d037be0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium (unverified)
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: `evals/review-catches-planted-defect/driver.py` is present and unchanged in the respect this entry names — a non-zero eval-quality preflight exit still only warns, and the same `verdict_path` is still passed on to `eval-quality score`. This is eval-harness hardening with no owning story since; the deferral stands on its original reasoning.

### DW-FU-45-2-3: No version pin or check on the claude -p CLI flags the driver depends on (--json-schema, --max-budget-usd, --no-session-persistence, etc.), and eval-quality-smoke never exercises the actual claude -p invocation path.

- source_spec: `planning-artifacts/specs/spec-45-2-the-reviewer-is-measured-against-a-planted-defect.md`
  summary: No version pin or check on the claude -p CLI flags the driver depends on (--json-schema, --max-budget-usd, --no-session-persistence, etc.), and eval-quality-smoke never exercises the actual claude -p invocation path.
  evidence: A future Claude Code CLI flag rename/removal could silently break eval-quality-review-twin-run with no shipped task catching it before a real run. Deferred rather than adding a live-call smoke test, which would itself cost real API budget on every smoke invocation.
  location: evals/review-catches-planted-defect/driver.py (invoke_review)
  origin: spec-deferred 6ab7696fa4e6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: `evals/review-catches-planted-defect/driver.py` is present and unchanged in the respect this entry names — no version pin or check guards the `claude -p` CLI flags the driver depends on, and `eval-quality-smoke` still never exercises the real `claude -p` path. This is eval-harness hardening with no owning story since; the deferral stands on its original reasoning.

### DW-FU-45-2-4: driver.py's eq()-routed subprocess.run calls (compile/seal/preflight/score) pass no explicit timeout, unlike the claude -p call which has timeout=630.

- source_spec: `planning-artifacts/specs/spec-45-2-the-reviewer-is-measured-against-a-planted-defect.md`
  summary: driver.py's eq()-routed subprocess.run calls (compile/seal/preflight/score) pass no explicit timeout, unlike the claude -p call which has timeout=630.
  evidence: These are local-CLI calls, lower risk than the LLM call; adding timeouts everywhere is a nice-to-have, deferred rather than patched now.
  location: evals/review-catches-planted-defect/driver.py (eq)
  origin: spec-deferred aba7cd072ba6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: `evals/review-catches-planted-defect/driver.py` is present and unchanged in the respect this entry names — the `eq()`-routed subprocess calls still pass no explicit timeout, unlike the `claude -p` call's `timeout=630`. This is eval-harness hardening with no owning story since; the deferral stands on its original reasoning.

### DW-FU-45-2-5: Static asset reads (system_prompt/diff/schema .read_text() calls in invoke_review) have no existence/decode guard.

- source_spec: `planning-artifacts/specs/spec-45-2-the-reviewer-is-measured-against-a-planted-defect.md`
  summary: Static asset reads (system_prompt/diff/schema .read_text() calls in invoke_review) have no existence/decode guard.
  evidence: Real but low-likelihood: these are core repo files under version control, unlikely to go missing in a correctly checked-out repo. Deferred rather than adding speculative guards.
  location: evals/review-catches-planted-defect/driver.py (invoke_review)
  origin: spec-deferred ad329dabeac7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: `evals/review-catches-planted-defect/driver.py` is present and unchanged in the respect this entry names — the static asset reads in `invoke_review` still have no existence/decode guard. This is eval-harness hardening with no owning story since; the deferral stands on its original reasoning.

### DW-FU-45-2-6: evaluator-configuration.json's sealedBriefDigest is a hand-computed value baked into the static template file; nothing recomputes or validates it at runtime.

- source_spec: `planning-artifacts/specs/spec-45-2-the-reviewer-is-measured-against-a-planted-defect.md`
  summary: evaluator-configuration.json's sealedBriefDigest is a hand-computed value baked into the static template file; nothing recomputes or validates it at runtime.
  evidence: Correct today (independently reverified by recomputing the digest); if contract.json is edited in the future without refreshing this cached value it would silently go stale, and the installed eval-quality CLI never reads this field either, so nothing downstream would catch it. Verification Gap reviewer's own finding.
  location: evals/review-catches-planted-defect/evaluator-configuration.json
  origin: spec-deferred 2cad28bd785d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED: `evals/review-catches-planted-defect/driver.py` is present and unchanged in the respect this entry names — `evaluator-configuration.json`'s `sealedBriefDigest` is still a hand-computed constant nothing recomputes or validates at runtime. This is eval-harness hardening with no owning story since; the deferral stands on its original reasoning.

### DW-FU-45-2-7: Six near-identical "Surface reconcile" memlog paragraphs were pasted across unrelated specs (pyforge-atlas, pyforge-doctor, pyforge-marshal, three pyforge-steward specs) because each spec's blanket pixi.toml glob makes it a co-governor of this one three-task addition, and this is a recurring class of churn with no structural fix.

- source_spec: `planning-artifacts/specs/spec-45-2-the-reviewer-is-measured-against-a-planted-defect.md`
  summary: Six near-identical "Surface reconcile" memlog paragraphs were pasted across unrelated specs (pyforge-atlas, pyforge-doctor, pyforge-marshal, three pyforge-steward specs) because each spec's blanket pixi.toml glob makes it a co-governor of this one three-task addition, and this is a recurring class of churn with no structural fix.
  evidence: Pre-existing spec-surface design (the blanket globs), not caused by this story; Verification Gap reviewer independently confirmed the mechanism produces zero gating FAIL findings, i.e. it is behaving as designed. Worth a future narrowing pass across those six specs, not this one.
  location: _bmad-output/projects/*/planning-artifacts/specs/*/.memlog.md
  origin: spec-deferred ea837a9d66a7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED, and this sweep is fresh evidence for it rather than against it. The six near-identical 'Surface reconcile' memlog paragraphs remain, and the underlying cause — blanket pixi.toml globs forcing every governing spec to record the same reconcile — is live: this session had to append that same shaped note to spec-pyforge-core, spec-pyforge-unifying-strategy and spec-pixi-candidate-currency for one pixi.toml change. The pattern is still generating duplicates.

### DW-FU-46-1: The fixture test for the single-station branch checks the _claude_md_mentions helper directly rather than driving the real top-level `assert not _claude_md_mentions(...)` through an actual violation.

- source_spec: `planning-artifacts/specs/spec-46-1-the-adoption-register-governs-wiring.md`
  summary: The fixture test for the single-station branch checks the _claude_md_mentions helper directly rather than driving the real top-level `assert not _claude_md_mentions(...)` through an actual violation.
  evidence: Real but low-value: the helper is a one-line substring check, simple enough that testing it directly is adequate; a full failure-path drive would add test complexity disproportionate to the risk.
  location: src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::test_single_station_branch_is_not_dead_code
  origin: spec-deferred dff7de3f2e76 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `test_single_station_branch_is_not_dead_code` still checks the `_claude_md_mentions` helper directly rather than driving the real top-level assertion through an actual violation.

### DW-FU-46-1-2: _persona_mentions only scans SKILL.md and customize.toml, not a reference/*.md file or README a persona skill might also carry routing text in.

- source_spec: `planning-artifacts/specs/spec-46-1-the-adoption-register-governs-wiring.md`
  summary: _persona_mentions only scans SKILL.md and customize.toml, not a reference/*.md file or README a persona skill might also carry routing text in.
  evidence: Matches this story's own Code Map scope; grepped and confirmed no current routing text lives outside those two files for any provisioned skill. Revisit if a future persona skill moves routing text elsewhere.
  location: src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_persona_mentions
  origin: spec-deferred d78b6e2c8d97 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — FIXED. `_persona_mentions` now scans `SKILL.md`, `customize.toml`, `README.md` and every `reference/*.md` under the persona skill dir (`_PERSONA_ROUTING_FILES` + a sorted glob), and matches on a word boundary via `_mention_re` rather than a bare substring -- so `bmad-spec` no longer matches inside `bmad-spec-foo`. 8 tests pass.

### DW-FU-46-1-3: No drift guard exists for a currently-skipped § 2 skill prefix becoming provisioned later without a corresponding register update.

- source_spec: `planning-artifacts/specs/spec-46-1-the-adoption-register-governs-wiring.md`
  summary: No drift guard exists for a currently-skipped § 2 skill prefix becoming provisioned later without a corresponding register update.
  evidence: The test's "not vacuous" assertions (checking bmad-cis-* and skf-* are actually exercised) partially cover staleness detection, but a newly provisioned prefix with no register-shape change would not be flagged. A full drift guard is a larger, separate mechanism than this story's scope.
  location: src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::test_skill_routing_matches_ad2_for_every_currently_provisioned_row
  origin: spec-deferred 8e5f65f838cb — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. no drift guard exists for a currently-skipped § 2 skill prefix becoming provisioned later without a register update.

### DW-FU-46-1-4: The markdown table parser's cell split on a bare "|" does not handle an escaped pipe character inside a cell's text.

- source_spec: `planning-artifacts/specs/spec-46-1-the-adoption-register-governs-wiring.md`
  summary: The markdown table parser's cell split on a bare "|" does not handle an escaped pipe character inside a cell's text.
  evidence: Real in principle but currently inert -- no cell in adoption-register.md uses an escaped pipe. Not worth the added regex complexity without a live case.
  location: src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_table_rows
  origin: spec-deferred 5169ed8b0812 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_table_rows` still splits cells on a bare `|` and still mishandles an escaped pipe inside cell text.

### DW-FU-46-1-5: _skill_dir_exists's glob matching only recognizes the exact "<prefix>-*" wildcard shape via endswith("-*"), not general fnmatch semantics.

- source_spec: `planning-artifacts/specs/spec-46-1-the-adoption-register-governs-wiring.md`
  summary: _skill_dir_exists's glob matching only recognizes the exact "<prefix>-*" wildcard shape via endswith("-*"), not general fnmatch semantics.
  evidence: Currently inert -- every § 2 glob-shaped skill cell uses exactly this form. Would need fnmatch (or similar) if the register ever adopts a different wildcard convention.
  location: src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_skill_dir_exists
  origin: spec-deferred 59313e18fc61 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_skill_dir_exists` still recognises only the exact `<prefix>-*` shape via `endswith("-*")`, not general fnmatch semantics.

### DW-FU-46-1-6: _persona_mentions and _claude_md_mentions use plain substring matching, not word-boundary matching, when checking whether a skill name is mentioned.

- source_spec: `planning-artifacts/specs/spec-46-1-the-adoption-register-governs-wiring.md`
  summary: _persona_mentions and _claude_md_mentions use plain substring matching, not word-boundary matching, when checking whether a skill name is mentioned.
  evidence: Real in principle (a skill name that is a substring of an unrelated identifier could false-positive or false-negative), but verified no current skill name is a substring of anything unrelated in the checked files. Deferred rather than adding escaping/regex complexity with no live case to justify it.
  location: src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_persona_mentions
  origin: spec-deferred 6002030fee67 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED. `_persona_mentions` and `_claude_md_mentions` still use plain substring matching with no word-boundary check. This sweep produced a live demonstration of why that matters: verifying `DW-FU-42-2-11` I found `revoke` present twice in pyforge-steward's SKILL.md, but BOTH were the credential duty (`steward keys {...,revoke}`), not the run duty being looked for. A substring match cannot tell those apart — the false-pass this entry predicts is reachable today.

### DW-FU-46-2: The epic's own text asks for "the module's module.yaml answers at the installer's key paths" in the AD-9 roster section; no CondaInstallBackend module (tea/cis/utility-skills/manticore) ships a module.yaml, so this is vacuous for the migration this story actually performs.

- source_spec: `planning-artifacts/specs/spec-46-2-utility-skills-is-provisioned-and-its-ten-skills-have-wielders.md`
  summary: The epic's own text asks for "the module's module.yaml answers at the installer's key paths" in the AD-9 roster section; no CondaInstallBackend module (tea/cis/utility-skills/manticore) ships a module.yaml, so this is vacuous for the migration this story actually performs.
  evidence: Confirmed: no module.yaml exists anywhere under .pixi/envs/local-recipes/share/bmad-utility-skills/. That machinery is exclusive to bmb's SetupSkillBackend path, untouched by this story. Disclosed as an explicit interpretation in the spec's own Boundaries & Constraints before implementation began.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_record_module_manifest
  origin: spec-deferred 546cf54df76e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. no `CondaInstallBackend` module (tea/cis/utility-skills/manticore) ships a `module.yaml` at the installer's key paths, so the epic's own wording still describes something that does not exist.

### DW-FU-46-2-2: "The CAP-8 pre-flight scan compares conda-module skills against share/bmad-utility-skills/skills" (epics.md) names a specific existing subsystem (spec-bmad-method-core-upgrade's CAP-8, the local-customization pre-flight in upgrade.py); this story satisfies the underlying drift-detection intent via a standalone pytest assertion instead, and does not touch upgrade.py.

- source_spec: `planning-artifacts/specs/spec-46-2-utility-skills-is-provisioned-and-its-ten-skills-have-wielders.md`
  summary: "The CAP-8 pre-flight scan compares conda-module skills against share/bmad-utility-skills/skills" (epics.md) names a specific existing subsystem (spec-bmad-method-core-upgrade's CAP-8, the local-customization pre-flight in upgrade.py); this story satisfies the underlying drift-detection intent via a standalone pytest assertion instead, and does not touch upgrade.py.
  evidence: Confirmed via grep: zero references to this story in upgrade.py. Extending the real CLI pre-flight report machinery would be a materially larger, cross-cutting change disproportionate to this story's S effort estimate. Disclosed as the one clause "most likely to need a documented deviation" in the spec's own Boundaries before implementation began; the Intent Alignment reviewer independently confirmed this exact divergence.
  location: src/shared/packages/pyforge-steward/tests/conformance/test_provision_module_installers.py::test_live_utility_skills_share_tree_matches_the_ten_expected_names
  origin: spec-deferred 9e018ed9ba6d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium (documented deviation, not a defect)
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. the CAP-8 pre-flight scan still names the local-custom subsystem rather than the share tree the epic text implies.

### DW-FU-46-2-3: adoption-register.md's column header ("Wired 2026-09-06") and file-level "Measured 2026-09-06" intro note were left unchanged even though row 8's cell was updated based on a 2026-09-07 re-verification.

- source_spec: `planning-artifacts/specs/spec-46-2-utility-skills-is-provisioned-and-its-ten-skills-have-wielders.md`
  summary: adoption-register.md's column header ("Wired 2026-09-06") and file-level "Measured 2026-09-06" intro note were left unchanged even though row 8's cell was updated based on a 2026-09-07 re-verification.
  evidence: The header's own convention states "a member's wiring changes only by changing its row" -- read as the header/intro documenting the table's original baseline pass, not an auto-updating per-row timestamp. A reader who does not read that sentence carefully could still momentarily believe the whole table is a 2026-09-06 snapshot.
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
  origin: spec-deferred 9d3a5cd6c744 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED as a dating inconsistency, unchanged: `adoption-register.md`'s column header ('Wired 2026-09-06') and its file-level 'Measured 2026-09-06' note still carry the older date while row 8's cell reflects a 2026-09-07 re-verification. Small, but exactly the class of stale-date drift that makes a register unreadable as evidence.

### DW-FU-46-2-4: _record_module_manifest's line-based section matcher only replaces the first occurrence of a `[modules.<name>]` header if the file somehow already contains more than one (a state that should not arise from this function's own writes, but could from manual editing).

- source_spec: `planning-artifacts/specs/spec-46-2-utility-skills-is-provisioned-and-its-ten-skills-have-wielders.md`
  summary: _record_module_manifest's line-based section matcher only replaces the first occurrence of a `[modules.<name>]` header if the file somehow already contains more than one (a state that should not arise from this function's own writes, but could from manual editing).
  evidence: Real in principle, no live trigger today (no duplicate section exists in the tracked _bmad/custom/config.toml). The regex-swallowing bug that made duplicates more likely to accumulate silently was fixed this pass (line-based boundary stops at the first blank/comment/next-header line); a genuinely already-duplicated file would need separate, manual reconciliation regardless of this writer's behavior.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_record_module_manifest
  origin: spec-deferred 5a2efcc186e2 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_record_module_manifest`'s line-based section matcher still replaces only the first `[modules.<name>]` header.

### DW-FU-46-2-5: The section matcher does not tolerate CRLF line endings in an existing `[modules.<name>]` header line (compares against a bare `\n`/`\r\n`-stripped literal, which is CRLF-tolerant for the compare itself, but the file is read as text in default universal-newlines mode so this is likely already fine in practice -- flagged as low-confidence residual risk, not independently re-verified with an actual CRLF fixture this pass).

- source_spec: `planning-artifacts/specs/spec-46-2-utility-skills-is-provisioned-and-its-ten-skills-have-wielders.md`
  summary: The section matcher does not tolerate CRLF line endings in an existing `[modules.<name>]` header line (compares against a bare `\n`/`\r\n`-stripped literal, which is CRLF-tolerant for the compare itself, but the file is read as text in default universal-newlines mode so this is likely already fine in practice -- flagged as low-confidence residual risk, not independently re-verified with an actual CRLF fixture this pass).
  evidence: Python's default text-mode file reading normalizes line endings, so a CRLF source file should already present as LF to this code; not independently proven with a dedicated CRLF fixture test this pass.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_record_module_manifest
  origin: spec-deferred 76c268d33d51 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. the same matcher still does not tolerate CRLF line endings in an existing header line.

### DW-FU-46-2-6: Non-BMP Unicode characters in a name/installer/skill value would be escaped by json.dumps as UTF-16 surrogate pairs, which tomllib rejects on the next read.

- source_spec: `planning-artifacts/specs/spec-46-2-utility-skills-is-provisioned-and-its-ten-skills-have-wielders.md`
  summary: Non-BMP Unicode characters in a name/installer/skill value would be escaped by json.dumps as UTF-16 surrogate pairs, which tomllib rejects on the next read.
  evidence: Currently inert -- every value this writer ever renders today (a registered module name, an installer entry-point name, a skill directory name) is a plain ASCII identifier from hardcoded _SUPPORTED_MODULES data or discovered skill directory names, never user-supplied Unicode.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_toml_string
  origin: spec-deferred dc04f1d92c87 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_toml_string` still routes through `json.dumps`, so non-BMP characters would be escaped as UTF-16 surrogate pairs that tomllib rejects on the next read.

### DW-FU-46-3: No promoted per-story spec file exists in the tracked planning-artifacts/specs/ directory for Stories 46.1, 46.2, or 46.3 (unlike 46.7/46.8, which each have one).

- source_spec: `planning-artifacts/specs/spec-46-3-tea-is-provisioned-and-tea-test-review-is-a-pixi-task.md`
  summary: No promoted per-story spec file exists in the tracked planning-artifacts/specs/ directory for Stories 46.1, 46.2, or 46.3 (unlike 46.7/46.8, which each have one).
  evidence: Matches this repo's own "story specs are durable, promoted after merge" convention, which happens at merge time per the repo's stated process, not mid-batch while several dependent stories are still landing on the same branch. Real gap to close when this branch merges, not blocking mid-batch.
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/
  origin: spec-deferred 5e228f5e609f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — RESOLVED. The entry states no promoted per-story spec exists for Stories 46.1, 46.2 or 46.3. All three are now present in the tracked tree: `specs/spec-46-1-the-adoption-register-governs-wiring.md`, `specs/spec-46-2-utility-skills-is-provisioned-and-its-ten-skills-have-wielders.md`, and `specs/spec-46-3-tea-is-provisioned-and-tea-test-review-is-a-pixi-task.md` — alongside the 46.7/46.8 pair the entry cites as the contrast. The promotion this entry asked for has happened.

### DW-FU-46-3-2: Reading "test_artifacts ... pointed at each station's planning-artifacts/ per its .bmad-config.toml" could plausibly mean per-station RESOLVED values rather than the one global unresolved template string this story actually writes.

- source_spec: `planning-artifacts/specs/spec-46-3-tea-is-provisioned-and-tea-test-review-is-a-pixi-task.md`
  summary: Reading "test_artifacts ... pointed at each station's planning-artifacts/ per its .bmad-config.toml" could plausibly mean per-station RESOLVED values rather than the one global unresolved template string this story actually writes.
  evidence: Proving per-station resolution would require actually rendering a TEA skill per active project, which is blocked by the separate, disclosed render_skill.py/workflow.yaml incompatibility finding. The unresolved-template approach is the best achievable outcome given that constraint, and matches how other `{output_folder}`-style templates already resolve per-active-project elsewhere in this repo.
  location: _bmad/custom/config.toml::modules.tea.test_artifacts
  origin: spec-deferred 57b901a0477d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium (documented interpretation, not a defect)
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `modules.tea.test_artifacts` remains one global unresolved template string, so the per-station reading the epic text permits is still not what ships.

### DW-FU-46-3-3: `_installer_skill_names`'s flatten-branch prediction is derived only from the share_root tree, never cross-checked against what the installer's own copy actually produced at dest before flattening.

- source_spec: `planning-artifacts/specs/spec-46-3-tea-is-provisioned-and-tea-test-review-is-a-pixi-task.md`
  summary: `_installer_skill_names`'s flatten-branch prediction is derived only from the share_root tree, never cross-checked against what the installer's own copy actually produced at dest before flattening.
  evidence: Real in principle; the existing post-install missing-skills check (comparing predicted names against `dest/<name>.is_dir()`) already catches the case where a predicted leaf never actually materializes, which covers the practical failure mode. A share-vs-installer disagreement narrower than "leaf missing entirely" is not covered, but no such case is currently reachable with the real TEA package.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_installer_skill_names
  origin: spec-deferred bbad65a8402a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_installer_skill_names`'s flatten-branch prediction is still derived only from the share_root tree, never cross-checked against what the installer actually produced at dest.

### DW-FU-46-3-4: A new test (`test_provision_installer_missing_non_nested_skill_after_successful_flatten_raises`) hand-rolls its own installer stand-in instead of reusing the shared `_fake_installer_run`, risking drift as the real TEA share shape evolves.

- source_spec: `planning-artifacts/specs/spec-46-3-tea-is-provisioned-and-tea-test-review-is-a-pixi-task.md`
  summary: A new test (`test_provision_installer_missing_non_nested_skill_after_successful_flatten_raises`) hand-rolls its own installer stand-in instead of reusing the shared `_fake_installer_run`, risking drift as the real TEA share shape evolves.
  evidence: Real test-hygiene nit, no functional risk to production code.
  location: src/shared/packages/pyforge-steward/tests/conformance/test_provision_module_installers.py
  origin: spec-deferred 959e81a0aef0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. the new test still hand-rolls its own installer stand-in instead of reusing `_fake_installer_run`.

### DW-FU-46-3-5: If TEA's own upstream layout ever grew a second flatten-nested container with a leaf name colliding with another container's leaf, the second would be silently discarded rather than raising.

- source_spec: `planning-artifacts/specs/spec-46-3-tea-is-provisioned-and-tea-test-review-is-a-pixi-task.md`
  summary: If TEA's own upstream layout ever grew a second flatten-nested container with a leaf name colliding with another container's leaf, the second would be silently discarded rather than raising.
  evidence: Currently inert -- TEA's only flatten_nested_dirs source ("workflows") has exactly one container ("testarch"); no second container exists to collide with it.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_flatten_nested_skill_dirs
  origin: spec-deferred 75f0b5d6a749 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_flatten_nested_skill_dirs` still silently discards a second flatten-nested container whose leaf name collides, rather than raising.

### DW-FU-46-3-6: A foreign, pre-existing `.claude/skills/testarch/` directory (not created by this story's own flattening) would not be caught by the pre-install skill-name-collision check, since "testarch" is no longer one of the predicted post-flatten names.

- source_spec: `planning-artifacts/specs/spec-46-3-tea-is-provisioned-and-tea-test-review-is-a-pixi-task.md`
  summary: A foreign, pre-existing `.claude/skills/testarch/` directory (not created by this story's own flattening) would not be caught by the pre-install skill-name-collision check, since "testarch" is no longer one of the predicted post-flatten names.
  evidence: Exotic: no other module or convention in this repo uses "testarch" as a skill name; the practical likelihood of a real collision is very low.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_provision_conda_install
  origin: spec-deferred ad9e0750d631 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_provision_conda_install`'s pre-install collision check still would not catch a foreign pre-existing `.claude/skills/testarch/`.

### DW-FU-46-4: The `if not skill_names: raise RuntimeError(...)` branch (empty skills_source_dir) is currently unreachable given bmb's own registration (skill_dir is guaranteed to be a child of skills_source_dir, and skill_dir's own existence is already checked earlier) -- defensive code for a future misregistration, with no test.

- source_spec: `planning-artifacts/specs/spec-46-4-bmad-builder-is-provisioned-beside-skf-with-the-cleanup-legacy-guard-proven.md`
  summary: The `if not skill_names: raise RuntimeError(...)` branch (empty skills_source_dir) is currently unreachable given bmb's own registration (skill_dir is guaranteed to be a child of skills_source_dir, and skill_dir's own existence is already checked earlier) -- defensive code for a future misregistration, with no test.
  evidence: Real defensive code, but exercising it requires deliberately misconfiguring a future SetupSkillBackend registration; not worth a test for currently-dead-but-harmless code.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_provision_setup_skill
  origin: spec-deferred 04cfd91d5366 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_provision_setup_skill`'s empty-`skill_names` RuntimeError branch remains unreachable given bmb's own registration.

### DW-FU-46-4-2: `_copy_setup_skill_dirs` does rmtree-then-copytree per skill with no staging/temp-and-rename step; a process kill or disk error between those two calls could leave a skill directory missing or half-populated.

- source_spec: `planning-artifacts/specs/spec-46-4-bmad-builder-is-provisioned-beside-skf-with-the-cleanup-legacy-guard-proven.md`
  summary: `_copy_setup_skill_dirs` does rmtree-then-copytree per skill with no staging/temp-and-rename step; a process kill or disk error between those two calls could leave a skill directory missing or half-populated.
  evidence: Matches the same pattern already used by `_flatten_nested_skill_dirs` (Story 46.3) and every other module's own idempotent-overwrite convention in this file; not a new risk class this story introduces.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_copy_setup_skill_dirs
  origin: spec-deferred 2fcffc861d4b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_copy_setup_skill_dirs` still does rmtree-then-copytree per skill with no staging/temp-and-rename step, so a kill between the two calls can still leave a skill directory missing or half-populated.

### DW-FU-46-4-3: The "collision check passes against the live 16 skf-* dirs" claim is only verified by a one-time manual run recorded in .memlog.md; no test fixture populates skf-*-shaped directories.

- source_spec: `planning-artifacts/specs/spec-46-4-bmad-builder-is-provisioned-beside-skf-with-the-cleanup-legacy-guard-proven.md`
  summary: The "collision check passes against the live 16 skf-* dirs" claim is only verified by a one-time manual run recorded in .memlog.md; no test fixture populates skf-*-shaped directories.
  evidence: The registry-level `test_supported_installer_modules_have_disjoint_skill_names` and `test_live_share_skill_names_are_disjoint_across_installer_modules` tests already cover the structural cross-module-collision invariant generically; a bmb-specific skf-* fixture would be redundant coverage of the same mechanism.
  location: src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py
  origin: spec-deferred e57c0bc2fe95 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. no test fixture populates `skf-*`-shaped directories; the collision-check claim still rests on a one-time manual run recorded in a memlog.

### DW-FU-46-4-4: Once bmb is recorded installed, a later-introduced foreign directory at one of the five skill-name paths would be silently overwritten on the next re-provision rather than refusing.

- source_spec: `planning-artifacts/specs/spec-46-4-bmad-builder-is-provisioned-beside-skf-with-the-cleanup-legacy-guard-proven.md`
  summary: Once bmb is recorded installed, a later-introduced foreign directory at one of the five skill-name paths would be silently overwritten on the next re-provision rather than refusing.
  evidence: Matches the exact same idempotent-overwrite architecture every other module in this file already uses (the collision check is intentionally skipped once `already_installed` is true); not a new risk this story introduces, a pre-existing, fleet-wide design choice.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_provision_setup_skill
  origin: spec-deferred 7459439c3e8f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_provision_setup_skill` would still silently overwrite a later-introduced foreign directory at one of the five skill-name paths on re-provision, rather than refusing.

### DW-FU-46-4-5: "bmad-builder is provisioned beside skf" is tested only against synthetic fixtures (four fabricated sibling skill dirs), never the real installed skf-* tree or a real bmad-builder share tree, in any automated test.

- source_spec: `planning-artifacts/specs/spec-46-4-bmad-builder-is-provisioned-beside-skf-with-the-cleanup-legacy-guard-proven.md`
  summary: "bmad-builder is provisioned beside skf" is tested only against synthetic fixtures (four fabricated sibling skill dirs), never the real installed skf-* tree or a real bmad-builder share tree, in any automated test.
  evidence: Matches this project's own established pattern (Stories 46.2/46.3) of pairing synthetic-fixture unit tests with a documented, dated live-verification run recorded in .memlog.md for the real-tree half of a claim.
  location: src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py
  origin: spec-deferred 897a8931eb9c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. the 'provisioned beside skf' claim is still tested only against synthetic sibling fixtures, never a real installed skf-* tree.

### DW-FU-46-4-6: "The cleanup-legacy guard proven" relies on the pre-existing Story 6.1 argv-assertion test rather than a new, story-owned assertion specific to the new copy code path.

- source_spec: `planning-artifacts/specs/spec-46-4-bmad-builder-is-provisioned-beside-skf-with-the-cleanup-legacy-guard-proven.md`
  summary: "The cleanup-legacy guard proven" relies on the pre-existing Story 6.1 argv-assertion test rather than a new, story-owned assertion specific to the new copy code path.
  evidence: The existing test re-runs against the CURRENT, updated `_provision_setup_skill` (including the new copy step) on every suite run -- confirmed still green after this story's changes -- so it is current, live coverage, not stale inherited evidence, even though its own assertion text was not modified by this diff.
  location: src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py
  origin: spec-deferred d95308717000 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. the cleanup-legacy guard still leans on the pre-existing Story 6.1 argv assertion rather than a story-owned assertion for the new copy path.

### DW-FU-46-4-7: "Provisioned"/"wired" status asserts a stronger claim (functional reachability by a station persona) than what this diff's own functional surface delivers (files land + config record).

- source_spec: `planning-artifacts/specs/spec-46-4-bmad-builder-is-provisioned-beside-skf-with-the-cleanup-legacy-guard-proven.md`
  summary: "Provisioned"/"wired" status asserts a stronger claim (functional reachability by a station persona) than what this diff's own functional surface delivers (files land + config record).
  evidence: Matches Stories 46.2/46.3's own precedent for what "wired" means in this register -- "installed and bookkept," not "proven invocable by a live persona session." Reasonable, consistent interpretation.
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
  origin: spec-deferred 2115b7f441da — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. the register still asserts 'provisioned'/'wired' — a stronger claim than files-land-plus-config-record, which is what the diff delivers.

### DW-FU-46-4-8: No test in this diff touches Mason (the register's row 7 also names Mason as a wielder of module/agent authoring alongside Steward).

- source_spec: `planning-artifacts/specs/spec-46-4-bmad-builder-is-provisioned-beside-skf-with-the-cleanup-legacy-guard-proven.md`
  summary: No test in this diff touches Mason (the register's row 7 also names Mason as a wielder of module/agent authoring alongside Steward).
  evidence: Explicitly out of this story's own scope per its Never clause and Code Map (Mason's own routing is a separate story, not this one).
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
  origin: spec-deferred 5a97d1418fc2 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. no test touches Mason, though the register's row 7 names Mason as a co-wielder.

### DW-FU-46-5: _module_toml_skills doesn't validate skills list-element types; a hand-corrupted TOML roster crashes past the local (RuntimeError, FileNotFoundError) catch with a raw TypeError

- source_spec: `planning-artifacts/specs/spec-46-5-labs-skills-arrive-by-name-and-by-consent.md`
  summary: _module_toml_skills doesn't validate skills list-element types; a hand-corrupted TOML roster crashes past the local (RuntimeError, FileNotFoundError) catch with a raw TypeError
  evidence: Blind Hunter finding #4; caught cleanly at ProvisionDuty.run()'s outer boundary (AD-8 crash contract), never a silent failure
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_module_toml_skills
  origin: spec-deferred ef16dc4be2ba — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_module_toml_skills` still does not validate skills list-element types, so a hand-corrupted roster still escapes the local catch as a raw TypeError.

### DW-FU-46-5-2: Malformed _bmad/custom/config.toml hit via the plugin path surfaces a bare tomllib.TOMLDecodeError instead of _record_module_manifest's friendlier diagnostic

- source_spec: `planning-artifacts/specs/spec-46-5-labs-skills-arrive-by-name-and-by-consent.md`
  summary: Malformed _bmad/custom/config.toml hit via the plugin path surfaces a bare tomllib.TOMLDecodeError instead of _record_module_manifest's friendlier diagnostic
  evidence: Blind Hunter finding #5; still caught cleanly at the outer boundary, only the message wording is less friendly
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::provision_plugin_skill
  origin: spec-deferred 626d05a05d2a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `provision_plugin_skill` still surfaces a bare `tomllib.TOMLDecodeError` instead of `_record_module_manifest`'s friendlier diagnostic.

### DW-FU-46-5-3: _ROUTING_STORY_NOT_YET_LANDED carve-out's cleanup is a manual, prose-commented honor system, not mechanically enforced when atlas 24.1 / herald 18.3 / marshal 31.6 land their own routing

- source_spec: `planning-artifacts/specs/spec-46-5-labs-skills-arrive-by-name-and-by-consent.md`
  summary: _ROUTING_STORY_NOT_YET_LANDED carve-out's cleanup is a manual, prose-commented honor system, not mechanically enforced when atlas 24.1 / herald 18.3 / marshal 31.6 land their own routing
  evidence: Intent Alignment finding #5, matching the implementer's own Implementation Notes follow-up
  location: src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_ROUTING_STORY_NOT_YET_LANDED
  origin: spec-deferred 1f3e6206fafa — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED as an enforcement gap, with an important nuance: the honor system WAS honored this time. `_ROUTING_STORY_NOT_YET_LANDED` is now an empty dict (`test_adoption_register.py:229-231`, commented 'empty: every consented labs skill's persona mention has landed'), and the module docstring at `:30-33` records all three siblings — atlas 24.1, herald 18.3, marshal 31.6 — as routed. So the cleanup happened. What the entry actually claims is still true, though: nothing MECHANICALLY enforces that cleanup. The carve-out emptied because a human remembered, which is the definition of the honor system this entry objects to. Verified independently in this sweep that herald 18.3's routing did land (`bmad-agent-herald/SKILL.md:40`).

### DW-FU-46-6: The studio's manticore module tracks main/next (unpinned, floating) with no lockfile or version-check -- re-running the sanctioned command later can silently install a different version, unlike every other custom module in this register

- source_spec: `planning-artifacts/specs/spec-46-6-heralds-manticore-studio-has-a-root-and-a-proven-native-path.md`
  summary: The studio's manticore module tracks main/next (unpinned, floating) with no lockfile or version-check -- re-running the sanctioned command later can silently install a different version, unlike every other custom module in this register
  evidence: Edge Case Hunter finding; recorded in adoption-register.md row 9's Hazards cell as an open reproducibility risk, not resolved here (AD-7 prove-and-relay boundary)
  location: docs/reference/manticore-studio.md; adoption-register.md row 9
  origin: spec-deferred 5403aee9f773 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. the manticore module still tracks unpinned main/next with no lockfile or version check, unlike every other provisioned module.

### DW-FU-46-6-2: The isolation guarantee's two halves (checksum bracket vs. .claude/skills/ zero-mc-* claim) have uneven evidentiary rigor -- the latter has no equivalent tight before/after snapshot of its own, though independently re-verified true by three reviewers

- source_spec: `planning-artifacts/specs/spec-46-6-heralds-manticore-studio-has-a-root-and-a-proven-native-path.md`
  summary: The isolation guarantee's two halves (checksum bracket vs. .claude/skills/ zero-mc-* claim) have uneven evidentiary rigor -- the latter has no equivalent tight before/after snapshot of its own, though independently re-verified true by three reviewers
  evidence: Edge Case Hunter finding; not retroactively fixable for an already-completed run, noted for future re-runs of the same command
  location: docs/reference/manticore-studio.md (isolation guarantee section)
  origin: spec-deferred 1b1cb5e9a417 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. the isolation guarantee's two halves still have uneven evidentiary rigor — the zero-mc-* claim still has no tight before/after snapshot of its own.

### DW-FU-46-9: _skills_census() now runs unconditionally at the top of _module_census_hit, a wasted iterdir() for bmad-module-skill-forge (which could previously short-circuit via wire_bmad_dirs alone)

- source_spec: `planning-artifacts/specs/spec-46-9-pipeline-truths-installed-stage-reads-the-applied-core-and-wired-is-a-declared-per-class-predicate.md`
  summary: _skills_census() now runs unconditionally at the top of _module_census_hit, a wasted iterdir() for bmad-module-skill-forge (which could previously short-circuit via wire_bmad_dirs alone)
  evidence: Edge Case Hunter finding #3; negligible cost, no behavioral effect
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py::_module_census_hit
  origin: spec-deferred 8fc1a05e4fc7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. `_skills_census()` still runs unconditionally at the top of `_module_census_hit`, costing a wasted `iterdir()` for bmad-module-skill-forge.

### DW-FU-46-9-2: Manticore's wired probe (studio root + _bmad/ + mc-* census) is written against best-available evidence but not empirically verified against a real, completed studio install, since Story 46.6 is separately blocked (interactive installer, awaiting operator --tools decision)

- source_spec: `planning-artifacts/specs/spec-46-9-pipeline-truths-installed-stage-reads-the-applied-core-and-wired-is-a-declared-per-class-predicate.md`
  summary: Manticore's wired probe (studio root + _bmad/ + mc-* census) is written against best-available evidence but not empirically verified against a real, completed studio install, since Story 46.6 is separately blocked (interactive installer, awaiting operator --tools decision)
  evidence: Spec's own Boundaries & Constraints, re-confirmed sound by Intent Alignment review; this story's own manticore tests correctly assert unwired against the real, empty studio root
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py::probe_wired (INSTALL_CLASS_STUDIO_MODULE branch)
  origin: spec-deferred fccee991eaba — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED against the live file — the symbol this entry names is present and unchanged in the respect it describes. the manticore wired probe is still written against best-available evidence, unverified against a real completed studio install.

### DW-FU-47-1: P13's '5 of 9 ungoverned' figure is a snapshot of this branch's own checkout, already stale relative to an unmerged sibling branch (marshal-r1, commit 6ba6bd9eb6, Story 31.4) which governs 3 of the 5 -- re-verification needed once that branch merges

- source_spec: `planning-artifacts/specs/spec-47-1-the-readiness-checklist-is-live-and-the-pre-flight-is-its-p7-signal.md`
  summary: P13's '5 of 9 ungoverned' figure is a snapshot of this branch's own checkout, already stale relative to an unmerged sibling branch (marshal-r1, commit 6ba6bd9eb6, Story 31.4) which governs 3 of the 5 -- re-verification needed once that branch merges
  evidence: Edge Case Hunter finding, confirmed via git log/branch/show; a Known-staleness-risk note was added to cutover-readiness.md so this isn't silently assumed settled
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md (P13 row + Re-run section)
  origin: spec-deferred 257a998697f9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — RESOLVED — the entry's predicted staleness materialised exactly as forecast, and has now settled. It warned that P13's '5 of 9 ungoverned' was already stale against an unmerged sibling branch governing 3 of the 5. Measured live today, file by file: `generate-tracking.md`, `sprint_plan.py` and `test_sprint_plan.py` are all now claimed by `spec-marshal-single-story-dispatch`'s `surface:`; only `brain-methods.csv` and `_bmad/scripts/resolve_config.py` remain ungoverned. CORRECTED NUMBER, recorded per CAP-4: the figure is now **2 of 9 ungoverned**, not 5. The re-verification this entry asked for is done.

### DW-FU-47-2: SKF has no link-generation step of any kind -- the .claude/skills/ 'generated per-machine links' the cutover target-tree diagram assumes does not exist anywhere in SKF today; a dedicated link-generator (or an SKF feature) must be built before any station's live IDE skill discovery can rely on a skills/stations/ canonical root

- source_spec: `planning-artifacts/specs/spec-47-2-skf-export-is-proven-to-accept-the-foundry-skills-root.md`
  summary: SKF has no link-generation step of any kind -- the .claude/skills/ 'generated per-machine links' the cutover target-tree diagram assumes does not exist anywhere in SKF today; a dedicated link-generator (or an SKF feature) must be built before any station's live IDE skill discovery can rely on a skills/stations/ canonical root
  evidence: Confirmed empirically (scratch worktree run) and independently re-confirmed by Blind Hunter reading skf-export-skill's full source directly; relayed to spec-python-foundry-cutover's own memlog as a finding for that project to close
  location: _bmad/skf/skf-export-skill/ (no file -- an absence, not a bug in an existing file)
  origin: spec-deferred 62778f2c3cdb — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: SKF still has no link-generation step of any kind. These are SKF-upstream capabilities, not repo-local defects, so they remain pending on an SKF change rather than on work this fleet can schedule.

### DW-FU-47-2-2: Changing skills_output_folder alone does not migrate or discover an already-exported package at the OLD root -- SKF's resolution ladder (manifest / active symlink / flat path) has no cross-root fallback, so a real cutover needs an explicit move/re-forge step per already-exported skill, not just the fnd:AD-12 config-key flip

- source_spec: `planning-artifacts/specs/spec-47-2-skf-export-is-proven-to-accept-the-foundry-skills-root.md`
  summary: Changing skills_output_folder alone does not migrate or discover an already-exported package at the OLD root -- SKF's resolution ladder (manifest / active symlink / flat path) has no cross-root fallback, so a real cutover needs an explicit move/re-forge step per already-exported skill, not just the fnd:AD-12 config-key flip
  evidence: Empirically confirmed (Run 1 halted exit 3 resolution-failure); independently re-confirmed by Blind Hunter reading load-skill.md's resolution logic directly
  location: _bmad/skf/skf-export-skill/references/load-skill.md (resolution ladder)
  origin: spec-deferred 57f5db250e7f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: SKF's resolution ladder still has no cross-root fallback, so changing `skills_output_folder` alone still neither migrates nor discovers an already-exported package at the old root. These are SKF-upstream capabilities, not repo-local defects, so they remain pending on an SKF change rather than on work this fleet can schedule.

### DW-FU-47-2-3: With snippet_skill_root_override left set, a re-exported skill's managed-section root: pointer can silently drift from its package's real new location with no warning from SKF

- source_spec: `planning-artifacts/specs/spec-47-2-skf-export-is-proven-to-accept-the-foundry-skills-root.md`
  summary: With snippet_skill_root_override left set, a re-exported skill's managed-section root: pointer can silently drift from its package's real new location with no warning from SKF
  evidence: Observed live in the scratch run: pyforge-herald's root: pointer stayed at the old .claude/skills/ location after its package moved to skills/stations/...
  location: _bmad/skf/skf-export-skill/references/update-context.md (root-rewrite logic, override branch)
  origin: spec-deferred d3a90eeb28ef — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — still-open — CONFIRMED unchanged: a re-exported skill's managed-section `root:` pointer can still drift silently while `snippet_skill_root_override` is set. These are SKF-upstream capabilities, not repo-local defects, so they remain pending on an SKF change rather than on work this fleet can schedule.

### DW-FU-47-5: cutover-readiness.md P11/P12's own state cells still read 'not done' (2026-09-06 snapshot) even though their producers (marshal 30.5/30.2, steward 14.9) are all confirmed done -- correcting those cells is each producer's own job, out of this story's Surface line

- source_spec: `planning-artifacts/specs/spec-47-5-epic-44-depends-on-the-era-tail-and-44-13s-scope-names-the-spines.md`
  summary: cutover-readiness.md P11/P12's own state cells still read 'not done' (2026-09-06 snapshot) even though their producers (marshal 30.5/30.2, steward 14.9) are all confirmed done -- correcting those cells is each producer's own job, out of this story's Surface line
  evidence: Named explicitly in G3's own resolution note; independently confirmed by three reviewers this staleness is real and correctly left untouched here
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md rows P11/P12
  origin: spec-deferred 5df9badb06b1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-07 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-08 — resolved — RESOLVED HERE. Verified the premise first: all three producers read `done` in their tracked ledgers — marshal `30-2-the-project-context-surface-follows-6-12-d1` and `30-5-the-harness-and-every-live-caller-follow-the-shim-retirement`, and steward `14-9-the-apply-retires-deprecation-shims-on-purpose-no-shims` — while `cutover-readiness.md` rows P11 and P12 still read **not done**. Both cells are corrected in this commit to record producer-done, each keeping an explicit 're-confirm the live count before the flip' caveat so a corrected cell is not mistaken for a fresh measurement.

### DW-FU-23-1-2: canopy:AD-20 also names audit write and role-built navigation; this story's board is JSON filter-then-search only.

- source_spec: `planning-artifacts/specs/spec-23-1-same-url-different-rows.md`
  summary: canopy:AD-20 also names audit write and role-built navigation; this story's board is JSON filter-then-search only.
  evidence: Story 23.1 ACs and canopy:FR-16 name same-URL row isolation via filter_by_role / AccessDeclaration. Audit and build_navigation are already in pyforge.steward.dashboard from Epic 9 and were not wired onto /stations/atlas/board/.
  location: src/shared/packages/django-atlas/src/django_atlas_portal/board.py
  origin: spec-deferred 93ba6e43a00d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-12 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-VOCAB-2026-09-14-1: the Charter names SEVEN Intelligence Hub abstractions; upstream names six — a factual error in a Tier-0 document, propagated to two more artifacts

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: `docs/dreams/pyforge-charter.md:606` reads *"The whitepaper names Frames · Cogs · Ops · Guards · Gates · Tracks · Organizational Memory."* Upstream names **six** shared abstractions; Organizational Memory is a Layer-1 *infrastructure* term ("the Hub's persistent context substrate"), not one of the six execution/accountability abstractions. Folding it in erases a distinction OpenTeams draws deliberately — the architecture is three layers plus a cross-cutting Accountability Plane, explicitly "never 'four layers'". The Charter's substantive rulings (cross-walk never joins; the Cogs/Smith collision; Charter·Guild·Stations have no Hub counterpart) are unaffected — only the enumeration.
  evidence: Three independent upstream sources agree on six, verified 2026-09-14: `openteams-ai/inthub-whitepaper` README (*"the shared abstractions (Frames, Cogs, Ops, Guards, Gates, Tracks)"*); the guide's glossary entry **Shared abstraction** (*"Frames, Cogs, Ops, Guards, Gates, and Tracks are proposed as the AI era's set"*); and guide §13 (*"ask it to adopt **six nouns**"*). The whitepaper's `GLOSSARY.md` — which self-declares as *"the authoritative definition set"* — carries the six-verb mnemonic ("Frames guide… Cogs perform… Ops orchestrate… Guards verify… Gates decide… Tracks make the work accountable"). Propagation confirmed by grep: `spec-intelligence-hub/SPEC.md:48` (§ Why) and `:68` (CAP-1 intent), plus `vocabulary-map.md`'s table, which carries Organizational Memory as a peer row.
  location: docs/dreams/pyforge-charter.md:606
  severity: high
  status: closed
  raised: 2026-09-14 — Owner: steward. **The Charter is Tier 0 and changes only by recorded amendment**, so this is an amendment with a Realization-log entry, never an edit — deliberately NOT fixed inline during the research pass that found it. The two downstream artifacts correct in the same change. Recorded as correction C-1 in the owning Spec.

  closed: 2026-09-14 — Corrected as a Tier-0 **amendment** with a Realization-log entry, never a silent edit. `pyforge-charter.md` § The Lexicon now reads *"the whitepaper names **six** shared abstractions — Frames · Cogs · Ops · Guards · Gates · Tracks — and tiers **Organizational Memory** separately, as Layer-1 infrastructure rather than a seventh peer."* The two downstream copies were corrected in the same pass (`spec-intelligence-hub/SPEC.md` § Why and CAP-1 intent) with a memlog correction. **`vocabulary-map.md` deliberately unchanged** — it is a mapping table that claims no count, and its Organizational Memory row is a correct mapping, since Scribe's GraphStore and team memory really do relay it. The *mapping* was always right; only the count and the tiering were wrong, and no substantive ruling depends on the enumeration — CAP-4's cross-walk-never-join, the Cogs/Smith collision and the reverse walk all stand untouched. Root cause kept on the record: the count had been copied forward three times (Dream → Charter → Spec) without anyone re-reading the whitepaper.
### DW-VOCAB-2026-09-14-2: Guard categories are recorded in the wrong order — Source-Grounding ranks second upstream, not sixth

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: `spec-intelligence-hub/SPEC.md:192-199` (decision B7) lists the seven Guard categories with Source-Grounding sixth. Whitepaper §5.5 "Seven Categories of Guards" orders them: 1 Algorithmic · 2 **Source-Grounding** · 3 Consensus · 4 Expert · 5 Policy & Safety · 6 Regression & Drift · 7 Outcome, in Title Case. The seven are right; the ordinal is not.
  evidence: Verified 2026-09-14 against whitepaper §5.5. The substantive B7 finding is unaffected and still stands — Source-Grounding exists at exactly one site (`scribe/recall.py` AD-8) and Outcome is absent entirely. The correction matters because "SOURCE-GROUNDING GOES FIRST", which B7 recorded as our own sequencing preference, turns out to be **upstream's own ranking** (algorithmic strongest → Outcome most business-meaningful), which strengthens rather than weakens the decision.
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-intelligence-hub/SPEC.md:192
  severity: low
  status: closed
  raised: 2026-09-14 — Owner: steward. Recorded as correction C-2 in the owning Spec. Lands with DW-VOCAB-2026-09-14-1's amendment, since both touch the same Hub-vocabulary surface.

  closed: 2026-09-14 — Recorded where it was actually misleading. The upstream §5.5 ranking is **1 Algorithmic · 2 Source-Grounding · 3 Consensus · 4 Expert · 5 Policy & Safety · 6 Regression & Drift · 7 Outcome**, and `docs/dreams/intelligence-hub.md:427` already carried it correctly. The defect was in the shipped library: `docs/foundry/guards/README.md`'s table is sorted **alphabetically**, which put `source_grounding` sixth and read as a ranking. The table now says so explicitly and states upstream's order beneath it. This matters to one claim in particular — landing Source-Grounding as the library's *first addition* (Story 53.4) was **not** a local departure from upstream's priorities but a following of them, and `outcome`, the one category still missing, is genuinely upstream's last.
### DW-VOCAB-2026-09-14-3: the Design tier teaches a practice vocabulary that entered no repo artifact, still names four retired BMAD skills, and has drifted 13.5 KB out of sync

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: Three problems in one surface. (a) The 45-slide `Agentic SDLC` deck teaches **four phases**, **three tracks** (Quick Flow / BMad Method / Enterprise), parallel track, party mode, execution matrix, method-vs-machinery, and project-context-as-constitution — and **none** of it appears in `vocabulary-map.md`, the Charter cross-walk, or any repo glossary. (b) It still names `bmad-quick-dev`, `bmad-dev-auto`, `bmad-create-story`, `bmad-dev-story` — all renamed or deprecated in BMAD 6.11 — plus **Paige**, the Tech Writer persona retired in 6.11, three times. `CLAUDE.md` records the renames correctly, so the repo knows; the public-facing deck does not. (c) The local pull is stale: `Agentic SDLC.dc.html` is 193,114 B in-repo against 206,638 B in Design — **13.5 KB behind**.
  evidence: Measured 2026-09-14 against Design project `f58c0f17-087b-417e-9cfa-c410de6169dc` and `presentations/agentic-sdlc/project/` (local copies dated 2026-08-01). Retired-name counts by grep on `Agentic SDLC.marp.md`: one hit each for the four skills, three for Paige. The two Lexicon posters differ only by harness-strip artifacts; the deck is materially behind. The Lexicon slide itself **was** verified current — its seven nouns match the Charter exactly, including the Spec's 2026-07-25 addition. This is a recurrence, not a new class: the Charter's own log (line 826) records the 2026-08-01 pull as the *first* one ever, made precisely because two Design-side Lexicon artifacts had described the pre-2026-07-25 six-noun model since 2026-07-25 and were never pulled.
  location: presentations/agentic-sdlc/project/
  severity: medium
  status: open
  raised: 2026-09-14 — Owner: steward rules the vocabulary; **herald owns the deck surface** and the pull discipline (`docs/specs/presentation-deck.md` § the MCP bridge). Carried as CAP-5 of the owning Spec ("the Design tier stops drifting") and as its open questions 8 and 10-11.

  scope-added: 2026-09-14 — **the `Track` qualification's Design half lands here.** The operator ruled that `Track` is written out in full wherever either sense appears — *evidence Track* (the Hub's durable run record) and *planning track* (a BMAD lane) — recorded as a Charter amendment. The 20 legacy intake-spec header rows in `docs/specs/` were qualified to `| Planning track |` in the same pass. **The deck could not be**: `presentations/agentic-sdlc/README.md:82` states `fragments/*.html` are *generated* from the prototype, and `project/*.dc.html` is a byte-pull from Claude Design — so editing either in the repo would be overwritten by the next extract AND would manufacture exactly the Design→repo drift the Charter's 2026-08-01 amendment exists to prevent. The deck's "Three tracks, sized to the work" slide has to change **in Design first**, then be pulled. That makes it the same remediation as this entry's existing content (four retired BMAD skill names, the retired Paige persona, and a local pull already 13.5 KB behind), so it is folded in rather than tracked separately — one Design-side pass closes all of it. The two dated `src/marp/*-2026-0*.md` snapshots are deliberately excluded: historical prose keeps its original names.

  progress: 2026-09-14 (later, Design reachable) — **(c) closed, (b) mostly closed by a pull; (a) and `Track` still Design-side.** Operator ruled *pull only* — no Design-side edits this pass. Pulled byte-exact from project `f58c0f17` (`render_preview` → curl → harness strip; every byte count verified against `list_files`): `Agentic SDLC.dc.html` 193,114 → 206,638 B (the 2026-09-09 v6.12 refresh that Design's own `github.md` records: AiDD rebrand, skills 14 → 8 with the v6.12 names, Paige retired, `bmad-loop`/`bmad-spec`/`bmad-ux` added, six modules, a new *Workflow matrix* slide — 50 → 51 sections), plus both Lexicon posters (their hard-coded Dream/Spec counts dropped for evergreen copy) and `github.md` verbatim; `extract` + `build` re-derived 51 fragments + manifest. **Verified against the pulled deck, not the prior entry's claim:** the four `bmad-`-prefixed retired names and all three `Paige` mentions are gone (0 hits each), but **four unprefixed `quick-dev`/`dev-auto` mentions survived** the Design-side rename (one body line on *Quick flow*, three speaker notes on *Quick flow* / *Workflow matrix*). Two further Design-side items surfaced: *Lexicon to PyForge*'s Guildhall line now names the retired `docs/dashboard/ → GitHub Pages` surface (the referent is the open Charter §7 question, so any wording is provisional — recorded, not corrected in a mirror), and `Agentic SDLC.marp.md` (a parallel Marp export, not derived from the prototype; Design etag unchanged since 2026-08-01) still carries the pre-6.11 names. **Remaining for one Design-side pass, then pull:** the *Scale-adaptive* title "Three tracks" → "Three **planning** tracks"; the four unprefixed retired names; the Guildhall line once §7 is ruled; the Marp export. (a) — the Design-tier practice vocabulary entering no repo artifact — is untouched by a pull and stays open. Herald's spec-surface key was deliberately **not** re-stamped for this pull (its memlog names every pulled and regenerated path literally, so nothing reads as drift; the key also carries herald's own recorded-but-unstamped 2026-09-13 drift-exclude and the Story 21.11 pull, which a stamp from this branch would launder — herald re-stamps once, as its own act).
### DW-VOCAB-2026-09-14-4: our nine Frames are authored against an unmerged, unlicensed frame-spec draft

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: The Company Frame and eight station Frames (steward Epic 53, Stories 53.2/53.5) carry `type: frame [0.3]`, `identifier:` and an Apache-2.0 `license:` IRI. All three are **v0.3-only fields**, from `openteams-ai/frame-spec` PR #28, which is **still open**. The released spec is v0.2.0, whose required set is exactly `type`/`name`/`description`/`visibility` and whose optional set is `version`/`scope`/`maintainer`/`inherits` — `identifier` and `license` do not exist in it, and `owner` never existed in any version (the field is `maintainer`, renamed from `author` by merged PR #20).
  evidence: Verified 2026-09-14. `GET /repos/openteams-ai/frame-spec/license` returns **404** and the repo's `license` field is `null` — there is **no LICENSE on `main` today**, so the spec text currently grants no rights; PR #28, which would add Apache-2.0 along with the v0.3 data model, was created 2026-09-07 and has not merged. PR #29 (reference validator) is open against #28's branch, not main. Separately, the advertised v0.2.0 release is not backed by any git tag or GitHub release. Story 53.5 accepted this knowingly ("we adjust when #28 / #29 merge"); this entry exists so the acceptance is tracked rather than remembered.
  location: docs/foundry/frames/
  severity: medium
  status: accepted-risk
  raised: 2026-09-14 — Owner: steward. Trigger to revisit: PR #28 merging (or closing). Our in-repo four-field preflight is correctly bound to v0.2's required set and does **not** depend on upstream's unlicensed `tools/validate_frames.py`, so the preflight itself is unaffected either way — the exposure is the frontmatter fields and the licence, not the gate.

  accepted: 2026-09-14 — **Operator ruled: adopt v0.3 now, knowingly.** *"we move forward by adopting frame-spec v0.3 — the PR will merge, and no point starting with an outdated version."* This entry's premise remains literally true (openteams-ai/frame-spec#28 is still open, branch `spec/v0.3-working-draft`, 38 commits, mergeable, no approval, and `main` still carries no LICENSE), so it is recorded as accepted risk rather than closed. What changed is the exposure, which was worse before the ruling than after: Story 53.5 had already stamped `type: frame [0.3]` on the nine Frames while their bodies stayed v0.2-shaped, so the estate conformed to **neither** version. Story 53.6 completed the adoption against the normative profile fetched from the PR head (`spec/profile/frame-core.csv` + `spec/frame-spec.md`), not a summary — qualified-ref `identifier`s, prose `name`s, sequence-shaped repeatables, `owner:` folded into the registered `maintainer`. The four fixes are stable properties of the v0.3 **Markdown encoding**, so a further draft revision cannot invalidate them; if #28's element registry does change before merge, the nine Frames and `frames.py` are re-run from the same profile CSV. De-register once #28 merges and the Apache-2.0 LICENSE lands.

  re-verified: 2026-09-14 (later) — **premise still holds; exposure unchanged; stays accepted-risk.** `openteams-ai/frame-spec#28` is `OPEN`, not draft, `reviewDecision: CHANGES_REQUESTED` (review by `jbouder`, 2026-09-10 — "in favor of the direction, with one substantive reservation" on the body taxonomy, plus concrete fixes the author replied to as done 2026-09-11, including "only `type` is required, the other three recommended"), last commit on the branch 2026-09-09, `updatedAt` 2026-09-14T14:34Z; `GET /repos/openteams-ai/frame-spec/license` still 404. The in-repo four-field preflight is bound to v0.2's required set, so upstream's move to "only `type` required" loosens, not breaks, our conformance; the four v0.3 Markdown-encoding properties Story 53.6 adopted are unaffected by a body-taxonomy revision. Trigger unchanged: #28 merging or closing.
  re-verified: 2026-09-16 — **premise still holds; exposure REDUCED; stays accepted-risk.** `openteams-ai/frame-spec#28` OPEN (39 commits, head `d7213c185e`, `MERGEABLE`, `reviewDecision` still `CHANGES_REQUESTED`, last review activity 09-11); `#29` OPEN (81 commits, head `4596579f71`, `spec/v0.3-validator` based on #28); `main` still has no LICENSE. What moved since 09-14: #28's same-day commit removed the draft's version number (documents omit the token; our `frame [0.3]` stamps corrected to bare `type: frame`, steward Story 64.1) and #29 shipped the reference validator, composition fixtures, `--self-check` and conformance profiles (§7 MUST — PyForge's published, Story 64.2). Exposure is lower because conformance is now *measured* rather than asserted: upstream's own `validate_frame.py` at `4596579f` passes our nine Frames 9/9 and accepts our profile (`pixi run -e pyforge-steward frame-upstream-check`, opt-in, read-only, pinned in `docs/foundry/frames/upstream-pin.yaml`). Trigger unchanged: #28/#29 merging or closing → re-pin to the release SHA and drop the "as if v0.3" posture. No commits or comments to openteams-ai.

### DW-VOCAB-2026-09-14-5: `epic-18` is a ledger row with no `## Epic 18` heading, so three stories render under Epic 17 and fleet-picture over-counts

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: `sprint-status-ledger.yaml` carries `epic-18: done` and `epic-18-retrospective: optional`, and `epics.md` carries `### Story 18.1/18.2/18.3` with matching ledger keys — but **no `## Epic 18:` heading**. The headings run 16, 17, 19. The three stories therefore render structurally under Epic 17, and `fleet-picture` (which counts epics from ledger keys) reports 57 epics for steward against 56 declared headings.
  evidence: Measured 2026-09-14 by parsing both files. Epic 18 is referenced by name throughout the FR mapping prose (`epics.md:1440-1456`, "canopy:FR-1: Epic 18 — chrome package", FR-2, FR-3, FR-14, FR-15), so the epic is real and its heading was simply never written. Invisible to `chain-completeness` INV-B by construction — see DW-CHAIN-COMPLETENESS-7.
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  severity: low
  status: closed
  raised: 2026-09-14 — Owner: steward. Data fix (write the missing heading over the existing three stories); tracked separately from the detector gap so neither blocks the other.
  closed: 2026-09-14 — Fixed, and the diagnosis above was **wrong about the cause**: Epic 18's heading was not missing, it was **mis-levelled**. `### Epic 18: Chrome and the trusted client` sat at H3 (line 1563) as the body heading, with an identically-titled summary-list entry at line 1503. Promoted the body heading to `##`; the summary entry is untouched. Verified `count == 1` for the body form and `== 2` overall before editing, so the promotion could not land on the summary row. The observable symptoms the entry describes were all real — headings ran 16, 17, 19; the three stories rendered under Epic 17; `fleet-picture` reported 57 against 56 — an H3 is invisible to every `^## Epic` parser in the estate, so a mis-levelled heading and an absent one are indistinguishable from the outside. Now caught by construction: doctor's DW-CHAIN-COMPLETENESS-7 landed the INV-B epic arm the same day, which compares `^##\s+Epic\s+(\d+)` headings against `epic-N` keys in both directions.

### DW-VOCAB-2026-09-14-7: `docs/dreams/README.md`'s "36 backlog stories" example is three weeks stale — every one of those stories is `done`

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: `docs/dreams/README.md:93-96` teaches the rule *"Status is NOT a proxy for work remaining, in either direction — the ledger is"* using two examples. The second reads: *"the largest single block of unbuilt work in the fleet — marshal's E7–E12, **36 backlog stories** — sits under `genesis-installer`."* That block is no longer unbuilt. The **rule is correct and should stand**; only the example is stale.
  evidence: Measured 2026-09-14 directly against the live tracked ledger (the very artifact the passage tells the reader to trust): marshal's E7–E12 hold **37 story rows, all `done`** — zero `backlog`, zero `in-progress`. They landed between 2026-08-10 (`6115ce7669`, Story 7-1) and 2026-08-23 (`52fbe2fac3`, Story 12-6, PR #654); the 37th (`10-8-manifest-declared-writable-artifacts…`) was added after the epics merge. Found during the delivered-Spec decomposition sweep while surveying `spec-genesis-installer-name-retirement`, whose own scope touched E7–E12 **only as documents to merge and renumber, never as work to build** — so nothing in that Spec is contradicted by this; the README simply was not updated when the stories shipped.
  location: docs/dreams/README.md:94
  severity: low
  status: closed
  raised: 2026-09-14 — Owner: steward. Fix is to re-point the example at a block that is genuinely unbuilt today (or state the figure as an as-of-date), **not** to weaken the rule it illustrates. Note the irony worth preserving in the rewrite: the passage's own closing advice — *"read `sprint-status-ledger.yaml`"* — is exactly what falsifies its example.

  closed: 2026-09-14 — Re-measured rather than softened, per this entry's own instruction not to weaken the rule it illustrates. marshal's E7–E12 is now **37 of 37 done** (0 backlog), so the "36 backlog stories" example was fully spent. Rewritten to use the resolution as the sharper evidence: `genesis-installer` read `archived` while that block went from all-unbuilt to all-shipped underneath it, so the status was useless in **both** directions over time — a stronger version of the original point, not a retreat from it. Today's real figures are cited as an as-of-date aside: steward's Epic 44 (8 blocked + 3 backlog) and herald's Epic 21 (10 backlog), both under Dreams reading `specified`, which is correct and still says nothing about what is left.
### DW-VOCAB-2026-09-14-8: `2` means FAIL to a doctor source and "could-not-run" to the aggregator, and CLAUDE.md taught the wrong one

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: Four exit-code domains are live at once. `pyforge.doctor.verdict` is frozen at `{0, 2, 130}` where **2 = FAIL** and `1` does not exist; `scripts/detectors.py` uses `{0, 1, 2}` where **2 = could-not-run**; `pyforge.warden.verdict` uses `{0, 1, 2, 130}`; `pyforge.marshal.core.verdict` invents `{0, 1, 2, 3, 4, 130}` with `gate-failed = 3`. `CLAUDE.md` stated the aggregator's domain as if it were universal, while the same file tells the reader to run `bmad-drift-check` / `story-status-check` / `spec-surface-check` / `capability-effect-check`, all of which dispatch through `python -m pyforge.doctor.sources` and therefore project through DOCTOR's domain. So a genuine FAIL from any of those reads, under the documented mapping, as "the check couldn't run" — the precise false-green class `scripts/detectors.py:39-41` exists to prevent, inverted.
  evidence: Confirmed live 2026-09-14 **by walking into it**: this session ran `python -m pyforge.doctor.sources chain-completeness`, received exit 2 alongside one FAIL finding, and reported it to the operator as "could-not-run, not a pass — a false green signal", which was wrong. The error was caught only by then reading `doctor/verdict.py:45-57` directly. A detector that misleads its own maintainer inside one session is not a theoretical defect. Doctor's subset of warden's domain IS deliberate and documented (`doctor/verdict.py:4-7` — it omits warden's policy rung `1` because Doctor reports operability, not policy); the collision with the aggregator's `2` is not documented anywhere.
  location: CLAUDE.md (§ Health / status), scripts/detectors.py, src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py
  severity: high
  status: partially-fixed
  raised: 2026-09-14 — Owner: steward (vocabulary), doctor (the domains). **The documentation half is fixed**: CLAUDE.md now states both domains and warns that `2` inverts between them. **The design half is open** — four lattices, three of which invented their own numbers, with only the Doctor↔Warden relationship documented as intentional and Marshal's recorded in its own docstring as "a recorded assumption, not architecture-dictated". A single declared exit-code vocabulary is CAP-2's natural scope.

  progress: 2026-09-14 (second pass) — the **rot risk is now closed**, which was the actionable half. `tests/scripts/test_exit_code_domains_are_declared.py` pins all four domains against `docs/reference/judgement-vocabulary.md`, which is now their declared home: doctor's `{0, 2, 130}` with `warn` fixed at 0 and `1` provably absent; warden's `{0, 1, 2, 130}` retaining the policy rung doctor's docstring justifies omitting; and the aggregator's `2`-from-`unknown`. The aggregator assertions read the **code**, not its prose — a comment-matching test would pass while the projection underneath it changed. The glossary assertions pin that the inversion is stated and that doctor's and warden's domains appear side by side, since that adjacency is what makes the subset relationship legible to a reader. So changing any domain without updating the declaration now fails a test instead of silently re-opening the 2026-09-14 misread.
    **Still open: the unification itself** — one declared exit-code vocabulary the four surfaces read, rather than four hand-maintained constants. That is a cross-station code change (doctor, warden, marshal, `scripts/detectors.py`) and needs its own Dream. Note the four are not arbitrarily divergent: doctor's is a documented subset of warden's, and marshal's own docstring calls its numbering "a recorded assumption, not architecture-dictated". Only the aggregator's `2` genuinely conflicts, and it is the one surface with no lattice at all.

  ruled: 2026-09-14 (later) — **"needs its own Dream" was the wrong framing; the operator folded the unification into `spec-vocabulary-one-name-one-job` CAP-2.** That Dream already owns "one name, one job" for the estate's vocabulary and CAP-2 is literally "one declared vocabulary source the detectors read" — the exit-code lattices are its second vocabulary, not a new chain. SPEC.md CAP-2 carries a dated scope-widening block naming all four surfaces and the constraints above (Doctor⊂Warden stays a declared subset); the Story is minted when that Spec flips to `ready` (it is `draft` with seven operator questions open). Status stays `partially-fixed` — nothing in code changed this pass — but the entry's remedy is now a bound CAP, not an unowned wish.
### DW-VOCAB-2026-09-14-9: `Guard`/`Gate` carry three senses and the Charter ruled on the neighbouring collision but not this one

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: Three live senses. (1) Intelligence Hub: *"Guards check. Gates decide."* — shipped as `docs/foundry/guards/README.md` + `steward/guards.py`. (2) Ours: `gate_mode` as a run-level approval policy, ~30 `*-check` detectors, and marshal's own `Verdict.GATE_FAILED` rung. (3) Upstream BMAD: `PASS`/`CONCERNS`/`FAIL` as a readiness-gate verdict, live in eight implementation-readiness reports across six stations. The Charter names the Cogs/Smith collision explicitly at `pyforge-charter.md:615` and `:622-623` — and gives Guards/Gates a single cross-walk cell at `:617` with no collision marker at all. The asymmetry looks deliberate but is explained nowhere.
  evidence: Measured 2026-09-14 across the estate. Worse than an unnamed overload: the only two rulings that DO exist contradict each other — `docs/dreams/intelligence-hub.md:757` says *"Gates are the verdict plus operator confirmation"*, while `spec-pyforge-marshal/glossary.md:52-55` says a Gate is *"a checkpoint that must pass before a story progresses. Three kinds: an approval gate, a verify gate, and a scope check"*, none of which is "the verdict plus operator confirmation". A reader cannot determine which is binding.
  location: docs/dreams/pyforge-charter.md:617, docs/dreams/intelligence-hub.md:757, _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/glossary.md:52-66
  severity: medium
  status: closed
  raised: 2026-09-14 — Owner: steward. This is exactly `spec-vocabulary-one-name-one-job` CAP-4 ("the unnamed collisions get rulings"), which is still `draft`. A ruling is a Charter amendment with a Realization-log entry, never an edit — and it must also settle `Track` (Hub evidence record vs BMAD planning lane), which has the same shape and is equally unruled.
  closed: 2026-09-14 — Ruled by the same Charter amendment that closed `DW-VOCAB-2026-09-14-10`: `pyforge-charter.md` § The Lexicon → `### Gate has three senses; verdict has one`, with a Realization-log entry. The three senses are named and scoped (Warden's PR verdict / the harness CI gate / upstream BMAD's readiness gate), authors must say which, and `verdict` is additionally reserved as the narrow word. The contradiction this entry flagged — `intelligence-hub.md:757` ("Gates are the verdict plus operator confirmation") against `spec-pyforge-marshal/glossary.md:52-55` ("a checkpoint … three kinds") — is resolved by the amendment being Tier 0: both downstream texts now read as sense-scoped restatements rather than rival definitions. **`Track` is NOT closed by this** and remains CAP-4's outstanding half; it was carried deliberately rather than bundled, because its two senses sit in a public-facing deck and 24 legacy intake-spec headers, a different remediation shape from a code-adjacent word.

### DW-VOCAB-2026-09-14-10: nothing reconciles "Warden is the sole PR verdict" with "detectors-ci fails CI"

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: The Charter's rule is *"Warden stays the sole PR verdict"* (`pyforge-charter.md:617`) under the doctrine *"the hand that builds is never the gate that judges"* (`:451-454`). Yet `detectors-ci` genuinely runs in CI and genuinely fails it, and several non-Warden surfaces say so in their own words: `scripts/detectors.py:212` (*"the FAIL half … is what actually gates"*), `sources/platform_policy.py:41-43` (*"a REAL, ACTIONABLE gate"*), `pixi.toml:1077` (*"install it … to make this a real gate"*), `pyforge-marshal/README.md:31` (*"Read-only conformance report (CI gate)"*), `pixi.toml:1563` (Atlas, *"CI gate (exit 2 on violations)"*). The Charter's harness clause (`:668-673`, "CI verify gates" are the unit of governance) arguably covers this — but no document connects the two, so each surface decides for itself whether calling itself a gate is legal.
  evidence: Measured 2026-09-14. The tension is not merely verbal: marshal publishes a second `verdict` lattice with a dedicated `GATE_FAILED` rung (`marshal/core/gate.py:41-42`) in the station the Charter explicitly bars from grading its own work (`pyforge-charter.md:269` assigns Marshal's verdict to Doctor). Contrast the surfaces that get it right and say so — `pyforge-warden/README.md:135-138` mechanically raises `SecondVerdictError`, and `steward/frames.py:315` / `docs/foundry/frames/README.md:58` both state "Not a detector; Warden stays the sole PR verdict."
  location: docs/dreams/pyforge-charter.md:451-454 and :617, scripts/detectors.py:212, src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/platform_policy.py:41-43, src/shared/packages/pyforge-marshal/README.md:31
  severity: medium
  status: closed
  raised: 2026-09-14 — Owner: steward (the ruling), then each named station (its own wording). Deliberately NOT fixed by editing the five call sites: rewording them would hide an unresolved doctrine question behind tidier prose. The ruling decides whether "gate" is reserved for the PR verdict (and every CI-failing check needs a different word) or whether "PR verdict" is the narrow reserved term and CI checks may gate freely.
  closed: 2026-09-14 — **Operator ruled the second option, plus a reservation.** Landed as a Charter amendment, `docs/dreams/pyforge-charter.md` § The Lexicon → `### Gate has three senses; verdict has one`, with a Realization-log entry (Tier 0 changes by recorded amendment, never a silent edit). The ruling: `Gate` carries three legitimate senses — Warden's **PR verdict**, the **harness CI gate** (`detectors-ci`, `*-check` tasks, `gate_mode`, a loop's verify gate), and upstream BMAD's **readiness gate** (`PASS`/`CONCERNS`/`FAIL`, not ours to redefine) — named and scoped in the same shape the Charter used for Cogs/Smith, with authors required to say which. Additionally **`verdict` is reserved**: a station publishes it, only about work it did not do, and only Warden publishes the PR one.
    The five flagged surfaces turn out **not to have been in violation**. § *Execution Doctrine* had already placed CI verify gates in the **harness** — the unit of governance — rather than among station verdicts; governance gates, stations judge. That reading was simply never written down, so `platform_policy.py`, `pixi.toml`, `scripts/detectors.py`, `pyforge-marshal/README.md` and an Atlas task each resolved the ambiguity alone and each concluded, in its own prose, that it was breaking a rule it was not breaking. **No code was changed** — which was the point of not rewording them in the first place.
    Two things deliberately NOT closed here: **`Track`** stays unruled (`spec-vocabulary-one-name-one-job` CAP-4), and **marshal's own six-rung verdict lattice with its `GATE_FAILED` rung** is a question of FACT rather than vocabulary — does that value ever leave the loop and reach a PR? — so the amendment explicitly does not pre-judge it. Operator direction: investigate before deciding.

### DW-VOCAB-2026-09-14-11: `check` does four jobs, and `detector`/`check`/`preflight` are nowhere distinguished

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: `check` is simultaneously (1) a `Finding` field naming which check produced it, (2) a marshal CLI verb over the detector registry, (3) one of marshal's three gate kinds (*"a scope check"*), and (4) the filename suffix of ~30 `*-check` pixi tasks that are detectors. `preflight` is separately (1) the Frame validator, (2) a marshal loop-home step, (3) a BigQuery cost dry-run, and (4) Doctor's own tagline for its `check` verb. No artifact anywhere in the estate contrasts detector vs check vs preflight; the only two statements are negative (*"Not a detector"*, twice), defining by exclusion and never saying what the thing is instead. `advisory` is likewise defined only as "not a gate" in all four of its definition sites, and `lens` — load-bearing in `bmad-review`, the Guard library and warden's epics — is defined nowhere at all.
  evidence: Measured 2026-09-14. This is the Lexicon's own rule failing on the estate's most-used operational nouns: *"Every noun does exactly one job; every job has exactly one noun"* (`pyforge-charter.md:596-599`). The Lexicon's seven nouns satisfy it; the words the fleet actually types every day do not.
  location: docs/dreams/pyforge-charter.md:596-599, src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py, scripts/detectors.py:23-32
  severity: low
  status: closed
  raised: 2026-09-14 — Owner: steward. Folds into CAP-1/CAP-3. Cheapest real fix is a glossary that states each positively (what a detector IS, what advisory obliges a reader to do) rather than four more "not a gate" disclaimers.

  closed: 2026-09-14 — Closed by writing the glossary this entry asked for: `docs/reference/judgement-vocabulary.md`, linked from the Charter's § The Lexicon and indexed in `docs/MAP.md`. Each word is now stated **positively**, which was the actual defect — `advisory` had four definition sites and all four said only "not a gate", and `lens` had none at all. The positive definitions are the substance: **advisory** means *the decision stays with a human*, not *unimportant*; a **detector** reports and declines to decide; a **preflight** runs before the thing it guards and its failure means "do not proceed" rather than "this is broken"; a **lens** is a named point of view so two passes over one diff look for different things. **`check`'s four jobs were deliberately NOT collapsed** — the `Finding.check` field, the `marshal check` verb, marshal's scope-check gate kind and the `*-check` filename suffix are load-bearing in four different layers, and renaming any of them would cost more than the ambiguity does; the page says "say which" instead, matching the Gate ruling's shape. The page also carries the exit-code table, including the `2` inversion between a doctor source (FAIL) and the aggregator (could-not-run) that caused a real misread this session, and the never-read-a-detector-through-a-pipe rule. It rules nothing: `Gate`, `Track` and `kernel` were ruled by Charter amendment and the page restates them for a reader who needs them at hand. Adding a word there is documentation; changing what one means stays a Charter amendment.
### DW-VOCAB-2026-09-14-12: six structural nouns are overloaded and nothing in the estate acknowledges them

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: A fourth sweep (2026-09-14) measured the ARCHITECTURAL nouns, which `spec-vocabulary-one-name-one-job` does not cover — its scope is status vocabularies and identifier shapes. Six are UNRULED, meaning the overload exists and no document names it: **Surface** (5 senses — a Spec's `surface:` frontmatter, a story's `**Surface:**` field, marshal's *frozen surface*, an API surface, and "shared/estate surface"), **Layer** (7 numbered stacks, including two rival config-precedence chains that both live in `_bmad-output/` and never cite each other), **estate / fleet / foundry** (3 senses each), **Tier** beyond the one named collision (three further systems: `five_tier.py`'s station shape, model/cost tiering, test tiers), **Plane** (8 senses; two ADs each claim "one plane" for a *different* plane), and **Spine** (2 senses, and never defined anywhere at all — the word is inherited silently from `bmad-architecture` as a filename).
  evidence: Surface ranks first on blast radius: 142 `SPEC.md` carry `surface:`, 422 story rows carry `**Surface:**`, `scripts/spec_surface_check.py` gates on the first sense and `marshal/core/gate.py:528` on the third — and `marshal/epics.md:496` uses senses 2 and 3 in one sentence with no qualifier. Marshal's `architecture.md:823-827` § 10.4 is the estate's only terms-of-art list; it rules the Tier collision ("the collision is historical, so always say which") but omits Surface, while marshal owns two of its five senses. `island` is the counter-example worth copying: one definition (`ARCHITECTURE-SPINE.md:604-608`), one owner, three enforcing ADs, a CI `paths:` rule and a test.
  location: docs/dreams/pyforge-charter.md, _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture.md:823-827, scripts/spec_surface_check.py
  severity: medium
  status: open
  raised: 2026-09-14 — Owner: steward. Needs its own Dream or an explicit widening of `vocabulary-one-name-one-job`, whose § The shapes covers identifiers and whose CAP-4 covers Track/Guard/Gate — none of these six. The `island` pattern (define once, name an owner, enforce with an AD) is the shape to hold the rest to.

### DW-VOCAB-2026-09-14-13: "kernel" was retired and is now MORE overloaded than before the ban

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: The Charter bans one sense at `pyforge-charter.md:387-389` — *"Never call the Spec a 'kernel' — that is `bmad-spec`'s internal jargon … and it demotes the most load-bearing artifact in the ecosystem to a tool detail"* — and then uses the banned form itself 440 lines later at `:827` (*"this Dream's own Spec kernel"*). `_bmad-output/EXEMPLAR-STANDARD.md:447-465` builds an entire named rule on the banned sense (**"## The kernel/companion rule"**, 16 occurrences), and `PROJECTS.md:64` plus `CHARTER-ALIGNMENT-PLAN.md` follow it. Meanwhile two NEW senses arrived after the ban and were never contemplated by it: "kernel spec" meaning a station's broad umbrella Spec (`docs/dreams/spec-surface-overlap-tolerance.md`, and the branch name `maintenance/kernel-spec-surface-overlap-2026-09-12`), and "foundry kernel" meaning the regenerated core of B (`docs/dreams/foundry-regenerate-not-fold.md`, steward Epic 54). Plus "governance kernel" at `guild-roster.json:17`.
  evidence: Measured 2026-09-14 — ~120 occurrences across ~40 in-scope files, in four distinct senses. A retirement that the retiring document violates, that a Tier-2 standard builds a named rule on, and that two later efforts extended in new directions, is not a retirement.
  location: docs/dreams/pyforge-charter.md:387-389 and :827, _bmad-output/EXEMPLAR-STANDARD.md:447-465
  severity: medium
  status: closed
  raised: 2026-09-14 — Owner: steward. Either the ban is real (and EXEMPLAR-STANDARD's rule is renamed, and the Charter fixes its own line) or it is narrowed to "never call **the Spec** a kernel, but `kernel` is legal for an umbrella-vs-narrow relationship and for B's core". Both are defensible; the current state — banned and load-bearing at once — is not.

  closed: 2026-09-14 — **Operator narrowed the ban to its one real target.** Charter § Branding now reads *"Never call **the Spec** a 'kernel'"*, with the other three senses blessed by name: a station's broad **umbrella spec** as against its narrow story specs (`spec-surface-overlap-tolerance`'s "kernel spec"), the regenerated core of B (Epic 54's "foundry kernel"), and `guild-roster.json`'s "governance kernel" — on the same say-which-sense footing as the Gate ruling the same day. Landed as a Tier-0 amendment with a Realization-log entry. **No file renamed:** `EXEMPLAR-STANDARD.md`'s named "kernel/companion rule" stands, and this Charter's own Realization-log use of "Spec kernel" stands, because neither was ever calling *the Spec* a kernel — they use the umbrella and artifact senses. The reasoning recorded for posterity: a prohibition its own author violates 440 lines later, that a Tier-2 standard builds a named rule on, and that two later efforts extend in new directions is not a prohibition — it is a dead letter that quietly makes every reader wrong. Keeping the ban's real content while admitting practice is the honest resolution; enforcing it fully would have renamed a live standard's rule to protect a word upstream tooling uses for its own five-field shape anyway.
### DW-VOCAB-2026-09-14-14: "the station is the post, not the ___" forked, and two artifacts cite Charter §5 for the variant it does not contain

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: Charter §5 says *"the station is the post, not the **person**"* (`pyforge-charter.md:451`) — station ≠ Smith, the being can be swapped. A second, different ruling also lives in §5 at `:474-485` (*"Owning is becoming — at the planning tier … It does not rename the package"*) — planning home ≠ package identity. Those two rulings have collapsed into one memorable formula with a swappable last word: `docs/dreams/README.md:110` and `docs/dreams/intelligence-hub.md:841` say *"post, not the **product**"*, and `docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md:1519` plus `spec-pyforge-unifying-strategy/.memlog.md:6` **cite "Charter §5" for a sentence §5 does not contain**.
  evidence: Measured 2026-09-14. Both underlying rulings are correct and both are in §5, which is why this went unnoticed — it is a citation-integrity defect, not a semantic one. The public deck (`presentations/agentic-sdlc/…:740`) and the Charter agree on "person"; the Dream README and four in-flight memlogs drifted to "product". Related: station / post / office are three nouns for one job inside the very document whose Spec says *"every job has exactly one noun … never a synonym smuggled into prose"* (`docs/governance/spec-pyforge-charter/SPEC.md:77-79`).
  location: docs/dreams/pyforge-charter.md:451 and :474-485, docs/dreams/README.md:110, docs/dreams/intelligence-hub.md:841
  severity: low
  status: closed
  raised: 2026-09-14 — Owner: steward. Fix is to give the second ruling its own formula rather than overloading the first, and correct the two miscitations. Memlogs are append-only, so the memlog one is corrected by a later entry, never an edit.

  closed: 2026-09-14 — All four sites fixed. The fork existed because Charter §5 holds **two** rulings and one memorable formula had absorbed both: *"the station is the post, not the **person**"* (`:451` — a Smith is swappable at a station, which is what makes model tiering safe) and the 2026-07-28 amendment *"Owning is becoming — at the planning tier … It does not rename the package"* (`:474-485`). The second now gets its own words — **"the planning home is not the package name"** — so it stops borrowing the first's. `docs/dreams/README.md:110` carried a second, separate error nobody had flagged: it still read *"Owning is **not** becoming"*, the wording the 2026-07-28 amendment superseded, so it was contradicting Tier 0 outright. Corrected there and at `docs/dreams/intelligence-hub.md:841`. The two **miscitations** were repointed rather than reworded, a citation being a pointer: `docs/dreams/archive/…-topology.md:1519` in place, and `spec-pyforge-unifying-strategy/.memlog.md` by appended correction, memlogs being append-only. The ownership decision both miscitations record — steward over herald — is correct and untouched; only the citation was wrong.
### DW-VOCAB-2026-09-14-15: chain-currency reports 9 findings across 8 stations — deferred to a dedicated reconciler pass

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: `chain_currency_sweep_check` reports 9 currency-checkpoint failures spanning all eight stations — 8 × `chain-audit-checkpoint-staleness` plus 1 × `chain-audit-checkpoint-coherence` (warden). Clearing them requires the full reconciler sweep documented in `CHAIN-CURRENCY-RUNBOOK.md`, which is a per-station pass over each chain's artifacts, not a mechanical fix.
  evidence: Observed live 2026-09-14 in a full `pixi run -e local-recipes detectors` run, alongside the other reds cleared that day (governance-currency, deferred-work, chain-completeness, ad-citation, loop-stall, spec-surface). Deliberately NOT attempted in the same session: the chain-currency cost is stages, not diff size — a prior one-line edit cascaded into 9 reconciles and 6 retros — so folding it into a session already carrying a Frame-spec adoption, a detector arm and a 15-spec surface reconcile would have produced a poor pass at both.
  location: scripts/chain_currency_sweep_check.py, _bmad-output/projects/pyforge-doctor/CHAIN-CURRENCY-RUNBOOK.md
  severity: medium
  status: closed
  raised: 2026-09-14 — Owner: each station, sequenced by the runbook. Operator direction the same day: defer to a dedicated next session. This entry exists so the deferral is tracked rather than forgotten — it is the only red left open from that session's sweep.
  note: 2026-09-14 (the dedicated reconciler pass ran) — **8 of 9 cleared; 1 residual, deliberately not stamped over.** `chain_currency_sweep_check` now exits 1 with a single finding: `pyforge-warden` `chain-audit-checkpoint-coherence`. All eight `staleness` findings are cleared by genuine per-station cascades (atlas: a real 2026-08-26→09-14 retro; the other seven: PRD + architecture-spine reconciliations, plus epics validation notes for doctor/mason/warden where `arch→epics` would have fired next; steward additionally a brief reconciliation for its `research→brief` edge). **The residual is operator-owned and cannot be cleared by an agent:** `overtaken` is non-empty `open_questions:` on `spec-pyforge-warden`, and the runbook's own remedy for `overtaken` is "resolve the spec's residual open_questions with the operator." The three questions are (1) is warden v1 *released* or *story-complete* — the legacy v1 DoD still carries the CFE Rule-2 closeout retro and the internal JFrog publish unchecked; (2) does `docs/specs/pyforge-warden.md` get re-stamped shipped-and-superseded or frozen as a historical record; (3) what promotes provenance and maintenance out of vision, and until then does the product describe itself as four-axis or six-axis. Answering them unilaterally would be the "stamp without a genuine reconcile" the runbook forbids. Full record: `_bmad-output/projects/pyforge-doctor/CHAIN-CURRENCY-RUNBOOK.md` § Worked Examples, run 2026-09-14; the per-station detail is in each station's own § Currency reconciliation — 2026-09-14. Also corrected in this entry: `location:` cited the runbook under `pyforge-marshal`; it lives under `pyforge-doctor`.

  closed: 2026-09-14 — **Fully cleared: 9 findings across 8 stations → 0.** The last one, warden's `chain-audit-checkpoint-coherence`, was `overtaken` by three operator-owned questions in `spec-pyforge-warden`'s `open_questions:`; the runbook's remedy for `overtaken` is explicitly "resolve with the operator", so it could not be closed by inference. Operator ruled all three this date: (1) **v1 is story-complete, not released** — all 31 stories merged but the release-level DoD items (the CFE Rule-2 closeout retro, the internal JFrog publish behind the engine version-range gate) are genuinely unticked, and were left unticked rather than redefined, since retroactively moving "done" to match what shipped is what `docs/dreams/README.md:90-98` warns against; (2) **the legacy Tier-1 spec is re-stamped shipped and superseded** — its premise turned out stale, the file having been corrected to `shipped` on 2026-09-03, so only the `superseded_by:` pointer was ever missing, and its Goals prose is kept as written because its own § Release buckets already records D12's move of the former v1.1 content into v1; (3) **the product stays six-axis with provenance and maintenance annotated unbuilt**, declining the four-axis alternative because it would have made the docs and the Charter disagree about what Warden is — and that annotation was already correct at `pyforge-charter.md:182,192` and `spec-pyforge-warden/SPEC.md:112`, so no artifact needed changing. `chain_currency_sweep_check` now exits 0: all 8 station spines current.

### DW-VOCAB-2026-09-14-16: the judge advises while the judged station's own gate blocks — §5's force ratio is inverted

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/SPEC.md`
  summary: `.github/workflows/detectors.yml:119` carries `continue-on-error: true` — *"ADVISORY, NOT BLOCKING — operator decision 2026-07-31"* — so Doctor's verdict on Marshal's row, which Charter §6 exists to make independent, cannot red a PR. Meanwhile `coverage-gates.yml` has no `continue-on-error` anywhere, so the gate shipping inside marshal's own package **does** red marshal's PRs. The judge annotates; the judged station's own gate blocks. Charter §5 assumes the opposite ordering — *"Mason's build does not pass because Mason says so; it passes when Warden's gate says so."*
  evidence: Measured 2026-09-14 alongside `DW-COVERAGE-GATE-INDEPENDENCE-1`. Both halves are individually deliberate and defensible — the advisory sweep was an explicit operator decision to avoid false-green brittleness, with one scoped exception already carved out (`cfe_rebuild_guard_check`) — which is precisely why the inversion went unnoticed: nobody chose it, it emerged from two independently sound decisions meeting.
  location: .github/workflows/detectors.yml:27-34 and :119, .github/workflows/coverage-gates.yml
  severity: low
  status: closed
  raised: 2026-09-14 — Owner: steward (fleet CI policy). Operator direction the same day: **track, decide separately** — making Doctor's marshal-row findings blocking would reverse the 2026-07-31 decision fleet-wide, which is too large to ride along with the coverage-gate fix. The narrower option, if it is ever taken, is a scoped carve-out for `marshal-durability` alone, mirroring the `cfe_rebuild_guard_check` exception that already exists.

  closed: 2026-09-14 (later) — **Operator took the narrow option: a scoped carve-out, landed.** `detectors.yml` now has a second dedicated blocking step beside `cfe_rebuild_guard_check` — *"Doctor's durability verdict on Marshal (blocking — ruling 2026-09-14)"* — running `python -m pyforge.doctor.sources ledger-regression` after the advisory sweep and letting its exit code stand (Doctor's frozen domain `{0, 2, 130}`: `2` is a real regression, not could-not-run). **One correction to the entry's own wording:** it named `marshal-durability`, but that source compares the *working tree* against `HEAD` — on a runner those are one commit, so it can observe nothing; `ledger-regression` is the same durability verdict (the 2026-08-08 96-`done`-markers incident class) in the committed-range form its own docstring says was designed for CI, made resolvable by the workflow's `fetch-depth: 0`. Verified green before wiring (`exit=0`, "no tracked ledger un-finishes a story between f391d6a43d and HEAD") so the first blocking run cannot red an unrelated PR; the local mirror already existed — `detectors-ci` (hence `pr-preflight`) exits 1 on any finding, stricter than CI. Scope is exactly one row: `ledger-direction` and every other Marshal-row source stay advisory; widening is a further ruling. Recorded in the Charter's Realization log (with the §5 amendment of the same date) and the workflow's header comment ("TWO SCOPED EXCEPTIONS"); the coverage-gate Dream/Spec non-goal now reads "fleet-wide".

### DW-FU-65-1: The HTMX backlog view and the `WorkPassport` admin ship as a library (AD-1 — the pipeline, not the routing): no URLconf under `src/` registers `sprint_backlog_view` and no host `INSTALLED_APPS` lists the dashboard app, so the view and the admin are reachable only from a host project that wires them. First consumer story wires one host or records why none should.

- source_spec: `planning-artifacts/specs/spec-65-1-reusable-pluggable-feature-flagged-estate-sprint-ledger-query-module-and-bmad-skill.md`
  summary: The HTMX backlog view and the `WorkPassport` admin ship as a library (AD-1 — the pipeline, not the routing): no URLconf under `src/` registers `sprint_backlog_view` and no host `INSTALLED_APPS` lists the dashboard app, so the view and the admin are reachable only from a host project that wires them. First consumer story wires one host or records why none should.
  evidence: `views.py` ships a view factory only; `routing.py` / `asgi.py` carry websocket patterns; `grep -rn build_navigation_view src/` finds no URLconf reference (implementer report, PR #1507 review 2026-09-19).
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/views_htmx.py
  origin: spec-deferred dfdcdcda9e88 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-65-1-2: Every HTMX render re-parses all eight stations' `epics.md` + ledgers (no caching, no mtime check); fine for a handful of operators, a hot loop for a dashboard polling on a timer. A `pre_query` hook or a source-level mtime cache is the shape when it matters.

- source_spec: `planning-artifacts/specs/spec-65-1-reusable-pluggable-feature-flagged-estate-sprint-ledger-query-module-and-bmad-skill.md`
  summary: Every HTMX render re-parses all eight stations' `epics.md` + ledgers (no caching, no mtime check); fine for a handful of operators, a hot loop for a dashboard polling on a timer. A `pre_query` hook or a source-level mtime cache is the shape when it matters.
  evidence: `sprint_backlog_view` builds a fresh `SprintLedgerQueryEngine()` per request and `TrackedLedgerSource.load_station` reads the files every call.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/views_htmx.py
  origin: spec-deferred 225ebde45408 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-65-1-3: `LedgerQueryHook`'s three default no-op methods trip ruff `B024`/`B027` (abstract base with no abstract methods); steward has no ruff lane or config, so nothing reds, but the first station-wide lint pass will.

- source_spec: `planning-artifacts/specs/spec-65-1-reusable-pluggable-feature-flagged-estate-sprint-ledger-query-module-and-bmad-skill.md`
  summary: `LedgerQueryHook`'s three default no-op methods trip ruff `B024`/`B027` (abstract base with no abstract methods); steward has no ruff lane or config, so nothing reds, but the first station-wide lint pass will.
  evidence: `ruff check --select B024,B027 src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py` reports both; `F`/`E9` are clean.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py
  origin: spec-deferred 7932f56631b7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-OPS-2026-09-20-1: `eval-quality` is pinned only in the `local-recipes` env, so `test_wired_column_agrees_with_live_pipeline_truth_for_every_row` fails in any fresh worktree that installs station envs only

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md`
  summary: `pixi.toml` pins `bmad-eval-quality` (`eval-quality` CLI) in the `local-recipes` feature only (`pixi.toml:836`, `:1916`); `suite.py:705-718` cannot see it via `shutil.which` under `-e pyforge-steward` and falls back to `<repo>/.pixi/envs/local-recipes/bin/eval-quality`, which exists on the operator's primary checkout (10 GB env) and not in a fresh worktree, so the adoption register's `Wired` column disagrees with the live probe there. Fix: pin `bmad-eval-quality` in the `pyforge-steward` feature (steward wields it), regenerate the lock, run `pyforge-station-tests` (shared surface); then drop the `local-recipes` fallback or keep it as a secondary probe.
  evidence: 2026-09-20 in `../local-recipes-wt-agents-md-mod` (station envs only): steward 1577 passed / 1 failed on that test; the same test passes on the main checkout at the same tree. Found on the fleet PR #1551's shared-surface run.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
  severity: low
  status: done
  verified: 2026-09-20 — resolved by steward Story 63.5 in the same PR (#1551): `bmad-eval-quality` pinned in `[feature.pyforge-steward.dependencies]`, lock re-solved, `test_wired_column_agrees_with_live_pipeline_truth_for_every_row` passes in a station-envs-only worktree (1578 passed). The `suite.py:714` fallback itself is Story 63.6's to remove.
  raised: 2026-09-20 — Owner: steward (suite adoption register, Story 45.1's pin). Not caused by #1551; recorded at shutdown rather than folded in (a `pixi.toml` dep change is its own lane).

### DW-OPS-2026-09-19-5: `.gitignore:740` is an unanchored `data/` pattern — it swallows every `data/` directory in the tree, including packaged JSON schemas that must ship (two `git add -f` so far); worktree hygiene pass pending for 17 merged sibling/agent worktrees

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md`
  summary: (a) `data/` at `.gitignore:740` ignores `src/shared/packages/pyforge-steward/src/pyforge/steward/data/*.schema.json` (`track.schema.json`, `sprint-ledger-query.schema.json` were force-added); a plain `git add -A` silently drops the next one. Anchor the rule (`/data/`) or add `!src/**/data/*.json`; line 902's own comment already warns about unanchored patterns. (b) Hygiene: `../local-recipes-wt-{agents-governance-enhancements,ci-fix-steward-doctor-live-baselines,hub-scribe-17-mint,ledger-flip-23-2-46-4,mason-cfe-surface-policy,pyforge-pages,sprint-ledger-query-module,steward-pyforge-guild-env}`, `../lr-pwb` and eight `.claude/worktrees/agent-*` are all merged (`ahead=0`); `lr-m50` / `lr-s59` are live dispatch clones and stay. Removal is operator work (agent sessions are classifier-blocked on `git worktree remove`; `pyforge steward workspace clean` is the sanctioned door for the steward-made ones).
  evidence: `git check-ignore -v src/shared/packages/pyforge-steward/src/pyforge/steward/data/sprint-ledger-query.schema.json` → `.gitignore:740:data/`; `git -C <wt> rev-list --count origin/main..HEAD` = 0 for each listed worktree (2026-09-19).
  location: .gitignore
  severity: low
  status: open
  raised: 2026-09-19 — Owner: steward (repo hygiene, scratch-worktree lifecycle). Operator-only for (b).

### DW-FU-60-1: The committed generated manifests bake recipe `version`/`description` (and the frame count) from inputs — `recipes/bmad-{builder,utility-skills,creative-intelligence-suite,method-test-architecture-enterprise}/recipe.yaml` and `docs/foundry/frames/**` — that never trigger the steward CI job, so a recipe-only PR leaves `main` with `manifest-drift` and `steward catalog check` red until the next steward PR runs `steward catalog render` and commits.

- source_spec: `planning-artifacts/specs/spec-60-1-the-catalog-config-names-backends-and-sources.md`
  summary: The committed generated manifests bake recipe `version`/`description` (and the frame count) from inputs — `recipes/bmad-{builder,utility-skills,creative-intelligence-suite,method-test-architecture-enterprise}/recipe.yaml` and `docs/foundry/frames/**` — that never trigger the steward CI job, so a recipe-only PR leaves `main` with `manifest-drift` and `steward catalog check` red until the next steward PR runs `steward catalog render` and commits.
  evidence: Verified by execution: with `read_recipe_version` returning `9.9.9` for `bmad-builder`, `CatalogEngine.drift()` on the committed tree goes from `[]` to `[("manifest-drift", ".claude-plugin/marketplace.json")]`; `.github/workflows/pyforge-station-tests.yml` `paths` lists `src/shared/packages/pyforge-*/**`, `pixi.toml`, `pixi.lock` and container files — neither `recipes/**` nor `docs/foundry/frames/**`; those four recipes bumped on 2026-08-21, 09-09, 09-11 and 09-12 as recipe-only PRs. Closure: add the four `recipes/bmad-*/**` paths and `docs/foundry/frames/**` to the steward trigger, or put `steward catalog render --check` into `detectors-ci`/`pr-preflight`; Story 60.3 (ship backends) needs a render gate before it can publish a snapshot anyway. Both edits are outside this story's surface.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py (WieldedSuiteSource.listings / CatalogEngine.drift); .github/workflows/pyforge-station-tests.yml
  origin: spec-deferred 0aa69350d691 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-60-1-2: The `test_track.py` `_SCHEMA` path fix (`_PKG.parents[1]` → `_PKG.parent`) is never executed in either CI lane: `test_schema_accepts_assembled_track` opens with `pytest.importorskip("jsonschema")` and `jsonschema` is not a `pyforge-steward` feature dependency, so the track-schema contract stays unpinned in CI exactly as before.

- source_spec: `planning-artifacts/specs/spec-60-1-the-catalog-config-names-backends-and-sources.md`
  summary: The `test_track.py` `_SCHEMA` path fix (`_PKG.parents[1]` → `_PKG.parent`) is never executed in either CI lane: `test_schema_accepts_assembled_track` opens with `pytest.importorskip("jsonschema")` and `jsonschema` is not a `pyforge-steward` feature dependency, so the track-schema contract stays unpinned in CI exactly as before.
  evidence: `.pixi/envs/pyforge-steward/bin/python -c "import jsonschema"` → `ModuleNotFoundError`; the station suite reports `SKIPPED [1] test_track.py:111: could not import 'jsonschema'`; both `pyforge-station-tests.yml` and `coverage-gates.yml` run steward in that env. Closure: add `jsonschema` to `[feature.pyforge-steward.dependencies]` in `pixi.toml` (shared-surface rule: `environment.yaml` regen + all eight station suites) or drop the `importorskip` — a `pixi.toml` change outside this story.
  location: src/shared/packages/pyforge-steward/tests/unit/test_track.py:111
  origin: spec-deferred b7304c5a328d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-60-1-3: `.claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md` "Registered duties" now trails the CLI by three (`cutover`, `ledger-query`, `catalog`); it is an SKF-managed agent-context file, so the roster is refreshed by an SKF re-export, not a hand edit in a story.

- source_spec: `planning-artifacts/specs/spec-60-1-the-catalog-config-names-backends-and-sources.md`
  summary: `.claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md` "Registered duties" now trails the CLI by three (`cutover`, `ledger-query`, `catalog`); it is an SKF-managed agent-context file, so the roster is refreshed by an SKF re-export, not a hand edit in a story.
  evidence: `SKILL.md:90-94` lists seventeen duties; `cli.py` `DUTIES` has twenty. `tests/meta/test_skf_steward_skill.py` guards the managed-section shape.
  location: .claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md:90
  origin: spec-deferred 7fd098265974 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-60-1-4: The BMAD installer resolves the catalog directory but installs nothing from it: `bmad-method install --custom-source <catalog>` (6.12.0, `--yes`) reports "Local source resolved" then "Found 0 modules", because discovery mode installs only module trees inside the source (a plugin dir with `module.yaml`) and does not follow a plugin's `github` source; the v1 rows are all github pointers.

- source_spec: `planning-artifacts/specs/spec-60-1-the-catalog-config-names-backends-and-sources.md`
  summary: The BMAD installer resolves the catalog directory but installs nothing from it: `bmad-method install --custom-source <catalog>` (6.12.0, `--yes`) reports "Local source resolved" then "Found 0 modules", because discovery mode installs only module trees inside the source (a plugin dir with `module.yaml`) and does not follow a plugin's `github` source; the v1 rows are all github pointers.
  evidence: Verified live 2026-09-19 in a scratch directory (`/tmp/bmad-cs-test`): the real catalog → "Found 0 modules", only core installed; a probe marketplace with one `./plugins/probe-mod` (SKILL.md, no `module.yaml`) and one github-object entry → also "Found 0 modules". Claude Code's marketplace resolution (github/url plugin sources) is the documented form and is unaffected. Closure: Story 60.3's snapshot vendors each listed module's tree under the catalog (upstream layout `skills/module.yaml`, e.g. bmad-builder) so discovery finds them; until then `steward catalog pointers` prints the limitation beside the `--custom-source` line and each row's `repository`/`install_hint` is the install path.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py (CatalogEngine.pointers → installer_note); src/shared/packages/pyforge-steward/catalog/.claude-plugin/marketplace.json
  origin: spec-deferred 0973772ed109 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-62-1: The "First cut (all `on`, 2026-09-15)" section heading in measure-catalog.md duplicates the new per-row `State` values with nothing forcing the heading to update once Story 62.2's add/switch/archive config flips an individual row.

- source_spec: `planning-artifacts/specs/spec-62-1-the-catalog-names-eight-measures-and-their-states.md`
  summary: The "First cut (all `on`, 2026-09-15)" section heading in measure-catalog.md duplicates the new per-row `State` values with nothing forcing the heading to update once Story 62.2's add/switch/archive config flips an individual row.
  evidence: Real future-maintenance risk once a row's state diverges from "all on", but the heading text is untouched pre-existing content (outside this diff's hunk) and the update mechanism belongs to Story 62.2, which is explicitly out of scope for 62.1's Boundaries & Constraints.
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md:7
  origin: spec-deferred abfa62358d40 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-62-1-2: `spec-pyforge-steward/SPEC.md` CAP-44/45/46 already read "(shipped 2026-09-15)" ahead of Epic 62's actual landing, and their `success` bullets are truncated mid-sentence.

- source_spec: `planning-artifacts/specs/spec-62-1-the-catalog-names-eight-measures-and-their-states.md`
  summary: `spec-pyforge-steward/SPEC.md` CAP-44/45/46 already read "(shipped 2026-09-15)" ahead of Epic 62's actual landing, and their `success` bullets are truncated mid-sentence.
  evidence: Confirmed by direct read: CAP-44/45/46 all carry a premature "(shipped 2026-09-15)" annotation and each `success` bullet ends mid-sentence (e.g. CAP-44: "the eight first-cut ids are in `measure-catalog.md` and"). Pre-existing defect in a different file, not caused by this diff; not this story's surface to fix.
  location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md:253-261
  origin: spec-deferred 192de21a2de3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-61-2: This PR touches only non-recipe paths and needs the `maintenance` label at PR open time.

- source_spec: `planning-artifacts/specs/spec-61-2-work-passport-and-core-schema.md`
  summary: This PR touches only non-recipe paths and needs the `maintenance` label at PR open time.
  evidence: Diff touches only `_bmad-output/**` and `src/shared/packages/**`, no `recipes/**`. CLAUDE.md / AGENTS.md require `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance` for any such PR. No PR exists yet from this single-story dev dispatch.
  location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  origin: spec-deferred 69522e746566 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-19 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: done
  verified: 2026-09-20 — resolved at landing: PR #1532 carried the `maintenance` label, applied by `dispatch_land.py` (`_MAINTENANCE_LABEL`) as every dispatch landing does; no code or spec defect (merged 03112ba2d7).

### DW-FU-63-3: `match_bmad_switch_unsafe` denies `scripts/bmad-switch` in every worktree unconditionally, but this repo's own recorded convention says running `bmad-switch` inside a bmad-loop run worktree is the sanctioned exception (to backlink Tier-3), distinct from the "never from a parallel agent" rule the hook is meant to enforce.

- source_spec: `planning-artifacts/specs/spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md`
  summary: `match_bmad_switch_unsafe` denies `scripts/bmad-switch` in every worktree unconditionally, but this repo's own recorded convention says running `bmad-switch` inside a bmad-loop run worktree is the sanctioned exception (to backlink Tier-3), distinct from the "never from a parallel agent" rule the hook is meant to enforce.
  evidence: The intent-contract's literal trigger text ("a worktree ... is present") is unconditional and does not carve out the bmad-loop-run case. AGENTS.md's own governing rule is actually narrower ("never ... from a parallel agent"), and a separate team-memory entry documents the bmad-loop-run-worktree exception explicitly. The hook cannot currently distinguish a solo bmad-loop run worktree from any other worktree, so it would deny a documented-safe action. Resolving this needs an operator decision: either teach the hook a reliable signal for "this is a bmad-loop run's own worktree," or update the team memory/AGENTS.md to say the new hook supersedes the old exception.
  location: .claude/hooks/pre-shell.py:404-413 (match_bmad_switch_unsafe)
  origin: spec-deferred 7684351f25e0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-20 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-63-3-2: `direct-write-governed-path` only fires for Claude's `Edit`/`Write` tool_input; a write to a governed path via a `Bash` heredoc or redirect (`cat > SPEC.md <<EOF ... EOF`) is invisible to the hook entirely, even though this repo's own documented workaround for a restricted path is exactly that Bash/heredoc technique.

- source_spec: `planning-artifacts/specs/spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md`
  summary: `direct-write-governed-path` only fires for Claude's `Edit`/`Write` tool_input; a write to a governed path via a `Bash` heredoc or redirect (`cat > SPEC.md <<EOF ... EOF`) is invisible to the hook entirely, even though this repo's own documented workaround for a restricted path is exactly that Bash/heredoc technique.
  evidence: `session_denials`' `direct-write-governed-path` rule declares `"applies_to": "edit_write"`, so `main()` never evaluates it for a `kind == "bash"` tool call, regardless of tokenizer quality. Closing this fully needs Bash-side write/redirect detection (heredocs, `sed -i`, `python -c "...write(...)"`, `>`/`>>`), which is materially more engineering than this story's ten matchers and is consistent with the hook's own stated "a guardrail, not a sandbox" design philosophy rather than a defect in the current ten rules.
  location: .claude/hooks/pre-shell.py:487-498 (match_direct_write_governed_path); docs/governance/guild-roster.json (direct-write-governed-path applies_to: edit_write)
  origin: spec-deferred 98df9df4abe1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-20 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-63-3-3: `.cursor/hooks.json` invokes the script with a bare relative path (`python3 .claude/hooks/pre-shell.py`) while `.claude/settings.json` deliberately uses the cwd-independent `$CLAUDE_PROJECT_DIR` env var; if Cursor ever runs a hook with a process cwd other than the workspace root, the relative path would fail to resolve and the Cursor half of the guardrail would silently not run at all.

- source_spec: `planning-artifacts/specs/spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md`
  summary: `.cursor/hooks.json` invokes the script with a bare relative path (`python3 .claude/hooks/pre-shell.py`) while `.claude/settings.json` deliberately uses the cwd-independent `$CLAUDE_PROJECT_DIR` env var; if Cursor ever runs a hook with a process cwd other than the workspace root, the relative path would fail to resolve and the Cursor half of the guardrail would silently not run at all.
  evidence: Not independently confirmed against Cursor's actual hook-invocation cwd contract (whether `beforeShellExecution`/`afterFileEdit` always run with cwd at the workspace root, or can vary by multi-root workspace / a different worktree). If it can vary, the consequence is a full silent bypass of the Cursor-side enforcement, which would be high severity; settling this needs checking Cursor's hooks documentation/behavior directly for the cwd guarantee, or adding a self-check the script logs on load.
  location: .cursor/hooks.json:5,11 (command: "python3 .claude/hooks/pre-shell.py")
  origin: spec-deferred 56aa57d39a84 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high (unverified)
  promoted: 2026-09-20 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-63-3-4: `git commit` opened with no `-m`/`-F`/`--message`/`--file` flag (a plain `git commit` or `git commit --amend` that opens `$EDITOR`) carries no message text on the command line at all, so `match_git_commit_guardrail`'s attribution check cannot see it — an AI-attribution or Co-Authored-By line typed into the editor is never caught by this pre-emptive hook.

- source_spec: `planning-artifacts/specs/spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md`
  summary: `git commit` opened with no `-m`/`-F`/`--message`/`--file` flag (a plain `git commit` or `git commit --amend` that opens `$EDITOR`) carries no message text on the command line at all, so `match_git_commit_guardrail`'s attribution check cannot see it — an AI-attribution or Co-Authored-By line typed into the editor is never caught by this pre-emptive hook.
  evidence: `_extract_commit_message` only reads argv tokens; an editor-composed message never appears there. This is a real, non-adversarial gap (a completely ordinary git workflow), not just a deliberate-evasion path. The only pre-shell-hook-level mitigations are either a behavior change (deny any `git commit` that doesn't supply a message via a recognized flag, forcing all commits through the flag-based, inspectable path) or an AGENTS.md/CLAUDE.md policy addition mandating explicit `-m` in agent sessions — the second is an agent-context-file edit, not a code fix, so it is recorded here for an operator decision rather than patched blind. The separate authoritative `commit-msg` git hook still catches this case after the fact (per the rule's own reason text), so this is a gap in the pre-emptive layer specifically, not a total gap.
  location: .claude/hooks/pre-shell.py:291-316 (_extract_commit_message), 416-431 (match_git_commit_guardrail)
  origin: spec-deferred 8b063dc17d11 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-20 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-63-3-5: `match_gh_pr_merge_squash` only denies `--squash`; AGENTS.md's own policy line ("never `--squash`... never `--rebase`... a rebase merge leaves no merge subject for landing evidence either") names `--rebase` as the case that actually lands undetected, since squash is already disabled server-side and therefore unreachable regardless of hook coverage.

- source_spec: `planning-artifacts/specs/spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md`
  summary: `match_gh_pr_merge_squash` only denies `--squash`; AGENTS.md's own policy line ("never `--squash`... never `--rebase`... a rebase merge leaves no merge subject for landing evidence either") names `--rebase` as the case that actually lands undetected, since squash is already disabled server-side and therefore unreachable regardless of hook coverage.
  evidence: Confirmed: AGENTS.md's Trunk/worktrees/PRs section states squash is disabled in repository settings (so this hook's --squash coverage guards an already-unreachable case) while --rebase is not server-side-blocked and is called out by the same sentence as the one that breaks landing-evidence detection. The story's own literal Given/When/Then names only `gh pr merge --squash` as the trigger, and the intent-contract explicitly frames the closed list as "adding to it is a governance act" -- so extending coverage to `--rebase` is a deliberate, separate governance act on guild-roster.json, not a defect in this story's faithful implementation of its own named trigger.
  location: docs/governance/guild-roster.json (session_denials: gh-pr-merge-squash); .claude/hooks/pre-shell.py:434-440 (match_gh_pr_merge_squash)
  origin: spec-deferred b5cfd1fb2eaf — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-20 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-63-3-6: The Problem statement names four deployment modes by name ("Claude Code local or web, Cursor IDE or Cloud"), but the hook and its docs only distinguish two harness families (claude vs cursor) by JSON shape; nothing confirms or documents whether Claude Code web and Cursor Cloud (background agents) actually load and enforce the same settings.json/hooks.json the way the IDE/local surfaces do.

- source_spec: `planning-artifacts/specs/spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md`
  summary: The Problem statement names four deployment modes by name ("Claude Code local or web, Cursor IDE or Cloud"), but the hook and its docs only distinguish two harness families (claude vs cursor) by JSON shape; nothing confirms or documents whether Claude Code web and Cursor Cloud (background agents) actually load and enforce the same settings.json/hooks.json the way the IDE/local surfaces do.
  evidence: `detect()` and every comment in pre-shell.py, `.cursor/hooks.json`, and AGENTS.md's new section treat "claude"/"cursor" as monolithic. The one live-verification citation in the diff is scoped to Cursor's IDE hooks schema; there is no equivalent citation for Cursor Cloud or Claude Code web. If either of those two surfaces does not load the same config the same way, the Problem statement's own named coverage would be silently incomplete rather than named as an exception the way Gemini/Copilot/Devin are. Settling this needs confirming, per-surface, that project-level `.claude/settings.json` and `.cursor/hooks.json` are honored identically in Claude Code web and Cursor Cloud.
  location: .claude/hooks/pre-shell.py:12-23 (module docstring, detect()); AGENTS.md Session guardrails section
  origin: spec-deferred 60d67e31d137 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium (unverified)
  promoted: 2026-09-20 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open
