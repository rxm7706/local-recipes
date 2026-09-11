# Troubleshooting recipe builds

Task-oriented fixes for common local build failures.

## "rattler-build not found"

```bash
# rattler-build ships in the local-recipes env (NOT the minimal `build` env)
pixi run -e local-recipes rattler-build --version

# Or activate manually
pixi shell -e local-recipes
rattler-build --version
```

## WSL conda-build fails with path errors

This occurs when the project is on a Windows filesystem. Solutions:

1. **Use rattler-build** for `recipe.yaml` recipes (works with WSL)
2. **Use Docker** for `meta.yaml` recipes (more reliable)
3. **Clone to WSL filesystem**: `git clone ... ~/local-recipes`

## Dependency resolution fails

```bash
# Try with verbose output
conda-build recipe/ -c conda-forge --debug

# Check for conflicts
mamba repoquery depends <package>
```

## Test phase fails

```bash
# Skip tests temporarily
conda-build recipe/ --no-test

# Run tests separately
conda-build recipe/ --test
```

## Go CGO builds failing on Windows with "/Werror" error

**Error**: `cl : Command line error D8021 : invalid numeric argument '/Werror'`

**Root Cause**: Go's CGO runtime passes GCC-style compiler flags that MSVC doesn't understand. This occurs during compilation of `runtime/cgo` or other CGO-enabled packages.

**Solution**: Use MinGW-w64 compilers instead of MSVC for Windows CGO builds.

For `meta.yaml` recipes:

```yaml
requirements:
  build:
    - {{ compiler('cgo') }}
    - {{ compiler('c') }}          # [unix]
    - {{ stdlib('c') }}             # [unix]
    - {{ compiler('m2w64_c') }}     # [win]
    - {{ stdlib('m2w64_c') }}       # [win]
    - m2-base                       # [win]
```

For `recipe.yaml` recipes:

```yaml
requirements:
  build:
    - ${{ compiler("go-cgo") }}
    - if: unix
      then:
        - ${{ compiler("c") }}
        - ${{ stdlib("c") }}
    - if: win
      then:
        - ${{ compiler("m2w64_c") }}      # MinGW-w64 C compiler
        - ${{ stdlib("m2w64_c") }}        # MinGW-w64 C stdlib
        - m2-base                          # MSYS2 base utilities
```

## Recipe development tips

1. **Use recipe.yaml** for new recipes (faster, cleaner syntax)
2. **Follow CFEP-25** — use `python_min` variable for Python bounds
3. **Pin dependencies** using conda-forge-pinning values
4. **Include tests** — at minimum `pip check` and imports
5. **Add maintainers** in `extra.recipe-maintainers`

## Version control tips

1. **Atomic commits** — One recipe change per commit
2. **Clear messages** — Describe what changed and why
3. **Skip CI** — Use `[skip ci]` for docs-only changes
4. **Branch per recipe** — Isolate work for PRs
