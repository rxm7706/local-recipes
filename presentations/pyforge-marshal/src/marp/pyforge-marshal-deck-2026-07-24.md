---
marp: true
paginate: true
size: 16:9
title: Marshal — enforce the spec, run the line
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.dark { background:#201e1d; color:#f3f2f2; }
  section.dark h1, section.dark h2, section.dark h3, section.dark code { color:#f3f2f2; }
  section.dark strong { color:#ec3013; }
  hr { border:none; border-top:3px solid #201e1d; margin:.4em 0; }
  table { font-size:.78em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- 01 · Cover -->

MARSHAL · The Commander · pyforge crew chapter · Dream: `docs/dreams/pyforge-marshal.md`

# enforce the spec.<br>run the line.

Marshal is the commanding operational authority of the Dream-to-Code factory — the **BMAD-method orchestrator** that turns a solidified Dream into **validated code**, without vibe coding.

| Role | Motto | Method | Autonomy |
| --- | --- | --- | --- |
| Build-factory supervisor | "Enforce the spec. Guard the boundaries. Run the line." | BMAD · bmad-loop | graduated, gated |

---

<!-- _class: dark -->

## Act I

# The Commander

While **Atlas** charts the map, **Warden** secures the perimeter, and **Mason** binds the packages — **Marshal runs the heavy automated machinery** of the factory floor.

---

## Anti-vibe pragmatism

Marshal operates entirely on **strict structural inputs**. "Good intentions" and "close enough" do not exist.

A sub-agent that deviates from the spec is **flagged instantly** and forced into a corrective iteration — the review lenses hunt, the verify gate decides, the merge subject records it.

---

## Ruthless context containment

Each sub-agent receives **only the exact context its task requires**.

Containment kills hallucination and keeps the line fast — targeted instruction blocks, isolated story worktrees, per-story budgets.

---

<!-- _class: dark -->

## Act II

# The bmad-suite

The full BMAD stack Marshal orchestrates — official modules, web bundles for flat-rate planning, community plugins, and the autonomy layer.

---

## One method, five modules

| Module | What it drives |
| --- | --- |
| **BMM** | the core — 34+ workflows |
| **BMB** | BMad Builder — custom agents & workflows |
| **TEA** | Test Architect — risk-based test strategy |
| **BMGD** | Game Dev Studio |
| **CIS** | Creative Intelligence |

Plus **web bundles** (Gemini Gems · Custom GPTs) for flat-rate upfront planning, **community plugins** (skill-forge), and the **autonomy layer**: `bmad-loop` + `bmad-dev-auto`.

---

<!-- _class: dark -->

## Act III

# Running the line

How a spec becomes validated code — and how the whole run stays visible.

---

## The factory loop

**Spec marshalling** — the Dream, solidified into targeted instruction blocks per story.

**Agent mobilization** — tactical sub-agents spawned per role: dev, review lenses, triage.

**Defect containment** — failed test output piped back as explicit self-healing instructions; escalation pauses, never guesses.

```
marshal init --spec ./docs/system_spec.md
marshal factory spin --pipeline standard --target ./src
bmad-loop run --story 6.3 --max-stories 1   # gates: per-story-spec-approval
```

---

## Every run stays visible

As bmad-loop drives epics and stories, the **program console** is kept current and published on **GitHub Pages** — deliveries, notables, roadmaps and updates marshalled from the same run state.

**Nothing invisible ships** — merge subjects, sprint feeds, and run journals are the ledger; the dashboard is derived, never hand-trusted.

---

<!-- _class: lead -->

## The creed

# Validated code, not vibes.

The Dream deserves better than vibes. Marshal exists so that **what ships is what was specified** — enforced, contained, validated. Then the line hands off: Atlas maps, Warden guards, Mason ships.

Marshal · pyforge crew · Dream to Code
