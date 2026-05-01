# DO NOT SUBMIT this recipe to conda-forge/staged-recipes

## TL;DR
The upstream license (`github/copilot-cli/LICENSE.md`) forbids the kind of
standalone redistribution a conda-forge package would do. A prior submission
([staged-recipes#32522](https://github.com/conda-forge/staged-recipes/pull/32522))
was rejected by conda-forge core on this exact ground. This recipe is kept
locally for personal/private-channel builds only.

## The blocking license clause

From `LICENSE.md` Section 2 ("Redistribution Rights and Conditions") — all of
the following must be true:

> - The Software is distributed only in unmodified form;
> - **The Software is redistributed solely as part of an application or service
>   that provides material functionality beyond the Software itself;**
> - **The Software is not distributed on a standalone basis or as a primary
>   product;**
> - You include a copy of this License and retain all applicable copyright,
>   trademark, and attribution notices; and
> - Your application or service is licensed independently of the Software.

A conda-forge package is precisely "a standalone redistribution as a primary
product." The two emphasised clauses are why this can't ship to conda-forge.

## Authoritative precedent

[`conda-forge/staged-recipes#32522`](https://github.com/conda-forge/staged-recipes/pull/32522)
(opened 2026-03-08 by `dhirschfeld`, a conda-forge MEMBER):

- Recipe built cleanly on linux-64 after fixing `c_stdlib_version` and adding
  `cf-nvidia-tools`' `check-glibc` to the test phase.
- Reviewed by `chrisburr` (conda-forge MEMBER) on 2026-03-10 with
  `CHANGES_REQUESTED`: *"I'm not convinced this can go on conda-forge with the
  current license. ... 'The Software is not distributed on a standalone basis'"*
- Submitter agreed: *"on the face of it, we're packaging it on a standalone
  basis"* and closed the PR the same day.

The current `LICENSE.md` is byte-for-byte identical to the version that was
rejected (last upstream change: 2026-01-22). Re-submitting today would be
re-litigating a settled question and would waste reviewer time.

## What would unblock submission

Any one of:

1. Upstream open-sources the CLI — tracked in
   [github/copilot-cli#83](https://github.com/github/copilot-cli/issues/83).
2. Upstream adopts a permissive license — there was a brief
   "Update to MIT license" commit on 2026-01-21 (sha `993cd5b3`) that was
   reverted within a day, so this is on their radar.
3. Upstream amends Section 2 to permit distribution via package managers /
   distro repos — tracked in
   [github/copilot-cli#1962](https://github.com/github/copilot-cli/issues/1962)
   and
   [github/copilot-cli#2294](https://github.com/github/copilot-cli/issues/2294).

If any of these resolves favourably:

1. Re-verify the new license against conda-forge's policy.
2. Update this recipe's `about.license` and the header comment.
3. Delete this `DO_NOT_SUBMIT.md` file.
4. Run the standard `validate_recipe` → `optimize_recipe` →
   `check_dependencies` → `trigger_build` → `submit_pr` loop.
5. Reference `staged-recipes#32522` and the new license language in the PR
   description.

## How this recipe is used in the meantime

- **Local build**: `python build-locally.py linux-64` (or via the
  `trigger_build` MCP tool with `config="linux-64"`).
- **Personal channel**: upload the resulting `.conda` artefact to your own
  `prefix.dev` or `anaconda.org` channel — note that this is still technically
  outside the license grant, so use is at your own risk and should remain
  individual / non-public.
- **Recommended alternative for general users**: `npm install -g @github/copilot`,
  `brew install copilot-cli`, `winget install GitHub.Copilot`, or the upstream
  installer at `https://gh.io/copilot-install`.
