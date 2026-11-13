---
title: "37.4: Mason's change closes: retro, surface reconcile, deferrals and ledger"
type: 'chore'
created: '2026-11-10'
status: 'done'
blocking_condition: 'forward dependency (2026-11-10): Deps S-38.1, S-38.2, S-38.3, S-39.1 are later epics; the operator unblocks it once they are done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-5-4-free-inheritance-verification.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-5-4-free-inheritance-verification-2.md
  - docs/dreams/pyforge-mason.md
  - docs/foundry/capability-ledger.yaml
  - scripts/deferred_work_intake.py
  - scripts/fleet_scan.py
surface:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/retros/retro-pyforge-mason-2026-11-*.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-5-4-free-inheritance-verification.md
  - docs/dreams/pyforge-mason.md
deferred:
  - id: open-mason-deferrals-untriaged
    summary: "108 open mason deferrals are untriaged against what has shipped since; 72 carry no severity. Counted by the 2026-11-10 audit; the burn-down is a Dream-sized effort of its own, as the 2026-10-01 campaign was."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
    severity: low
  - id: two-story-specs-carry-a-2-suffix
    summary: "Two mason story specs carry a `-2` suffix no ledger key has (spec-2-5-mason-recipe-validate-2.md, spec-5-4-free-inheritance-verification-2.md); CHAIN-STANDARD section 5 names a story spec by its key exactly. Both are entries in docs/governance/flag-rule-baseline.json, which only scripts/flag_rule_baseline.py writes, so a rename needs that script's pass."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-5-4-free-inheritance-verification-2.md
    severity: low
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-38.1, S-38.2, S-38.3, S-39.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** The chain steps every story owes but no build agent may take alone: one memlog writer reconciles the surface of five code and test stories; the deferral rows the story specs carry enter the ledger through the intake; the ledger keys move through the Tier-3 feed. Story 38.2's `pyproject.toml` edit is the package's `code` stage for the currency sweep, so a mason retro dated within two days is owed. Two records the audit found wrong close here: Story 5.4's first spec says blocked while its ledger key says done, and `DW-mason-25-2-3` sits open beside CAP-35's marker.

**Approach:**
- Runs last in the station; never dispatched beside another mason story.
- (1) The retro, through `bmad-retrospective` over Epics 37 to 39, saved as `retros/retro-pyforge-mason-<date>.md` with `updated: <date>`.
- (2) One memlog edit appending a `Surface reconcile <date>:` event per moved path, from `git diff --name-only origin/main...HEAD`, naming in full every tracked path the widened `surface:` newly governs that this PR did not change (the `.claude/skills/mason-*/**` files and `scripts/cfe_rebuild_guard_check.py`), so none reads `drift-presumed`. Doctor Story 58.4 runs the scoped stamp once, after the last edit.
- (3) This story writes its own two rows (Notes) to its `deferred:`, then runs `python scripts/deferred_work_intake.py --fix --project mason` in the pyforge-guild environment for this station's story specs (Stories 37.1, 38.3 and 39.1 write their rows at build; every story spec carries `deferred: []` at mint).
- (4) Story 5.4's first spec to `status: 'superseded'` with a pointer to the recheck spec (its ledger key stays done); `DW-mason-25-2-3` judged on its evidence: closed with the commits that prove it, or open with a dated note of what remains.
- (5) One closing Realization-log line on `docs/dreams/pyforge-mason.md`, `- **<date> (cutover readiness, closed)** — ...` (CHAIN-STANDARD § 3 step 7).
- (6) Ledger: story promotion to `done` for every story of this change runs once per project in the CLOSE-LEDGERS job (Tier-3 feed, then `sprint-ledger-sync -- --project mason`, then `story-status-check`); this story does not write `sprint-status-ledger.yaml`. Story 39.2 stays `blocked`.

Ledger key: `37-4-mason-s-change-closes-retro-surface-reconcile-deferrals-and-ledger`.
Ledger status: `blocked` (forward dependency, 2026-11-10; unblocked only with operator confirmation once its later-epic deps are done).
Type / Effort / Deps: chore / M / S-37.1, S-37.2, S-37.3, S-38.1, S-38.2, S-38.3, S-39.1.

### Living CAP citations

- The chain close for `spec-pyforge-mason` (CHAIN-STANDARD § 3 step 7); no CAP and no FR.
- The ledger-mode check reads control-plane's regenerated `docs/foundry/capability-ledger.yaml`, in modes.md § Schema v1's forms: cells `cell:conda-forge-expert/<part>`, qualified and quoted expiries (`mason:39.2`, `steward:44.8`).

## Boundaries & Constraints

**Always:**
- Append only `Surface reconcile` events after Story 37.2's re-stamps; the retro and the readiness gate stand.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never write `sprint-status-ledger.yaml`; never use `--allow-regression`.
- Never close a deferral on a bare note.
- Never hand-edit a `SPEC.md` or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**AC1 — A mason retro covers Epics 37 to 39 within two days of the code change.**

```bash
ls _bmad-output/projects/pyforge-mason/planning-artifacts/retros/retro-pyforge-mason-2026-11-*.md
```

Expect: one file, written by `bmad-retrospective` with sourced findings and an acceptance decision, dated on or after the last commit of the package pyproject.toml.

**AC2 — The mason chain is current by the sweep's own rules.**

```bash
python3 -  <<'EOF'
"""Exit 0 when the mason chain's dates are in feed order and none trails the code. Run from the repo
root; no argv. Mirrors scripts/fleet_scan.py `_artifact_dates` (frontmatter `updated:` first, then the
path date, then git's last touch), `_spec_feeds_updated` and `_memlog_contract_updated` (Story 6.13: the
spec stage is the later of SPEC.md's date and the memlog's contract date; when the memlog's last entry is
bookkeeping, a `(event) Surface reconcile` or `(event) Story N.M landed` line, the contract date is the
latest git-blame day of the entries that are not, an uncommitted line counting as today) and `_currency`
(feeds fire only past a 2-day grace; behind-code has none) for one station: research -> brief -> prd ->
arch -> epics and spec -> prd within 2 days; Spec, PRD and spine not older than the last change of the
package pyproject.toml; the newest retro within 2 days of that change; the newest readiness gate no older
than 90 days."""
import datetime
import glob
import re
import subprocess
import sys

PA = "_bmad-output/projects/pyforge-mason/planning-artifacts"
PKG = "src/shared/packages/pyforge-mason"
GRACE = 2
ISO = re.compile(r"(\d{4}-\d{2}-\d{2})")


def git_last(path: str) -> str:
    return subprocess.run(["git", "log", "-1", "--format=%cs", "--", path], capture_output=True, text=True).stdout.strip()


def updated(path: str) -> str:
    text = open(path, encoding="utf-8").read()
    fm = ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        fm = text[3:end] if end != -1 else ""
    m = re.search(r"^updated:\s*[\"']?(\d{4}-\d{2}-\d{2})", fm, re.M)
    if m:
        return m.group(1)
    p = ISO.search(path)
    return p.group(1) if p else git_last(path)


def stage(*patterns: str) -> str:
    days = [updated(p) for pat in patterns for p in glob.glob(pat)]
    return max(d for d in days if d) if days else ""


ITEM = re.compile(r"^-\s+\(([^)]+)\)\s+(.*)$")
LANDED = re.compile(r"Story \d+\.\d+ landed")


def bookkeeping(tag: str, body: str) -> bool:
    if tag.split(" by ", 1)[0].strip() != "event":
        return False
    body = body.lstrip()
    return body.startswith("Surface reconcile") or bool(LANDED.match(body))


def memlog_contract(path: str) -> str:
    fm = updated(path)
    lines = open(path, encoding="utf-8").read().splitlines()
    items = [(i, m) for i, line in enumerate(lines, 1) if (m := ITEM.match(line.strip()))]
    if not items or not bookkeeping(items[-1][1].group(1), items[-1][1].group(2)):
        return fm
    contract = [i for i, m in items if not bookkeeping(m.group(1), m.group(2))]
    if not contract:
        return fm
    r = subprocess.run(["git", "blame", "--line-porcelain", "-L", f"{min(contract)},{max(contract)}", "--", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return fm
    days, num, when = {}, min(contract) - 1, None
    for line in r.stdout.splitlines():
        if line.startswith("committer-time "):
            when = datetime.datetime.fromtimestamp(int(line.split()[1]), datetime.UTC).strftime("%Y-%m-%d")
        elif line.startswith("\t"):
            num += 1
            if when:
                days[num] = when
            when = None
    today = datetime.date.today().isoformat()
    return max(days.get(i, today) for i in contract) or fm


research = stage(f"{PA}/research/*.md")
brief = stage(f"{PA}/briefs/brief-pyforge-mason-*/brief*.md")
prd = stage(f"{PA}/prds/prd-pyforge-mason-*/prd.md")
arch = stage(f"{PA}/architecture/architecture-pyforge-mason-*/*.md")
epics = stage(f"{PA}/epics.md")
spec = max(stage(f"{PA}/specs/spec-pyforge-mason/SPEC.md"), memlog_contract(f"{PA}/specs/spec-pyforge-mason/.memlog.md"))
code = git_last(f"{PKG}/pyproject.toml")
retro = stage(f"{PA}/retros/*pyforge-mason*.md")
gate = stage(f"{PA}/implementation-readiness-report*.md", f"{PA}/validation-report-PRD*.md")
day = datetime.date.fromisoformat
bad = []
for up, down, a, b in (("research", "brief", research, brief), ("brief", "prd", brief, prd), ("prd", "arch", prd, arch),
                       ("spec", "prd", spec, prd), ("arch", "epics", arch, epics), ("code", "retro", code, retro)):
    if a and b and (day(a) - day(b)).days > GRACE:
        bad.append(f"feeds: {up} {a} is newer than {down} {b} by more than {GRACE} days")
for name, when in (("spec", spec), ("prd", prd), ("arch", arch)):
    if when < code:
        bad.append(f"behind-code: {name} {when} is older than code {code}")
if gate and (datetime.date.today() - day(gate)).days > 90:
    bad.append(f"shelf: readiness gate {gate} is past its 90-day shelf life")
print(f"research={research} brief={brief} prd={prd} arch={arch} epics={epics} spec={spec} code={code} retro={retro} gate={gate}")
for row in bad:
    print("  " + row)
sys.exit(1 if bad else 0)
EOF
pixi run --frozen -e pyforge-guild chain-currency-sweep-check -- --project pyforge-mason; echo $?
```

Expect: the helper exits 0 (exit 1 today: research newer than brief, prd newer than arch, readiness gate past its shelf; Story 37.2's brief review, spine stamp and readiness gate clear all three), then the sweep prints 0.

**AC3 — The story specs' deferral rows are in the ledger.**

```bash
pixi run -e pyforge-guild python scripts/deferred_work_intake.py --fix --project mason; echo $?; pixi run -e pyforge-guild deferred-work-check; echo $?
```

Expect: 0 and 0; the rows written at build to the `deferred:` lists of Stories 37.1, 37.4, 38.3 and 39.1 now have DW-mason ids.

**AC4 — This story spec carries the burn-down and naming rows.**

```bash
python3 - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-37-4-*.md' 'open mason deferrals' '-2' <<'EOF'
"""Exit 0 when a story spec's frontmatter `deferred:` list carries one row for each phrase given (case-
insensitive match in the row's summary). Run from the repo root. argv: story spec path (glob allowed),
then one or more phrases."""
import glob
import sys

import yaml

path = sorted(glob.glob(sys.argv[1]))[0]
text = open(path, encoding="utf-8").read()
fm = yaml.safe_load(text.split("\n---", 1)[0].lstrip("-\n")) or {}
rows = [str(r.get("summary", "")).lower() for r in (fm.get("deferred") or []) if isinstance(r, dict)]
missing = [p for p in sys.argv[2:] if not any(p.lower() in r for r in rows)]
print(f"{path}: deferred rows={len(rows)} missing={missing}")
sys.exit(1 if missing else 0)
EOF
```

Expect: exit 0 once this story has written the two rows listed under Notes into its `deferred:` (exit 1 at mint, where `deferred: []`: the rows are written at build, before AC3's intake, never at mint).

**AC5 — DW-mason-25-2-3 says what is true.**

```bash
grep -n -A12 '^### DW-mason-25-2-3' _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md | grep -E 'status:'
```

Expect: `status: closed` with the commits that prove it (Stories 25.5 to 25.12, 25.18, 25.19), or `status: open` with a dated note saying what remains; never closed on a bare note.

**AC6 — Story 5.4's first spec no longer contradicts its ledger key.**

```bash
grep -n "^status:" _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-5-4-free-inheritance-verification.md
```

Expect: prints `status: 'superseded'`.

**AC7 — The capability ledger routes every mason capability as the rulings say (control-plane's regenerated rows).**

```bash
python3 -  <<'EOF'
"""Exit 0 when docs/foundry/capability-ledger.yaml routes every mason capability as the 2026-11-10 rulings
say. Run from the repo root; no argv. retire: the Presenton set and CAP-14..CAP-17 (never built; closed campaign),
CAP-31 and CAP-35 (closed one-time recipe campaigns). A-only with expiry `mason:39.2` (conda-forge-expert's own
Spec Story): CAP-19, CAP-21..CAP-26, CAP-32..CAP-34, and the four `cells:` rows cell:conda-forge-expert/{skill,
scripts,mcp-server,data}. A-only with expiry steward:44.8 (the recipes working set): CAP-18. A-only with expiry
`flip`: CAP-20 and CAP-29 (Mason's skills). rebuild: every other id CAP-1..CAP-37."""
import sys

import yaml

d = yaml.safe_load(open("docs/foundry/capability-ledger.yaml", encoding="utf-8"))
rows = {r.get("id"): r for r in d["capabilities"] if isinstance(r, dict)}
CFE = "mason:39.2"
want: dict[str, tuple[str, str | None]] = {}
for n in range(1, 38):
    want[f"pyforge-mason:CAP-{n}"] = ("rebuild", None)
for n in [*range(8, 18), 31, 35]:
    want[f"pyforge-mason:CAP-{n}"] = ("retire", None)
for n in (19, 21, 22, 23, 24, 25, 26, 32, 33, 34):
    want[f"pyforge-mason:CAP-{n}"] = ("A-only", CFE)
want["pyforge-mason:CAP-18"] = ("A-only", "steward:44.8")
want["pyforge-mason:CAP-20"] = ("A-only", "flip")
want["pyforge-mason:CAP-29"] = ("A-only", "flip")
cells = {r.get("id"): r for r in (d.get("cells") or []) if isinstance(r, dict)}
for c in ("skill", "scripts", "mcp-server", "data"):
    want[f"cell:conda-forge-expert/{c}"] = ("A-only", CFE)
bad = []
for rid, (mode, expiry) in sorted(want.items()):
    row = rows.get(rid) or cells.get(rid)
    if row is None:
        bad.append(f"{rid}: no row")
        continue
    if row.get("mode") != mode or (expiry is not None and str(row.get("expiry")) != expiry):
        bad.append(f"{rid}: mode={row.get('mode')} expiry={row.get('expiry')} want {mode} {expiry or ''}")
extra = sorted(k for k in rows if str(k).startswith("pyforge-mason:") and k not in want)
bad += [f"{k}: row for no mason capability" for k in extra]
for b in bad:
    print(b)
print(f"checked={len(want)} bad={len(bad)}")
sys.exit(1 if bad else 0)
EOF
```

Expect: exit 0 (exit 1 today: 29 rows differ; the CAP-36 and CAP-37 rows exist since the mint).

**AC8 — Ledger and status detectors.**

```bash
pixi run -e pyforge-guild story-status-check; echo $?; pixi run -e pyforge-guild ledger-regression-check; echo $?; pixi run -e pyforge-guild chain-completeness-check; echo $?
```

Expect: 0, 0 and 0.

**AC9 — no unreconciled drift row names pyforge-mason/spec-pyforge-mason (the closer's memlog names every changed path; doctor 58.4 stamps).**

```bash
pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "${TMPDIR:-/tmp}/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "${TMPDIR:-/tmp}/ss.json" pyforge-mason/spec-pyforge-mason
```

Expect: prints 0, exit 0.

**AC10 — docs/dreams/pyforge-mason.md records the close.**

```bash
grep -c 'cutover readiness, closed' docs/dreams/pyforge-mason.md
```

Expect: prints 1 or more.

**AC11 — mason's chain is current: no feeds finding and no shelf finding, read from the exit code.**

```bash
pixi run --frozen -e pyforge-guild chain-currency-sweep-check -- --project pyforge-mason
```

Expect: exit 0 (1 is a finding, 2 could not run; never through a pipe).

**AC12 — every path mason's widened surface newly governs is named in its reconcile event.**

```bash
python3 - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md <<'EOF'
import sys,subprocess,yaml,fnmatch
spec,ml=sys.argv[1],sys.argv[2]
surf=lambda t:(yaml.safe_load(t.split('---')[1]) or {}).get('surface') or []
new=surf(open(spec).read());old=surf(subprocess.run(['git','show','origin/main:'+spec],capture_output=True,text=True).stdout)
files=subprocess.run(['git','ls-files'],capture_output=True,text=True).stdout.split()
m=lambda p,gs:any(fnmatch.fnmatch(p,g) or (g.endswith('/**') and p.startswith(g[:-2])) or (g.endswith('/') and p.startswith(g)) for g in gs)
added=[p for p in files if m(p,new) and not m(p,old)];t=open(ml).read();miss=[p for p in added if p not in t]
print(len(added),miss);sys.exit(1 if miss else 0)
EOF
```

Expect: prints the count and [], exit 0.

*Mint adjustment (2026-11-10):* AC7's docstring names the Presenton set in words, for the same `ad-citation-check` reason; the check itself is the plan's.

*Review fix (2026-11-10):* the frontmatter `deferred:` is empty at mint and AC4 is met at build; AC2's heredoc terminator stands on its own line (the plan's text joined it to the next command, so bash never closed the heredoc); AC9 falls back to `/tmp` when `TMPDIR` is unset.

*Review fix (2026-11-11):* AC2's helper dates the spec stage as the sweep does (`_spec_feeds_updated` and `_memlog_contract_updated`, Story 6.13), so step (2)'s own `Surface reconcile` event no longer re-dates the Spec past the PRD; AC7's count today is 29, the CAP-36 and CAP-37 rows having been added at the mint; the frontmatter carries a `blocking_condition:` that marshal's `parse_blocking_condition` reads.

</intent-contract>

## Binding

- Parent: `spec-pyforge-mason`.
- Requirements: none.
- Dream: `docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*.
- Epic 37, `### Story 37.4: Mason's change closes: retro, surface reconcile, deferrals and ledger` in `planning-artifacts/epics.md`.
- Wave: BUILD-9 (cutover readiness plan).
- Findings closed: SHOULD: stories (5.4 story spec says blocked, ledger says done); SHOULD: deferred work (DW-mason-25-2-3 beside CAP-35's marker).

## Notes

- Cross-station dependency: steward:S-121.7 (control-plane's capability-ledger regeneration after every Spec sweep); the ledger-mode check waits on it.
- Cross-station: doctor:S-58.4 runs every scoped stamp once, after the last edit, and refreshes `scripts/.spec-surface-baseline.json`.
- Rows this story writes to its `deferred:` at build, before AC3's intake (not at mint, so no row sits in frontmatter without a ledger twin):
  - id `open-mason-deferrals-untriaged`; severity low; location `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md`; summary: "108 open mason deferrals are untriaged against what has shipped since; 72 carry no severity. Counted by the 2026-11-10 audit; the burn-down is a Dream-sized effort of its own, as the 2026-10-01 campaign was."
  - id `two-story-specs-carry-a-2-suffix`; severity low; location `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-5-4-free-inheritance-verification-2.md`; summary: "Two mason story specs carry a `-2` suffix no ledger key has (spec-2-5-mason-recipe-validate-2.md, spec-5-4-free-inheritance-verification-2.md); CHAIN-STANDARD section 5 names a story spec by its key exactly. Both are entries in docs/governance/flag-rule-baseline.json, which only scripts/flag_rule_baseline.py writes, so a rename needs that script's pass."
