#!/usr/bin/env python3
"""Extract B9-H4 story specs from real sources: epics.md + deferred-work.md + git commits.
Produces Deliverable 3 (epics-only) and Deliverable 1 (epics + DW + PR evidence)."""
import subprocess, datetime
from pathlib import Path

ROOT = Path("/home/user/local-recipes")
PA = ROOT / "_bmad-output/projects/pyforge-atlas/planning-artifacts"
IA = ROOT / "_bmad-output/projects/pyforge-atlas/implementation-artifacts"
OUTDIR = Path("/tmp/claude-0/-home-user-local-recipes/8c301a61-5446-55e6-b085-93ba3871f3dc/scratchpad")

IDS = ["B9","B10","C1","C2","D1","D2","D3","E1","E2","F1","F2","F3","F4","G1","G2","G3","H1","H2","H3","H4"]
STORY_PR = {
 "B9":("#82",["73e477f"]), "B10":("#83",["ecc161a","520a75b"]),
 "C1":("#84",["166eb42"]), "C2":("#85",["d4d7372"]),
 "D1":("#86",["580e5ba"]), "D2":("#87",["7b6b3ca"]), "D3":("#88",["d58a4bd"]),
 "E1":("#90",["210b3a3","01f8f82"]), "E2":("#91",["153a5ad"]),
 "F1":("#92",["13a5ce3"]), "F2":("#93",["1e122c8"]), "F3":("#94",["df58bfc","2acfeaa"]), "F4":("#95",["fd8e1c9"]),
 "G1":("#96",["203be0c"]), "G2":("#97",["6146f83","33b3fd8"]), "G3":("#98",["40b9eae"]),
 "H1":("#99",["fe52bbd"]), "H2":("#100",["2f4240f"]), "H3":("#101",["4e95efb"]), "H4":("#102",["6cc2dbf"]),
}

epics = (PA / "epics.md").read_text(encoding="utf-8").splitlines()
dw = (IA / "deferred-work.md").read_text(encoding="utf-8").splitlines()

def epics_block(sid):
    start = None
    for i, ln in enumerate(epics):
        if ln.startswith(f"### Story {sid} (") or ln.startswith(f"### Story {sid}:"):
            start = i; break
    if start is None:
        return None
    end = len(epics)
    for j in range(start + 1, len(epics)):
        s = epics[j]
        if s.startswith("### Story ") or s.startswith("## Epic") or s.startswith("## "):
            end = j; break
    block = epics[start:end]
    while block and (block[-1].strip() == "" or block[-1].strip() == "---"):
        block.pop()
    return "\n".join(block)

def dw_blocks(sid):
    out = []
    i = 0
    while i < len(dw):
        ln = dw[i]
        if ln.startswith(f"## DW-{sid}-") or ln.startswith(f"## DW-{sid} ") or ln.strip() == f"## DW-{sid}":
            j = i + 1
            while j < len(dw) and not dw[j].startswith("## "):
                j += 1
            blk = dw[i:j]
            while blk and blk[-1].strip() == "":
                blk.pop()
            out.append("\n".join(blk))
            i = j
        else:
            i += 1
    return out

def git_body(sha):
    try:
        return subprocess.run(["git","-C",str(ROOT),"show","-s","--format=%b",sha],
                              capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""
def git_subject(sha):
    try:
        return subprocess.run(["git","-C",str(ROOT),"show","-s","--format=%h %ad %s","--date=short",sha],
                              capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return sha

date = datetime.date.today().isoformat()

# ---------- Deliverable 3: epics-only ----------
d3 = [f"""# pyforge-atlas — B9–H4 story definitions (epics.md, verbatim)

> The 20 stories from Waves B9→H4 that were **never** emitted as individual
> story files (those waves ran through the in-session agent loop, not
> `bmad-create-story`). This is their authoritative Tier-2 spec content,
> extracted **verbatim** from
> `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md`, plus the
> matching `deferred-work.md` (DW-*) ledger entries. No fabrication — every line
> below is copied from a real planning artifact.
>
> Generated: {date}. For the full-detail B1–B8 story files see
> `ATLAS-BMAD-SPECS-CONSOLIDATED.md`.

---
"""]
for sid in IDS:
    eb = epics_block(sid) or f"*(No epics.md block found for {sid}.)*"
    d3.append(f"## Story {sid}\n\n{eb}\n")
    dws = dw_blocks(sid)
    if dws:
        d3.append(f"**Deferred-work ledger ({sid}):**\n\n" + "\n\n".join(dws) + "\n")
    d3.append("---\n")
(OUTDIR / "ATLAS-B9-H4-EPICS-DEFINITIONS.md").write_text("\n".join(d3), encoding="utf-8")

# ---------- Deliverable 1: epics + DW + PR/commit evidence ----------
d1 = [f"""# pyforge-atlas — B9–H4 story specs with implementation & review evidence

> The 20 Wave B9→H4 stories, reconstructed **only from real sources** — no
> invented `Dev Agent Record` / `Review Triage Log` sections (those were never
> authored; these waves ran through the in-session loop, not `bmad-create-story`).
>
> Per story: (1) the **verbatim epics.md binding definition**; (2) the matching
> **deferred-work.md** entries; (3) the **implementation evidence** — merged PR
> number + real git commit subjects/bodies. Fuller review-thread detail lives in
> each linked PR on GitHub.
>
> Generated: {date}. Repo: rxm7706/local-recipes.

---
"""]
for sid in IDS:
    pr, shas = STORY_PR[sid]
    d1.append(f"## Story {sid} — PR {pr}\n")
    eb = epics_block(sid) or f"*(No epics.md block found for {sid}.)*"
    d1.append("### Binding definition (epics.md, verbatim)\n\n" + eb + "\n")
    dws = dw_blocks(sid)
    if dws:
        d1.append("### Deferred-work ledger\n\n" + "\n\n".join(dws) + "\n")
    # PR evidence
    d1.append(f"### Implementation evidence (PR {pr})\n")
    d1.append(f"Merged PR: `rxm7706/local-recipes{pr}`. Commits:\n")
    for sha in shas:
        d1.append(f"- `{git_subject(sha)}`")
    d1.append("")
    body = git_body(shas[0])
    if body:
        d1.append(f"<details><summary>Primary commit body (`{shas[0]}`)</summary>\n\n```\n{body}\n```\n</details>\n")
    d1.append("---\n")
(OUTDIR / "ATLAS-B9-H4-SPECS-WITH-PR-EVIDENCE.md").write_text("\n".join(d1), encoding="utf-8")

for f in ["ATLAS-B9-H4-EPICS-DEFINITIONS.md","ATLAS-B9-H4-SPECS-WITH-PR-EVIDENCE.md"]:
    p = OUTDIR / f
    print(f"{f}: {p.stat().st_size:,} bytes")
missing = [s for s in IDS if epics_block(s) is None]
print("Stories with no epics block:", missing or "none")
print("DW coverage:", {s: len(dw_blocks(s)) for s in IDS})
