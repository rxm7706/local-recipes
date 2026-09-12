# bmad-suite-package

Conda recipes for the **BMAD suite**, published to the private prefix.dev
`openteams` channel: 13 packages plus the `bmad-suite` metapackage that installs
them together. Tracks
[mgmt-wf-python-modernization#9939](https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/9939).

## Layout

```
recipes/<package>/recipe.yaml     # plus build scripts, wrappers, LICENSE
```

All 14 recipes live in one repo because `bmad-suite` depends on the other 13, so
they have to build in order: members first, metapackage last.

## How CI works

`select` derives the build matrix from the recipes themselves:

- a recipe with `noarch: generic|python` builds once, on linux
- anything else builds on every runner its `skip:` block does not exclude

so adding a recipe under `recipes/` needs no workflow edit. Only recipes touched
by a push or PR are rebuilt; a change under `.github/` rebuilds all.

`members` builds those. On a PR it builds only — publishing happens solely on
`main`, via `rattler-build upload prefix -c openteams`.

`metapackage` builds `bmad-suite` last, gated on `needs: members` and on `main`.
It cannot run on a PR, because its run deps are the other 13 packages and those
exist only on the private channel.

## Setup still required

`PREFIX_API_KEY` must be added as a repository secret before anything can be
published — it is per-repo and is not inherited from the template. It
authenticates **uploads**; the metapackage job additionally needs to *read* the
private channel, which it does by writing the same token into a
`RATTLER_AUTH_FILE`.
