// Small DSL on top of docx-js for the study document.
const fs = require("fs");
const d = require("docx");
const { Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
        ShadingType, BorderStyle, ImageRun, PageBreak, LevelFormat } = d;

const NAVY = "1E2761", MUTED = "5B6070", PALE = "F1F3F8", AMBERBG = "FDF3DF", GREENBG = "E6F3EC", REDBG = "FBEBE8";
const FONT = "Calibri";
const PAGE_W = 9360; // content width in DXA (US Letter, 1" margins)

// inline markup: **bold**, *italic*, `code`
function runs(str, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(str)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: str.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Consolas", size: 20, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < str.length) out.push(new TextRun({ text: str.slice(last), ...base }));
  return out;
}

const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun(t)] });
const H1nb = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const P = (t, opts = {}) => new Paragraph({ spacing: { after: 120, line: 276 }, children: runs(t, opts.run || {}),
                                           alignment: opts.align });
const B = (t, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, spacing: { after: 60, line: 264 },
                                           children: runs(t) });
const N = (t, ref = "num1") => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60, line: 264 },
                                              children: runs(t) });
const EQ = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 160 },
  shading: { type: ShadingType.CLEAR, color: "auto", fill: PALE },
  children: [new TextRun({ text: t, font: "Cambria Math", size: 24, bold: true, color: NAVY })] });

function box(lines, fill = PALE, title = null) {
  const children = [];
  if (title) children.push(new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: title, bold: true, color: NAVY, size: 23 })] }));
  for (const l of lines) {
    if (l.startsWith("- ")) children.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 50 }, children: runs(l.slice(2)) }));
    else children.push(new Paragraph({ spacing: { after: 80, line: 264 }, children: runs(l) }));
  }
  return new Table({
    width: { size: PAGE_W, type: WidthType.DXA }, columnWidths: [PAGE_W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: PAGE_W, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, color: "auto", fill },
      margins: { top: 140, bottom: 100, left: 200, right: 200 },
      borders: { top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
                 left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } },
      children })] })] });
}
const NOTE = (lines, title = "Note") => box(lines, PALE, title);
const WARN = (lines, title = "Careful") => box(lines, AMBERBG, title);
const SAY = (lines, title = "What to say") => box(lines, GREENBG, title);
const DONT = (lines, title = "Do not say") => box(lines, REDBG, title);
const SP = () => new Paragraph({ spacing: { after: 60 }, children: [] });

// table: rows = array of arrays of strings (markup ok); widths in fractions or DXA
function T(rows, widths, opts = {}) {
  const total = PAGE_W;
  let w = widths.map((x) => (x <= 1 ? Math.round(x * total) : x));
  const diff = total - w.reduce((a, b) => a + b, 0); w[w.length - 1] += diff;
  const border = { style: BorderStyle.SINGLE, size: 2, color: "D5D8E0" };
  const borders = { top: border, bottom: border, left: border, right: border };
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: w,
    rows: rows.map((row, r) => new TableRow({ tableHeader: r === 0, children: row.map((cell, c) => new TableCell({
      width: { size: w[c], type: WidthType.DXA }, borders,
      shading: { type: ShadingType.CLEAR, color: "auto", fill: r === 0 ? NAVY : (opts.hl && opts.hl.includes(r) ? "E4E8F6" : (r % 2 ? "FFFFFF" : PALE)) },
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: String(cell).split("\n").map((line) => new Paragraph({ spacing: { after: 20 },
        children: runs(line, r === 0 ? { bold: true, color: "FFFFFF", size: 19 } : { size: 19, bold: (opts.boldFirst && c === 0) || undefined }) })) })) })) });
}

function IMG(path, wIn, hIn, caption) {
  const out = [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 40 },
    children: [new ImageRun({ type: "png", data: fs.readFileSync(path), transformation: { width: wIn * 96, height: hIn * 96 },
      altText: { title: caption || "figure", description: caption || "figure", name: "figure" } })] })];
  if (caption) out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
    children: [new TextRun({ text: caption, italics: true, size: 18, color: MUTED })] }));
  return out;
}
function QA(q, a) {
  const out = [new Paragraph({ spacing: { before: 140, after: 60 }, keepNext: true,
    children: [new TextRun({ text: "Q. ", bold: true, color: "A86E10" }), ...runs(q, { bold: true })] })];
  (Array.isArray(a) ? a : [a]).forEach((x) => out.push(x.startsWith("- ") ? B(x.slice(2)) :
    new Paragraph({ spacing: { after: 80, line: 264 }, children: [new TextRun({ text: "", bold: true }), ...runs(x)] })));
  return out;
}
module.exports = { d, runs, H1, H1nb, H2, H3, P, B, N, EQ, NOTE, WARN, SAY, DONT, SP, T, IMG, QA, PageBreak, Paragraph, TextRun,
                   AlignmentType, NAVY, MUTED, FONT, LevelFormat };
