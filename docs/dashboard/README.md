# Program console — Warden + Atlas

A single-page, self-contained status console for the bmad-loop build program:
per-project story/epic progress, gates, velocity, and delivery-timing metrics,
with a project toggle (Warden / Atlas). Theme-aware, no external assets.

This **complements — does not replace** the official BMad Method UI
(`bmad-dashboard` VS Code extension + MyBMAD, packaged in the `bmad-ui` pixi
env). That tool is the *live, per-project* view (kanban, active-story tracking,
"next action" hints) driven straight off `_bmad-output/`. This console is the
*curated cross-project* view — both projects in one frame, plus timing/velocity
the official UI doesn't show — meant to be committed, hosted, and shared.

## Layout (data / shell split)

| File | Role |
|---|---|
| `index.html` | Render **shell** — all CSS + render logic. Loads `data.js`, renders `window.DASHBOARD_DATA`. Never holds data. |
| `data.js` | The **data** — `window.DASHBOARD_DATA = { projects, snapshot, defaultProject }`. Hand-curated narrative (titles, timing, gatenotes, roadmap) + per-story status. |
| `generate.py` | Refreshes each story's **status** + the snapshot timestamp in `data.js` from the live `sprint-status.yaml` files. |
| `../../.github/workflows/dashboard.yml` | Publishes this folder to GitHub Pages; regenerates data (git mode) at deploy time. |

Everything except per-story status and the timestamp is authored by hand in
`data.js` — the generator only syncs those two.

## Two refresh modes

`generate.py --source {sprint-status,git}`:

| | `sprint-status` (default) | `git` |
|---|---|---|
| Runs where | **Locally** (sources are gitignored) | **CI** (and locally) |
| Reads | `sprint-status.yaml` per project | `main`'s commit subjects |
| Sets | full status: done / **active** / **gated** / pending | **done only** — upgrades, never downgrades |
| Sees in-flight? | yes (active / gated) | no — in-flight shows as its committed baseline until its merge commit lands |
| Richness | richest | hands-off |

### Local refresh (richest — shows in-flight & gated)

```bash
python docs/dashboard/generate.py      # or: pixi run dashboard-gen
git add docs/dashboard/data.js && git commit -m "dashboard: refresh status" && git push
```

`sprint-status.yaml`
(`_bmad-output/projects/<slug>/implementation-artifacts/…`) is Tier-3
**gitignored / local-only**, so this mode is local-only. It syncs full status,
so it can also *downgrade* — it's only as current as that file. A project driven
live by bmad-loop (Warden) keeps its sprint-status current. A project whose real
status is *merged PRs* while its local sprint-status lags (Atlas, at time of
writing) will be synced to the **lagging** view — bring its sprint-status.yaml up
to date first, or edit that project's statuses directly in `data.js`.

### CI / hands-off (fully automatic)

`.github/workflows/dashboard.yml` runs `generate.py --source git` **at deploy
time** against a full-history checkout, then publishes to GitHub Pages. The site
**auto-refreshes on every push to `main` and daily (cron)** — a story flips to
`done` on the live site as soon as its merge/story commit lands on `main`, with
**no bot commit-back** (which would loop). `git` mode only *upgrades* to done and
never downgrades, so the committed `data.js` acts as the **seed / floor**: it
carries the curated narrative plus any status git can't derive (in-flight/gated,
or a story landed via a commit that doesn't match the done-detection patterns).

Done-detection patterns (`main` commit subjects):
- Warden — `Merge bmad-loop/<run-id>/<X-Y>-…` → id `X.Y`
- Atlas — `story(<id>)` (e.g. `story(B10)`, `story(0.1)`) and bare `GN:` / `HN:`

## Reuse in another repo

1. Copy `docs/dashboard/` and `.github/workflows/dashboard.yml`.
2. In `generate.py`, edit `PROJECT_SOURCES` (sprint-status mode) and, for the
   hands-off CI mode, the `MAIN_BRANCH` constant + the `_WARDEN_DONE` /
   `_ATLAS_*` done-detection regexes to match the new repo's commit conventions.
3. Re-seed `data.js`: replace the `projects` object with your own project/epic/
   story structure (each story is `[id, status, title, ...optional chip]`;
   optional `timing`, `velocity`/`roadmap`, `inflight` blocks per project — see
   the Warden/Atlas entries as templates), then run `generate.py` to sync status.
4. Enable GitHub Pages (Settings → Pages → Source: GitHub Actions).
