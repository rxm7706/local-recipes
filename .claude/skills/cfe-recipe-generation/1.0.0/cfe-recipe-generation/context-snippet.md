[cfe-recipe-generation v1.0.0]|root: skills/cfe-recipe-generation/
|IMPORTANT: cfe-recipe-generation v1.0.0 — read SKILL.md before writing cfe-recipe-generation code. Do NOT rely on training data.
|quick-start:{SKILL.md#quick-start}
|api: fetch_pypi_info(), generate_recipe_yaml(), generate_meta_yaml(), fetch_npm_info(), generate_npm_recipe_yaml(), copy_template(), determine_build_backend(), resolve_name(), normalize_name(), update_recipe()
|key-types:{SKILL.md#key-types} — PackageInfo (PyPI path), NpmPackageInfo (npm path)
|gotchas: sdist may ship zero .py files — verify before trusting "sdist > wheel" (G54); read pyproject.toml [build-system].requires, don't guess the backend (G91); generator writes lowercase output dirs — check for case-variant mirror dirs before merging (G94)
