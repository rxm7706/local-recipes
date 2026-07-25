#!/usr/bin/env python3
"""Deliverable 2: retro-generate B9-H4 story files in the BMAD story-file format,
populated ONLY from real sources (epics.md + deferred-work.md + the merged git commits).
Honestly marked 'done / retro-reconstructed' — NOT the skill's 'ready-for-dev' — and
sprint-status.yaml is left untouched (these stories are shipped, not pending)."""
import subprocess, datetime
from pathlib import Path

ROOT = Path("/home/user/local-recipes")
PA = ROOT / "_bmad-output/projects/pyforge-atlas/planning-artifacts"
IA = ROOT / "_bmad-output/projects/pyforge-atlas/implementation-artifacts"
OUTDIR = Path("/tmp/claude-0/-home-user-local-recipes/8c301a61-5446-55e6-b085-93ba3871f3dc/scratchpad/retro-story-files")
OUTDIR.mkdir(parents=True, exist_ok=True)
CONCAT = OUTDIR.parent / "ATLAS-B9-H4-RETRO-STORY-FILES.md"

IDS = ["B9","B10","C1","C2","D1","D2","D3","E1","E2","F1","F2","F3","F4","G1","G2","G3","H1","H2","H3","H4"]
# id -> (epic.story alias, PR, [ (sha, kind) ])  kind: impl | review
STORY = {
 "B9":("3.9","#82",[("73e477f","impl")]),
 "B10":("3.10","#83",[("ecc161a","impl"),("520a75b","review")]),
 "C1":("4.1","#84",[("166eb42","impl")]),
 "C2":("4.2","#85",[("d4d7372","impl")]),
 "D1":("5.1","#86",[("580e5ba","impl")]),
 "D2":("5.2","#87",[("7b6b3ca","impl")]),
 "D3":("5.3","#88",[("d58a4bd","impl")]),
 "E1":("6.1","#90",[("210b3a3","impl"),("01f8f82","review")]),
 "E2":("6.2","#91",[("153a5ad","impl")]),
 "F1":("7.1","#92",[("13a5ce3","impl")]),
 "F2":("7.2","#93",[("1e122c8","impl")]),
 "F3":("7.3","#94",[("df58bfc","impl"),("2acfeaa","review")]),
 "F4":("7.4","#95",[("fd8e1c9","impl")]),
 "G1":("8.1","#96",[("203be0c","impl")]),
 "G2":("8.2","#97",[("6146f83","impl"),("33b3fd8","review")]),
 "G3":("8.3","#98",[("40b9eae","impl")]),
 "H1":("9.1","#99",[("fe52bbd","impl")]),
 "H2":("9.2","#100",[("2f4240f","impl")]),
 "H3":("9.3","#101",[("4e95efb","impl")]),
 "H4":("9.4","#102",[("6cc2dbf","impl")]),
}

epics = (PA / "epics.md").read_text(encoding="utf-8").splitlines()
dw = (IA / "deferred-work.md").read_text(encoding="utf-8").splitlines()

def git(args):
    try:
        return subprocess.run(["git","-C",str(ROOT)]+args, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""

def epics_block(sid):
    start = next((i for i,l in enumerate(epics) if l.startswith(f"### Story {sid} (") or l.startswith(f"### Story {sid}:")), None)
    if start is None: return None, None
    end = len(epics)
    for j in range(start+1, len(epics)):
        if epics[j].startswith("### Story ") or epics[j].startswith("## Epic") or epics[j].startswith("## "):
            end = j; break
    blk = epics[start:end]
    while blk and blk[-1].strip() in ("","---"): blk.pop()
    title = epics[start].split(":",1)[1].strip() if ":" in epics[start] else sid
    return "\n".join(blk), title

def section(block, header):
    """Return the text under a bold-**header:** or line marker inside an epics block."""
    return block  # helper reserved; we inline-parse below

def dw_blocks(sid):
    out, i = [], 0
    while i < len(dw):
        if dw[i].startswith(f"## DW-{sid}-") or dw[i].startswith(f"## DW-{sid} ") or dw[i].strip()==f"## DW-{sid}":
            j=i+1
            while j<len(dw) and not dw[j].startswith("## "): j+=1
            blk=dw[i:j]
            while blk and blk[-1].strip()=="": blk.pop()
            out.append("\n".join(blk)); i=j
        else: i+=1
    return out

def parse_story_narrative(block):
    """Extract the 'As a / I want / So that' + AC lines + metadata bullets from an epics block."""
    lines = block.splitlines()
    # narrative = lines after heading until '**Acceptance Criteria'
    body = lines[1:]
    narr, ac, meta = [], [], []
    mode = "narr"
    for l in body:
        if l.startswith("**Acceptance Criteria"):
            mode="ac"; continue
        if l.startswith("- **FRs:**") or l.startswith("- **Invariants:**") or l.startswith("- **Mode:**") \
           or l.startswith("- **Gating") or l.startswith("- **Verify") or l.startswith("- **Depends") \
           or l.startswith("- **Wave"):
            mode="meta"
        if mode=="narr": narr.append(l)
        elif mode=="ac": (meta if l.startswith("- **") else ac).append(l)
        if mode=="meta": meta.append(l)
    # dedupe meta lines
    seen=set(); meta2=[]
    for l in meta:
        if l.strip() and l not in seen: seen.add(l); meta2.append(l)
    return "\n".join(narr).strip(), "\n".join(ac).strip(), "\n".join(meta2).strip()

date = datetime.date.today().isoformat()
concat = [f"""# pyforge-atlas — B9–H4 retro-reconstructed story files

> **What these are.** BMAD story files for the 20 Wave B9→H4 stories, generated
> retroactively in the standard `bmad-create-story` template format. These waves
> shipped through the **in-session agent loop**, so no story files were authored
> at build time — these are reconstructed **after the fact from real sources
> only**: the verbatim `epics.md` binding definition, the `deferred-work.md`
> ledger, and each story's **merged git commit(s)** (File List = the real diff
> stat; Completion Notes = the real commit body). Nothing is invented.
>
> **Honest deviations from `bmad-create-story`:** Status is `done
> (retro-reconstructed {date})`, not `ready-for-dev` — the work is shipped.
> `sprint-status.yaml` is intentionally **left untouched**. The `Dev Agent
> Record` reflects that these ran via the loop, not a story-file-driven dev run;
> `Tasks / Subtasks` are derived from the ACs (no original breakdown existed).
>
> Generated: {date}. Repo: rxm7706/local-recipes.

---
"""]

for sid in IDS:
    alias, pr, commits = STORY[sid]
    block, title = epics_block(sid)
    narr, ac, meta = parse_story_narrative(block)
    dws = dw_blocks(sid)
    impl = [c for c,k in commits if k=="impl"]
    revs = [c for c,k in commits if k=="review"]

    out = []
    out.append(f"# Story {alias} ({sid}): {title}")
    out.append("")
    out.append(f"Status: done (retro-reconstructed {date})")
    out.append("")
    out.append(f"> ⚠️ **Retro-reconstructed** from `epics.md` + `deferred-work.md` + merged "
               f"PR `{pr}`. Not an original build-time story file (this wave ran through the "
               f"in-session loop). Dev Agent Record / File List / Review Triage Log below are "
               f"the **actual shipped git evidence**, not a live dev-agent transcript.")
    out.append("")
    out.append("## Story")
    out.append("")
    out.append(narr or "*(see epics.md)*")
    out.append("")
    out.append("## Acceptance Criteria")
    out.append("")
    out.append("*(Verbatim from `epics.md` — spec § 9 binding.)*")
    out.append("")
    out.append(ac or "*(see epics.md)*")
    out.append("")
    out.append("## Tasks / Subtasks")
    out.append("")
    out.append("*(Derived from the ACs — no original task breakdown was authored for this "
               "loop-run story.)*")
    out.append("")
    # derive one task per AC 'Then/And' clause
    n=0
    for l in ac.splitlines():
        ls=l.strip()
        if ls.startswith("**Then**") or ls.startswith("**And**"):
            n+=1
            out.append(f"- [x] {ls.replace('**Then**','').replace('**And**','').strip()}")
    if n==0: out.append("- [x] Implement per the Acceptance Criteria above.")
    out.append("")
    out.append("## Dev Notes")
    out.append("")
    out.append("**Planning metadata (from `epics.md`):**")
    out.append("")
    out.append(meta or "*(none)*")
    out.append("")
    out.append("### References")
    out.append("")
    out.append(f"- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-{sid}]")
    out.append(f"- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-{sid}]")
    out.append(f"- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]")
    out.append("")
    out.append("## Dev Agent Record")
    out.append("")
    out.append("### Agent Model Used")
    out.append("")
    out.append("In-session BMAD agent loop (draft → 2× adversarial review → 1× independent "
               "fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.")
    out.append("")
    out.append("### Completion Notes List")
    out.append("")
    for c in impl:
        subj = git(["show","-s","--format=%s","--date=short",c])
        body = git(["show","-s","--format=%b",c])
        out.append(f"- **Impl commit `{c}`** — {subj}")
        if body:
            for bl in body.splitlines():
                if bl.strip(): out.append(f"  - {bl.strip()}")
    out.append("")
    out.append("### File List")
    out.append("")
    out.append("*(Real `git show --stat` of the shipped commit(s).)*")
    out.append("")
    out.append("```")
    for c in impl+revs:
        stat = git(["show","--stat","--format=%h %s",c])
        out.append(stat)
        out.append("")
    out.append("```")
    out.append("")
    out.append("## Review Triage Log")
    out.append("")
    if revs:
        out.append(f"Independent/Gemini review produced follow-up fix commit(s) on PR `{pr}`:")
        out.append("")
        for c in revs:
            subj = git(["show","-s","--format=%s",c])
            out.append(f"- `{c}` — {subj}")
    else:
        out.append(f"No separate review-fix commit; findings (if any) folded into the impl "
                   f"commit. Full review threads on PR `{pr}`.")
    out.append("")
    if dws:
        out.append("## Deferred Work (DW ledger)")
        out.append("")
        out.append("\n\n".join(dws))
        out.append("")
    out.append("<!-- end retro story -->")

    text = "\n".join(out)
    fname = f"{alias.replace('.','-')}-{sid.lower()}.md"
    (OUTDIR / fname).write_text(text, encoding="utf-8")
    concat.append(text)
    concat.append("\n---\n")

CONCAT.write_text("\n".join(concat), encoding="utf-8")
files = sorted(OUTDIR.glob("*.md"))
print(f"Wrote {len(files)} story files to {OUTDIR}")
print(f"Concatenated: {CONCAT} ({CONCAT.stat().st_size:,} bytes)")
for f in files: print(" ", f.name, f"({f.stat().st_size:,}B)")
