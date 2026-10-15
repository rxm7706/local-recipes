/**
 * `docs-site-validate-sidebar` (Story 27.4; Story 43.7 moved it here from the retired `sidebar_from_map.py --check`):
 * `docs/map.yaml` and `docs/` agree -- every quadrant page is mapped once, every mapped page exists -- and the map
 * carries the `sections` list every menu of the site reads. Exits 1 listing every defect; writes nothing.
 *
 *     node scripts/nav-check.mts            # from docs-site/, after `npm ci` (it reads YAML with the `yaml` package)
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { parse as parseYaml } from 'yaml';

import { quadrantGroups, registry } from '../src/lib/nav.ts';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const file = path.join(repo, 'docs', 'map.yaml');
let errors: string[];
try {
  const reg = registry(parseYaml(fs.readFileSync(file, 'utf8')), file);
  errors = quadrantGroups(reg.pages, path.join(repo, 'docs')).errors;
} catch (exc) {
  errors = [(exc as Error).message];
}
for (const line of errors) {
  console.error(line);
}
process.exit(errors.length ? 1 : 0);
