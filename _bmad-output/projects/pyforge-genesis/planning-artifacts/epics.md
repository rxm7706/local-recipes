---
title: "Epics — pyforge-genesis (constitutive)"
status: final
created: 2026-07-28
project: pyforge-genesis
---

# Epics — pyforge-genesis

## No epics, and that is the contract

Epics decompose a Spec into buildable work. `pyforge-genesis` is the **constitutive**
project: it records the operating model and ships nothing, so there is no work to decompose.

Present because INV-3 admits no exemption — a tier stating its emptiness is auditable, an
absent one is ambiguous. See the PRD and architecture beside it for the same reasoning.

## What would decompose, if anything did

Both Specs here govern *discipline*, not delivery:

| Spec | What it governs | Why it has no epics |
|---|---|---|
| `spec-pyforge-charter` | amendment discipline; claims backed by detectors; constants in step across their readers | continuous obligation, not a work item — closer to a practice than a project |
| `spec-pyforge-genesis` | the Lexicon, membership, the Dream-tier contract | records what is, rather than commissioning what will be |

## Where Genesis's real epics went

The installer's 6 epics — Foundation & the Write Guard, the Managed-Region Engine, Detect &
Plan, and the rest — moved to `pyforge-marshal` as `epics-genesis-installer.md` when the
buildable half split out on 2026-07-28. If epics reappear here, that is the signal to check
whether buildable work has drifted back into the constitutive project.

### The split moved the epics and left the feed (found and closed 2026-07-30)

The tripwire above was written to watch this file. **The drift went somewhere it wasn't
watching.** Until 2026-07-30 this project's `sprint-status.yaml` — and its tracked twin —
still listed **all 36 installer stories**, and `bmad-loop` reads exactly that feed
(`[stories] source = "sprint-status"`), not this document. Launching the `pyforge-genesis`
loop home would have dispatched `1-1-package-skeleton-as-a-pixi-workspace-member` and begun
building a package for the project whose contract is that it ships nothing.

The feed *was* the drift this section tells you to look for; it simply never left. Both
feeds are now empty, which is the correct steady state for a constitutive project — stated
rather than left ambiguous, on the same INV-3 reasoning that requires this epics file to
exist and declare its own emptiness.

**Two things worth carrying forward:**

1. **A tier is retired only when its *execution* surface is retired too.** Epics are what a
   human reads; the feed is what the machine dispatches. Moving one without the other leaves
   a document that says "no work here" and a machine that disagrees — and the machine wins.
2. **The stories are renumbered.** They run from marshal's feed as **epics 7–12**
   (`S-7.1` … `S-12.6`), because 33 of the 36 ids collided with marshal's own `1.1`–`6.6`
   and AD-23 requires the canonical key `<epic>.<seq>` to be unique within a project — the
   loop, the journal, the spec archive, the merge subject and the dashboard all key on it.
   The epics and the execution feed live in `pyforge-marshal` as `epics-genesis-installer.md`
   — unchanged, still true, still a separate document.

**Update (2026-08-02, explicit user override):** the line above about "the PRD, architecture
and research" was already physically inaccurate by this point (they had lived under
`pyforge-marshal` since the 2026-07-28 split, never here) and is now doubly wrong: as of
2026-08-02 there is no separate installer PRD, architecture, brief, or Spec at all. All four
were **consolidated** into `pyforge-marshal`'s own single brief / PRD / architecture / Spec
(`product-brief-pyforge-marshal.md`, `prds/prd-pyforge-marshal-2026-07-25/prd.md`,
`architecture/architecture-pyforge-marshal-2026-07-25/architecture.md`,
`specs/spec-pyforge-marshal/SPEC.md`, each carrying a "Satellite: Genesis Installer" section
or continued `CAP-`/`AD-` numbering) — a direct user override of the "kept separate on
purpose" decision that had stood since the split. Only the installer's **epics** stay a
separate document, per that same override — `epics-genesis-installer.md` is untouched. The
four original standalone documents are preserved at
`archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/{research/product-brief-pyforge-genesis.md,
prds/prd-genesis-installer-2026-07-25/, architecture/architecture-genesis-installer-2026-07-25/,
specs/spec-genesis-installer/}`.
