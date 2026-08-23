"""Regression gate for this repo's base-layer convention across all three
Containerfiles (`Containerfile`, `src/platform/Containerfile`,
`src/platform/compose/dbgpt/Containerfile`).

Two anti-patterns, both statically detectable from the Containerfile text
alone (see `docs/reference/container-base-layer-convention.md` for the full
convention, incl. the multi-stage pixi-materialization shape this file
does NOT check -- that pillar is structural, not a grep):

1. **Unpinned base image.** Every `FROM` in every stage of every
   Containerfile must carry an explicit, non-floating tag -- never
   bare/untagged (Docker silently defaults that to `:latest`), never
   `:latest` literally, and never an empty tag (`FROM image:`). Exempted:
   `FROM <stage-name> AS <new-stage>` re-FROM's an EARLIER stage declared
   in the same file by its `AS <name>`, not an external image, so it never
   carries a tag at all and must not be flagged.
2. **`ENV`-declared credential.** No `ENV` key may match a
   credential-shaped deny-list -- build-time secrets must cross the build
   boundary only via `--mount=type=secret`, never a baked `ENV` (or
   `COPY`/layer). Docker allows multiple `KEY=VALUE` pairs on one `ENV`
   line; every key on the line is checked, not just the first.

**Pure stdlib, by design.** Only `re` + `pathlib` + `pytest`, matching this
repo's other `tests/packaging` gates (see
`test_containerfile_checkout_path.py`), so it runs in the deliberately lean
`pyforge-ci` env with zero runtime libraries installed. This is a static
text scan over the Containerfiles as committed -- not a build-time or
runtime check; `scripts/container-gates secrets-scan` (wired into all three
Containerfiles as a `RUN` step) is the complementary, different-layer check
that a *built* image ships nothing secret-shaped.

**Synthetic-regression coverage is mandatory here, not optional.**
`test_containerfile_checkout_path.py`'s own docstring records this repo's
precedent for a guard whose failure branch was never exercised and shipped
a broken assertion unnoticed -- every check below has a parametrized test
proving it actually fires on a planted violation, driven directly against
strings (or synthetic multi-line snippets) that are never written to disk.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

CONTAINERFILES: tuple[Path, ...] = (
    REPO_ROOT / "Containerfile",
    REPO_ROOT / "src" / "platform" / "Containerfile",
    REPO_ROOT / "src" / "platform" / "compose" / "dbgpt" / "Containerfile",
)

# Tolerates a leading `--platform=...` flag and a trailing `AS <name>`, e.g.:
#   FROM --platform=linux/amd64 ghcr.io/prefix-dev/pixi:0.77.0 AS builder
#   FROM --platform=linux/amd64 ubuntu:24.04
#   FROM --platform=linux/amd64 registry.access.redhat.com/ubi9/ubi-minimal:9.6 AS runtime
#   FROM builder AS test                     (re-FROM'ing an earlier stage)
# Group 1 = the image ref (or stage-name reference); group 2 = the stage
# name this line itself declares, if any.
FROM_LINE_RE = re.compile(
    r"^FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?\s*$"
)

# Everything after `ENV `, to be split into individual keys by `_env_keys()`
# below -- a single `ENV` line can declare more than one key (Docker's
# `ENV KEY1=val1 KEY2=val2 ...` form), so a single capture group here is
# deliberately NOT the key itself.
ENV_HEADER_RE = re.compile(r"^ENV\s+(.+?)\s*$")

# Matches one `KEY=` token within an ENV line's remainder, preceded by
# either the start of the string or whitespace (so it does not fire on a
# `=` embedded inside a value).
ENV_KEY_EQUALS_RE = re.compile(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=")

# Case-insensitive substrings. Deliberately does NOT flag this repo's real
# non-secret ENV keys (`HOME`, `DJANGO_SETTINGS_MODULE`) -- see the
# docstring above and the convention doc's pillar 3 for why the pattern is
# scoped this way rather than narrowed further.
CREDENTIAL_DENYLIST: tuple[str, ...] = (
    "PASSWORD",
    "SECRET",
    "TOKEN",
    "API_KEY",
    "APIKEY",
    "PRIVATE_KEY",
    "ACCESS_KEY",
    "CREDENTIAL",
)

# 2 stages (builder + runtime) x 3 Containerfiles, today. A regression that
# drops below this is itself worth a look even before considering whether
# any individual FROM is unpinned.
MIN_EXPECTED_FROM_LINES = 6

# `src/platform/Containerfile` (HOME, DJANGO_SETTINGS_MODULE) +
# `src/platform/compose/dbgpt/Containerfile` (HOME) = 3 ENV directives, one
# key each, today. The root `Containerfile` has none. This floor exists so
# a regex that stopped matching ENV lines entirely would fail loudly here
# rather than letting `test_no_env_key_is_credential_shaped` pass having
# checked nothing.
MIN_EXPECTED_ENV_LINES = 3


def _parse_image_ref(ref: str) -> tuple[str, str | None]:
    """(image name, tag or None if untagged -- including the trailing-colon
    empty-tag spelling `image:`, which `_is_unpinned` also treats as
    untagged).

    Looks only at the final `/`-separated path segment for the `:` that
    separates name from tag, so a registry host that itself contains a
    colon (e.g. a port) never gets mistaken for the tag separator.
    """
    last_segment = ref.rsplit("/", 1)[-1]
    if ":" in last_segment:
        name, tag = ref.rsplit(":", 1)
        return name, tag
    return ref, None


def _is_unpinned(tag: str | None) -> bool:
    """No tag, an empty tag (`FROM image:`), or a literal `latest` --
    `not tag` covers both `None` and `""` since both are falsy."""
    return not tag or tag.lower() == "latest"


def _is_credential_shaped(key: str) -> bool:
    upper = key.upper()
    return any(term in upper for term in CREDENTIAL_DENYLIST)


def _env_keys(rest: str) -> list[str]:
    """Every key declared on one `ENV` directive's remainder text (`rest` =
    everything after `ENV `). Docker allows two forms on one line:
      - `ENV KEY1=val1 KEY2=val2 ...` (equals form, any number of pairs) --
        every `KEY=` token contributes its key.
      - `ENV KEY value with spaces` (legacy single-pair form, no `=`) --
        only the first token is the key.
    Detected by whether the equals-form regex finds anything at all; a line
    with no `KEY=` token anywhere falls back to the legacy single-pair
    reading.
    """
    keys = ENV_KEY_EQUALS_RE.findall(rest)
    if keys:
        return keys
    first_token = rest.split(None, 1)[0] if rest.strip() else ""
    return [first_token] if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", first_token) else []


def _parse_from_lines(text: str) -> list[tuple[int, str, str | None, bool]]:
    """Every `FROM` directive in `text`, as (1-indexed line number, image
    ref, tag or None, whether the ref is a same-file stage-name reference
    rather than an external image). A stage-name reference is a `FROM`
    whose ref exactly matches an `AS <name>` declared by an EARLIER `FROM`
    line in the same text -- the only order Docker itself accepts, so no
    forward-reference case needs handling.

    A pure function over text, not a file -- reused by both the real-file
    scan below and by synthetic-regression tests that never touch disk.
    """
    results: list[tuple[int, str, str | None, bool]] = []
    declared_stage_names: set[str] = set()
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = FROM_LINE_RE.match(line)
        if match:
            ref = match.group(1)
            stage_name = match.group(2)
            is_stage_reference = ref in declared_stage_names
            _, tag = _parse_image_ref(ref)
            results.append((lineno, ref, tag, is_stage_reference))
            if stage_name:
                declared_stage_names.add(stage_name)
    return results


def _from_directives() -> list[tuple[Path, int, str, str | None, bool]]:
    """Every `FROM` directive across all three Containerfiles, as
    (file, 1-indexed line number, raw image ref, tag or None, is a
    same-file stage-name reference)."""
    results: list[tuple[Path, int, str, str | None, bool]] = []
    for path in CONTAINERFILES:
        assert path.is_file(), f"Containerfile missing: {path}"
        text = path.read_text(encoding="utf-8")
        for lineno, ref, tag, is_stage_reference in _parse_from_lines(text):
            results.append((path, lineno, ref, tag, is_stage_reference))
    return results


def _env_directives() -> list[tuple[Path, int, str]]:
    """Every `ENV` key across all three Containerfiles, as (file,
    1-indexed line number, key). A single `ENV` line can declare more than
    one key (the `ENV KEY1=val1 KEY2=val2` multi-pair form) -- each
    contributes its own entry at the same line number."""
    results: list[tuple[Path, int, str]] = []
    for path in CONTAINERFILES:
        assert path.is_file(), f"Containerfile missing: {path}"
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = ENV_HEADER_RE.match(line)
            if match:
                for key in _env_keys(match.group(1)):
                    results.append((path, lineno, key))
    return results


def test_discovery_is_not_vacuous():
    """If either regex ever stopped matching, the corresponding assertion
    below would iterate over an empty (or too-small) list and pass having
    checked nothing -- the one failure mode this file must never have."""
    froms = _from_directives()
    envs = _env_directives()
    assert len(froms) >= MIN_EXPECTED_FROM_LINES, (
        f"expected at least {MIN_EXPECTED_FROM_LINES} FROM directives across "
        f"{[str(p.relative_to(REPO_ROOT)) for p in CONTAINERFILES]}, found "
        f"{len(froms)}: {froms}. Either a stage lost its FROM or the parsing "
        "regex stopped matching -- both are regressions."
    )
    assert len(envs) >= MIN_EXPECTED_ENV_LINES, (
        f"expected at least {MIN_EXPECTED_ENV_LINES} ENV directives across "
        f"{[str(p.relative_to(REPO_ROOT)) for p in CONTAINERFILES]}, found "
        f"{len(envs)}: {envs}. Either an ENV line was removed or the parsing "
        "regex stopped matching -- both are regressions."
    )


def test_every_from_has_an_explicit_non_latest_tag():
    """The AC: every base image in every stage of every Containerfile is
    registry-pinned to an explicit, non-`latest` tag. A `FROM` that
    re-references an earlier same-file stage (`FROM builder AS test`) is
    exempt -- it names a build stage, not an external image, and never
    carries a tag."""
    froms = _from_directives()
    unpinned = [
        (path, lineno, ref)
        for path, lineno, ref, tag, is_stage_reference in froms
        if not is_stage_reference and _is_unpinned(tag)
    ]
    assert not unpinned, (
        "Every FROM must carry an explicit, non-'latest' tag (see "
        "docs/reference/container-base-layer-convention.md, pillar 1). "
        "Offending line(s): "
        + ", ".join(
            f"{path.relative_to(REPO_ROOT)}:{lineno}: {ref!r}"
            for path, lineno, ref in unpinned
        )
    )


def test_no_env_key_is_credential_shaped():
    """The AC: no ENV key across any of the three Containerfiles matches a
    credential-shaped deny-list -- secrets must cross the build boundary
    only via `--mount=type=secret` (convention doc pillar 3)."""
    envs = _env_directives()
    offending = [
        (path, lineno, key) for path, lineno, key in envs if _is_credential_shaped(key)
    ]
    assert not offending, (
        "No ENV key may look credential-shaped (see "
        "docs/reference/container-base-layer-convention.md, pillar 3). "
        "Offending line(s): "
        + ", ".join(
            f"{path.relative_to(REPO_ROOT)}:{lineno}: {key!r}"
            for path, lineno, key in offending
        )
    )


@pytest.mark.parametrize(
    "line,expected_tag,expect_unpinned",
    [
        # Bare, no tag at all -- Docker silently defaults this to :latest.
        ("FROM ubuntu", None, True),
        # Explicit :latest, spelled out.
        ("FROM ubuntu:latest", "latest", True),
        # --platform flag + AS clause, still untagged.
        ("FROM --platform=linux/amd64 ubuntu AS runtime", None, True),
        # Trailing colon, empty tag -- distinct from "no colon at all"
        # (`_parse_image_ref` returns "" here, not None); must still count
        # as unpinned.
        ("FROM ubuntu:", "", True),
        # Real, correctly-pinned examples (mirroring the three real files) --
        # prove the check does NOT false-positive on the golden shape.
        (
            "FROM --platform=linux/amd64 ghcr.io/prefix-dev/pixi:0.77.0 AS builder",
            "0.77.0",
            False,
        ),
        (
            "FROM --platform=linux/amd64 registry.access.redhat.com/ubi9/ubi-minimal:9.6 AS runtime",
            "9.6",
            False,
        ),
    ],
)
def test_unpinned_base_guard_fires_on_synthetic_regressions(
    line, expected_tag, expect_unpinned
):
    """The two tests above only ever run against the real, already-correct
    Containerfiles, so they never exercise their own failure branches. This
    drives the same regex and pin-check logic against synthetic FROM lines
    that are never written to disk, so it can assert the failure branch
    actually fires without corrupting a real Containerfile."""
    match = FROM_LINE_RE.match(line)
    assert match, f"regex failed to match a syntactically valid FROM line: {line!r}"
    ref = match.group(1)
    _, tag = _parse_image_ref(ref)

    assert tag == expected_tag, f"tag-parsing mismatch for {line!r}: got {tag!r}"
    assert _is_unpinned(tag) == expect_unpinned, f"pin-check mismatch for {line!r}"


def test_stage_name_reuse_is_not_flagged_as_unpinned():
    """Docker allows re-FROM'ing an earlier build stage by name (e.g.
    `FROM builder AS test`) to branch off it without pulling a fresh image
    -- this has no `:tag` at all and must NOT be flagged as an unpinned
    external image. A genuinely unpinned external image later in the same
    synthetic file must still be caught -- this proves the exemption is
    scoped to real stage-name references, not a blanket skip.

    Driven against a synthetic multi-line Containerfile-shaped snippet
    (never written to disk), through `_parse_from_lines` directly -- the
    same function `_from_directives()` uses against the real files.
    """
    text = "\n".join(
        [
            "FROM ghcr.io/prefix-dev/pixi:0.77.0 AS builder",
            "FROM builder AS test",
            "FROM ubuntu",
        ]
    )
    parsed = _parse_from_lines(text)
    assert parsed == [
        (1, "ghcr.io/prefix-dev/pixi:0.77.0", "0.77.0", False),
        (2, "builder", None, True),
        (3, "ubuntu", None, False),
    ], f"unexpected parse of the synthetic snippet: {parsed!r}"

    unpinned = [
        (lineno, ref)
        for lineno, ref, tag, is_stage_reference in parsed
        if not is_stage_reference and _is_unpinned(tag)
    ]
    assert unpinned == [(3, "ubuntu")], (
        "the stage-name reference on line 2 (FROM builder AS test) must not be "
        "flagged, but the genuinely unpinned external image on line 3 (FROM "
        f"ubuntu) must be: got {unpinned!r}"
    )


@pytest.mark.parametrize(
    "line,expected_key,expect_flagged",
    [
        # Credential-shaped keys -- one per deny-list term.
        ("ENV DB_PASSWORD=hunter2", "DB_PASSWORD", True),
        ("ENV APP_SECRET=xyz", "APP_SECRET", True),
        ("ENV GITHUB_TOKEN=xyz", "GITHUB_TOKEN", True),
        ("ENV OPENAI_API_KEY=xyz", "OPENAI_API_KEY", True),
        ("ENV STRIPE_APIKEY=xyz", "STRIPE_APIKEY", True),
        ("ENV TLS_PRIVATE_KEY=xyz", "TLS_PRIVATE_KEY", True),
        ("ENV AWS_ACCESS_KEY=xyz", "AWS_ACCESS_KEY", True),
        ("ENV DB_CREDENTIAL=xyz", "DB_CREDENTIAL", True),
        # Real, non-credential examples this repo actually ships -- prove
        # the deny-list does NOT false-positive on them (Block-If constraint).
        ("ENV HOME=/app/.home", "HOME", False),
        (
            "ENV DJANGO_SETTINGS_MODULE=config.settings.production",
            "DJANGO_SETTINGS_MODULE",
            False,
        ),
    ],
)
def test_env_credential_guard_fires_on_synthetic_regressions(
    line, expected_key, expect_flagged
):
    """Same rationale as the FROM regression test above, for the ENV-key
    deny-list: drives the real regex + deny-list check against synthetic
    single-key ENV lines never written to disk, proving both the positive
    (flagged) and negative (not flagged) branches actually fire."""
    match = ENV_HEADER_RE.match(line)
    assert match, f"regex failed to match a syntactically valid ENV line: {line!r}"
    keys = _env_keys(match.group(1))

    assert keys == [expected_key], f"key-parsing mismatch for {line!r}: got {keys!r}"
    assert _is_credential_shaped(keys[0]) == expect_flagged, f"deny-list mismatch for {line!r}"


def test_env_credential_guard_catches_key_after_first_on_multi_var_line():
    """Docker allows `ENV KEY1=val1 KEY2=val2 ...` on a single line. A
    credential-shaped key placed second (or later) on such a line must
    still be caught -- not silently skipped because only the first key on
    the line was ever extracted. Mirrors this repo's own real shape (`ENV
    HOME=...` is always safe) with a planted second key that is not."""
    line = "ENV HOME=/app/.home DB_PASSWORD=hunter2"
    match = ENV_HEADER_RE.match(line)
    assert match, f"regex failed to match a syntactically valid ENV line: {line!r}"
    keys = _env_keys(match.group(1))

    assert keys == ["HOME", "DB_PASSWORD"], f"multi-var key extraction mismatch: {keys!r}"
    assert _is_credential_shaped("HOME") is False
    assert _is_credential_shaped("DB_PASSWORD") is True
