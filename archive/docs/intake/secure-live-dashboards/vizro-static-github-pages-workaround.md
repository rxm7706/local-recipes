# Static workaround for Vizro dashboards via GitHub Pages — technical specification (intake, v1.0)

> **Intake material.** Externally authored, captured verbatim in substance on 2026-08-09.
> Second source for `docs/dreams/secure-live-dashboards.md`, alongside
> `role-based-live-dashboard-blueprint.md`. Recorded as given — the tension it creates with
> the live/RLS blueprint is flagged at the bottom but **not resolved here**; that is the Spec
> and architecture phase's job.
>
> Framing note: the blueprint intake describes the **hosted** delivery of a Vizro dashboard.
> This document describes the **static** delivery of the same dashboard. The Dream's scope is
> that one dashboard definition can be delivered either way.

---

## 1. Background

Vizro relies on a live Python (Flask/Dash) backend for server-side calculation, data filtering
and UI updates. **GitHub Pages hosts static assets only** — HTML, CSS, JavaScript — and cannot
run a Python server, so a dynamic Vizro deployment fails there out of the box.

**The workaround:** export individual Plotly chart components as static HTML assets and
assemble them into a responsive layout. Client-side interactivity that Plotly provides in the
browser — hover tooltips, zoom, pan — is preserved without a Python server.

## 2. Mission

Build an automated Python workflow that converts Vizro chart components into static HTML files,
injects them into a responsive grid template, and deploys the bundle to GitHub Pages.

**Core goal:** free dashboard hosting on GitHub Pages while retaining basic front-end chart
interactivity.

## 3. Actions

**Action 1 — extract components from the Vizro architecture.** Isolate the underlying Plotly
configurations (`vm.Graph(figure=...)`) from the server-dependent container layout. Store the
source dataframe structures directly in a local script, or load them via fixed CSV URLs.

**Action 2 — write the export script (`build_static.py`).** Generate the individual layout
graphs. Convert components to HTML strings with
`fig.to_html(full_html=False, include_plotlyjs='cdn')` to keep file sizes small.

**Action 3 — create the HTML/CSS grid template.** A responsive HTML wrapper mimicking Vizro's
minimalist aesthetic. Inject the generated raw chart HTML fragments into structural template
placeholders.

**Action 4 — configure automation and deployment.** A GitHub Actions workflow runs the build
script on every repository push and commits the generated static directory to the `gh-pages`
branch.

## 4. Client-side interactivity extension (optional)

**Strategy.** To mimic Vizro's dynamic filtering without a server, **embed the data for all
possible states directly into the client-side JavaScript layer**. DOM UI elements (dropdowns,
checkboxes) listen for user input events and call custom JavaScript functions that manipulate
the Plotly charts in real time via the `Plotly.react()` API.

**Action 5** — export data matrices directly into JSON strings during the Python build step.
**Action 6** — build JavaScript event-listener hooks to catch UI state changes.
**Action 7** — write a client-side update loop that safely redraws Plotly instances using
`Plotly.react()`.

---

## Tensions and gaps recorded for the Spec phase

These are **not** resolved here.

- **Section 4 is incompatible with row-level security, by construction.** "Embed the data for
  all possible states directly into the client-side JavaScript layer" means every role's rows
  ship to every browser, and the dropdown is presentation. That is the exact thing the
  blueprint intake's own constraint forbids — *the absent UI control is never the access
  control* — taken to its limit, because the data is in the page. A dashboard delivered this
  way cannot also be role-isolated.
- **Section 3 Action 1's "fixed CSV URLs" is a second exposure path.** A URL the browser can
  fetch is a URL anyone can fetch. Whatever it serves is public.
- **No audit trail is possible.** There is no server to record who loaded what, so the
  blueprint's `dashboard_audit_trail` and its row-count guarantee have no counterpart here.
- **`include_plotlyjs='cdn'` introduces a third-party runtime dependency** fetched by the
  viewer's browser at load time. It keeps the bundle small, and it means the page does not
  work air-gapped and executes code from a host the estate does not control — relevant given
  `spec-enterprise-airgap` is a neighbouring Steward surface.
- **Freshness is push-shaped.** Data is as current as the last build, so the blueprint's
  15-minute refresh cycle, manual refresh control and F5-triggered refresh have no meaning in
  this mode; "refresh" becomes "re-run CI".
- **What keeps the two modes from diverging** is unaddressed. If the static export re-derives
  charts from `vm.Graph(figure=...)` by hand, the two deliveries of "the same dashboard" can
  drift into two different dashboards.
