# devin-cli — DO NOT SUBMIT, DO NOT PUBLISH

**Status: permanently blocked.** Unlike most blockers in this repo, there is no
upstream fix to wait for — short of Cognition open-sourcing the CLI or granting
an explicit redistribution license.

## The finding

Determined 2026-07-26 during the agent-CLI recipe wave.

| Check | Result |
|---|---|
| Public source repository | **None** |
| LICENSE file in the release bundle | **None** (verified: bundle is `bin/devin` + `share/devin/docs/*.mdx` only) |
| OSI-approved license | **No** |
| Binary | 133 MB stripped static-PIE Rust ELF, `static.devin.ai`, manifest `3000.2.17` |
| Governing terms | <https://cognition.com/pages/terms-of-service> |

Cognition's Terms of Service grant only:

> a non-exclusive, non-sublicensable, non-transferable right to access and use
> the Services

for

> your internal business purposes only, solely for use by you and your
> Authorized Users

and expressly prohibit:

> copy, reproduce, modify, translate, or create derivative works of the
> Services or Documentation

with all rights not expressly granted reserved by Cognition.

## Why this blocks both paths

1. **conda-forge** distributes only OSI-approved open-source licenses. A
   proprietary binary with no source and no redistribution grant is ineligible.
   Do not open a staged-recipes PR.
2. **Personal channels too.** Uploading the built artifact to SelfExplainML (or
   any anaconda.org channel) publishes it to third parties. That is
   redistribution, which the ToS does not permit. This is the difference from
   most `DO_NOT_SUBMIT` recipes here, which are only blocked from *conda-forge*
   and can still be channel-hosted.

## Stricter than copilot-cli

`recipes/copilot-cli` is the nearest precedent, but the two are not equivalent:

- **GitHub Copilot CLI** *does* grant a redistribution right (LICENSE.md
  Section 2), conditioned on the Software not being shipped "on a standalone
  basis or as a primary product". A conda package trips that condition — hence
  staged-recipes#32522 was rejected — but the grant exists.
- **Devin CLI** grants no redistribution right at all.

So copilot-cli is blocked from conda-forge but channel-hostable; devin-cli is
blocked from everywhere.

## What this recipe is for

The operator was told the above and confirmed "we will not distribute". The
recipe exists so an already-entitled user can install the CLI into a conda
environment locally, as a convenience over `curl -fsSL https://cli.devin.ai/install.sh | bash`.

Nothing here conveys a license to the Software.

## Maintenance

There is no git tag, changelog feed or release API. The version of record is:

    https://static.devin.ai/cli/current/manifest.json

which carries both the promoted version and the per-target `sha256`. Bump
`context.version` and all five checksums from that manifest together. Note the
manifest lists 10 targets, but the `*-musl` entries are byte-identical to the
glibc tarballs and the `windows-gnu` / `gnullvm` entries reuse the MSVC zip —
only 5 map to standard conda subdirs.
