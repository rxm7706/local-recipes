# Herald documentation

Operator-facing documentation for the `herald` CLI and its web dashboard
(Epic 12, `pyforge-herald` PRD). All four documents assume the current,
scaled-down architecture — local JSON storage under `.herald/`, every
write triggered by an explicit CLI command, no webhook/database/cron
anywhere in this package. See
`docs/dreams/herald-moments-2-4-live-backend.md` (repo root) for the
deferred live-backend version.

- **[`operator-guide.md`](operator-guide.md)** — start here. What Herald
  is, the Four Moments, a realistic how-to per Moment with real captured
  command output, and an FAQ for the confusions this architecture
  actually produces.
- **[`cli-runbooks.md`](cli-runbooks.md)** — task-oriented walkthroughs
  (author a notice, publish a claim), the operator-role gate, and CLI-level
  troubleshooting (auth refusal, evidence-link failure at publish time,
  malformed storage, `--date-range`/`--json` usage).
- **[`web-ux-guide.md`](web-ux-guide.md)** — the web dashboard's tabs,
  filters, empty/error states, and — the single most important
  operational fact about it — how to regenerate each Moment's static JSON
  snapshot after a CLI write.
- **[`automation-troubleshooting.md`](automation-troubleshooting.md)** —
  the honestly-scoped replacement for "webhook/cron troubleshooting":
  stale evidence links (`herald success validate`), malformed local
  storage, and a stale (silently unrefreshed) web snapshot.
