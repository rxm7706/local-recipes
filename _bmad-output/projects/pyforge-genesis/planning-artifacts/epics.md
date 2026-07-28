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

The installer's 8 epics — Foundation & the Write Guard, the Managed-Region Engine, Detect &
Plan, and the rest — moved to `pyforge-marshal` as `epics-genesis-installer.md` when the
buildable half split out on 2026-07-28. If epics reappear here, that is the signal to check
whether buildable work has drifted back into the constitutive project.
