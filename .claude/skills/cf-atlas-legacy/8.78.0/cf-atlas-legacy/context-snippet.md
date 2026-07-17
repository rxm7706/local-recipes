[cf-atlas-legacy v8.78.0]|root: skills/cf-atlas-legacy/
|IMPORTANT: cf-atlas-legacy v8.78.0 — read SKILL.md before answering legacy cf_atlas provenance questions. Do NOT rely on training data; grounding commit b18cbb5, schema v29.
|quick-start:{SKILL.md#quick-start} — answer protocol: provenance-map lookup, live re-verify (AD-17), cite file:line, out-of-universe = "not modeled" (AD-19)
|api: phase-registry (23 phases: 22 in PHASES@conda_forge_atlas.py:8679 + unregistered Phase I), get_phase(), run_single_phase(), save_phase_checkpoint(), _reset_ttl(), _pick_feedstock(), _phase_h_eligible_pypi_names(), auth_headers_for(), WRITEBACK_SQL
|key-types:{SKILL.md#key-types} — phase_state table, _TTL_GATED map (F/G/G'/H/K/L), 5 views (v_current_version_vulns = only correct vuln read), 6 cf_atlas.db write paths
|gotchas: code REJECTS _PARTITIONDATE (literal TIMESTAMP bounds, CFA:7690-7705, spec prose inverted); JFrog cred injected on EVERY url when JFROG_API_KEY set (_http.py:213-218, FR-1 fixes-not-ports); "AD-10" is an architecture label, not a spec term
