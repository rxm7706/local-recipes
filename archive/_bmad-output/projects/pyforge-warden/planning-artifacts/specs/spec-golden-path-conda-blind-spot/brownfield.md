# Brownfield — the live surfaces this spec changes or preserves

Verified against `main` on 2026-09-05 (line numbers as of that day).

| Surface | What it does today | Spec |
|---|---|---|
| `scripts/platform-golden-path-promotion.sh` | Copies the workspace `pixi.toml` (no lock) into `mktemp -d`/workspace and runs `warden scan <scratch> --format json`; its own comment (lines 12–15) records why: Warden has no per-environment selector and its lock reader does not accept this workspace's `pixi.lock`. Writes `warden_status` from the report's `status.value`. | CAP-2 replaces the staging with a scoped scan of the root `pixi.lock`. |
| `src/shared/packages/pyforge-warden/src/pyforge/warden/extract/lockfiles.py::PixiLockExtractor` | Walks the lock's `packages:` list — every environment/platform the file ever resolved, no selection (module docstring lines 51–55, class docstring 184–185; a deliberate Story 2.2 scope decision). | CAP-1 adds one-env / one-platform selection; the union stays for unscoped calls. |
| `.github/workflows/platform-ci.yml` → `golden-path-promotion` job | `needs: container`; installs the `pyforge-warden` env via setup-pixi; runs the script; `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` is unset (as everywhere in CI). | CAP-3 adds the explicit provisioning step. |
| `scripts/platform-deploy-verify-promotion.py` | Since `1016f4e763` (2026-09-04): refuses when `warden_status != "clean"`, naming the driver finding id; also refuses a missing artifact or an unrecorded digest. `platform-deploy.yml` runs it (line 53). The Dream's "gates on the record existing" measurement predates this commit. | CAP-5 preserves it with a regression test. |
| `planning-artifacts/osv-db-offline-provisioning-decision.md` (Story 1.4, accepted 2026-07-14) | Mechanism: `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` → `<cache>/osv-scanner/<Ecosystem>/all.zip`; provisioning order conda-packaged DB → osv-native `--download-offline-databases` → air-gap mirror; stale = `snapshot_at` strictly older than `now − db-max-age` (7 d default); unknown/absent/future-dated provenance ⇒ `indeterminate`. | Adopted companion; CAP-3 wires it, never re-derives it. |
| `specs/spec-2-1-conda-pypi-map-the-ecosystem-identity-predicate.md` (Epic 2, shipped) | Verified-confidence conda→pypi identity map. | Adopted companion; CAP-4's identity resolution. |
| First measured run (`retro-pyforge-steward-2026-09-04.md`) | `warden_status: indeterminate`, 329 components, vulnerability axis 0 assessed. | The baseline the success signal is measured against. |
