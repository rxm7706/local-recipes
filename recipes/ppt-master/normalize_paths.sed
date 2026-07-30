# Rewrite every internal reference to the renamed brand/deck kits and logo
# files. Applied to *.md / *.svg / *.json under the staged skills tree by both
# build.sh and build.bat (GNU sed on unix, m2-sed on Windows).
#
# Only PATH-shaped and IDENTIFIER-shaped occurrences are rewritten. Chinese
# prose inside document bodies is deliberately left alone: prose does not
# trigger conda's path warnings, and rewriting it would corrupt the docs
# (e.g. "CATARC (中汽研) Brand Specification").

# --- logo filenames (these only ever appear as path references) --------------
s|电建logo\.png|powerchina-logo.png|g
s|华东院logo\.png|east-china-institute-logo.png|g
s|中国水务logo\.png|china-water-logo.png|g
s|水电三局logo\.png|sinohydro-bureau3-logo.png|g
s|大型 logo\.png|large-logo.png|g
s|右上角 logo\.png|header-logo.png|g

# --- brand_id frontmatter must track the directory name ---------------------
s|brand_id: 中国电信|brand_id: china-telecom|g
s|brand_id: 中国电建|brand_id: powerchina|g
s|brand_id: 中汽研|brand_id: catarc|g

# --- explicit path references to a kit directory ----------------------------
s|brands/中国电信|brands/china-telecom|g
s|brands/中国电建|brands/powerchina|g
s|brands/中汽研|brands/catarc|g
s|decks/中国电信|decks/china-telecom|g
s|decks/中国电建|decks/powerchina|g
s|decks/中汽研|decks/catarc|g

# --- brands_index.json / decks_index.json top-level keys --------------------
s|"中国电信":|"china-telecom":|g
s|"中国电建":|"powerchina":|g
s|"中汽研":|"catarc":|g
