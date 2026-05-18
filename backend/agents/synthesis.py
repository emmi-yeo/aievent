"""
RAG synthesis using ChromaDB + Gemini to produce the Analysed Summary.
Each section is generated with focused context from the relevant document category.
"""
import asyncio
import json
import os
import re
from typing import List, Dict, AsyncGenerator

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from models.schemas import DOCUMENT_CATEGORIES, CATEGORY_LABELS

SECTION_MAP = {
    "financial_report":    ("Financial Health",    "Analyse the company's financial health, key metrics, revenue trends, profitability, and financial risks."),
    "business_plan":       ("Business Direction",   "Summarise the company's strategic direction, goals, growth plans, and key milestones."),
    "market_view":         ("Market Perspective",   "Describe how the company views its own market, positioning, and competitive landscape."),
    "fact_finding":        ("Key Findings",         "Extract the most important facts, data points, and insights from the fact-finding documents."),
    "value_proposition":   ("Value & Positioning",  "Clarify the company's value proposition, unique differentiators, and target customer segments."),
    "pricing_structure":   ("Revenue Model",        "Explain the pricing strategy, revenue streams, and how the business monetises its offering."),
    "market_research":     ("Market Landscape",     "Describe the broader market, industry trends, opportunities, and threats from market research."),
}


def _get_collection(engagement_id: str):
    from gcloud.chroma import get_collection
    return get_collection(engagement_id)


def _query_category(collection, category: str, query: str, n: int = 6) -> List[str]:
    """Retrieve top-n chunks for a specific category."""
    try:
        from gcloud.chroma import embed_query
        count = collection.count()
        if count == 0:
            return []
        results = collection.query(
            query_embeddings=[embed_query(query)],
            n_results=min(n, count),
            where={"category": category},
        )
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []


def _query_all(collection, query: str, n: int = 10) -> List[str]:
    """Retrieve top-n chunks across all categories."""
    try:
        from gcloud.chroma import embed_query
        count = collection.count()
        if count == 0:
            return []
        results = collection.query(
            query_embeddings=[embed_query(query)],
            n_results=min(n, count),
        )
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []


def _build_context(chunks: List[str]) -> str:
    return "\n\n---\n\n".join(chunks) if chunks else "No documents available for this section."


def _parse_retry_delay(exc: ResourceExhausted) -> int:
    """Extract the suggested retry delay from a 429 error message, default 30s."""
    match = re.search(r"retry[^\d]*(\d+)", str(exc), re.IGNORECASE)
    return int(match.group(1)) + 2 if match else 30


async def _generate_with_retry(model, prompt: str, max_retries: int = 5) -> str:
    """Call model.generate_content with automatic retry on 429 rate-limit errors."""
    for attempt in range(max_retries):
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
            return response.text.strip()
        except ResourceExhausted as exc:
            if attempt == max_retries - 1:
                raise
            wait = _parse_retry_delay(exc)
            await asyncio.sleep(wait)
    raise RuntimeError("Unreachable")


async def generate_analysed_summary(
    engagement_id: str,
    onboarding_answers: List[Dict],
    company: str,
    industry: str,
) -> AsyncGenerator[str, None]:
    """
    Streams the full Analysed Summary as JSON-line events.
    Each event: {"event": "section", "title": "...", "content": "...", "key": "..."}
    Final event: {"event": "done", "brief": {...}}
    """
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")

    collection = _get_collection(engagement_id)

    # Build onboarding context string
    onboarding_context = "\n".join(
        f"Q: {a['question']}\nA: {a['answer']}"
        for a in onboarding_answers
        if a.get("answer")
    ) or "No onboarding answers available."

    brief = {
        "engagement_id": engagement_id,
        "company": company,
        "industry": industry,
        "executive_summary": "",
        "sections": [],
        "strategic_recommendations": "",
    }

    # Generate each section
    for category, (title, instruction) in SECTION_MAP.items():
        chunks = _query_category(collection, category, instruction)
        context = _build_context(chunks)

        prompt = f"""You are a senior strategy consultant preparing a pre-meeting briefing document.

Company: {company}
Industry: {industry}

Client Onboarding Context:
{onboarding_context}

Relevant Documents ({CATEGORY_LABELS[category]}):
{context}

Task: {instruction}

Write a clear, concise section (3-5 paragraphs) for the consultant's briefing document. 
Use professional language suitable for a C-suite strategy meeting.
Focus on insights the consultant can act on.
Do not repeat the company name in every sentence."""

        section_content = await _generate_with_retry(model, prompt)

        section = {
            "key": category,
            "title": title,
            "content": section_content,
            "sources": [CATEGORY_LABELS[category]],
        }
        brief["sections"].append(section)

        yield json.dumps({"event": "section", "key": category,
                          "title": title, "content": section_content}) + "\n"

    # Executive Summary (uses all chunks)
    all_chunks = _query_all(collection, "business overview executive summary")
    exec_context = _build_context(all_chunks)

    exec_prompt = f"""You are a senior strategy consultant. 
Write an executive summary (1 page maximum) for a strategy meeting about:

Company: {company}
Industry: {industry}

Client Background:
{onboarding_context}

Document Highlights:
{exec_context}

The executive summary should cover:
- What the business does and its current position
- Key strengths and challenges
- The strategic opportunity or decision at hand
- Why this meeting matters

Write in a direct, consultant-ready style. No fluff."""

    exec_summary = await _generate_with_retry(model, exec_prompt)
    brief["executive_summary"] = exec_summary

    yield json.dumps({"event": "section", "key": "executive_summary",
                      "title": "Executive Summary", "content": exec_summary}) + "\n"

    # Strategic Recommendations
    sections_text = "\n\n".join(
        f"## {s['title']}\n{s['content']}" for s in brief["sections"]
    )
    rec_prompt = f"""Based on this complete analysis of {company}:

{sections_text}

Onboarding Context:
{onboarding_context}

Write 5-7 strategic recommendations for the consultant to use in the meeting.
Each recommendation should be:
- Specific and actionable
- Backed by evidence from the analysis
- Prioritised (most important first)
- Written as a numbered list with a bold headline and 2-3 sentence explanation

Focus on growth, risk mitigation, and competitive positioning."""

    recommendations = await _generate_with_retry(model, rec_prompt)
    brief["strategic_recommendations"] = recommendations

    yield json.dumps({"event": "section", "key": "strategic_recommendations",
                      "title": "Strategic Recommendations",
                      "content": recommendations}) + "\n"

    yield json.dumps({"event": "done", "brief": brief}) + "\n"
