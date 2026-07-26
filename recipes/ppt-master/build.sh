#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "skills/ppt-master" ]; then
    echo "ERROR: skills/ppt-master/ directory not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/ppt-master"
mkdir -p "${SHARE}/skills"
cp -r skills/ppt-master "${SHARE}/skills/"
cp LICENSE README.md "${SHARE}/"

SKILL="${SHARE}/skills/ppt-master"

# Drop the legacy halves of the AI image reference gallery (~20 MB of 44 MB).
# Upstream's own references/ai-image-comparison/README.md states the Confirm UI
# "displays rendering only", calls palette/ "legacy diagnostic material ... not
# a runtime catalog", and calls type/ an internal composition reference.
# rendering/ is KEPT because scripts/confirm_ui/server.py actively serves it.
rm -rf "${SKILL}/references/ai-image-comparison/palette"
rm -rf "${SKILL}/references/ai-image-comparison/type"

# --- ASCII-normalize the brand/deck kit paths -------------------------------
# Upstream names three brand kits and two deck kits in Chinese and ships six
# logo files whose names are non-ASCII and/or contain spaces. conda emits 34
# path warnings for those. Rename them and rewrite every internal reference
# (SVG href=, design_spec.md asset tables, brand_id frontmatter, and the
# brands_index.json / decks_index.json keys) so nothing breaks.
#
# Done with mv + sed rather than a Python helper on purpose: this recipe is
# noarch:generic, and an unpinned `python` build dep makes rattler-build expand
# the python variant matrix, splitting one noarch package into four identical
# py3XX artifacts.
for base in brands decks; do
    d="${SKILL}/templates/${base}"
    [ -d "${d}/中国电信" ] && mv "${d}/中国电信" "${d}/china-telecom"
    [ -d "${d}/中国电建" ] && mv "${d}/中国电建" "${d}/powerchina"
    [ -d "${d}/中汽研" ]   && mv "${d}/中汽研"   "${d}/catarc"
done

# Logo files (paths are known now that the kit directories are ASCII).
for base in brands decks; do
    p="${SKILL}/templates/${base}/powerchina/images"
    [ -f "${p}/电建logo.png" ]     && mv "${p}/电建logo.png"     "${p}/powerchina-logo.png"
    [ -f "${p}/华东院logo.png" ]   && mv "${p}/华东院logo.png"   "${p}/east-china-institute-logo.png"
    [ -f "${p}/中国水务logo.png" ] && mv "${p}/中国水务logo.png" "${p}/china-water-logo.png"
    [ -f "${p}/水电三局logo.png" ] && mv "${p}/水电三局logo.png" "${p}/sinohydro-bureau3-logo.png"
    c="${SKILL}/templates/${base}/catarc/images"
    [ -f "${c}/大型 logo.png" ]   && mv "${c}/大型 logo.png"   "${c}/large-logo.png"
    [ -f "${c}/右上角 logo.png" ] && mv "${c}/右上角 logo.png" "${c}/header-logo.png"
done

# Rewrite the references. `sed -i.bak` is the portable in-place form (GNU sed
# and BSD/macOS sed both accept it); the backups are removed straight after.
# Whole tree, not just templates/: scripts/prompt_audit_manifest.json carries a
# "paths" array referencing the brand design_spec.md files, so a templates-only
# pass leaves those references dangling.
# *.py is included for one stale --help usage string in
# scripts/svg_quality_checker.py; it is the only .py hit for these patterns.
find "${SKILL}" -type f \( -name '*.md' -o -name '*.svg' -o -name '*.json' -o -name '*.py' \) \
    -exec sed -i.bak -f "${RECIPE_DIR}/normalize_paths.sed" {} +
find "${SKILL}" -type f -name '*.bak' -delete

# Fail loudly if any non-ASCII or spaced path survived -- a silent miss would
# reintroduce the warnings this exists to remove.
if find "${SKILL}" | LC_ALL=C grep -qP '[^\x00-\x7F]| '; then
    echo "ERROR: non-ASCII/spaced paths remain after normalization:" >&2
    find "${SKILL}" | LC_ALL=C grep -P '[^\x00-\x7F]| ' >&2
    exit 1
fi

mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/ppt_master_install.py" "${PREFIX}/bin/ppt-master-install"
chmod +x "${PREFIX}/bin/ppt-master-install"
