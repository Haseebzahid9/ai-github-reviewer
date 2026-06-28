"""
Generate a professional project report Word document for AI GitHub Reviewer.
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

# ── Color palette ──────────────────────────────────────────────────────────
VIOLET      = RGBColor(0x7C, 0x5C, 0xFC)
DARK_BG     = RGBColor(0x0F, 0x11, 0x17)
DARK_CARD   = RGBColor(0x1E, 0x23, 0x33)
DARK_BORDER = RGBColor(0x2A, 0x30, 0x47)
MUTED       = RGBColor(0x88, 0x92, 0xA4)
TEXT        = RGBColor(0x1E, 0x23, 0x33)
SUCCESS     = RGBColor(0x22, 0xD3, 0xA5)
WARNING     = RGBColor(0xF5, 0x9E, 0x0B)
DANGER      = RGBColor(0xF4, 0x60, 0x6C)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY  = RGBColor(0xF5, 0xF5, 0xF7)
DARK_GRAY   = RGBColor(0x44, 0x44, 0x55)
ACCENT_LT   = RGBColor(0xA7, 0x8B, 0xFA)

doc = Document()

# ── Page margins ───────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin   = Cm(2.5)
    section.right_margin  = Cm(2.5)

# ── Helper functions ────────────────────────────────────────────────────────

def set_cell_bg(cell, hex_color: str):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)

def set_cell_borders(cell, color="CCCCCC", size="4"):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        border = OxmlElement(f"w:{side}")
        border.set(qn("w:val"),   "single")
        border.set(qn("w:sz"),    size)
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), color)
        tcBorders.append(border)
    tcPr.append(tcBorders)

def add_heading(text, level=1, color=None, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=14, space_after=6):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after  = Pt(space_after)
    run = p.add_run(text)
    sizes = {1: 22, 2: 16, 3: 13, 4: 11}
    run.font.size = Pt(sizes.get(level, 12))
    run.font.bold = True
    if color:
        run.font.color.rgb = color
    else:
        run.font.color.rgb = TEXT
    return p

def add_body(text, bold=False, italic=False, color=None, size=10.5, space_after=4, align=WD_ALIGN_PARAGRAPH.LEFT):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after  = Pt(space_after)
    p.paragraph_format.space_before = Pt(2)
    run = p.add_run(text)
    run.font.size   = Pt(size)
    run.font.bold   = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = color
    return p

def add_bullet(text, color=None, indent=0.4):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent   = Inches(indent)
    p.paragraph_format.space_after   = Pt(3)
    p.paragraph_format.space_before  = Pt(1)
    run = p.add_run(text)
    run.font.size = Pt(10)
    if color:
        run.font.color.rgb = color
    return p

def add_divider():
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    pPr  = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),   "single")
    bottom.set(qn("w:sz"),    "4")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "D0D0E0")
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p

def add_colored_box(text, bg_hex="F0EFFE", border_hex="C4B5FD", text_color=None):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0)
    set_cell_bg(cell, bg_hex)
    set_cell_borders(cell, color=border_hex, size="6")
    cell.width = Inches(6.0)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(6)
    p.paragraph_format.left_indent  = Pt(8)
    run = p.add_run(text)
    run.font.size = Pt(10)
    if text_color:
        run.font.color.rgb = text_color
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

def make_table(headers, rows, header_bg="2D3047", alt_bg="F8F8FC"):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    hdr = t.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        set_cell_bg(cell, header_bg)
        p    = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run  = p.add_run(h)
        run.font.size  = Pt(9.5)
        run.font.bold  = True
        run.font.color.rgb = WHITE

    # Data rows
    for ri, row in enumerate(rows):
        tr = t.rows[ri + 1]
        bg = alt_bg if ri % 2 == 0 else "FFFFFF"
        for ci, val in enumerate(row):
            cell = tr.cells[ci]
            set_cell_bg(cell, bg)
            p    = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run  = p.add_run(str(val))
            run.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


# ════════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ════════════════════════════════════════════════════════════════════════════

# Title block
doc.add_paragraph().paragraph_format.space_after = Pt(30)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(40)
p.paragraph_format.space_after  = Pt(6)
r = p.add_run("AI GITHUB PROJECT REVIEWER")
r.font.size  = Pt(28)
r.font.bold  = True
r.font.color.rgb = VIOLET

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
p2.paragraph_format.space_after = Pt(4)
r2 = p2.add_run("Project Report & Technical Documentation")
r2.font.size  = Pt(14)
r2.font.color.rgb = DARK_GRAY
r2.font.italic = True

add_divider()

# Meta box
t = doc.add_table(rows=5, cols=2)
t.alignment = WD_TABLE_ALIGNMENT.CENTER
meta = [
    ("Author",      "Haseeb Raza"),
    ("GitHub",      "github.com/Haseebzahid9"),
    ("LinkedIn",    "linkedin.com/in/haseebraza4998"),
    ("Email",       "haseebzahid4998@gmail.com"),
    ("Report Date", datetime.date.today().strftime("%B %d, %Y")),
]
for i, (k, v) in enumerate(meta):
    row = t.rows[i]
    set_cell_bg(row.cells[0], "EEEEFF")
    set_cell_bg(row.cells[1], "FAFAFA")
    p0 = row.cells[0].paragraphs[0]
    p1 = row.cells[1].paragraphs[0]
    r0 = p0.add_run(k)
    r0.font.size = Pt(10); r0.font.bold = True; r0.font.color.rgb = VIOLET
    r1 = p1.add_run(v)
    r1.font.size = Pt(10); r1.font.color.rgb = TEXT

doc.add_paragraph().paragraph_format.space_after = Pt(10)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Powered by  Google Gemini AI  ·  FastAPI  ·  React 18  ·  Tailwind CSS")
r.font.size  = Pt(10)
r.font.color.rgb = MUTED
r.font.italic = True

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 1. PROJECT OVERVIEW
# ════════════════════════════════════════════════════════════════════════════

add_heading("1.  Project Overview", 1, VIOLET, space_before=4)
add_divider()

add_body(
    "AI GitHub Project Reviewer is a full-stack web application that analyses the quality of any public "
    "GitHub repository and delivers a structured, data-dense report in under 60 seconds. The user pastes "
    "a repository URL and receives a weighted score across five dimensions — Project Structure, "
    "Documentation, Code Quality, Security, and AI Assessment — alongside a full Gemini AI narrative, "
    "per-language static analysis, README grading, and a downloadable PDF report."
)

add_body(
    "The application is targeted at developers evaluating open-source dependencies, hiring managers "
    "auditing candidate portfolios, and engineers conducting pre-integration due diligence on third-party "
    "codebases."
)

add_heading("Key Highlights", 2, TEXT, space_before=10)
highlights = [
    "Instant 0–100 quality score with letter grade (A+ to F)",
    "Five weighted scoring dimensions with transparent breakdown",
    "Static analysis across 14+ programming languages",
    "14-section README quality checker",
    "Security anti-pattern detection (hardcoded secrets, injection risks, eval() usage)",
    "Google Gemini AI review: strengths, weaknesses, next steps",
    "Downloadable 6-page PDF report via ReportLab",
    "Full review history stored in SQLite with delete support",
    "Graceful degradation — works without Gemini API key",
    "Responsive dark-theme dashboard built with React 18 + Tailwind CSS",
]
for h in highlights:
    add_bullet(h, color=DARK_GRAY)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 2. TECH STACK
# ════════════════════════════════════════════════════════════════════════════

add_heading("2.  Technology Stack", 1, VIOLET, space_before=4)
add_divider()

add_heading("2.1  Backend", 2, TEXT, space_before=10)
make_table(
    ["Package", "Version", "Purpose"],
    [
        ["FastAPI",              "≥ 0.115",  "Async REST API framework"],
        ["Uvicorn",              "≥ 0.30",   "ASGI server"],
        ["SQLAlchemy + aiosqlite","≥ 2.0",   "Async ORM with SQLite"],
        ["httpx",                "≥ 0.27",   "Async HTTP client for GitHub API"],
        ["google-genai",         "≥ 1.0",    "Official Google Gemini SDK"],
        ["ReportLab",            "≥ 4.2",    "PDF report generation"],
        ["Pydantic v2",          "≥ 2.10",   "Request / response validation"],
        ["python-dotenv",        "≥ 1.0",    "Environment variable loading"],
        ["Python",               "3.10+",    "Runtime (3.14 confirmed working)"],
    ]
)

add_heading("2.2  Frontend", 2, TEXT, space_before=10)
make_table(
    ["Package", "Version", "Purpose"],
    [
        ["React",           "18",    "UI framework"],
        ["Vite",            "5",     "Build tool with HMR"],
        ["Tailwind CSS",    "3",     "Utility-first styling"],
        ["React Router DOM","6",     "Client-side routing"],
        ["Recharts",        "2",     "Language distribution donut chart"],
        ["Axios",           "1",     "HTTP client with error interceptor"],
        ["Inter (Google Fonts)", "—","Primary typeface"],
    ]
)

add_heading("2.3  Infrastructure & Deployment", 2, TEXT, space_before=10)
make_table(
    ["Service", "Role"],
    [
        ["GitHub",  "Source repository — github.com/Haseebzahid9/ai-github-reviewer"],
        ["Render",  "Backend deployment (Procfile + render.yaml pre-configured)"],
        ["Vercel",  "Frontend deployment (vercel.json SPA rewrites + API proxy)"],
        ["SQLite",  "Local persistence for review history (zero-setup)"],
    ]
)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 3. ARCHITECTURE
# ════════════════════════════════════════════════════════════════════════════

add_heading("3.  System Architecture", 1, VIOLET, space_before=4)
add_divider()

add_heading("3.1  High-Level Flow", 2, TEXT, space_before=10)
add_body("The application follows a clean client–server architecture:")

steps = [
    "1.  User enters a GitHub URL in the React frontend.",
    "2.  Frontend sends POST /api/review to the FastAPI backend.",
    "3.  Backend validates the URL and calls the GitHub REST API to fetch: repo metadata, file tree, README, and up to 20 source files.",
    "4.  Analyzer services run multi-language static analysis, README grading, and project-structure checks synchronously.",
    "5.  Gemini AI review is requested asynchronously (degraded gracefully on failure).",
    "6.  A weighted final score is computed and the full report is persisted to SQLite.",
    "7.  The JSON report is returned to the frontend and rendered as a data-dense dashboard.",
    "8.  User can download a 6-page PDF or revisit the report via the History page.",
]
for s in steps:
    add_bullet(s, color=DARK_GRAY)

add_heading("3.2  Project Structure", 2, TEXT, space_before=12)
add_colored_box(
    "ai-github-reviewer/\n"
    "├── backend/\n"
    "│   ├── app/\n"
    "│   │   ├── main.py              # FastAPI app, CORS, middleware\n"
    "│   │   ├── models/database.py   # SQLAlchemy models + async migrations\n"
    "│   │   ├── routers/review.py    # All API endpoints\n"
    "│   │   ├── services/\n"
    "│   │   │   ├── github.py        # GitHub REST API client\n"
    "│   │   │   ├── analyzer.py      # Multi-language static analyzer\n"
    "│   │   │   ├── gemini.py        # Google Gemini AI integration\n"
    "│   │   │   ├── report.py        # Score aggregation + SQLite persistence\n"
    "│   │   │   └── pdf_report.py    # 6-page PDF generator (ReportLab)\n"
    "│   │   └── utils/\n"
    "│   │       ├── helpers.py       # Score calculation helpers\n"
    "│   │       └── validators.py    # GitHub URL validation\n"
    "│   ├── tests/test_review.py     # 25 pytest unit tests\n"
    "│   ├── .env.example             # Environment variable template\n"
    "│   ├── requirements.txt\n"
    "│   ├── Procfile                 # Render deployment config\n"
    "│   └── render.yaml\n"
    "│\n"
    "├── frontend/\n"
    "│   ├── src/\n"
    "│   │   ├── App.jsx              # Router, navbar, toast context\n"
    "│   │   ├── pages/\n"
    "│   │   │   ├── Home.jsx         # Hero + repo input + progress loader\n"
    "│   │   │   ├── Dashboard.jsx    # Full report dashboard (8 sections)\n"
    "│   │   │   ├── History.jsx      # Saved reports table\n"
    "│   │   │   └── About.jsx        # Scoring methodology explained\n"
    "│   │   ├── components/          # Shared UI components\n"
    "│   │   ├── services/api.js      # Axios client + error interceptor\n"
    "│   │   └── hooks/useToasts.js\n"
    "│   ├── tailwind.config.js\n"
    "│   ├── vite.config.js\n"
    "│   └── vercel.json\n"
    "│\n"
    "├── .gitignore\n"
    "├── LICENSE                      # MIT\n"
    "└── README.md                    # 466-line professional readme",
    bg_hex="F2F2FA", border_hex="C4B5FD"
)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 4. FEATURES
# ════════════════════════════════════════════════════════════════════════════

add_heading("4.  Features & Functionality", 1, VIOLET, space_before=4)
add_divider()

features = [
    ("5-Dimension Scoring",
     "Structure (20%) · Documentation (20%) · Code Quality (30%) · Security (15%) · AI Assessment (15%). "
     "Each dimension is calculated independently and combined into a single weighted 0–100 score."),
    ("14+ Language Support",
     "Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, PHP, Swift, Kotlin, Ruby, SQL, HTML, CSS. "
     "Per-language issue detection with error/warning/info severity levels."),
    ("Static Code Analysis",
     "Per-file issue detection. Issues are counted and density-normalised per 100 LOC to produce a fair "
     "per-language score regardless of file size."),
    ("README Grading",
     "14-section checklist: title, description, badges, installation, usage, screenshots, contributing, "
     "license, code of conduct, changelog, FAQ, roadmap, contact, and examples."),
    ("Security Detection",
     "Keyword-matched anti-patterns including hardcoded API keys, SQL injection risks, eval() usage, "
     "deprecated API calls, and missing Subresource Integrity (SRI) attributes."),
    ("File Structure Analysis",
     "22 rules checking for the presence of CI configs (GitHub Actions, CircleCI, Travis), Dockerfile, "
     ".gitignore, test directories, package manifests, and documentation files."),
    ("Google Gemini AI Review",
     "Project overview, tech-stack assessment, strengths list, weaknesses list, security suggestions, "
     "performance suggestions, maintainability suggestions, beginner-friendliness score, "
     "production-readiness score, and actionable next steps."),
    ("PDF Export",
     "Full 6-page formatted report generated server-side with ReportLab. Downloaded via a single button click."),
    ("Review History",
     "All reports persisted to SQLite via SQLAlchemy async ORM. Viewable and deletable from the History page."),
    ("Graceful Degradation",
     "If the Gemini API key is absent or the AI call fails, the application continues to function. "
     "The AI Review section displays a fallback notice instead of crashing."),
]

for title, desc in features:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after  = Pt(3)
    p.paragraph_format.left_indent  = Inches(0.2)
    r1 = p.add_run(f"{title}:  ")
    r1.font.bold = True
    r1.font.size = Pt(10.5)
    r1.font.color.rgb = VIOLET
    r2 = p.add_run(desc)
    r2.font.size = Pt(10)
    r2.font.color.rgb = DARK_GRAY

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 5. SCORING SYSTEM
# ════════════════════════════════════════════════════════════════════════════

add_heading("5.  Scoring System", 1, VIOLET, space_before=4)
add_divider()

add_heading("5.1  Dimension Weights", 2, TEXT, space_before=10)
make_table(
    ["Dimension", "Weight", "Measurement Approach"],
    [
        ["Project Structure",  "20%", "22 file-presence and organisation rules"],
        ["Documentation",      "20%", "README completeness across 14 sections"],
        ["Code Quality",       "30%", "Issues per 100 LOC, density-normalised per language"],
        ["Security",           "15%", "Keyword-matched anti-patterns in analyzed source files"],
        ["AI Assessment",      "15%", "Google Gemini holistic quality score (0–10 → 0–100)"],
    ]
)

add_heading("5.2  Grade Thresholds", 2, TEXT, space_before=10)
make_table(
    ["Grade", "Score Range", "Meaning"],
    [
        ["A+", "90 – 100", "Excellent — production-ready quality"],
        ["A",  "80 – 89",  "Very Good"],
        ["B+", "70 – 79",  "Good"],
        ["B",  "60 – 69",  "Above Average"],
        ["C+", "50 – 59",  "Average"],
        ["C",  "40 – 49",  "Below Average"],
        ["D",  "30 – 39",  "Needs significant improvement"],
        ["F",  "0 – 29",   "Major issues detected"],
    ]
)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 6. API REFERENCE
# ════════════════════════════════════════════════════════════════════════════

add_heading("6.  API Reference", 1, VIOLET, space_before=4)
add_divider()
add_body("Base URL (local): http://localhost:8000", bold=True, color=DARK_GRAY)

endpoints = [
    ("POST",   "/api/review",                "Analyse a public GitHub repository. Returns full report JSON."),
    ("GET",    "/api/history",               "List all saved reports, newest first (last 20)."),
    ("GET",    "/api/report/{id}",           "Fetch a full saved report by database ID."),
    ("DELETE", "/api/history/{id}",          "Delete a saved report by ID."),
    ("GET",    "/api/report/{id}/download",  "Download the 6-page PDF report (application/pdf)."),
    ("GET",    "/api/health",                "Service liveness check — returns {status: ok, version: 1.0.0}."),
    ("GET",    "/health",                    "Root health check for load-balancer probes."),
    ("GET",    "/docs",                      "Interactive Swagger UI — auto-generated by FastAPI."),
]

make_table(["Method", "Endpoint", "Description"], endpoints)

add_heading("6.1  POST /api/review — Request Body", 2, TEXT, space_before=10)
add_colored_box(
    '{\n  "repo_url": "https://github.com/owner/repository"\n}',
    bg_hex="F2F2FA", border_hex="C4B5FD"
)

add_heading("6.2  Error Codes", 2, TEXT, space_before=10)
make_table(
    ["HTTP Status", "Code", "Cause"],
    [
        ["400", "INVALID_URL",   "Not a valid GitHub repository URL"],
        ["403", "FORBIDDEN",     "Repository is private"],
        ["404", "NOT_FOUND",     "Repository does not exist"],
        ["429", "RATE_LIMIT",    "GitHub API rate limit reached"],
        ["504", "TIMEOUT",       "Analysis exceeded 60-second pipeline timeout"],
        ["500", "INTERNAL_ERROR","Unexpected server error"],
    ]
)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 7. FRONTEND DESIGN SYSTEM
# ════════════════════════════════════════════════════════════════════════════

add_heading("7.  Frontend Design System", 1, VIOLET, space_before=4)
add_divider()

add_heading("7.1  Design Tokens (CSS Custom Properties)", 2, TEXT, space_before=10)
make_table(
    ["Variable", "Value", "Usage"],
    [
        ["--bg",        "#0f1117", "Page background"],
        ["--surface",   "#181c27", "Navbar / footer / secondary surfaces"],
        ["--card",      "#1e2333", "All card components"],
        ["--border",    "#2a3047", "Borders, dividers, progress tracks"],
        ["--muted",     "#8892a4", "Secondary text, labels, metadata"],
        ["--text",      "#e8ecf4", "Primary text"],
        ["--accent",    "#7c5cfc", "Violet — buttons, icons, rings"],
        ["--accent-lt", "#a78bfa", "Light violet — links, hover states"],
        ["--success",   "#22d3a5", "Green — passing scores, found sections"],
        ["--warning",   "#f59e0b", "Amber — moderate issues"],
        ["--danger",    "#f4606c", "Red — errors, delete actions"],
    ]
)

add_heading("7.2  Component Library", 2, TEXT, space_before=10)
components = [
    (".card",          "Dark card with border-radius 12px and var(--card) background."),
    (".btn-primary",   "Violet accent button with glow shadow on hover, disabled at 45% opacity."),
    (".btn-ghost",     "Transparent button with border, fills var(--surface) on hover."),
    (".section-title", "0.75rem uppercase tracking-wide label used as section headers."),
    (".animate-bar",   "CSS animation for score bars — expands from 0 to var(--bar-width)."),
    (".animate-fade-in","Opacity 0 → 1 entrance animation, 350ms ease-out."),
    (".animate-slide-up","Combined opacity + translateY(12px → 0) entrance animation."),
]
for cls, desc in components:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after  = Pt(2)
    p.paragraph_format.left_indent  = Inches(0.2)
    r1 = p.add_run(f"{cls}  ")
    r1.font.bold = True; r1.font.size = Pt(10); r1.font.color.rgb = VIOLET
    r2 = p.add_run(desc)
    r2.font.size = Pt(10); r2.font.color.rgb = DARK_GRAY

add_heading("7.3  Pages", 2, TEXT, space_before=10)
pages = [
    ("Home (/)","Hero section with animated eyebrow pill, headline, RepoInput component, "
                "step-by-step progress loader during analysis, 6-feature grid."),
    ("Dashboard (/dashboard)","8-section report view: repo header + stats → score ring → language chart → "
                              "file structure tree → README quality → code analysis → AI review → PDF download."),
    ("History (/history)","Sortable table of all saved reports with score badges and per-row delete."),
    ("About (/about)","Scoring methodology documentation with dimension weights and grade thresholds."),
]
make_table(["Page", "Content"], pages)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 8. INSTALLATION GUIDE
# ════════════════════════════════════════════════════════════════════════════

add_heading("8.  Installation & Setup", 1, VIOLET, space_before=4)
add_divider()

add_heading("8.1  Prerequisites", 2, TEXT, space_before=10)
make_table(
    ["Requirement", "Minimum", "Notes"],
    [
        ["Python",  "3.10",  "3.14 confirmed working"],
        ["Node.js", "18",    "20 LTS recommended"],
        ["npm",     "9",     "Bundled with Node.js"],
        ["Git",     "Any",   "—"],
    ]
)
add_body("You also need a GitHub Personal Access Token and a Google Gemini API Key.", color=DARK_GRAY)

add_heading("8.2  Clone & Install", 2, TEXT, space_before=10)
add_colored_box(
    "# 1. Clone the repository\n"
    "git clone https://github.com/Haseebzahid9/ai-github-reviewer.git\n"
    "cd ai-github-reviewer\n\n"
    "# 2. Backend setup\n"
    "cd backend\n"
    "python -m venv .venv\n"
    ".venv\\Scripts\\activate          # Windows\n"
    "# source .venv/bin/activate     # macOS/Linux\n"
    "pip install -r requirements.txt\n"
    "cp .env.example .env             # then fill in your API keys\n\n"
    "# 3. Frontend setup (new terminal)\n"
    "cd frontend\n"
    "npm install",
    bg_hex="F2F2FA", border_hex="C4B5FD"
)

add_heading("8.3  Environment Variables (backend/.env)", 2, TEXT, space_before=10)
make_table(
    ["Variable", "Required", "Default", "Description"],
    [
        ["GITHUB_TOKEN",         "Yes", "—",                                     "GitHub PAT (public_repo scope)"],
        ["GEMINI_API_KEY",       "Yes", "—",                                     "Google Gemini API key"],
        ["DATABASE_URL",         "No",  "sqlite+aiosqlite:///./github_reviewer.db","SQLite DB connection string"],
        ["MAX_FILE_SIZE_KB",     "No",  "150",                                   "Max KB per source file"],
        ["MAX_FILES_TO_ANALYZE", "No",  "20",                                    "Max files per repository"],
        ["CORS_ORIGINS",         "No",  "http://localhost:5173,...",             "Comma-separated allowed origins"],
    ]
)

add_heading("8.4  Running Locally", 2, TEXT, space_before=10)
add_colored_box(
    "# Terminal 1 — Backend (from backend/, venv active)\n"
    "uvicorn app.main:app --reload --host 127.0.0.1 --port 8000\n\n"
    "# Terminal 2 — Frontend (from frontend/)\n"
    "npm run dev\n\n"
    "# Open in browser\n"
    "http://localhost:5173\n\n"
    "# Health check\n"
    'http://localhost:8000/health  →  {"status":"ok","version":"1.0.0"}',
    bg_hex="F2F2FA", border_hex="C4B5FD"
)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 9. TESTING
# ════════════════════════════════════════════════════════════════════════════

add_heading("9.  Testing", 1, VIOLET, space_before=4)
add_divider()

add_body(
    "The backend includes 25 pytest unit tests covering all core logic modules. "
    "Tests are located in backend/tests/test_review.py."
)

add_heading("Test Suites", 2, TEXT, space_before=10)
make_table(
    ["Test Class", "Coverage Area", "Test Count"],
    [
        ["TestValidateGithubUrl",    "GitHub URL format validation (valid/invalid patterns)",   "6"],
        ["TestClamp",                "Score clamping to 0–100 range",                           "4"],
        ["TestCalculateFinalScore",  "Weighted score aggregation with all five dimensions",      "5"],
        ["TestAnalyzeReadme",        "README section detection across 14 categories",            "5"],
        ["TestAnalyzeStructure",     "Project structure rule evaluation (22 rules)",             "3"],
        ["TestParseGithubUrl",       "URL parsing — both full URL and owner/repo shorthand",     "2"],
    ]
)

add_colored_box(
    "cd backend\n"
    ".venv\\Scripts\\activate\n"
    "pip install pytest pytest-asyncio\n"
    "pytest tests/ -v",
    bg_hex="F2F2FA", border_hex="C4B5FD"
)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 10. DEPLOYMENT
# ════════════════════════════════════════════════════════════════════════════

add_heading("10.  Deployment", 1, VIOLET, space_before=4)
add_divider()

add_heading("10.1  Backend — Render", 2, TEXT, space_before=10)
steps_render = [
    "Push repository to GitHub.",
    "Go to render.com → New Web Service.",
    "Connect the repository; set root directory to backend/.",
    "Set Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "Add environment variables: GITHUB_TOKEN and GEMINI_API_KEY.",
    "Click Deploy.",
]
for s in steps_render:
    add_bullet(s, color=DARK_GRAY)

add_body("backend/Procfile and backend/render.yaml are pre-configured and committed to the repository.", italic=True, color=MUTED)

add_heading("10.2  Frontend — Vercel", 2, TEXT, space_before=10)
steps_vercel = [
    "Go to vercel.com → New Project.",
    "Import the GitHub repository; set Root Directory to frontend/.",
    "Add environment variable: VITE_API_URL = your Render backend URL.",
    "Click Deploy.",
]
for s in steps_vercel:
    add_bullet(s, color=DARK_GRAY)

add_body("frontend/vercel.json is pre-configured with SPA rewrites and an API proxy.", italic=True, color=MUTED)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 11. SECURITY CONSIDERATIONS
# ════════════════════════════════════════════════════════════════════════════

add_heading("11.  Security Considerations", 1, VIOLET, space_before=4)
add_divider()

points = [
    ("API Keys never committed",
     "backend/.env is explicitly listed in .gitignore. The repository contains only "
     ".env.example with placeholder values. API keys are loaded exclusively at runtime via python-dotenv."),
    ("CORS restriction",
     "CORS_ORIGINS environment variable restricts allowed origins. In production the Vercel "
     "frontend origin should be the only allowed value. A regex also allows Vercel preview deployments."),
    ("Read-only GitHub Token",
     "Only the public_repo scope is required. No write access is requested or needed."),
    ("Input validation",
     "All GitHub URLs are validated against a strict regex before any HTTP request is made. "
     "owner/repo shorthand is also normalised through the same validator."),
    ("Rate limit protection",
     "RateLimitError from the GitHub API is surfaced as HTTP 429 with a human-readable retry hint."),
    ("No secrets stored",
     "The SQLite database stores only report metadata and JSON payloads. No user credentials, "
     "tokens, or PII are persisted at any point."),
    ("Pipeline timeout",
     "The full review pipeline is wrapped in asyncio.wait_for with a 60-second timeout to prevent "
     "resource exhaustion on very large repositories."),
]

for title, desc in points:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after  = Pt(3)
    p.paragraph_format.left_indent  = Inches(0.2)
    r1 = p.add_run(f"{title}:  ")
    r1.font.bold = True; r1.font.size = Pt(10.5); r1.font.color.rgb = VIOLET
    r2 = p.add_run(desc)
    r2.font.size = Pt(10); r2.font.color.rgb = DARK_GRAY

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 12. KNOWN ISSUES & LIMITATIONS
# ════════════════════════════════════════════════════════════════════════════

add_heading("12.  Known Issues & Limitations", 1, VIOLET, space_before=4)
add_divider()

limitations = [
    "Private repositories are not supported — a GitHub token with full repo access and additional OAuth flow would be required.",
    "Analysis is limited to the first 20 source files (configurable via MAX_FILES_TO_ANALYZE) to keep response times under 60 seconds.",
    "Files larger than 150 KB (configurable via MAX_FILE_SIZE_KB) are skipped to avoid memory pressure.",
    "Gemini AI review is subject to the Google Gemini free-tier rate limits. Heavy usage may trigger temporary degradation.",
    "The SQLite database is local — review history is not shared between deployments or users.",
    "The frontend requires JavaScript to function (React SPA — no server-side rendering).",
    "Browser cache can cause a blank page on first load after a hard refresh. Opening in an Incognito window or clearing cache resolves this.",
]

for lim in limitations:
    add_bullet(lim, color=DARK_GRAY)

add_heading("12.1  Potential Future Improvements", 2, TEXT, space_before=12)
improvements = [
    "OAuth flow for private repository support.",
    "PostgreSQL support for multi-user cloud deployments.",
    "Real-time WebSocket progress streaming instead of client-side timers.",
    "GitHub Actions CI badge generation based on analysis results.",
    "Comparative analysis — score a repo against a baseline or a category average.",
    "Browser extension for one-click analysis from any GitHub page.",
]
for imp in improvements:
    add_bullet(imp, color=DARK_GRAY)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 13. AUTHOR & LICENSE
# ════════════════════════════════════════════════════════════════════════════

add_heading("13.  Author & License", 1, VIOLET, space_before=4)
add_divider()

add_heading("Author", 2, TEXT, space_before=10)
t = doc.add_table(rows=4, cols=2)
t.alignment = WD_TABLE_ALIGNMENT.LEFT
author_meta = [
    ("Name",     "Haseeb Raza"),
    ("GitHub",   "https://github.com/Haseebzahid9"),
    ("LinkedIn", "https://www.linkedin.com/in/haseebraza4998/"),
    ("Email",    "haseebzahid4998@gmail.com"),
]
for i, (k, v) in enumerate(author_meta):
    row = t.rows[i]
    set_cell_bg(row.cells[0], "EEEEFF")
    set_cell_bg(row.cells[1], "FAFAFA")
    r0 = row.cells[0].paragraphs[0].add_run(k)
    r0.font.bold = True; r0.font.size = Pt(10); r0.font.color.rgb = VIOLET
    r1 = row.cells[1].paragraphs[0].add_run(v)
    r1.font.size = Pt(10); r1.font.color.rgb = DARK_GRAY

doc.add_paragraph().paragraph_format.space_after = Pt(8)

add_heading("Repository", 2, TEXT, space_before=10)
add_body("https://github.com/Haseebzahid9/ai-github-reviewer", color=VIOLET)

add_heading("License", 2, TEXT, space_before=10)
add_colored_box(
    "MIT License\n\n"
    "Copyright (c) 2024 Haseeb Raza\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
    "of this software and associated documentation files (the \"Software\"), to deal\n"
    "in the Software without restriction, including without limitation the rights\n"
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
    "copies of the Software, and to permit persons to whom the Software is\n"
    "furnished to do so, subject to the following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all\n"
    "copies or substantial portions of the Software.\n\n"
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
    "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.",
    bg_hex="F8F8F8", border_hex="DDDDDD"
)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 14. DASHBOARD SCREENSHOTS DESCRIPTION
# ════════════════════════════════════════════════════════════════════════════

add_heading("14.  UI Screens Reference", 1, VIOLET, space_before=4)
add_divider()
add_body(
    "Below is a description of each screen in the application. "
    "Add your own screenshots by inserting images at the placeholder positions.",
    italic=True, color=MUTED
)

screens = [
    ("Home Page",
     "Dark hero section with violet eyebrow pill ('Powered by Google Gemini & FastAPI'), "
     "large headline 'Instant code review for any GitHub repository', description paragraph, "
     "URL input box with violet focus ring, Analyze button, and 3 quick-pick chips (fastapi, react, vscode). "
     "Below the input: 6-card feature grid showing what is analyzed."),
    ("Analysis Progress",
     "While the backend pipeline runs, the input area is replaced by an animated step list "
     "showing: Validating → Fetching data → Analyzing code → Running AI review → Calculating scores → Report ready. "
     "Each step shows a spinner (current), checkmark (done), or muted dot (pending). "
     "A progress bar fills from 0% to 100%."),
    ("Dashboard — Top",
     "Repository header card: full_name, description, language badges, license/branch/year metadata. "
     "GitHub link and PDF Report buttons top-right. "
     "Below: 4 stat cards — Stars, Forks, Open Issues, Watchers."),
    ("Dashboard — Score + Languages",
     "Side-by-side cards on large screens. Left: SVG animated ring showing 0–100 score with letter grade, "
     "5 dimension bars each with a colored progress bar and weight percentage. "
     "Right: Recharts donut chart of language distribution with per-language mini-bars."),
    ("Dashboard — File Structure + README",
     "Side-by-side. Left: file presence tree with green ticks and red crosses for each of the 22 rules. "
     "Right: README quality score bar, two-column list of found sections (green ticks) and missing sections (amber crosses), "
     "plus suggestion items."),
    ("Dashboard — Code Analysis",
     "Grid of per-language cards. Each card shows language name, total LOC, error count (red), "
     "warning count (amber), and scrollable list of up to 10 issues with severity dots and file:line references."),
    ("Dashboard — AI Review",
     "Full-width card with Beginner Friendly and Production Readiness mini-bars, "
     "violet project overview box, tech-stack assessment paragraph, strengths/weaknesses grid, "
     "security/performance/maintainability suggestion columns, overall review paragraph, "
     "and recommended next steps list."),
    ("History Page",
     "Table of past analyses: repo name, score badge (color-coded by grade), grade letter, "
     "language, date. Each row has a red delete button."),
    ("About Page",
     "Scoring methodology documentation: dimension table with weights, grade thresholds table, "
     "and explanation of the calculation approach."),
]

for title, desc in screens:
    add_heading(title, 3, VIOLET, space_before=10)
    add_body(desc, color=DARK_GRAY)
    add_colored_box(
        f"[ Screenshot placeholder: {title} ]\n"
        "Add your screenshot here using Insert > Picture in Microsoft Word.",
        bg_hex="F9F9FF", border_hex="CCCCEE"
    )

doc.add_page_break()

# ── Final page ──────────────────────────────────────────────────────────────
doc.add_paragraph().paragraph_format.space_after = Pt(60)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("— End of Report —")
r.font.size  = Pt(11)
r.font.color.rgb = MUTED
r.font.italic = True

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
p2.paragraph_format.space_before = Pt(8)
r2 = p2.add_run("AI GitHub Project Reviewer  ·  Built by Haseeb Raza  ·  MIT License")
r2.font.size  = Pt(9)
r2.font.color.rgb = MUTED

# ── Save ────────────────────────────────────────────────────────────────────
out = r"C:\Users\HASEEB TOBA\Documents\Ai github repo\AI_GitHub_Reviewer_Project_Report.docx"
doc.save(out)
print(f"Report saved: {out}")
