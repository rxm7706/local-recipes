---
title: "Test Architecture — pyforge-genesis"
type: test-architecture
date: 2026-08-02
version: 2.0.0
status: final
scope: "None — constitutive project, ships no product"
---

# Test Architecture — PyForge Genesis

## This tier has nothing to test, and says so

`pyforge-genesis` is the **constitutive** project (see
`prds/prd-pyforge-genesis-2026-07-28/prd.md`): it records the operating model — the
Charter, the Lexicon, the Guild's membership — and ships no product. A test
architecture describes *how a product's behavior is verified*; there is no
product here, so there is nothing to describe.

There is no `src/pyforge_genesis` package and no CLI. The installer that
bootstraps this model into other repos (`genesis init` / `genesis adopt`) is
buildable work that moved to **Marshal** in the 2026-07-28 split
(`pyforge-marshal` · `spec-genesis-installer`) — its test architecture lives
there, not here.

The one artifact this project produces — the master vision deck
(`presentations/pyforge-genesis/`) — is a static Vite/React build with no test
script and no test files of its own; it is verified the way every deck in the
`presentation-deck` workflow is, by rendering it and by
`bmad_drift_check.py`/`dream_chain_check.py` catching drift between the deck's
claims and the live repo, not by a pytest suite.

## If this ever gains a test surface

It would mean the constitutive project had acquired buildable code — which is
the same signal the PRD names: check whether that work belongs to a Smith
instead. A previous version of this file described unit/integration/E2E
coverage targets for an "installer" and "environment provisioning" that were
never Genesis's to build; that content was fabricated by a 2026-08-02 bulk
template commit and is corrected here, not carried forward.

**Last updated**: 2026-08-02
