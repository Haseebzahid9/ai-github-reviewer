"""
Gemini AI integration service for AI GitHub Project Reviewer.
Uses the google-genai SDK (replaces deprecated google-generativeai).

Public API
----------
  generate_ai_review(repo_data: dict, analysis_data: dict) -> dict

  repo_data keys expected:
    full_name, description, language, stars, forks, open_issues,
    size_kb, topics, license, created_at, updated_at, readme (str)

  analysis_data keys expected:
    overall_score, readme_analysis (dict), structure_analysis (dict),
    code_analysis (dict with overall_score, files_analyzed,
                   lines_analyzed, top_issues, by_language, languages)

The returned dict always contains every key listed in _REQUIRED_FIELDS,
plus "ai_available": True|False so callers can distinguish real AI output
from the fallback.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

_MODEL_ID = "gemini-1.5-flash"

_GENERATE_CONFIG = types.GenerateContentConfig(
    temperature=0.3,       # low temperature → more deterministic JSON
    top_p=0.85,
    max_output_tokens=2048,
)

# Lazy-initialised client — created once on first real API call.
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    return _client


# ---------------------------------------------------------------------------
# Exact response schema
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS: dict[str, Any] = {
    "project_overview":              "",
    "tech_stack_assessment":         "",
    "strengths":                     [],
    "weaknesses":                    [],
    "security_suggestions":          [],
    "performance_suggestions":       [],
    "maintainability_suggestions":   [],
    "best_practices":                [],
    "beginner_friendly_score":       5,
    "production_readiness_score":    5,
    "documentation_quality":         "fair",
    "overall_review":                "",
    "recommended_next_steps":        [],
    "similar_projects_to_study":     [],
    "ai_quality_score":              50,
}

_DOC_QUALITY_VALUES = {"poor", "fair", "good", "excellent"}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(repo_data: dict, analysis_data: dict) -> str:
    repo    = repo_data
    code    = analysis_data.get("code_analysis", {})
    readme  = analysis_data.get("readme_analysis", {})
    struct  = analysis_data.get("structure_analysis", {})
    overall = analysis_data.get("overall_score", 0)

    # --- Section 1: Repository metadata ---
    topics_str  = ", ".join(repo.get("topics", [])) or "none"
    license_str = repo.get("license") or "not specified"
    meta_section = f"""\
=== REPOSITORY METADATA ===
Name        : {repo.get('full_name', 'unknown')}
Description : {repo.get('description') or 'No description provided'}
Language    : {repo.get('language') or 'Unknown'}
Stars       : {repo.get('stars', 0):,}
Forks       : {repo.get('forks', 0):,}
Open Issues : {repo.get('open_issues', 0):,}
Size        : {repo.get('size_kb', 0):,} KB
Topics      : {topics_str}
License     : {license_str}
Created     : {repo.get('created_at', 'unknown')[:10]}
Last update : {repo.get('updated_at', 'unknown')[:10]}
Overall score (0-100): {overall}"""

    # --- Section 2: README summary (first 2 000 chars) ---
    readme_content = (repo.get("readme") or "").strip()
    readme_preview = readme_content[:2000]
    if len(readme_content) > 2000:
        readme_preview += "\n… [truncated]"
    readme_section = f"""\
=== README CONTENT (first 2 000 chars) ===
{readme_preview if readme_preview else '(no README found)'}
README quality score : {readme.get('score', 0)}/100
Sections found       : {', '.join(readme.get('sections_found', [])) or 'none'}
Missing sections     : {', '.join(readme.get('sections_missing', [])) or 'none'}"""

    # --- Section 3: Project structure ---
    found_items   = list((struct.get("found") or {}).keys())
    missing_items = list((struct.get("missing") or {}).keys())
    struct_section = f"""\
=== PROJECT STRUCTURE ===
Structure score  : {struct.get('score', 0)}/100
Present          : {', '.join(found_items) or 'none'}
Missing          : {', '.join(missing_items) or 'none'}"""

    # --- Section 4: Static analysis ---
    languages = [s.get("language", "") for s in code.get("by_language", [])]
    top_issues = code.get("top_issues", [])
    top_issues_str = "; ".join(
        f"{i.get('severity','?').upper()}: {i.get('message','')} (×{i.get('count',1)})"
        for i in top_issues
    ) or "none detected"

    by_lang_rows = "\n".join(
        f"  {s.get('language','?'):15} files={s.get('file_count',0)}  "
        f"avg_score={s.get('avg_score',0)}/100  "
        f"errors={s.get('errors',0)}  warnings={s.get('warnings',0)}"
        for s in code.get("by_language", [])
    )

    code_section = f"""\
=== STATIC CODE ANALYSIS ===
Code quality score : {code.get('overall_score', 0)}/100
Files analysed     : {code.get('files_analyzed', 0)}
Total lines        : {code.get('lines_analyzed', 0):,}
Languages detected : {', '.join(languages) or 'none'}
Top issues         : {top_issues_str}
Per-language breakdown:
{by_lang_rows or '  (no source files fetched)'}"""

    # --- Section 5: JSON schema instructions ---
    schema_section = """\
=== YOUR TASK ===
Based solely on the data above, produce a JSON object with EXACTLY these keys.
Follow all constraints strictly — your response will be machine-parsed.

{
  "project_overview": "<2-3 sentence summary of what this project does and its purpose>",
  "tech_stack_assessment": "<1-2 sentence assessment of the chosen technologies and their suitability>",
  "strengths": [
    "<specific strength 1 grounded in the data>",
    "<specific strength 2>",
    "<specific strength 3>",
    "<optional 4th>",
    "<optional 5th>"
  ],
  "weaknesses": [
    "<specific weakness or gap 1 grounded in the data>",
    "<specific weakness 2>",
    "<specific weakness 3>",
    "<optional 4th>",
    "<optional 5th>"
  ],
  "security_suggestions": [
    "<specific, actionable security improvement 1>",
    "<security improvement 2>",
    "<optional 3rd>",
    "<optional 4th>"
  ],
  "performance_suggestions": [
    "<specific performance improvement 1>",
    "<performance improvement 2>",
    "<optional 3rd>",
    "<optional 4th>"
  ],
  "maintainability_suggestions": [
    "<specific maintainability improvement 1>",
    "<maintainability improvement 2>",
    "<optional 3rd>",
    "<optional 4th>"
  ],
  "best_practices": [
    "<best practice to adopt 1>",
    "<best practice 2>",
    "<best practice 3>",
    "<optional 4th>",
    "<optional 5th>"
  ],
  "beginner_friendly_score": <integer 1-10>,
  "production_readiness_score": <integer 1-10>,
  "documentation_quality": "<one of: poor | fair | good | excellent>",
  "overall_review": "<3-4 paragraph detailed review covering code quality, architecture, docs, and community health>",
  "recommended_next_steps": [
    "<highest-priority actionable next step>",
    "<next step 2>",
    "<next step 3>",
    "<optional 4th>",
    "<optional 5th>"
  ],
  "similar_projects_to_study": [
    "<well-known open-source project name + one sentence on what to learn from it>",
    "<similar project 2>",
    "<similar project 3>"
  ],
  "ai_quality_score": <integer 0-100, your overall assessment of this project>
}

RULES:
- Output ONLY the JSON object — no markdown fences, no explanation text outside the JSON.
- Every list must have at least 2 items (use the optional slots if the data supports it).
- beginner_friendly_score and production_readiness_score MUST be integers between 1 and 10.
- ai_quality_score MUST be an integer between 0 and 100.
- documentation_quality MUST be exactly one of: poor, fair, good, excellent.
- Base all assessments on the provided data, not general assumptions."""

    return "\n\n".join([meta_section, readme_section, struct_section, code_section, schema_section])


# ---------------------------------------------------------------------------
# JSON extraction & validation
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict | None:
    """
    Try progressively looser extractions:
    1. Entire text is valid JSON.
    2. Strip leading/trailing markdown fences, then parse.
    3. Extract first {...} block with a regex (handles extra prose before/after).
    """
    # 1. Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences
    stripped = re.sub(
        r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE
    ).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 3. Regex: grab the first top-level {...} block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _coerce_int_range(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        v = int(value)
        return max(lo, min(hi, v))
    except (TypeError, ValueError):
        return default


def _coerce_list(value: Any, min_items: int = 1) -> list:
    if isinstance(value, list) and len(value) >= min_items:
        return [str(item) for item in value if item]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _validate_and_fill(data: dict) -> dict:
    """
    Ensure every required key is present and the right type.
    Invalid / missing values are replaced with safe defaults so the frontend
    never has to handle absent fields.
    """
    out: dict = {}

    # String fields
    for key in ("project_overview", "tech_stack_assessment", "overall_review"):
        v = data.get(key, "")
        out[key] = str(v).strip() if isinstance(v, str) and v.strip() else _REQUIRED_FIELDS[key]

    # List-of-string fields
    list_fields = (
        "strengths", "weaknesses", "security_suggestions",
        "performance_suggestions", "maintainability_suggestions",
        "best_practices", "recommended_next_steps", "similar_projects_to_study",
    )
    for key in list_fields:
        out[key] = _coerce_list(data.get(key), min_items=1) or list(_REQUIRED_FIELDS[key])

    # Integer score fields
    out["beginner_friendly_score"]   = _coerce_int_range(data.get("beginner_friendly_score"),   1, 10, 5)
    out["production_readiness_score"]= _coerce_int_range(data.get("production_readiness_score"), 1, 10, 5)
    out["ai_quality_score"]          = _coerce_int_range(data.get("ai_quality_score"),           0, 100, 50)

    # Enum field
    dq = str(data.get("documentation_quality", "")).lower().strip()
    out["documentation_quality"] = dq if dq in _DOC_QUALITY_VALUES else "fair"

    return out


# ---------------------------------------------------------------------------
# Fallback response (no API key, or all retries exhausted)
# ---------------------------------------------------------------------------

def _fallback_response(repo_data: dict, reason: str) -> dict:
    name  = repo_data.get("full_name", "this repository")
    lang  = repo_data.get("language") or "unknown"
    stars = repo_data.get("stars", 0)
    desc  = repo_data.get("description") or "No description provided."

    return {
        "ai_available": False,
        "fallback_reason": reason,
        "project_overview": (
            f"{name} is a {lang} project on GitHub. {desc}"
        ),
        "tech_stack_assessment": (
            f"Primary language is {lang}. Add a GEMINI_API_KEY to get a full technology assessment."
        ),
        "strengths": [
            "Repository is publicly accessible on GitHub",
            f"Has {stars:,} stars indicating community interest" if stars else
            "Version control history is tracked with Git",
        ],
        "weaknesses": [
            "Unable to perform AI-powered analysis without GEMINI_API_KEY",
            "Manual review required to identify specific weaknesses",
        ],
        "security_suggestions": [
            "Audit dependencies for known CVEs using a tool like Dependabot or Snyk",
            "Ensure no secrets are committed; use .env.example for environment variable documentation",
        ],
        "performance_suggestions": [
            "Profile the application before optimising",
            "Add caching for expensive or repeated operations",
        ],
        "maintainability_suggestions": [
            "Enforce a consistent code style with a linter/formatter",
            "Add automated tests to prevent regressions",
        ],
        "best_practices": [
            "Add CI/CD pipeline for automated testing and deployment",
            "Pin dependency versions to reproducible builds",
            "Write meaningful commit messages following Conventional Commits",
        ],
        "beginner_friendly_score":    5,
        "production_readiness_score": 5,
        "documentation_quality":      "fair",
        "overall_review": (
            f"{name} could not be fully analysed because the Gemini API key is not configured. "
            "Set GEMINI_API_KEY in the backend .env file to enable AI-powered code review.\n\n"
            "The static analysis and project structure scores above are still accurate — "
            "only the AI narrative and qualitative assessments require Gemini."
        ),
        "recommended_next_steps": [
            "Set GEMINI_API_KEY in backend/.env to enable full AI review",
            "Review the static analysis results for concrete code quality issues",
            "Check the project structure score for missing best-practice files",
        ],
        "similar_projects_to_study": [
            "Search GitHub for well-starred projects in the same language for inspiration",
        ],
        "ai_quality_score": 50,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_ai_review(repo_data: dict, analysis_data: dict) -> dict:
    """
    Call Gemini to produce a structured review of the repository.

    Parameters
    ----------
    repo_data       Repository metadata including the raw readme string.
    analysis_data   Pre-computed scores from analyzer.py (code, readme, structure).

    Returns
    -------
    dict containing all _REQUIRED_FIELDS keys plus "ai_available": True|False.
    Never raises — failures return the fallback response.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        log.info("GEMINI_API_KEY not set — returning fallback response")
        return _fallback_response(repo_data, "GEMINI_API_KEY not configured")

    prompt = _build_prompt(repo_data, analysis_data)
    last_error = ""

    client = _get_client()

    for attempt in range(1, 3):          # 2 attempts, 1-indexed for readable logs
        try:
            log.debug("Gemini attempt %d/2 for %s", attempt, repo_data.get("full_name"))
            response = await client.aio.models.generate_content(
                model=_MODEL_ID,
                contents=prompt,
                config=_GENERATE_CONFIG,
            )
            raw_text = response.text

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            log.warning("Gemini attempt %d/2 failed: %s", attempt, last_error)
            if attempt < 2:
                await asyncio.sleep(2)
            continue

        parsed = _extract_json(raw_text)
        if parsed is None:
            last_error = "Response did not contain parseable JSON"
            log.warning("Gemini attempt %d/2: %s — raw=%r", attempt, last_error, raw_text[:200])
            if attempt < 2:
                await asyncio.sleep(2)
            continue

        validated = _validate_and_fill(parsed)
        validated["ai_available"] = True
        log.info(
            "Gemini review generated for %s (ai_quality_score=%s)",
            repo_data.get("full_name"), validated.get("ai_quality_score"),
        )
        return validated

    # All attempts failed
    log.error("All Gemini attempts failed for %s: %s", repo_data.get("full_name"), last_error)
    result = _fallback_response(repo_data, f"Gemini API error after 2 attempts: {last_error}")
    result["error_detail"] = last_error
    return result


# ---------------------------------------------------------------------------
# Legacy shim — keeps any code still calling generate_recommendations working
# ---------------------------------------------------------------------------

async def generate_recommendations(repo_summary: dict) -> dict:
    """Compatibility wrapper around generate_ai_review for the old flat-dict call shape."""
    repo_data = {
        "full_name":    repo_summary.get("full_name", ""),
        "description":  repo_summary.get("description", ""),
        "language":     repo_summary.get("language", ""),
        "stars":        repo_summary.get("stargazers_count", 0),
        "forks":        repo_summary.get("forks_count", 0),
        "open_issues":  repo_summary.get("open_issues_count", 0),
        "size_kb":      repo_summary.get("size_kb", 0),
        "topics":       repo_summary.get("topics", []),
        "license":      repo_summary.get("license", ""),
        "created_at":   repo_summary.get("created_at", ""),
        "updated_at":   repo_summary.get("updated_at", ""),
        "readme":       repo_summary.get("readme", ""),
    }
    analysis_data = {
        "overall_score": repo_summary.get("score", 0),
        "code_analysis": {
            "overall_score":  repo_summary.get("code_quality_score", 0),
            "files_analyzed": repo_summary.get("files_analyzed", 0),
            "lines_analyzed": 0,
            "top_issues":     [],
            "by_language":    [],
            "languages":      [],
        },
        "readme_analysis": {
            "score":            repo_summary.get("readme_score", 0),
            "sections_found":   [],
            "sections_missing": repo_summary.get("readme_missing_sections", "").split(", "),
        },
        "structure_analysis": {
            "score":   repo_summary.get("structure_score", 0),
            "found":   {},
            "missing": {k: k for k in repo_summary.get("structure_missing", "").split(", ") if k},
        },
    }
    return await generate_ai_review(repo_data, analysis_data)
