# Sentinel — repatriated evidence & provenance map

Companion assets for the [`sentinel`](../../dreams/sentinel.md) Dream. On 2026-04-19 the
Sentinel v2.1 effort produced a complete, reviewer-ready release — and never
landed in any repository. These files are the recovered evidence, pulled through
the Design↔Code bridge on 2026-07-23.

## Repatriated here (byte-exact intent, entity-decoded)

- **`COMMIT_MSG.txt`** — the canonical commit message that was never committed:
  the full ADR ledger (11 deltas folded; 39 ADRs total), the Apache-2.0 license
  bar, the WASM/airgap branch (§36–§41).
- **`PR_BODY.md`** — the reviewer-ready PR body: fold-in table, ADR ledger,
  reviewer checklist, the move script, open questions (§B).

## Deliberately left at the source (pull on activation)

Design project **"LLM Knowledge Bases"** (`fca0375d-4244-41e5-afae-fb59992ce346`):

| Artifact | Size | etag (2026-07-23) | Deferred because |
|---|---|---|---|
| `Sentinel-Build-Spec-vlatest.md` (v2.1, 764 lines) | 55,958 B | `1776603674091669` | The activation input for Sentinel's future `bmad-spec` run — pull byte-exact then; etag makes any drift detectable now |
| `Sentinel-Engineering-Deck-v2026-04-19-2.html` (18 slides) | 31,854 B | `1776605127396593` | Decks live on the Design surface by the bridge model |
| `Sentinel-Stakeholder-Deck-v2026-04-19-2.html` (12 slides) | 19,017 B | `1776605110286489` | ditto |
| `LLM Knowledge Bases.html` (origin essay deck) | 113,016 B | `1776608402058367` | ditto |
| `archive/` (6 superseded docs + index) | ~260 KB | — | Superseded by v2.1 (its header folds them in) |
| `tokens/` + `scripts/` (design-tokens pipeline) | ~45 KB | — | Claimed by [`modernist-identity`](../../dreams/modernist-identity.md) / [`deckcraft`](../../dreams/deckcraft.md) — lands with deckcraft's intake |
| `screenshots/`, `uploads/` (incl. 6.7 MB PNG) | ~8 MB | — | Binaries; regenerable/reference only |

## Provenance

Origin: a 2026-04-18 essay on LLM-powered personal knowledge bases → deck
("dark terminal" aesthetic) → 24 hours later, the consolidated v2.1 build spec
(BMAD-METHOD v6.3.x, spec-kit format, "Ready for Implementation"). Methodology
and full lineage: the [`sentinel`](../../dreams/sentinel.md) Dream.
