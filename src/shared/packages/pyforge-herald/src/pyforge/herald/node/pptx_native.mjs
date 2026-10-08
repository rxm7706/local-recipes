#!/usr/bin/env node
/**
 * Render a herald slide-model JSON file to a native editable .pptx (Story 32.1, 32.3).
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
const T = model.tokens;
if (!T) {
  console.error("pptx-native: model JSON missing tokens block");
  process.exit(1);
}

const pres = new PptxGenJS();
pres.layout = "LAYOUT_16x9";

const canvasW = T.canvas.width;
// presLayout width/height are EMU; positions use inches, font sizes use points (pptxgenjs-plus).
const slideWIn = pres.presLayout.width / (pres.presLayout.width / 10);
const pointsPerInch = 71 + 1;
const slideWPt = slideWIn * pointsPerInch;

function pxToIn(px) {
  return (px * slideWIn) / canvasW;
}

function pxToPt(px) {
  return (px * slideWPt) / canvasW;
}

function padLeftIn() {
  return pxToIn(T.spacing.padX);
}

function contentWidthIn() {
  return slideWIn - pxToIn(T.spacing.padX) * 2;
}

function gapIn() {
  return pxToIn(T.spacing.baseline);
}

function textColor() {
  return T.palette.text.replace(/^#/, "");
}

function addBlock(s, block, yRef) {
  let y = yRef.value;
  const kind = block.kind;
  const bodyFace = T.fonts.body;
  const headingFace = T.fonts.heading;
  const color = textColor();
  const x = padLeftIn();
  const w = contentWidthIn();
  const lineStep = gapIn();

  if (kind === "heading") {
    s.addText(block.text, {
      x,
      y,
      w,
      h: pxToIn(T.type.subtitle),
      fontSize: pxToPt(T.type.subtitle),
      fontFace: headingFace,
      bold: T.fonts.headingBold,
      color,
    });
    yRef.value = y + lineStep;
    return;
  }
  if (kind === "paragraph") {
    s.addText(block.text, {
      x,
      y,
      w,
      h: pxToIn(T.type.body) + lineStep,
      fontSize: pxToPt(T.type.body),
      fontFace: bodyFace,
      color,
      valign: "top",
    });
    yRef.value = y + lineStep;
    return;
  }
  if (kind === "quote") {
    s.addText(block.text, {
      x: x + lineStep,
      y,
      w: w - lineStep,
      h: pxToIn(T.type.body) + lineStep,
      fontSize: pxToPt(T.type.body),
      fontFace: bodyFace,
      italic: true,
      color,
    });
    yRef.value = y + lineStep;
    return;
  }
  if (kind === "code") {
    s.addText(block.text, {
      x,
      y,
      w,
      h: pxToIn(T.type.small) + lineStep * 2,
      fontSize: pxToPt(T.type.small),
      fontFace: bodyFace,
      color,
      valign: "top",
    });
    yRef.value = y + lineStep * 2;
    return;
  }
  if (kind === "bullets") {
    const runs = (block.items || []).map((item) => ({
      text: item.text,
      options: { bullet: true, indentLevel: item.depth || 0 },
    }));
    if (runs.length) {
      const blockH = lineStep * runs.length + pxToIn(T.type.body);
      s.addText(runs, {
        x,
        y,
        w,
        h: blockH,
        fontSize: pxToPt(T.type.body),
        fontFace: bodyFace,
        color,
        valign: "top",
      });
      yRef.value = y + blockH;
    }
    return;
  }
  if (kind === "numbered") {
    const runs = (block.items || []).map((item) => ({
      text: `${item.number}. ${item.text}`,
      options: { bullet: { type: "number" } },
    }));
    if (runs.length) {
      const blockH = lineStep * runs.length + pxToIn(T.type.body);
      s.addText(runs, {
        x,
        y,
        w,
        h: blockH,
        fontSize: pxToPt(T.type.body),
        fontFace: bodyFace,
        color,
        valign: "top",
      });
      yRef.value = y + blockH;
    }
    return;
  }
  if (kind === "table" && block.rows && block.rows.length) {
    const rows = block.rows.map((row) => row.map((cell) => ({ text: String(cell) })));
    const tableY = y > pxToIn(T.spacing.padTop) ? y : pxToIn(T.spacing.padTop);
    s.addTable(rows, {
      x,
      y: tableY,
      w,
      fontSize: pxToPt(T.type.small),
      fontFace: bodyFace,
      color,
      fill: { color: T.palette.surface.replace(/^#/, "") },
      border: { pt: pxToPt(T.type.kicker) / pxToPt(T.type.kicker), color },
    });
    yRef.value = tableY + lineStep * block.rows.length;
  }
}

for (const slide of model.slides || []) {
  const s = pres.addSlide();
  s.background = { color: T.palette.bg.replace(/^#/, "") };
  const yRef = { value: pxToIn(T.spacing.padTop) };
  if (slide.title) {
    s.addText(slide.title, {
      x: padLeftIn(),
      y: yRef.value,
      w: contentWidthIn(),
      h: pxToIn(T.type.title),
      fontSize: pxToPt(T.type.title),
      fontFace: T.fonts.heading,
      bold: T.fonts.headingBold,
      color: textColor(),
    });
    yRef.value += gapIn();
  }
  const blocks = slide.blocks && slide.blocks.length ? slide.blocks : legacyBlocks(slide);
  for (const block of blocks) {
    addBlock(s, block, yRef);
  }
  for (const img of slide.images || []) {
    if (!img.path) continue;
    try {
      const imgW = pxToIn(T.type.title);
      const imgH = pxToIn(T.type.subtitle);
      const imgX = slideWIn - padLeftIn() - imgW;
      const imgY = pxToIn(T.spacing.padTop) + gapIn();
      s.addImage({ path: img.path, x: imgX, y: imgY, w: imgW, h: imgH, altText: img.alt || "" });
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
