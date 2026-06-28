from __future__ import annotations

import dataclasses
import json
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete

from app.models.database import Report
from app.services.github import GitHubData


def build_report(
    data: GitHubData,
    score_data: dict,
    ai_data: dict,
    final_score: dict | None = None,
) -> dict:
    """Assemble the complete JSON report returned to clients and stored in SQLite."""
    repo = data.repo
    return {
        "repo": {
            "full_name":      repo.full_name,
            "owner":          repo.owner,
            "name":           repo.name,
            "description":    repo.description,
            "url":            repo.url,
            "homepage":       repo.homepage,
            "stars":          repo.stars,
            "forks":          repo.forks,
            "watchers":       repo.watchers,
            "open_issues":    repo.open_issues,
            "language":       repo.language,
            "license":        repo.license,
            "created_at":     repo.created_at,
            "updated_at":     repo.updated_at,
            "size_kb":        repo.size_kb,
            "topics":         repo.topics,
            "default_branch": repo.default_branch,
            "is_fork":        repo.is_fork,
            "is_archived":    repo.is_archived,
            "visibility":     repo.visibility,
        },
        "languages":     data.languages,
        "contributors":  data.contributors,
        "file_tree":     data.file_tree,
        "file_presence": dataclasses.asdict(data.file_presence),
        "source_files": [
            {
                "path":        sf.path,
                "language":    sf.language,
                "size_bytes":  sf.size_bytes,
            }
            for sf in data.source_files
        ],
        "score":       score_data,
        "final_score": final_score,   # calculate_final_score output; may be None
        "ai":          ai_data,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


async def save_report(
    db: AsyncSession,
    repo_url: str,
    repo_name: str,
    score: float,
    grade: str,
    primary_language: str,
    report: dict,
) -> Report:
    record = Report(
        repo_url=repo_url,
        repo_name=repo_name,
        score=score,
        grade=grade,
        primary_language=primary_language,
        report_data=json.dumps(report),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_history(db: AsyncSession, limit: int = 20) -> list[dict]:
    result = await db.execute(
        select(Report).order_by(desc(Report.created_at)).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id":               r.id,
            "repo_url":         r.repo_url,
            "repo_name":        r.repo_name,
            "score":            r.score,
            "grade":            r.grade,
            "primary_language": r.primary_language,
            "created_at":       r.created_at.isoformat() + "Z",
        }
        for r in rows
    ]


async def get_report_by_id(db: AsyncSession, report_id: int) -> dict | None:
    result = await db.execute(select(Report).where(Report.id == report_id))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    payload = row.report_data_as_dict()
    payload["id"]         = row.id
    payload["created_at"] = row.created_at.isoformat() + "Z"
    return payload


async def delete_report(db: AsyncSession, report_id: int) -> bool:
    """Return True if a row was deleted, False if it didn't exist."""
    result = await db.execute(
        delete(Report).where(Report.id == report_id)
    )
    await db.commit()
    return result.rowcount > 0
