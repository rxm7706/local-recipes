# The planning-artifacts exemplar standard

**Reference implementation: `projects/pyforge-atlas/planning-artifacts/`.**
Established 2026-07-27. Applies to every BMAD project in this repo under
bmad-method ≥ 6.10 with bmad-loop.

This document is the conformance target. When it and pyforge-atlas disagree,
**pyforge-atlas is right and this document is stale** — the exemplar is a working tree,
not a specification of one.

---

## Why a standard

Fourteen projects live under `_bmad-output/projects/`, built across three different BMAD
eras. They diverged in shape, not just content: some carry a flat `prd.md`, some a dated
`prds/<run>/` folder; some have story specs, some have stubs; one has a deferred-work
ledger and the rest do not. Divergence is fine while a project is in flight and expensive
once you need to answer "is this project's record complete?" across all of them.

The standard exists so that question has a mechanical answer.

## The conformance table

| # | Requirement | Why it is load-bearing |
|---|---|---|
| **1** | PRD lives in `prds/prd-<slug>-<date>/` with `prd.md`, `.memlog.md`, and any `addendum.md` / `review-*.md` / `validation-report.*` | This is what `bmad-prd` binds (`{prd_output_path}/{run_folder_pattern}/`). A flat `prd.md` is pre-6.10 `bmad-create-prd` output — a deprecated wrapper slated for removal in v7. |
| **2** | Architecture lives in `architecture/architecture-<slug>-<date>/ARCHITECTURE-SPINE.md` with its `.memlog.md` and `reviews/` | Same reason: `bmad-architecture` binds a spine run folder. A flat `architecture.md` predates the spine concept. |
| **3** | Core docs carry `status` / `created` / `updated` frontmatter | `stepsCompleted:` alone records *which workflow steps ran*, not whether the document is final. Only the former survives a reader who wasn't there. |
| **4** | A Spec kernel exists at `specs/spec-<slug>/SPEC.md` | The Spec is the unit of contract. The planning chain decomposes it; it does not replace it. |
| **5** | Companions are **peer contracts** in the kernel directory; `companions:` frontmatter lists only those; the chain (PRD / spine / epics) lives in `sources:` | Two different relationships. Conflating them makes "what is normative?" unanswerable. |
| **6** | Every kernel Constraint that compresses an enumeration cross-references its companion inline | A companion nobody is pointed to is documentation, not contract. |
| **7** | Per-story specs are tracked in `specs/`, never left in gitignored `implementation-artifacts/` | In a spec-driven build the spec *is* the contract. Tier-3 specs die on worktree teardown — this has already cost this repo real artifacts twice. |
| **8** | Every story has a delivery record — in its spec and in `epics.md` | Otherwise the planning chain reads as pre-implementation forever, no matter what shipped. |
| **9** | The deferred-work ledger is tracked in `planning-artifacts/` | The bmad-loop ledger is Tier-3 and gets truncated. If it matters after the run, it belongs in Tier-2. |
| **10** | `planning-artifacts/README.md` explains the layout and any deliberate asymmetry | The next reader is an agent with no session context. |

## The kernel/companion rule

> If a normative claim in the kernel cannot be reviewed or refuted without an enumeration,
> that enumeration is a **companion** — a contract, not documentation.

Worked examples from the exemplar:

| Kernel claim | Without the table | Companion |
|---|---|---|
| "TTLs are declared per dataset, never a global constant" | unverifiable | `catalog-contract.md` |
| "Gates are never weakened, and the verify set only grows" | unenforceable against an unenumerated set | `gate-contract.md` |
| "The legacy phases survive the port with their contracts intact" | names no contract | `signals.md` |
| "Three markers, never interchanged" | three words that look like synonyms | `degradation-contract.md` |

The pattern originates in `pyforge-warden` (`verdict-contract.md` / `axes.md` /
`extraction-contract.md`); pyforge-atlas is where it was generalized.

**Companions hold tables; the kernel holds the compressed normative sentence.** A companion
that argues rather than enumerates has drifted into being a second kernel.

## Provenance rules

These are the ones most likely to be violated with good intentions.

1. **Never fabricate a session record.** A `Dev Agent Record` or `Review Triage Log` describes
   something that happened. If the session never emitted one, say so and supply a
   `## Delivery Record` derived from durable evidence (PR body, merge date, commit list, exact
   file list from the diff) — labeled as derived.
2. **Recovered originals are not normalized.** If a spec was recovered verbatim, it keeps its
   original shape and its `<!-- RECOVERED … -->` banner even when siblings look different.
   Uniformity is worth less than provenance. Document the asymmetry instead of erasing it.
3. **Derive counts; do not restate them.** Every number in a companion should be reproducible
   from the code or the API. The exemplar's "86 datasets / 7 pipelines / 7 gates" came from
   `catalog.yml` and `pixi.toml`, and the kernel's own "six gates" prose was found wrong
   against it.
4. **Corrections stay on the record.** When a claim is found wrong, correct it *and* say what
   it used to say and why it was wrong. The exemplar's ledger and SPEC both carry dated
   corrections rather than silent edits.

## Conformance status

| Project | 6.10 shape | Spec kernel | Companions | Story specs | Delivery records | DW ledger | README |
|---|---|---|---|---|---|---|---|
| **pyforge-atlas** | ✅ | ✅ | ✅ 4 | ✅ 32 | ✅ 32/32 | ✅ 52 | ✅ |
| pyforge-warden | ❌ flat | ✅ | ✅ 3 | ✅ 31 | ❌ | ❌ | ❌ |
| pyforge-doctor / mason / herald / scribe / steward | ✅ | ✅ | ❌ | partial | ❌ | ❌ | mostly ✅ |
| pyforge-marshal / genesis / deckcraft | ❌ flat | ✅ | ❌ | partial | ❌ | ❌ | partial |

Warden is the closest and the cheapest to finish: reshard `prd.md` → `prds/prd-pyforge-warden-<date>/`,
regenerate `architecture.md` as an `ARCHITECTURE-SPINE.md` run folder, and back-fill delivery
records from PR #110. Its companion pattern and story-spec fidelity already exceed the bar.

## Verifying conformance

No detector exists yet — `scripts/bmad_drift_check.py` covers the `local-recipes` project only.
Adding a `--projects` mode that checks items 1–10 across all fourteen is the natural next step,
and is the difference between a standard that holds and a standard that decays.

Until then, the mechanical checks the exemplar was verified with:

```bash
# companions all exist and are all cross-referenced from the kernel
python3 - <<'PY'
import yaml, re, pathlib
p = pathlib.Path('specs/spec-<slug>')
t = (p / 'SPEC.md').read_text()
fm = yaml.safe_load(t.split('---')[1])
body = t.split('---', 2)[2]
refs = set(re.findall(r'`([a-z-]+\.md)`', body))
for c in fm['companions']:
    print(('OK  ' if (p / c).exists() else 'MISS'), c, '| referenced' if c in refs else '| NOT REFERENCED')
PY

# every story has exactly one contract, and no spec carries a sibling's
grep -c '^### Story ' specs/spec-*.md

# nothing Tier-3 became tracked
git status --porcelain | grep implementation-artifacts

# the switch is not desynced before any write-skill runs
scripts/bmad-switch --current && readlink -f _bmad-output/planning-artifacts
```
