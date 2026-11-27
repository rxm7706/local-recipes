"""Story 61.1 (spec-pyforge-steward:CAP-175): the docs loader keeps a page it already rendered, only when asked.

``docs-site/src/loaders/shelf-docs-loader.ts`` rendered every docs page on every build (about 4 s of a 7 s build).
With ``PAGES_REUSE_RENDERED_DOCS`` on, a page whose source, path and rendering pipeline (the config, the link plugins,
the loader, the base path and the repository a link to an unpublished file goes to) match what the store holds keeps
that rendering; herald's test builds turn it on, the Pages build leaves it off. Either way a page that is gone leaves
the store, which outlives a build in the same tree.

The loader runs through node with type stripping (no ``node_modules``) against a fake loader context: a store, a
``renderMarkdown`` that counts its calls, ``generateDigest`` as sha256, and a logger. It walks the real docs shelf.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "meta"))
from pages_astro import DOCS_SITE, needs_node, ts  # noqa: E402 -- the shared Pages helpers

# This module reads the live tree outside its package (docs-site/ and the docs shelf), so it runs in herald's live half.
pytestmark = [pytest.mark.live_tree, needs_node]

LOADER = DOCS_SITE / "src" / "loaders" / "shelf-docs-loader.ts"

# One load against a store that persists between calls; each call returns how many pages it rendered, the store's ids
# and what the loader logged. ``env`` is set on process.env for that load and removed after it.
_HARNESS = """
const { createHash } = await import('node:crypto');
const entries = new Map(Object.entries(inp.seed));
const store = {
  get: (id) => entries.get(id),
  set: (entry) => { entries.set(entry.id, entry); return true; },
  keys: () => [...entries.keys()],
  delete: (id) => { entries.delete(id); },
};
const runs = [];
for (const step of inp.steps) {
  const saved = {};
  for (const [name, value] of Object.entries(step.env)) { saved[name] = process.env[name]; process.env[name] = value; }
  let rendered = 0;
  const logs = [];
  await m.shelfDocsLoader().load({
    store,
    config: { root: new URL(inp.root), base: step.base },
    renderMarkdown: async (body) => { rendered += 1; return { html: `<p>${rendered}</p>`, metadata: {} }; },
    generateDigest: (text) => createHash('sha256').update(String(text)).digest('hex'),
    logger: { info: (message) => logs.push(message) },
  });
  for (const [name, value] of Object.entries(saved)) {
    if (value === undefined) delete process.env[name]; else process.env[name] = value;
  }
  runs.push({ rendered, ids: store.keys().length, ghost: entries.has('ghost'), logs });
}
return runs;
"""

BASE = "/local-recipes/"
ON = {"PAGES_REUSE_RENDERED_DOCS": "1"}


def _load(steps: list[dict], seed: dict | None = None) -> list[dict]:
    runs = ts(LOADER, _HARNESS, root=DOCS_SITE.as_uri() + "/", seed=seed or {}, steps=steps)
    assert isinstance(runs, list), runs
    return runs


def test_off_every_load_renders_every_page_and_a_gone_page_leaves_the_store() -> None:
    first, second = _load([{"env": {}, "base": BASE}, {"env": {}, "base": BASE}], seed={"ghost": {"id": "ghost"}})
    assert first["rendered"] > 50
    assert second["rendered"] == first["rendered"]
    assert first["ghost"] is False
    assert first["ids"] == first["rendered"]
    assert first["logs"] == second["logs"] == []


def test_on_a_second_load_keeps_every_page_it_rendered() -> None:
    first, second = _load([{"env": ON, "base": BASE}, {"env": ON, "base": BASE}])
    pages = first["rendered"]
    assert pages > 50
    assert second["rendered"] == 0
    assert second["ids"] == pages
    assert first["logs"] == [f"kept 0 of {pages} rendered pages (PAGES_REUSE_RENDERED_DOCS)"]
    assert second["logs"] == [f"kept {pages} of {pages} rendered pages (PAGES_REUSE_RENDERED_DOCS)"]


def test_on_a_page_rendered_with_it_off_renders_again() -> None:
    """A rendering stored with the variable off carries no digest, so the first load with it on cannot keep it."""
    off, on = _load([{"env": {}, "base": BASE}, {"env": ON, "base": BASE}])
    assert on["rendered"] == off["rendered"]


@pytest.mark.parametrize(
    "changed",
    [
        {"env": ON, "base": "/elsewhere/"},
        {"env": {**ON, "GITHUB_REPOSITORY": "someone/fork"}, "base": BASE},
        {"env": {**ON, "GITHUB_SERVER_URL": "https://ghe.example.com"}, "base": BASE},
    ],
    ids=["base-path", "repository", "server"],
)
def test_on_a_change_the_rendering_reads_renders_every_page_again(changed: dict) -> None:
    first, second = _load([{"env": ON, "base": BASE}, changed])
    assert second["rendered"] == first["rendered"]
