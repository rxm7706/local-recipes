---
marp: true
paginate: true
size: 16:9
title: Mason — we forge the blocks, we ship the structure
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

MASON · The Artisan · pyforge crew chapter · Dream: `docs/dreams/packaging-factory.md`

# we forge the blocks.<br>we ship the structure.

Mason is the **practical builder** of the factory — once Atlas has mapped the landscape and Warden has cleared the perimeter, Mason binds raw software ingredients into **concrete, production-ready structures**. Behind the persona stands a working forge: **769 feedstocks**.

| Role | Motto | Toolchain | Scale |
| --- | --- | --- | --- |
| Package artisan | "We forge the blocks. We bind the environment. We ship the structure." | rattler-build · pixi | 769 feedstocks |

---

<!-- _class: dark -->

## Act I

# The Artisan

After the map and the perimeter comes the binding: **raw ingredients into unyielding structures.**

---

## Dual-ecosystem mastery

**PyPI and Conda are complementary building blocks, not rivals.**

PyPI for fast pure-Python agility; Conda for heavy analytics, compiled C-extensions, and hardware-accelerated platforms. Mason works both sides of the wall as one craft.

---

## Structural integrity

Mason rejects brittle runtime environments. Everything is **deterministic, binary-compatible, reproducible** — developer needs converted into unyielding cross-platform structures.

---

<!-- _class: dark -->

## Act II

# The craft

Recipes, releases, and environment binding.

---

## The three crafts

| Craft | What it is |
| --- | --- |
| **Recipe crafting** | v1 `recipe.yaml` — selectors, multi-outputs, skips, patches; the 10-step gated lifecycle |
| **Library distribution** | one release → wheel **and** conda package, simultaneously |
| **Environment binding** | unified lockfiles across pip and conda; one lockfile, every platform |

```
mason recipe craft --source pypi:<pkg> --target conda-forge
mason package --ship conda-forge
mason env bind --lock pixi.lock --platforms linux-64,osx-arm64,win-64
```

---

<!-- _class: dark -->

## Act III

# The forge today

Unlike most visions, Mason's forge **already runs at scale** — the AI-assisted conda-forge packaging factory behind this repo.

---

## A working forge

**769 maintained feedstocks** · the full staged-recipes lifecycle from generation to PR submission · the modern **rattler-build + pixi** toolchain · 106 hard-won gotchas encoded in the conda-forge-expert skill · campaigns: bulk refresh, platform expansion, failure remediation.

---

## Ship to both worlds

One release, two registries — the same library lands as **wheel and conda package** from one synchronized pipeline; one lockfile serves every platform. **Downstream usability, maximized.**

---

<!-- _class: lead -->

## The creed

# We forge the blocks. We bind the environment. We ship the structure.

Then the pristine artifacts go to Herald — for the proclamation.

Mason · pyforge crew · Dream to Code
