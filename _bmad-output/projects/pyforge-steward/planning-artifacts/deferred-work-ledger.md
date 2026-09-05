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

### DW-10-3-8: The repo-root Containerfile pins a pixi below the floor its own manifest declares, so that image's builder stage cannot install at all.

- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md`
  summary: The repo-root Containerfile pins a pixi below the floor its own manifest declares, so that image's builder stage cannot install at all.
  evidence: `Containerfile:58` (Story 7.1, the Guild's unified image, governed by `pyforge-steward/spec-unified-container` CAP-1) is `FROM ghcr.io/prefix-dev/pixi:0.76.1`, while `pixi.toml`'s `requires-pixi` is `>=0.76.2`. Pixi enforces that floor, so the builder stage's `pixi install` aborts with `this project requires pixi '>=0.76.2', but you have pixi 0.76.1`. Not inferred — Story 10.3 hit this exact error live when its own Containerfile first reused Story 7.1's tag, which is why `src/platform/Containerfile` is on 0.76.2. Live inventory taken during the follow-up review: thirteen sites carry a pixi version and TWELVE are at 0.76.2 (`requires-pixi`, the `$schema` URL, three `feature.*` floors, `environment.yaml`, `dashboard.yml`, `kedro-viz-publish.yml`, three pins in `herald-live-demo.yml`, `sync-pypi-mappings/action.yml`, `staged-recipes-linter.yml`, and `src/platform/Containerfile`); the root Containerfile is the only holdout. This is NOT covered by DW-7-1-2, which is `status: resolved` (2026-08-09, when all sites were aligned at 0.76.1) — everything except the root Containerfile has since moved up and left it behind, which is that entry's own residual ("the equality is still COMMENT-MAINTAINED — nothing enforces it") coming true a second time. Two pieces of work, neither this story's: raise the tag to 0.76.2 (one line, but it belongs to the spec that owns that image, and the fix should be verified with a real build), and build the cross-site pixi-version detector DW-7-1-2 named as the durable remedy. Note also that `herald-live-demo.yml`'s three pins were absent from the enumeration entirely until this pass; a hand-maintained list that has now been wrong about both its count and its contents is the argument for the detector.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-10-3-8` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-10-3-one-image-both-engines.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

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

### DW-9-3-1: AD-14's PostgreSQL contention proof is not delivered for the new audit store — every test runs against in-memory SQLite only
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-3-the-audit-trail-records-what-was-seen.md`
  summary: AD-14 states "Contention behaviour is proven against PostgreSQL in CI, never inferred from a green SQLite run," and explicitly names the audit store and AD-12's per-message hot-path write as the reason this binds here. This story's entire test suite (`test_dashboard_audit.py`) runs against a single in-process SQLite `:memory:` database with no concurrent-write test — unlike `test_dashboard_cache.py`'s threaded race test for the analogous cache invariant, nothing here exercises concurrent `record_audit_entry` calls at all, against SQLite or otherwise.
  evidence: Raised by Blind Hunter in this story's review pass. Not patched: the spec's own Boundaries explicitly ruled this out of scope ("Prove AD-14's PostgreSQL contention claim — no PostgreSQL CI service exists in this repo's pixi environments yet... the contention proof is a new deferred-work entry, not attempted here"), because no `psycopg2`/PostgreSQL service is provisioned in the `pyforge-steward` pixi feature or anywhere in this repo's CI today — standing one up is an environment/CI-topology decision beyond one story's Code Map, the same class of decision Story 9.1/9.5 repeatedly deferred for the cache backend. Whoever adds PostgreSQL CI coverage (most naturally Story 9.5's deployment-perimeter surface, which already owns the estate's other backend/infra decisions on this ledger, or Story 9.6's proof suite) should add a concurrent-write contention test for `record_audit_entry` at the same time.
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

### DW-9-4-4: `ExportPolicy.webhook_url` has no protection against loopback/link-local/internal targets
- source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md`
  summary: Construction-time validation only checks for an http(s) scheme and a real host — nothing rejects a declared webhook pointed at a loopback, link-local, or cloud-metadata address (e.g. `169.254.169.254`), a defense-in-depth gap for a server-side outbound POST.
  evidence: Raised by Blind Hunter in this story's first review pass. Not patched: `webhook_url` is adopter-declared configuration, the same trust level as `TrustedIngress.addresses`/`AccessDeclaration` elsewhere in this epic, not attacker-controlled per-request input, so this is not a classic SSRF vector today — but Story 9.1 set a precedent of deferring rather than dismissing this class of address-form concern for `TrustedIngress.addresses` (CIDR/hostname/IPv6-mapped forms, still open on this ledger), and this is the same category applied to a new declaration. Belongs with Story 9.5's deployment-perimeter/ingress model, which already owns the estate's other address-form questions.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-9-4-4` there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-4-export-gated-server-side.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

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

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

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

  verified: 2026-08-26 — resolved — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to resolved

  verified: 2026-09-02 — resolved — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-steward/implementation-artifacts/spec-11-2-db-gpt-joins-as-a-pluggable-app.md); ledger status mapped to resolved; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

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
  status: open

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
  evidence: Epic 11 Stories 11.1–11.2 provisioned `langflow_schema` / `dbgpt_schema` via Django `RunSQL` under parent AD-5; Canopy CAP-9 / FR-22 / canopy AD-9 moves production DDL to Liquibase (Epic 27). Architecture spine marks this as conflict-not-override — isolation and `search_path` remain; only the DDL producer changes.
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

### DW-FU-18-2: Live IdP revoke on the next request (FR-31 / canopy AD-15 strong reading) still waits on a per-request token, not this session snapshot.

- source_spec: `planning-artifacts/specs/spec-18-2-the-switcher-shows-only-what-the-user-may-reach.md`
  summary: Live IdP revoke on the next request (FR-31 / canopy AD-15 strong reading) still waits on a per-request token, not this session snapshot.
  evidence: OIDC login writes group-claim names into session idp_token_roles until the next successful pre_social_login. 18.3 JWT re-verify is out of scope. Epic 21 / FR-31 owns next-request revoke.
  location: src/platform/config/authorization/adapters.py
  origin: spec-deferred 47f46e0ea931 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
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

### DW-FU-21-1: Timing, heartbeat, and ingest-at-completion columns for FR-41/FR-42 are not on RunState yet.

- source_spec: `planning-artifacts/specs/spec-21-1-supervisor-tables-in-public.md`
  summary: Timing, heartbeat, and ingest-at-completion columns for FR-41/FR-42 are not on RunState yet.
  evidence: Story 21.1 lands the two public tables only; 21.5 owns front-door query and completed-run timing ingest.
  location: src/shared/packages/django-pyforge/src/django_pyforge/models.py
  origin: spec-deferred 2967d8a34b8a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
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
  evidence: FR-42 budget vs unbounded SELECT; retention is not this story.
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

### DW-FU-23-1: Canopy AD-20 also names audit write and role-built navigation; this story's board is JSON filter-then-search only.

- source_spec: `planning-artifacts/specs/spec-23-1-same-url-different-rows.md`
  summary: Canopy AD-20 also names audit write and role-built navigation; this story's board is JSON filter-then-search only.
  evidence: Story 23.1 ACs and FR-16 name same-URL row isolation via filter_by_role / AccessDeclaration. Audit and build_navigation are already in pyforge.steward.dashboard from Epic 9 and were not wired onto /stations/atlas/board/.
  location: src/shared/packages/django-atlas/src/django_atlas_portal/board.py
  origin: spec-deferred edb30b7864b7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-24-1: Applied-id keys on redis-broker have no TTL, so pyforge.events.applied:* grows on a noeviction instance.

- source_spec: `planning-artifacts/specs/spec-24-1-cloudevents-on-redis-broker.md`
  summary: Applied-id keys on redis-broker have no TTL, so pyforge.events.applied:* grows on a noeviction instance.
  evidence: EventFabric._mark_applied uses SET NX with no EXPIRE. Canopy AD-10 binds redis-broker as noeviction. Story 24.1 ACs do not require a retention policy for idempotency keys.
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

- source_spec: `planning-artifacts/specs/spec-33-2-first-portal-slice-provision-list.md`
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

### DW-FU-8-1-8: No detector semantically verifies the `sync` duty's actual AD-1..AD-9 (from `architecture-jira-github-projects-sync-2026-08-09/ARCHITECTURE-SPINE.md`) compliance — `spec-pyforge-steward`'s surface/memlog machinery only tracks file-level hash drift for files landing under its own package-path and `.steward/*` globs, not cross-spec architectural/behavioral compliance for a capability whose intent is authored entirely by a sibling spec (`spec-jira-github-projects-sync`, `surface: []`) but whose code physically lives under this spec's surface.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md`
  summary: No detector semantically verifies the `sync` duty's actual AD-1..AD-9 (from `architecture-jira-github-projects-sync-2026-08-09/ARCHITECTURE-SPINE.md`) compliance — `spec-pyforge-steward`'s surface/memlog machinery only tracks file-level hash drift for files landing under its own package-path and `.steward/*` globs, not cross-spec architectural/behavioral compliance for a capability whose intent is authored entirely by a sibling spec (`spec-jira-github-projects-sync`, `surface: []`) but whose code physically lives under this spec's surface.
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

### DW-FU-8-2-6: No test anywhere in `test_sync_reconcile_propagation.py` (old or new) covers a first-link item whose CURRENT tracked status value is itself unset/`None` at read time — every existing "never synced" (first-link) test seeds a concrete current status on both sides, only the BASELINE key is absent. The `_MISSING`-vs-`None` sentinel distinction AD-10 exists specifically to prevent collapsing (an absent baseline key means "never synced"; a present key holding `None` means "synced, then explicitly cleared") is therefore never exercised end-to-end for the case where the CURRENT value itself reads as unset on a first link.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-2-zero-loop-guarantee.md`
  summary: No test anywhere in `test_sync_reconcile_propagation.py` (old or new) covers a first-link item whose CURRENT tracked status value is itself unset/`None` at read time — every existing "never synced" (first-link) test seeds a concrete current status on both sides, only the BASELINE key is absent. The `_MISSING`-vs-`None` sentinel distinction AD-10 exists specifically to prevent collapsing (an absent baseline key means "never synced"; a present key holding `None` means "synced, then explicitly cleared") is therefore never exercised end-to-end for the case where the CURRENT value itself reads as unset on a first link.
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

### DW-FU-9-1-4: `get_master_dataset()` is synchronous and its waiter path calls `time.sleep()`. Called from an async Channels consumer — which is the architecture's own model (AD-8/AD-12 put data fetching on the hot path of each data-returning message) — it blocks that worker's entire event loop, stalling every other connection on the process for up to `lock_timeout` (default 30s), not just the waiting one. No async variant, no `sync_to_async` guidance.

- source_spec: `_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md`
  summary: `get_master_dataset()` is synchronous and its waiter path calls `time.sleep()`. Called from an async Channels consumer — which is the architecture's own model (AD-8/AD-12 put data fetching on the hot path of each data-returning message) — it blocks that worker's entire event loop, stalling every other connection on the process for up to `lock_timeout` (default 30s), not just the waiting one. No async variant, no `sync_to_async` guidance.
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

### DW-FU-34-1: Federated-read and write-refused tests skip when the DuckDB `postgres` extension is not already in the local cache, so a CI image without that cache can stay green without proving FR-46 live ATTACH.

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md`
  summary: Federated-read and write-refused tests skip when the DuckDB `postgres` extension is not already in the local cache, so a CI image without that cache can stay green without proving FR-46 live ATTACH.
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
  evidence: Raised by Blind Hunter during Story 8.7's adversarial review pass. Not a NEW unhandled failure mode -- `SyncBaselineTooLargeError` (Story 8.1, AD-2/AD-10's documented escape hatch to Mode B) already exists and already surfaces an oversized baseline as a named, graceful failure rather than a crash or silent truncation -- but this story never measured how much of that pre-existing 255-byte margin it consumes, so whether real boards with long field-override/status-vocabulary combinations will start hitting it more often is genuinely unverified. Worth a follow-up: compute/test a realistic worst-case combined baseline size (longest expected status name + a real Jira accountId) against the ceiling.
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

### DW-FU-8-7-5: The AD-10 "missing baseline key" rule is gated per-PAIR: when both sides' baseline maps are non-empty, a side missing the `"assignee"` key adopts its own CURRENT value as its baseline without comparing or propagating. That is exactly right for the documented accepted limitation (a pre-8.7 pair where NEITHER side has ever observed assignee). It also silently covers an asymmetric state the spec never considered: one side's baseline already carries a real `"assignee"` value while the other side's non-empty baseline lacks the key. There, the pair HAS observed assignee before, but the side missing the key still adopts-without-comparing, so a genuine live divergence (the two systems naming different people) is recorded as converged and never propagated -- no write, no error, no flag.

- source_spec: `_bmad-output/implementation-artifacts/spec-8-7-assignee-and-identity-link-propagation.md`
  summary: The AD-10 "missing baseline key" rule is gated per-PAIR: when both sides' baseline maps are non-empty, a side missing the `"assignee"` key adopts its own CURRENT value as its baseline without comparing or propagating. That is exactly right for the documented accepted limitation (a pre-8.7 pair where NEITHER side has ever observed assignee). It also silently covers an asymmetric state the spec never considered: one side's baseline already carries a real `"assignee"` value while the other side's non-empty baseline lacks the key. There, the pair HAS observed assignee before, but the side missing the key still adopts-without-comparing, so a genuine live divergence (the two systems naming different people) is recorded as converged and never propagated -- no write, no error, no flag.
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
  status: promoted
  disposition: 2026-09-04 — promoted to steward Story 44.7 (spec-python-foundry-cutover fnd:CAP-4, Phase 3 factory island; R-17a env export in 44.3); held ledger `blocked` pending solutioning review (sprint-change-proposal-2026-09-04-foundry-cutover.md)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-2

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-18** — Sizing rewrite: per-pod rows for web (memory-bound; `--preload`; Langflow RSS measured), worker (CPU-bound; separate builds pool), mcp-host, DB-GPT sidecar, Liquibase Job (JVM), Vizro; requests/limits in values; HPA on web and worker; PodDisruptionBudgets; LLM inference stated as external. (red-team S-7, T-7)
  evidence: Review § 4 (R-18); finding ids in parentheses map to § 2 rows with file:line citations.
  status: open
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); Epic 45 candidate against src/platform/; travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-3

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-19** — Network baseline: default-deny NetworkPolicy in the namespace with explicit allows; `automountServiceAccountToken: false`. (red-team X-4, X-6)
  evidence: Review § 4 (R-19); finding ids in parentheses map to § 2 rows with file:line citations.
  status: open
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); Epic 45 candidate against src/platform/; travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-4

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-20** — Secrets profile: age key custody and rotation, an `ExternalSecret` example for the Vault/ESO profile, a rotation runbook for `DJANGO_SECRET_KEY`, `REDIS_PASSWORD`, the DB roles and the assertion PEM (dual-key verify during rotation). (red-team X-7)
  evidence: Review § 4 (R-20); finding ids in parentheses map to § 2 rows with file:line citations.
  status: open
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); Epic 45 candidate against src/platform/; travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-5

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-21** — Observability contract: SLOs for `/ht/`, MCP p99, queue age, event lag; alert rules; a metrics write path for Doctor's flag kill-switch. (red-team A-7, B-5)
  evidence: Review § 4 (R-21); finding ids in parentheses map to § 2 rows with file:line citations.
  status: open
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); Epic 45 candidate against src/platform/; travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-6

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-22** — Live browser streaming: implement `/ws/events/` as a Channels consumer over redis-broker Streams with per-`sub` filtering, or delete the pillar from the Dream. (red-team T-8)
  evidence: Review § 4 (R-22); finding ids in parentheses map to § 2 rows with file:line citations.
  status: open
  disposition: 2026-09-04 — carried, not a cutover blocker (operator: fold docs / carry ops); Epic 45 candidate against src/platform/; travels to python-foundry as a steward-owned entry (spec-python-foundry-cutover Non-goals)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-7

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-23** — Dream doc fixes: `readOnlyRootFilesystem`, Windows / free-threading claims aligned to the shipped Containerfile and `pixi.toml` platforms. (red-team X-6, D-5)
  evidence: Review § 4 (R-23); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — promoted to steward Story 44.2 (document fixes; spec-python-foundry-cutover Constraints); held ledger `blocked` pending solutioning review (sprint-change-proposal-2026-09-04-foundry-cutover.md)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-8

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-24** — Pin the Keycloak version once (`26.4.0`) across Dream, compose and research. (red-team S-6)
  evidence: Review § 4 (R-24); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — promoted to steward Story 44.2 (document fixes; spec-python-foundry-cutover Constraints); held ledger `blocked` pending solutioning review (sprint-change-proposal-2026-09-04-foundry-cutover.md)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-RT-2026-09-02-9

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
  summary: **R-25** — Rewrite the "zero domain models" constraint as "no station-domain models on `django-<station>`". (red-team T-9)
  evidence: Review § 4 (R-25); finding ids in parentheses map to § 2 rows with file:line citations.
  status: promoted
  disposition: 2026-09-04 — promoted to steward Story 44.2 (document fixes; spec-python-foundry-cutover Constraints); held ledger `blocked` pending solutioning review (sprint-change-proposal-2026-09-04-foundry-cutover.md)

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## Foundry cutover 2026-09-04 — carried residue (owner: steward; not a story yet)

Source: `sprint-change-proposal-2026-09-04-foundry-cutover.md`. Bound to Story 44.10 when it dispatches.

### DW-CC-2026-09-04-1

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md`
  summary: Worktree residue on the `local-recipes` checkout — 268 registered git worktrees (58 `.worktrees/`, 66 `.cursor/worktrees`, 33 `.claude/worktrees`, 93 retired under loop homes, 8 loop homes, 3 `local-recipes-wt-*`) and 85 GB under `.claude/worktrees/` — retired at Phase 6, never moved (fnd:AD-1).
  evidence: `git worktree list --porcelain | grep -c '^worktree '` = 268 on 2026-09-04; `du -sh .claude/worktrees` = 85G.
  status: open

### DW-FU-40-1: Structured-log assertions for assertion.mint_refused (caplog on 401/403, no bearer echo) — AC requires logging but tests only check HTTP status.

- source_spec: `planning-artifacts/specs/spec-40-1-idp-bearer-is-verified-before-mint.md`
  summary: Structured-log assertions for assertion.mint_refused (caplog on 401/403, no bearer echo) — AC requires logging but tests only check HTTP status.
  evidence: Refusal tests assert status codes only; removing logger.warning would not fail CI today.
  origin: spec-deferred 03d7c6b1f3a6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-40-1-2: HTTPS JWKS fetch path integration test (production urlopen contract).

- source_spec: `planning-artifacts/specs/spec-40-1-idp-bearer-is-verified-before-mint.md`
  summary: HTTPS JWKS fetch path integration test (production urlopen contract).
  evidence: All assertion tests use file:// JWKS; _fetch_https is never exercised in CI.
  origin: spec-deferred d58ee2121818 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-40-1-3: Import-time no-network invariant test for django_pyforge.assertion.jwks.

- source_spec: `planning-artifacts/specs/spec-40-1-idp-bearer-is-verified-before-mint.md`
  summary: Import-time no-network invariant test for django_pyforge.assertion.jwks.
  evidence: Lazy load is implemented but not pinned by a test that blocks urlopen at import.
  origin: spec-deferred 02a2d7cd20e0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-40-1-4: Full 503 matrix for every _require_verifier_settings() failure mode beyond empty OIDC_JWKS_URL (http:// scheme, blank issuer/audience/algorithms).

- source_spec: `planning-artifacts/specs/spec-40-1-idp-bearer-is-verified-before-mint.md`
  summary: Full 503 matrix for every _require_verifier_settings() failure mode beyond empty OIDC_JWKS_URL (http:// scheme, blank issuer/audience/algorithms).
  evidence: Only test_unconfigured_verifier_returns_503 covers empty JWKS URL; other misconfigurations could regress undetected.
  origin: spec-deferred 9247533f1e37 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-2: Reconcile `resilience-invariants.md` BS-5 row to Story 41.2 single-writer-on-RWO / Parquet model (still describes read-only shared mounts).

- source_spec: `planning-artifacts/specs/spec-41-2-query-plane-process-boundary.md`
  summary: Reconcile `resilience-invariants.md` BS-5 row to Story 41.2 single-writer-on-RWO / Parquet model (still describes read-only shared mounts).
  evidence: Companion invariant doc not in Story 41.2 AC scope; Dream/stack updated but tier-2 resilience doc drift remains.
  origin: spec-deferred cd1c82a2f0e7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-2-2: Extend estate DuckDB policy gate to cover file-backed `ibis.duckdb.connect` and aliased `duckdb` imports.

- source_spec: `planning-artifacts/specs/spec-41-2-query-plane-process-boundary.md`
  summary: Extend estate DuckDB policy gate to cover file-backed `ibis.duckdb.connect` and aliased `duckdb` imports.
  evidence: AST gate matches bare `duckdb.connect` only; production dashboard/semantic layers use no-arg in-memory ibis today but file-backed regression would pass.
  origin: spec-deferred b3fdec19aaea — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-2-3: Add positive Helm fixture when writer plane PVC lands (`pyforge.io/query-plane`, RWO).

- source_spec: `planning-artifacts/specs/spec-41-2-query-plane-process-boundary.md`
  summary: Add positive Helm fixture when writer plane PVC lands (`pyforge.io/query-plane`, RWO).
  evidence: Chart RWO invariant is vacuous on live render until a plane PVC template exists; spec residual already notes this.
  origin: spec-deferred 00bfc74ef4eb — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-2-4: Run duckdb-boundary chart live-render proofs in platform-ci-test (helm currently platform-dev only).

- source_spec: `planning-artifacts/specs/spec-41-2-query-plane-process-boundary.md`
  summary: Run duckdb-boundary chart live-render proofs in platform-ci-test (helm currently platform-dev only).
  evidence: @requires_helm proofs skip in platform-ci-test; guard fixtures only catch synthetic violations, not template regressions.
  origin: spec-deferred b0f3185e8c6f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3: db.changelog-master.yaml's include order does not satisfy its own FK dependencies: python-agent-platform:18 adds a socialaccount FK to django_site, which :10 (sites.0001) creates later.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: db.changelog-master.yaml's include order does not satisfy its own FK dependencies: python-agent-platform:18 adds a socialaccount FK to django_site, which :10 (sites.0001) creates later.
  evidence: Real `liquibase update` on the master changelog stops at `Run: 10` with `ERROR: relation "django_site" does not exist`. Reproduced identically against the baseline master changelog (`git show a4316334fe:...`), so it predates this story; scribe's changesets are appended last and are unaffected. No test executes the master changelog in include order.
  location: src/platform/db/changelog/db.changelog-master.yaml
  origin: spec-deferred b2e7ae9d2371 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-2: No CI workflow runs the scribe suite, so this story's behavioural proofs (DDL-revoked role, named error, changeset-provisioned database) gate nothing.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: No CI workflow runs the scribe suite, so this story's behavioural proofs (DDL-revoked role, named error, changeset-provisioned database) gate nothing.
  evidence: Nothing under .github/workflows/ invokes `pyforge-scribe-test`, and `src/shared/packages/pyforge-scribe/**` is absent from platform-ci.yml's `paths:` filter. This PR runs platform CI only because it touches src/platform/**; a later edit to graph_store_pg.py alone triggers no workflow. Pre-existing — the scribe suite was never wired in.
  location: .github/workflows/platform-ci.yml
  origin: spec-deferred 5bd99ab9e250 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-3: platform_app's real grant set is never executed by any test; the DML-revoked-role test hand-writes equivalent grants instead.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: platform_app's real grant set is never executed by any test; the DML-revoked-role test hand-writes equivalent grants instead.
  evidence: No test applies create_app_role.sql or pyforge-scribe:3 and then connects. test_store_works_as_a_ddl_revoked_role synthesises its own role and types the grants into the test body, so the shipped SQL could drift from it and stay green. Flipping :3's precondition to `expectedResult:0` would skip the grants on exactly the databases where platform_app exists, and every test still passes.
  location: src/platform/db/changelog/changes/pyforge-scribe-3-app-role-grants.sql
  origin: spec-deferred b017b5861086 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-4: Red-team B-1 is only half-addressed — numbering is per-distribution, but scribe's changesets still ship inside the single master changelog, so a scribe schema change still rides the platform release.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Red-team B-1 is only half-addressed — numbering is per-distribution, but scribe's changesets still ship inside the single master changelog, so a scribe schema change still rides the platform release.
  evidence: There is no per-distribution sub-changelog, includeAll, or contexts:/labels: on the new changesets, and every estate gets scribe's DDL whether or not scribe is deployed. Unmapped django-<station> migrations also still fall through to `default: python-agent-platform`, so the release coupling B-1 names persists by default until each station registers.
  location: src/platform/db/changelog/db.changelog-master.yaml
  origin: spec-deferred b1923db21c86 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-5: graph_nodes.embedding is declared without a dimension, so no ivfflat or hnsw index is possible and query_similar sequentially scans the table.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: graph_nodes.embedding is declared without a dimension, so no ivfflat or hnsw index is possible and query_similar sequentially scans the table.
  evidence: `embedding vector` in pyforge-scribe:2, and no index changeset exists. This is parity with the pre-41.3 driver, not a regression, but bringing the DDL under governance is the natural moment to fix it — and it leaves the new README's CREATE INDEX CONCURRENTLY exception process with no user.
  location: src/platform/db/changelog/changes/pyforge-scribe-2-graph-nodes.sql
  origin: spec-deferred a441d8e7a1a7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-6: Every django_db test in src/platform errors at test-database setup on `ValidationError: slug 'home' is already in use`.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Every django_db test in src/platform errors at test-database setup on `ValidationError: slug 'home' is already in use`.
  evidence: Raised from front_door.apps::_seed_lane1_homepage in post_migrate. Reproduced on tests/test_health_endpoint.py, which this story never touches, and it persists with --create-db, so it is not a --reuse-db artifact. It blocks test_app_role_create_alter_drop_refused_by_postgresql and test_live_first_party_tree_is_covered locally; the CI step they mirror was run directly instead.
  location: src/platform/platformapp/front_door/lane1_seed.py:41
  origin: spec-deferred e7fd703e7270 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-7: Two test_openfeature_channel_policy tests are red on main from a cachebox pin drift.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Two test_openfeature_channel_policy tests are red on main from a cachebox pin drift.
  evidence: `cachebox must be pinned '>=5.1,<6' so conda-forge 6.x is not selected (got '>=5.2.3')`. The test reads pixi.toml, which this story does not modify.
  location: src/platform/tests/policy/test_openfeature_channel_policy.py:137
  origin: spec-deferred eca25a0ad356 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-8: GraphSchemaMissing is not re-exported from pyforge.scribe, and no scribe doc records that the durable graph store now requires Liquibase to have run.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: GraphSchemaMissing is not re-exported from pyforge.scribe, and no scribe doc records that the durable graph store now requires Liquibase to have run.
  evidence: PostgresGraphStore.__init__ now raises on an unprovisioned database — a behaviour change for every existing consumer — but only src/platform/db/README.md says so. The scribe package README, docs/cli-runbooks.md and .claude/skills/pyforge-scribe/SKILL.md are silent.
  location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py
  origin: spec-deferred bce4bb0e169d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4: An explicit COMPONENT_BROKER_CA_BUNDLE cannot override a resolving OS trust store, so the operator knob is unreachable on any host that ships a default CA file.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: An explicit COMPONENT_BROKER_CA_BUNDLE cannot override a resolving OS trust store, so the operator knob is unreachable on any host that ships a default CA file.
  evidence: The intent's "Always" clause mandates "Truststore first; explicit bundle path second", so the ordering is contractual and was deliberately not changed here. The consequence is that tier 2 is reached only when tier 1 resolves nothing: `.pixi/envs/python-agent-platform/ssl/cert.pem` exists, and Containerfile:153 copies the env to the same absolute prefix, so the compiled-in default resolves inside the shipped image. An operator installing a private CA at, say, /etc/pki/corp-ca.pem and setting COMPONENT_BROKER_CA_BUNDLE gets the distro bundle in ssl_ca_certs instead, and fails verification at first connect. The escape hatch under the current ordering is SSL_CERT_FILE / SSL_CERT_DIR. Needs a product decision (explicit-wins, or document SSL_CERT_FILE as the knob).
  location: src/platform/config/broker_tls.py — resolve_ca_trust()
  origin: spec-deferred 0719d3dc32ee — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-2: CHANNEL_LAYERS (channels_redis) and REDIS_CACHE_URL (django-redis) share the Redis URL but get none of this TLS posture.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: CHANNEL_LAYERS (channels_redis) and REDIS_CACHE_URL (django-redis) share the Redis URL but get none of this TLS posture.
  evidence: src/platform/config/settings/production.py wires channel_layers_for_broker( REDIS_BROKER_URL) and the django-redis cache aliases; both build their own TLS context with no COMPONENT_BROKER_CA_BUNDLE and no CERT_NONE opt-out. The intent scoped this story to "the Celery broker and the result backend", so this is out of scope here, but it means "single declaration site for the broker's TLS posture" is true for Celery only.
  location: src/platform/config/settings/production.py
  origin: spec-deferred c22fd7e99777 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-3: The Helm chart still wires plaintext redis://, so no deployed component takes the new code path and nothing refuses unencrypted broker traffic.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: The Helm chart still wires plaintext redis://, so no deployed component takes the new code path and nothing refuses unencrypted broker traffic.
  evidence: deploy/charts/platform/templates/_helpers.tpl templates redis:// for REDIS_BROKER_URL, REDIS_CACHE_URL and REDIS_URL, with no TLS key and no COMPONENT_BROKER_CA_BUNDLE; tests/test_chart_invariants.py is unchanged. This story makes TLS honest when it is used; it does not turn it on. Red-team X-2 / directive R-14 is only half-discharged until the chart moves to rediss:// and a deployed plaintext broker is itself refused.
  location: deploy/charts/platform/templates/_helpers.tpl
  origin: spec-deferred 5652c1016bee — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-4: mypy cannot run at all, so the new modules got no type check.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: mypy cannot run at all, so the new modules got no type check.
  evidence: "Error constructing plugin instance of NewSemanalDjangoPlugin" / INTERNAL ERROR (django-stubs vs mypy 2.3.1). It fails before analysing any file, on a clean tree too. Platform CI runs `mypy platformapp config tests`, so that step is red independently of this story — pre-existing, not caused here.
  location: src/platform (Platform CI mypy step)
  origin: spec-deferred 306fd05c246e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-5: configure_observability() now materializes Django settings even when OTel is disabled, and config/__init__.py imports celery_app at module scope.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: configure_observability() now materializes Django settings even when OTel is disabled, and config/__init__.py imports celery_app at module scope.
  evidence: The story added load_django_settings() to configure_observability() to repair a real swallow (DjangoInstrumentor catching ImproperlyConfigured and calling settings.configure()). The call sits ahead of configure_telemetry's otel_sdk_is_disabled() early return, so fail-fast is now imposed on a broader set of process configurations than the bug required, and importing any config.* module pins the settings singleton to whatever DJANGO_SETTINGS_MODULE is set at that moment. No in-repo regression observed — the full suite's failure/error set is byte-identical to baseline — but the import-time contract is now stricter and undocumented.
  location: src/platform/config/observability/__init__.py
  origin: spec-deferred f2ce97b91c74 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-6: REDIS_SSL in base settings has no readers anywhere in the tree.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: REDIS_SSL in base settings has no readers anywhere in the tree.
  evidence: The removed CELERY_BROKER_USE_SSL ternary was its only consumer; a repo-wide grep now returns only its own definition. This change kept it alive (rewritten through is_tls_broker) rather than removing a public settings name that ops tooling might read. Decide whether to drop it or record why it stays.
  location: src/platform/config/settings/base.py
  origin: spec-deferred d081c2e07dbf — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-7: scripts/.spec-surface-baseline.json needs a scoped stamp for the changed and new config/** files.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: scripts/.spec-surface-baseline.json needs a scoped stamp for the changed and new config/** files.
  evidence: The baseline hashes src/platform/config/** per file under the pyforge-mason/spec-django-accelerator-framework entry; settings/base.py, startup/stage_one.py, startup/__init__.py, observability/__init__.py, manage.py and settings/production.py all changed, and config/broker_tls.py is new with no entry at all, so spec-surface-check will report surface-changed. Left to the dedicated fleet reconciliation pass (a scoped stamp from a clean tree, never a bare --write-baseline), matching what stories 41.1, 41.2 and 41.3 did.
  location: scripts/.spec-surface-baseline.json
  origin: spec-deferred f142ec1dd975 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1: Nothing outside the pytest settings supplies PYFORGE_ASSERTION_PUBLIC_KEY, so a deployed or laptop run now answers 503 on every station MCP route.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: Nothing outside the pytest settings supplies PYFORGE_ASSERTION_PUBLIC_KEY, so a deployed or laptop run now answers 503 on every station MCP route.
  evidence: `config/settings/base.py:610-611` defaults both assertion keys to `""`; only `config/settings/test.py:66-67` assigns them, and `grep -rn ASSERTION src/platform/deploy/` returns nothing — `platform.djangoEnv` carries no such env and no secretKeyRef. `resolve_public_pem()` therefore yields `""` and the gate takes its fail-closed 503 branch. The underlying gap is pre-existing — `supervisor.start_run`/`get`, `assertion/client.py`, `AssertionMiddleware` and the mason/doctor portals already call `crypto.verify_assertion`, whose `_setting_pem` raises on an empty key — but this story widens the blast radius from "the supervisor tools and portals" to "every JSON-RPC method on every station". Wiring the keypair Secret is AD-19 / Story 40.1 territory; the matching chart invariant and a `REQUIRED_SETTINGS` entry belong with it.
  location: src/platform/deploy/charts/platform/templates/_helpers.tpl (platform.djangoEnv)
  origin: spec-deferred e25b89413149 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1-2: The new NetworkPolicy admits only `component: web`, while mcp-host's three probes are httpGet on the same port and originate from the node.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: The new NetworkPolicy admits only `component: web`, while mcp-host's three probes are httpGet on the same port and originate from the node.
  evidence: `mcp-host-deployment.yaml:40-55` uses httpGet startup/liveness/readiness probes on `:8090`; the policy has no ipBlock or node allowance. The chart's only prior NetworkPolicy guards Redis, whose probes are `exec`, so there is no in-repo precedent for an HTTP-probed pod behind a podSelector-only ingress rule. On a CNI that subjects node→pod probe traffic to NetworkPolicy the pod never passes its startupProbe. Not fixable inside this story: AC 4 requires ingress "only from web pods", and the invariant enforces exactly one ingress rule, so a probe exception would fail the story's own test. Needs a deploy-profile decision alongside the mTLS/mesh item above.
  location: src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml
  origin: spec-deferred 027cb8cce764 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1-3: The sidecar hop never watches `receive` for `http.disconnect`, and its budget rose from 5s to at least 300s.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: The sidecar hop never watches `receive` for `http.disconnect`, and its budget rose from 5s to at least 300s.
  evidence: `_stream_upstream_body` relays until upstream ends; with `Queue(maxsize=1)` backpressure an abandoned request pins both the pump task and the upstream sidecar connection for the full read budget. Harmless at the old 5s cap, a real resource-holding window at the Celery hard limit. Out of scope on intent authority — the intent asks only that the budget be raised.
  location: src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  origin: spec-deferred 16bc6c104154 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1-4: Agent-facing docs and station skills still document a bare `POST /stations/<name>/mcp`, which now returns 401.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: Agent-facing docs and station skills still document a bare `POST /stations/<name>/mcp`, which now returns 401.
  evidence: `CLAUDE.md`, `AGENTS.md`, the eight `.claude/skills/pyforge-*/SKILL.md` blocks and the `bmad-agent-*` persona skills all describe the route with no `Authorization: Bearer <assertion>` requirement and no pointer to how a caller obtains one. No in-repo caller breaks (portals call in-process by design, per `assertion/client.py`), so the whole behavioural change lands on out-of-repo callers whose contract lives in files this story does not touch.
  origin: spec-deferred 025d5b60e556 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1-5: AC 4's only chart-render proof is `@requires_helm`, and the CI test env has no helm, so it silently skips there.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: AC 4's only chart-render proof is `@requires_helm`, and the CI test env has no helm, so it silently skips there.
  evidence: `requires_helm` is a `skipif`, not a failure. The Platform CI `test` job runs the `platform-ci-test` pixi env, whose deps declare no helm; `kubernetes-helm` is only in `feature.platform-dev`. The story's three (now eight) guard-removed companions are not helm-gated but feed hand-built dicts to the helper, so they prove the helper, not the chart — the template could be deleted with a green CI run. Pre-existing for every chart test in this suite, not introduced here.
  location: src/platform/tests/test_chart_invariants.py
  origin: spec-deferred 20e3e0ad533b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1-6: 401/403 refusals carry no `WWW-Authenticate` challenge and the body is not JSON-RPC-shaped.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: 401/403 refusals carry no `WWW-Authenticate` challenge and the body is not JSON-RPC-shaped.
  evidence: `TransportRefusal.body()` emits `{"error": "..."}` on an endpoint that otherwise speaks JSON-RPC 2.0, and no challenge header points a client at the mint view or at protected-resource metadata, so an MCP client has no discoverable path from the refusal to a working call. The intent specifies the status codes only.
  location: src/shared/packages/django-pyforge/src/django_pyforge/mcp_auth.py
  origin: spec-deferred 645ced623f6b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2: No `celery beat` process is deployed, so `CELERY_BEAT_SCHEDULE`'s retention entry never fires in the cluster.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: No `celery beat` process is deployed, so `CELERY_BEAT_SCHEDULE`'s retention entry never fires in the cluster.
  evidence: The chart's only Celery workload is `worker-deployment.yaml` (`args: ["celery", "-A", "config", "worker", "-l", "info"]`); `grep -n beat` over `compose/compose.yml` and `deploy/charts/platform/values.yaml` returns nothing. `CELERY_BEAT_SCHEDULER` has named `django_celery_beat`'s DatabaseScheduler since before this story, with nothing running it. Mitigated but not closed: `manage.py prune_run_state` makes the sweep runnable by an operator or any external scheduler today, and the story's own test drives both runners. Adding a beat Deployment belongs with Story 42.4, which owns Celery's deployment topology (per-station queues, the `builds` pool, grace periods).
  location: src/platform/deploy/charts/platform/templates/
  origin: spec-deferred 120db8626212 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-2: The station and per-subject ceilings are count-then-create, so simultaneous starts can overshoot by the number of racing requests.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The station and per-subject ceilings are count-then-create, so simultaneous starts can overshoot by the number of racing requests.
  evidence: `enforce_run_bounds` reads `station_queue_depth` / `live_runs_for_subject` before `publish_start` opens its transaction; nothing serialises the two steps. Deliberate, and documented in `supervisor.py`'s module docstring: the failure the bound exists to stop is an agent loop issuing thousands of starts, which an off-by-a-few boundary does not restore, and making it exact needs a lock on a row that does not exist yet. Revisit only if a bound is ever repurposed as a licence/quota rather than backpressure.
  location: src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
  origin: spec-deferred d67fea3b5d6b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-3: A silently-failing cache `set` leaves the bucket unwritten for one request before the next `get` fails closed.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: A silently-failing cache `set` leaves the bucket unwritten for one request before the next `get` fails closed.
  evidence: `django_redis` with `IGNORE_EXCEPTIONS` swallows a write failure into `None`, and `set`'s return is backend-dependent (`BaseCache.set` returns `None` normally), so it cannot be read as a health signal without coupling the limiter to one backend. The following `get` returns `None` and refuses, so the window is one request per subject per outage, not an open door.
  location: src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
  origin: spec-deferred 9cf6509a1547 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-4: The scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run by this story.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run by this story.
  evidence: `.memlog.md` carries this story's surface entry, which downgrades the drift from `fail` to `drift-presumed: warn`, but `--write-baseline --spec pyforge-steward/spec-pyforge-unifying-strategy` must run from a CLEAN worktree after the commit lands or it bakes uncommitted working-tree bytes into the baseline. That spec's baseline also still lags Stories 40.1, 41.2–41.4 and 42.1 (~60 paths), which this story neither caused nor reconciled.
  location: scripts/.spec-surface-baseline.json
  origin: spec-deferred 6e9cafc1fb4f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-5: Nothing outside the pytest settings supplies `PYFORGE_ASSERTION_PUBLIC_KEY` (inherited from Story 42.1), so the limiter is unreachable in a deployed run.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Nothing outside the pytest settings supplies `PYFORGE_ASSERTION_PUBLIC_KEY` (inherited from Story 42.1), so the limiter is unreachable in a deployed run.
  evidence: The rate limiter sits behind the transport gate, which answers 503 when no public key resolves. Until the AD-19 keypair Secret lands (Story 40.1 territory), no deployed MCP call gets far enough to be counted. Recorded here only because it now also gates this story's AC 1; the underlying gap and its remedy are already tracked on `spec-42-1-mcp-transport-authorization.md`.
  location: src/platform/deploy/charts/platform/templates/_helpers.tpl
  origin: spec-deferred 1886c187bae3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-6: `test_mcp_start_audit_returns_handle` leaks a committed live `RunState` row per run, which `MAX_RUNNING_PER_SUB` now counts.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `test_mcp_start_audit_returns_handle` leaks a committed live `RunState` row per run, which `MAX_RUNNING_PER_SUB` now counts.
  evidence: Found during the review pass. `TestClient` drives the app in a worker thread whose connection is in autocommit, so a row the tool creates is committed OUTSIDE the test transaction and survives rollback — the leak predates this story (subject `agent-10-2`, one row per run). Harmless until now; with the 42.2 ceilings in place, five `--reuse-db` runs against the same database exhaust that subject's allowance and the sixth run reds a pre-existing test. CI is unaffected (a fresh PostgreSQL service per job), so the exposure is repeated local runs without `--create-db`. This story's own MCP tests are immune by construction (`_fresh_subject`), which is why they were written that way rather than seeding a fixed subject.
  location: src/platform/tests/test_warden_portal_audit_start_get.py
  origin: spec-deferred 50ce8084d1fb — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-7: `enforce_run_bounds` spends a `start` token before it checks either ceiling, so a subject parked at a ceiling burns its rate allowance on refusals.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `enforce_run_bounds` spends a `start` token before it checks either ceiling, so a subject parked at a ceiling burns its rate allowance on refusals.
  evidence: Raised independently by three review layers. After ~30 refused attempts in a minute the caller receives 429 `rate limited` instead of the 409 that names its live run ids — the response AC 3 exists to deliver, and the one the caller needs in order to wait on or revoke its own runs. Kept as-is because the bucket is the cheap cache check standing in front of two indexed COUNT queries: checking ceilings first would let an unbounded caller drive unbounded database work, which is the failure this story exists to stop. Revisit if the 409 path ever becomes the common case.
  location: src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
  origin: spec-deferred 51cbaac4e31a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-8: The token bucket is a non-atomic read-modify-write, so concurrent requests across web pods lose updates and the effective ceiling exceeds `burst`.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The token bucket is a non-atomic read-modify-write, so concurrent requests across web pods lose updates and the effective ceiling exceeds `burst`.
  evidence: `consume()` does `store.get` -> compute -> `store.set` with no `INCR`, no CAS and no Lua script. N simultaneous requests read the same token count and the last write wins. Same class as the documented count-then-create race on the ceilings, and tolerable for the same reason — an agent loop issuing thousands of calls is still stopped, and a boundary off by the concurrency count does not restore that failure. Recorded because the module's docstring argues its other properties carefully and is silent on this one. Wall clock compounds it: a pod with a fast clock mints tokens, and only backwards skew is guarded (`max(0.0, moment - updated_at)`).
  location: src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
  origin: spec-deferred f4e841b2809b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-9: Migration 0004 adds `subject` without backfilling it, so every pre-existing run counts against nobody's ceiling and cannot be revoked by subject.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Migration 0004 adds `subject` without backfilling it, so every pre-existing run counts against nobody's ceiling and cannot be revoked by subject.
  evidence: `McpHandle.subject` already carries the value, so a `RunPython` backfill joining `run_state` to `mcp_handles` would be mechanical. Left out because it is a data migration over an estate whose row count is unknown, and because the safe guard landed instead: `revoke_subject` now refuses an empty subject, so the `subject=""` cohort cannot be cancelled wholesale by accident. Until backfilled, those rows are invisible to `MAX_RUNNING_PER_SUB` and unreachable by `steward revoke --sub`.
  location: src/shared/packages/django-pyforge/src/django_pyforge/migrations/0004_run_bounds.py
  origin: spec-deferred c10ce373744e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-10: Neither the Helm chart nor compose exposes the eight new tunables, so "tunable without a code change" holds only for whoever can set pod env.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Neither the Helm chart nor compose exposes the eight new tunables, so "tunable without a code change" holds only for whoever can set pod env.
  evidence: `grep -rn "MAX_RUNNING_PER_SUB|MCP_RATE_LIMIT|RUN_STATE_RETENTION"` over `src/platform/deploy/` and `src/platform/compose/` returns nothing. The settings themselves are correct — every number is an `env.int` with a documented default, which is what the spec's Always clause requires — but an operator tuning them today edits the Deployment rather than `values.yaml`. Belongs with the same chart pass that adds the `beat` Deployment (Story 42.4).
  location: src/platform/deploy/charts/platform/values.yaml
  origin: spec-deferred 275898433474 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-11: The `pyforge-steward` skill card's duty list omits `revoke` (this story) and `restore` (Story 41.1), and that file is context-injected.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The `pyforge-steward` skill card's duty list omits `revoke` (this story) and `restore` (Story 41.1), and that file is context-injected.
  evidence: `.claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md` line 90 enumerates the duties ending at `validate-fast`, citing `cli.py:L41-L55`; its grammar block has no `steward revoke --sub` line. The only `revoke` on that page is the unrelated `steward keys revoke` subcommand, which makes the omission actively misleading. An agent reading the card will not know the duty exists. Not fixed here because the card is SKF-compiled output that `skf-update-skill` regenerates, and because Story 41.1 established that the refresh is a separate pass — but that backlog is now two duties deep.
  location: .claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md
  origin: spec-deferred 88a8fcf7b7c5 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-12: Celery tasks outside `execute_supervised_run` carry no `sub` header, so `revoke --sub` does not reach them.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Celery tasks outside `execute_supervised_run` carry no `sub` header, so `revoke --sub` does not reach them.
  evidence: The spec's Approach says "every Celery task tagged with `sub`". Live untagged enqueues remain: `run_compliance_job.delay` (`django_warden_fabric/views.py`), `run_django_task.delay` (`platformapp/front_door/celery_task_backend.py`), plus the langflow and dbgpt integrations. The narrower reading was implemented — the Problem paragraph describes only the supervisor `start` path, which is the only one that creates a `RunState` row — so a revoked subject can still hold work on those queues. Widening needs each of those call sites to carry a verified subject, which most of them do not have today.
  location: src/shared/packages/django-warden/src/django_warden_fabric/views.py
  origin: spec-deferred 06604e77b7b1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-13: No `RateLimit-*` response headers, so a well-behaved agent can only discover its limit by tripping it.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: No `RateLimit-*` response headers, so a well-behaved agent can only discover its limit by tripping it.
  evidence: `Decision` already carries `remaining`, `retry_after`, `rate_per_minute` and `burst`; everything except `Retry-After` on a refusal is discarded. For an agent-facing platform the `RateLimit-Limit` / `-Remaining` / `-Reset` triple is the difference between a client that self-throttles and one that must fail first. Related: the MCP bucket is charged for reads as well as writes, so a client polling `get_run` once a second while holding its permitted runs is throttled for waiting; no cheaper read cost and no documented safe poll cadence exist yet.
  location: src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  origin: spec-deferred 536a9e4da372 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-14: `manage.py revoke_subject` exits 0 when the broker revoke failed, so a shell or cron caller reads a partial revoke as success.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `manage.py revoke_subject` exits 0 when the broker revoke failed, so a shell or cron caller reads a partial revoke as success.
  evidence: `handle()` writes `revoke error: ...` to stderr and returns `None`. Only the steward duty gets this right, because it parses `ok` out of the JSON report — which is what its own `test_a_partial_revoke_is_not_reported_as_ success` pins. The command's contract should match its wrapper's; a `CommandError` on `report["revoke_error"]` would do it. Low because the sanctioned operator grammar is `pyforge steward revoke`, not the management command.
  location: src/shared/packages/django-pyforge/src/django_pyforge/management/commands/revoke_subject.py
  origin: spec-deferred 55a8ece075d0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-15: The steward `revoke` duty exposes neither `--reason` nor `--json`, though the command it drives accepts both.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: The steward `revoke` duty exposes neither `--reason` nor `--json`, though the command it drives accepts both.
  evidence: `manage.py revoke_subject` takes `--reason` (recorded on every cancelled run's `result`), so every revoke driven through the operator grammar is logged as the default "revoked by operator" with no incident reference. `_add_revoke_arguments` also omits the `--json` flag its sibling duties (`init`/`shell-init`/`setup`/`initrepo`/`validate-fast`) carry, even though `RevokeDuty` already returns the full report in `details`.
  location: src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  origin: spec-deferred 1d51b02666b9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-16: `_restore` returns a FULL bucket for stored state that is present but malformed, a fail-open path in a module that promises not to have one.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `_restore` returns a FULL bucket for stored state that is present but malformed, a fail-open path in a module that promises not to have one.
  evidence: A non-dict value, a missing key, or a non-finite number all return `(burst, now)`. The module docstring says "silently allowing traffic because the cache is down is the one outcome this module must never produce"; a poisoned or schema-drifted key produces exactly that. Kept deliberately: the alternative — treating malformed state as unavailable — would lock out every subject during a rolling deploy that changed the stored shape, which is a worse failure than one refill. The narrower real bug (an unbounded `Retry-After` from a negative token count) was patched in this pass; only the full-bucket-on-garbage policy remains.
  location: src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
  origin: spec-deferred 49d0a361b008 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-17: Six new `spec-surface` `drift: fail` rows for this story's four new files land under three OTHER specs' globs and need scoped stamps at landing.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: Six new `spec-surface` `drift: fail` rows for this story's four new files land under three OTHER specs' globs and need scoped stamps at landing.
  evidence: Measured against a detached worktree at the `629ee8c5` baseline: 196 fails before, 136 after, and the comm-diff shows exactly six new rows, all of kind "added" — `revoke.py` and `test_revoke_duty.py` under `pyforge-steward/spec-pyforge-steward`, and the 0004 changeset plus `test_agent_rate_limits_and_run_bounds.py` under both `pyforge-steward/spec-python-agent-platform` and `pyforge-mason/spec-django-accelerator-framework`. Not stamped here for two reasons: `--write-baseline` reads the WORKING TREE, so stamping from a dirty dispatch worktree bakes in uncommitted bytes, and a foreign spec's baseline needs the three-check procedure first. Landing-pass work, scoped per spec — never a bare `--write-baseline`.
  location: scripts/.spec-surface-baseline.json
  origin: spec-deferred 65f67bcb68da — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-18: A RUNNING row whose worker died without reaching `complete_run` counts against both ceilings forever, and nothing reaps it.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: A RUNNING row whose worker died without reaching `complete_run` counts against both ceilings forever, and nothing reaps it.
  evidence: Found by the 2026-09-02 follow-up pass (two review layers). A hard `CELERY_TASK_TIME_LIMIT` SIGKILL, an OOM kill or a pod eviction ends the task without the `except` in `execute_supervised_run` running, so the row stays RUNNING; retention never touches live rows by design. Before this story such a row was a phantom on the board; with the ceilings in place enough of them lock a subject out (`MAX_RUNNING_PER_SUB`) and then the station (`MAX_QUEUE_DEPTH_PER_STATION`), and the only lever is `revoke --sub` per subject. Not patched because a reaper cannot yet tell a dead worker from a task still waiting on the queue: rows are RUNNING from publish and nothing stamps `heartbeat_at` when a worker picks the task up, so "heartbeat older than the hard limit" also describes a task that has legitimately queued behind a full station for ten minutes. The fix needs a pickup heartbeat (or a PENDING->RUNNING transition at pickup) first; then a `prune_run_state` pass that FAILs live rows whose heartbeat is older than `CELERY_TASK_TIME_LIMIT` plus grace is mechanical, and the worker pre-flight added this pass already makes such a row safe to terminalise (a late pickup skips it).
  location: src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
  origin: spec-deferred aaa86de4ce7c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-19: `django_cache_aliases` sets no `SOCKET_CONNECT_TIMEOUT` / `SOCKET_TIMEOUT`, so a partitioned redis-cache stalls each limiter call for the kernel's TCP timeout rather than failing closed quickly.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: `django_cache_aliases` sets no `SOCKET_CONNECT_TIMEOUT` / `SOCKET_TIMEOUT`, so a partitioned redis-cache stalls each limiter call for the kernel's TCP timeout rather than failing closed quickly.
  evidence: Found by the 2026-09-02 follow-up pass. `IGNORE_EXCEPTIONS` turns a connection *failure* into a fast `None`, but a black-holed host is a hang, not a failure, and django_redis passes no timeout unless the OPTIONS name one. This pass moved the limiter off the event loop (`sync_to_async`, thread-insensitive), so a stall no longer freezes the pod, but each stalled call still holds an executor thread until the socket gives up. Pre-existing (steward 20.2 composed the alias, and sessions and renditions share it) and one setting away: `SOCKET_CONNECT_TIMEOUT` and `SOCKET_TIMEOUT` of a few seconds in the alias OPTIONS, which is also what makes the fail-closed refusal *fast*. Belongs with the cache composition, not this story, because it changes every consumer of the alias.
  location: src/platform/platformapp/front_door/lane1_runtime.py
  origin: spec-deferred dae189bbb8f6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-2-20: No index serves the retention sweep, so both passes scan `run_state` on every tick once the table is large.

- source_spec: `planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`
  summary: No index serves the retention sweep, so both passes scan `run_state` on every tick once the table is large.
  evidence: Found by the 2026-09-02 follow-up pass. The two indexes 0004 adds (`subject, status` and `station, status`) serve the start-path counts and the revoke selection; the age pass filters `status IN (...) AND completed_at < cutoff` and the cap pass orders terminal rows by `completed_at, started_at`, neither of which they cover. Tolerable while `RUN_STATE_MAX_ROWS` holds the table near 100k rows and the sweep runs hourly; a `(status, completed_at)` index is a new migration plus a CAP-9 Liquibase changeset, which is why it is not folded into a review pass.
  location: src/shared/packages/django-pyforge/src/django_pyforge/models.py
  origin: spec-deferred ef1cf7616ead — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-02 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open
### DW-FU-42-3: The shipped adapters validate shape and log; Doctor's and Mason's actual reactions (choosing a remedy, running a rebuild, reporting completion) are not implemented here.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The shipped adapters validate shape and log; Doctor's and Mason's actual reactions (choosing a remedy, running a rebuild, reporting completion) are not implemented here.
  evidence: `DomainAdapter.apply` is a no-op for all four types in `django_pyforge/events/adapters.py`. The story's Approach binds the vocabulary, the consumer runner and its Deployment — which now exist and are proven end to end (publish -> consume -> Celery header) — but the station-side behaviour behind each type is station work (Doctor owns the `remedy.requested` consumer per the change proposal's ownership table). `register_adapter()` is the seam: a station subclasses the adapter for its type and re-registers it at AppConfig ready time.
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/adapters.py
  origin: spec-deferred c5a1635a3361 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-2: A process that dies mid-handler leaves the event at-most-once: the applied key is set before the handler runs (red-team A-3, not in this story's scope).

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: A process that dies mid-handler leaves the event at-most-once: the applied key is set before the handler runs (red-team A-3, not in this story's scope).
  evidence: `_apply` does `SET NX` before calling the handler and only deletes the key on a raised exception. After a crash the retry pass re-claims the entry, `_mark_applied` fails because the key is still set, and the entry is ACKed as a duplicate without re-running. The TTL from Story 40.2 bounds this to seven days. Fixing it means moving the applied mark after the handler (at-least-once) or a per-consumer in-flight marker; both change the idempotency contract and belong to a story that names A-3.
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred c3e6568d3cd6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-3: The handler timeout is a budget, not an enforced limit: nothing interrupts a handler that runs past `DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS`.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The handler timeout is a budget, not an enforced limit: nothing interrupts a handler that runs past `DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS`.
  evidence: The consumer runs handlers inline. The timeout is what `harvest_poison` uses as its `min_idle_time` (so a live handler is never stolen from) and what the chart's `terminationGracePeriodSeconds` is sized against; a handler that hangs holds its entry until the pod is replaced, after which the harvest reclaims it. A real limit needs a thread or `SIGALRM` guard; handlers today enqueue Celery work rather than doing it, so the exposure is a stuck consumer, not a stuck event. Review P3 narrowed the rollout exposure to exactly one handler: SIGTERM now stops the fabric before the next claim/read and interrupts the idle wait.
  location: src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
  origin: spec-deferred 1eef53560bc7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-4: `consume_events` now binds through `connect_event_broker` (review P6), so a deployment whose `REDIS_CACHE_URL` equals `REDIS_BROKER_URL` -- the compose stack, which sets only `REDIS_URL` -- refuses to start the consumer with `EventBrokerConfigError`.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: `consume_events` now binds through `connect_event_broker` (review P6), so a deployment whose `REDIS_CACHE_URL` equals `REDIS_BROKER_URL` -- the compose stack, which sets only `REDIS_URL` -- refuses to start the consumer with `EventBrokerConfigError`.
  evidence: `config/settings/base.py` defaults both `REDIS_BROKER_URL` and `REDIS_CACHE_URL` to `REDIS_URL`; the chart sets distinct Service URLs, compose does not. That refusal is AD-10 doing its job (one Redis serving both roles is the canopy anti-pattern), and it lands on the same compose gap already recorded above (no `consume-events` service). Running the consumer locally needs `REDIS_CACHE_URL` pointed at a second database or instance.
  location: src/platform/compose/compose.yml
  origin: spec-deferred d2b7e301ee52 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-5: A SIGTERM that lands mid-batch leaves the entries XREADGROUP already delivered (but not yet attempted) pending under the departing consumer name.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: A SIGTERM that lands mid-batch leaves the entries XREADGROUP already delivered (but not yet attempted) pending under the departing consumer name.
  evidence: Review P3's stop check runs before each entry, so a batch of up to 100 new entries read in one XREADGROUP may be partly unattempted when the loop returns. Those entries carry delivery count 1 and are retried after `backoff_ms(1)` by a consumer of the same name, or reclaimed by `harvest_poison` after the handler timeout by the replacement pod (whose hostname-derived name differs) -- a delay, never a loss. Covered by `test_run_passes_stops_after_pass_harvests_on_schedule_and_waits_only_when_idle`. Reading smaller batches once a stop is likely would shorten it.
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred 93dd72ab6eab — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-6: A harvest claim counts as a delivery, so an abandoned delivery spends an attempt; with `EVENT_MAX_ATTEMPTS=1` a reclaimed entry is quarantined without a retry.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: A harvest claim counts as a delivery, so an abandoned delivery spends an attempt; with `EVENT_MAX_ATTEMPTS=1` a reclaimed entry is quarantined without a retry.
  evidence: XAUTOCLAIM increments the delivery counter (JUSTID would not, but then the fields needed for the unparseable check are not returned). The rule is stated in `harvest_poison` and covered by `test_harvest_quarantines_exhausted_entry_with_recorded_error`; with the default of five attempts it costs one retry per crash, which is the honest reading of "delivered and never acknowledged".
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred b634a61bf243 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-7: compose.yml has no `consume-events` service; only the chart deploys the consumer.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: compose.yml has no `consume-events` service; only the chart deploys the consumer.
  evidence: AC 4 names `helm template`. The local compose stack still runs a producer with no listener; `python manage.py consume_events --station doctor` from a shell against the compose Redis is the workaround until a compose service is added alongside `worker`.
  location: src/platform/compose/compose.yml
  origin: spec-deferred 8cd74bd9678d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-8: `events.replicaCount` and `events.resources` are one knob for every consumer station.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: `events.replicaCount` and `events.resources` are one knob for every consumer station.
  evidence: The values block is a list of station names plus shared settings. Per-station replicas would need a map-shaped value; deliberately not done until a station needs more than one consumer.
  location: src/platform/deploy/charts/platform/values.yaml
  origin: spec-deferred 1ab61d6bae11 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-9: `test_execute_supervised_run_leaves_no_celery_result_key` (pre-existing, Story 40.2) fails locally for lack of a `django_db` mark; unchanged here.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: `test_execute_supervised_run_leaves_no_celery_result_key` (pre-existing, Story 40.2) fails locally for lack of a `django_db` mark; unchanged here.
  evidence: It calls `migrate` and creates a `RunState` row without the mark, so pytest-django refuses the connection. Identical at the `1af2ca2b62` baseline (verified by running the HEAD copy in isolation); it is one of the thirteen pre-existing local failures the platform-suite memory note lists. Not touched because it is not this story's test and a mark change deserves its own eyes.
  location: src/platform/tests/test_cloudevents_redis_broker.py
  origin: spec-deferred 87ff8d12d36c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-10: Ruff and mypy findings on the touched files are pre-existing categories, not new ones.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: Ruff and mypy findings on the touched files are pre-existing categories, not new ones.
  evidence: `ruff check` (platform config) over the touched django-pyforge files: 18 findings, all `PLR0913`/`PLR0917`/`FBT001`/`FBT002` on signatures that predate this story plus five `E501` in code this story did not write. `mypy tests/test_cloudevents_redis_broker.py tests/test_chart_invariants.py` (CI's scope): five errors, all in pre-existing code (`CountingRedis.xadd` override, the `lookup_runner` monkeypatch, the liquibase Job helper's `Any | None` key). Platform CI's `ruff check .` does not lint `src/shared/packages/`.
  location: src/platform/pyproject.toml
  origin: spec-deferred 604a08154215 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-11: Scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run by this story.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: Scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run by this story.
  evidence: The memlog entry for this story is appended (downgrading the drift to `drift-presumed: warn`); `--write-baseline --spec pyforge-steward/spec-pyforge-unifying-strategy` must run from a CLEAN worktree after landing, never from the dispatch worktree — the same residual Story 42.2 recorded, whose ~60-path lag this story does not reconcile either.
  location: scripts/.spec-surface-baseline.json
  origin: spec-deferred 2d7798eb123a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-12: The real-redis delivery test skips in CI: `platform-ci-test` has no `redis-server` binary, so CI proves retry/backoff/DLQ/harvest only against `MemoryRedis`.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The real-redis delivery test skips in CI: `platform-ci-test` has no `redis-server` binary, so CI proves retry/backoff/DLQ/harvest only against `MemoryRedis`.
  evidence: `test_real_redis_retry_backoff_dlq_and_harvest` skips when `shutil.which("redis-server")` is None; the binary is a `platform-dev` feature dependency only and CI's `redis:7` is a service container, not a PATH binary. Adding it to the CI env is a `pixi.toml` + `environment.yaml` change outside this story. The in-memory double now pins redis-py's XCLAIM contract (review P13b), which narrows but does not close the gap.
  location: pixi.toml (feature.platform-dev)
  origin: spec-deferred 864542725626 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-13: A process that dies mid-handler still leaves that group's event at-most-once (red-team A-3): the group-scoped applied key is set before the handler runs, so the redelivery is ACKed as a duplicate.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: A process that dies mid-handler still leaves that group's event at-most-once (red-team A-3): the group-scoped applied key is set before the handler runs, so the redelivery is ACKed as a duplicate.
  evidence: Review pass reaffirmed the implementation pass's A-3 entry after the applied key became group-scoped (review P1): scoping fixed cross-group loss, not same-group crash loss. Out of this story's intent (A-1, A-2, A-4, A-5, R-9).
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred 60b84d1bc4e8 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-14: The handler timeout remains a budget, not an enforced limit; a handler that blocks past it stalls the single-threaded consumer and the harvester re-runs the entry concurrently after the threshold.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The handler timeout remains a budget, not an enforced limit; a handler that blocks past it stalls the single-threaded consumer and the harvester re-runs the entry concurrently after the threshold.
  evidence: Nothing wraps `handler(event)` in a timeout. Reaffirmed by the review pass; the intent treats the handler timeout as a given, not a deliverable.
  location: src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  origin: spec-deferred 6bc0d169948a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-15: Consumer names default to `<station>-<hostname>` (the pod name), so every rollout mints a new consumer and dead consumers accumulate in the group; nothing runs XGROUP DELCONSUMER.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: Consumer names default to `<station>-<hostname>` (the pod name), so every rollout mints a new consumer and dead consumers accumulate in the group; nothing runs XGROUP DELCONSUMER.
  evidence: `consume_events.py` derives the consumer from `socket.gethostname()`; abandoned entries return only via `harvest_poison` after the handler timeout, and `XINFO CONSUMERS` grows with each restart.
  location: src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
  origin: spec-deferred 341892aa5399 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-16: The consumer has no in-process reconnect for a broker outage; a redis ConnectionError ends the loop and the pod relies on Kubernetes restarts (CrashLoopBackOff) to recover.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The consumer has no in-process reconnect for a broker outage; a redis ConnectionError ends the loop and the pod relies on Kubernetes restarts (CrashLoopBackOff) to recover.
  evidence: `run_passes` wraps neither `consume` nor `harvest_poison`; a redis-broker restart kills every consumer pod once.
  location: src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
  origin: spec-deferred 70ec5f7d3ec9 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-3-17: The consume-events Deployment has no liveness probe, so a consumer whose Redis socket hangs or whose handler blocks forever is never replaced.

- source_spec: `planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md`
  summary: The consume-events Deployment has no liveness probe, so a consumer whose Redis socket hangs or whose handler blocks forever is never replaced.
  evidence: The template states "No probes -- the consumer has no HTTP surface"; an exec probe on a per-pass heartbeat file would let the Deployment self-heal. Parity with the worker Deployment, which the intent asked for, is preserved as shipped.
  location: src/platform/deploy/charts/platform/templates/consume-events-deployment.yaml
  origin: spec-deferred 1a0310b208e0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-4: Compose stack still runs a single undifferentiated Celery worker with no beat or builds pool — local dev does not mirror the Kubernetes split-pool topology introduced here.

- source_spec: `planning-artifacts/specs/spec-42-4-celery-hardening-and-the-builds-pool.md`
  summary: Compose stack still runs a single undifferentiated Celery worker with no beat or builds pool — local dev does not mirror the Kubernetes split-pool topology introduced here.
  evidence: src/platform/compose/compose.yml worker service unchanged; deploy/README documents K8s only.
  location: src/platform/compose/compose.yml
  origin: spec-deferred e9c1ae35bc3d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-4-2: Story 42.4 Helm render tests are gated on `@requires_helm` and skip in platform-ci-test when helm is absent — the same pre-existing CI pattern as other chart stories.

- source_spec: `planning-artifacts/specs/spec-42-4-celery-hardening-and-the-builds-pool.md`
  summary: Story 42.4 Helm render tests are gated on `@requires_helm` and skip in platform-ci-test when helm is absent — the same pre-existing CI pattern as other chart stories.
  evidence: test_chart_invariants.py `@requires_helm`; platform-ci-test env has no kubernetes-helm dependency.
  location: src/platform/tests/test_chart_invariants.py
  origin: spec-deferred 395c8d2f9102 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-5: Per-tenant quotas (after R-8 limiter).

- source_spec: `planning-artifacts/specs/spec-42-5-role-namespaces-and-the-tenant-claim.md`
  summary: Per-tenant quotas (after R-8 limiter).
  evidence: Per-tenant quotas (after R-8 limiter).
  origin: spec-deferred 2d5f6c25f413 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-5-2: Legacy bare tenant ids (east/west without pyforge:tenant:) are not accepted even under DJANGO_PYFORGE_LEGACY_BARE_ROLES — only bare station slugs get the migration switch.

- source_spec: `planning-artifacts/specs/spec-42-5-role-namespaces-and-the-tenant-claim.md`
  summary: Legacy bare tenant ids (east/west without pyforge:tenant:) are not accepted even under DJANGO_PYFORGE_LEGACY_BARE_ROLES — only bare station slugs get the migration switch.
  evidence: Spec AC targets bare station names; tenant prefix is required from day one per R-13.
  origin: spec-deferred 0d3ef5a74e33 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-43-4: GitOps repository / Argo profile (steward deploy-profile).

- source_spec: `planning-artifacts/specs/spec-43-4-golden-path-cd-by-digest.md`
  summary: GitOps repository / Argo profile (steward deploy-profile).
  evidence: GitOps repository / Argo profile (steward deploy-profile).
  origin: spec-deferred dd1ebb009b7a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-43-4-2: golden-path-promotion rebuilds all three images after the container job — extra CI minutes per platform-ci run.

- source_spec: `planning-artifacts/specs/spec-43-4-golden-path-cd-by-digest.md`
  summary: golden-path-promotion rebuilds all three images after the container job — extra CI minutes per platform-ci run.
  evidence: The promotion job runs three docker builds independently rather than reusing container job artifacts.
  location: .github/workflows/platform-ci.yml
  origin: spec-deferred dbd876ccb82a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-03 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-9: The chart and compose ship stock `postgres:17`, which has no pgvector, so `pyforge-scribe:1` moves a CREATE EXTENSION failure out of scribe's own process and into the platform's pre-upgrade hook Job.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: The chart and compose ship stock `postgres:17`, which has no pgvector, so `pyforge-scribe:1` moves a CREATE EXTENSION failure out of scribe's own process and into the platform's pre-upgrade hook Job.
  evidence: values.yaml pins `repository: postgres` / `tag: "17"` and compose.yml `image: postgres:17`; `grep -rn -i pgvector src/platform/deploy/ src/platform/compose/` returns nothing. The Helm Job (`post-install,pre-upgrade`) applies the master changelog, so on a stock image `:1` aborts with `could not open extension control file "vector.control"` and the release fails -- for every estate, including ones that never deploy scribe. Before this story the same statement failed only inside the scribe station. Supplying a pgvector-capable image is a deploy-side decision outside this story's boundaries.
  location: src/platform/deploy/charts/platform/values.yaml:108-113
  origin: spec-deferred f23d35461a00 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-10: `_assert_provisioned` names only the relation-absent and no-schema-USAGE cases; column drift and a table-privilege gap still leak raw psycopg errors with no changeset named.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: `_assert_provisioned` names only the relation-absent and no-schema-USAGE cases; column drift and a table-privilege gap still leak raw psycopg errors with no changeset named.
  evidence: `to_regclass` answers existence only. A role with schema USAGE but no table grants passes the assert and then raises a raw `InsufficientPrivilege` from `_load`; a `graph_nodes` missing a column raises a raw `UndefinedColumn`, which `test_legacy_table_without_stale_is_back_filled_by_the_changeset` pins as expected pre-`:4` behaviour. AC-1 only requires the relation-absent case to be named, so this is beyond the contract, but it is the same class of unrecoverable state the review's high finding fixed.
  location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py:114
  origin: spec-deferred 9c5844ee95ba — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-11: Master-changelog include order is load-bearing for scribe (`:1` before `:2` before `:3`) but only set membership and duplicates are asserted.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Master-changelog include order is load-bearing for scribe (`:1` before `:2` before `:3`) but only set membership and duplicates are asserted.
  evidence: `test_every_changeset_file_is_included_in_the_master_changelog` compares sets. Order cannot be inferred from seq either -- the file already includes `python-agent-platform-15` between `:5` and `:6`. A reordered include would put `CREATE TABLE ... embedding vector` before the extension exists and fail at deploy time, with every test green. Distinct from the pre-existing FK-ordering deferral above, which is about python-agent-platform's own order.
  location: src/platform/tests/policy/test_liquibase_ddl_governance.py:252
  origin: spec-deferred 0bbe6f067ad7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-12: `load_map`'s new "default distribution not registered" ValueError is untested and reaches CI as a traceback, and no path migrates a pre-41.3 `sqlmigrate-map.yaml`.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: `load_map`'s new "default distribution not registered" ValueError is untested and reaches CI as a traceback, and no path migrates a pre-41.3 `sqlmigrate-map.yaml`.
  evidence: `run_live_check` calls `load_map` with no handler, so a malformed or old-format map exits with a stack trace instead of the module's `format_findings` output. `test_sqlmigrate_extraction.py` never asserts the rejection. An old-format map (top-level `distribution:` / `migrations:`) yields `distributions == {}` and trips the guard with no hint that the format changed.
  location: src/platform/db/sqlmigrate_extraction.py:125
  origin: spec-deferred fe1bd6c953f3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-13: `MigrationMap.lookup` resolves a migration key claimed by two distributions by YAML insertion order, while db/README.md calls the map a register that "cannot silently collide".

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: `MigrationMap.lookup` resolves a migration key claimed by two distributions by YAML insertion order, while db/README.md calls the map a register that "cannot silently collide".
  evidence: `lookup` returns the first distribution whose `migrations` contains the key and never reports the duplicate. The anti-collision property the README claims for the map is actually provided by `test_changeset_ids_are_unique_across_files`, which scans `changes/*.sql` -- a different artifact from the one AC-3 names.
  location: src/platform/db/sqlmigrate_extraction.py:57
  origin: spec-deferred 991513e38329 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-3-14: Scribe's test suite now hard-depends on the platform tree, so the package can no longer be tested standalone.

- source_spec: `planning-artifacts/specs/spec-41-3-scribe-ddl-moves-into-the-changelog.md`
  summary: Scribe's test suite now hard-depends on the platform tree, so the package can no longer be tested standalone.
  evidence: `tests/unit/conftest.py` resolves `parents[5] / "platform" / "db" / "changelog" / "changes"` and calls `pytest.fail` (not `skip`) when it is absent. The wheel excludes `tests/`, so this bites an sdist or standalone checkout rather than an installed wheel. The reverse edge (host importing `pyforge.*`) is the one the Boundaries forbid; this direction is unaddressed by them.
  location: src/shared/packages/pyforge-scribe/tests/unit/conftest.py:12
  origin: spec-deferred 541750e35940 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-8: load_django_settings() makes Django construct its Settings object twice, re-entrantly, on every process that imports config.*.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: load_django_settings() makes Django construct its Settings object twice, re-entrantly, on every process that imports config.*.
  evidence: config/__init__.py imports celery_app, whose module scope calls configure_observability() -> load_django_settings() -> settings.INSTALLED_APPS. That re-enters LazySettings._setup while Django's outer Settings.__init__ is still importing config.settings.production (which reaches config/__init__.py through `from .base import *`). The inner Settings object is assigned to _wrapped and then silently replaced by the outer one; read_dot_env() also runs twice. No in-repo regression is observable (the whole-suite failure/error set is byte-identical to baseline, 436 passed here vs 420 pre-change with the delta exactly this story's tests), but the work is duplicated and the settings module is imported while the config package is only partially initialised. The existing "materializes settings even when OTel is disabled" entry records the import-time contract; it does not record the double construction.
  location: src/platform/config/observability/__init__.py -- load_django_settings()
  origin: spec-deferred 1468c3938a11 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-9: A CA path that is readable but not parseable as PEM passes the boot gate and fails at first connect.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: A CA path that is readable but not parseable as PEM passes the boot gate and fails at first connect.
  evidence: resolve_ca_trust() checks existence and permission bits, never content, so an empty or truncated corporate bundle resolves as a trust source, stage 1 accepts it, and the component boots -- then every broker handshake fails. That inverts the property resolve_ca_trust()'s own docstring advertises ("a typo or a permission mistake degrades to no trust source -- which stage 1 refuses at boot instead of failing at first connect"). A guard would be a throwaway SSLContext.load_verify_locations(cafile=...) in a try/except ssl.SSLError; note it only helps the cafile half, since capath lookup is lazy by design.
  location: src/platform/config/broker_tls.py -- resolve_ca_trust()
  origin: spec-deferred cf91f75436b1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-10: config.settings.production with COMPONENT_RUNTIME=local composes CERT_NONE and no stage 1 runs to refuse it.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: config.settings.production with COMPONENT_RUNTIME=local composes CERT_NONE and no stage 1 runs to refuse it.
  evidence: Confirmed live: the production leaf + COMPONENT_RUNTIME=local + COMPONENT_BROKER_SSL_CERT_REQS=none + a rediss:// broker loads cleanly and composes ssl_cert_reqs=0, because run_stage_one() early-returns on is_deployed(). The intent keys the exception to COMPONENT_RUNTIME ("CERT_NONE is permitted only under COMPONENT_RUNTIME=local"), so this is contract-compliant and was rejected as a finding in the first review pass on those grounds; R-14's own wording is "must fail the production settings check", which is the leaf, not the marker. Whether the lever should also be refused at the production leaf is the product decision left open.
  location: src/platform/config/startup/stage_one.py -- run_stage_one()
  origin: spec-deferred b9762643b07d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-11: config.asgi -- the entrypoint the production image actually runs -- is covered by nothing in the env CI uses.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: config.asgi -- the entrypoint the production image actually runs -- is covered by nothing in the env CI uses.
  evidence: Containerfile CMD is `gunicorn config.asgi:application`. The three tests that import config.asgi are each gated on pytest.importorskip("langflow"), and langflow is in the python-agent-platform feature, not platform-ci-test -- which is what Platform CI installs for `python -m pytest`. So they skip in CI. This story's entrypoint tests exclude config.asgi for the same reason. The container job boots the image with a healthy config, which is a control, not a refusal. Needs either a langflow-free import path for the ASGI seam or a container-level refusal case.
  location: src/platform/config/asgi.py
  origin: spec-deferred c95ddcf312d7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-12: LANGFLOW_REDIS_URL is a third consumer of the shared Redis URL with no TLS posture, alongside CHANNEL_LAYERS and the django-redis caches.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: LANGFLOW_REDIS_URL is a third consumer of the shared Redis URL with no TLS posture, alongside CHANNEL_LAYERS and the django-redis caches.
  evidence: config/settings/base.py does `os.environ["LANGFLOW_REDIS_URL"] = env("LANGFLOW_REDIS_URL", default=REDIS_CACHE_URL)`, handing the same URL to a third-party service that builds its own client. The existing "CHANNEL_LAYERS and REDIS_CACHE_URL share the URL" entry names two consumers; a follow-up scoped from it would miss this one.
  location: src/platform/config/settings/base.py
  origin: spec-deferred 5a69dfaa81be — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-41-4-13: test_production_leaf_source_wires_stage_one is still a source-substring assertion, and the call-position requirement it sits next to is unguarded.

- source_spec: `planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`
  summary: test_production_leaf_source_wires_stage_one is still a source-substring assertion, and the call-position requirement it sits next to is unguarded.
  evidence: It asserts `"run_stage_one(" in source`, the exact assertion style this story's review pass removed from the broker suite, and it passes regardless of where in production.py the call sits. Story 41.4 made the position load-bearing: the condition reads the composed CELERY_BROKER_URL off the module, so moving the call above the Celery block silently reverts stage 1 to the env-derived URL. test_run_stage_one_forwards_the_settings_module pins the forwarding; nothing pins the ordering.
  location: src/platform/tests/test_startup_required_settings.py
  origin: spec-deferred 041ca9bd08cd — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1-7: Every station app is built `json_response=True`, so the keep-alive frame never fires against the real sidecar and the raised budget stays capped by the ~30s ingress idle timeout.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: Every station app is built `json_response=True`, so the keep-alive frame never fires against the real sidecar and the raised budget stays capped by the ~30s ingress idle timeout.
  evidence: `mcp_dual_era.py:55-56` builds every station MCP app with `json_response=True, stateless_http=True`, so the sidecar's body is always `application/json` and never `text/event-stream`. `_keepalive_frame()` returns `None` for anything but an event stream — correctly, since a comment frame injected into JSON corrupts it — which means the keep-alive path is unreachable in production and a JSON tool call still emits no bytes until it completes. T-5 is therefore only partially closed: the 5s cap and the full-response buffering are gone, but a long JSON call still dies at whatever idle timeout sits in front of the pod. Not fixable inside this story: the intent prescribes comment frames, and there is no legal way to keep a JSON body alive. Closing it needs either SSE-shaped sidecar responses or an ingress idle-timeout decision.
  location: src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  origin: spec-deferred ec2f85a6906c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1-8: The chart wires `MCP_HOST_SIDECAR_BASE_URL` into worker and migrate-job pods that the new NetworkPolicy then denies.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: The chart wires `MCP_HOST_SIDECAR_BASE_URL` into worker and migrate-job pods that the new NetworkPolicy then denies.
  evidence: `_helpers.tpl` (`platform.djangoEnv`) injects the sidecar URL into `worker-deployment.yaml` and `migrate-job.yaml`, and `test_platform_pods_wire_mcp_host_sidecar_base_url_to_internal_service` (`test_chart_invariants.py:1349`) asserts web AND worker carry it — while the new policy admits only `component: web` and the X-5 guard pins the rule to exactly one peer. Nothing breaks today: the only reader is `sidecar_base_url()`, reached solely from `config/asgi.py`'s dispatch, which runs in web. But the two invariants now encode opposite intents, and the first worker-side MCP call will fail at the network layer rather than at the config layer.
  location: src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml
  origin: spec-deferred 514865ff9aff — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1-9: No test drives the real ASGI entrypoint; every test builds its own app around `dispatch_station_mcp`.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: No test drives the real ASGI entrypoint; every test builds its own app around `dispatch_station_mcp`.
  evidence: The single production caller is `_dispatch_http` in `src/platform/config/asgi.py`. `test_mcp_transport_auth.py` calls `dispatch_station_mcp` directly with hand-built scope dicts, and the five updated files each wrap it in their own `application`. So the ACs' "Given `POST /stations/atlas/mcp`" is proved against an assembled callable, not the app gunicorn serves — a reordering inside `_dispatch_http` that let a station path bypass the gate would not fail any test. Pre-existing convention across this suite, not introduced here.
  location: src/platform/config/asgi.py
  origin: spec-deferred 466a9520472a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-42-1-10: `MCP_PROXY_TIMEOUT_SECONDS` is documented only in a source comment.

- source_spec: `planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`
  summary: `MCP_PROXY_TIMEOUT_SECONDS` is documented only in a source comment.
  evidence: The new env var appears in no `values.yaml`, no chart template, and not in `src/platform/deploy/overlays/ocp/cluster-bringup.md`, which already carries an mcp-host readiness checklist. An operator raising the sidecar budget has to read `mcp_http.py` to learn the name exists.
  location: src/platform/deploy/overlays/ocp/cluster-bringup.md
  origin: spec-deferred 5095bc3a8325 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-43-2: PyForgeStationClient default urllib transport has no executing test.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract.md`
  summary: PyForgeStationClient default urllib transport has no executing test.
  evidence: Unit tests inject a mock transport; _urllib path untested in CI.
  location: src/shared/packages/pyforge-core/src/pyforge/core/client.py
  origin: spec-deferred 85ddd72a0ee3 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-43-2-2: Langflow /langflow/api/v1/ prefix-preserving redirect not gated in platform-ci-test.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract.md`
  summary: Langflow /langflow/api/v1/ prefix-preserving redirect not gated in platform-ci-test.
  evidence: test_langflow_mount.py requires langflow package; langflow-free suite covers bare /api/v1 only.
  location: src/platform/tests/test_langflow_mount.py
  origin: spec-deferred fa60252fa0b0 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-43-2-3: Server-side X-PyForge-API-Version header enforcement not implemented.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract.md`
  summary: Server-side X-PyForge-API-Version header enforcement not implemented.
  evidence: Client sets header; station_api.py never validates it against URL version.
  location: src/platform/config/station_api.py
  origin: spec-deferred c22f18414780 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-43-2-4: django-warden portal has not adopted StationHttpClient for host calls.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract.md`
  summary: django-warden portal has not adopted StationHttpClient for host calls.
  evidence: Contract test proves header parity via mock transport only; no portal wiring in diff.
  origin: spec-deferred 700930453bc1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-FU-43-2-5: OpenAPI documents are not schema-validated beyond path-key presence.

- source_spec: `planning-artifacts/specs/spec-43-2-station-api-contract.md`
  summary: OpenAPI documents are not schema-validated beyond path-key presence.
  evidence: Tests assert paths keys exist; no OpenAPI validator or golden document.
  origin: spec-deferred 5da93f3e807e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-09-05 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open
