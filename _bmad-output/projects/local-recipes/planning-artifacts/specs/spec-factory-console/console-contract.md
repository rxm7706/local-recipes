# Console contract — normative behavior of `docs/dashboard/generate.py`

Companion to SPEC.md (CAP-1..4). A rebuild from THIS FILE ALONE must be
behavior-equivalent. Python stdlib only; the script lives at
`docs/dashboard/generate.py` and resolves paths relative to itself
(`HERE = dirname of the script`; `REPO_ROOT = HERE/../..`; `DATA_JS = HERE/data.js`).

## CLI

`python docs/dashboard/generate.py [--source {sprint-status,git}]`
(default `sprint-status`). Exit 0 on success. argparse; description may cite
the module docstring.

## data.js read/write

- Read: strip leading `window.DASHBOARD_DATA =` (regex
  `^window\.DASHBOARD_DATA\s*=\s*`) from the stripped file text, strip a
  trailing `;`, `json.loads` the rest.
- Write: `"window.DASHBOARD_DATA = " + json.dumps(data, indent=2,
  ensure_ascii=False) + ";\n"` (UTF-8).
- Structure used here: `data["projects"]` is an ordered dict of project
  objects; each has `"epics"`: list of `{"badge", "title", "stories"}` where
  each story is a mutable list `[id, status, title, ...]` (index 1 = status;
  mutate ONLY index 1). `data["snapshot"]` is a string containing a
  timestamp. `data["dreams"]` is fully regenerated each run (see below).
  All other content is hand-curated and must round-trip untouched.

## Source: sprint-status (local default)

- Per-project sources (repo-root-relative), dict `PROJECT_SOURCES`:
  - `warden` → `_bmad-output/projects/pyforge-warden/implementation-artifacts/sprint-status.yaml`
  - `atlas` → `_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml`
  - `regen` → `_bmad-output/projects/local-recipes/implementation-artifacts/sprint-status.yaml`
- Parse (no YAML lib): scan lines; the block starts at a line exactly
  `development_status:`; it ends at the next non-indented, non-comment,
  non-empty line. Within it, entries match regex
  `^\s{2}(?P<key>[^:#\s][^:]*?):\s*(?P<val>[a-z][a-z-]*)\s*(#.*)?$` →
  `{key: val}`.
- Story id → sprint key: `prefix = id.lower().replace(".", "-") + "-"`;
  the first sprint key that `startswith(prefix)` supplies the status
  (`None` if no match).
- Sprint status → dashboard status: `done`→`done`; `in-progress`→`active`;
  otherwise keep `gated` if the story's current status is `gated`, else
  `pending`. (This mode may downgrade — full fidelity.)
- Missing project in data.js or missing source file: print a note and skip
  (statuses left as-is). Per project print
  `[<key>] N matched / M unmatched (of N+M)` plus the unmatched ids.

## Source: git (CI, hands-off)

- Subjects: `git log <ref> --format=%s` where `<ref>` is `main` if
  `git rev-parse --verify --quiet main` succeeds, else `HEAD` (detached CI).
- DONE-id extraction per subject line (a set, all patterns applied):
  - Warden: regex `Merge bmad-loop/[^/]+/(\d+-\d+)-` → capture with `-`→`.`
    (e.g. `6-1` → `6.1`).
  - Atlas: every match of `story\((\w[\w.]*)\)` → capture as-is; every match
    of `\b([GH]\d+):` → capture as-is.
  - Regen program: every match of `\brf\((\d+\.\w+)\):` → capture as-is.
- Apply to EVERY project: a story whose id is in the set and isn't `done`
  becomes `done`. UPGRADE ONLY — never downgrade (in-flight states aren't
  derivable from history). Print the derived id list and per-project
  `[<key>] D/T done (+u upgraded …)`.

## Dreams scan (both modes, every run)

- Files: sorted `docs/dreams/*.md`, skipping `README.md`.
- Frontmatter: only if line 0 (stripped) is `---`; read until the closing
  `---`; capture `title:`, `status:`, `owner:` values (split on first `:`,
  strip).
- Valid statuses: `("seeded", "in-deck", "in-spec", "realized")`. Unknown or
  missing → print a WARN naming the file (value passed through raw; the
  front-end buckets unknowns under seeded). Missing owner → WARN.
- Output: `data["dreams"] = [{"slug": stem, "title": title or stem,
  "status": status or "", "owner": owner or ""}, ...]` in filename order.
- Print a summary: count + per-status tallies.

## Snapshot stamp

Replace the FIRST occurrence of regex `\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC`
inside `data["snapshot"]` with the current UTC time formatted
`%Y-%m-%d %H:%M UTC`. Print a closing line naming the timestamp and source.

## Non-behavior

No network. No YAML/third-party imports. Never rewrites index.html. Never
touches fields other than story status index 1, `dreams`, `snapshot`.
