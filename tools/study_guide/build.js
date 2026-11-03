const fs = require("fs");
const L = require("./lib");
const { d, P, Paragraph, TextRun, AlignmentType, NAVY, MUTED, FONT, LevelFormat } = L;
const { Document, Packer, TableOfContents, Footer, Header, PageNumber, HeadingLevel, PageBreak } = d;

const flat = (arr) => arr.flat(Infinity);
const body = flat([require("./part1"), require("./part2"), require("./part3"), require("./part4"),
                   require("./part5"), require("./part6")]);

const title = [
  new Paragraph({ spacing: { before: 2400, after: 200 }, children: [new TextRun({ text: "Value-Aware Team-Level Stopping for Multi-Robot Exploration", bold: true, size: 44, color: NAVY, font: FONT })] }),
  new Paragraph({ spacing: { after: 400 }, children: [new TextRun({ text: "Study guide to the revised proposal deck: every slide, formula, metric, result and likely question explained", size: 26, color: MUTED, font: FONT })] }),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Chaitanya Goyal (2024A7PS0557P)", size: 24, font: FONT })] }),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Supervisor: Prof. Avinash Gautam · BITS Pilani", size: 24, font: FONT })] }),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Companion to Value_Aware_Stopping_Proposal_v2.pptx · 30 September 2026", size: 22, color: MUTED, font: FONT })] }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Contents")] }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
];

const numbering = { config: [
  { reference: "bullets", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 270 } } } }] },
  ...["num1", "num2", "num3", "num4", "num5", "num6"].map((ref) => ({ reference: ref, levels: [
    { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] })),
] };

const doc = new Document({
  creator: "Chaitanya Goyal", title: "Study guide: value-aware team-level stopping",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 34, bold: true, color: NAVY, font: FONT }, paragraph: { spacing: { before: 240, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 27, bold: true, color: NAVY, font: FONT }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, color: "333A55", font: FONT }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2, keepNext: true } },
    ],
  },
  numbering,
  features: { updateFields: true },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "Value-aware team-level stopping · study guide", size: 16, color: MUTED })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: MUTED })] })] }) },
    children: [...title, ...body],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("/home/claude/studydoc/Study_Guide_Value_Aware_Stopping.docx", buf);
  console.log("written", buf.length);
});
