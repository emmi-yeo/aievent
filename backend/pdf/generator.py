"""
PDF report generation from an Analysed Summary brief JSON.
Uses WeasyPrint to render an HTML template to PDF.
"""
import json
from datetime import datetime
from typing import Dict


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Georgia', serif; font-size: 11pt; color: #1a1a2e; line-height: 1.6; }}
  .cover {{ page-break-after: always; display: flex; flex-direction: column;
            justify-content: center; min-height: 100vh; padding: 80px 60px;
            background: #0f3460; color: white; }}
  .cover h1 {{ font-size: 32pt; font-weight: bold; margin-bottom: 12px; }}
  .cover .subtitle {{ font-size: 14pt; color: #a8dadc; margin-bottom: 40px; }}
  .cover .meta {{ font-size: 10pt; color: #ccc; }}
  .cover .label {{ font-size: 9pt; text-transform: uppercase;
                   letter-spacing: 2px; color: #a8dadc; margin-bottom: 4px; }}
  .section {{ padding: 40px 60px; page-break-inside: avoid; }}
  .section + .section {{ border-top: 1px solid #e0e0e0; }}
  h2 {{ font-size: 16pt; color: #0f3460; margin-bottom: 16px;
        padding-bottom: 8px; border-bottom: 2px solid #e94560; }}
  h3 {{ font-size: 12pt; color: #16213e; margin: 16px 0 8px; }}
  p {{ margin-bottom: 10px; text-align: justify; }}
  .exec-summary {{ background: #f0f4ff; padding: 40px 60px; }}
  .exec-summary h2 {{ color: #0f3460; }}
  .recommendations ol {{ padding-left: 20px; }}
  .recommendations li {{ margin-bottom: 12px; }}
  .source-tag {{ display: inline-block; background: #e8f4f8; color: #0f3460;
                  font-size: 8pt; padding: 2px 8px; border-radius: 12px;
                  margin-bottom: 12px; }}
  .footer {{ text-align: center; font-size: 8pt; color: #999;
             padding: 20px; border-top: 1px solid #eee; }}
</style>
</head>
<body>

<div class="cover">
  <div class="label">Confidential — Strategy Brief</div>
  <h1>{company}</h1>
  <div class="subtitle">Analysed Summary Report</div>
  <div class="meta">
    <div><strong>Industry:</strong> {industry}</div>
    <div><strong>Generated:</strong> {date}</div>
    <div style="margin-top:8px; font-style:italic; color:#ccc; font-size:9pt;">
      Prepared by AI Market Research Tool — For Consultant Use Only
    </div>
  </div>
</div>

<div class="exec-summary">
  <h2>Executive Summary</h2>
  {executive_summary_html}
</div>

{sections_html}

<div class="section recommendations">
  <h2>Strategic Recommendations</h2>
  {recommendations_html}
</div>

<div class="footer">
  Confidential — {company} Strategy Brief — Generated {date}
</div>

</body>
</html>
"""


def _text_to_html(text: str) -> str:
    """Convert plain text with newlines to HTML paragraphs."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in paragraphs)


def generate_pdf(brief: Dict) -> bytes:
    """Render the brief dict to a PDF and return bytes."""
    from weasyprint import HTML

    company = brief.get("company", "Company")
    industry = brief.get("industry", "")
    date = datetime.utcnow().strftime("%B %d, %Y")

    exec_html = _text_to_html(brief.get("executive_summary", ""))

    sections_html_parts = []
    for section in brief.get("sections", []):
        source_tag = ""
        if section.get("sources"):
            source_tag = f'<div class="source-tag">Source: {", ".join(section["sources"])}</div>'
        section_html = f"""
        <div class="section">
          <h2>{section['title']}</h2>
          {source_tag}
          {_text_to_html(section['content'])}
        </div>
        """
        sections_html_parts.append(section_html)

    sections_html = "\n".join(sections_html_parts)
    rec_html = _text_to_html(brief.get("strategic_recommendations", ""))

    html_content = HTML_TEMPLATE.format(
        company=company,
        industry=industry,
        date=date,
        executive_summary_html=exec_html,
        sections_html=sections_html,
        recommendations_html=rec_html,
    )

    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
