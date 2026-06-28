"""
FastAPI router for AI GitHub Project Reviewer.

Endpoints
---------
POST   /api/review              Run full review pipeline
GET    /api/history             Last 20 reviews (summary)
GET    /api/report/{id}         Full report by ID
DELETE /api/history/{id}        Delete a report
GET    /api/health              Health-check (also at app root via main.py)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.pdf_report import generate_pdf_report
from app.services.github import (
    GitHubError,
    RateLimitError,
    RepoNotFoundError,
    RepoPrivateError,
    fetch_all,
    validate_github_url,
)
from app.services import analyzer, gemini, report as report_svc
from app.utils.helpers import calculate_final_score
from app.utils.validators import parse_github_url as _parse_shorthand

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["review"])

# Maximum wall-clock time for the full review pipeline (seconds).
_PIPELINE_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    repo_url: str = Field(..., examples=["https://github.com/owner/repo"])

    @field_validator("repo_url")
    @classmethod
    def _normalise(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("http"):
            parsed = _parse_shorthand(v)
            if parsed:
                v = f"https://github.com/{parsed[0]}/{parsed[1]}"
        return v


class HistoryItem(BaseModel):
    id:               int
    repo_url:         str
    repo_name:        str
    score:            float
    grade:            str
    primary_language: str
    created_at:       str


class DeleteResponse(BaseModel):
    deleted: bool
    id:      int


class HealthResponse(BaseModel):
    status:    str
    timestamp: str
    version:   str = "1.0.0"


# ---------------------------------------------------------------------------
# Error response helpers
# ---------------------------------------------------------------------------

def _err(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


# ---------------------------------------------------------------------------
# Core pipeline (extracted so the timeout wrapper stays clean)
# ---------------------------------------------------------------------------

async def _run_pipeline(owner: str, repo_name: str, db: AsyncSession) -> dict:
    # ── 1. Fetch all GitHub data ─────────────────────────────────────────────
    try:
        github_data = await fetch_all(owner, repo_name)
    except RepoNotFoundError:
        raise _err(
            status.HTTP_404_NOT_FOUND,
            f"Repository '{owner}/{repo_name}' was not found. "
            "Check the spelling or ensure it is a public repository.",
        )
    except RepoPrivateError as exc:
        raise _err(status.HTTP_403_FORBIDDEN, str(exc))
    except RateLimitError as exc:
        raise _err(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))
    except GitHubError as exc:
        log.exception("GitHub API error for %s/%s", owner, repo_name)
        raise _err(status.HTTP_502_BAD_GATEWAY, f"GitHub API error: {exc}")

    # ── 2. Static analyses (CPU-bound, run synchronously) ────────────────────
    code_analysis      = analyzer.analyze_code(github_data)
    readme_analysis    = analyzer.analyze_readme(github_data.readme or "")
    structure_analysis = analyzer.analyze_structure(github_data.file_tree)

    # Partial score_data from analyzer (used as sub-scores for dimensions
    # that the old system cares about).
    score_data = analyzer.compute_score(
        github_data, code_analysis, readme_analysis, structure_analysis
    )

    # ── 3. AI review (network call, may degrade gracefully) ──────────────────
    repo_payload = {
        "full_name":   github_data.repo.full_name,
        "description": github_data.repo.description,
        "language":    github_data.repo.language,
        "stars":       github_data.repo.stars,
        "forks":       github_data.repo.forks,
        "open_issues": github_data.repo.open_issues,
        "size_kb":     github_data.repo.size_kb,
        "topics":      github_data.repo.topics,
        "license":     github_data.repo.license,
        "created_at":  github_data.repo.created_at,
        "updated_at":  github_data.repo.updated_at,
        "readme":      github_data.readme or "",
    }

    # code_analysis sub-dict for Gemini prompt
    ca_payload = {
        "overall_score":  code_analysis.overall_score,
        "files_analyzed": code_analysis.total_files_analyzed,
        "lines_analyzed": code_analysis.total_lines_analyzed,
        "top_issues": [
            {"severity": i.severity, "message": i.message, "count": i.count}
            for i in code_analysis.top_issues
        ],
        "by_language": [
            {
                "language":   s.language,
                "file_count": s.file_count,
                "avg_score":  s.avg_score,
                "errors":     s.error_count,
                "warnings":   s.warning_count,
            }
            for s in code_analysis.language_summaries
        ],
        "languages": [s.language for s in code_analysis.language_summaries],
        # Include per-file issue lists so calculate_final_score can derive
        # the security score.
        "files": [
            {
                "filename": f.filename,
                "issues": [
                    {"severity": i.severity, "message": i.message, "count": i.count}
                    for i in f.issues
                ],
            }
            for f in code_analysis.files
        ],
    }

    analysis_payload = {
        "overall_score":      score_data["total"],
        "readme_analysis":    readme_analysis,
        "structure_analysis": structure_analysis,
        "code_analysis":      ca_payload,
    }

    ai_data = await gemini.generate_ai_review(repo_payload, analysis_payload)

    # ── 4. Final weighted score ───────────────────────────────────────────────
    final_score = calculate_final_score({
        "structure_analysis": structure_analysis,
        "readme_analysis":    readme_analysis,
        "code_analysis":      ca_payload,
        "ai_data":            ai_data,
    })

    # ── 5. Build and persist report ──────────────────────────────────────────
    full_report = report_svc.build_report(
        github_data, score_data, ai_data, final_score
    )

    repo_url_canonical = f"https://github.com/{owner}/{repo_name}"
    record = await report_svc.save_report(
        db,
        repo_url=repo_url_canonical,
        repo_name=f"{owner}/{repo_name}",
        score=final_score["total_score"],
        grade=final_score["grade"],
        primary_language=github_data.repo.language or "",
        report=full_report,
    )

    # Attach DB id so the frontend can call /api/report/{id}/download
    full_report["id"] = record.id

    return full_report


# ---------------------------------------------------------------------------
# POST /api/review
# ---------------------------------------------------------------------------

@router.post(
    "/review",
    summary="Run a full AI review of a GitHub repository",
    response_description="Complete review report",
    status_code=status.HTTP_200_OK,
)
async def review_repo(body: ReviewRequest, db: AsyncSession = Depends(get_db)):
    """
    Accepts a GitHub URL or `owner/repo` shorthand.

    Runs the complete pipeline:
    1. Validate URL format
    2. Fetch repository data from the GitHub API
    3. Analyse project structure, README quality, and static code quality
    4. Request an AI review from Gemini (degrades gracefully on failure)
    5. Compute the weighted final score
    6. Persist the report to SQLite
    7. Return the full JSON report
    """
    parsed = validate_github_url(body.repo_url)
    if not parsed:
        raise _err(
            status.HTTP_400_BAD_REQUEST,
            "Invalid GitHub repository URL. "
            "Accepted formats: https://github.com/owner/repo  or  owner/repo",
        )

    owner, repo_name = parsed

    try:
        result = await asyncio.wait_for(
            _run_pipeline(owner, repo_name, db),
            timeout=_PIPELINE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise _err(
            status.HTTP_504_GATEWAY_TIMEOUT,
            f"Review timed out after {_PIPELINE_TIMEOUT}s. "
            "The repository may be very large. Please try again.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unexpected error reviewing %s/%s", owner, repo_name)
        raise _err(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Unexpected server error: {type(exc).__name__}: {exc}",
        )

    return result


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=list[HistoryItem],
    summary="Return the last 20 repository reviews",
)
async def get_history(db: AsyncSession = Depends(get_db)):
    return await report_svc.get_history(db)


# ---------------------------------------------------------------------------
# GET /api/report/{id}
# ---------------------------------------------------------------------------

@router.get(
    "/report/{report_id}",
    summary="Return the full saved report for the given ID",
)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    data = await report_svc.get_report_by_id(db, report_id)
    if data is None:
        raise _err(
            status.HTTP_404_NOT_FOUND,
            f"No report with id={report_id} exists.",
        )
    return data


# ---------------------------------------------------------------------------
# GET /api/report/{id}/download
# ---------------------------------------------------------------------------

@router.get(
    "/report/{report_id}/download",
    summary="Download the full report as a PDF file",
    response_class=Response,
)
async def download_report_pdf(report_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetches the saved report by ID, generates a multi-page PDF with ReportLab,
    and returns it as an attachment download.
    """
    data = await report_svc.get_report_by_id(db, report_id)
    if data is None:
        raise _err(
            status.HTTP_404_NOT_FOUND,
            f"No report with id={report_id} exists.",
        )

    try:
        pdf_bytes = generate_pdf_report(data)
    except Exception as exc:
        log.exception("PDF generation failed for report id=%s", report_id)
        raise _err(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"PDF generation failed: {type(exc).__name__}: {exc}",
        )

    repo      = data.get("repo_info") or data.get("repo") or {}
    repo_name = repo.get("full_name") or repo.get("name") or f"report_{report_id}"
    safe_name = repo_name.replace("/", "_").replace(" ", "_")
    filename  = f"{safe_name}_review.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# DELETE /api/history/{id}
# ---------------------------------------------------------------------------

@router.delete(
    "/history/{report_id}",
    response_model=DeleteResponse,
    summary="Delete a saved report",
)
async def delete_report(report_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await report_svc.delete_report(db, report_id)
    if not deleted:
        raise _err(
            status.HTTP_404_NOT_FOUND,
            f"No report with id={report_id} exists.",
        )
    return DeleteResponse(deleted=True, id=report_id)


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health():
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
