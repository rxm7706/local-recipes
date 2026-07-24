---
marp: true
paginate: true
size: 16:9
title: Mason — the forge, at a glance
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:25px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.dark { background:#201e1d; color:#f3f2f2; }
  section.dark h1, section.dark h2, section.dark code { color:#f3f2f2; }
  section.dark strong { color:#ec3013; }
  hr { border:none; border-top:3px solid #201e1d; margin:.4em 0; }
  table { font-size:.76em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- _class: lead -->

# The forge
## Mason · The Artisan — at a glance

Raw ingredients in. **Deterministic, cross-platform structures out.** 769 feedstocks strong.

---

## A recipe's journey through the forge

| Step | Gate |
| --- | --- |
| **generate** — PyPI / npm / CRAN / CPAN / LuaRocks / GitHub source | assumptions surfaced first |
| **validate + lint** — schema, license, checksums, CI-parity | zero warnings advance |
| **scan** — OSV vulnerabilities, KEV/EPSS overlays | no unexplained criticals |
| **optimize** — 18 check codes | reviewer-grade before review |
| **build** — rattler-build, native + Docker CI-parity | green on linux-64 minimum |
| **submit** — staged-recipes or feedstock PR, template + checklist | verified strip, one review ping |

---

## Both worlds, one craft

**PyPI** — fast pure-Python agility · wheels · `pyproject.toml`.
**conda-forge** — compiled analytics + ML/AI stacks · ABI discipline · selectors, multi-outputs, per-platform matrices.
**One release → two registries; one lockfile → every platform.**

---

## The forge today

**769** maintained feedstocks · **~900** governed local mirrors · **106** encoded gotchas · **15** atlas pipeline phases feeding "what should I work on?" · campaigns for refresh, platform expansion, and red-PR remediation.

---

<!-- _class: dark -->

## The creed

Structural integrity is not optional. Deterministic, binary-compatible, reproducible — or it does not ship.

# We forge the blocks. We bind the environment. We ship the structure.
