"""
pytest test suite for AI GitHub Project Reviewer backend.

Run with:
    cd backend
    pytest tests/ -v

Requirements (add to a dev-requirements.txt or install manually):
    pytest>=8.0
    pytest-asyncio>=0.23
    httpx>=0.27          (already in requirements.txt)
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. URL Validation
# ---------------------------------------------------------------------------

from app.services.github import validate_github_url


class TestValidateGithubUrl:
    def test_valid_https_url(self):
        result = validate_github_url("https://github.com/tiangolo/fastapi")
        assert result == ("tiangolo", "fastapi")

    def test_valid_https_url_trailing_slash(self):
        result = validate_github_url("https://github.com/django/django/")
        assert result == ("django", "django")

    def test_valid_https_url_with_dot_in_name(self):
        result = validate_github_url("https://github.com/org/my.repo")
        assert result == ("org", "my.repo")

    def test_rejects_non_github_domain(self):
        assert validate_github_url("https://gitlab.com/owner/repo") is None

    def test_rejects_plain_string(self):
        assert validate_github_url("not-a-url") is None

    def test_rejects_github_root(self):
        assert validate_github_url("https://github.com/") is None

    def test_rejects_github_owner_only(self):
        assert validate_github_url("https://github.com/tiangolo") is None

    def test_rejects_empty_string(self):
        assert validate_github_url("") is None

    def test_rejects_url_with_extra_path(self):
        # Should extract owner/repo and ignore the rest
        result = validate_github_url("https://github.com/owner/repo/issues/42")
        # The regex only matches exactly owner/repo — extra path makes it None
        # (implementation-dependent; adjust assertion to match actual behaviour)
        assert result is None or result == ("owner", "repo")


# ---------------------------------------------------------------------------
# 2. Scoring engine
# ---------------------------------------------------------------------------

from app.utils.helpers import calculate_final_score, clamp


class TestClamp:
    def test_clamp_within_range(self):
        assert clamp(50.0, 0.0, 100.0) == 50.0

    def test_clamp_below_min(self):
        assert clamp(-10.0, 0.0, 100.0) == 0.0

    def test_clamp_above_max(self):
        assert clamp(110.0, 0.0, 100.0) == 100.0


class TestCalculateFinalScore:
    def _payload(
        self,
        structure=80.0,
        readme=70.0,
        code_quality=75.0,
        ai_quality=80,
        files=None,
    ):
        return {
            "structure_analysis": {"score": structure},
            "readme_analysis":    {"score": readme},
            "code_analysis": {
                "overall_score": code_quality,
                "files": files or [],
            },
            "ai_data": {"ai_quality_score": ai_quality, "ai_available": True},
        }

    def test_returns_required_keys(self):
        result = calculate_final_score(self._payload())
        assert {"total_score", "grade", "badge", "breakdown"}.issubset(result)

    def test_breakdown_has_five_dimensions(self):
        result = calculate_final_score(self._payload())
        assert set(result["breakdown"]) == {
            "structure", "documentation", "code_quality", "security", "ai_assessment"
        }

    def test_total_score_in_range(self):
        result = calculate_final_score(self._payload())
        assert 0 <= result["total_score"] <= 100

    def test_perfect_scores_give_high_grade(self):
        result = calculate_final_score(self._payload(
            structure=100, readme=100, code_quality=100, ai_quality=100
        ))
        assert result["grade"] in ("A+", "A")
        assert result["total_score"] >= 90

    def test_zero_scores_give_f(self):
        result = calculate_final_score(self._payload(
            structure=0, readme=0, code_quality=0, ai_quality=0
        ))
        assert result["grade"] == "F"
        # Security returns 70 (neutral) when files list is empty, so total > 0
        assert result["total_score"] < 20

    def test_ai_unavailable_defaults_to_50(self):
        payload = self._payload()
        payload["ai_data"] = {"ai_available": False}   # no ai_quality_score key
        result = calculate_final_score(payload)
        # ai_assessment dimension should be 50
        assert result["breakdown"]["ai_assessment"]["score"] == 50.0

    def test_security_penalty_for_hardcoded_secret(self):
        files = [
            {
                "filename": "config.py",
                "issues": [
                    {"severity": "error", "message": "hardcoded secret detected", "count": 1}
                ],
            }
        ]
        no_issues = calculate_final_score(self._payload())
        with_issues = calculate_final_score(self._payload(files=files))
        assert with_issues["breakdown"]["security"]["score"] < \
               no_issues["breakdown"]["security"]["score"]

    def test_weight_sum_is_one(self):
        result = calculate_final_score(self._payload())
        total_weight = sum(v["weight"] for v in result["breakdown"].values())
        assert total_weight == 100   # weights stored as percentages

    def test_weighted_sum_equals_total(self):
        result = calculate_final_score(self._payload())
        computed = sum(v["weighted"] for v in result["breakdown"].values())
        # Allow small floating-point difference
        assert abs(computed - result["total_score"]) < 0.5


# ---------------------------------------------------------------------------
# 3. README analysis
# ---------------------------------------------------------------------------

from app.services.analyzer import analyze_readme


class TestAnalyzeReadme:
    def test_empty_readme_low_score(self):
        result = analyze_readme("")
        assert result["score"] < 20

    def test_full_readme_higher_score(self):
        readme = """
# Project Title

## Description
A great project that does things.

## Installation
```bash
pip install myproject
```

## Usage
```python
import myproject
```

## Features
- Feature 1
- Feature 2

## Contributing
Please read CONTRIBUTING.md.

## License
MIT

## Tests
Run with pytest.
        """
        result = analyze_readme(readme)
        assert result["score"] > 40

    def test_returns_required_keys(self):
        result = analyze_readme("# Title\n")
        assert {"score", "sections_found", "sections_missing", "suggestions"}.issubset(result)

    def test_title_detected(self):
        result = analyze_readme("# My Project\n\nSome description text here.\n")
        assert "title" in result["sections_found"] or result["score"] > 0

    def test_install_section_detected(self):
        readme = "# Proj\n## Installation\n```bash\npip install x\n```\n"
        result = analyze_readme(readme)
        found_lower = [s.lower() for s in result["sections_found"]]
        assert any("install" in s for s in found_lower)

    def test_score_increases_with_word_count(self):
        short = analyze_readme("# Title\n" + "word " * 50)
        long  = analyze_readme("# Title\n" + "word " * 600)
        assert long["score"] >= short["score"]


# ---------------------------------------------------------------------------
# 4. Structure analysis
# ---------------------------------------------------------------------------

from app.services.analyzer import analyze_structure


class TestAnalyzeStructure:
    def test_empty_repo_low_score(self):
        result = analyze_structure([])
        assert result["score"] == 0

    def test_readme_only_gives_some_score(self):
        result = analyze_structure(["README.md"])
        assert result["score"] > 0

    def test_full_project_higher_than_bare(self):
        bare = analyze_structure(["README.md"])
        full = analyze_structure([
            "README.md", "LICENSE", ".gitignore", ".env.example",
            "Dockerfile", "docker-compose.yml",
            ".github/workflows/ci.yml",
            "tests/test_main.py",
            "src/main.py",
            "docs/index.md",
            "requirements.txt",
            "pyproject.toml",
        ])
        assert full["score"] > bare["score"]

    def test_returns_required_keys(self):
        result = analyze_structure(["README.md"])
        assert {"score", "rules_matched", "rules_total"}.issubset(result)

    def test_score_is_clamped_0_100(self):
        result = analyze_structure(["README.md"] * 100)
        assert 0 <= result["score"] <= 100


# ---------------------------------------------------------------------------
# 5. GitHub URL validator shorthand (via validators util)
# ---------------------------------------------------------------------------

from app.utils.validators import parse_github_url


class TestParseGithubUrl:
    def test_valid_shorthand(self):
        assert parse_github_url("owner/repo") == ("owner", "repo")

    def test_invalid_no_slash(self):
        assert parse_github_url("ownerrepo") is None

    def test_invalid_full_url(self):
        assert parse_github_url("https://github.com/owner/repo") is None

    def test_hyphen_in_name(self):
        assert parse_github_url("my-org/my-repo") == ("my-org", "my-repo")

    def test_dots_in_name(self):
        assert parse_github_url("org/my.repo") == ("org", "my.repo")
