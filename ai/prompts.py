"""
HFIP – LLM Prompts
All Groq prompt templates in one place for easy editing.
"""

from __future__ import annotations

# ─── System Prompt ───────────────────────────────────────────────────────────

EVALUATOR_SYSTEM_PROMPT = """You are an expert healthcare funding analyst specialising in AI and digital health projects.

Your task is to evaluate procurement notices and funding calls for strategic relevance to a healthcare AI research organisation.

You evaluate tenders on the following criteria:
1. Healthcare AI relevance – Does it involve AI/ML in a clinical or healthcare context?
2. Digital Health relevance – Does it involve digital health technologies (FHIR, EHR, DiGA, telehealth)?
3. Research / innovation value – Is this a research or innovation project vs. simple procurement?
4. Required expertise – What technical and domain skills are needed?
5. Proposal complexity – How much effort would a proposal require?
6. Consortium requirements – Does it require or favour a consortium?

Rules:
- Be concise and precise
- Return ONLY valid JSON with no markdown fences, explanations, or extra text
- Use English regardless of the tender's language
- If the tender is clearly irrelevant (construction, catering, facility management), set relevant=false and score=0
"""

# ─── User Prompt Template ────────────────────────────────────────────────────

EVALUATOR_USER_PROMPT_TEMPLATE = """Evaluate the following funding opportunity:

TITLE: {title}

SOURCE: {source}

ORGANIZATION: {organization}

COUNTRY: {country}

DEADLINE: {deadline}

DESCRIPTION:
{description}

{tavily_context_section}

Return a JSON object with exactly these fields:
{{
  "relevant": <boolean>,
  "score": <integer 0-100>,
  "category": <string, one of: "Healthcare AI", "Digital Health", "Medical Imaging", "Health Data & Interoperability", "Biomedical Research", "Health Informatics", "Other Health", "Not Relevant">,
  "summary": <string, 2-3 sentence summary in English>,
  "required_skills": <array of strings, max 6 skills>,
  "proposal_effort": <string, one of: "Low", "Medium", "High">,
  "consortium_required": <boolean>
}}"""

# ─── Tavily Context Section ───────────────────────────────────────────────────

TAVILY_CONTEXT_TEMPLATE = """ADDITIONAL RESEARCH CONTEXT (from web search):
{context}
"""


def build_user_prompt(
    title: str,
    source: str,
    organization: str,
    country: str,
    deadline: str,
    description: str,
    tavily_context: str = "",
) -> str:
    """Render the evaluator user prompt with tender data."""
    tavily_section = ""
    if tavily_context:
        tavily_section = TAVILY_CONTEXT_TEMPLATE.format(context=tavily_context)

    return EVALUATOR_USER_PROMPT_TEMPLATE.format(
        title=title,
        source=source,
        organization=organization or "Unknown",
        country=country or "Unknown",
        deadline=deadline or "Not specified",
        description=description[:3000] if description else "Not provided",
        tavily_context_section=tavily_section,
    )
