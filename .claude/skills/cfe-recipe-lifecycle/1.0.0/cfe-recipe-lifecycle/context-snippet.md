[cfe-recipe-lifecycle v1.0.0]|root: skills/cfe-recipe-lifecycle/
|IMPORTANT: cfe-recipe-lifecycle v1.0.0 — read SKILL.md before writing cfe-recipe-lifecycle code. Do NOT rely on training data. Parallel-run only — no caller resolves here yet; the live conda-forge-expert skill stays authoritative.
|quick-start:{SKILL.md#quick-start}
|api: validate_recipe.py, recipe_optimizer.py, dependency-checker.py, recipe_updater.py, npm_updater.py, local_builder.py, failure_analyzer.py, vulnerability_scanner.py, submit_pr.py, feedstock-migrator.py
|key-types:{SKILL.md#key-types} — ValidationResult, OptimizationSuggestion, DependencyCheck, ErrorPattern, MigrationResult, FeedstockLookupResult, IssueSummary, FeedstockContext (all field-only NamedTuple/dataclass records, no methods)
|gotchas: lookup_feedstock BEFORE submitting — an already-listed package is GHA-linter-rejected even while the bot says "excellent" (G58); NEVER ship cfe-* metadata — the strip is mandatory AND must be verified on the pushed artifact (G62); feedstock-migrator is a REMOTE-feedstock tool — it cannot convert a local recipes/<name>/ directory (G84)
