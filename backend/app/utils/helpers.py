"""
Utility helpers for AI GitHub Project Reviewer.

Public scoring API
------------------
  calculate_final_score(analysis_results: dict) -> dict

  analysis_results shape:
    {
      "structure_analysis": {"score": float, ...},
      "readme_analysis":    {"score": float, ...},
      "code_analysis": {
          "overall_score": float,
          "files": [{"issues": [{"severity": str, "message": str, "count": int}]}],
      },
      "ai_data": {"ai_quality_score": int, "ai_available": bool, ...},
    }
"""
from __future__ import annotations

from datetime import datetime


# ---------------------------------------------------------------------------
# Primitive utilities (unchanged from original)
# ---------------------------------------------------------------------------

def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def score_label(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Average"
    return "Needs Work"


def bytes_to_kb(b: int) -> float:
    return round(b / 1024, 2)


# ---------------------------------------------------------------------------
# Security-issue keyword matching
# ---------------------------------------------------------------------------

# Substrings that flag an issue message as security-related.
# These match the exact message strings produced by the static analyzers.
_SECURITY_KEYWORDS: frozenset[str] = frozenset([
    "hardcoded secret",        # Python: password/api_key literal
    "hardcoded api",           # JS/TS: apiKey literal
    "sql injection",           # PHP / SQL dynamic query
    "eval()",                  # PHP eval
    "unsafe gets",             # C: gets() buffer overflow
    "injection risk",          # SQL concat pattern
    "sri integrity",           # HTML: external script without integrity
    "deprecated mysql",        # PHP: mysql_* functions
    "error suppression",       # PHP: @ operator hides errors
    "unsanitized",             # PHP: $_GET/$_POST in query
])


def _is_security_issue(message: str) -> bool:
    low = message.lower()
    return any(kw in low for kw in _SECURITY_KEYWORDS)


def _compute_security_score(code_analysis: dict) -> float:
    """
    Derive a 0-100 security score from per-file issue lists.

    Deduction schedule (capped per issue at count=5 to avoid absurd numbers):
      error   → 10 pts × min(count, 5)
      warning → 4  pts × min(count, 5)

    Returns 70 when no source files were analysed (neutral / unknown).
    """
    files = code_analysis.get("files", [])
    if not files:
        return 70.0

    deduction = 0.0
    for file_result in files:
        for issue in file_result.get("issues", []):
            if not _is_security_issue(issue.get("message", "")):
                continue
            count = min(int(issue.get("count", 1)), 5)
            sev   = issue.get("severity", "info")
            if sev == "error":
                deduction += 10 * count
            elif sev == "warning":
                deduction += 4 * count

    return round(clamp(100.0 - deduction, 0.0, 100.0), 1)


# ---------------------------------------------------------------------------
# Grade / badge tables
# ---------------------------------------------------------------------------

# (minimum_score_inclusive, grade_string)
_GRADE_TABLE: list[tuple[int, str]] = [
    (90, "A+"),
    (80, "A"),
    (70, "B+"),
    (60, "B"),
    (50, "C+"),
    (40, "C"),
    (30, "D"),
    (0,  "F"),
]

# (minimum_score_inclusive, badge_string)
_BADGE_TABLE: list[tuple[int, str]] = [
    (85, "🏆 Excellent"),
    (70, "👍 Good"),
    (50, "📈 Average"),
    (30, "⚠️ Needs Work"),
    (0,  "🔴 Poor"),
]

# Scoring weights — must sum to 1.0
_WEIGHTS: dict[str, float] = {
    "structure":     0.20,
    "documentation": 0.20,
    "code_quality":  0.30,
    "security":      0.15,
    "ai_assessment": 0.15,
}


def _grade(score: float) -> str:
    for threshold, label in _GRADE_TABLE:
        if score >= threshold:
            return label
    return "F"


def _badge(score: float) -> str:
    for threshold, label in _BADGE_TABLE:
        if score >= threshold:
            return label
    return "🔴 Poor"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def calculate_final_score(analysis_results: dict) -> dict:
    """
    Compute the canonical 5-dimension final score for a repository review.

    Dimensions and weights
    ----------------------
    structure      20%  — project structure score
    documentation  20%  — README analysis score
    code_quality   30%  — static code analysis overall score
    security       15%  — derived from security-related issues in code files
    ai_assessment  15%  — Gemini ai_quality_score (50 when AI unavailable)

    Returns
    -------
    {
      "total_score": float,          # 0-100, one decimal place
      "grade":  "A+"|"A"|…|"F",
      "badge":  "🏆 Excellent"|…,
      "breakdown": {
          "<dimension>": {
              "score":    float,     # raw 0-100 for this dimension
              "weight":   int,       # percentage (20, 30, 15, …)
              "weighted": float,     # score × weight/100
          },
          …
      }
    }
    """
    structure_analysis  = analysis_results.get("structure_analysis") or {}
    readme_analysis     = analysis_results.get("readme_analysis")    or {}
    code_analysis       = analysis_results.get("code_analysis")      or {}
    ai_data             = analysis_results.get("ai_data")            or {}

    raw: dict[str, float] = {
        "structure":     clamp(float(structure_analysis.get("score",    0)), 0, 100),
        "documentation": clamp(float(readme_analysis.get("score",       0)), 0, 100),
        "code_quality":  clamp(float(code_analysis.get("overall_score", 0)), 0, 100),
        "security":      _compute_security_score(code_analysis),
        # Fall back to 50 when AI was unavailable so the grade isn't unfairly penalised.
        "ai_assessment": clamp(float(ai_data.get("ai_quality_score", 50)), 0, 100),
    }

    total = clamp(
        sum(raw[k] * _WEIGHTS[k] for k in _WEIGHTS),
        0, 100
    )
    total = round(total, 1)

    breakdown = {
        k: {
            "score":    round(raw[k], 1),
            "weight":   round(_WEIGHTS[k] * 100),
            "weighted": round(raw[k] * _WEIGHTS[k], 1),
        }
        for k in _WEIGHTS
    }

    return {
        "total_score": total,
        "grade":       _grade(total),
        "badge":       _badge(total),
        "breakdown":   breakdown,
    }
