<div align="center">

# AI GitHub Project Reviewer

**Instant, AI-powered code-quality analysis for any public GitHub repository.**

Paste a repo URL → get a structured score, multi-language static analysis, security flags,
README grading, and a full Gemini AI narrative — in under 60 seconds.
Export the entire report as a PDF.

[![License: MIT](https://img.shields.io/badge/License-MIT-7c5cfc.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646cff?logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-38bdf8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)

[Report a Bug](https://github.com/Haseebzahid9/ai-github-reviewer/issues) · [Request a Feature](https://github.com/Haseebzahid9/ai-github-reviewer/issues)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [1 · Clone the repository](#1--clone-the-repository)
  - [2 · Backend setup](#2--backend-setup)
  - [3 · Frontend setup](#3--frontend-setup)
  - [4 · Run both servers](#4--run-both-servers)
- [Environment Variables](#environment-variables)
  - [GitHub Token](#github-token)
  - [Gemini API Key](#gemini-api-key)
- [API Reference](#api-reference)
- [Scoring System](#scoring-system)
- [Deployment](#deployment)
  - [Backend — Render](#backend--render)
  - [Frontend — Vercel](#frontend--vercel)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [Author](#author)
- [License](#license)

---

## Overview

AI GitHub Project Reviewer is a full-stack web application that evaluates the quality of any public
GitHub repository across five weighted dimensions and presents the results in a data-dense dashboard.
It combines rule-based static analysis with a Google Gemini AI narrative to provide both objective
metrics and human-readable insights — making it useful for developers evaluating open-source libraries,
hiring managers auditing candidate portfolios, or anyone curious about a codebase before diving in.

---

## Features

| Capability | Detail |
|---|---|
| **5-Dimension Scoring** | Structure · Documentation · Code Quality · Security · AI Assessment |
| **14+ Language Support** | Python · JS/TS · Java · C/C++ · C# · Go · Rust · PHP · Swift · Kotlin · Ruby · SQL · HTML · CSS |
| **Static Code Analysis** | Per-file issue detection (error/warning/info), LOC counting, density-normalized scoring |
| **README Grading** | 14-section checklist: badges, install, usage, contributing guide, license, and more |
| **Security Detection** | Hardcoded secrets, injection patterns, `eval()` usage, deprecated APIs, missing SRI |
| **File Structure Check** | 22 rules for CI configs, Dockerfile, `.gitignore`, test directories, package manifests |
| **Gemini AI Review** | Project overview, tech-stack assessment, strengths, weaknesses, actionable next steps |
| **PDF Export** | Full 6-page formatted report downloadable in one click |
| **Review History** | SQLite-persisted reports, viewable and deletable from the History page |
| **Graceful Degradation** | App works without Gemini — AI section shows a fallback badge instead of crashing |

---

## Tech Stack

### Backend

| Package | Version | Purpose |
|---|---|---|
| **FastAPI** | ≥ 0.115 | Async REST API framework |
| **SQLAlchemy + aiosqlite** | ≥ 2.0 | Async ORM with SQLite |
| **httpx** | ≥ 0.27 | Async HTTP client for the GitHub API |
| **google-genai** | ≥ 1.0 | Official Google Gemini SDK |
| **ReportLab** | ≥ 4.2 | PDF generation |
| **Pydantic v2** | ≥ 2.10 | Request/response validation |
| **python-dotenv** | ≥ 1.0 | Environment variable loading |

### Frontend

| Package | Version | Purpose |
|---|---|---|
| **React** | 18 | UI framework |
| **Vite** | 5 | Build tool with HMR |
| **Tailwind CSS** | 3 | Utility-first styling |
| **React Router DOM** | 6 | Client-side routing |
| **Recharts** | 2 | Language donut chart |
| **Axios** | 1 | HTTP client with interceptors |

---

## Project Structure

```
ai-github-reviewer/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, middleware
│   │   ├── models/
│   │   │   └── database.py          # SQLAlchemy models + migrations
│   │   ├── routers/
│   │   │   └── review.py            # All API endpoints
│   │   ├── services/
│   │   │   ├── github.py            # GitHub REST API client
│   │   │   ├── analyzer.py          # Multi-language static analyzer
│   │   │   ├── gemini.py            # Gemini AI integration
│   │   │   ├── report.py            # Score aggregation engine
│   │   │   └── pdf_report.py        # 6-page PDF generator
│   │   └── utils/
│   │       ├── helpers.py
│   │       └── validators.py        # GitHub URL validation
│   ├── tests/
│   │   └── test_review.py           # 25 pytest unit tests
│   ├── .env.example                 # Environment variable template
│   ├── requirements.txt
│   ├── Procfile                     # Render deployment config
│   └── render.yaml
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Router, navbar, toast context
│   │   ├── pages/
│   │   │   ├── Home.jsx             # Hero section, repo input, progress loader
│   │   │   ├── Dashboard.jsx        # Full report dashboard (8 sections)
│   │   │   ├── History.jsx          # Saved reports table
│   │   │   └── About.jsx            # Scoring methodology explained
│   │   ├── components/              # Shared UI components
│   │   ├── services/
│   │   │   └── api.js               # Axios client + error interceptor
│   │   └── hooks/
│   │       └── useToasts.js
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── vercel.json                  # Vercel SPA rewrites + API proxy
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## Getting Started

### Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| **Python** | 3.10 | 3.14 confirmed working |
| **Node.js** | 18 | 20 LTS recommended |
| **npm** | 9 | Bundled with Node.js |
| **Git** | Any | — |

You will also need:

- A **GitHub Personal Access Token** → [instructions below](#github-token)
- A **Google Gemini API Key** → [instructions below](#gemini-api-key)

---

### 1 · Clone the repository

```bash
git clone https://github.com/Haseebzahid9/ai-github-reviewer.git
cd ai-github-reviewer
```

---

### 2 · Backend setup

```bash
cd backend

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Create your environment file from the template
cp .env.example .env
```

Now open `backend/.env` in a text editor and fill in your two API keys:

```env
GITHUB_TOKEN=<your_github_personal_access_token>
GEMINI_API_KEY=<your_gemini_api_key>
```

---

### 3 · Frontend setup

Open a **second terminal** and run:

```bash
cd frontend
npm install
```

No environment file is needed for local development — the Vite dev server automatically proxies all `/api/*` requests to `http://localhost:8000`.

---

### 4 · Run both servers

**Terminal 1 — Backend** (from `backend/`, venv active):

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Frontend** (from `frontend/`):

```bash
npm run dev
```

Open **http://localhost:5173** in your browser.

**Health check:** `http://localhost:8000/health` → `{"status":"ok","version":"1.0.0"}`

---

## Environment Variables

All variables live in `backend/.env`. Copy `backend/.env.example` to create it.

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | **Yes** | — | GitHub PAT — 5 000 req/hr authenticated vs 60 unauthenticated |
| `GEMINI_API_KEY` | **Yes** | — | Google Gemini API key for the AI review |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./github_reviewer.db` | Database connection string |
| `MAX_FILE_SIZE_KB` | No | `150` | Max file size (KB) to download per source file |
| `MAX_FILES_TO_ANALYZE` | No | `20` | Max source files analyzed per repository |
| `CORS_ORIGINS` | No | `http://localhost:5173,...` | Comma-separated list of allowed frontend origins |

### GitHub Token

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Give it a descriptive name (e.g. `ai-github-reviewer`)
4. Set an expiration date
5. Under **Scopes**, tick only **`public_repo`**
6. Click **Generate token** — copy it immediately (shown only once)

> No write scopes are needed. The token is used only for reading repository metadata, file trees, and source files.

### Gemini API Key

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account
3. Click **Create API key**
4. Copy the key into `GEMINI_API_KEY` in your `.env`

> The free tier is sufficient for development. If the key is absent or invalid, the app continues to function — the AI Review section displays a fallback notice instead of crashing.

---

## API Reference

Base URL (local): `http://localhost:8000`

### `POST /api/review`

Analyze a public GitHub repository.

**Request:**
```json
{
  "repo_url": "https://github.com/owner/repository"
}
```

**Success:** Full report JSON (200)

**Errors:**

| Status | Code | Cause |
|---|---|---|
| 400 | `INVALID_URL` | Not a valid GitHub repository URL |
| 404 | `NOT_FOUND` | Repository does not exist or is private |
| 429 | `RATE_LIMIT` | GitHub API rate limit hit |
| 504 | `TIMEOUT` | Analysis exceeded 60 seconds |

---

### `GET /api/history`

List all saved reports, newest first.

**Response:**
```json
[
  {
    "id": 1,
    "repo_name": "owner/repo",
    "score": 74.5,
    "grade": "B+",
    "primary_language": "Python",
    "created_at": "2024-01-15T10:30:00"
  }
]
```

---

### `GET /api/report/{id}`

Fetch a full saved report by ID.

---

### `DELETE /api/history/{id}`

Delete a saved report by ID.

---

### `GET /api/report/{id}/download`

Download the 6-page PDF report. Returns `application/pdf`.

---

### `GET /health`

Service liveness check. Returns `{"status":"ok","version":"1.0.0"}`.

---

## Scoring System

The final score (0–100) is a weighted average of five dimensions:

| Dimension | Weight | Measurement approach |
|---|---|---|
| **Project Structure** | 20% | 22 file-presence and organisation rules |
| **Documentation** | 20% | README completeness across 14 sections |
| **Code Quality** | 30% | Issues per 100 LOC, density-normalized per language |
| **Security** | 15% | Keyword-matched anti-patterns in analyzed source files |
| **AI Assessment** | 15% | Google Gemini holistic quality score (0–10 → 0–100) |

**Grade thresholds:**

| Grade | Range | Meaning |
|---|---|---|
| A+ | 90 – 100 | Excellent — production-ready quality |
| A | 80 – 89 | Very Good |
| B+ | 70 – 79 | Good |
| B | 60 – 69 | Above Average |
| C+ | 50 – 59 | Average |
| C | 40 – 49 | Below Average |
| D | 30 – 39 | Needs significant improvement |
| F | 0 – 29 | Major issues detected |

---

## Deployment

### Backend — Render

`backend/render.yaml` and `backend/Procfile` are pre-configured.

1. Push your repository to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your repository; set the root to `backend/`
4. Set **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in the Render dashboard:
   - `GITHUB_TOKEN`
   - `GEMINI_API_KEY`
6. Deploy

### Frontend — Vercel

`frontend/vercel.json` is pre-configured with SPA rewrites and an API proxy.

1. Go to [vercel.com](https://vercel.com) → **New Project**
2. Import your GitHub repository; set **Root Directory** to `frontend/`
3. Add one environment variable:
   - `VITE_API_URL` = your Render backend URL (e.g. `https://your-app.onrender.com`)
4. Deploy

---

## Running Tests

```bash
cd backend

# Activate your virtual environment first
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install pytest pytest-asyncio
pytest tests/ -v
```

The test suite covers 25 unit tests across:

- GitHub URL validation (`TestValidateGithubUrl`)
- Score clamping (`TestClamp`)
- Final score aggregation (`TestCalculateFinalScore`)
- README section detection (`TestAnalyzeReadme`)
- Project structure rule evaluation (`TestAnalyzeStructure`)
- URL parsing helpers (`TestParseGithubUrl`)

---

## Contributing

Contributions are welcome. Follow this workflow:

1. **Fork** the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes with clear messages
4. Run the test suite: `pytest tests/ -v`
5. Push: `git push origin feature/your-feature-name`
6. Open a **Pull Request** against `main`

For large changes, please open an issue first to discuss the approach.

---

## Author

**Haseeb Raza**

[![GitHub](https://img.shields.io/badge/GitHub-Haseebzahid9-181717?logo=github)](https://github.com/Haseebzahid9)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-haseebraza4998-0A66C2?logo=linkedin)](https://www.linkedin.com/in/haseebraza4998/)
[![Email](https://img.shields.io/badge/Email-haseebzahid4998%40gmail.com-EA4335?logo=gmail&logoColor=white)](mailto:haseebzahid4998@gmail.com)

---

## License

This project is released under the **MIT License**. See the [LICENSE](LICENSE) file for full details.

---

<div align="center">

Made with ♥ by [Haseeb Raza](https://github.com/Haseebzahid9)

</div>
