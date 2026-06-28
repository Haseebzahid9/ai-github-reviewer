"""
PDF report generator for AI GitHub Project Reviewer.
Uses ReportLab to produce a multi-page styled PDF from a stored report dict.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

# ── Colour palette ────────────────────────────────────────────────────────────
BLUE_DARK   = colors.HexColor("#1e3a8a")   # cover background, headers
BLUE_MID    = colors.HexColor("#2563eb")   # accent
BLUE_LIGHT  = colors.HexColor("#dbeafe")   # table row highlight
BLUE_PALE   = colors.HexColor("#eff6ff")   # alternating row
WHITE       = colors.white
GRAY_DARK   = colors.HexColor("#1f2937")
GRAY_MID    = colors.HexColor("#6b7280")
GRAY_LIGHT  = colors.HexColor("#f3f4f6")
RED_SOFT    = colors.HexColor("#fee2e2")
ORANGE_SOFT = colors.HexColor("#ffedd5")
GREEN_SOFT  = colors.HexColor("#dcfce7")

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm

# ── Grade / badge helpers ─────────────────────────────────────────────────────

def _grade_color(grade: str) -> Any:
    return {
        "A+": colors.HexColor("#059669"),
        "A":  colors.HexColor("#16a34a"),
        "B+": colors.HexColor("#65a30d"),
        "B":  colors.HexColor("#ca8a04"),
        "C+": colors.HexColor("#ea580c"),
        "C":  colors.HexColor("#dc2626"),
        "D":  colors.HexColor("#b91c1c"),
        "F":  colors.HexColor("#7f1d1d"),
    }.get(grade, GRAY_MID)


def _score_bar_color(score: float) -> Any:
    if score >= 80: return colors.HexColor("#10b981")
    if score >= 65: return colors.HexColor("#22c55e")
    if score >= 50: return colors.HexColor("#eab308")
    if score >= 35: return colors.HexColor("#f97316")
    return colors.HexColor("#ef4444")


def _severity_color(sev: str) -> Any:
    return {"error": RED_SOFT, "warning": ORANGE_SOFT, "info": BLUE_PALE}.get(sev, BLUE_PALE)


# ── Custom flowables ──────────────────────────────────────────────────────────

class ScoreBar(Flowable):
    """Horizontal filled bar representing a 0-100 score."""

    def __init__(self, score: float, width: float = 10 * cm, height: float = 10):
        super().__init__()
        self.score  = min(max(score, 0), 100)
        self.width  = width
        self.height = height

    def wrap(self, *_):
        return self.width, self.height + 4

    def draw(self):
        c = self.canv
        # Background track
        c.setFillColor(GRAY_LIGHT)
        c.roundRect(0, 2, self.width, self.height, self.height / 2, fill=1, stroke=0)
        # Filled portion
        filled = self.width * (self.score / 100)
        if filled > 0:
            c.setFillColor(_score_bar_color(self.score))
            c.roundRect(0, 2, filled, self.height, self.height / 2, fill=1, stroke=0)
        # Score label to the right
        c.setFillColor(GRAY_DARK)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(self.width, self.height / 2, f"{self.score:.0f}/100")


class ColorBlock(Flowable):
    """A solid filled rectangle, used as a section-header background."""

    def __init__(self, label: str, width: float, height: float = 22,
                 bg: Any = BLUE_DARK, fg: Any = WHITE, font_size: int = 12):
        super().__init__()
        self.label     = label
        self.width     = width
        self.height    = height
        self.bg        = bg
        self.fg        = fg
        self.font_size = font_size

    def wrap(self, *_):
        return self.width, self.height + 4

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        c.setFillColor(self.fg)
        c.setFont("Helvetica-Bold", self.font_size)
        c.drawString(8, self.height / 2 - self.font_size / 3, self.label)


# ── Style helpers ─────────────────────────────────────────────────────────────

_BASE = getSampleStyleSheet()

def _style(name: str = "Normal", **kw) -> ParagraphStyle:
    base = _BASE.get(name, _BASE["Normal"])
    return ParagraphStyle(name + "_custom_" + str(id(kw)), parent=base, **kw)


S_BODY   = _style(fontSize=9,  textColor=GRAY_DARK, leading=14, spaceAfter=4)
S_SMALL  = _style(fontSize=8,  textColor=GRAY_MID,  leading=12)
S_BULLET = _style(fontSize=9,  textColor=GRAY_DARK, leading=13, leftIndent=12,
                  bulletIndent=4, spaceAfter=3)
S_H2     = _style(fontSize=11, textColor=BLUE_DARK, leading=16, spaceBefore=8,
                  spaceAfter=4, fontName="Helvetica-Bold")
S_H3     = _style(fontSize=9,  textColor=GRAY_DARK, leading=13, spaceBefore=4,
                  spaceAfter=2, fontName="Helvetica-Bold")
S_CENTER = _style(fontSize=9,  textColor=GRAY_DARK, alignment=TA_CENTER)

_COL_HEADER_STYLE = [
    ("BACKGROUND",  (0, 0), (-1, 0), BLUE_DARK),
    ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
    ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE",    (0, 0), (-1, 0), 8),
    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ("TOPPADDING",    (0, 0), (-1, 0), 6),
    ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE",    (0, 1), (-1, -1), 8),
    ("TOPPADDING",  (0, 1), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
    ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
    ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
]


def _table(data: list, col_widths: list, extra_style: list | None = None) -> Table:
    style = list(_COL_HEADER_STYLE)
    if extra_style:
        style.extend(extra_style)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t


def _bullets(items: list[str], style: ParagraphStyle = S_BULLET) -> list[Paragraph]:
    return [Paragraph(f"• {item}", style) for item in (items or [])]


def _safe(val: Any, fallback: str = "—") -> str:
    if val is None or val == "":
        return fallback
    return str(val)


# ── Page template with header / footer ───────────────────────────────────────

class _HeaderFooterCanvas:
    """Mixin — not used directly; we use onPage callbacks instead."""


def _make_doc(buf: io.BytesIO, repo_name: str) -> BaseDocTemplate:
    content_w = PAGE_W - 2 * MARGIN
    content_h = PAGE_H - 2 * MARGIN - 1.2 * cm  # room for footer

    def _header_footer(canvas, doc):
        canvas.saveState()
        # Footer line
        canvas.setStrokeColor(BLUE_LIGHT)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 1.5 * cm, PAGE_W - MARGIN, 1.5 * cm)
        # Repo name left
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY_MID)
        canvas.drawString(MARGIN, 0.9 * cm, repo_name)
        # Page number right
        canvas.drawRightString(
            PAGE_W - MARGIN, 0.9 * cm, f"Page {doc.page}"
        )
        # Header — thin blue top bar (skip cover page 1)
        if doc.page > 1:
            canvas.setFillColor(BLUE_DARK)
            canvas.rect(0, PAGE_H - 1 * cm, PAGE_W, 1 * cm, fill=1, stroke=0)
            canvas.setFillColor(WHITE)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(MARGIN, PAGE_H - 0.65 * cm, "GitHub Repository Analysis Report")
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.65 * cm, repo_name)
        canvas.restoreState()

    normal_frame = Frame(
        MARGIN, 1.8 * cm,
        content_w, content_h,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    cover_frame = Frame(
        0, 0, PAGE_W, PAGE_H,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=2 * cm,
        title="GitHub Repository Analysis Report",
        author="AI GitHub Project Reviewer",
    )
    doc.addPageTemplates([
        PageTemplate(id="cover",  frames=[cover_frame], onPage=_header_footer),
        PageTemplate(id="normal", frames=[normal_frame], onPage=_header_footer),
    ])
    return doc


# ── Page builders ─────────────────────────────────────────────────────────────

def _page_cover(report: dict, generated_at: str) -> list:
    repo       = report.get("repo_info") or report.get("repo") or {}
    final      = report.get("final_score") or {}
    languages  = report.get("languages") or {}
    code_an    = report.get("code_analysis") or {}
    file_pres  = report.get("file_presence") or {}

    full_name    = _safe(repo.get("full_name") or repo.get("name"), "Unknown Repo")
    url          = _safe(repo.get("html_url") or repo.get("url"))
    description  = repo.get("description") or ""
    stars        = repo.get("stargazers_count") or repo.get("stars") or 0
    forks        = repo.get("forks_count")      or repo.get("forks") or 0
    total_score  = final.get("total_score", 0)
    grade        = final.get("grade", "—")
    badge        = final.get("badge", "")
    primary_lang = (list(languages.keys()) or [repo.get("language"), "Unknown"])[0] or "Unknown"

    files_analyzed = (
        code_an.get("files_analyzed")
        or code_an.get("total_files")
        or len(report.get("source_files") or [])
        or 0
    )

    story: list = []

    # ── Solid dark-blue cover background ──────────────────────────────────────
    class CoverBackground(Flowable):
        def wrap(self, *_): return PAGE_W, PAGE_H
        def draw(self):
            c = self.canv
            # Full page background
            c.setFillColor(BLUE_DARK)
            c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            # White content card
            card_x, card_y = 2 * cm, 3.5 * cm
            card_w, card_h = PAGE_W - 4 * cm, PAGE_H - 7 * cm
            c.setFillColor(WHITE)
            c.roundRect(card_x, card_y, card_w, card_h, 8, fill=1, stroke=0)

    story.append(CoverBackground())

    # Spacer to push content below the top of the page
    story.append(Spacer(1, 2.8 * cm))

    # ── Logo placeholder + title ──────────────────────────────────────────────
    class LogoTitle(Flowable):
        def wrap(self, *_): return PAGE_W, 2.8 * cm
        def draw(self):
            c = self.canv
            cx = PAGE_W / 2
            # Circle logo placeholder
            c.setFillColor(BLUE_MID)
            c.circle(cx, 1.6 * cm, 0.9 * cm, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(cx, 1.6 * cm - 6, "GR")
            # Title
            c.setFont("Helvetica-Bold", 18)
            c.setFillColor(WHITE)
            c.drawCentredString(cx, 0.2 * cm, "GitHub Repository Analysis Report")

    story.append(LogoTitle())
    story.append(Spacer(1, 0.6 * cm))

    # ── Repo name + URL on white card ─────────────────────────────────────────
    class RepoBlock(Flowable):
        def wrap(self, *_): return PAGE_W, 3 * cm
        def draw(self):
            c = self.canv
            cx = PAGE_W / 2
            c.setFont("Helvetica-Bold", 15)
            c.setFillColor(BLUE_DARK)
            c.drawCentredString(cx, 2 * cm, full_name)
            c.setFont("Helvetica", 8)
            c.setFillColor(BLUE_MID)
            c.drawCentredString(cx, 1.3 * cm, url)
            if description:
                c.setFont("Helvetica", 8)
                c.setFillColor(GRAY_MID)
                max_w = PAGE_W - 6 * cm
                # Truncate long descriptions
                desc_text = description if len(description) < 110 else description[:107] + "…"
                c.drawCentredString(cx, 0.6 * cm, desc_text)

    story.append(RepoBlock())
    story.append(Spacer(1, 0.3 * cm))

    # ── Big score circle ──────────────────────────────────────────────────────
    class BigScore(Flowable):
        def wrap(self, *_): return PAGE_W, 4.5 * cm
        def draw(self):
            c = self.canv
            cx = PAGE_W / 2
            cy = 2.4 * cm
            r  = 1.7 * cm
            # Outer ring
            c.setStrokeColor(_grade_color(grade))
            c.setLineWidth(6)
            c.circle(cx, cy, r, fill=0, stroke=1)
            # Score number
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(BLUE_DARK)
            c.drawCentredString(cx, cy - 9, f"{total_score:.0f}")
            # /100 subscript
            c.setFont("Helvetica", 10)
            c.setFillColor(GRAY_MID)
            c.drawCentredString(cx, cy - 20, "/100")
            # Grade badge below
            bw, bh = 2.4 * cm, 0.7 * cm
            bx = cx - bw / 2
            by = cy - r - 1.1 * cm
            c.setFillColor(_grade_color(grade))
            c.roundRect(bx, by, bw, bh, 4, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 13)
            c.setFillColor(WHITE)
            c.drawCentredString(cx, by + 4, grade)
            # Badge text
            c.setFont("Helvetica", 8)
            c.setFillColor(GRAY_MID)
            c.drawCentredString(cx, by - 0.5 * cm, badge)

    story.append(BigScore())

    # ── Quick stats row ───────────────────────────────────────────────────────
    class QuickStats(Flowable):
        def wrap(self, *_): return PAGE_W, 2.2 * cm
        def draw(self):
            c = self.canv
            items = [
                ("⭐ Stars",  f"{int(stars):,}"),
                ("🍴 Forks",  f"{int(forks):,}"),
                ("💻 Language", primary_lang),
                ("📄 Files", str(files_analyzed)),
                ("📅 Generated", generated_at[:10]),
            ]
            n   = len(items)
            col = PAGE_W / n
            for i, (lbl, val) in enumerate(items):
                cx = col * i + col / 2
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(BLUE_DARK)
                c.drawCentredString(cx, 1.1 * cm, val)
                c.setFont("Helvetica", 7)
                c.setFillColor(GRAY_MID)
                c.drawCentredString(cx, 0.5 * cm, lbl)

    story.append(QuickStats())
    story.append(Spacer(1, 0.5 * cm))

    # Divider
    story.append(HRFlowable(width="80%", thickness=0.5, color=BLUE_LIGHT,
                             hAlign="CENTER", spaceAfter=6))

    # Generated timestamp centred
    ts_style = _style(fontSize=8, textColor=GRAY_MID, alignment=TA_CENTER)
    story.append(Paragraph(f"Report generated: {generated_at}", ts_style))

    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())
    return story


def _page_score_breakdown(report: dict) -> list:
    final     = report.get("final_score") or {}
    breakdown = final.get("breakdown") or {}
    total     = final.get("total_score", 0)
    grade     = final.get("grade", "—")
    badge     = final.get("badge", "")

    story = [
        ColorBlock("Score Breakdown", PAGE_W - 2 * MARGIN),
        Spacer(1, 0.4 * cm),
    ]

    LABELS = {
        "structure":    "Project Structure",
        "documentation":"Documentation",
        "code_quality": "Code Quality",
        "security":     "Security",
        "ai_assessment":"AI Assessment",
    }

    # Summary pill
    summary_color = _grade_color(grade)
    grade_para = _style(fontSize=20, textColor=summary_color, alignment=TA_CENTER,
                        fontName="Helvetica-Bold")
    badge_para = _style(fontSize=11, textColor=GRAY_MID, alignment=TA_CENTER)
    story.append(Paragraph(f"{total:.0f}/100  ·  {grade}", grade_para))
    story.append(Paragraph(badge, badge_para))
    story.append(Spacer(1, 0.5 * cm))

    # Table
    content_w = PAGE_W - 2 * MARGIN
    col_w = [3.8 * cm, 2 * cm, 2 * cm, 2 * cm, content_w - 9.8 * cm]
    table_data = [["Dimension", "Score", "Weight", "Weighted", "Visual"]]

    bar_rows = []
    for dim, data in breakdown.items():
        sc  = data.get("score", 0)
        wt  = data.get("weight", 0)
        wtd = data.get("weighted", sc * wt)
        bar_rows.append((len(table_data), sc))
        table_data.append([
            LABELS.get(dim, dim),
            f"{sc:.1f}",
            f"{wt*100:.0f}%",
            f"{wtd:.1f}",
            "",  # bar inserted as flowable below
        ])

    t = _table(table_data, col_w)
    story.append(t)

    # Individual bars after the table
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Per-Dimension Score Bars", S_H2))
    bar_w = content_w - 4 * cm

    for dim, data in breakdown.items():
        sc = data.get("score", 0)
        label = LABELS.get(dim, dim)
        row = [
            Paragraph(label, S_H3),
            ScoreBar(sc, width=bar_w),
        ]
        bar_table = Table([row], colWidths=[4 * cm, bar_w])
        bar_table.setStyle(TableStyle([
            ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ]))
        story.append(bar_table)

    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())
    return story


def _page_repo_overview(report: dict) -> list:
    repo      = report.get("repo_info") or report.get("repo") or {}
    languages = report.get("languages") or {}
    fp        = report.get("file_presence") or {}
    readme_an = report.get("readme_analysis") or {}

    full_name = _safe(repo.get("full_name") or repo.get("name"))
    desc      = repo.get("description") or "No description provided."
    stars     = repo.get("stargazers_count") or repo.get("stars") or 0
    forks     = repo.get("forks_count")      or repo.get("forks") or 0
    issues    = repo.get("open_issues_count") or repo.get("open_issues") or 0
    license_  = repo.get("license") or "—"
    branch    = repo.get("default_branch") or "—"

    content_w = PAGE_W - 2 * MARGIN
    story = [
        ColorBlock("Repository Overview", content_w),
        Spacer(1, 0.4 * cm),
        Paragraph(full_name, S_H2),
        Paragraph(desc, S_BODY),
        Spacer(1, 0.3 * cm),
    ]

    # Meta stats
    meta_data = [
        ["Stars", "Forks", "Open Issues", "License", "Default Branch"],
        [f"{int(stars):,}", f"{int(forks):,}", f"{int(issues):,}", license_, branch],
    ]
    story.append(_table(meta_data, [content_w / 5] * 5))
    story.append(Spacer(1, 0.4 * cm))

    # ── Language distribution ─────────────────────────────────────────────────
    if languages:
        story.append(Paragraph("Language Distribution", S_H2))
        total_bytes = sum(languages.values()) or 1
        lang_data = [["Language", "Bytes", "Share (%)"]]
        for lang, byt in sorted(languages.items(), key=lambda x: -x[1])[:12]:
            pct = byt / total_bytes * 100
            lang_data.append([lang, f"{byt:,}", f"{pct:.1f}%"])
        story.append(_table(lang_data, [5 * cm, 5 * cm, content_w - 10 * cm]))
        story.append(Spacer(1, 0.4 * cm))

    # ── File presence ─────────────────────────────────────────────────────────
    story.append(Paragraph("File Structure Findings", S_H2))
    FILE_LABELS = {
        "readme": "README", "license": "LICENSE", "gitignore": ".gitignore",
        "env_example": ".env.example", "dockerfile": "Dockerfile",
        "docker_compose": "docker-compose.yml", "github_actions": "GitHub Actions",
        "tests_dir": "Tests directory", "src_dir": "src/ directory",
        "docs_dir": "docs/ directory", "requirements_txt": "requirements.txt",
        "package_json": "package.json", "setup_py": "setup.py",
        "pyproject_toml": "pyproject.toml", "ci_files": "CI config files",
    }
    present = [lbl for k, lbl in FILE_LABELS.items() if fp.get(k)]
    missing = [lbl for k, lbl in FILE_LABELS.items() if not fp.get(k)]

    half = content_w / 2 - 0.2 * cm
    rows = max(len(present), len(missing))
    fp_data = [
        [Paragraph("✔ Present", _style(fontSize=8, textColor=colors.HexColor("#059669"),
                                        fontName="Helvetica-Bold")),
         Paragraph("✘ Missing", _style(fontSize=8, textColor=colors.HexColor("#dc2626"),
                                        fontName="Helvetica-Bold"))],
    ]
    for i in range(rows):
        p = present[i] if i < len(present) else ""
        m = missing[i]  if i < len(missing)  else ""
        fp_data.append([
            Paragraph(f"• {p}", S_SMALL) if p else Paragraph("", S_SMALL),
            Paragraph(f"• {m}", S_SMALL) if m else Paragraph("", S_SMALL),
        ])
    story.append(Table(fp_data, colWidths=[half, half],
                       style=TableStyle([
                           ("BACKGROUND", (0, 0), (0, 0), GREEN_SOFT),
                           ("BACKGROUND", (1, 0), (1, 0), RED_SOFT),
                           ("TOPPADDING",    (0, 0), (-1, -1), 3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                           ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                           ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
                       ])))
    story.append(Spacer(1, 0.4 * cm))

    # ── README checklist ──────────────────────────────────────────────────────
    if readme_an:
        story.append(Paragraph("README Quality", S_H2))
        rm_score    = readme_an.get("score", 0)
        rm_found    = readme_an.get("sections_found") or []
        rm_missing  = readme_an.get("sections_missing") or []
        rm_suggest  = readme_an.get("suggestions") or []

        story.append(Paragraph(f"README score: <b>{rm_score:.0f}/100</b>", S_BODY))
        if rm_found:
            story.append(Paragraph("Sections present:", S_H3))
            story.extend(_bullets(rm_found))
        if rm_missing:
            story.append(Paragraph("Sections missing:", S_H3))
            story.extend(_bullets(rm_missing, _style(
                fontSize=9, textColor=colors.HexColor("#dc2626"), leading=13,
                leftIndent=12, bulletIndent=4, spaceAfter=2,
            )))
        if rm_suggest:
            story.append(Paragraph("Suggestions:", S_H3))
            story.extend(_bullets(rm_suggest))

    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())
    return story


def _page_code_analysis(report: dict) -> list:
    code_an   = report.get("code_analysis") or {}
    by_lang   = code_an.get("by_language") or {}
    top_issues = []

    # Collect top issues across all languages
    if isinstance(by_lang, dict):
        for lang_data in by_lang.values():
            for iss in (lang_data.get("issues") or []):
                top_issues.append(iss)
    elif isinstance(by_lang, list):
        for s in by_lang:
            top_issues.append({
                "severity": "info",
                "message": f"{s.get('language','?')}: {s.get('errors',0)}E / {s.get('warnings',0)}W",
                "file": "",
            })

    # Sort by severity
    sev_order = {"error": 0, "warning": 1, "info": 2}
    top_issues.sort(key=lambda i: sev_order.get(i.get("severity", "info"), 2))
    top_issues = top_issues[:10]

    content_w = PAGE_W - 2 * MARGIN
    story = [
        ColorBlock("Code Analysis", content_w),
        Spacer(1, 0.4 * cm),
    ]

    # Summary line
    total_files = code_an.get("total_files") or code_an.get("files_analyzed") or 0
    total_loc   = code_an.get("total_loc")   or code_an.get("lines_analyzed") or 0
    story.append(Paragraph(
        f"Files analyzed: <b>{total_files}</b>  ·  Total lines: <b>{total_loc:,}</b>",
        S_BODY,
    ))
    story.append(Spacer(1, 0.3 * cm))

    # ── Per-language table ────────────────────────────────────────────────────
    story.append(Paragraph("Per-Language Summary", S_H2))

    col_w = [3.5 * cm, 2 * cm, 2.5 * cm, 2.5 * cm, content_w - 10.5 * cm]
    lang_table_data = [["Language", "Files", "Lines of Code", "Issues Found", "Score"]]

    if isinstance(by_lang, dict):
        for lang, data in by_lang.items():
            issues_list = data.get("issues") or []
            errors   = sum(1 for i in issues_list if i.get("severity") == "error")
            warnings = sum(1 for i in issues_list if i.get("severity") == "warning")
            total_iss = errors + warnings + sum(
                1 for i in issues_list if i.get("severity") == "info"
            )
            score = data.get("score", "—")
            lang_table_data.append([
                lang,
                str(data.get("file_count", data.get("files", 0))),
                f"{data.get('total_loc', data.get('loc', 0)):,}",
                f"{total_iss} ({errors}E / {warnings}W)",
                f"{score:.0f}" if isinstance(score, (int, float)) else score,
            ])
    elif isinstance(by_lang, list):
        for s in by_lang:
            lang_table_data.append([
                s.get("language", "?"),
                str(s.get("file_count", 0)),
                f"{s.get('total_loc', 0):,}",
                f"{s.get('errors', 0)}E / {s.get('warnings', 0)}W",
                f"{s.get('avg_score', 0):.0f}",
            ])

    if len(lang_table_data) > 1:
        story.append(_table(lang_table_data, col_w))
    else:
        story.append(Paragraph("No language data available.", S_SMALL))

    story.append(Spacer(1, 0.5 * cm))

    # ── Top 10 issues ─────────────────────────────────────────────────────────
    story.append(Paragraph("Top Critical Issues", S_H2))
    if top_issues:
        iss_col_w = [2 * cm, 4 * cm, content_w - 6 * cm]
        iss_data = [["Severity", "File", "Message"]]
        extra_style = []
        for idx, iss in enumerate(top_issues, start=1):
            sev  = iss.get("severity", "info")
            file = iss.get("file", "") or iss.get("filename", "")
            msg  = iss.get("message", "")
            iss_data.append([sev.upper(), file or "—", msg])
            bg = _severity_color(sev)
            extra_style.append(("BACKGROUND", (0, idx), (0, idx), bg))

        story.append(_table(iss_data, iss_col_w, extra_style))
    else:
        story.append(Paragraph("No issues found — great work!", S_BODY))

    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())
    return story


def _page_ai_review(report: dict) -> list:
    ai = report.get("ai_review") or report.get("ai") or {}

    content_w = PAGE_W - 2 * MARGIN
    story = [
        ColorBlock("AI Review (Powered by Google Gemini)", content_w),
        Spacer(1, 0.4 * cm),
    ]

    # AI scores
    bfs = ai.get("beginner_friendly_score")
    prs = ai.get("production_readiness_score")
    dq  = ai.get("documentation_quality", "—")
    aqs = ai.get("ai_quality_score")
    ai_available = ai.get("ai_available", True)

    if not ai_available:
        story.append(Paragraph(
            "⚠  AI review unavailable — showing fallback data.",
            _style(fontSize=9, textColor=colors.HexColor("#92400e"), leading=13)
        ))
        story.append(Spacer(1, 0.2 * cm))

    if any(v is not None for v in [bfs, prs, aqs]):
        scores_data = [["Metric", "Value"]]
        if bfs is not None: scores_data.append(["Beginner Friendly",    f"{bfs}/10"])
        if prs is not None: scores_data.append(["Production Readiness", f"{prs}/10"])
        if dq:              scores_data.append(["Documentation Quality", dq.title()])
        if aqs is not None: scores_data.append(["AI Quality Score",      f"{aqs}/100"])
        story.append(_table(scores_data, [6 * cm, content_w - 6 * cm]))
        story.append(Spacer(1, 0.4 * cm))

    def _ai_section(title: str, content):
        if not content:
            return
        story.append(Paragraph(title, S_H2))
        if isinstance(content, list):
            story.extend(_bullets(content))
        else:
            story.append(Paragraph(str(content), S_BODY))
        story.append(Spacer(1, 0.2 * cm))

    _ai_section("Project Overview",          ai.get("project_overview"))
    _ai_section("Tech Stack Assessment",     ai.get("tech_stack_assessment"))
    _ai_section("Strengths",                 ai.get("strengths"))
    _ai_section("Weaknesses",                ai.get("weaknesses"))
    _ai_section("Security Recommendations",  ai.get("security_suggestions"))
    _ai_section("Performance Recommendations", ai.get("performance_suggestions"))
    _ai_section("Maintainability",           ai.get("maintainability_suggestions"))
    _ai_section("Best Practices",            ai.get("best_practices"))
    _ai_section("Overall Review",            ai.get("overall_review"))
    _ai_section("Recommended Next Steps",    ai.get("recommended_next_steps"))
    _ai_section("Similar Projects to Study", ai.get("similar_projects_to_study"))

    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())
    return story


def _page_detailed_metrics(report: dict) -> list:
    code_an      = report.get("code_analysis") or {}
    by_lang      = code_an.get("by_language") or {}
    source_files = report.get("source_files") or []

    content_w = PAGE_W - 2 * MARGIN
    story = [
        ColorBlock("Detailed File Metrics", content_w),
        Spacer(1, 0.4 * cm),
    ]

    # ── Per-file table (from source_files list) ───────────────────────────────
    if source_files:
        story.append(Paragraph("Source Files Analyzed", S_H2))
        col_w = [content_w - 9 * cm, 2 * cm, 2 * cm, 2.5 * cm, 2.5 * cm]
        file_data = [["File Path", "Lang", "KB", "Issues", "LOC"]]

        # Build a quick lookup of per-file metrics from by_language if available
        file_issues: dict[str, int] = {}
        file_loc: dict[str, int] = {}
        if isinstance(by_lang, dict):
            for lang_data in by_lang.values():
                for iss in (lang_data.get("issues") or []):
                    fname = iss.get("file", "")
                    if fname:
                        file_issues[fname] = file_issues.get(fname, 0) + 1

        for sf in source_files[:50]:  # cap at 50 rows to avoid page overflow
            path     = sf.get("path", "")
            lang     = sf.get("language", "?")
            size_kb  = sf.get("size_bytes", 0) / 1024
            n_issues = file_issues.get(path, "—")
            loc      = file_loc.get(path, "—")
            # Truncate long paths
            display_path = path if len(path) <= 48 else "…" + path[-45:]
            file_data.append([
                Paragraph(display_path, S_SMALL),
                lang,
                f"{size_kb:.1f}",
                str(n_issues),
                str(loc),
            ])

        story.append(_table(file_data, col_w))

        if len(source_files) > 50:
            story.append(Paragraph(
                f"… and {len(source_files) - 50} more files not shown.",
                S_SMALL,
            ))
        story.append(Spacer(1, 0.4 * cm))

    # ── Structure analysis scores ─────────────────────────────────────────────
    struct_an = report.get("structure_analysis") or {}
    if struct_an:
        story.append(Paragraph("Structure Analysis Scores", S_H2))
        cat_scores = struct_an.get("category_scores") or {}
        if cat_scores:
            cat_data = [["Category", "Score"]]
            for cat, sc in cat_scores.items():
                cat_data.append([cat.replace("_", " ").title(), f"{sc:.1f}"])
            half_w = content_w / 2
            story.append(_table(cat_data, [half_w - 2 * cm, 2 * cm]))

    return story


# ── Public entry point ────────────────────────────────────────────────────────

def generate_pdf_report(report_data: dict) -> bytes:
    """
    Build a multi-page PDF from a stored report dict and return it as bytes.
    """
    buf = io.BytesIO()

    # Derive generated_at
    generated_at = report_data.get("generated_at") or datetime.utcnow().isoformat() + "Z"
    # Friendly format: 2026-06-28T14:32:00Z → 2026-06-28 14:32 UTC
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        generated_at = dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        pass

    repo      = report_data.get("repo_info") or report_data.get("repo") or {}
    repo_name = repo.get("full_name") or repo.get("name") or "repository"

    doc   = _make_doc(buf, repo_name)
    story = []

    story.extend(_page_cover(report_data, generated_at))
    story.extend(_page_score_breakdown(report_data))
    story.extend(_page_repo_overview(report_data))
    story.extend(_page_code_analysis(report_data))
    story.extend(_page_ai_review(report_data))
    story.extend(_page_detailed_metrics(report_data))

    doc.build(story)
    return buf.getvalue()
