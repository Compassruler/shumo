"""Render the non-source parameter inventory Markdown as a polished PDF."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "非题给参数与新增假设清单.md"
OUTPUT = ROOT / "reports" / "非题给参数与新增假设清单.pdf"

PAGE_W, PAGE_H = A4
LEFT = RIGHT = 16 * mm
TOP = 17 * mm
BOTTOM = 16 * mm
CONTENT_W = PAGE_W - LEFT - RIGHT

NAVY = colors.HexColor("#18324A")
TEAL = colors.HexColor("#1B7284")
LIGHT_TEAL = colors.HexColor("#DDEEF1")
LIGHT_BLUE = colors.HexColor("#EDF3F7")
GRID = colors.HexColor("#AEBCC6")
TEXT = colors.HexColor("#202B33")
MUTED = colors.HexColor("#667784")


FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"
pdfmetrics.registerFont(TTFont("Heiti", FONT_PATH, subfontIndex=0))
pdfmetrics.registerFontFamily("Heiti", normal="Heiti", bold="Heiti", italic="Heiti", boldItalic="Heiti")


def inline(text: str) -> str:
    text = html.escape(text.strip())
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", text)
    return text


styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "TitleCN",
    parent=styles["Title"],
    fontName="Heiti",
    fontSize=20,
    leading=28,
    textColor=NAVY,
    alignment=TA_CENTER,
    spaceAfter=8 * mm,
)
h2_style = ParagraphStyle(
    "H2CN",
    parent=styles["Heading2"],
    fontName="Heiti",
    fontSize=13.2,
    leading=18,
    textColor=TEAL,
    spaceBefore=5 * mm,
    spaceAfter=2.2 * mm,
    keepWithNext=True,
)
body_style = ParagraphStyle(
    "BodyCN",
    parent=styles["BodyText"],
    fontName="Heiti",
    fontSize=9.2,
    leading=14.2,
    textColor=TEXT,
    alignment=TA_LEFT,
    spaceAfter=2.0 * mm,
)
bullet_style = ParagraphStyle(
    "BulletCN",
    parent=body_style,
    leftIndent=5 * mm,
    firstLineIndent=-3.5 * mm,
    spaceAfter=1.2 * mm,
)
note_style = ParagraphStyle(
    "NoteCN",
    parent=body_style,
    fontSize=8.3,
    leading=12.5,
    textColor=MUTED,
)
cell_style = ParagraphStyle(
    "CellCN",
    parent=body_style,
    fontSize=7.3,
    leading=10.2,
    spaceAfter=0,
)
head_cell_style = ParagraphStyle(
    "HeadCellCN",
    parent=cell_style,
    fontSize=7.6,
    leading=10.5,
    textColor=colors.white,
    alignment=TA_CENTER,
)


def page_decor(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(TEAL)
    canvas.setLineWidth(0.8)
    canvas.line(LEFT, PAGE_H - 10 * mm, PAGE_W - RIGHT, PAGE_H - 10 * mm)
    canvas.setFont("Heiti", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(LEFT, 8 * mm, "问题一：非题给参数与新增假设清单")
    canvas.drawRightString(PAGE_W - RIGHT, 8 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


class InventoryDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=LEFT,
            rightMargin=RIGHT,
            topMargin=TOP,
            bottomMargin=BOTTOM,
            title="问题一非题给参数与新增假设清单",
            author="问题一建模工作文件",
            subject="参数来源、经验闭合、数值设置与结构假设审计",
        )
        frame = Frame(LEFT, BOTTOM, CONTENT_W, PAGE_H - TOP - BOTTOM, id="main")
        self.addPageTemplates(PageTemplate(id="content", frames=[frame], onPage=page_decor))


def column_widths(ncols: int):
    ratios = {
        3: [1.2, 1.5, 2.8],
        4: [1.35, 1.45, 1.45, 2.15],
        5: [0.38, 1.15, 1.45, 1.35, 2.15],
    }.get(ncols, [1] * ncols)
    total = sum(ratios)
    return [CONTENT_W * r / total for r in ratios]


def make_table(rows: list[list[str]]):
    ncols = len(rows[0])
    rendered = []
    for ridx, row in enumerate(rows):
        style = head_cell_style if ridx == 0 else cell_style
        rendered.append([Paragraph(inline(cell), style) for cell in row])
    table = LongTable(
        rendered,
        colWidths=column_widths(ncols),
        repeatRows=1,
        splitByRow=True,
        hAlign="LEFT",
    )
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for ridx in range(1, len(rows)):
        if ridx % 2 == 0:
            commands.append(("BACKGROUND", (0, ridx), (-1, ridx), LIGHT_BLUE))
    table.setStyle(TableStyle(commands))
    return table


def parse_markdown(text: str):
    lines = text.splitlines()
    story = []
    paragraph: list[str] = []

    def flush_paragraph():
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), body_style))
            paragraph.clear()

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            flush_paragraph()
            i += 1
            continue
        if stripped.startswith("# "):
            flush_paragraph()
            story.append(Spacer(1, 5 * mm))
            story.append(Paragraph(inline(stripped[2:]), title_style))
            story.append(Paragraph("参数来源 · 经验闭合 · 数值设置 · 结构假设", note_style))
            story.append(Spacer(1, 3 * mm))
            i += 1
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(inline(stripped[3:]), h2_style))
            i += 1
            continue
        if stripped.startswith("|"):
            flush_paragraph()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            raw_rows = [[c.strip() for c in row.strip("|").split("|")] for row in table_lines]
            if len(raw_rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", c) for c in raw_rows[1]):
                raw_rows.pop(1)
            story.append(make_table(raw_rows))
            story.append(Spacer(1, 2.5 * mm))
            continue
        if re.match(r"^-\s+", stripped):
            flush_paragraph()
            story.append(Paragraph("• " + inline(re.sub(r"^-\s+", "", stripped)), bullet_style))
            i += 1
            continue
        numbered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if numbered:
            flush_paragraph()
            story.append(Paragraph(f"{numbered.group(1)}. " + inline(numbered.group(2)), bullet_style))
            i += 1
            continue
        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    return story


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = InventoryDoc(str(OUTPUT))
    story = parse_markdown(SOURCE.read_text(encoding="utf-8"))
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
