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

function addBlock(s, block, yRef) {
  let y = yRef.value;
  const kind = block.kind;
  if (kind === "heading") {
    const size = Math.max(14, 34 - block.level * 2);
    s.addText(block.text, {
      x: 0.5,
      y,
      w: 9,
      h: 0.7,
      fontSize: size,
      bold: true,
    });
    yRef.value = y + 0.85;
    return;
  }
  if (kind === "paragraph") {
    s.addText(block.text, { x: 0.5, y, w: 9, h: 2, fontSize: 18, valign: "top" });
    yRef.value = y + 1.0;
    return;
  }
  if (kind === "quote") {
    s.addText(block.text, {
      x: 0.7,
      y,
      w: 8.5,
      h: 1.2,
      fontSize: 16,
      italic: true,
      color: "666666",
    });
    yRef.value = y + 1.0;
    return;
  }
  if (kind === "code") {
    s.addText(block.text, {
      x: 0.5,
      y,
      w: 9,
      h: 2,
      fontSize: 12,
      fontFace: "Courier New",
      valign: "top",
    });
    yRef.value = y + 1.2;
    return;
  }
  if (kind === "bullets") {
    const runs = (block.items || []).map((item) => ({
      text: item.text,
      options: { bullet: true, indentLevel: item.depth || 0 },
    }));
    if (runs.length) {
      s.addText(runs, { x: 0.5, y, w: 9, h: 4, fontSize: 18, valign: "top" });
      yRef.value = y + Math.min(4, 0.35 * runs.length + 0.5);
    }
    return;
  }
  if (kind === "numbered") {
    const runs = (block.items || []).map((item) => ({
      text: `${item.number}. ${item.text}`,
      options: { bullet: { type: "number" } },
    }));
    if (runs.length) {
      s.addText(runs, { x: 0.5, y, w: 9, h: 4, fontSize: 18, valign: "top" });
      yRef.value = y + Math.min(4, 0.35 * runs.length + 0.5);
    }
    return;
  }
  if (kind === "table" && block.rows && block.rows.length) {
    const rows = block.rows.map((row) => row.map((cell) => ({ text: String(cell) })));
    s.addTable(rows, { x: 0.5, y: Math.max(y, 1.0), w: 8.5, fontSize: 14, border: { pt: 1 } });
    yRef.value = y + 1.5;
  }
}

for (const slide of model.slides || []) {
  const s = pres.addSlide();
  const yRef = { value: 0.4 };
  if (slide.title) {
    s.addText(slide.title, {
      x: 0.5,
      y: yRef.value,
      w: 9,
      h: 0.8,
      fontSize: 32,
      bold: true,
    });
    yRef.value += 1.0;
  }
  const blocks = slide.blocks && slide.blocks.length ? slide.blocks : legacyBlocks(slide);
  for (const block of blocks) {
    addBlock(s, block, yRef);
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

function legacyBlocks(slide) {
  const out = [];
  if (slide.bullets && slide.bullets.length) {
    out.push({
      kind: "bullets",
      items: slide.bullets.map((text) => ({ text, depth: 0 })),
    });
  }
  if (slide.table && slide.table.length) {
    out.push({ kind: "table", rows: slide.table });
  }
  return out;
}

await pres.writeFile({ fileName: outArg });
