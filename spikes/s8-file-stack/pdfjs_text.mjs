// Prints {"<path>": "<text of page 1>"} for each PDF given, extracted with pdf.js (Firefox's engine).
// PDFJS_DIR must point to a folder where pdfjs-dist is installed: PDFJS_DIR=... node <this file> a.pdf b.pdf
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const root = process.env.PDFJS_DIR;
if (!root) {
  throw new Error("Set PDFJS_DIR to a folder with pdfjs-dist installed");
}
const { getDocument } = await import(
  pathToFileURL(join(root, "node_modules", "pdfjs-dist", "legacy", "build", "pdf.mjs")).href
);

const out = {};
for (const path of process.argv.slice(2)) {
  const data = new Uint8Array(await readFile(path));
  const task = getDocument({ data, verbosity: 0, isEvalSupported: false });
  const document = await task.promise;
  const page = await document.getPage(1);
  const content = await page.getTextContent();
  out[path] = content.items.map((item) => ("str" in item ? item.str + (item.hasEOL ? "\n" : "") : "")).join("");
  await task.destroy();
}
process.stdout.write(JSON.stringify(out));
