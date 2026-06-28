"""
Multi-language static code analyzer for AI GitHub Project Reviewer.

Public API
----------
  analyze_code(data: GitHubData) -> CodeAnalysis
  analyze_readme(readme_content: str) -> dict
  analyze_structure(file_list: list[str | dict]) -> dict
  compute_score(data: GitHubData,
                code_analysis: CodeAnalysis | None,
                readme_analysis: dict | None,
                structure_analysis: dict | None) -> dict
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from app.services.github import GitHubData, FilePresence, SourceFile
from app.utils.helpers import clamp


# ---------------------------------------------------------------------------
# Output data structures
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    severity: str   # "error" | "warning" | "info"
    message: str
    count: int = 1


@dataclass
class FileMetrics:
    lines_of_code: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    code_lines: int = 0


@dataclass
class FileResult:
    filename: str
    language: str
    metrics: FileMetrics
    issues: list[Issue]
    score: float          # 0-100


@dataclass
class LanguageSummary:
    language: str
    file_count: int
    total_lines: int
    avg_score: float
    total_issues: int
    error_count: int
    warning_count: int


@dataclass
class CodeAnalysis:
    files: list[FileResult]
    language_summaries: list[LanguageSummary]
    overall_score: float
    top_issues: list[Issue]           # top-5 across all files
    chart_data: list[dict]            # [{language, score, files}]
    total_files_analyzed: int
    total_lines_analyzed: int


# ---------------------------------------------------------------------------
# Shared line-counting utility
# ---------------------------------------------------------------------------

def _base_metrics(lines: list[str], comment_chars: tuple[str, ...]) -> FileMetrics:
    blank = comment = 0
    for ln in lines:
        s = ln.strip()
        if not s:
            blank += 1
        elif any(s.startswith(c) for c in comment_chars):
            comment += 1
    code = len(lines) - blank - comment
    return FileMetrics(
        lines_of_code=len(lines),
        blank_lines=blank,
        comment_lines=comment,
        code_lines=max(code, 0),
    )


def _score_from_issues(issues: list[Issue], loc: int) -> float:
    """Deduct from 100 based on severity and density."""
    deduction = 0.0
    for iss in issues:
        if iss.severity == "error":
            deduction += iss.count * 4
        elif iss.severity == "warning":
            deduction += iss.count * 2
        else:
            deduction += iss.count * 0.5
    # Normalise by LOC so small files aren't unfairly penalised
    density_factor = clamp(100 / max(loc, 50), 0.2, 1.0)
    return round(clamp(100 - deduction * density_factor, 0, 100), 1)


# ---------------------------------------------------------------------------
# Python analyzer
# ---------------------------------------------------------------------------

_PY_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([\w.]+)", re.MULTILINE)
_PY_DEF_RE    = re.compile(r"^\s*def\s+\w+", re.MULTILINE)
_PY_CLASS_RE  = re.compile(r"^\s*class\s+\w+", re.MULTILINE)
_PY_SECRET_RE = re.compile(
    r'(?:password|api_key|secret|token|passwd)\s*=\s*["\'][^"\']{3,}["\']',
    re.IGNORECASE,
)
_PY_TYPE_HINT_RE = re.compile(r"def\s+\w+\s*\(.*?\)\s*->|:\s*(?:int|str|bool|float|list|dict|tuple|set|None|Optional|Union|Any)\b")


def _analyze_python(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("#",))
    issues: list[Issue] = []

    # Counts
    imports = _PY_IMPORT_RE.findall(src)
    funcs   = _PY_DEF_RE.findall(src)
    classes = _PY_CLASS_RE.findall(src)

    # --- Unused imports ---
    imported_names = []
    for imp in imports:
        imported_names.append(imp.split(".")[0])
    body_without_imports = re.sub(r"^\s*(?:import|from)\s+.*$", "", src, flags=re.MULTILINE)
    unused = [n for n in imported_names if n and not re.search(r"\b" + re.escape(n) + r"\b", body_without_imports)]
    if unused:
        issues.append(Issue("warning", f"Potentially unused imports: {', '.join(set(unused))}", len(set(unused))))

    # --- Docstring coverage ---
    def_positions = [m.start() for m in re.finditer(r"^\s*def\s+", src, re.MULTILINE)]
    missing_docs = 0
    for pos in def_positions:
        after = src[pos:pos + 300]
        if '"""' not in after[:200] and "'''" not in after[:200]:
            missing_docs += 1
    if missing_docs:
        issues.append(Issue("info", f"Functions missing docstrings", missing_docs))

    # --- Long functions (>50 lines) ---
    func_blocks = re.split(r"(?=^\s*def\s)", src, flags=re.MULTILINE)
    long_funcs = sum(1 for b in func_blocks if b.strip().startswith("def") and len(b.splitlines()) > 50)
    if long_funcs:
        issues.append(Issue("warning", "Functions exceeding 50 lines", long_funcs))

    # --- Exception handling ---
    try_count = len(re.findall(r"^\s*try\s*:", src, re.MULTILINE))
    bare_except = len(re.findall(r"^\s*except\s*:", src, re.MULTILINE))
    if bare_except:
        issues.append(Issue("warning", "Bare except clauses (catches all exceptions)", bare_except))

    # --- Debug statements ---
    debug = len(re.findall(r"\bprint\s*\(", src)) + \
            len(re.findall(r"\bpdb\b", src)) + \
            len(re.findall(r"\bbreakpoint\s*\(\s*\)", src))
    if debug:
        issues.append(Issue("info", "Debug statements (print/pdb/breakpoint)", debug))

    # --- Hardcoded secrets ---
    secrets = _PY_SECRET_RE.findall(src)
    if secrets:
        issues.append(Issue("error", "Potential hardcoded secrets (password/api_key/secret)", len(secrets)))

    # --- Type hints ---
    annotated = len(_PY_TYPE_HINT_RE.findall(src))
    total_funcs = len(funcs)
    if total_funcs > 0:
        hint_pct = int(annotated / total_funcs * 100)
        if hint_pct < 30:
            issues.append(Issue("info", f"Low type-hint coverage (~{hint_pct}% of functions)", 1))

    # --- Commented-out code ---
    commented_code = len(re.findall(r"#\s*(?:def |class |import |return |if |for |while )", src))
    if commented_code:
        issues.append(Issue("info", "Commented-out code blocks", commented_code))

    return FileResult(
        filename=sf.path, language="Python",
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# JavaScript / JSX analyzer
# ---------------------------------------------------------------------------

_JS_ARROW_RE  = re.compile(r"(?:const|let|var)\s+\w+\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>")
_JS_FUNC_RE   = re.compile(r"\bfunction\s*\w*\s*\(")
_JS_CLASS_RE  = re.compile(r"\bclass\s+\w+")
_JS_IMPORT_RE = re.compile(r"^\s*(?:import\s|require\s*\()", re.MULTILINE)
_JS_SECRET_RE = re.compile(
    r'(?:apiKey|api_key|password|secret|token)\s*[:=]\s*["\'][A-Za-z0-9+/=_\-]{8,}["\']',
    re.IGNORECASE,
)
_JS_URL_RE = re.compile(r'(?:https?://(?!example\.com|localhost)[a-zA-Z0-9\-./]{10,})')


def _analyze_javascript(sf: SourceFile, is_ts: bool = False) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("//", "/*", " *", "*/"))
    issues: list[Issue] = []
    lang = "TypeScript" if is_ts else ("JSX" if sf.path.endswith(".jsx") else "JavaScript")

    funcs   = len(_JS_FUNC_RE.findall(src)) + len(_JS_ARROW_RE.findall(src))
    classes = len(_JS_CLASS_RE.findall(src))

    # --- console.log ---
    console_logs = len(re.findall(r"\bconsole\.\w+\s*\(", src))
    if console_logs:
        issues.append(Issue("warning", "console.log/warn/error debug statements", console_logs))

    # --- TODO/FIXME ---
    todos = len(re.findall(r"//\s*(?:TODO|FIXME|HACK|XXX)\b", src, re.IGNORECASE))
    if todos:
        issues.append(Issue("info", "TODO/FIXME comments", todos))

    # --- Error handling ---
    try_catch = len(re.findall(r"\btry\s*\{", src))
    dot_catch  = len(re.findall(r"\.catch\s*\(", src))
    if try_catch + dot_catch == 0 and funcs > 2:
        issues.append(Issue("warning", "No error handling (try/catch or .catch) detected", 1))

    # --- var usage ---
    var_count = len(re.findall(r"\bvar\s+\w+", src))
    if var_count:
        issues.append(Issue("warning", "var declarations (prefer let/const)", var_count))

    # --- Long functions ---
    blocks = re.split(r"(?=\bfunction\b|\bconst\b|\blet\b)", src)
    long_f = sum(1 for b in blocks if re.match(r"(?:function|const|let)", b.strip()) and len(b.splitlines()) > 40)
    if long_f:
        issues.append(Issue("warning", "Functions exceeding 40 lines", long_f))

    # --- Hardcoded secrets / URLs ---
    secrets = _JS_SECRET_RE.findall(src)
    if secrets:
        issues.append(Issue("error", "Potential hardcoded API keys/secrets", len(secrets)))
    urls = _JS_URL_RE.findall(src)
    if len(urls) > 3:
        issues.append(Issue("info", "Hardcoded URLs (consider env variables)", len(urls)))

    # --- TypeScript-specific ---
    if is_ts:
        any_count = len(re.findall(r":\s*any\b", src))
        if any_count:
            issues.append(Issue("warning", "Explicit 'any' type usage", any_count))

        non_null = len(re.findall(r"\w+!", src))
        if non_null > 5:
            issues.append(Issue("info", "Non-null assertions (!)", non_null))

        interfaces = len(re.findall(r"\binterface\s+\w+", src))
        types      = len(re.findall(r"\btype\s+\w+\s*=", src))
        if interfaces + types == 0 and metrics.code_lines > 30:
            issues.append(Issue("info", "No interfaces or type aliases defined", 1))

    return FileResult(
        filename=sf.path, language=lang,
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# Java analyzer
# ---------------------------------------------------------------------------

def _analyze_java(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("//", "/*", " *", "*/"))
    issues: list[Issue] = []

    methods   = len(re.findall(r"(?:public|private|protected)\s+\w[\w<>\[\]]*\s+\w+\s*\(", src))
    classes   = len(re.findall(r"\bclass\s+\w+", src))
    imports   = len(re.findall(r"^\s*import\s+", src, re.MULTILINE))
    interfaces= len(re.findall(r"\binterface\s+\w+", src))

    # --- Javadoc on public methods ---
    public_methods = re.findall(r"((?:\/\*\*.*?\*\/\s*)?public\s+\w[\w<>\[\]]*\s+\w+\s*\()", src, re.DOTALL)
    no_javadoc = sum(1 for m in public_methods if "/**" not in m)
    if no_javadoc:
        issues.append(Issue("info", "Public methods without Javadoc", no_javadoc))

    # --- System.out.println ---
    sout = len(re.findall(r"\bSystem\.out\.print", src))
    if sout:
        issues.append(Issue("warning", "System.out.println debug statements", sout))

    # --- Empty catch blocks ---
    empty_catch = len(re.findall(r"catch\s*\([^)]+\)\s*\{\s*\}", src))
    if empty_catch:
        issues.append(Issue("error", "Empty catch blocks (swallowed exceptions)", empty_catch))

    # --- Magic numbers ---
    magic = len(re.findall(r"(?<![A-Z_])\b(?!0\b|1\b)\d{2,}\b", src))
    if magic > 5:
        issues.append(Issue("info", "Magic number literals (consider named constants)", magic))

    # --- Long methods (>30 lines) ---
    method_blocks = re.split(r"(?=(?:public|private|protected)\s)", src)
    long_m = sum(1 for b in method_blocks if len(b.splitlines()) > 30 and
                 re.match(r"(?:public|private|protected)", b.strip()))
    if long_m:
        issues.append(Issue("warning", "Methods exceeding 30 lines", long_m))

    return FileResult(
        filename=sf.path, language="Java",
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# C analyzer
# ---------------------------------------------------------------------------

def _analyze_c(sf: SourceFile, is_cpp: bool = False) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("//", "/*", " *", "*/"))
    issues: list[Issue] = []
    lang = "C++" if is_cpp else "C"

    includes = len(re.findall(r"^\s*#include\s*", src, re.MULTILINE))
    funcs    = len(re.findall(r"^\w[\w\s\*]+\w\s*\([^;]*\)\s*\{", src, re.MULTILINE))
    structs  = len(re.findall(r"\bstruct\s+\w+", src))

    # --- malloc without free ---
    mallocs = len(re.findall(r"\bmalloc\s*\(", src))
    frees   = len(re.findall(r"\bfree\s*\(", src))
    if mallocs > frees:
        issues.append(Issue("error", f"malloc calls ({mallocs}) exceed free calls ({frees}) — possible leak", mallocs - frees))

    # --- gets() unsafe ---
    if re.search(r"\bgets\s*\(", src):
        issues.append(Issue("error", "Unsafe gets() usage (use fgets instead)", len(re.findall(r"\bgets\s*\(", src))))

    # --- NULL checks ---
    ptr_derefs = len(re.findall(r"\*\w+\s*(?:[=\+\-\[\(]|->)", src))
    null_checks = len(re.findall(r"if\s*\([^)]*(?:NULL|nullptr|!= NULL)", src))
    if ptr_derefs > 5 and null_checks == 0:
        issues.append(Issue("warning", "Pointer dereferences with no NULL checks detected", 1))

    # --- Long functions ---
    func_blocks = re.split(r"(?=^\w[\w\s\*]+\w\s*\()", src, flags=re.MULTILINE)
    long_f = sum(1 for b in func_blocks if len(b.splitlines()) > 50)
    if long_f:
        issues.append(Issue("warning", "Functions exceeding 50 lines", long_f))

    # --- Magic numbers ---
    magic = len(re.findall(r"(?<![A-Z_])\b(?!0\b|1\b)\d{3,}\b", src))
    if magic > 3:
        issues.append(Issue("info", "Magic number literals", magic))

    # --- TODO/FIXME ---
    todos = len(re.findall(r"//\s*(?:TODO|FIXME)\b", src, re.IGNORECASE))
    if todos:
        issues.append(Issue("info", "TODO/FIXME comments", todos))

    # C++-specific
    if is_cpp:
        raw_ptrs = len(re.findall(r"\bnew\s+\w+", src))
        smart_ptrs = len(re.findall(r"\b(?:unique_ptr|shared_ptr|weak_ptr)\b", src))
        if raw_ptrs > smart_ptrs and raw_ptrs > 2:
            issues.append(Issue("warning", f"Raw new/delete ({raw_ptrs}) vs smart pointers ({smart_ptrs})", raw_ptrs))

        if re.search(r"using\s+namespace\s+std\s*;", src) and sf.path.endswith((".hpp", ".h")):
            issues.append(Issue("error", "using namespace std in header file (pollutes global namespace)", 1))

        if re.search(r"\bclass\s+\w+", src) and not re.search(r"\bvirtual\s+~", src):
            if re.search(r"\bvirtual\s+\w", src):
                issues.append(Issue("warning", "Class with virtual methods but no virtual destructor", 1))

    return FileResult(
        filename=sf.path, language=lang,
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# C# analyzer
# ---------------------------------------------------------------------------

def _analyze_csharp(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("//", "/*", " *", "///"))
    issues: list[Issue] = []

    classes    = len(re.findall(r"\bclass\s+\w+", src))
    methods    = len(re.findall(r"(?:public|private|protected|internal)\s+\w[\w<>\[\]?]*\s+\w+\s*\(", src))
    namespaces = len(re.findall(r"\bnamespace\s+\w+", src))
    interfaces = len(re.findall(r"\binterface\s+I\w+", src))

    # --- XML doc comments ---
    public_m = len(re.findall(r"public\s+\w[\w<>\[\]?]*\s+\w+\s*\(", src))
    xml_docs  = len(re.findall(r"///\s*<summary>", src))
    if public_m > 0 and xml_docs < public_m // 2:
        issues.append(Issue("info", "Public members missing XML documentation comments", public_m - xml_docs))

    # --- Exception handling ---
    empty_catch = len(re.findall(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}", src))
    if empty_catch:
        issues.append(Issue("error", "Empty catch blocks", empty_catch))

    # --- Nullable usage ---
    nullable = len(re.findall(r"\w+\?\s+\w+", src))
    if nullable == 0 and methods > 3:
        issues.append(Issue("info", "No nullable reference types used (consider enabling nullable context)", 1))

    # --- LINQ ---
    linq = len(re.findall(r"\.(Where|Select|OrderBy|GroupBy|FirstOrDefault|Any|All|Count)\s*\(", src))

    # --- Magic strings/numbers ---
    magic_str = len(re.findall(r'(?:==|!=)\s*"[^"]{3,}"', src))
    if magic_str > 3:
        issues.append(Issue("info", "Magic string comparisons (consider constants)", magic_str))

    magic_num = len(re.findall(r"(?<![A-Z_])\b(?!0\b|1\b)\d{3,}\b", src))
    if magic_num > 3:
        issues.append(Issue("info", "Magic numeric literals", magic_num))

    return FileResult(
        filename=sf.path, language="C#",
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# SQL analyzer
# ---------------------------------------------------------------------------

def _analyze_sql(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("--", "/*", " *"))
    issues: list[Issue] = []

    tables  = len(re.findall(r"\bCREATE\s+TABLE\b", src, re.IGNORECASE))
    procs   = len(re.findall(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\b", src, re.IGNORECASE))
    funcs   = len(re.findall(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\b", src, re.IGNORECASE))
    views   = len(re.findall(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\b", src, re.IGNORECASE))
    indexes = len(re.findall(r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b", src, re.IGNORECASE))

    # --- SELECT * ---
    star_selects = len(re.findall(r"\bSELECT\s+\*", src, re.IGNORECASE))
    if star_selects:
        issues.append(Issue("warning", "SELECT * usage (specify columns explicitly)", star_selects))

    # --- DELETE/UPDATE without WHERE ---
    naked_delete = len(re.findall(r"\bDELETE\s+FROM\s+\w+\s*;", src, re.IGNORECASE))
    naked_update = len(re.findall(r"\bUPDATE\s+\w+\s+SET\s+[^W]+;", src, re.IGNORECASE))
    if naked_delete:
        issues.append(Issue("error", "DELETE without WHERE clause (will delete all rows)", naked_delete))
    if naked_update:
        issues.append(Issue("error", "UPDATE without WHERE clause (will update all rows)", naked_update))

    # --- No indexes ---
    if tables > 0 and indexes == 0:
        issues.append(Issue("warning", "Tables defined but no indexes created", 1))

    # --- Missing PRIMARY KEY ---
    create_blocks = re.findall(r"CREATE\s+TABLE[^;]+;", src, re.IGNORECASE | re.DOTALL)
    no_pk = sum(1 for b in create_blocks if "PRIMARY KEY" not in b.upper())
    if no_pk:
        issues.append(Issue("warning", "Tables without PRIMARY KEY definition", no_pk))

    # --- SQL injection risk: string concat in queries ---
    concat_risk = len(re.findall(r"[\"']\s*\+\s*\$|EXEC\s*\(|EXECUTE\s*\(", src, re.IGNORECASE))
    if concat_risk:
        issues.append(Issue("error", "Possible SQL injection: dynamic query construction", concat_risk))

    return FileResult(
        filename=sf.path, language="SQL",
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# HTML analyzer
# ---------------------------------------------------------------------------

def _analyze_html(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("<!--",))
    issues: list[Issue] = []

    all_tags = len(re.findall(r"<\w+", src))
    forms    = len(re.findall(r"<form\b", src, re.IGNORECASE))
    links    = len(re.findall(r"<a\s+", src, re.IGNORECASE))
    images   = len(re.findall(r"<img\b", src, re.IGNORECASE))
    scripts  = len(re.findall(r"<script\b", src, re.IGNORECASE))

    # --- Missing alt on img ---
    imgs_no_alt = len(re.findall(r"<img\b(?![^>]*\balt\s*=)[^>]*>", src, re.IGNORECASE))
    if imgs_no_alt:
        issues.append(Issue("error", "Images missing alt attribute (accessibility)", imgs_no_alt))

    # --- Missing lang on html ---
    if re.search(r"<html\b", src, re.IGNORECASE) and not re.search(r"<html\b[^>]*\blang\s*=", src, re.IGNORECASE):
        issues.append(Issue("warning", "Missing lang attribute on <html> element", 1))

    # --- Inline styles ---
    inline_styles = len(re.findall(r'\bstyle\s*=\s*"[^"]{5,}"', src, re.IGNORECASE))
    if inline_styles:
        issues.append(Issue("info", "Inline style attributes (prefer CSS classes)", inline_styles))

    # --- Deprecated tags ---
    deprecated = ["<font", "<center", "<marquee", "<blink", "<frame", "<frameset"]
    dep_count = sum(len(re.findall(re.escape(t), src, re.IGNORECASE)) for t in deprecated)
    if dep_count:
        issues.append(Issue("error", "Deprecated HTML tags (<font>, <center>, <marquee>, etc.)", dep_count))

    # --- Missing meta viewport ---
    if not re.search(r'<meta\b[^>]*\bviewport\b', src, re.IGNORECASE):
        issues.append(Issue("warning", "Missing <meta name='viewport'> (not mobile-friendly)", 1))

    # --- Inputs without labels ---
    inputs = len(re.findall(r"<input\b", src, re.IGNORECASE))
    labels = len(re.findall(r"<label\b", src, re.IGNORECASE))
    if inputs > labels:
        issues.append(Issue("warning", f"Input elements ({inputs}) may lack labels ({labels} found)", inputs - labels))

    # --- External scripts without integrity ---
    ext_scripts = re.findall(r'<script\b[^>]*src\s*=\s*"http[^"]*"[^>]*>', src, re.IGNORECASE)
    no_sri = sum(1 for s in ext_scripts if "integrity" not in s)
    if no_sri:
        issues.append(Issue("warning", "External scripts without SRI integrity attribute", no_sri))

    return FileResult(
        filename=sf.path, language="HTML",
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# CSS / SCSS / SASS analyzer
# ---------------------------------------------------------------------------

def _analyze_css(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("/*", " *", "//"))
    issues: list[Issue] = []
    lang = "SCSS" if sf.path.endswith((".scss", ".sass")) else "CSS"

    rules        = len(re.findall(r"\{", src))
    media_queries= len(re.findall(r"@media\s+", src, re.IGNORECASE))
    css_vars     = len(re.findall(r"--[\w-]+\s*:", src))
    scss_vars    = len(re.findall(r"\$[\w-]+\s*:", src))

    # --- !important overuse ---
    important = len(re.findall(r"!important", src, re.IGNORECASE))
    if important > 3:
        issues.append(Issue("warning", f"Excessive !important usage ({important} times)", important))
    elif important:
        issues.append(Issue("info", "!important usage", important))

    # --- Deep selector chains (> 4 levels) ---
    deep = [ln for ln in lines if ln.strip() and not ln.strip().startswith(("/", "*", "@", "{", "}"))
            and ln.count(" ") > 4 and re.search(r"\w\s+\w", ln)]
    if len(deep) > 5:
        issues.append(Issue("info", "Very deep selector chains (>4 levels)", len(deep)))

    # --- Duplicate selectors ---
    selectors = [m.group(0).strip() for m in re.finditer(r"^[^\{@/\*\n][^\{]*(?=\s*\{)", src, re.MULTILINE)]
    dup_sel = {s: c for s, c in Counter(selectors).items() if c > 1}
    if dup_sel:
        issues.append(Issue("warning", f"Duplicate selectors ({len(dup_sel)} repeated)", sum(dup_sel.values())))

    # --- Magic px values ---
    px_vals = re.findall(r"\b(\d+)px\b", src)
    unique_px = len(set(px_vals))
    if unique_px > 10:
        issues.append(Issue("info", f"Many hardcoded px values ({unique_px} unique) — consider CSS variables", unique_px))

    # --- Hardcoded colors vs CSS vars ---
    hardcoded_colors = len(re.findall(r"(?:^|[\s:])#[0-9a-fA-F]{3,6}\b", src))
    if hardcoded_colors > 5 and css_vars + scss_vars == 0:
        issues.append(Issue("info", "Hardcoded color values with no CSS/SCSS variables defined", hardcoded_colors))

    return FileResult(
        filename=sf.path, language=lang,
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# Go analyzer
# ---------------------------------------------------------------------------

def _analyze_go(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("//", "/*"))
    issues: list[Issue] = []

    funcs      = len(re.findall(r"^func\s+", src, re.MULTILINE))
    structs    = len(re.findall(r"\btype\s+\w+\s+struct\b", src))
    interfaces = len(re.findall(r"\btype\s+\w+\s+interface\b", src))
    imports    = len(re.findall(r'"[\w./]+"', src))

    # --- Ignored error returns ---
    ignored_errs = len(re.findall(r"\b_\s*,\s*(?:err|error)\b|\b(?:err|error)\s*,\s*_\b", src))
    if ignored_errs:
        issues.append(Issue("error", "Error return values ignored (_, err pattern)", ignored_errs))

    # --- fmt.Println debug ---
    fmt_print = len(re.findall(r"\bfmt\.Print(?:ln|f)?\s*\(", src))
    if fmt_print:
        issues.append(Issue("info", "fmt.Println/Printf debug statements", fmt_print))

    # --- Missing error handling ---
    err_returns = len(re.findall(r"\berr\s*:=", src))
    err_checks  = len(re.findall(r"if\s+err\s*!=\s*nil", src))
    unchecked = err_returns - err_checks
    if unchecked > 2:
        issues.append(Issue("warning", f"Error values assigned but possibly not checked ({unchecked})", unchecked))

    # --- Long functions ---
    func_blocks = re.split(r"(?=^func\s)", src, flags=re.MULTILINE)
    long_f = sum(1 for b in func_blocks if b.strip().startswith("func") and len(b.splitlines()) > 40)
    if long_f:
        issues.append(Issue("warning", "Functions exceeding 40 lines", long_f))

    return FileResult(
        filename=sf.path, language="Go",
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# PHP analyzer
# ---------------------------------------------------------------------------

def _analyze_php(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("//", "#", "/*"))
    issues: list[Issue] = []

    funcs   = len(re.findall(r"\bfunction\s+\w+", src))
    classes = len(re.findall(r"\bclass\s+\w+", src))
    includes= len(re.findall(r"\b(?:include|require)(?:_once)?\s*[(\"]", src))

    # --- SQL injection risk ---
    sqli = len(re.findall(r'(?:mysql_query|mysqli_query|pg_query)\s*\([^)]*\$_(?:GET|POST|REQUEST)', src))
    if sqli:
        issues.append(Issue("error", "SQL injection risk: unsanitized user input in query", sqli))

    # --- eval() usage ---
    evals = len(re.findall(r"\beval\s*\(", src))
    if evals:
        issues.append(Issue("error", "eval() usage (security risk)", evals))

    # --- Deprecated mysql_ functions ---
    deprecated_mysql = len(re.findall(r"\bmysql_\w+\s*\(", src))
    if deprecated_mysql:
        issues.append(Issue("error", "Deprecated mysql_* functions (use PDO or mysqli)", deprecated_mysql))

    # --- Error suppression operator ---
    error_suppression = len(re.findall(r"@\w+\s*\(", src))
    if error_suppression:
        issues.append(Issue("warning", "Error suppression operator @ usage", error_suppression))

    return FileResult(
        filename=sf.path, language="PHP",
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# Rust analyzer
# ---------------------------------------------------------------------------

def _analyze_rust(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("//", "/*"))
    issues: list[Issue] = []

    funcs   = len(re.findall(r"\bfn\s+\w+", src))
    structs = len(re.findall(r"\bstruct\s+\w+", src))
    enums   = len(re.findall(r"\benum\s+\w+", src))

    unwraps = len(re.findall(r"\.unwrap\(\)", src))
    if unwraps > 3:
        issues.append(Issue("warning", ".unwrap() calls without error handling", unwraps))

    todos = len(re.findall(r"\btodo!\s*\(|\bunimplemented!\s*\(", src))
    if todos:
        issues.append(Issue("info", "todo!() / unimplemented!() macros", todos))

    unsafe_blocks = len(re.findall(r"\bunsafe\s*\{", src))
    if unsafe_blocks:
        issues.append(Issue("warning", "unsafe blocks", unsafe_blocks))

    panics = len(re.findall(r"\bpanic!\s*\(", src))
    if panics:
        issues.append(Issue("info", "panic!() calls", panics))

    return FileResult(
        filename=sf.path, language="Rust",
        metrics=metrics, issues=issues,
        score=_score_from_issues(issues, metrics.lines_of_code),
    )


# ---------------------------------------------------------------------------
# Swift / Kotlin stubs (structural only)
# ---------------------------------------------------------------------------

def _analyze_swift(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("//", "/*"))
    issues: list[Issue] = []

    force_unwrap = len(re.findall(r"\w+!\s*[\.\(]", src))
    if force_unwrap:
        issues.append(Issue("warning", "Force unwrap (!) usage", force_unwrap))
    if len(re.findall(r"\bprint\s*\(", src)) > 2:
        issues.append(Issue("info", "print() debug statements", len(re.findall(r"\bprint\s*\(", src))))

    return FileResult(filename=sf.path, language="Swift", metrics=metrics, issues=issues,
                      score=_score_from_issues(issues, metrics.lines_of_code))


def _analyze_kotlin(sf: SourceFile) -> FileResult:
    src = sf.content
    lines = src.splitlines()
    metrics = _base_metrics(lines, ("//", "/*"))
    issues: list[Issue] = []

    force_non_null = len(re.findall(r"\w+!!\.", src))
    if force_non_null:
        issues.append(Issue("warning", "Non-null assertion (!!) usage", force_non_null))
    if len(re.findall(r"\bprintln\s*\(", src)) > 2:
        issues.append(Issue("info", "println() debug statements", len(re.findall(r"\bprintln\s*\(", src))))

    return FileResult(filename=sf.path, language="Kotlin", metrics=metrics, issues=issues,
                      score=_score_from_issues(issues, metrics.lines_of_code))


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

def _dispatch(sf: SourceFile) -> FileResult:
    ext = sf.path.rsplit(".", 1)[-1].lower() if "." in sf.path else ""
    dispatch = {
        "py":   _analyze_python,
        "js":   lambda f: _analyze_javascript(f, is_ts=False),
        "jsx":  lambda f: _analyze_javascript(f, is_ts=False),
        "ts":   lambda f: _analyze_javascript(f, is_ts=True),
        "tsx":  lambda f: _analyze_javascript(f, is_ts=True),
        "java": _analyze_java,
        "c":    lambda f: _analyze_c(f, is_cpp=False),
        "h":    lambda f: _analyze_c(f, is_cpp=False),
        "cpp":  lambda f: _analyze_c(f, is_cpp=True),
        "hpp":  lambda f: _analyze_c(f, is_cpp=True),
        "cc":   lambda f: _analyze_c(f, is_cpp=True),
        "cs":   _analyze_csharp,
        "sql":  _analyze_sql,
        "html": _analyze_html,
        "htm":  _analyze_html,
        "css":  _analyze_css,
        "scss": _analyze_css,
        "sass": _analyze_css,
        "go":   _analyze_go,
        "php":  _analyze_php,
        "rs":   _analyze_rust,
        "swift":_analyze_swift,
        "kt":   _analyze_kotlin,
        "rb":   lambda f: FileResult(f.path, "Ruby",   _base_metrics(f.content.splitlines(), ("#",)),  [], 80.0),
    }
    fn = dispatch.get(ext)
    if fn:
        try:
            return fn(sf)
        except Exception:
            pass
    # Fallback: basic line count, neutral score
    lines = sf.content.splitlines()
    return FileResult(sf.path, sf.language, _base_metrics(lines, ("#", "//")), [], 75.0)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _aggregate(results: list[FileResult]) -> tuple[list[LanguageSummary], float, list[Issue], list[dict]]:
    by_lang: dict[str, list[FileResult]] = defaultdict(list)
    for r in results:
        by_lang[r.language].append(r)

    summaries: list[LanguageSummary] = []
    for lang, files in sorted(by_lang.items()):
        total_lines = sum(f.metrics.lines_of_code for f in files)
        avg_score   = sum(f.score for f in files) / len(files)
        errors   = sum(i.count for f in files for i in f.issues if i.severity == "error")
        warnings = sum(i.count for f in files for i in f.issues if i.severity == "warning")
        total_iss = sum(len(f.issues) for f in files)
        summaries.append(LanguageSummary(
            language=lang, file_count=len(files),
            total_lines=total_lines, avg_score=round(avg_score, 1),
            total_issues=total_iss, error_count=errors, warning_count=warnings,
        ))

    # Overall score: weighted by LOC
    total_loc = sum(r.metrics.lines_of_code for r in results) or 1
    overall = sum(r.score * (r.metrics.lines_of_code / total_loc) for r in results)
    overall = round(clamp(overall, 0, 100), 1)

    # Top-5 issues: aggregate across all files, rank by severity × count
    issue_totals: dict[str, Issue] = {}
    for r in results:
        for iss in r.issues:
            key = f"{iss.severity}::{iss.message}"
            if key in issue_totals:
                issue_totals[key].count += iss.count
            else:
                issue_totals[key] = Issue(iss.severity, iss.message, iss.count)

    severity_rank = {"error": 3, "warning": 2, "info": 1}
    top5 = sorted(
        issue_totals.values(),
        key=lambda i: (severity_rank.get(i.severity, 0), i.count),
        reverse=True,
    )[:5]

    chart_data = [
        {"language": s.language, "score": s.avg_score, "files": s.file_count,
         "errors": s.error_count, "warnings": s.warning_count}
        for s in summaries
    ]

    return summaries, overall, top5, chart_data


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def analyze_code(data: GitHubData) -> CodeAnalysis:
    """Run all language analyzers over fetched source files."""
    results = [_dispatch(sf) for sf in data.source_files]
    summaries, overall, top5, chart_data = _aggregate(results) if results else ([], 75.0, [], [])

    return CodeAnalysis(
        files=results,
        language_summaries=summaries,
        overall_score=overall if results else 75.0,
        top_issues=top5,
        chart_data=chart_data,
        total_files_analyzed=len(results),
        total_lines_analyzed=sum(r.metrics.lines_of_code for r in results),
    )


# ---------------------------------------------------------------------------
# README analyzer
# ---------------------------------------------------------------------------

# Section regexes — headings are matched case-insensitively; aliases are
# combined into single patterns so "## Getting Started" matches "installation".
_README_SECTIONS: list[tuple[str, str, int]] = [
    # (key, heading pattern, points)
    ("title",          r"^#\s+\S",                                               5),
    ("description",    r"(?:^#{1,3}\s+(?:about|description|overview)\b|^>\s+\S)",5),
    ("installation",   r"^#{1,3}\s+(?:install(?:ation)?|getting[\s\-]started|setup|quick[\s\-]start)\b", 15),
    ("usage",          r"^#{1,3}\s+usage\b",                                     15),
    ("features",       r"^#{1,3}\s+features?\b",                                 10),
    ("screenshots",    r"!\[",                                                    10),
    ("contributing",   r"^#{1,3}\s+contribut(?:ing|e|ions?)\b",                  10),
    ("license",        r"^#{1,3}\s+licen[sc]e\b|!\[.*licen[sc]e.*\]",            10),
    ("badges",         r"!\[(?!.*screenshot).*\]\(https?://",                     5),
    ("api_docs",       r"^#{1,3}\s+api(?:\s+(?:docs?|documentation|reference))?\b", 5),
    ("requirements",   r"^#{1,3}\s+(?:requirements?|prerequisites?|dependencies)\b", 5),
    ("toc",            r"^#{1,3}\s+(?:table\s+of\s+contents?|contents?)\b|\[.*\]\(#", 5),
    ("contact",        r"^#{1,3}\s+(?:contact|support|help|community)\b",         5),
    ("changelog",      r"^#{1,3}\s+(?:change[\s\-]?log|version\s+history|releases?|history)\b", 5),
]

# Weight map: key -> points (used to compute the section score ceiling).
# Scores are already embedded in _README_SECTIONS; this dict lets us look them
# up quickly without iterating the list each time.
_README_WEIGHTS: dict[str, int] = {k: pts for k, _, pts in _README_SECTIONS}

# The description check needs a word-count check, not just a heading match.
_PARA_WORDS_RE = re.compile(r"\b\w{3,}\b")


def analyze_readme(readme_content: str) -> dict:
    """
    Analyse a README for structural completeness and return a scored dict.

    Returns
    -------
    {
      "score": 0-100,
      "word_count": int,
      "sections_found": [str],
      "sections_missing": [str],
      "section_scores": {key: {"found": bool, "points": int, "max_points": int}},
      "word_count_bonus": int,
      "suggestions": [str],
    }
    """
    if not readme_content:
        return {
            "score": 0,
            "word_count": 0,
            "sections_found": [],
            "sections_missing": [k for k, *_ in _README_SECTIONS],
            "section_scores": {
                k: {"found": False, "points": 0, "max_points": pts}
                for k, _, pts in _README_SECTIONS
            },
            "word_count_bonus": 0,
            "suggestions": ["Add a README.md file to the repository."],
        }

    src = readme_content
    src_lower = src.lower()
    word_count = len(_PARA_WORDS_RE.findall(src))

    # --- Description quality: requires a paragraph with >50 words after any
    #     heading that looks like a description, OR the opening paragraph.
    has_long_description = False
    paragraphs = re.split(r"\n{2,}", src)
    for para in paragraphs[:5]:          # check first 5 paragraphs
        if len(_PARA_WORDS_RE.findall(para)) >= 50:
            has_long_description = True
            break

    section_scores: dict[str, dict] = {}
    found: list[str] = []
    missing: list[str] = []

    for key, pattern, pts in _README_SECTIONS:
        flags = re.IGNORECASE | re.MULTILINE

        # Screenshots/badges are detected by the presence of markdown image
        # syntax anywhere in the doc, not just at headings.
        if key in ("screenshots", "badges"):
            matched = bool(re.search(pattern, src, re.IGNORECASE))
        elif key == "description":
            # Heading OR a long opening paragraph
            matched = bool(re.search(pattern, src, flags)) or has_long_description
        else:
            matched = bool(re.search(pattern, src, flags))

        awarded = pts if matched else 0
        section_scores[key] = {"found": matched, "points": awarded, "max_points": pts}
        (found if matched else missing).append(key)

    # --- Word-count bonus ---
    bonus = 0
    if word_count > 500:
        bonus = 10
    elif word_count > 200:
        bonus = 5

    raw_score = sum(v["points"] for v in section_scores.values()) + bonus
    score = round(clamp(raw_score, 0, 100), 1)

    # --- Suggestions ---
    suggestions: list[str] = []
    priority_order = [
        ("installation",  "Add an Installation / Getting Started section with step-by-step setup instructions."),
        ("usage",         "Add a Usage section with code examples showing how to use the project."),
        ("description",   "Expand the project description to at least 50 words explaining what it does and why."),
        ("license",       "Add a License section or badge so users know how they can use the code."),
        ("features",      "Add a Features section highlighting what makes this project useful."),
        ("contributing",  "Add a Contributing section or CONTRIBUTING.md to welcome contributors."),
        ("screenshots",   "Add screenshots or a demo GIF so visitors can see the project in action."),
        ("badges",        "Add status badges (build, coverage, license) near the top of the README."),
        ("api_docs",      "Document the public API surface in an API Reference section."),
        ("requirements",  "List prerequisites / system requirements so users know what they need."),
        ("toc",           "Add a Table of Contents for easier navigation (README is growing long)."),
        ("contact",       "Add a Contact / Support section so users know where to get help."),
        ("changelog",     "Add a Changelog section or link to CHANGELOG.md to track version history."),
    ]
    for key, suggestion in priority_order:
        if key in missing:
            suggestions.append(suggestion)

    return {
        "score": score,
        "word_count": word_count,
        "sections_found": found,
        "sections_missing": missing,
        "section_scores": section_scores,
        "word_count_bonus": bonus,
        "suggestions": suggestions[:5],   # top-5 most impactful
    }


# ---------------------------------------------------------------------------
# Project structure analyzer
# ---------------------------------------------------------------------------

# Each rule: (key, display_label, points, category, match_fn)
# match_fn receives the normalised path set and returns bool.

def _any_match(paths: set[str], *patterns: str) -> bool:
    """True if any path starts with or equals any of the given patterns."""
    for path in paths:
        for pat in patterns:
            if path == pat or path.startswith(pat + "/") or path.startswith(pat + "\\"):
                return True
    return False


def _root_file(paths: set[str], *names: str) -> bool:
    """True if any of *names* appears as a root-level file (no directory separator)."""
    return any(n in paths for n in names)


_STRUCTURE_RULES: list[tuple[str, str, int, str, object]] = [
    # Essential files (10 pts each)
    ("readme",        "README.md / README",             10, "essential",
     lambda p: _root_file(p, "readme.md", "readme.rst", "readme.txt", "readme")),
    ("license",       "LICENSE / LICENSE.md",            10, "essential",
     lambda p: _root_file(p, "license", "license.md", "license.txt", "license.rst",
                            "licence", "copying")),
    ("gitignore",     ".gitignore",                      10, "essential",
     lambda p: _root_file(p, ".gitignore")),
    ("dep_file",      "Dependency manifest (requirements.txt / package.json / …)", 10, "essential",
     lambda p: _root_file(p, "requirements.txt", "package.json", "pom.xml",
                            "go.mod", "cargo.toml", "gemfile", "pipfile",
                            "pyproject.toml", "build.gradle", "build.gradle.kts")),

    # Good practice (7 pts each)
    ("env_example",   ".env.example / .env.sample",      7, "good_practice",
     lambda p: _root_file(p, ".env.example", ".env.sample", ".env.template")),
    ("contributing",  "CONTRIBUTING.md",                  7, "good_practice",
     lambda p: _root_file(p, "contributing.md", "contributing.rst")),
    ("changelog",     "CHANGELOG.md / CHANGELOG",         7, "good_practice",
     lambda p: _root_file(p, "changelog.md", "changelog", "changelog.txt",
                            "changelog.rst", "history.md", "history")),
    ("docker",        "Dockerfile / docker-compose.yml",  7, "good_practice",
     lambda p: _root_file(p, "dockerfile", "docker-compose.yml", "docker-compose.yaml",
                            "compose.yml", "compose.yaml")),
    ("editorconfig",  ".editorconfig",                    7, "good_practice",
     lambda p: _root_file(p, ".editorconfig")),

    # CI/CD (5 pts each)
    ("github_actions","GitHub Actions (.github/workflows/)", 5, "ci_cd",
     lambda p: any(path.startswith(".github/workflows/") or path.startswith(".github\\workflows\\") for path in p)),
    ("travis",        ".travis.yml",                     5, "ci_cd",
     lambda p: _root_file(p, ".travis.yml")),
    ("jenkins",       "Jenkinsfile",                     5, "ci_cd",
     lambda p: _root_file(p, "jenkinsfile")),
    ("circleci",      ".circleci/config.yml",            5, "ci_cd",
     lambda p: any(path.startswith(".circleci/") for path in p)),
    ("gitlab_ci",     ".gitlab-ci.yml",                  5, "ci_cd",
     lambda p: _root_file(p, ".gitlab-ci.yml")),
    ("azure_pipelines","azure-pipelines.yml",            5, "ci_cd",
     lambda p: _root_file(p, "azure-pipelines.yml")),

    # Testing (5 pts each)
    ("tests_dir",     "tests/ or test/ directory",        5, "testing",
     lambda p: _any_match(p, "tests", "test")),
    ("js_tests",      "__tests__/ directory (JS)",        5, "testing",
     lambda p: _any_match(p, "__tests__")),
    ("spec_dir",      "spec/ directory (Ruby/RSpec)",     5, "testing",
     lambda p: _any_match(p, "spec")),

    # Documentation (3 pts each)
    ("docs_dir",      "docs/ or doc/ directory",          3, "documentation",
     lambda p: _any_match(p, "docs", "doc", "documentation")),
    ("wiki_dir",      "wiki/ directory",                  3, "documentation",
     lambda p: _any_match(p, "wiki")),
    ("extra_md",      "Additional .md files beyond README", 3, "documentation",
     lambda p: sum(1 for path in p if path.endswith(".md") and
                   not path.startswith("readme")) > 0),

    # Code organisation (5 pts each)
    ("src_dir",       "src/ source directory",            5, "code_organisation",
     lambda p: _any_match(p, "src", "lib", "source", "app")),
    ("mvc_pattern",   "MVC pattern (models/, views/, controllers/)", 5, "code_organisation",
     lambda p: sum(1 for d in ("models", "views", "controllers") if _any_match(p, d)) >= 2),
]

# Maximum raw score across all rules
_STRUCTURE_MAX_RAW: int = sum(pts for _, _, pts, _, _ in _STRUCTURE_RULES)


def analyze_structure(file_list: list) -> dict:
    """
    Score a repository's file/directory structure for best-practice completeness.

    *file_list* accepts either:
      - list of path strings  ("src/main.py", ".gitignore", …)
      - list of dicts with a "path" key (GitHub API git-tree items)

    Returns
    -------
    {
      "score": 0-100,
      "raw_score": int,
      "max_possible": int,
      "found": {key: label},
      "missing": {key: label},
      "by_category": {
          category: {"found": [...], "missing": [...], "score": int, "max_score": int}
      },
      "suggestions": [str],
    }
    """
    # Normalise to a flat set of lowercase paths
    paths: set[str] = set()
    for item in file_list:
        if isinstance(item, dict):
            raw = item.get("path") or item.get("name") or ""
        else:
            raw = str(item)
        paths.add(raw.lower().lstrip("/"))

    found_keys: dict[str, str] = {}
    missing_keys: dict[str, str] = {}
    by_category: dict[str, dict] = {}

    for key, label, pts, category, match_fn in _STRUCTURE_RULES:
        if category not in by_category:
            by_category[category] = {"found": [], "missing": [], "score": 0, "max_score": 0}
        by_category[category]["max_score"] += pts

        try:
            matched = match_fn(paths)
        except Exception:
            matched = False

        if matched:
            found_keys[key] = label
            by_category[category]["found"].append({"key": key, "label": label, "points": pts})
            by_category[category]["score"] += pts
        else:
            missing_keys[key] = label
            by_category[category]["missing"].append({"key": key, "label": label, "points": pts})

    raw_score = sum(pts for key, label, pts, cat, _ in _STRUCTURE_RULES if key in found_keys)

    # Scale to 0-100, cap at 100
    scaled = round(clamp(raw_score / _STRUCTURE_MAX_RAW * 100, 0, 100), 1)

    # --- Prioritised suggestions ---
    _SUGGESTIONS: dict[str, str] = {
        "readme":         "Add a README.md file — it's the first thing visitors see.",
        "license":        "Add a LICENSE file so users know the terms under which they can use your code.",
        "gitignore":      "Add a .gitignore to prevent committing build artefacts, secrets, and IDE files.",
        "dep_file":       "Add a dependency manifest (requirements.txt, package.json, go.mod, etc.).",
        "github_actions": "Set up GitHub Actions CI/CD in .github/workflows/ for automated testing.",
        "tests_dir":      "Create a tests/ directory and add automated tests to improve confidence.",
        "contributing":   "Add a CONTRIBUTING.md to make it easier for others to contribute.",
        "env_example":    "Add a .env.example listing all required environment variables.",
        "docker":         "Add a Dockerfile or docker-compose.yml for reproducible deployments.",
        "changelog":      "Add a CHANGELOG.md to track version history and communicate changes.",
        "docs_dir":       "Create a docs/ directory for detailed documentation beyond the README.",
        "editorconfig":   "Add a .editorconfig to enforce consistent coding style across editors.",
        "src_dir":        "Organise source code in a src/ or app/ directory for clarity.",
        "mvc_pattern":    "Adopt a standard directory structure (models/, views/, controllers/) for maintainability.",
    }

    suggestions = [
        _SUGGESTIONS[key]
        for key in _SUGGESTIONS
        if key in missing_keys
    ][:5]

    return {
        "score": scaled,
        "raw_score": raw_score,
        "max_possible": _STRUCTURE_MAX_RAW,
        "found": found_keys,
        "missing": missing_keys,
        "by_category": by_category,
        "suggestions": suggestions,
    }


def compute_score(
    data: GitHubData,
    code_analysis: CodeAnalysis | None = None,
    readme_analysis: dict | None = None,
    structure_analysis: dict | None = None,
) -> dict:
    """
    Score a repository across six dimensions (0-100 each).

    When the optional analysis dicts are provided the relevant dimensions are
    driven by real measured data instead of heuristic file-presence flags.
    """
    scores: dict[str, float] = {}
    fp: FilePresence = data.file_presence

    # ------------------------------------------------------------------
    # 1. Documentation (25%)
    #    Prefer README analysis score when available; fall back to heuristic.
    # ------------------------------------------------------------------
    if readme_analysis:
        # readme score is 0-100; augment with structure signals
        doc = readme_analysis["score"]
        if fp.license:     doc = clamp(doc + 5, 0, 100)
        if fp.env_example: doc = clamp(doc + 3, 0, 100)
        if fp.docs_dir:    doc = clamp(doc + 5, 0, 100)
        if structure_analysis:
            struct_score = structure_analysis.get("score", 0)
            # Small blending bonus for having good project structure alongside docs
            doc = clamp(doc * 0.85 + struct_score * 0.15, 0, 100)
    else:
        doc = 0.0
        readme = data.readme
        if readme:
            doc += clamp(len(readme) / 30, 0, 40)
            markers = ["##", "installation", "usage", "license", "contributing",
                       "getting started", "quick start", "example"]
            doc += sum(12 for m in markers if m.lower() in readme.lower())
        if fp.license:      doc += 10
        if fp.env_example:  doc += 5
        if fp.docs_dir:     doc += 10
    scores["documentation"] = clamp(doc, 0, 100)

    # ------------------------------------------------------------------
    # 2. Activity (20%)
    # ------------------------------------------------------------------
    scores["activity"] = clamp(len(data.commits) * 3, 0, 100)

    # ------------------------------------------------------------------
    # 3. Popularity (15%)
    # ------------------------------------------------------------------
    scores["popularity"] = clamp((data.repo.stars * 0.6 + data.repo.forks * 1.5) / 10, 0, 100)

    # ------------------------------------------------------------------
    # 4. Community (15%)
    # ------------------------------------------------------------------
    scores["community"] = clamp(
        len(data.contributors) * 10 + (15 if fp.github_actions else 0), 0, 100
    )

    # ------------------------------------------------------------------
    # 5. Code quality (15%)
    #    Driven by static analysis when available; structure score adds a bonus.
    # ------------------------------------------------------------------
    struct_bonus = 0
    if structure_analysis:
        # Scale structure score (0-100) to a max 20-point bonus
        struct_bonus = round(structure_analysis.get("score", 0) * 0.20, 1)

    if code_analysis and code_analysis.total_files_analyzed > 0:
        presence_bonus = sum([
            fp.tests_dir * 10, fp.ci_files * 10,
            fp.gitignore * 5, fp.dockerfile * 5,
        ])
        scores["code_quality"] = clamp(
            code_analysis.overall_score * 0.70 + presence_bonus + struct_bonus, 0, 100
        )
    else:
        lang_diversity = clamp(len(data.languages) * 10, 0, 40)
        presence_score = sum([
            fp.tests_dir * 25, fp.src_dir * 15, fp.ci_files * 15,
            fp.dockerfile * 10, fp.setup_py * 10, fp.pyproject_toml * 10, fp.gitignore * 5,
        ])
        scores["code_quality"] = clamp(lang_diversity + presence_score + struct_bonus, 0, 100)

    # ------------------------------------------------------------------
    # 6. Maintenance (10%)
    # ------------------------------------------------------------------
    oi = data.repo.open_issues
    scores["maintenance"] = 90.0 if oi == 0 else clamp(100 - oi * 2, 20, 100)

    # ------------------------------------------------------------------
    # Weighted total
    # ------------------------------------------------------------------
    weights = {
        "documentation": 0.25, "activity": 0.20, "popularity": 0.15,
        "community": 0.15, "code_quality": 0.15, "maintenance": 0.10,
    }
    total = sum(scores[k] * weights[k] for k in weights)

    result: dict = {
        "dimensions": {k: round(v, 1) for k, v in scores.items()},
        "total": round(total, 1),
    }

    # ------------------------------------------------------------------
    # Embed sub-analyses into the score payload for the frontend
    # ------------------------------------------------------------------
    if readme_analysis:
        result["readme_analysis"] = readme_analysis

    if structure_analysis:
        result["structure_analysis"] = structure_analysis

    if code_analysis:
        result["code_analysis"] = {
            "overall_score": code_analysis.overall_score,
            "files_analyzed": code_analysis.total_files_analyzed,
            "lines_analyzed": code_analysis.total_lines_analyzed,
            "top_issues": [
                {"severity": i.severity, "message": i.message, "count": i.count}
                for i in code_analysis.top_issues
            ],
            "by_language": [
                {
                    "language": s.language,
                    "file_count": s.file_count,
                    "total_lines": s.total_lines,
                    "avg_score": s.avg_score,
                    "errors": s.error_count,
                    "warnings": s.warning_count,
                }
                for s in code_analysis.language_summaries
            ],
            "chart_data": code_analysis.chart_data,
            "files": [
                {
                    "filename": f.filename,
                    "language": f.language,
                    "metrics": {
                        "lines_of_code": f.metrics.lines_of_code,
                        "blank_lines": f.metrics.blank_lines,
                        "comment_lines": f.metrics.comment_lines,
                        "code_lines": f.metrics.code_lines,
                    },
                    "issues": [
                        {"severity": i.severity, "message": i.message, "count": i.count}
                        for i in f.issues
                    ],
                    "score": f.score,
                }
                for f in code_analysis.files
            ],
        }

    return result
