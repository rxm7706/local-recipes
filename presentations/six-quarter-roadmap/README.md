# six-quarter-roadmap

A local twin of the **PyForge six-quarter roadmap** Claude Design project —
not one of the fourteen `pyforge-*` station decks, and not built through the
React + Vite deck-family pipeline those use. This project holds two
standalone `.dc.html` roadmap screens (no shared engine, no `npm run
extract`/`build` step) plus the Design-side bridge record; each pull lands
the file byte-exact, verbatim.

Per its own `project/github.md`, both screens are rebuilt from this repo's
own fleet data (`_bmad-output/PROJECTS.md`, per-project
`sprint-status-ledger.yaml` files, `FLEET-READINESS-*`/`DREAM-TRIAGE-*`) —
`PyForge Roadmap.dc.html` is the current, fully-detailed roadmap;
`PyForge Roadmap Deck.dc.html` is a shorter companion screen. A third file
the Design project also carries, `PyForge Roadmap Deck v1.dc.html`, is an
earlier draft `project/github.md` no longer names as a tracked screen and is
deliberately not mirrored here.

Both screens reference a `deck-stage.js`/`support.js` runtime pair and a
`_ds/modernist-fbc1d6c8-.../{styles.css,_ds_bundle.js}` stylesheet+bundle
(the Modernist design-system files they render against) by relative path,
so those are pulled too — otherwise this "local twin" would not actually
render standalone. Design's `_ds/` folder also carries embedded Broadsheet
and Nocturne copies, but neither screen references them, so they are left
unpulled (scope is "what these screens actually load", not everything
Design happens to have bundled in). A `.thumbnail` and one `uploads/*.png`
are Design-side scratch, binary, and `read_file` cannot return them at all.

## Design project (the bridge's far end)
Prototype lives in Claude Design project **"PyForge six-quarter roadmap"** (`951513af-877d-4267-8346-2bde77a3d6f1`):
https://claude.ai/design/p/951513af-877d-4267-8346-2bde77a3d6f1
