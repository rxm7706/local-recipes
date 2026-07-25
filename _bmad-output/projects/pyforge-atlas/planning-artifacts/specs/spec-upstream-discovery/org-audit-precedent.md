# Org-audit precedent (Track B worked example)

Reference detail for CAP-4 (fixed-source audit track). This is **historical
precedent from the June 2026 Microsoft org audit**, carried from the legacy
`docs/specs/trendshift-conda-forge.md` Track B — it illustrates the
discover→triage→tier→wave-package shape applied to a fixed source, not a
committed list for a future batch. Re-verify every entry (`lookup_feedstock`
+ current PyPI facts) before treating any of it as live scope; 5+ weeks have
passed since the audit and conda-forge coverage shifts weekly.

## Shape

Enumerate a fixed org's repos by stars → cross-check each against
conda-forge (`lookup_feedstock`) → classify the gap with CAP-2's tier
taxonomy → wave-package the survivors. The same shape generalizes to any
fixed candidate source (a named org, a curated list), not only
`github.com/microsoft/*`.

## June 2026 snapshot (illustrative only — do not re-assert as current)

- **Already shipped at audit time** (20+ feedstocks): markitdown, autogen
  family, graphrag, presidio-analyzer, pyright, FLAML, LightGBM, DeepSpeed,
  ONNX Runtime, onnxscript, LoRA, LLMLingua, hummingbird-ml, TorchGeo,
  TypeScript, Playwright (+Python), debugpy, GSL (`ms-gsl`), picologging,
  the Microsoft 365 Agents kiota family, `agent-framework-core`.
- **Material gaps identified** (~10–14 candidates, 3 difficulty waves):
  `microsoft/edit` (Rust CLI), `microsoft/agent-framework` (umbrella meta),
  `microsoft/qlib` (`pyqlib`), `microsoft/PyRIT` (`pyrit`),
  `microsoft/promptflow` (4 outputs), `microsoft/semantic-kernel`,
  `microsoft/torchscale`, `microsoft/SEAL` (C++, CMake),
  `microsoft/DiskANN` (C++ + `diskannpy` bindings, multi-output).
- **Investigated and ruled out at audit time**: `microsoft/typescript-go`
  (pre-1.0, no stable tag), `microsoft/VibeVoice` (upstream pulled the code;
  research-snapshot, not maintained), `microsoft/BitNet` (multi-week custom
  build, stretch-only), `microsoft/recommenders` (wide optional-extras
  surface, effort-pending), `microsoft/PromptWizard` (PyPI name collision
  with an unrelated package — needs its own artifact confirmed before a
  recipe is promised).
- **Categorically out of scope**: Windows-only system tools, .NET-heavy
  repos, research code without library shape, docs/training repos,
  vendor-distributed binaries, browser-only npm libs.

## Reuse note

A future org-audit batch reuses CAP-2's classifier and CAP-1's already-on-cf
join rather than a manual `lookup_feedstock` sweep — the automation this
kernel adds is exactly the thing the June 2026 audit did by hand.
