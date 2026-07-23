---
marp: true
size: 16:9
paginate: true
theme: default
style: |
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
  section { background:#F6F4EE; color:#0E1C30; font-family:'IBM Plex Sans',sans-serif; font-size:26px; padding:70px 90px; }
  h1 { font-family:'Space Grotesk',sans-serif; font-weight:600; font-size:50px; line-height:1.07; letter-spacing:-0.02em; margin:0 0 0.4em; }
  h2,h3 { font-family:'Space Grotesk',sans-serif; font-weight:600; letter-spacing:-0.01em; }
  h6 { font-family:'IBM Plex Mono',monospace; font-weight:500; letter-spacing:0.22em; text-transform:uppercase; color:#2F86DD; font-size:15px; margin:0 0 0.2em; }
  strong { color:#C8901A; font-weight:600; }
  code { font-family:'IBM Plex Mono',monospace; background:rgba(14,28,48,0.08); padding:1px 5px; border-radius:4px; }
  a { color:#2F86DD; }
  hr { border:none; border-top:3px solid #0E1C30; margin:.4em 0; }
  table { font-size:.82em; border-collapse:collapse; }
  th { background:#0E1C30; color:#F6F4EE; text-align:left; }
  th,td { border:1px solid #D8D3C7; padding:6px 10px; }
  section::after { color:#8A94A3; font-family:'IBM Plex Mono',monospace; font-size:14px; }
---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### A FIELD GUIDE FOR ENGINEERS · EXECUTIVE SUMMARY

# Build software with AI agents — as collaborators, not autocomplete.

### One structured process. Idea to shipped code.

Agentic AI across the SDLC replaces prompt-and-pray with a **spec-driven process**: specialist agents run each phase — analysis, planning, solutioning, build — while humans direct and gate through documents they can read and review. The concrete framework is the open-source **BMAD Method**.

<!-- Executive one-slide summary. The agentic AI-SDLC is a structured, spec-driven way to build software with AI agents; BMAD is the working framework this deck teaches. -->

---

## Why it matters — three outcomes

**Structure beats prompting**
A repeatable process — analyze → plan → design → build — yields reviewable decisions and documents, not average code from vague context. Built for systems, not just snippets.

**Documents are the brain**
Specs carry state between phases; agents are transient workers that read and write them. Open a fresh chat and the team resumes from the files in git — no leaky chat memory, no key-person knowledge.

**Ceremony sized to the work**
A bug fix gets three commands; an enterprise system adds security and compliance reviews. A human stays in the loop and chooses how tight the automation runs.

---

## The numbers

| Metric | Value |
| --- | --- |
| Phases · narrative acts | **4 · 6** |
| Named specialist agents | **6** |
| Installable `bmad-*` workflows | **34+** |
| License · cost | **MIT · $0** |

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

## Fix the doc, not the code

Wrong output is an upstream spec flaw — correct the document and rerun; don't patch the code. The lifecycle is a funnel of increasing resolution — **why → what → how → build** — and no agent writes code until the *what* and the *how* are frozen in a text file.

**Don't hand off your judgment. Give it a structure to work in.**

Agentic AI-SDLC · BMAD Method · docs.bmad-method.org
