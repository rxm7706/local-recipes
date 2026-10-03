---
name: "mason-story-26-1-done-cfe-tests-stub-conda-smithy-maintainer"
description: "Mason Story 26.1 (done): CFE tests stub conda-smithy _maintainer_exists and _team_exists for every non-network test, in…"
metadata:
  type: project
---

Mason Story 26.1 (done): CFE tests stub conda-smithy _maintainer_exists and _team_exists for every non-network test, in-process and in the validate_recipe child via PYTHONPATH sitecustomize (v8.91.3, retro(cfe):). The child-path regression must exec the fixture sitecustomize already on PYTHONPATH, then wrap requests — it must not re-implement the stub, or emptying sitecustomize_source() stays green while test_workflow_npm.py talks to GitHub again.
