# Pixitainer re-eval (CAP-3)

Adopted from `.cursor/pyforge-fleet-drain/NEXT-AFTER-12-7.md`. Story 10.3 (2026-08-14)
rejected conda-forge `pixitainer` 0.8.3 because `pixi-containerize` ships **Apptainer `.sif`**,
default `ubuntu:24.04`, pixi re-installed in the build, no UBI-minimal / GID-0 /
`restricted-v2` story.

This follow-up tries **`pixitainer-docker`** (not the SIF CLI) against the same 10.3 contract.
If any row fails, keep the hand-rolled `src/platform/Containerfile` and only delete the pip
`RUN`. Pixitainer remains valid for **other** images (presenton, tool CLIs).

| Must hold | Why 10.3 hand-rolled |
|-----------|----------------------|
| OCI for **docker and podman** | SIF-only binary failed the dual-engine AC |
| UBI9-minimal runtime, **no pixi** in the final image | Seamless pixitainer keeps `pixi run --locked`; platform runtime copies the env only |
| `USER` + GID 0 `g+rwX` for `restricted-v2` | Generated defs did not |
| App tree + gunicorn CMD (not only env trampolines) | `--add-file` / `--post-command` may or may not be enough |

**What pixitainer does not replace:** the pip-vs-conda *solve*. It only packages whatever one
env already locked.
