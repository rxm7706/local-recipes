#!/usr/bin/env node
/**
 * Render a herald slide-model JSON file to a native editable .pptx (Story 32.1).
 *
 * Usage: node pptx_native.mjs <model.json> <output.pptx>
 * Requires pptxgenjs-plus on NODE_PATH ($CONDA_PREFIX/lib/node_modules).
 */
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

const require = createRequire(import.meta.url);
const PptxGenJS = require("pptxgenjs-plus");

const [, , modelArg, outArg] = process.argv;
if (!modelArg || !outArg) {
  console.error("usage: node pptx_native.mjs <model.json> <output.pptx>");
  process.exit(1);
}

const model = JSON.parse(readFileSync(modelArg, "utf8"));
const pres = new PptxGenJS();
pres.layout = "LAYOUT_16x9";

for (const slide of model.slides || []) {
  const s = pres.addSlide();
  let y = 0.4;
  if (slide.title) {
    s.addText(slide.title, {
      x: 0.5,
      y,
      w: 9,
      h: 0.8,
      fontSize: 32,
      bold: true,
    });
    y += 1.0;
  }
  if (slide.bullets && slide.bullets.length) {
    const runs = slide.bullets.map((text) => ({ text, options: { bullet: true } }));
    s.addText(runs, { x: 0.5, y, w: 9, h: 4, fontSize: 18 });
    y += Math.min(4, 0.35 * slide.bullets.length + 0.5);
  }
  if (slide.table && slide.table.length) {
    const rows = slide.table.map((row) => row.map((cell) => ({ text: String(cell) })));
    s.addTable(rows, { x: 0.5, y: Math.max(y, 1.5), w: 8.5, fontSize: 14, border: { pt: 1 } });
  }
  for (const img of slide.images || []) {
    if (!img.path) continue;
    try {
      s.addImage({ path: img.path, x: 6.5, y: 1.2, w: 3, h: 2.2, altText: img.alt || "" });
    } catch (err) {
      console.error(`pptx-native: skip image ${img.path}: ${err}`);
    }
  }
  if (slide.notes) {
    s.addNotes(slide.notes);
  }
}

await pres.writeFile({ fileName: outArg });
