## Title

langflow / pandas / onnxruntime co-solve blocks composing python-agent-platform into laptop SBOM

## Body

The `python-agent-platform` pixi feature (langflow, dbgpt, django) cannot join `pyforge-foundry-full` because conda-forge co-solve conflicts — notably langflow-base's onnxruntime pin versus pandas — keep the agent platform in its own environment (`platform-dev` composes on top).

## Reproduce or evidence

- `docs/foundry/sbom-gaps.md:23` — `feature:python-agent-platform` upstream
- `docs/dreams/pyforge-unifying-strategy.md:806-808` — campaign map names langflow vs pandas / onnxruntime
- mason Story 13.1 (langflow-base onnxruntime pin) — done; residual co-solve remains

## Local workaround

Use `pixi install -e platform-dev` or `python-agent-platform` standalone; do not expect the feature inside `pyforge-foundry-full` until upstream pins align.

## What resolution unblocks here

Update `feature:python-agent-platform` disposition in `docs/foundry/sbom-gaps.md` when langflow-feedstock (or related pins) allow SBOM composition.
