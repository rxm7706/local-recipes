import fs from "node:fs";
import path from "node:path";
const root = process.argv[2];
const walk = (d) => {
  for (const e of fs.readdirSync(d, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else if (/^(licen[cs]e|copying)/i.test(e.name)) {
      const bar = "=".repeat(78);
      process.stdout.write(`${bar}\n${path.relative(root, p)}\n${bar}\n${fs.readFileSync(p, "utf8")}\n`);
    }
  }
};
walk(root);
