import re
from urllib.parse import urlparse

# GitHub owner/repo shorthand: alphanumeric with hyphens/dots/underscores,
# must start and end with alphanumeric, no consecutive dots.
_SHORTHAND_RE = re.compile(
    r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"/([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)$"
)


def parse_github_url(url: str) -> tuple[str, str] | None:
    """
    Accept owner/repo shorthand only.
    Full https://github.com/… URLs are handled by github.validate_github_url.
    Returns (owner, repo) or None.
    """
    url = url.strip().rstrip("/")
    m = _SHORTHAND_RE.match(url)
    if m:
        return m.group(1), m.group(2)
    return None


def validate_repo_url(url: str) -> bool:
    return parse_github_url(url) is not None
