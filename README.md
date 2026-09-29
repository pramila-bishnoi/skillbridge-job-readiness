# SkillBridge

SkillBridge is a job-readiness coach for students. Upload a resume, paste or
import a job description, and get an explainable readiness score, a skill-gap
breakdown, a study plan, and interview questions — all deterministic, with no
external LLM or AI API involved anywhere.

## Problem

Most students comparing themselves to a job posting get one of two things:
generic advice ("learn Docker") that ignores their actual resume, or a
black-box match score that won't explain itself. SkillBridge is built around
the second problem specifically — every score and recommendation it produces
traces back to something the student actually wrote or a rule you can inspect.

## Features

- **Resume & skill extraction** — upload a PDF/DOC/DOCX resume, get skills
  normalized against a canonical catalog (so "Postgres" and "PostgreSQL"
  count as the same skill).
- **Job description analysis** — paste a description and get it split into
  required skills, preferred skills, and an experience requirement.
- **Job URL import** — paste a public job-posting link instead of copying
  text by hand; the backend fetches it safely (SSRF-protected, size/time
  bounded) and prefers structured JobPosting data when the site publishes it.
- **Explainable readiness score** — one number, built from four visible
  components, never a black box.
- **Skill gaps** — matched / missing / related, with a reason for each.
- **Preparation plan** — missing skills turned into a prioritized study list.
- **Interview preparation** — practice questions generated from your own
  skill gaps and resume/project text.
- **Job comparison** — put 2–5 analyzed jobs side by side.
- **Skill progress** — track what you're learning, independent of any one job.

## Tech Stack

- **Frontend:** React + TypeScript, Vite
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL, via SQLAlchemy + Alembic migrations
- **Infra:** Docker
- **Testing:** pytest (backend), Vitest (frontend)
- **Matching:** TF-IDF + cosine similarity for resume/job text comparison

## How It Works

```
Resume → Skills → Job Analysis → Readiness → Skill Gaps → Preparation → Interview Prep → Progress
```

Each step is a real API call, and each one builds on data the previous step
already produced — nothing is recomputed from scratch or invented along the way.

## Readiness Score

The score is a weighted sum of four independently visible components:

| Component | Weight | What it measures |
|---|---|---|
| Required skills | 45% | How many of the job's required skills you have |
| Preferred skills | 15% | How many of the job's preferred skills you have |
| Experience | 20% | Whether your detected experience meets the job's requirement |
| Text similarity | 20% | Lexical overlap between your resume and the job description |

Every component is shown on its own, alongside the final score — you can see
exactly what it's built from, not just the number.

## Testing

357 backend tests (pytest) and 90 frontend tests (Vitest), both currently
passing.

```bash
cd backend && pytest
cd frontend && npm run test
```

## Local Setup

```bash
git clone <this-repo>
cd skillbridge-job-readiness
cp .env.example .env

docker compose up --build
```

The frontend runs on `http://localhost:5173`, the API on `http://localhost:8000`.
Create a profile from the UI to get started — no seed data or manual setup needed.

## Attribution

SkillBridge was built on top of an existing open-source recruitment platform,
[`AIWITHKAUSHAL/full-stack-recruitment-platform`](https://github.com/AIWITHKAUSHAL/full-stack-recruitment-platform),
which provided the initial backend/frontend structure and a recruiter-facing
ATS. The student-facing readiness product — skill matching, readiness
scoring, preparation plans, interview prep, job comparison, skill progress,
and job-URL import — was built on top of that foundation.

## Future Improvements

- Readiness history/trends over time, not just a snapshot
- Ranked job recommendations with a stated reason
- Admin-editable skill catalog
- Richer job-URL extraction for sites without structured data
