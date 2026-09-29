# SkillBridge Architecture

A short technical reference for how SkillBridge is put together. For the
product overview, see the top-level [README](../README.md).

## Layering

Every backend feature follows the same layering, no exceptions:

```
route (FastAPI) → service (business rules) → repository (SQLAlchemy) → model
```

Routes are thin: resolve a dependency, call one service method, return a
schema. Services hold business rules and never construct SQL directly. Only
repository modules build `select()` queries. This convention is inherited
from the original recruitment-platform foundation and applied consistently
to every SkillBridge feature built on top of it.

## Data model

One PostgreSQL database, versioned by Alembic. SkillBridge-specific tables:

- `student_profiles` — the student account (no password; a bearer token is
  issued at creation).
- `skills`, `skill_aliases`, `skill_relations` — the canonical skill catalog
  and its seeded synonyms/relationships.
- `student_skills` — normalized skills extracted from a resume, with
  matched-text evidence.
- `job_profiles`, `job_skills` — a saved/analyzed job description and its
  required/preferred skills.
- `match_analyses` (unique per student × job) and `skill_gaps` — the
  readiness analysis and its matched/missing/related breakdown.
- `preparation_plans`, `preparation_items` — a prioritized study list built
  from the skill gaps.
- `interview_topics`, `interview_questions` — practice questions grouped by
  category.
- `skill_progress` — a sparse table of student-tracked learning status per
  skill.

## Readiness scoring

`readiness_score = required×0.45 + preferred×0.15 + experience×0.20 + text_similarity×0.20`,
scaled to a percentage. Required-skill coverage carries the most weight
because it's the most direct signal a job posting gives; the other three are
real but secondary. The weights are a stated engineering choice, not fit
against outcome data — there's no "who got hired" dataset in this system to
fit against.

Text similarity reuses the inherited TF-IDF/cosine matching engine as one of
the four inputs, never the whole score. Every component is stored on its own
and shown to the student alongside the final number — nothing is collapsed
into an opaque single output.

## Skill matching

Skills are matched with a word-boundary regex against a canonical catalog
plus its seeded aliases (so "Postgres" and "PostgreSQL" resolve to one
skill), not a machine-learning model. The boundary check is what keeps
"Java" from matching inside "JavaScript." A "related" skill (e.g. Django to
Python) is only ever reported from an explicit, seeded relationship table —
never inferred at runtime.

## Job URL import

A student can paste a public job-posting URL instead of copying text by
hand. The backend validates the URL, blocks requests to private/internal
addresses (checked on every redirect hop, not just the initial URL), fetches
with a timeout and response-size cap, and prefers schema.org `JobPosting`
structured data when the page publishes it, falling back to plain HTML text
extraction otherwise. It never executes fetched JavaScript and never
attempts to bypass a login wall or CAPTCHA.

## Security

- Two independent JWT flows: an admin/recruiter token (bcrypt password,
  short-lived) and a student token (issued at profile creation, no
  password, longer-lived).
- A student can only ever read or write rows that belong to their own
  profile; an ownership mismatch returns 404, not 403, so it doesn't confirm
  another student's data exists.
- Resume uploads are validated by extension and content type, size-capped,
  and stored under a generated key — never the client's filename.
- No secrets are committed; all configuration comes from environment
  variables.

## Known limitations

- No readiness history over time — each (student, job) pair keeps only its
  latest analysis.
- No rate limiting on any endpoint.
- Skill matching is lexical, not semantic — a skill described in
  unfamiliar wording won't be recognized unless it's in the catalog.
- The skill catalog is seeded in code, not editable from the UI.

## Attribution

Built on the open-source
[`AIWITHKAUSHAL/full-stack-recruitment-platform`](https://github.com/AIWITHKAUSHAL/full-stack-recruitment-platform),
which supplied the layered architecture, auth pattern, and the inherited
ATS. The student-facing features described above are new work on top of
that foundation.
