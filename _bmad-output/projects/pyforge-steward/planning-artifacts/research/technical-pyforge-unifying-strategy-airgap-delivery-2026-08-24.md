---
title: "Air-gap delivery policy — does it govern container images?"
chain: "pyforge-unifying-strategy"
type: "technical"
created: "2026-08-24"
updated: "2026-08-24"
status: "ready"
decision: "Whether Liquibase arrives as a conda-forge feedstock or as a container image, and under which policy"
answers:
  - liquibase-airgap-policy
---

# Air-gap delivery policy — and the Liquibase vehicle

Repo-internal precedent research, run 2026-08-24 to answer the open question
`liquibase-airgap-policy`, which gates `liquibase-delivery-vehicle`, which gates CAP-9's
scheduling.

**Headline: the question was framed wrong, and the repo already contains the answer.** Policy does
govern container images — but CAP-9 does not need a new one. The Helm hook RFC-5 asks for is
already shipped, already runs the platform image, and already takes its command as `args`. If
Liquibase is in the platform environment, CAP-9 adds a second hook Job and changes one argument.

---

## 1. Policy: two supply paths, both in-boundary, governing different things

The repo runs **two** air-gap boundaries, and conflating them is what made the original question
look hard.

**Conda channels** govern Python and pixi dependencies.
`docs/reference/enterprise-deployment.md` documents JFrog conda/PyPI remotes, pixi `[mirrors]`,
`offline: true`, `allow_other_channels: false`, and a `*_BASE_URL` override table. Searched that
document for `container`, `image`, `OCI` — **not found**. It is silent on images, not permissive
about them.

**Container images** are governed separately and explicitly, by
`spec-python-agent-platform` CAP-6:

> **intent:** Every deployment artifact resolves inside the boundary: **internal-registry images**,
> mirrored indexes, zero-CDN assets, env/secret-mount credentials …
> **success:** A build + deploy executed with external egress blocked succeeds end-to-end; **any
> external reference is a FAILING check, not a warning.**

So images are in scope, and third-party images are already consumed under it: `postgres:17`,
`redis:7` in the chart, `quay.io/keycloak/keycloak:26.4.0` in compose. None has a feedstock.
`.github/workflows/platform-ci.yml`'s `air-gap-parity` job pre-pulls postgres and redis, `kind
load`s the platform image, blocks egress with iptables, and installs from mirror-only channels.

**Consequence for this chain's constraint.** `SPEC.md`'s *"every dependency resolves from
conda-forge"* is written without a carve-out, but CAP-6 already admits images that are not conda
packages. The constraint governs the **Python/pixi dependency graph**, not every artifact in the
namespace. That needed saying in prose rather than being left implicit.

## 2. The finding that resolves it: the pre-upgrade hook already exists

`src/platform/deploy/charts/platform/templates/migrate-job.yaml` is shipped, and it is precisely
the seam RFC-5 asks for:

```yaml
  annotations:
    helm.sh/hook: post-install,pre-upgrade
    helm.sh/hook-weight: "0"
    helm.sh/hook-delete-policy: before-hook-creation
```
```yaml
          image: {{ include "platform.imageRef" (dict "image" .Values.image "path" "image") }}
          # args (not command): runs through the image ENTRYPOINT so the
          # pixi shell-hook puts python on PATH.
          args: ["python", "manage.py", "migrate", "--noinput"]
```

Three things follow.

**CAP-9 modifies an existing hook rather than introducing a chart pattern.** Story 12.1's chart
contract is `done` and `spec-platform-fifteen-factors` declares AD-4/AD-17 topology HARD; this was
the risk convergence flagged. It is smaller than feared — Liquibase becomes a second hook Job at
weight `-1`, and this Job's args change from `migrate --noinput` to `migrate --fake`.

**The Job runs the platform image and takes its command as `args`.** Anything on the platform
environment's PATH is runnable in that Job with no new image whatsoever.

**Its header independently corroborates Phase-2's "not an init container" conclusion**, for a
different reason. Phase 2 rejected init containers because N replicas contend on
`DATABASECHANGELOGLOCK` (default wait 5 min). This file rejects them because with `helm install
--wait`, post-install hooks fire only after resources are Ready, so migration-gated readiness
deadlocks. Two unrelated arguments, same answer — the strongest form of corroboration available.

## 3. Consequence: the vehicle options collapse

| Option | What it costs | Verdict |
|---|---|---|
| **A — conda-forge feedstock**, Liquibase into the platform pixi env, second hook Job on the **existing** image at weight `-1` | One JVM feedstock. `openjdk` 25.0.2 is on conda-forge and clears the Java 17+ floor. `apache-tika` is the exact recipe shape — Maven jars into `$PREFIX/share/java/…`, `openjdk` run-dep, CLI wrapper — and ~12 such recipes already exist here. JDBC driver vendored into the recipe. | **No new image, no new supply path, no policy exception.** |
| **B — upstream `liquibase/liquibase` image** | A third-party image class the repo has **no documented mirroring pattern for** — postgres/redis are relocated by values and preloaded in CI, never mirrored through JFrog. *And* Liquibase 5.x Community dropped the bundled PostgreSQL JDBC driver, with LPM fetching it over the network — so an air-gapped path must bake the JAR, meaning a derived image gets built regardless. | Pays a new supply path **and** still builds an image. |
| **C — self-built Liquibase image** from the platform base | The repo's Containerfiles all materialize a pixi environment into OCI. To build this image you need the conda package first — so C requires A and then adds an image A does not need. | Collapses into A plus redundant work. |

B's only advantage was avoiding feedstock work, and the 5.x driver change removes it.

## 4. Gaps

- **No ADR** scoped to "conda vs container for operational binaries". Closest records are
  `architecture-unified-container` AD-1 (what may enter the Guild image) and Mason's presenton
  model (conda artifacts → signed OCI image). This research is the nearest thing to a decision
  record and should be cited as such.
- **`imagePullSecrets` has a seam but no example values** (defaults to `[]`), so the internal-registry
  path is declared but not demonstrated for a third-party image.
- **The `air-gap-parity` CI job does not preload `platform-dbgpt-sidecar`**, though the chart defines
  it. Pre-existing, adjacent, not this chain's to fix — but it means CAP-6's gate is narrower than
  its success criterion reads.
- **Story 12.3's spec file is absent** from `planning-artifacts/specs/` although epics and
  `scripts/build-pixi-mirror.py` both cite `spec-12-3-air-gap-parity-is-a-failing-check`. Likely
  lost to the Tier-3 worktree-teardown failure mode CLAUDE.md documents; worth a recovery pass, and
  out of scope here.
