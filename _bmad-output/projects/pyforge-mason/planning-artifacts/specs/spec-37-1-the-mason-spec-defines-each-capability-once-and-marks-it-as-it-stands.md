---
title: "37.1: The mason Spec defines each capability once and marks it as it stands"
type: 'chore'
created: '2026-11-10'
status: 'blocked'
blocking_condition: 'forward dependency (2026-11-10): Deps S-38.1, S-38.2, S-38.3, S-39.1 are later epics; the operator unblocks it once they are done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md
  - docs/dreams/pyforge-mason.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py
  - scripts/ad_citation_check.py
surface:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-38.1, S-38.2, S-38.3, S-39.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** The Spec text is wrong where the code, the ledger and the rulings are right. Fourteen ids (CAP-14..CAP-27) are defined twice, once as short headings under `## Capabilities` and once as long-form bullets under `## Fold provenance`; the never-built Presenton set and the closed rebuild campaign read shipped; CAP-28..CAP-35 carry no marker; the kernel text still promises a diff-before-write the operator ruled out on 2026-09-14, a 3.12 floor and a fake-root-only suite; and the detectors read only the capabilities written as bullets inside `## Capabilities` (before this change, 7 of 35).

**Approach:**
- **The memlog is already written.** The mint appended the decision of record (the 2026-11-10 rulings), the correction naming the duplicate definitions and the fold that made them, and one `capability` entry for each amended id or group (memlog entries of 2026-11-10). This story renders them; it appends a `correction` only where the build finds a plan date or sentence wrong, and a `capability` entry for each marker it moves.
- **Target form**, the one form every reader parses (INV-A in `pyforge-doctor` `sources/board.py`, the ledger extract in `sources/capability_ledger.py`, `scripts/ad_citation_check.py`): all 37 capabilities are `- **CAP-n — <title>** ← <provenance> (<marker>)` bullets with `intent:` and `success:` sub-bullets, in numeric order, inside `## Capabilities`. Epic and FR lines already cite CAP-1..CAP-37, so no citation is added.
- **Markers.** The Presenton set: `(retired 2026-11-10: never built)` (ruling R3's form; the "Retire both" ruling is quoted in each one-sentence body, never in the marker); CAP-14..CAP-17: `(retired 2026-09-10: ...)`; CAP-31 and CAP-35: `(retired 2026-11-10: closed one-time campaign)`, the day their campaign shipped kept in the definition text as prose, never as a second parenthesized marker (memlog corrections of 2026-11-10); CAP-32: `(ready 2026-09-28)`; every other: shipped with the date the memlog names, each re-checked with `git log --merges --grep 'pyforge-mason/<E>-<S>'` before it is written. The mint wrote CAP-5, CAP-7, CAP-36 and CAP-37 at `(ready 2026-11-10)`; this story writes CAP-5, CAP-7 and CAP-36 `(shipped <day their tests landed>)` after Stories 38.1, 38.2, 38.3 and 39.1, and CAP-37 `(shipped 2026-08-25)` once its success command passes.
- **Same render, other text.** CAP-2's update clause (ruling 2026-09-14); CAP-7 names `scripts/mason_cfe_surface_check.py` as FR-45's detector (doctor's request); Python floor 3.14 (decision D6); `Every test runs against a fake root` names the live-tree half and the one slow exception; `Degradation` names three discoverable steps and the terminal state; `No configuration file` enumerates the six global knobs and the two factory-island variables; the Non-goal and the `companions:` comment stop calling an absorbed pointer the governing Spec; the as-built numerics point at their sources; `companions:` gains `contract.md` (Story 38.1 writes it); `surface:` gains `.claude/skills/mason-*/**` and `scripts/cfe_rebuild_guard_check.py`.
- **Records keep their words.** The `- **verified:**` lines and the dated passages under `## Currency reconciliation — 2026-08-26` are not rewritten; one appended `### Correction — 2026-11-1x` subsection says the Dream is `specified` and the Spec `ready` (CHAIN-STANDARD § 4) and that the update claim was ruled out on 2026-09-14.
- **Render.** The anchor-asserting script render (each anchor asserted to occur once; the precedent of Stories 33.1 and 36.1 and of the mint itself), then both self-validate passes logged as memlog events in the form `Self-validate pass 1 (coherence) 2026-11-1x` and `Self-validate pass 2 (preservation) 2026-11-1x`.

Ledger key: `37-1-the-mason-spec-defines-each-capability-once-and-marks-it-as-it-stands`.
Ledger status: `blocked` (forward dependency, 2026-11-10; unblocked only with operator confirmation once its later-epic deps are done).
Type / Effort / Deps: chore / L / S-38.1, S-38.2, S-38.3, S-39.1.

### Living CAP citations

- **CAP-37** (minted; FR-59) and the final markers of **CAP-5**, **CAP-7** and **CAP-36**.
- **CAP-2** and `spec-pyforge-mason:CAP-8` to `spec-pyforge-mason:CAP-35` amended or re-marked, by the memlog's 2026-11-10 entries.
- Operator rulings 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log): "Accept all", "Retire both", "Accept all, run mint"; CHAIN-STANDARD § 4 as amended by steward Story 120.3.

## Boundaries & Constraints

**Always:**
- Build on the `SPEC.md` the mint and Stories 38.1 to 39.1 leave; it is this change's one build-phase writer of `SPEC.md` and of `.memlog.md` before Story 37.4.
- Check every marker date against git before writing it.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never hand-edit (render through the anchored script) a `SPEC.md` or `sprint-status-ledger.yaml`.
- Never rewrite a dated record; correct it by appending.
- Never change code.
- Never append a `Surface reconcile` line to another Spec's memlog and never run `spec_surface_check.py --write-baseline`: Story 37.4 writes mason's reconcile event, each other Spec's closer writes its own, and doctor Story 58.4 runs every scoped stamp once, after the last edit (cutover readiness plan, integration 2026-11-10).
- Never treat `capability-ledger-check` as this story's gate: control-plane judges it at steward Story 121.7.

## Acceptance Criteria

**AC1 — Every capability CAP-1..CAP-37 is defined once, with no gap, as a bullet inside `## Capabilities`.**

```bash
python3 - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md 37 <<'EOF'
"""Exit 0 when SPEC.md defines CAP-1..CAP-<last> exactly once each, no gap, and every definition is a
`- **CAP-n — title**` bullet inside the `## Capabilities` block (the one form board.py's INV-A,
capability_ledger.py's extract, ad_citation_check.py and one_chain.py all read). argv: SPEC.md path, last id."""
import collections
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
last = int(sys.argv[2])
any_form = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+|[-*][ \t]+\*\*|\*\*)CAP-(\d+)\b", re.M)
counts = collections.Counter(int(m.group(1)) for m in any_form.finditer(text))
dup = sorted(n for n, k in counts.items() if k != 1)
gap = [n for n in range(1, last + 1) if n not in counts]
extra = sorted(n for n in counts if n > last)
start = re.search(r"^## Capabilities\b.*$", text, re.M)
block = ""
if start:
    nxt = re.search(r"^## ", text[start.end():], re.M)
    block = text[start.end(): start.end() + nxt.start() if nxt else len(text)]
bullets = {int(m.group(1)) for m in re.finditer(r"^- \*\*CAP-(\d+) — ", block, re.M)}
outside = sorted(set(counts) - bullets)
print(f"defined={len(counts)} duplicate={dup} gap={gap} beyond={extra} not-a-bullet-under-Capabilities={outside}")
sys.exit(1 if dup or gap or extra or outside else 0)
EOF
```

Expect: exit 0 (exit 1 at mint: duplicate=[14..27], gap=[], and 28 definitions outside the bullet form; the mint wrote CAP-36 and CAP-37).

**AC2 — Every capability carries exactly one dated marker of the expected word, and the four whose success this change made true carry the day their code landed.**

```bash
python3 - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md 5=src/shared/packages/pyforge-mason/tests/meta/test_public_contract.py 7=src/shared/packages/pyforge-mason/tests/meta/test_live_tree_split.py,src/shared/packages/pyforge-mason/tests/meta/test_cfe_adapter_argv_live.py 36=src/shared/packages/pyforge-mason/tests/unit/test_factory_island.py <<'EOF'
"""Exit 0 when every CAP block of SPEC.md carries exactly one status marker, it is the expected word, and
the markers of capabilities whose success clause this change made true carry the day their code landed.
argv: SPEC.md path, then zero or more N=path[,path...] pairs (CAP number = the files whose last commit
made its success clause true). Expected words: the Presenton set, CAP-14..CAP-17, CAP-31 and CAP-35 retired, CAP-32
ready, every other CAP shipped. For each N=paths the marker date D must satisfy 2026-11-10 <= D <= the latest
last-author date (git log -1 --format=%as) among those files."""
import re
import subprocess
import sys

text = open(sys.argv[1], encoding="utf-8").read()
landed = {k: v.split(",") for k, v in (a.split("=", 1) for a in sys.argv[2:])}
defs = list(re.finditer(r"^[ \t]*(?:#{1,6}[ \t]+|[-*][ \t]+\*\*|\*\*)CAP-(\d+)\b", text, re.M))
marker = re.compile(r"\((ready|shipped|retired) (\d{4}-\d{2}-\d{2})\b[^)]*\)")
want = {n: "retired" for n in (*range(8, 18), 31, 35)} | {32: "ready"}
bad = []
for i, m in enumerate(defs):
    n = int(m.group(1))
    end = defs[i + 1].start() if i + 1 < len(defs) else len(text)
    block = text[m.start():end]
    nxt = re.search(r"^## ", block, re.M)
    if nxt:
        block = block[: nxt.start()]
    found = marker.findall(block)
    words = [w for w, _ in found]
    expect = want.get(n, "shipped")
    if words != [expect]:
        bad.append("CAP-%d markers=%s expected=[%s]" % (n, words, expect))
        continue
    paths = landed.get(str(n))
    if paths:
        days = [
            subprocess.run(["git", "log", "-1", "--format=%as", "--", p], capture_output=True, text=True).stdout.strip()
            for p in paths
        ]
        last = max(d for d in days if d) if any(days) else ""
        day = found[0][1]
        if not last or not ("2026-11-10" <= day <= last):
            bad.append("CAP-%d shipped %s is outside 2026-11-10..%s (last change of %s)" % (n, day, last, paths))
missing = sorted(set(landed) - {m.group(1) for m in defs})
for n in missing:
    bad.append("CAP-%s has no definition" % n)
for row in bad:
    print(row)
sys.exit(1 if bad else 0)
EOF
```

Expect: exit 0 and no output (exit 1 today): the Presenton set, CAP-14..CAP-17, CAP-31 and CAP-35 retired, CAP-32 ready, every other shipped; CAP-5, CAP-7 and CAP-36 dated between 2026-11-10 and the last change of their tests; CAP-37 reads `(shipped 2026-08-25)`.

**AC3 — No intent or success sentence of CAP-18..CAP-27 was lost in the merge of the two definitions.**

```bash
python3 - a2a97a1eef _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md <<'EOF'
"""Exit 0 when every intent/success sentence of the long-form CAP-18..CAP-27 definitions at the base
revision is still in SPEC.md. argv: base revision, SPEC.md path (repo-relative). Run from the repo root."""
import re
import subprocess
import sys

base, path = sys.argv[1], sys.argv[2]
old = subprocess.run(["git", "show", f"{base}:{path}"], capture_output=True, text=True, check=True).stdout
new = " ".join(open(path, encoding="utf-8").read().split())
tail = old[old.index("### Absorbed capabilities reminted"):]
missing = []
for m in re.finditer(r"^- \*\*CAP-(\d+) —.*?(?=^- \*\*CAP-|\Z)", tail, re.M | re.S):
    n = int(m.group(1))
    if not 18 <= n <= 27:
        continue
    for b in re.finditer(r"\*\*(intent|success):\*\*\s*(.+)", m.group(0)):
        text = " ".join(b.group(2).split())
        if text not in new:
            missing.append((n, b.group(1), text[:70]))
for row in missing:
    print("CAP-%d %s lost: %s" % row)
sys.exit(1 if missing else 0)
EOF
```

Expect: exit 0 and no output.

**AC4 — The stale sentences are gone from the contract text, and the dated record says what changed.**

```bash
python3 - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md <<'EOF'
"""Exit 0 when no stale sentence is left in the contract text of SPEC.md and the dated record section carries
its correction. argv: SPEC.md path. Contract text = the file minus (a) every `- **verified:**` line (a dated
verification record) and (b) the `## Currency reconciliation` section with its subsections (dated records,
corrected by appending, never rewritten). The record section must hold a `### Correction — 2026-11-1x`
subsection that names both `specified` and `ready`."""
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
stale = re.compile(
    r"scripts/dream_chain_check\.py|update shows the change before writing it|Python floor `>= 3\.12`"
    r"|status: (?:shipped|realized)|Spec is `shipped`|flipped to `realized`|naming all four resolution steps"
    r"|under this Spec.s directory lists every slice|\(CAP-3\)\.$|expiry: 44\.5"
    r"|authoritative over Mason \(Rule 1\)|11 epics / 50 stories",
    re.M,
)
record = re.search(r"^## Currency reconciliation\b.*?(?=^## |\Z)", text, re.M | re.S)
record_text = record.group(0) if record else ""
contract = text.replace(record_text, "") if record else text
contract = "\n".join(line for line in contract.splitlines() if not line.lstrip().startswith("- **verified:**"))
hits = [(contract.count("\n", 0, m.start()) + 1, m.group(0)) for m in stale.finditer(contract)]
corr = re.search(r"^### Correction — 2026-11-1\d\b.*?(?=^### |\Z)", record_text, re.M | re.S)
ok_corr = bool(corr) and "specified" in corr.group(0) and "ready" in corr.group(0)
print(f"stale-in-contract={len(hits)} record-correction={'yes' if ok_corr else 'no'}")
for line, what in hits:
    print(f"  contract line {line}: {what}")
sys.exit(1 if hits or not ok_corr else 0)
EOF
```

Expect: exit 0 (exit 1 today: `stale-in-contract=10 record-correction=no`). Contract text is SPEC.md minus the `- **verified:**` lines and the `## Currency reconciliation — 2026-08-26` section, which are dated records corrected by appending a `### Correction — 2026-11-1x` subsection naming the Spec `ready` and the Dream `specified`, never rewritten.

**AC5 — Frontmatter: status ready, the surface claims Mason's four hand-authored skills and the rebuild guard, contract.md is a companion, and no companion line calls an absorbed pointer the governing Spec.**

```bash
python3 -c "import yaml,sys; t=open('_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md',encoding='utf-8').read(); fm=yaml.safe_load(t.split('---')[1]); s=fm['surface']; c=[str(x) for x in fm['companions']]; ok=fm['status']=='ready' and '.claude/skills/mason-*/**' in s and 'scripts/cfe_rebuild_guard_check.py' in s and 'src/shared/packages/pyforge-mason/**' in s and any(x.startswith('contract.md') for x in c) and 'authoritative over Mason' not in t.split('---')[1]; sys.exit(0 if ok else 1)"
```

Expect: exit 0 (exit 1 today).

**AC6 — The Python floor constraint reads 3.14 (decision D6).**

```bash
grep -c 'Python floor `>= 3.14`' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
```

Expect: prints 1.

**AC7 — CAP-7 names FR-45's detector.**

```bash
grep -c 'scripts/mason_cfe_surface_check.py' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
```

Expect: prints 1 or more (0 today).

**AC8 — CAP-37's success command passes.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_build_hooks.py src/shared/packages/pyforge-mason/tests/unit/test_airgap_contract.py src/shared/packages/pyforge-mason/tests/unit/test_boot_reconcile.py -q; echo $?
```

Expect: 0.

**AC9 — Every success command this change wrote passes together (CAP-5, CAP-7, CAP-36).**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_public_contract.py src/shared/packages/pyforge-mason/tests/meta/test_live_tree_split.py src/shared/packages/pyforge-mason/tests/meta/test_cfe_adapter_argv_live.py src/shared/packages/pyforge-mason/tests/unit/test_factory_island.py -q; echo $?
```

Expect: 0 (drop the 38.3 path if that story was dropped).

**AC10 — Both bmad-spec self-validate passes are logged for this re-derive.**

```bash
grep -cE 'Self-validate pass [12] \((coherence|preservation)\) 2026-11-1[0-9]' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md
```

Expect: prints 2 or more, and each of the two entries ends in PASS.

**AC11 — The dead air-gap key guard is recorded, not claimed.**

```bash
python3 - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-37-1-*.md' 'contract-key' <<'EOF'
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

Expect: exit 0 once the build has written the row listed under Notes into this story spec's `deferred:` (exit 1 at mint, where `deferred: []`: the row is written at build, not at mint, and Story 37.4's intake mints its DW-mason twin).

**AC12 — Every declared capability is cited by an epic or a requirement.**

```bash
pixi run -e pyforge-guild chain-completeness-check; echo $?
```

Expect: 0.

**AC13 — Citations and status text agree with the Spec.**

```bash
pixi run -e pyforge-guild ad-citation-check; echo $?; pixi run -e pyforge-guild status-body-consistency-check; echo $?; pixi run -e pyforge-guild dream-chain-check; echo $?
```

Expect: 0, 0 and 0.

*Mint adjustment (2026-11-10):* AC1's expected output is restated at the mint's state; AC2's docstring names the Presenton set in words (a bare citation of an id the Spec does not yet define in bullet form reds `ad-citation-check`); the check itself is the plan's.

*Review fix (2026-11-10):* the frontmatter `deferred:` is empty at mint and AC11 is met at build (deferral rows are written at build, never at mint); CAP-31 and CAP-35 join AC2's retired set, because control-plane retires both ledger rows and a retire row needs a retired marker; the Presenton marker is ruling R3's `(retired 2026-11-10: never built)`.

</intent-contract>

## Binding

- Parent: `spec-pyforge-mason` CAP-37 (minted); amends CAP-2, CAP-5, CAP-7, the Presenton set (`spec-pyforge-mason:CAP-8` to `spec-pyforge-mason:CAP-13`), CAP-14..CAP-17, CAP-18..CAP-27, CAP-28..CAP-35, CAP-29, CAP-32..CAP-34, CAP-31, CAP-35, CAP-36.
- Requirements: FR-59 ← CAP-37.
- Dream: `docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*.
- Epic 37, `### Story 37.1: The mason Spec defines each capability once and marks it as it stands` in `planning-artifacts/epics.md`.
- Wave: BUILD-2 (cutover readiness plan).
- Findings closed: MUST 2; MUST 3; MUST 9; SHOULD: status markers on CAP-28..35; SHOULD: ledger rows (placeholder headings, CAP-29 expiry, campaign modes); SHOULD: status text; SHOULD: skills (surface and stale anchors); SHOULD: memlog entries after the last re-derive; NICE: stale Spec numerics; NICE: unresolved-root message says three steps, Spec says four; PLAN: detectors read 7 of mason's 35 capabilities; PLAN: the air-gap contract-key guard cannot fire; REQUEST from doctor: name scripts/mason_cfe_surface_check.py in the capability FR-45 cites.

## Notes

- Cross-station: control-plane re-modes every mason row (steward:S-121.3, steward:S-121.7); the `pyforge-mason:CAP-36` and `pyforge-mason:CAP-37` rows were added at the mint.
- Risk to check, not assume: `capability-effect-check` and the flag inventory read 30 more capabilities once every capability is a bullet.
- Row this story writes to its `deferred:` at build (not at mint, so no row sits in frontmatter without a ledger twin; Story 37.4's intake mints the DW-mason twin, and `deferred-work-check` reads the row as `spec-frontmatter-only-deferral` until then):
  - id `airgap-contract-key-guard-is-dead`; severity low; location `src/shared/packages/pyforge-mason/src/pyforge/mason/airgap_contract.py:71`; summary: "validate_backend_shape's missing-contract-key branch is dead: `provided` is hard-coded to the three contract keys (airgap_contract.py:71-78), so the guard cannot fire. CAP-37 is worded as the code behaves and does not claim it; making the guard live is a small code fix for a later Story under CAP-37."
