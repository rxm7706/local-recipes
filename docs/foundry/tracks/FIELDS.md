# Track field list (marshal relay)

Frozen enumeration for one tracked `track.json` per bmad-loop / `marshal factory
spin` run (steward Story 53.3, `hub:CAP-3` / B8). Marshal supplies the
enumeration from existing run evidence (`journal.jsonl`, `gate-record.json`,
`state.json`); steward encodes the list and writes the Track. Code constant:
`pyforge.steward.track.TRACK_FIELDS`.

| Field | Required on record | Missing source |
|---|---|---|
| `run_id` | yes | directory name of the run dir |
| `timestamps.started_at` / `timestamps.ended_at` | keys present | `null` |
| `tree_revision` | key present | `null` |
| `guards` | array (may be empty) | `[]` — never inferred from policy TOML |
| `gates` | array (may be empty) | `[]` — rules/verdicts only if on the record |
| `model_adapter` | key present | `null` (do not invent version/config) |
| `human_approvals_overrides` | key present | `[]` |
| `retention` | always | `{ "track": "indefinite", "raw_payload_days": 90 }` |

Retention: the Track is kept indefinitely; the raw payload (journal, gate
record, state, logs) is retained 90 days. Both statements live on the record.

Guards and Gates must be readable from `track.json`, not reconstructed from
loop `policy.toml`.

Writer: `steward track assemble --run-dir DIR --out PATH`.
Schema: `src/shared/packages/pyforge-steward/src/pyforge/steward/data/track.schema.json`.
Example: `docs/foundry/tracks/example-track.json` (from the unit-test fixture).
