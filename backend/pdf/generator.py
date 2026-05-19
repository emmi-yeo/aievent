"""
PDF report generation from an Analysed Summary brief JSON.
Uses ReportLab (pure Python, no system dependencies).
"""
import io
import re
from datetime import datetime
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph,
    Spacer, HRFlowable, PageBreak, KeepTogether, NextPageTemplate,
)

# ── Brand colours ─────────────────────────────────────────────────────────────
NAVY    = colors.HexColor("#0f3460")
RED     = colors.HexColor("#e94560")
SLATE   = colors.HexColor("#1e293b")
GREY    = colors.HexColor("#6b7280")
LGREY   = colors.HexColor("#f1f5f9")
WHITE   = colors.white


def _styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        base.add(ParagraphStyle(name=name, **kw))

    # Cover
    add("CoverLabel",  fontSize=9,  textColor=colors.HexColor("#94a3b8"),
        fontName="Helvetica-Bold", spaceAfter=6, leading=12,
        letterSpacing=2)
    add("CoverTitle",  fontSize=34, textColor=WHITE, fontName="Helvetica-Bold",
        spaceAfter=10, leading=40)
    add("CoverSub",    fontSize=14, textColor=colors.HexColor("#cbd5e1"),
        fontName="Helvetica", spaceAfter=28, leading=20)
    add("CoverMeta",   fontSize=10, textColor=colors.HexColor("#94a3b8"),
        fontName="Helvetica", spaceAfter=5, leading=15)

    # Section headings
    add("SectionHead", fontSize=16, textColor=NAVY, fontName="Helvetica-Bold",
        spaceBefore=4, spaceAfter=6, leading=22)
    add("SubHead",     fontSize=12, textColor=SLATE, fontName="Helvetica-Bold",
        spaceBefore=10, spaceAfter=4, leading=16)

    # Body text — left-aligned, comfortable size
    add("Body",        fontSize=11, textColor=SLATE, fontName="Helvetica",
        spaceAfter=8, leading=18, alignment=TA_LEFT)
    add("ExecBody",    fontSize=11, textColor=colors.HexColor("#e2e8f0"),
        fontName="Helvetica", spaceAfter=8, leading=18, alignment=TA_LEFT)

    # Lists
    add("Numbered",    fontSize=11, textColor=SLATE, fontName="Helvetica",
        spaceAfter=8, leading=18, leftIndent=20, firstLineIndent=0)
    add("BulletItem",  fontSize=11, textColor=SLATE, fontName="Helvetica",
        spaceAfter=6, leading=18, leftIndent=20)

    # Source tag — rendered as small label above section
    add("SourceTag",   fontSize=8,  textColor=colors.HexColor("#2563eb"),
        fontName="Helvetica-Bold", spaceAfter=8, leading=11,
        backColor=colors.HexColor("#dbeafe"),
        borderPadding=(3, 8, 3, 8))

    add("Footer",      fontSize=8,  textColor=GREY, fontName="Helvetica",
        alignment=TA_CENTER, leading=10)

    return base


def _cover_background(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Dark gradient-like navy cover
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    # Subtle red accent stripe at bottom
    canvas.setFillColor(RED)
    canvas.rect(0, 0, w, 0.6 * cm, fill=1, stroke=0)
    canvas.restoreState()


def _page_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Ensure content pages are always white
    canvas.setFillColor(WHITE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    # Footer rule + page number
    canvas.setFillColor(colors.HexColor("#e2e8f0"))
    canvas.rect(0, 1 * cm, w, 0.05 * cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(w / 2, 0.5 * cm,
                             f"Confidential  ·  Page {doc.page}")
    canvas.restoreState()


def _render_text(text: str, styles, exec_mode=False) -> list:
    """Convert plain/markdown text into ReportLab flowables."""
    flowables = []
    body_st   = styles["ExecBody"] if exec_mode else styles["Body"]
    sub_st    = styles["SubHead"]
    num_st    = styles["Numbered"]
    bul_st    = styles["BulletItem"]

    lines = [ln for ln in text.split("\n") if ln.strip()]
    for line in lines:
        stripped = line.strip()

        # Bold heading: ## heading or standalone **text**
        if re.match(r"^#{1,3}\s", stripped):
            clean = re.sub(r"^#+\s*", "", stripped).replace("**", "")
            flowables.append(Paragraph(clean, sub_st))

        # Numbered list item
        elif re.match(r"^\d+\.\s", stripped):
            body = re.sub(r"^\d+\.\s*", "", stripped)
            body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body)
            num  = re.match(r"^(\d+)", stripped).group(1)
            flowables.append(
                Paragraph(f"<b>{num}.</b>  {body}", num_st))

        # Bullet
        elif stripped.startswith(("- ", "• ", "* ")):
            body = re.sub(r"^[-•*]\s+", "", stripped)
            body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body)
            flowables.append(Paragraph(f"•  {body}", bul_st))

        else:
            clean = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
            clean = re.sub(r"^#+\s*", "", clean)
            flowables.append(Paragraph(clean, body_st))

    return flowables


def generate_pdf(brief: Dict) -> bytes:
    buf    = io.BytesIO()
    styles = _styles()
    w, h   = A4

    margin = 2.2 * cm
    cover_frame   = Frame(margin, 1.5*cm, w - 2*margin, h - 2*margin,
                          id="cover", showBoundary=0)
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
    company  = brief.get("company", "Company")
    industry = brief.get("industry", "")
    date     = datetime.utcnow().strftime("%B %d, %Y")

    # ── Cover ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph("STRATEGY BRIEF  ·  CONFIDENTIAL", styles["CoverLabel"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(company, styles["CoverTitle"]))
    story.append(Paragraph("Analysed Summary Report", styles["CoverSub"]))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=colors.HexColor("#334155"), spaceAfter=20))
    story.append(Paragraph(f"<b>Industry:</b>   {industry}", styles["CoverMeta"]))
    story.append(Paragraph(f"<b>Generated:</b>  {date}",    styles["CoverMeta"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "Prepared by AI Market Research Tool — For Consultant Use Only",
        styles["CoverMeta"]))
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ── Executive Summary ────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=2.5, color=RED, spaceAfter=14))
    story.extend(_render_text(brief.get("executive_summary", ""), styles))
    story.append(Spacer(1, 0.8 * cm))

    # ── Detailed sections ────────────────────────────────────────────────────
    for section in brief.get("sections", []):
        block = []
        block.append(Paragraph(section["title"], styles["SectionHead"]))
        block.append(HRFlowable(width="100%", thickness=1.5,
                                 color=RED, spaceAfter=10))
        if section.get("sources"):
            block.append(Paragraph(
                f"SOURCE:  {',  '.join(section['sources']).upper()}",
                styles["SourceTag"]))
        block.extend(_render_text(section.get("content", ""), styles))
        block.append(Spacer(1, 0.6 * cm))
        # Keep heading + rule + first paragraph together
        story.append(KeepTogether(block[:3]))
        story.extend(block[3:])

    # ── Strategic Recommendations ─────────────────────────────────────────────
    story.append(Paragraph("Strategic Recommendations", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=2.5, color=RED, spaceAfter=14))
    story.extend(_render_text(brief.get("strategic_recommendations", ""), styles))

    # ── Document footer ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Confidential  ·  {company} Strategy Brief  ·  Generated {date}",
        styles["Footer"]))

    doc.build(story)
    return buf.getvalue()
