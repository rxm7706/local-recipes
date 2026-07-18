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
| `../../.github/workflows/dashboard.yml` | Publishes this folder to GitHub Pages on push to `main`. |

Everything except per-story status and the timestamp is authored by hand in
`data.js` — the generator only syncs those two.

## Refresh

```bash
python docs/dashboard/generate.py      # or: pixi run dashboard-gen
git add docs/dashboard/data.js && git commit -m "dashboard: refresh status" && git push
```

The push triggers the Pages workflow, which republishes the static folder.

**Why no CI generation:** the source of truth,
`_bmad-output/projects/<slug>/implementation-artifacts/sprint-status.yaml`, is
Tier-3 **gitignored / local-only**, so it isn't present in CI. Generation is a
local step; CI only publishes the committed result.

**Staleness caveat:** `generate.py` reads `sprint-status.yaml`, so it is only as
current as that file. A project driven live by bmad-loop (Warden) keeps its
sprint-status current, so the sync is accurate. A project whose status is really
tracked by *merged PRs* while its local sprint-status lags (Atlas, at the time
of writing) will be synced to the **lagging** view — either bring its
sprint-status.yaml up to date first, or edit that project's statuses directly in
`data.js`. The committed `data.js` reflects true (merged-PR) status, which may be
ahead of what a bare `generate.py` run would produce for such a project.

## Reuse in another repo

1. Copy `docs/dashboard/` and `.github/workflows/dashboard.yml`.
2. In `generate.py`, edit `PROJECT_SOURCES` to point at the new repo's
   `sprint-status.yaml` file(s).
3. Re-seed `data.js`: replace the `projects` object with your own project/epic/
   story structure (each story is `[id, status, title, ...optional chip]`;
   optional `timing`, `velocity`/`roadmap`, `inflight` blocks per project — see
   the Warden/Atlas entries as templates), then run `generate.py` to sync status.
4. Enable GitHub Pages (Settings → Pages → Source: GitHub Actions).
