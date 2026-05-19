"""
PDF report generation from an Analysed Summary brief JSON.
Uses ReportLab (pure Python, no system dependencies).
"""
import io
import re
from datetime import datetime
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph,
    Spacer, HRFlowable, PageBreak, KeepTogether,
)

# ── Brand colours ─────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0f3460")
RED    = colors.HexColor("#e94560")
LIGHT  = colors.HexColor("#f0f4ff")
GREY   = colors.HexColor("#6b7280")
WHITE  = colors.white
BLACK  = colors.HexColor("#1a1a2e")


def _styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        base.add(ParagraphStyle(name=name, **kw))

    add("CoverTitle",   fontSize=28, textColor=WHITE,  fontName="Helvetica-Bold",
        spaceAfter=8,  leading=34)
    add("CoverSub",     fontSize=13, textColor=colors.HexColor("#a8dadc"),
        fontName="Helvetica", spaceAfter=30, leading=18)
    add("CoverMeta",    fontSize=9,  textColor=colors.HexColor("#cccccc"),
        fontName="Helvetica", spaceAfter=4,  leading=13)
    add("CoverLabel",   fontSize=8,  textColor=colors.HexColor("#a8dadc"),
        fontName="Helvetica-Bold", spaceAfter=2, leading=11,
        wordWrap="CJK")

    add("SectionHead",  fontSize=14, textColor=NAVY, fontName="Helvetica-Bold",
        spaceBefore=6, spaceAfter=8, leading=18)
    add("ExecHead",     fontSize=14, textColor=WHITE, fontName="Helvetica-Bold",
        spaceBefore=4, spaceAfter=8, leading=18)
    add("SubHead",      fontSize=11, textColor=BLACK, fontName="Helvetica-Bold",
        spaceBefore=8, spaceAfter=4, leading=14)
    add("Body",         fontSize=10, textColor=BLACK, fontName="Helvetica",
        spaceAfter=6,  leading=15, alignment=TA_JUSTIFY)
    add("ExecBody",     fontSize=10, textColor=colors.HexColor("#e5e7eb"),
        fontName="Helvetica", spaceAfter=6, leading=15, alignment=TA_JUSTIFY)
    add("BulletItem",   fontSize=10, textColor=BLACK, fontName="Helvetica",
        spaceAfter=6,  leading=15, leftIndent=16, bulletIndent=4)
    add("Tag",          fontSize=8,  textColor=NAVY,  fontName="Helvetica",
        spaceAfter=6,  leading=10,
        backColor=colors.HexColor("#e8f4f8"),
        borderPadding=(2, 6, 2, 6), borderRadius=8)
    add("Footer",       fontSize=7,  textColor=GREY,  fontName="Helvetica",
        alignment=TA_CENTER, leading=10)

    return base


def _cover_background(canvas, doc):
    """Draw the dark-navy cover page background."""
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.restoreState()


def _page_footer(canvas, doc):
    """Draw page number footer on non-cover pages."""
    canvas.saveState()
    w, _ = A4
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(w / 2, 1.2 * cm,
                             f"Confidential — Page {doc.page}")
    canvas.restoreState()


def _render_text(text: str, styles, body_style="Body", exec_mode=False) -> list:
    """Convert plain/markdown text into ReportLab flowables."""
    flowables = []
    body_st  = styles[body_style]
    sub_st   = styles["SubHead"]
    bullet_st = styles["BulletItem"]

    lines = [ln for ln in text.split("\n") if ln.strip()]
    for line in lines:
        stripped = line.strip()

        # Bold heading: **text** or ## heading
        if re.match(r"^\*\*.+\*\*$", stripped) or re.match(r"^#{1,3}\s", stripped):
            clean = re.sub(r"^#+\s*", "", stripped).replace("**", "")
            flowables.append(Paragraph(clean, sub_st))

        # Numbered list
        elif re.match(r"^\d+\.\s", stripped):
            clean = re.sub(r"^\d+\.\s*", "", stripped)
            # Bold the first part if **...**
            clean = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", clean)
            num   = re.match(r"^(\d+)", stripped).group(1)
            flowables.append(Paragraph(
                f"<b>{num}.</b> {clean}", bullet_st))

        # Bullet
        elif stripped.startswith("- ") or stripped.startswith("• "):
            clean = stripped.lstrip("-•").strip()
            clean = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", clean)
            flowables.append(Paragraph(f"• {clean}", bullet_st))

        else:
            clean = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
            flowables.append(Paragraph(clean, body_st))

    return flowables


def generate_pdf(brief: Dict) -> bytes:
    """Render the brief dict to a PDF and return bytes."""
    buf    = io.BytesIO()
    styles = _styles()
    w, h   = A4

    # ── Document with two page templates ─────────────────────────────────────
    margin = 2 * cm
    cover_frame  = Frame(margin, margin, w - 2*margin, h - 2*margin,
                         id="cover",  showBoundary=0)
    content_frame = Frame(margin, 1.8*cm, w - 2*margin, h - margin - 1.8*cm,
                          id="content", showBoundary=0)

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=1.8*cm,
    )
    doc.addPageTemplates([
        PageTemplate(id="Cover",   frames=[cover_frame],
                     onPage=_cover_background),
        PageTemplate(id="Content", frames=[content_frame],
                     onPage=_page_footer),
    ])

    story = []

    # ── Cover page ────────────────────────────────────────────────────────────
    company  = brief.get("company", "Company")
    industry = brief.get("industry", "")
    date     = datetime.utcnow().strftime("%B %d, %Y")

    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph("CONFIDENTIAL — STRATEGY BRIEF", styles["CoverLabel"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(company, styles["CoverTitle"]))
    story.append(Paragraph("Analysed Summary Report", styles["CoverSub"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(f"<b>Industry:</b> {industry}", styles["CoverMeta"]))
    story.append(Paragraph(f"<b>Generated:</b> {date}", styles["CoverMeta"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "Prepared by AI Market Research Tool — For Consultant Use Only",
        styles["CoverMeta"]))

    story.append(PageBreak())

    # ── Executive Summary (light-blue background via coloured paragraph) ──────
    story.append(Paragraph("Executive Summary", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=2, color=RED, spaceAfter=10))
    exec_text = brief.get("executive_summary", "")
    story.extend(_render_text(exec_text, styles))
    story.append(Spacer(1, 0.5 * cm))

    # ── Detailed sections ────────────────────────────────────────────────────
    for section in brief.get("sections", []):
        block = []
        block.append(Paragraph(section["title"], styles["SectionHead"]))
        block.append(HRFlowable(width="100%", thickness=1.5, color=RED, spaceAfter=8))
        if section.get("sources"):
            block.append(Paragraph(
                f"Source: {', '.join(section['sources'])}", styles["Tag"]))
        block.extend(_render_text(section.get("content", ""), styles))
        block.append(Spacer(1, 0.4 * cm))
        story.append(KeepTogether(block[:4]))   # keep heading + first para together
        story.extend(block[4:])

    # ── Strategic Recommendations ─────────────────────────────────────────────
    story.append(Paragraph("Strategic Recommendations", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=2, color=RED, spaceAfter=10))
    story.extend(_render_text(brief.get("strategic_recommendations", ""), styles))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Paragraph(
        f"Confidential — {company} Strategy Brief — Generated {date}",
        styles["Footer"]))

    doc.build(story)
    return buf.getvalue()
