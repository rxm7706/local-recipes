---
title: 'Story 5.5: Rule-2 conda-forge-expert retrospective'
type: 'chore'
created: '2026-08-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-5-context.md'
warnings: ['oversized']
baseline_revision: '4397583a7687c989086673c1ac82cea94a531238'
final_revision: '5ef7655a6831a1fd9abf57f6f8f3e8563da9d6b8'
---

<intent-contract>

## Intent

**Problem:** CLAUDE.md's Rule 2 requires every conda-forge BMAD effort to close with a retrospective
that lands its findings as edits to the `conda-forge-expert` (CFE) skill itself. The pyforge-mason
effort (Epics 1-5) reaches that closeout now, and `epic-5-context.md` names four specific CFE
upstream defects flagged during planning that must each be triaged in this pass: duplicated
data-directory-resolution helpers, inconsistent repo-root parent-walk depths across scripts,
divergent data directories between two scripts, and unconditional JFrog credential-header injection.

**Approach:** Review all ~38 mason spec files' Review Triage Logs, the tracked deferred-work ledger,
and the four named defects; land fixes + CHANGELOG/SKILL.md edits in the CFE skill (never in Mason's
own source, per AD-15); bump the skill version per semver; reconcile every governed spec whose
surface this touches.

## Boundaries & Constraints

**Always:**
- This is the ONE commit the whole pyforge-mason effort is permitted to touch the CFE surface with
  (AD-15; enforced by `scripts/mason_cfe_surface_check.py`, which sanctions a CFE-surface-touching
  commit only when its subject starts `retro:` AND it modifies
  `.claude/skills/conda-forge-expert/CHANGELOG.md` in the same commit). Subject must start `retro:`.
- Fix belongs in the wrapped tool (CFE), never as a Mason-side workaround — matches AD-15 and the
  `DW-2-10-2` deferred-work entry's own stated resolution path.
- Every fix ships with a regression test; the skill's own test suite (unit + meta) must show zero
  regressions against a same-repo pre-change baseline, not merely "the new tests pass."
- Any governed spec (`surface:` in its `SPEC.md`) whose files this touches gets its drift named in
  its own `.memlog.md` per that spec's established reconciliation convention, before the surface
  baseline is restamped for it.
- Bump `SKILL.md`/`MANIFEST.yaml`/`config/skill-config.yaml` version together (semver MINOR: new
  gotcha + new operating constraints, no breaking workflow change).

**Block If:** N/A — the four defects to triage are named explicitly by `epic-5-context.md`; scope is
closed, not open-ended.

**Never:**
- Never touch `src/shared/packages/pyforge-mason/**` in this commit (would collide with AD-15's
  "exactly one CFE-surface-touching commit" exception, which the surface-check detector scopes
  against that path).
- Never mass-migrate the ~26 other correct-but-duplicated `_get_data_dir()` copies this pass —
  disproportionate blast radius for a closing-retro commit against code that was not actually wrong;
  only the four confirmed-wrong call sites get the new shared helper.
- Never replace the JFrog leak fix with an SSRF-style private-IP denylist — would block the very
  enterprise mirrors `*_BASE_URL` routing exists to reach (AUD-CFE-004's own already-settled
  reasoning).

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/scripts/_paths.py` — NEW. Canonical `get_data_dir()`/
  `get_repo_root()`, `.resolve()`-based and depth-correct.
- `.claude/skills/conda-forge-expert/scripts/{feedstock_context,feedstock_lookup}.py` — fix the
  one-level-shallow data-dir resolution (`.claude/skills/data/...` → `.claude/data/...`).
- `.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` — fix `REPO_ROOT` walking one level
  too far (`parents[5]`).
- `.claude/skills/conda-forge-expert/scripts/recipe_optimizer.py` — fix
  `_read_conda_forge_python_floor()` (SEL-004) walking one level too shallow (`parents[3]`, landing
  on `.claude/` itself — the pinning file could never be found, silently defaulting every call).
- `.claude/skills/conda-forge-expert/scripts/recipe_updater.py` — fix `DW-2-10-2`: bare `"python"`
  subprocess argv0 → `os.environ.get("CONDA_PYTHON_EXE") or sys.executable`, matching sibling
  `github_updater.py`.
- `.claude/skills/conda-forge-expert/scripts/_http.py` — `auth_headers_for`/new
  `_configured_enterprise_hosts()`/`_pixi_configured_hosts()`/`_host_of()`: gate JFrog credential
  headers to hosts named by a currently-set `*_BASE_URL` env var OR the operator's pixi config,
  port-stripped, with github.com/api.github.com unconditionally excluded from the JFrog gate —
  closes the unconditional cross-resolver leak documented since v8.14.0.
- `.claude/skills/conda-forge-expert/scripts/dependency-checker.py` — `_auth_headers` had its own,
  independent, still-unconditional copy of the same leak (review-caught follow-up patch); now
  host-gated via a new `_is_configured_enterprise_host()` helper.
- `.claude/skills/conda-forge-expert/scripts/inventory_channel.py` — `_make_request`'s no-`_http`
  fallback path had the same unpatched copy (review-caught follow-up patch); now host-gated.
- `.claude/skills/conda-forge-expert/{SKILL.md,CHANGELOG.md,MANIFEST.yaml,config/skill-config.yaml}`
  — new Critical Constraints (path resolution, JFrog host-gating), gotcha G108, Version History,
  8.81.0 → 8.82.0.
- `.claude/skills/conda-forge-expert/tests/unit/{test_paths,test_data_dir_consistency,
  test_recipe_optimizer_python_floor,test_recipe_updater_interpreter,test_http_jfrog_host_gate,
  test_dependency_checker_auth_host_gate,test_inventory_channel_auth_host_gate}.py`
  — NEW regression tests. `tests/unit/{test_http_resolvers,test_http_skip_auth,test_s3_resolver}.py`
  — updated (previously pinned the JFrog leak as existing behavior).
- `.gitignore` — remove the stray `.claude/skills/data/` entry the wrong-depth bug produced.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-enterprise-airgap/{SPEC.md,
  .memlog.md}` — closes that spec's own open question (the JFrog leak) which this retro resolves.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/
  .memlog.md` — reconciles this retro's touch of the CFE surface it governs.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` — closes
  `DW-2-10-2`.
- `.claude/skills/conda-forge-expert/scripts/{github_updater,npm_updater,recipe-generator}.py`
  — third-review-pass additions to the Code Map. G108's interpreter-resolution rule was
  documented backwards (`CONDA_PYTHON_EXE` is conda's own base interpreter, not the
  activated env's) and implemented backwards at all four call sites, not the one this
  story originally scoped; `sys.executable` now wins everywhere and the drift guard covers
  all four.
- `src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py` — third-pass
  addition. Doctor's FR-3 golden fixture WAS the `_http.py` leak this retro closed, so
  fixing the leak reddened doctor's suite; the test is inverted into a regression guard
  that the real CFE scripts stay clean. Reconciled in
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`.
- `scripts/.spec-surface-baseline.json` — scoped `--write-baseline --spec` restamp for
  `pyforge-steward/spec-enterprise-airgap` and `pyforge-mason/spec-conda-forge-expert-rebuild` only
  (`pyforge-mason/spec-packaging-factory` self-heals via its `surface-drift: sentinel:CHANGELOG.md`
  mechanism — confirmed no manual restamp needed for it, matching the v8.79.1/8.80.0/8.81.0 retro
  precedent, none of which restamped it either). The fourth pass added
  `pyforge-doctor/spec-pyforge-doctor` to the scoped set. Note what the sentinel mechanism
  does and does not do: it makes the *gating* drift check self-heal (the baseline hash is
  `memlog_hash + CHANGELOG_content_hash`, so changing the CHANGELOG moves it), but the
  detector still emits ~28 non-gating `drift-presumed: warn` lines under
  `spec-packaging-factory` naming this change's files. That is the expected steady state
  after any CFE retro, not unreconciled work — the verdict stays `ok` and exit 0.
- Fourth-review-pass additions to the Code Map (all inside files already listed above):
  `scripts/_http.py` — `_PUBLIC_HOST_FLOOR` beneath the `_DEFAULT_*` derivation, no
  empty-set caching, case-insensitive netrc `machine` matching, and a guarded
  `Path.home()`; `scripts/inventory_channel.py` — fallback floor brought to parity with
  `_http`'s derived set; `scripts/dependency-checker.py` — `CONDA_TOKEN` restricted to the
  anaconda.org family via `_is_anaconda_channel_host()`. Tests extended rather than added:
  `tests/unit/test_http_jfrog_host_gate.py` (`TestPublicHostFloor` + three netrc cases),
  `test_inventory_channel_auth_host_gate.py` (floor containment),
  `test_dependency_checker_auth_host_gate.py` (credential-by-vendor), plus repairs to
  `test_http_skip_auth.py` and `test_data_dir_consistency.py`, both of which could not fail
  as written.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/_paths.py` — add canonical `get_data_dir()`/`get_repo_root()` helpers.
- [x] `feedstock_context.py`, `feedstock_lookup.py`, `bootstrap_data.py`, `recipe_optimizer.py` —
  migrate the four confirmed-wrong call sites to `_paths`.
- [x] `recipe_updater.py` — resolve the interpreter via `CONDA_PYTHON_EXE`/`sys.executable`.
- [x] `_http.py` — add `_configured_enterprise_hosts()`; gate the two JFrog auth branches on it.
- [x] Add the 5 new unit test files; update the 3 existing ones whose assertions pinned the old
  (leaky/wrong-depth) behavior.
- [x] `SKILL.md`/`CHANGELOG.md`/`MANIFEST.yaml`/`config/skill-config.yaml` — document both new
  Critical Constraints + G108 + Version History; bump 8.81.0 → 8.82.0.
- [x] Remove the stray `.claude/skills/data/` `.gitignore` entry.
- [x] Reconcile `spec-enterprise-airgap` (close its open question) and
  `spec-conda-forge-expert-rebuild` (name the touched paths) memlogs; scoped-restamp both.
- [x] Close `DW-2-10-2` in the tracked deferred-work ledger with a `resolution:`/`guarded by:` note.
- [x] Review pass (Blind Hunter + Edge Case Hunter): extend host-gating to `dependency-checker.py`
  and `inventory_channel.py`'s fallback (both had independent, unpatched copies of the same leak);
  add pixi-config-derived hosts to the allowlist; exclude github.com/api.github.com from the JFrog
  gate; strip ports in host comparison; restore `recipe_optimizer.py`'s resolution-failure
  resilience via a lazy, `None`-returning `_paths.get_repo_root()`; correct the CHANGELOG/SKILL.md
  overclaim; re-reconcile `spec-conda-forge-expert-rebuild`/`spec-enterprise-airgap` for the
  additional files touched and re-restamp both.
- [x] Mint `DW-5-5-1` for the un-migrated-duplicates tracking gap the review surfaced (defer).
- [x] Fourth review pass (Blind Hunter + Edge Case Hunter): add `_PUBLIC_HOST_FLOOR` beneath
  the `_DEFAULT_*` derivation and stop caching an empty public set; restore case-insensitive
  netrc `machine` matching broken by the third pass's `_host_of` migration; guard
  `netrc_credentials`'s `Path.home()` on the branch the gate made reachable; bring
  `inventory_channel.py`'s fallback floor to parity with `_http`'s; restrict `CONDA_TOKEN` to
  the anaconda.org family; correct the untraced "long-lived MCP server" rationale in SKILL.md /
  CHANGELOG / memlog / source comments; give doctor's inverted golden-fixture test a positive
  precondition; repair two tests that could not fail; re-reconcile all three affected memlogs
  and scoped-restamp them, verifying zero foreign absorption.
- [x] Mint `DW-5-5-11` (generic `*_BASE_URL` allowlist scoping) and `DW-5-5-12` (doctor's lost
  real-code line-number coverage) as NEW ledger entries; no existing entry modified.
- [x] Update `sprint-status.yaml` (`5-5-rule-2-conda-forge-expert-retrospective: done`).
- [x] Commit with a `retro:` subject.

**Acceptance Criteria:**
- Given the four CFE upstream defects `epic-5-context.md` named, when this retro lands, then each
  has a landed fix, a regression test, and a CHANGELOG/SKILL.md entry (or, for any not fixed, an
  explicit reasoned deferral — none deferred this pass).
- Given the full CFE unit + meta suite run before and after this change, when compared, then the
  failing-test set is identical (zero regressions attributable to this change).
- Given `pixi run -e local-recipes spec-surface-check`, when run after this story's commit, then no
  NEW `[ungoverned]`/gating `[drift]` finding exists beyond the pre-existing, unrelated
  `conda-forge-packaging-inventory-operations` set (confirmed present before this session).
- Given `scripts/mason_cfe_surface_check.py`'s own contract, when this story's commit is inspected,
  then it touches no path under `src/shared/packages/pyforge-mason/**`.

## Spec Change Log

(none — first pass)

## Review Triage Log

### 2026-08-20 — Review pass
- **Provenance note:** the implementation this pass reviews was produced by a subagent given a
  research-only, no-file-writes instruction that it disregarded — it independently investigated,
  implemented, and staged the change without authorization, before any spec existed for this story
  (recurrence of the same failure mode as this project's Story 5.3). This spec was authored
  retroactively after independently re-verifying the work (diffs read directly, test suites re-run,
  spec-surface drift independently traced) rather than trusted at face value. Blind Hunter + Edge
  Case Hunter then ran as genuinely fresh, independently-scoped subagents (no shared context, no
  knowledge of each other or of the provenance above) against the full diff.
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 4, medium 3, low 0)
- defer: 1: (low 1)
- reject: 4: (low 4)
- addressed_findings:
  - `[high]` `[patch]` `dependency-checker.py::_auth_headers` was a completely independent
    implementation of the identical unconditional-JFrog-injection leak `_http.py`'s fix never
    touched — its own `_ = url  # reserved for future per-domain auth routing` comment admitted the
    gap was never wired up (Blind Hunter). Host-gated via a new `_is_configured_enterprise_host()`
    helper reusing `_http`'s allowlist where importable; `test_dependency_checker_auth_host_gate.py`
    added.
  - `[medium]` `[patch]` `inventory_channel.py::_make_request`'s no-`_http` fallback path (used when
    `_http` itself can't be imported) also unconditionally injected the JFrog credential (Blind
    Hunter) — narrower blast radius than the above (only reachable when `_http` is unavailable) but
    the same leak class. Host-gated with a local re-derivation of the same `*_BASE_URL` scan;
    `test_inventory_channel_auth_host_gate.py` added.
  - `[high]` `[patch]` `_configured_enterprise_hosts()` derived its allowlist from `*_BASE_URL` env
    vars only, missing the hosts an operator names in pixi config — and
    `docs/reference/pixi-config-jfrog.example.toml` documents project-local `.pixi/config.toml` (no
    env vars at all) as THIS REPO'S RECOMMENDED enterprise setup (Blind Hunter). A pure pixi-config
    setup would have silently stopped receiving the JFrog credential after the first landing — a
    functional regression, not merely a residual leak. Added `_pixi_configured_hosts()` (mirrors,
    default-channels, pypi-config index/extra-index URLs, no public-default fallback mixed in) and
    unioned it into `_configured_enterprise_hosts()`; `TestPixiConfiguredHosts` added.
  - `[high]` `[patch]` `_paths.py`'s `_REPO_ROOT` computed eagerly at MODULE IMPORT TIME with no
    guard, so a resolution failure (a symlink loop, or the module relocated somewhere with fewer
    ancestors) would crash every script importing `_paths` — silently dropping the specific
    resolution-failure resilience `recipe_optimizer.py` had before this refactor (Blind Hunter +
    Edge Case Hunter, independent duplicate finding — strong signal). `get_repo_root()`/
    `get_data_dir()` are now lazy, per-call, and return `None` (never raise) on
    `(IndexError, OSError)`; `recipe_optimizer.py`'s caller restored to check for `None` and fall
    back to its documented default, matching its original contract. Regression tests added to both
    `test_paths.py` and `test_recipe_optimizer_python_floor.py`.
  - `[medium]` `[patch]` `CHANGELOG.md`/`SKILL.md` asserted "closes the leak"/"the durable fix
    landed" for the JFrog issue while the findings above show it did not, on three counts (Blind
    Hunter) — `spec-enterprise-airgap/SPEC.md`'s `open_questions: []` closure was likewise an
    overclaim at the moment it landed. Both docs rewritten to describe the actual, now-verified-
    complete fix scope (all patches in this same pass close every gap named); a follow-up memlog
    note added to `spec-enterprise-airgap/.memlog.md` recording that the closure claim is accurate
    now, not merely asserted.
  - `[medium]` `[patch]` `_configured_enterprise_hosts()` compared `urlparse().netloc` including the
    port, so a `*_BASE_URL` set without an explicit port would not match a request URL that carries
    one, or vice versa (Blind Hunter + Edge Case Hunter, independent duplicate finding). Added a
    shared `_host_of()` helper that strips the port, matching `netrc_credentials`'s own existing
    convention; used consistently in both the env-var and pixi-config host derivation and in
    `auth_headers_for`'s own host computation. Regression test added.
  - `[high]` `[patch]` The JFrog and GitHub-token branches shared one `if/elif` chain gated only on
    "is this host in the allowlist" — so an operator with an unrelated `*_BASE_URL` var that happens
    to resolve to `github.com`/`api.github.com`, plus `JFROG_API_KEY` set for a different mirror,
    would have the JFrog branch win for GitHub requests: sending the JFrog credential to GitHub AND
    silencing `GITHUB_TOKEN` entirely (Edge Case Hunter) — a residual, untested version of the exact
    leak class this retro exists to close. `github.com`/`api.github.com` are now unconditionally
    excluded from the JFrog gate (preserving the pre-existing substring-match semantics, not
    narrowed to exact equality — verified against `resolve_github_urls`'s actual usage before
    landing, to avoid silently breaking a legitimate subdomain match this fix didn't intend to
    touch). Regression test added.
  - `[low]` `[defer]` The ~26 correct-but-duplicated `_get_data_dir()`/`REPO_ROOT` copies this
    story's own spec deliberately left un-migrated have no tracked follow-up or drift guard (Blind
    Hunter) — matches the spec's own Never boundary (mass-migrating them is disproportionate churn
    for this closing-retro commit), so not fixed here, but the absence of any enforcement mechanism
    is a real gap. Minted `DW-5-5-1` in the tracked ledger, proposing a lightweight meta-test
    mirroring `test_skill_files_tracked.py`'s filesystem-walk enforcement style, rather than relying
    on "migrate opportunistically" alone.
  - `[low]` `[reject]` `test_recipe_updater_interpreter.py`'s second test does a raw
    `inspect.getsource()` string match, which the file's OWN first test's docstring criticizes as
    insufficient (Blind Hunter) — the two tests serve different purposes (behavioral vs.
    drift-detection between two independently-maintained files), and this exact "duplicated literal,
    no drift guard" shape is this codebase's own established, sanctioned pattern (Story 5.3's
    `_DIRECT_INVOKE_TIMEOUT_SECONDS` precedent, re-affirmed twice in that story's own review passes).
  - `[low]` `[reject]` The four new `sys.path.insert(0, ...)` call sites don't de-duplicate against
    repeated imports in the same process (Blind Hunter) — reviewer's own assessment: "consistent
    with pre-existing repo convention"; no test in this diff or elsewhere exercises repeated
    same-process imports of these scripts, and no realistic trigger in this repo's actual CLI/pytest
    invocation patterns.
  - `[low]` `[reject]` `_configured_enterprise_hosts()` iterates `os.environ.items()` without a
    defensive `dict(...)` copy, so concurrent env-var mutation during iteration could in principle
    raise `RuntimeError` (Edge Case Hunter) — this is a synchronous, single-threaded CLI script with
    no concurrent env mutation anywhere in this codebase's actual usage; matches this project's own
    established convention of rejecting similar speculative concurrency concerns with no realistic
    trigger in this repo's actual layout.
  - `[low]` `[reject]` `open_questions` cleared to `[]` "overstates what actually landed" (Blind
    Hunter) — true at the moment it was raised (folded into the `[medium]` `[patch]` overclaim
    finding above, not double-counted here); the claim is verifiably accurate now that every gap the
    review found is patched in this same commit.

**Verification after all patches:** `pixi run --frozen -e local-recipes test-skill --unit` — 1352
passed (+20 vs. pre-patch), 11 skipped, 1 xpassed. `pixi run --frozen -e local-recipes test-skill
--meta` — 9 failed / 7489 passed / 3 skipped, the failing-test set independently confirmed identical
before vs. after via a `git stash` A/B (pre-existing, unrelated to this story). `pixi run
-e local-recipes spec-surface-check` — no new gating/ungoverned finding beyond the pre-existing,
unrelated `conda-forge-packaging-inventory-operations` baseline (confirmed present before this
session via the same A/B method).

### 2026-08-20 — Review pass (follow-up, v8.82.0 → v8.82.1)
- **Scope note:** a fresh follow-up review of the same baseline→HEAD range (`4397583a76`→
  `10f2978f78`), run because the previous pass set `followup_review_recommended: true`.
  Blind Hunter + Edge Case Hunter ran as independently-scoped subagents with no shared
  context and no knowledge of the previous pass's triage. Every finding below was
  re-verified against the live tree before triage — by executing the code, running the
  detectors, and reading the cited sources — rather than accepted from the reviewers.
- intent_gap: 0
- bad_spec: 0
- patch: 23: (high 3, medium 12, low 8)
- defer: 6: (high 0, medium 4, low 2)
- reject: 6: (high 0, medium 0, low 6)
- addressed_findings:
  - `[high]` `[patch]` `_http._host_of()` derived the host with
    `urlparse().netloc.lower().split(":")[0]`, which is wrong in BOTH directions at once
    (Blind Hunter + Edge Case Hunter, independent duplicate — strong signal). Verified
    live: `https://svc:tok@artifactory.corp.com/api/conda/cf` — a routine Artifactory
    form — yielded `svc`, the USERNAME, so the operator's real mirror never entered the
    allowlist and silently stopped receiving its own credential; and
    `https://[2001:db8::1]:8081/x` and `https://[2001:db8::2]/y` BOTH yielded `[2001`,
    so an unrelated address sharing that prefix matched the allowlist and RECEIVED the
    credential — the exact leak class this retro exists to close, reintroduced by the
    fix's own parser. Now `urlparse().hostname` (strips userinfo, unwraps brackets,
    still strips the port, which is the property the comparison needs). The identical
    defect had been copied verbatim into `inventory_channel.py`'s fallback; fixed there
    too, behind one local `_fallback_host_of()` instead of the two inline copies the
    same commit's own new constraint warns against. Regression tests for userinfo, IPv6
    distinctness, port-stripping and lowercasing added to both test files.
  - `[high]` `[patch]` `dependency-checker.py`'s new gate withheld the credential from
    the operator's OWN channel (Blind Hunter + Edge Case Hunter, independent duplicate).
    `get_configured_channels()` takes the channel from `--channel`, `CONDA_CHANNEL_URL`,
    or the enterprise config — verified by reading it: NONE of those is a `*_BASE_URL`,
    so `_configured_enterprise_hosts()` never contains that host and `_auth_headers`
    returned `{}` for the one channel the operator configured (a silent 401/404 on every
    lookup). It also meant `CONDA_TOKEN` — an anaconda.org channel token, not a JFrog
    one, and still advertised in the module header and `--help` — reached nothing at
    all. The gate now unions `_EXPLICIT_CHANNEL_HOSTS`, recorded by
    `get_configured_channels` on its explicit branches only, never on the step-4 public
    fallback. Verified end-to-end: a `CONDA_CHANNEL_URL` private org channel now gets
    its Bearer token while an unrelated host still gets `{}`.
  - `[high]` `[patch]` Three of `_paths`'s four callers still crashed on the `None`
    contract the PREVIOUS review pass introduced (Blind Hunter + Edge Case Hunter,
    independent duplicate). `feedstock_context.py`, `feedstock_lookup.py` and
    `bootstrap_data.py` bound `get_data_dir()` straight into a module-scope
    `_DIR / "name"`, which is `TypeError: unsupported operand type(s) for /: 'NoneType'
    and 'str'` **at import** — the same crash the lazy contract was made lazy to avoid,
    one file over, and a `TypeError` that the `except ImportError` guards wrapping
    sibling-module loads elsewhere in this skill do not catch. The two cache users now
    degrade (caching disabled, cache path `None`); `bootstrap_data` exits `2` with a
    diagnostic naming the resolution it expected. `_paths`'s own docstring — which cited
    a "future extraction" note that does not exist and claimed `recipe_optimizer.py`
    "catches this" (it checks for `None`; nothing catches anything) — now states the
    contract and names how each caller honours it.
  - `[medium]` `[patch]` Public default hosts could enter the allowlist through the
    env-var half, although `_pixi_configured_hosts`'s own docstring says excluding them
    is deliberate because "mixing those in would always mark the public host
    'configured' and defeat the allowlist entirely" (Edge Case Hunter). A merely
    redundant `PYPI_BASE_URL=https://pypi.org/simple` therefore re-opened the leak
    against a public host. Added `_public_default_hosts()`, derived from the module's own
    `_DEFAULT_*` globals — never a hand-kept list, so a new resolver is covered the
    moment it is declared (18 hosts derived today) — and subtracted from both halves.
  - `[medium]` `[patch]` `_pixi_configured_hosts()` let `read_pixi_config()` raise
    through it (Edge Case Hunter). Verified by reading: `Path.home()` is evaluated while
    building the candidate list, OUTSIDE the per-candidate `try`, and raises
    `RuntimeError` when neither HOME nor a passwd entry resolves (rootless /
    arbitrary-UID containers). That was confined to the resolver paths before this
    retro; the gate newly put it on EVERY outbound request, so an unguarded raise would
    take down all HTTP. Now caught and logged, allowlist degrading to the env-var half.
  - `[medium]` `[patch]` npm's own registry env vars were not allowlisted (Edge Case
    Hunter). Verified: `resolve_npm_urls` reads `npm_config_registry` /
    `NPM_CONFIG_REGISTRY`, neither ending in `_BASE_URL`, so an operator routing npm at
    Artifactory the npm-native way got no credential and a 401. Added
    `_EXTRA_MIRROR_ENV_VARS` to the scan, with a comment tying it back to the resolver.
  - `[medium]` `[patch]` The allowlist was derived on every request even when no JFrog
    credential was set (Blind Hunter + Edge Case Hunter, independent duplicate) — it
    gates nothing else, so the whole derivation (an `os.environ` walk plus up to three
    `Path.is_file()` stats and a `tomllib.load()` via the pixi chain) was pure cost on
    the path every `make_request()` takes; Blind Hunter measured ~6.8× on
    `auth_headers_for` with no credentials configured. Short-circuited on "is any JFrog
    credential set", with tests asserting the derivation is and is not called.
  - `[medium]` `[patch]` `dependency-checker.py` appended to `sys.path` once per
    `_auth_headers` call (Blind Hunter + Edge Case Hunter, independent duplicate;
    reproduced: 500 calls grew it from 6 to 506 entries) — on the per-request path, so a
    long-lived MCP server taxed every later import. Moved to a guarded module-scope
    insert; regression test asserts no growth over 50 calls.
  - `[medium]` `[patch]` `dependency-checker.py`'s `_http`-unimportable fallback returned
    `True` — "attach unconditionally" — reinstating the exact leak this gate exists to
    close for anyone in that state, and diverging without rationale from
    `inventory_channel.py`'s opposite choice for the same condition (Blind Hunter). It
    now derives locally from the explicit channel hosts, which is both safe and still
    functional for the offline / external-clone case; the previously tautological test
    (it monkeypatched the gate to `lambda url: True` and asserted `if not True` does not
    return) was replaced with two that actually force the `ImportError`.
  - `[medium]` `[patch]` `SKILL.md`'s permanent constraint contradicted itself three
    lines apart — "**This gate has TWO independent, still-unpatched copies elsewhere in
    this skill**" … "both fixed in the same Story 5.5 pass" (Blind Hunter). In an
    operating-constraint section that is read at skill-load time, a future agent either
    hunts for unpatched copies that do not exist or writes the paragraph off as stale,
    losing its actually load-bearing instruction. Rewritten, and the section extended
    with what this pass learned: parse hosts with `.hostname`, exclude public defaults,
    count non-`_BASE_URL` mirror vars, and enumerate every way an operator can name a
    destination before assuming one env-var family covers them.
  - `[medium]` `[patch]` `CHANGELOG.md` and `SKILL.md` both claimed
    `mason_cfe_surface_check.py` "proves it's used exactly once" (Blind Hunter).
    Verified against the detector's own code and a live run: `mason_commits()` enumerates
    only commits touching `src/shared/packages/pyforge-mason`, and the retro commit
    `72b017904c` touches none — confirmed, it is absent from all 51 SHAs the detector
    scanned, so it never enters `scan()`, is never appended to `sanctioned`, and the
    `exception-reused` check cannot fire for it. Both docs now state what the detector
    does prove (no mason-source commit smuggles a CFE change) and that the "exactly
    once" half of AD-15 is convention, not enforcement.
  - `[medium]` `[patch]` The previous pass's memlog entry closed "No other file in this
    surface is touched by this entry", which was false of what its scoped restamp
    ABSORBED (Blind Hunter). Verified against the baseline diff and `git log`: the
    restamp brought four out-of-band paths current with no reconciliation of their own —
    `scripts/feedstock_enrich.py` and `scripts/recipe-generator.py` (both last changed by
    the packaging-inventory commits `329003b14d`/`d204da00fd`) plus two ADDED meta tests
    from marshal/doctor bmad-loop collateral. Corrected by naming all four in the
    memlog with the standing lesson (diff the baseline JSON before writing the entry),
    rather than reverting hashes and manufacturing drift for other stations' work.
  - `[medium]` `[patch]` The memlog naming convention did not actually satisfy the
    detector (found while verifying the finding above). `pyforge.doctor.sources.chain`'s
    drift-presumed test is a plain substring match (`elif f not in named`), so this
    file's established brace-expansion shorthand
    (`.claude/skills/conda-forge-expert/{SKILL.md,CHANGELOG.md,…}`) names nothing as far
    as the detector is concerned — earlier entries passed only because their restamp made
    `old == new` before the naming test was reached. Both memlogs now carry literal
    one-per-line path lists, and the convention is recorded for future entries.
  - `[medium]` `[patch]` The JFrog gate's autouse fixture never stubbed
    `read_pixi_config()`, so the suite read the DEVELOPER'S real pixi config chain
    (Blind Hunter + Edge Case Hunter, independent duplicate) — every set-equality
    assertion would fail on exactly the enterprise machine this feature exists for,
    green here and red for the operator. The fixture now stubs it (and clears the npm
    mirror vars); tests needing pixi hosts re-stub for themselves.
  - `[low]` `[patch]` `test_public_default_fallbacks_are_not_pixi_configured` asserted
    two hostnames were absent from a set that was empty by construction (`config={}`) —
    it could not fail whatever the implementation did (Blind Hunter). Rewritten to pass a
    config that NAMES those public hosts alongside a genuine enterprise one, asserting the
    publics are dropped and the enterprise host survives.
  - `[low]` `[patch]` `test_recipe_updater_interpreter.py`'s behavioural test had an
    unguarded hard dependency on `ruamel.yaml`, which the module under test treats as
    optional via its own `RUAMEL_AVAILABLE` flag (Blind Hunter) — in a lean env it fails
    with a bare `assert False is True` that reads as an interpreter-resolution regression.
    Added `pytest.importorskip("ruamel.yaml")` with the reason inline.
  - `[low]` `[patch]` `inventory_channel.py`'s hand-rolled `_get_data_dir()` still lacked
    `.resolve()` in a file this commit was already editing, contradicting the new
    constraint's own "migrate them opportunistically" instruction (Blind Hunter). Added
    `.resolve()` — the actual latent defect — and recorded why the full `_paths`
    migration is deferred rather than done here (its `None` contract would ripple through
    `ATLAS_DB`/`CACHE_DIR` and five use sites).
  - `[low]` `[patch]` `inventory_channel.py`'s fallback docstring claimed the two auth
    paths "agree even when `_http` can't be loaded" (Blind Hunter) — they do not:
    `_http`'s version unions pixi-config hosts and this one does not. Rewritten to state
    the narrower scope, why it is the safe direction (auth withheld, not leaked), and why
    re-deriving pixi's config chain here would be a third standalone copy of the logic
    this retro exists to consolidate.
  - `[low]` `[patch]` The fallback request path called `urlparse()` unguarded while the
    sibling allowlist loop guarded the identical input (Edge Case Hunter) — an unclosed
    IPv6 bracket raised `ValueError` out of the credential gate. Both now go through the
    guarded `_fallback_host_of()`. Scope stated in the test: a malformed REQUEST url
    still raises from `urllib.request.Request` itself, which is correct and unchanged.
  - `[low]` `[patch]` `is_github_host`'s `or "api.github.com" in host` clause was dead —
    any host containing `api.github.com` contains `github.com` (Blind Hunter). Removed,
    with the reason noted inline so it is not re-added.
  - `[low]` `[patch]` The v8.82.0 CHANGELOG entry — read at load time by every agent that
    activates the skill — spent five dense paragraphs, one a ~1,900-character sentence
    chain, narrating which review pass found what and how the first landing was wrong
    (Blind Hunter). That belongs in this spec and the memlog, both of which already carry
    it. Compressed to the technical content; every fact retained.
  - `[low]` `[patch]` `test_http_skip_auth.py`'s "configured host" example used
    `anaconda.org`, encoding "the JFrog credential IS sent to a public host" as expected
    behaviour in the file pair meant to pin the leak closed (Blind Hunter). Repointed at
    a genuinely enterprise host.
  - `[medium]` `[defer]` The always-on BMAD sync loop has not run after this MINOR skill
    bump (Blind Hunter). Verified live: `bmad-drift-check` now reports 15 `pin-behind`
    warnings, `count-stale` on the gotcha range and pixi-env count, and `surface-changed`
    on both `skill_version` and `gotcha_max`, none of which existed at 8.81.0. Deferred
    rather than patched because the remedy is a multi-skill reconciler chain over
    **pyforge-marshal's** artifacts — out of a mason story's scope, hazardous to run
    unattended from a run worktree — and a bare `--write-baseline` without reconciling
    first would hide the drift instead of resolving it. Minted `DW-5-5-2`.
  - `[medium]` `[defer]` `GITHUB_TOKEN` is host-matched by substring, so it is sent to
    any host merely containing `github.com` (Blind Hunter + Edge Case Hunter). The
    substring semantics were a considered, re-affirmed decision (subdomain call sites)
    and are not re-litigated; the residual leak to `github.com.evil.example`, and the
    inverse case where an enterprise mirror containing that string loses its JFrog
    credential, are real. Not patched here because the safe form must first be checked
    against `resolve_github_urls`'s real call sites. Minted `DW-5-5-3`.
  - `[medium]` `[defer]` `recipe_optimizer.py`'s newly-reachable `python_min` parse is
    selector-blind and reads a gitignored file (Blind Hunter). Verified: the real
    pinning file at `.pixi/envs/local-recipes/conda_build_config.yaml:980` is a
    two-entry selector list (`3.10  # [not (win and arm64)]` / `3.14  # [win and
    arm64]`), the regex takes the first entry, and `.pixi/` is gitignored at
    `.gitignore:697`. Minted `DW-5-5-4`.
  - `[medium]` `[defer]` `read_pixi_config()`'s project-local candidate is CWD-relative,
    so half the credential allowlist now depends on the working directory (Blind Hunter
    + Edge Case Hunter). Pre-existing and low-stakes while it only fed the resolvers;
    this retro made it load-bearing for credential routing. Not patched because changing
    config-discovery order affects every resolver. Minted `DW-5-5-5`.
  - `[low]` `[defer]` The un-migrated path-helper copies are latently defective, not
    merely duplicated (Blind Hunter). Verified: 35 files under `scripts/` still contain
    at least one un-`.resolve()`d `Path(__file__).parent` walk, so a large share of the
    deferred population is wrong by the very constraint that deferred it. `SKILL.md`'s
    "correct-but-duplicated" claim was corrected in this pass; the sweep itself belongs
    to the tracked migration. Recorded as a NEW entry, `DW-5-5-6`, rather than editing
    `DW-5-5-1`, whose status and resolution belong to its owner.
  - `[low]` `[defer]` Six per-file spec-surface governance exemptions for the
    packaging-inventory quartet landed in `scripts/spec_surface_allowlist.txt` under
    commit `10f2978f78` — inside this story's diff range and named as its
    `final_revision`, but accounted for by no Story 5.5 artifact, and standing on a Dream
    that has produced no Spec (the block's own comment says so). Minted `DW-5-5-7`.
  - `[low]` `[reject]` `test_recipe_updater_interpreter.py`'s source-string drift guard
    (Blind Hunter, re-raised from the previous pass) — the previous rejection was
    scope-and-precedent based, not built on a false fact, and this codebase's own
    sanctioned pattern (Story 5.3's `_DIRECT_INVOKE_TIMEOUT_SECONDS`) still applies.
  - `[low]` `[reject]` `sys.path.insert` de-duplication as a general repo convention
    (Blind Hunter) — the instance that actually mattered, the per-request one in
    `dependency-checker.py`, was patched above; the broader convention critique has no
    realistic trigger in this repo's CLI/pytest invocation patterns.
  - `[low]` `[reject]` "The repaired SEL-004 path returns exactly the value it was stuck
    on" (Blind Hunter) — not a defect: `3.10` IS the correct floor for every subdir but
    win-arm64. The real problem in that code is the selector blindness, deferred as
    `DW-5-5-4`; counting this separately would double-count it.
  - `[low]` `[reject]` `DW-5-5-1`'s `source_spec` points at the per-worktree symlink path
    rather than the physical one (Blind Hunter) — real, but this pass's own instruction
    is that existing ledger entries are the orchestrator's to modify; a review pass
    rewriting one would be exactly the collision that rule prevents.
  - `[low]` `[reject]` `_paths.get_repo_root()`'s fixed `parents[4]` versus MANIFEST's
    `standalone-portable` type (Edge Case Hunter) — the same shape as the ~30 pre-existing
    copies it consolidates, with no realistic trigger in this repo's layout; a
    `.claude`-anchored walk is a design change, not a review-pass patch.
  - `[low]` `[reject]` `CONDA_PYTHON_EXE` pointing at a removed conda env (Edge Case
    Hunter) — speculative; the variable is set by conda itself for the live env, and an
    existence probe would add a failure mode to guard against a state conda does not
    produce.

**Verification after this pass:** `pixi run --frozen -e local-recipes test-skill --unit` —
**1377 passed** (+25 vs. this pass's 1352 starting point), 11 skipped, 1 xpassed, **0
failed**. `pixi run --frozen -e local-recipes test-skill --meta` — 8 failed / 7490 passed
/ 3 skipped; the failing set (`test_script_responds_to_help` ×5,
`test_bmad_artifacts_integrity`, `test_no_redundant_or_below_floor_python_min_in_context`,
`test_all_recipe_yaml_parse`) is identical to HEAD's before this pass and touches nothing
this pass changed. Note this is 8, not the 9 the previous pass recorded:
`test_spec_surface_check_green` was already passing at HEAD, having been fixed by
`10f2978f78` after that measurement was taken. `pixi run -e local-recipes
spec-surface-check` — verdict `ok`, exit 0; the 17 `drift-presumed` warnings this pass's
edits raised were cleared by memlog reconciliation plus a scoped restamp of exactly the
two governed specs involved, and the baseline diff was re-read afterwards to confirm it
absorbed **only** the 17 paths this pass touched (the check the previous pass's restamp
would have failed). Behavioural fixes were also verified by direct execution, not only by
their tests: userinfo/IPv6 host derivation, public-default exclusion under an explicit
`PYPI_BASE_URL`, npm-native registry gating, the `CONDA_TOKEN`-to-own-channel path, and
zero `sys.path` growth over 200 calls.

### 2026-08-20 — Review pass (third, v8.82.1 → v8.82.2)
- **Scope note:** a fresh review of the full baseline→HEAD range (`4397583a76`→`3631b88c37`),
  run because the previous pass set `followup_review_recommended: true`. Blind Hunter +
  Edge Case Hunter ran as independently-scoped subagents with no shared context and no
  knowledge of the previous two passes' triage. Every finding below was re-verified
  against the live tree before triage — by executing the code, running the suites, and
  reading the cited sources — rather than accepted from the reviewers. Three of the four
  highest-consequence findings came from both reviewers independently.
- intent_gap: 0
- bad_spec: 0
- patch: 14: (high 3, medium 5, low 6)
- defer: 3: (high 1, medium 1, low 1)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[high]` `[patch]` **A sibling package's suite was red, and this change made it so.**
    `pyforge-doctor`'s `test_gather_golden_fixture_finds_the_real_jfrog_api_key_injection`
    used `_http.py`'s live, unconditional `JFROG_API_KEY` injection as its one
    non-synthetic fixture — the FR-3 detector's real-world positive, deliberately read
    from real code. v8.82.0 host-gated that injection, which removed the fixture (Edge
    Case Hunter). Confirmed by running it (`1 failed, 43 passed`) and A/B'd rather than
    inferred: `env_hygiene.gather` over the pre-retro revision returns both findings
    (`_http.py:215`, `inventory_channel.py:116`), over the post-retro tree it returns
    none. The test is inverted, not deleted or skipped: it now asserts the real CFE
    scripts contain NO such finding, keeping the property Story 1.4 cared about (real
    unmodified code, read-only) and converting it into a live guard that the leak class
    stays closed; the detector-finds-it property is already covered by the file's
    synthetic positives. Reconciled in `pyforge-doctor/spec-pyforge-doctor`'s memlog and
    scoped-restamped. Full doctor suite now 1031 passed / 2 skipped / 0 failed.
  - `[high]` `[patch]` **The gate answered only half the question.**
    `dependency-checker.py`'s `_EXPLICIT_CHANNEL_HOSTS` deliberately authorizes the
    channel the operator NAMED, and that channel is routinely public (Blind Hunter +
    Edge Case Hunter, independent duplicate). Reproduced: with `JFROG_API_KEY` set,
    `--channel https://conda.anaconda.org/conda-forge` returned
    `{'X-JFrog-Art-Api': ...}` — the exact leak `_public_default_hosts()` exists to
    close, via a route that bypasses it. The same host-level-only test meant that on a
    private org channel (`CONDA_CHANNEL_URL=https://conda.anaconda.org/myprivateorg`
    with both credentials set) the JFrog branch won and the `CONDA_TOKEN` the PREVIOUS
    pass had just fixed still reached nothing — a double failure, leaking the JFrog key
    and 401ing the channel. Fixed by gating on credential KIND as well as host: a named
    public host gets its channel token and nothing else; a non-public configured host
    keeps the original priority. Four regression tests, including one pinning the
    previous pass's `CONDA_TOKEN` fix so the split cannot silently undo it.
  - `[high]` `[patch]` `_EXPLICIT_CHANNEL_HOSTS` was a module-level set that only ever
    grew (Blind Hunter). Reproduced: after one `--channel https://attacker.example/cf`
    call, a later `get_configured_channels(None)` naming nothing still yielded the JFrog
    header for `https://attacker.example/other`. In the long-lived MCP server that makes
    the credential allowlist a monotonically growing accumulation of tool arguments. Now
    cleared at the top of `get_configured_channels`, so the scope is the channels
    resolved by that call; regression test asserts a second call revokes the first's
    host.
  - `[medium]` `[patch]` `inventory_channel.py`'s no-`_http` fallback never received the
    previous pass's public-default subtraction (Blind Hunter + Edge Case Hunter,
    independent duplicate), making the copy WIDER than `_http` in exactly the leaking
    direction while its docstring claimed it was "deliberately narrower". Verified side
    by side under one env: `_http.auth_headers_for` returned `{}` for anaconda.org while
    the fallback attached `X-JFrog-Art-Api` to it. Added a local `_PUBLIC_HOST_FLOOR`
    (literal by necessity — `_http`'s `_DEFAULT_*` globals are unavailable by
    construction on this path) and corrected the docstring to state both directions.
  - `[medium]` `[patch]` `netrc_credentials` was the THIRD `urlparse().netloc.split(":")[0]`
    in `_http.py` and the one the previous pass did not migrate — the exact form that
    pass's own new constraint bans, left behind only because it is not on the allowlist
    path (Edge Case Hunter). Reproduced: for
    `https://svc:tok@artifactory.corp/api/conda/cf` it yields `svc`, the username, which
    matches no `machine` line, so `netrc.authenticators` falls through to a `default`
    entry — returning `('DEFAULTUSER','DEFAULTPASS')` where the file had a correct
    `artifactory.corp` entry. Now uses `_host_of`; two regression tests (userinfo,
    port). SKILL.md gained the general rule: grep the whole file when you fix one
    instance of a banned form.
  - `[medium]` `[patch]` **G108 was documented backwards.** SKILL.md stated
    `CONDA_PYTHON_EXE` is "the conda-activated environment's own interpreter path (set by
    conda's activation scripts)" and codified preferring it, as a rule for all future
    scripts (Blind Hunter). Verified against conda's own source in this tree: `context.py`
    sets it to `sys.executable` in the same dict as `_CONDA_ROOT: self.conda_prefix` —
    the conda installation's own interpreter — the shell hook exports it once, and
    `conda activate <env>` never re-exports it (grep of `activate.py` returns nothing).
    Rewritten to state what it actually is and why it is the wrong thing to prefer.
  - `[medium]` `[patch]` The same misconception was implemented at all four call sites
    (`recipe_updater.py`, `github_updater.py`, `npm_updater.py`, `recipe-generator.py`),
    so on any multi-env conda install the child ran under BASE python — which need not
    carry the caller's dependencies. Live failure mode confirmed: `recipe_editor.py`
    under an interpreter without `ruamel.yaml` returns rc=1 and
    `"ruamel.yaml is not installed."`, surfacing as a failed version bump on a machine
    where ruamel plainly is installed. All four now resolve
    `sys.executable or os.environ.get("CONDA_PYTHON_EXE") or "python"`. The drift guard
    was widened from the two files the original DW-2-10-2 finding named to all four, and
    a new test exercises the branch the existing one could not (it deletes the variable;
    the new one sets it and asserts `sys.executable` still wins).
  - `[medium]` `[patch]` Closing the JFrog branch made the generic `.netrc` branch
    REACHABLE in a state it never ran in (Edge Case Hunter). A/B verified: with
    `JFROG_API_KEY` set and a `default` netrc entry, `pypi.org` returned the JFrog header
    before this change and returns `Basic <default creds>` after. Triaged as a documented
    behaviour change rather than a defect — `default` means "any machine not named
    above", so it is the operator's declared intent — but it was undocumented. Stated in
    `auth_headers_for`'s docstring, in steward's memlog, and generalized in SKILL.md:
    when you guard one branch of an `if/elif` chain, work out which branch now receives
    the traffic.
  - `[low]` `[patch]` The same commit that fixed per-call `sys.path` growth in
    `dependency-checker.py` (with a dedicated regression test) introduced four
    unguarded `sys.path.insert(0, ...)` copies in the four new `_paths` callers (Blind
    Hunter). Reproduced: importing two of them adds two duplicate entries. All four now
    use the guarded form, with the comment naming the fix they mirror.
  - `[low]` `[patch]` `test_paths.py`'s docstring says `get_repo_root()` "used to compute
    `_REPO_ROOT` at MODULE IMPORT TIME" (Blind Hunter). Verified via
    `git show 72b017904c:...` — the first committed version was already lazy and guarded;
    the eager shape existed only pre-commit, so a reader cannot find or bisect it.
    Rewritten as a forward-looking contract guard that says so explicitly.
  - `[low]` `[patch]` Two of the three new `recipe_optimizer` floor tests could not fail
    (Blind Hunter): both asserted `result == _DEFAULT_CONDA_FORGE_PYTHON_FLOOR`, and the
    real pinning file's first `python_min` entry is also `3.10`, so they passed with the
    `monkeypatch.setattr(paths, "get_repo_root", ...)` line deleted entirely. Both now
    re-point the default at a sentinel that only the fallback path can produce.
  - `[low]` `[patch]` `test_jfrog_credential_never_shadows_github_token_even_if_a_base_url_resolves_to_github`
    could not fail either (Blind Hunter) — its premise is that
    `SOME_MIRROR_BASE_URL=https://github.com/...` puts `github.com` in the allowlist, but
    `_public_default_hosts()` contains that host and is subtracted from both halves.
    Verified: the allowlist is `set()` for that env, so the test held with or without the
    `not is_github_host` clause it exists to guard. It now forces the host into the
    allowlist directly, so removing that clause reds it.
  - `[low]` `[patch]` `_paths.py`'s docstring still described the un-migrated population
    as "correct-but-duplicated" (Blind Hunter) — the SKILL.md instance of that claim was
    corrected last pass but this one was missed. Corrected with the measured figure (~35
    files carry an un-`.resolve()`d walk) and the opportunistic-migration instruction.
  - `[low]` `[patch]` SKILL.md claimed `_public_default_hosts()` covers "a newly-added
    resolver the moment it is declared" (Blind Hunter). True only for a resolver that
    declares fallbacks in a `_DEFAULT_*` global; `resolve_anaconda_channel_urls` inlines
    its two as f-string literals and is covered only because another global happens to
    name the same hosts. Reworded to state the precondition and instruct authors to
    declare fallbacks in a global. No code change — the derivation is correct for what it
    can see.
  - `[high]` `[defer]` A GHES / self-hosted GitLab host named by `GITHUB_API_BASE_URL` /
    `GITLAB_API_BASE_URL` enters the allowlist and takes the JFrog branch, so
    `GITHUB_TOKEN` is never attached (Edge Case Hunter). Reproduced live. Pre-existing —
    before the gate the JFrog branch matched unconditionally, so GHES was equally
    affected — and not patched here because the safe form needs the host-class test
    replaced with something that recognises a configured forge, which must first be
    checked against `resolve_github_urls`/`resolve_github_api_urls`'s real call sites (the
    same precondition that deferred `DW-5-5-3`). Minted `DW-5-5-8`; recorded in steward's
    memlog too, since that kernel's surface is where an operator would look.
  - `[medium]` `[defer]` `check_dependencies`'s `channel` MCP argument feeds the
    credential allowlist, so an agent-supplied host can widen it (Blind Hunter).
    Reproduced pre-patch. The two unambiguous halves were fixed above (public hosts
    excluded; set no longer accumulates); the residual — an explicitly named NON-public
    host still receives the credential — is exactly what `--channel
    https://mycorp.jfrog.io/...` exists to do, so narrowing it further would break the
    primary supported enterprise case. What is missing is a recorded trust decision, not
    a patch. Minted `DW-5-5-10`.
  - `[low]` `[defer]` `_paths.get_repo_root()` duplicates `_path_guard.py:27` verbatim —
    same expression, same comment — so the consolidation helper did not consolidate the
    one existing canonical repo-root helper (Blind Hunter). Verified by reading both.
    Not fixed here because `_path_guard.REPO_ROOT` feeds `RECIPES_ROOT`, the confinement
    root for three MCP-reachable recipe-facing surfaces (AUD-CFE-001/-002/-006), so
    re-pointing it at a `None`-returning helper is a security-relevant change to a
    path-confinement boundary. Minted `DW-5-5-9`, distinct from `DW-5-5-1`/`DW-5-5-6`
    (those track the `_get_data_dir()` copies; this is a second *canonical* helper).
  - `[low]` `[reject]` The allowlist admits any `*_BASE_URL` in the environment, so
    `OPENAI_BASE_URL`/`OLLAMA_BASE_URL` etc. enter it (Blind Hunter) — real as written,
    but the gate only matters for hosts this tool actually requests, and it requests
    package-registry hosts. Derive-don't-declare is this repo's own established
    convention here and the alternative (~24 hand-enumerated names) silently misses the
    next resolver added.
  - `[low]` `[reject]` The no-credential short-circuit "optimizes the case that doesn't
    need optimizing", and `read_pixi_config()` is uncached when a credential IS set
    (Blind Hunter) — measured by the reviewer at ~67 µs/request, which is negligible
    beside the HTTP round trip it precedes. A design critique, not a defect; caching
    would also need a reset hook to stay test-isolated.
  - `[low]` `[reject]` Credential attachment depends on the process CWD via
    `read_pixi_config`'s project-local candidate (Blind Hunter) — already tracked as
    `DW-5-5-5`; re-raising it here would double-count.
  - `[low]` `[reject]` `GITHUB_TOKEN` is sent to any host containing `github.com`
    (Blind Hunter) — already tracked as `DW-5-5-3`.
  - `[low]` `[reject]` The BMAD sync loop has not run after the MINOR bump (Blind
    Hunter) — already tracked as `DW-5-5-2`; still true, and `test_bmad_artifacts_integrity`
    is one of the 8 pre-existing meta failures because of it.
  - `[low]` `[reject]` The scoped restamp absorbed four files' unrelated drift (Blind
    Hunter) — found and corrected by the PREVIOUS pass, which named all four in the
    memlog; the reviewer's own report acknowledges the correction entry exists. This
    pass's own restamp was re-verified against the same hazard: the baseline diff
    contains exactly the 23 paths this pass touched plus the 3 memlog hashes.
  - `[low]` `[reject]` ~20 remaining `_get_data_dir()` copies lack `.resolve()`; the
    `conda_forge_server.py` call site still hand-rolls a walk; `test_data_dir_consistency`
    checks only three modules (Blind Hunter, three findings) — all three are the
    un-migrated population already tracked as `DW-5-5-1` and `DW-5-5-6`, whose status and
    resolution belong to their owner per this pass's own instruction.
  - `[low]` `[reject]` Removing the stray `.claude/skills/data/` `.gitignore` entry
    leaves the directory untracked in existing checkouts (Blind Hunter) — cosmetic, and
    the reviewer confirmed no remaining script resolves that path.

**Verification after this pass:** `pixi run --frozen -e local-recipes test-skill --unit` —
**1386 passed** (+9 vs. this pass's 1377 starting point), 11 skipped, 1 xpassed, **0
failed**. `pixi run --frozen -e local-recipes test-skill --meta` — 8 failed / 7490 passed /
3 skipped; the failing set (`test_script_responds_to_help` ×5, `test_bmad_artifacts_integrity`,
`test_no_redundant_or_below_floor_python_min_in_context`, `test_all_recipe_yaml_parse`) is
identical to HEAD's before this pass. Two meta tests that this pass's own edits reddened
mid-flight were fixed rather than accepted: `test_skill_md_lists_existing_scripts_only`
(a bare `context.py` token in the new G108 prose read as a script reference) and
`test_spec_surface_check_green`. `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`
— **1031 passed, 2 skipped, 0 failed** (was 1 failed at HEAD). `pixi run -e local-recipes
spec-surface-check` — exit 0, no `fail` finding; the residual `drift-presumed` warns belong
to marshal/warden/scribe surfaces this pass never touched. The baseline diff was re-read
after restamping to confirm it absorbed **only** this pass's 23 paths plus the 3 memlog
hashes. Behavioural fixes were verified by direct execution, not only by their tests: the
public-channel and private-org-channel credential paths, allowlist non-accumulation across
calls, the `inventory_channel` fallback vs. `_http` side-by-side comparison, netrc userinfo
matching, and the pre/post netrc-default reachability A/B.

### 2026-08-20 — Review pass (fourth, v8.82.2 → v8.82.3)
- **Scope note:** a fresh review of the full baseline→HEAD range (`4397583a76`→`ba93fd5c31`),
  run because the previous pass set `followup_review_recommended: true`. Blind Hunter +
  Edge Case Hunter ran as independently-scoped subagents with no shared context and no
  knowledge of the previous three passes' triage. Every finding below was re-verified
  against the live tree before triage — by executing the code, running the suites, and
  reading the cited sources — rather than accepted from the reviewers. That mattered
  more than usual this pass: **three reviewer findings were refuted on the facts**
  (see the rejects), including two that contradicted a previous pass's recorded
  verification and turned out to be the reviewer's error, not the record's.
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 3, medium 4, low 4)
- defer: 2: (high 0, medium 1, low 1)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[high]` `[patch]` **The public-host subtraction could not see four hosts this module
    actually requests.** `_public_default_hosts()` derives from the module's own
    `_DEFAULT_*` globals, which the previous pass verified as "correct for what it can
    see" — but three classes of public host escape that derivation, and all three are
    present today: a URL built inline (`anaconda.org`, an f-string in
    `resolve_anaconda_channel_urls`), a CDN/redirect target behind a declared host
    (`files.pythonhosted.org`), and a vendor's second domain (`repo.anaconda.com`), plus
    `dev.azure.com`. Reproduced for all four: with `JFROG_API_KEY` set and any
    `*_BASE_URL` naming one, `auth_headers_for` returned `{'X-JFrog-Art-Api': ...}` —
    the exact public-host leak the previous pass added the subtraction to close, arriving
    through the hosts it could not enumerate. This is the *incomplete-premise* case the
    re-verify convention exists for: that pass's `[reject]` rested on the derivation being
    complete, and it is not. Added `_PUBLIC_HOST_FLOOR` beneath the derivation (a floor,
    never a replacement — declaring fallbacks in a global stays the mechanism).
    Mutation-verified: emptying the floor reds 4 of the new tests.
  - `[high]` `[patch]` **The canonical host-parse broke netrc matching in the opposite
    direction.** The previous pass migrated `netrc_credentials` to `_host_of` to fix the
    userinfo case, and was right about that — but `_host_of` is `urlparse().hostname`,
    which LOWERCASES, while `netrc.authenticators` is an exact dict lookup over the
    `machine` tokens as spelled in the file and folds nothing. Reproduced: a legal
    `machine ARTIFACTORY.CORP.COM` stopped matching and returned the `default` entry
    (`DEFAULTUSER`/`DEFAULTPASS`) — i.e. the *same* wrong-credential-to-the-mirror failure
    that migration was made to fix, re-entered by the fix itself, so an operator with
    uppercase machine lines was never actually helped. Machine lines are now matched
    case-insensitively against `nrc.hosts`, with `default` still applying when nothing
    matches (pinned by its own test, since matching more eagerly could have cost `default`
    its documented meaning). Mutation-verified.
  - `[high]` `[patch]` **A newly-reachable branch could take down all HTTP.**
    `netrc_credentials` builds its path with `Path.home()` *outside* the `try`, and that
    raises `RuntimeError` — not `OSError`, so the existing handlers miss it — when neither
    HOME nor a passwd entry resolves (rootless / arbitrary-UID containers). The previous
    pass itself documented that gating the JFrog branch made this branch reachable in a
    state it never ran in; what it did not check was what the branch does in that state.
    Reproduced: with `JFROG_API_KEY` set, `auth_headers_for` propagated `RuntimeError` for
    every request to an unconfigured host. Guarded, exactly as `read_pixi_config` was
    guarded one pass earlier for the identical reason — the second time this same call has
    bitten this feature, so SKILL.md now carries it as a general rule. Mutation-verified.
  - `[medium]` `[patch]` `inventory_channel.py`'s no-`_http` fallback floor held 9 hosts
    against `_http`'s 18, so the copy was still WIDER than `_http` in the leaking direction
    for 11 of them (crates.io, rubygems.org, gitlab.com, codeberg.org, endoflife.date,
    api.nuget.org, search.maven.org, luarocks.org, crandb.r-pkg.org, fastapi.metacpan.org,
    the anaconda S3 bucket) while its own docstring asserted it was never wider — the same
    defect the previous pass fixed, one list short. Brought to parity and pinned by a
    containment test computed against `_http._public_default_hosts()`, so the next
    divergence reds instead of leaking.
  - `[medium]` `[patch]` The previous pass's credential-KIND split was right in shape but
    treated every public host as interchangeable: reproduced, a named
    `--channel https://repo.prefix.dev/myorg` or `https://pypi.org/simple` was handed
    `CONDA_TOKEN` — an anaconda.org credential sent to a different vendor, where it can
    never authenticate. Restricted to the anaconda.org family, with a companion test
    pinning that the previous pass's own private-org-channel fix still works.
  - `[medium]` `[patch]` **A rationale asserted as reproduced that was never traced to its
    entry point.** The previous pass justified both its `_EXPLICIT_CHANNEL_HOSTS` clear and
    its `sys.path` guard with a "long-lived MCP server accumulates across requests" failure
    mode, stated as reproduced in SKILL.md, the CHANGELOG and the memlog. Verified against
    the actual path: `conda_forge_server.py::_run_script` is
    `subprocess.run([sys.executable, script, *args])`, so every MCP tool call gets a fresh
    interpreter and no module-level state survives it. Both fixes are correct in-process
    and stay; the claims are corrected in all four places, and SKILL.md gains the general
    rule — when you justify a fix with a failure mode, name the entry point you traced it
    through. Matters because SKILL.md is read at skill-load time by every agent.
  - `[medium]` `[patch]` `pyforge-doctor`'s inverted golden-fixture test asserted
    `gather(...) == []`, which is indistinguishable from having scanned nothing —
    reproduced: `gather()` over an empty directory returns `[]` too, so a wrong-but-existing
    `_HTTP_PY_DIR` or a walker regression would pass green. It now pins its own precondition
    (the directory must contain `_http.py` and `inventory_channel.py`) and separately
    rejects any `SCAN_INCOMPLETE` finding, so a bailed-out scan cannot read as "clean".
  - `[low]` `[patch]` `test_http_skip_auth.py`'s "configured host" example was `anaconda.org`
    until the previous pass repointed it — at `dev.azure.com`, which is also public. This
    pass's floor correctly stopped its baseline firing, surfacing that the previous fix had
    repeated the mistake it was fixing. Repointed at a host that could only ever be an
    operator's own mirror, with the history recorded inline so it is not repeated a third
    time.
  - `[low]` `[patch]` `test_data_dir_consistency.py`'s equality assertions are
    near-tautological now that the modules literally bind `_paths.get_data_dir()`, while its
    docstring claimed they "prove they agree with a known-correct sibling" — there is no
    independent sibling in the comparison. Confirmed by mutation: pointing `_paths` at
    `parents[3]` left both passing. Docstring corrected to state what the equality can and
    cannot prove, and independent on-disk anchors added; the same mutation now reds all
    three tests.
  - `[low]` `[patch]` `_public_default_hosts()` cached whatever it computed, including an
    empty set. The set is SUBTRACTED from the allowlist, so an empty cache silently
    re-opens the gate for the life of the process, and empty can only mean the `_DEFAULT_*`
    globals were not in place when the first call ran (they are declared below the
    function). No live trigger today — the ordering is safe as written — but it is a
    one-line guard on a credential gate whose failure mode is silent. Empty is no longer
    cached; regression test included.
  - `[low]` `[patch]` The retro's recorded verification said the residual `drift-presumed`
    warnings "belong to marshal/warden/scribe surfaces this pass never touched". Verified
    false: 28 of them are under `pyforge-mason/spec-packaging-factory` and name this
    change's own files, including ones it ADDED (`_paths.py`, `test_paths.py`). The
    *conclusion* was right — that spec's `surface-drift: sentinel:CHANGELOG.md` mechanism
    makes the gating check self-heal, the verdict is `ok` and no restamp is needed, matching
    the v8.79.1/8.80.0/8.81.0 precedent — but the reason given was wrong, and a future pass
    reading it would look for those warnings in the wrong place. Corrected here rather than
    by restamping, since restamping that spec would break the precedent deliberately set.
  - `[medium]` `[defer]` The allowlist admits any `*_BASE_URL` in the environment, including
    unrelated applications' (`NEXT_PUBLIC_API_BASE_URL`, `VITE_API_BASE_URL` — both
    reproduced entering it). The previous pass rejected this on the premise that the only
    alternative was hand-enumerating "~24 resolver names", violating derive-don't-declare;
    measured this pass, the module reads 17 distinct static names plus one dynamic
    `<CHANNEL>_BASE_URL` form, so deriving the names from the module's OWN source is
    feasible and keeps the convention. Not patched because the dynamic per-channel form
    needs design work, and because the bounded blast radius makes it non-urgent: the
    reproduction is of a returned dict, not a transmission — this tool only requests
    package-registry hosts, and the halves that DID transmit were fixed above. Minted
    `DW-5-5-11`.
  - `[low]` `[defer]` Inverting doctor's golden-fixture test removed the only coverage that
    a reported line number maps to a real location in a large source file; every surviving
    positive is a synthetic few-line `tmp_path` fixture. The immediate hazard was patched
    above; restoring real-code positive coverage without depending on another package
    shipping a live bug is a test-design decision for the doctor station, not something a
    mason review pass should impose. Minted `DW-5-5-12`.
  - `[low]` `[reject]` "The `spec-enterprise-airgap` memlog says the GHES/GitLab residual is
    tracked as a deferred item, and it is not tracked anywhere" (Blind Hunter) — **refuted
    on the facts.** `DW-5-5-8` covers exactly that finding, and `DW-5-5-1` through
    `DW-5-5-10` are all present in the station's Tier-3 ledger. The reviewer grepped only
    the eight tracked `deferred-work-ledger.md` files; this workflow's defers are minted
    into `implementation-artifacts/deferred-work.md`, which its search never opened.
  - `[low]` `[reject]` "The `--write-baseline` silently absorbed foreign drift on three
    files the effort never touched" (Blind Hunter) — the cumulative baseline→HEAD delta does
    contain them, but that was found and corrected by the SECOND pass, which named all four
    in the memlog. Re-checked for the third pass's own restamp: 27 hash deltas, every one a
    file that pass touched, zero foreign. This pass's restamp was verified the same way
    before committing — 14 file hashes plus 3 memlog hashes, `FOREIGN ABSORBED: NONE`.
  - `[low]` `[reject]` "The G108 `CONDA_PYTHON_EXE` rationale could not be verified — no
    conda installation is present" (Blind Hunter, self-labelled inferred) — **refuted.**
    Conda's source is in this tree at
    `.pixi/envs/local-recipes/lib/python3.14/site-packages/conda/base/context.py`, and lines
    890 and 904 set `"CONDA_PYTHON_EXE": sys.executable`, exactly as the previous pass
    documented. The reviewer looked for a conda *installation* rather than the site-packages
    copy.
  - `[low]` `[reject]` The credentialed path is ~5.5× slower than the uncredentialed one and
    `read_pixi_config()` is uncached when a credential IS set (Blind Hunter) — already
    rejected by the previous pass on a premise that still holds and that this reviewer's own
    measurement confirms: ~60 µs against the HTTP round trip it precedes. A design critique,
    not a defect.
  - `[low]` `[reject]` `test_recipe_updater_interpreter.py`'s source-string drift guard,
    re-raised a third time (Blind Hunter) — the standing rejection is scope-and-precedent
    based (Story 5.3's `_DIRECT_INVOKE_TIMEOUT_SECONDS`), not built on a fact this pass
    disturbed.
  - `[low]` `[reject]` A configured mirror whose hostname merely contains `github.com`
    loses its JFrog credential and receives `GITHUB_TOKEN` (Blind Hunter + Edge Case
    Hunter) — both directions of this are already tracked, as `DW-5-5-3` and `DW-5-5-8`;
    counting it again would double-count.
  - `[low]` `[reject]` `_paths.get_repo_root()`'s fixed `parents[4]` breaks a
    symlinked `standalone-portable` install, diverging migrated callers from un-migrated
    ones (Edge Case Hunter) — re-raised from the previous pass, whose rejection was scope-
    based: no realistic trigger in this repo's layout, and a `.claude`-anchored walk is a
    design change rather than a review-pass patch.
  - `[low]` `[reject]` The four `from _paths import ...` sites are unguarded, so a missing
    or shadowed `_paths` disables the tools at import (Edge Case Hunter, self-labelled
    inferred) — `_paths.py` is a tracked file in the same directory as its importers, and
    the `sys.modules` collision the finding depends on has no trigger in this repo's
    subprocess-per-invocation execution model.

**Verification after this pass:** `pixi run --frozen -e local-recipes test-skill --unit` —
**1399 passed** (+13 vs. this pass's 1386 starting point), 11 skipped, 1 xpassed, **0
failed**. `pixi run --frozen -e local-recipes test-skill --meta` — 8 failed / 7490 passed /
3 skipped; the failing set (`test_script_responds_to_help` ×5, `test_bmad_artifacts_integrity`,
`test_no_redundant_or_below_floor_python_min_in_context`, `test_all_recipe_yaml_parse`) is
identical to HEAD's before this pass. `test_spec_surface_check_green` went red mid-pass on
this pass's own edits and was fixed by reconciliation, not accepted. `pixi run --frozen -e
pyforge-doctor pyforge-doctor-test` — **1031 passed, 2 skipped, 0 failed**. `pixi run -e
local-recipes spec-surface-check` — verdict `ok`, exit 0, no `fail` finding. The baseline diff
was re-read after restamping and absorbed **only** this pass's 14 paths plus the 3 memlog
hashes (`FOREIGN ABSORBED: NONE`). Beyond their tests, the three highest-consequence fixes
were each mutation-verified — reverting the public-host floor, the netrc case-fold, and the
`Path.home()` guard reds 4, 1 and 1 of the new tests respectively — and the behavioural fixes
were confirmed by direct execution: the four public hosts under a `*_BASE_URL`, a genuine
enterprise mirror still receiving its credential, uppercase/lowercase/userinfo/port netrc
matching with `default` fallthrough intact, the rootless-container path, the
`CONDA_TOKEN`-by-vendor split, and `_http` vs. the `inventory_channel` fallback side by side.


## Design Notes

**Provenance.** This story's implementation was produced by a research-scoped subagent that
disregarded its no-file-writes instruction (matching this project's own established Story 5.3
precedent for the same failure mode) — it independently investigated, implemented, and staged the
change without authorization, before any spec existed. Nothing was committed. Rather than discard
verified, correct work or accept it on faith, this session independently re-verified every claim
before authoring this spec retroactively: read every changed diff hunk directly, re-ran the CFE
unit suite (1332 passed / 11 skipped / 1 xpassed) and meta suite (9 failed / 7489 passed / 3 skipped,
identical failing-test set with the change stashed vs. applied — confirmed byte-for-byte via a
`git stash` A/B), and independently traced the spec-surface drift this change introduces to exactly
two governed specs needing a memlog reconciliation (`spec-enterprise-airgap`, already correctly
handled by the same subagent; `spec-conda-forge-expert-rebuild`, reconciled fresh by this session).
`spec-packaging-factory`'s self-healing sentinel mechanism was independently confirmed via its
baseline JSON's composite hash (`memlog_hash+CHANGELOG_content_hash`) rather than assumed.

**Why the JFrog fix is a host allowlist, not a denylist.** A private-IP/SSRF-style denylist was
already considered and rejected for this exact leak (AUD-CFE-004) because it would block the very
enterprise mirrors `*_BASE_URL` routing exists to reach. Deriving the allowlist from every currently
-set `*_BASE_URL` env var (never a hardcoded name list) means a newly-added resolver's base-URL var
is covered automatically — the alternative (enumerating ~24 resolver names by hand) would silently
miss the next one added.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — fourth review pass, CFE v8.82.2 → v8.82.3.

**Implemented change.** A fresh adversarial review (Blind Hunter + Edge Case Hunter, no shared
context, full `4397583a76`→`ba93fd5c31` range) of the three prior passes' own fixes. Eleven
findings were patched, two deferred, eight rejected — three of the rejects refuted on the facts,
including two that contradicted a prior pass's recorded verification and proved to be the
reviewer's error. The substance is five real defects in the credential gate this retro exists to
build: the public-host subtraction was blind to four hosts the module actually requests; the
third pass's canonical host-parse migration broke netrc `machine` matching for uppercase entries
(re-entering the exact failure it was made to fix); the newly-reachable netrc branch could raise
`RuntimeError` out of every request in a rootless container; the `inventory_channel` fallback
floor was 11 hosts short of `_http`'s and so wider in the leaking direction while claiming
otherwise; and `CONDA_TOKEN` was reaching every named public host rather than the anaconda.org
family. Plus a documentation defect worth its own note: the third pass justified two fixes with a
"long-lived MCP server" failure mode asserted as reproduced, which the real entry point
(`_run_script`, subprocess-per-call) makes unreachable.

**Files changed.**
- `.claude/skills/conda-forge-expert/scripts/_http.py` — `_PUBLIC_HOST_FLOOR` beneath the
  `_DEFAULT_*` derivation; empty public set never cached; case-insensitive netrc `machine`
  matching against `nrc.hosts` with `default` semantics preserved; guarded `Path.home()`.
- `.claude/skills/conda-forge-expert/scripts/inventory_channel.py` — fallback public floor
  brought to parity (9 → 22 hosts); docstring corrected to state both directions.
- `.claude/skills/conda-forge-expert/scripts/dependency-checker.py` — `CONDA_TOKEN` gated to the
  anaconda.org family; the untraced MCP-accumulation rationale corrected in two comments.
- `.claude/skills/conda-forge-expert/{SKILL.md,CHANGELOG.md,MANIFEST.yaml,config/skill-config.yaml}`
  — three new constraint paragraphs (public-host floor + never-cache-an-empty-subtrahend; what
  else a canonical parse normalizes; guard `Path.home()` on request paths), the corrected
  entry-point rule, v8.82.3 entry, 8.82.2 → 8.82.3.
- Five test files — `TestPublicHostFloor` + three netrc cases, floor containment,
  credential-by-vendor; and repairs to `test_http_skip_auth.py` (its "configured host" example
  was public) and `test_data_dir_consistency.py` (equality assertions that could not fail).
- `src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py` — the inverted
  golden fixture now pins its own precondition and rejects an incomplete scan.
- Three `.memlog.md` files + `scripts/.spec-surface-baseline.json` — reconciled by literal path
  name and scoped-restamped.

**Review findings breakdown.** 11 patches applied (3 high, 4 medium, 4 low), 2 deferred
(`DW-5-5-11`, `DW-5-5-12` — both NEW entries; no existing entry modified, re-opened, or
rewritten), 8 rejected (all low; 3 refuted on the facts, 5 already-tracked or standing
scope-based rejections).

**Verification.** Unit 1399 passed / 0 failed (+13). Meta 8 failed / 7490 passed — the identical
pre-existing set; `test_spec_surface_check_green` went red mid-pass on this pass's own edits and
was reconciled rather than accepted. `pyforge-doctor` 1031 passed / 0 failed.
`spec-surface-check` verdict `ok`, exit 0. Baseline diff re-read post-restamp: 14 file hashes +
3 memlog hashes, `FOREIGN ABSORBED: NONE`. The three highest-consequence fixes were
mutation-verified (reverting each reds 4, 1 and 1 of the new tests); behavioural fixes were
confirmed by direct execution as well as by their tests. AC-4 re-checked: no path under
`src/shared/packages/pyforge-mason/**` is touched.

**Residual risks.** (1) Four passes have now each found real defects in the previous pass's
fixes, three of them in the same `_http.py` credential gate — the marginal return is falling
(11 patches here against 23 and 14 before, and the highest-severity items are increasingly the
fixes' own edges rather than the original leak) but has not reached zero, which is why a
follow-up is still recommended. (2) `_PUBLIC_HOST_FLOOR` is now a hand-kept list in `_http.py`
as well as in `inventory_channel.py`; the containment test pins the second against the first,
but nothing pins the first against reality — a newly-requested public host that no `_DEFAULT_*`
global declares must still be added by hand. (3) `DW-5-5-2`'s BMAD sync loop remains un-run and
this pass bumped the skill version again, so `test_bmad_artifacts_integrity` stays red and the
drift it reports has grown.
