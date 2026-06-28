"""
GitHub REST API v3 service for AI GitHub Project Reviewer.

Public entry points
-------------------
  validate_github_url(url)          -> (owner, repo) | None   (strict regex)
  fetch_all(owner, repo)            -> GitHubData             (full parallel fetch)

Exception hierarchy
-------------------
  GitHubError
    RepoNotFoundError   – 404, repo may be deleted or never existed
    RepoPrivateError    – repo is private / token lacks access
    RateLimitError      – 403/429 rate-limit hit
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

import httpx
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API = "https://api.github.com"
_MAX_SOURCE_FILES = 20
_MAX_FILE_BYTES = 150 * 1024          # 150 KB per source file
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF = (0.0, 1.0, 3.0)     # seconds before each attempt

# GitHub URL strict regex
# Accepts: https://github.com/owner/repo  (with or without .git / trailing slash)
_GITHUB_URL_RE = re.compile(
    r"^https?://(?:www\.)?github\.com"
    r"/([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"   # owner
    r"/([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"   # repo
    r"(?:\.git)?/?$"
)

# Language lookup by file extension
SOURCE_EXTENSIONS: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cc": "C++",
    ".cs": "C#",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
}

# Directory names to skip when collecting source files
_SKIP_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", "dist", "build", "__pycache__",
    "vendor", "venv", ".venv", "env", "coverage",
    ".nyc_output", "target", "out", ".next", ".nuxt",
    ".cache", ".parcel-cache", "eggs", ".eggs",
})

# CI/CD config filenames at repo root
_CI_ROOT_FILES: frozenset[str] = frozenset({
    ".travis.yml", "jenkinsfile", ".gitlab-ci.yml",
    "bitbucket-pipelines.yml", "azure-pipelines.yml",
    "circle.yml", "codefresh.yml",
})


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GitHubError(Exception):
    """Base class for all GitHub service errors."""


class RepoNotFoundError(GitHubError):
    """404 – repository does not exist or caller cannot see it."""


class RepoPrivateError(GitHubError):
    """Repository is private and the supplied token lacks access."""


class RateLimitError(GitHubError):
    """GitHub API rate limit exceeded."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RepoInfo:
    full_name: str
    owner: str
    name: str
    description: str | None
    url: str
    homepage: str | None
    stars: int
    forks: int
    watchers: int
    open_issues: int
    language: str | None          # GitHub's detected primary language
    license: str | None
    created_at: str               # ISO-8601
    updated_at: str               # ISO-8601
    size_kb: int
    topics: list[str]
    default_branch: str
    is_fork: bool
    is_archived: bool
    visibility: str               # "public" | "private" | "internal"


@dataclass
class FilePresence:
    """Boolean flags for important files detected in the repository tree."""
    readme: bool = False
    license: bool = False
    gitignore: bool = False
    requirements_txt: bool = False
    package_json: bool = False
    dockerfile: bool = False
    docker_compose: bool = False
    github_actions: bool = False  # any .github/workflows/ file
    tests_dir: bool = False       # tests/ test/ __tests__/ spec/
    src_dir: bool = False         # src/ lib/ source/
    docs_dir: bool = False        # docs/ doc/ documentation/
    setup_py: bool = False
    pyproject_toml: bool = False
    env_example: bool = False
    ci_files: bool = False        # any CI/CD config detected


@dataclass
class SourceFile:
    path: str
    language: str
    size_bytes: int
    content: str


@dataclass
class GitHubData:
    repo: RepoInfo
    languages: dict[str, int]         # language name -> byte count
    contributors: list[dict]           # [{login, contributions, avatar_url}]
    file_tree: list[dict]              # root-level items for the frontend tree view
    file_presence: FilePresence
    readme: str | None
    source_files: list[SourceFile]     # up to MAX_SOURCE_FILES, content included
    commits: list[dict]                # last 30 commits, summarised


# ---------------------------------------------------------------------------
# HTTP client factory
# ---------------------------------------------------------------------------

def _make_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=_make_headers(), timeout=20.0, follow_redirects=True)


# ---------------------------------------------------------------------------
# Low-level request with retry + rate-limit handling
# ---------------------------------------------------------------------------

async def _request(
    client: httpx.AsyncClient,
    url: str,
    params: dict | None = None,
) -> httpx.Response:
    """
    GET ``url`` with up to _RETRY_ATTEMPTS tries and exponential backoff.

    Raises
    ------
    RateLimitError      on 403 (rate-limit) or 429
    RepoPrivateError    on 403 (non-rate-limit)
    RepoNotFoundError   on 404
    GitHubError         on any other failure after all retries
    """
    last_exc: Exception = GitHubError("Unknown error")

    for attempt in range(_RETRY_ATTEMPTS):
        if attempt:
            await asyncio.sleep(_RETRY_BACKOFF[attempt])

        try:
            resp = await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            last_exc = GitHubError(f"Request timed out: {url}")
            log.warning("Attempt %d/%d timeout for %s", attempt + 1, _RETRY_ATTEMPTS, url)
            continue
        except httpx.RequestError as exc:
            last_exc = GitHubError(f"Network error: {exc}")
            log.warning("Attempt %d/%d network error for %s: %s", attempt + 1, _RETRY_ATTEMPTS, url, exc)
            continue

        # 404 – don't retry
        if resp.status_code == 404:
            raise RepoNotFoundError(f"Resource not found: {url}")

        # Rate limit – don't retry, surface immediately
        if resp.status_code in (403, 429):
            body: dict = {}
            ct = resp.headers.get("content-type", "")
            if "json" in ct:
                try:
                    body = resp.json()
                except Exception:
                    pass
            msg = body.get("message", "")
            remaining = resp.headers.get("X-RateLimit-Remaining", "?")
            reset_ts = resp.headers.get("X-RateLimit-Reset", "?")

            if resp.status_code == 429 or "rate limit" in msg.lower():
                raise RateLimitError(
                    f"GitHub API rate limit exceeded (remaining={remaining}, "
                    f"reset={reset_ts}). Add GITHUB_TOKEN to raise the limit."
                )
            raise RepoPrivateError(
                f"GitHub access denied (HTTP 403). "
                "The repository may be private or your token lacks permissions. "
                f"API message: {msg or '(none)'}"
            )

        # Other HTTP errors – retry transient ones (5xx, 408, 503 …)
        if resp.is_error:
            last_exc = GitHubError(f"GitHub API returned {resp.status_code} for {url}")
            log.warning(
                "Attempt %d/%d HTTP %d for %s",
                attempt + 1, _RETRY_ATTEMPTS, resp.status_code, url,
            )
            continue

        return resp

    raise last_exc


# ---------------------------------------------------------------------------
# Individual fetch helpers (each takes an already-open client)
# ---------------------------------------------------------------------------

async def _fetch_repo(client: httpx.AsyncClient, owner: str, repo: str) -> dict:
    r = await _request(client, f"{_API}/repos/{owner}/{repo}")
    return r.json()


async def _fetch_languages(client: httpx.AsyncClient, owner: str, repo: str) -> dict[str, int]:
    try:
        r = await _request(client, f"{_API}/repos/{owner}/{repo}/languages")
        return r.json()
    except GitHubError as exc:
        log.warning("Could not fetch languages for %s/%s: %s", owner, repo, exc)
        return {}


async def _fetch_contributors(
    client: httpx.AsyncClient, owner: str, repo: str
) -> list[dict]:
    try:
        r = await _request(
            client,
            f"{_API}/repos/{owner}/{repo}/contributors",
            params={"per_page": "10", "anon": "false"},
        )
        raw = r.json()
        return [
            {
                "login": c.get("login"),
                "contributions": c.get("contributions", 0),
                "avatar_url": c.get("avatar_url"),
            }
            for c in raw
            if isinstance(c, dict)
        ]
    except GitHubError as exc:
        log.warning("Could not fetch contributors for %s/%s: %s", owner, repo, exc)
        return []


async def _fetch_readme(
    client: httpx.AsyncClient, owner: str, repo: str
) -> str | None:
    try:
        r = await _request(client, f"{_API}/repos/{owner}/{repo}/readme")
    except RepoNotFoundError:
        return None
    except GitHubError as exc:
        log.warning("Could not fetch README for %s/%s: %s", owner, repo, exc)
        return None

    data = r.json()
    raw = data.get("content", "")
    encoding = data.get("encoding", "base64")
    try:
        if encoding == "base64":
            return base64.b64decode(raw).decode("utf-8", errors="replace")
        return raw
    except Exception as exc:
        log.warning("Could not decode README for %s/%s: %s", owner, repo, exc)
        return None


async def _fetch_commits(
    client: httpx.AsyncClient, owner: str, repo: str
) -> list[dict]:
    try:
        r = await _request(
            client,
            f"{_API}/repos/{owner}/{repo}/commits",
            params={"per_page": "30"},
        )
        raw = r.json()
        return [
            {
                "sha": c.get("sha", "")[:8],
                "message": (
                    (c.get("commit") or {}).get("message", "").split("\n")[0][:120]
                ),
                "author": (
                    ((c.get("commit") or {}).get("author") or {}).get("name")
                ),
                "date": (
                    ((c.get("commit") or {}).get("author") or {}).get("date")
                ),
            }
            for c in raw
            if isinstance(c, dict)
        ]
    except GitHubError as exc:
        log.warning("Could not fetch commits for %s/%s: %s", owner, repo, exc)
        return []


async def _fetch_git_tree(
    client: httpx.AsyncClient, owner: str, repo: str, branch: str
) -> list[dict]:
    """
    Fetch the full recursive file tree via the Git Trees API.
    Falls back to empty list on failure or truncation of extremely large repos.
    """
    try:
        r = await _request(
            client,
            f"{_API}/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
        )
    except GitHubError as exc:
        log.warning("Could not fetch git tree for %s/%s@%s: %s", owner, repo, branch, exc)
        return []

    data = r.json()
    if data.get("truncated"):
        log.warning(
            "Git tree for %s/%s is truncated (repo too large for a single API call).",
            owner, repo,
        )

    return [item for item in data.get("tree", []) if isinstance(item, dict)]


# ---------------------------------------------------------------------------
# File-presence detection (runs entirely on the in-memory tree)
# ---------------------------------------------------------------------------

def _detect_file_presence(tree: list[dict]) -> FilePresence:
    all_paths: set[str] = {item["path"].lower() for item in tree}

    # Root-level names only (no directory separator)
    root_lower: set[str] = {
        item["path"].lower()
        for item in tree
        if "/" not in item["path"]
    }

    # First-level directory names
    top_dirs: set[str] = {
        item["path"].lower().split("/")[0]
        for item in tree
        if "/" in item["path"]
    }
    # Also include root tree-type entries as directory names
    top_dirs |= {
        item["path"].lower()
        for item in tree
        if item.get("type") == "tree" and "/" not in item["path"]
    }

    def root_has(*names: str) -> bool:
        return any(n in root_lower for n in names)

    def dir_has(*names: str) -> bool:
        return any(n in top_dirs for n in names)

    ci = root_has(*_CI_ROOT_FILES) or any(
        p.startswith(".circleci/") or p.startswith(".github/workflows/")
        for p in all_paths
    )

    return FilePresence(
        readme=root_has("readme.md", "readme.rst", "readme.txt", "readme"),
        license=root_has(
            "license", "license.md", "license.txt", "license.rst",
            "licence", "copying", "copying.md",
        ),
        gitignore=root_has(".gitignore"),
        requirements_txt=root_has("requirements.txt"),
        package_json=root_has("package.json"),
        dockerfile=root_has("dockerfile"),
        docker_compose=root_has(
            "docker-compose.yml", "docker-compose.yaml",
            "compose.yml", "compose.yaml",
        ),
        github_actions=any(p.startswith(".github/") for p in all_paths),
        tests_dir=dir_has("tests", "test", "__tests__", "spec"),
        src_dir=dir_has("src", "lib", "source"),
        docs_dir=dir_has("docs", "doc", "documentation"),
        setup_py=root_has("setup.py"),
        pyproject_toml=root_has("pyproject.toml"),
        env_example=root_has(".env.example", ".env.sample", ".env.template"),
        ci_files=ci,
    )


# ---------------------------------------------------------------------------
# Source-file collection
# ---------------------------------------------------------------------------

def _should_skip_path(path: str) -> bool:
    """True if any directory component of *path* is in the skip list."""
    # Only check directory parts (everything except the last segment)
    parts = path.split("/")
    return any(part in _SKIP_DIRS for part in parts[:-1])


def _is_candidate_source_file(item: dict) -> bool:
    if item.get("type") != "blob":
        return False
    path = item.get("path", "")
    if _should_skip_path(path):
        return False
    ext = PurePosixPath(path).suffix.lower()
    return ext in SOURCE_EXTENSIONS


async def _fetch_blob_content(
    client: httpx.AsyncClient, owner: str, repo: str, sha: str
) -> str | None:
    """Fetch a single blob by SHA and decode it to a UTF-8 string."""
    try:
        r = await _request(
            client,
            f"{_API}/repos/{owner}/{repo}/git/blobs/{sha}",
        )
    except GitHubError:
        return None

    data = r.json()
    encoding = data.get("encoding", "base64")
    raw = data.get("content", "")

    try:
        if encoding == "base64":
            return base64.b64decode(raw).decode("utf-8", errors="replace")
        return raw  # "utf-8" encoding returned directly
    except Exception:
        return None


async def _fetch_source_files(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    tree: list[dict],
) -> list[SourceFile]:
    # Filter to source files within size budget
    candidates = [
        item for item in tree
        if _is_candidate_source_file(item)
        and item.get("size", 0) <= _MAX_FILE_BYTES
        and item.get("size", 0) > 0
    ]

    # Prefer smaller files (faster, usually more focused code)
    candidates.sort(key=lambda x: x.get("size", 0))
    candidates = candidates[:_MAX_SOURCE_FILES]

    # Throttle concurrent blob fetches to avoid secondary rate limits
    sem = asyncio.Semaphore(5)

    async def fetch_one(item: dict) -> SourceFile | None:
        async with sem:
            content = await _fetch_blob_content(client, owner, repo, item["sha"])
            if content is None:
                return None
            ext = PurePosixPath(item["path"]).suffix.lower()
            return SourceFile(
                path=item["path"],
                language=SOURCE_EXTENSIONS[ext],
                size_bytes=item.get("size", 0),
                content=content,
            )

    results = await asyncio.gather(*(fetch_one(item) for item in candidates))
    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _build_repo_info(raw: dict, owner: str, repo: str) -> RepoInfo:
    return RepoInfo(
        full_name=raw.get("full_name", f"{owner}/{repo}"),
        owner=owner,
        name=repo,
        description=raw.get("description") or None,
        url=raw.get("html_url", f"https://github.com/{owner}/{repo}"),
        homepage=raw.get("homepage") or None,
        stars=raw.get("stargazers_count", 0),
        forks=raw.get("forks_count", 0),
        watchers=raw.get("watchers_count", 0),
        open_issues=raw.get("open_issues_count", 0),
        language=raw.get("language") or None,
        license=(raw.get("license") or {}).get("name") or None,
        created_at=raw.get("created_at", ""),
        updated_at=raw.get("updated_at", ""),
        size_kb=raw.get("size", 0),
        topics=raw.get("topics", []),
        default_branch=raw.get("default_branch", "main"),
        is_fork=bool(raw.get("fork", False)),
        is_archived=bool(raw.get("archived", False)),
        visibility=raw.get("visibility", "public"),
    )


def _build_root_file_tree(tree: list[dict]) -> list[dict]:
    """
    Extract root-level entries only, converting the flat git-tree format
    to the {name, type, size, path} shape expected by the frontend.
    """
    root_items = [item for item in tree if "/" not in item.get("path", "")]
    return [
        {
            "name": item["path"],
            "type": "dir" if item.get("type") == "tree" else "file",
            "size": item.get("size", 0),
            "path": item["path"],
        }
        for item in root_items
    ]


# ---------------------------------------------------------------------------
# URL validation (strict, full-URL only)
# ---------------------------------------------------------------------------

def validate_github_url(url: str) -> tuple[str, str] | None:
    """
    Validate a full GitHub URL with a strict regex.

    Returns (owner, repo) on success, None on any mismatch.
    Accepted forms:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - https://github.com/owner/repo/
    Rejected: non-HTTPS, non-GitHub hosts, extra path segments, bare owner/repo.
    """
    m = _GITHUB_URL_RE.match(url.strip())
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    # Reject names that look like Git reserved words or are suspiciously short
    if owner.lower() in (".", "..") or repo.lower() in (".", ".."):
        return None
    return owner, repo


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def fetch_all(owner: str, repo: str) -> GitHubData:
    """
    Fetch all data for *owner/repo* and return a fully populated GitHubData.

    The single client is reused for all requests in this call to benefit from
    HTTP keep-alive connection pooling.

    Raises
    ------
    RepoNotFoundError   – repo does not exist (or token can't see it)
    RepoPrivateError    – repo is private
    RateLimitError      – rate limit hit
    GitHubError         – any other unrecoverable API error
    """
    async with _make_client() as client:
        # Fail fast if the repo itself is inaccessible
        raw_repo = await _fetch_repo(client, owner, repo)

        if raw_repo.get("private"):
            raise RepoPrivateError(
                f"Repository {owner}/{repo} is private. "
                "Provide a GITHUB_TOKEN that has read access to this repository."
            )

        branch = raw_repo.get("default_branch", "main")

        # All secondary fetches are independent – run them concurrently.
        # return_exceptions=True means a failed fetch degrades gracefully
        # instead of aborting the entire review.
        (
            languages_r,
            contributors_r,
            readme_r,
            commits_r,
            tree_r,
        ) = await asyncio.gather(
            _fetch_languages(client, owner, repo),
            _fetch_contributors(client, owner, repo),
            _fetch_readme(client, owner, repo),
            _fetch_commits(client, owner, repo),
            _fetch_git_tree(client, owner, repo, branch),
            return_exceptions=True,
        )

        # Unwrap results, substituting safe defaults for any that failed
        def _unwrap(result, default):
            if isinstance(result, Exception):
                log.warning("Secondary fetch failed: %s", result)
                return default
            return result

        languages: dict[str, int] = _unwrap(languages_r, {})
        contributors: list[dict] = _unwrap(contributors_r, [])
        readme: str | None = _unwrap(readme_r, None)
        commits: list[dict] = _unwrap(commits_r, [])
        tree: list[dict] = _unwrap(tree_r, [])

        file_presence = _detect_file_presence(tree)
        source_files = await _fetch_source_files(client, owner, repo, tree)

        return GitHubData(
            repo=_build_repo_info(raw_repo, owner, repo),
            languages=languages,
            contributors=contributors,
            file_tree=_build_root_file_tree(tree),
            file_presence=file_presence,
            readme=readme,
            source_files=source_files,
            commits=commits,
        )
