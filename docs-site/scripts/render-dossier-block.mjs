#!/usr/bin/env node
/** Golden-test helper: render one dossier block JSON to HTML (Story 43.1). */
import { readFileSync } from 'node:fs';

import { renderBlock } from '../src/lib/dossier-blocks.ts';

const json = readFileSync(0, 'utf8');
const block = JSON.parse(json);
process.stdout.write(renderBlock(block));
