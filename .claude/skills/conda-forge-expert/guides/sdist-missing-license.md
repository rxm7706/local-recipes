# Sdist omits LICENSE — secondary source pattern

When a PyPI sdist doesn't ship a LICENSE file, rattler-build fails at the "Copying license files" step. This guide shows how to fetch LICENSE from the upstream GitHub tag as a secondary source.

## When this happens

Common with build backends that produce metadata-rich but file-sparse sdists:

- `maturin` (Rust + PyO3 packages) — frequently omits LICENSE
- `hatchling` with non-default `[tool.hatch.build.targets.sdist]` config
- Custom `pyproject.toml` setups that explicitly exclude LICENSE from sdist

The package compiles and the wheel installs, but conda-forge rejects the build for missing license bundling.

## Detection

You'll see one of these:

- `validate_recipe` warns `Missing license_file` (ABT-001)
- rattler-build runs through pip install successfully, then errors at the license-copy stage:
  ```
  ⚠ warning Warnings:
  Error:   × No license files were copied
  ```

## Verify the sdist actually omits LICENSE

Before adding a secondary source, confirm the sdist doesn't have it:

```bash
pip download <pkg>==<ver> --no-deps --no-binary :all: --dest /tmp/sdist-check
tar tzf /tmp/sdist-check/<pkg>-<ver>.tar.gz | grep -iE "license|copying|notice"
```

If the output is empty (or shows only `THIRD_PARTY_NOTICES.html`-style files but no `LICENSE`), the sdist is missing it.

## Fix: secondary source

Add a second entry to `source:` (which becomes a list):

```yaml
source:
  - url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
    sha256: <sdist sha256>
  # PyPI sdist omits LICENSE; fetch from upstream GitHub tag.
  - url: https://raw.githubusercontent.com/<org>/<repo>/v${{ version }}/LICENSE
    sha256: <license file sha256>
    file_name: LICENSE
```

`file_name: LICENSE` extracts the URL content as `$SRC_DIR/LICENSE`, where `license_file:` finds it.

### Compute the LICENSE sha256

```bash
curl -sL -o /tmp/upstream-LICENSE "https://raw.githubusercontent.com/<org>/<repo>/v<ver>/LICENSE"
sha256sum /tmp/upstream-LICENSE
```

### Reference both files in `about.license_file`

```yaml
about:
  license: Apache-2.0
  license_file:
    - LICENSE              # from secondary source
    - THIRDPARTY.yml       # from cargo-bundle-licenses (Rust packages)
```

## Worked example: cocoindex 1.0.3

cocoindex (`https://github.com/cocoindex-io/cocoindex`) is a maturin-built Rust + PyO3 package. The PyPI sdist ships only `THIRD_PARTY_NOTICES.html`, not LICENSE.

```yaml
source:
  - url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
    sha256: 1b242c348b501ec8b9836a626a1779a7f6185f479818dac73f7d9dd769d9b192
  # cocoindex sdist omits LICENSE; fetch from upstream GitHub tag.
  - url: https://raw.githubusercontent.com/cocoindex-io/cocoindex/v${{ version }}/LICENSE
    sha256: c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4
    file_name: LICENSE
```

See [staged-recipes PR #33231](https://github.com/conda-forge/staged-recipes/pull/33231) for the full submission.

## Caveats

- **Pin the LICENSE sha256.** The hash will change if upstream rewrites their LICENSE (rare, but it happens). On version bumps, refresh the LICENSE sha alongside the sdist sha.
- **Verify the GitHub tag matches the PyPI version.** Some projects don't tag releases on GitHub, or use a different naming scheme (`v1.0.3` vs `1.0.3` vs `release/1.0.3`). The pattern `v${{ version }}` works for the common case but adjust as needed.
- **Don't fetch from `main`/`master`.** Pinning to a moving branch makes the build non-reproducible — always pin to the tag matching the sdist version.
- **Filing an upstream PR is the long-term fix.** If you control or can contact the upstream, ask them to include LICENSE in their sdist (typically a one-line addition to `MANIFEST.in` or `pyproject.toml`'s `tool.hatch.build.targets.sdist.include` / `[tool.maturin] include`).

## Related

- [Recipe Authoring Gotchas G4 in SKILL.md](../SKILL.md#g4-sdist-may-omit-license--pip-install-succeeds-build-fails-with-no-license-files-were-copied)
- [Apache-2.0 license bundling expectations](https://www.apache.org/licenses/LICENSE-2.0#redistribution)
