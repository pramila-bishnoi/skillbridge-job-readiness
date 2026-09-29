"""Canonical skill catalog seed data.

Phase 2 (Skill Intelligence) replaces the Phase 1 hardcoded skill list
(previously ``services/skill_extraction.py``) with data: a canonical name plus
zero or more synonyms a resume might actually use. Adding a skill or a synonym
is then a change to this tuple, not a change to the matching logic.

This module is imported from two places that must seed the *same* catalog:

* ``alembic/versions/0004_skill_intelligence.py`` — real environments.
* the pytest fixture (``tests/conftest.py``) — the test database is built with
  ``Base.metadata.create_all`` (CLAUDE.md §7), which never runs a migration.

It stays plain data (no SQLAlchemy import) so both call sites can use it
without coupling a migration to application code that might change shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_key(value: str) -> str:
    """Lower-cased, whitespace-collapsed lookup key for a skill name or alias.

    Used only to keep the catalog free of duplicate rows (``"PostgreSQL"`` and
    ``" postgresql "`` must resolve to one seeded row) — actual resume matching
    is done with case-insensitive word-boundary regexes in
    ``services/skill_normalization.py``, not with this key.
    """
    return _WHITESPACE_RE.sub(" ", value.strip()).casefold()


@dataclass(frozen=True)
class SkillSeed:
    name: str
    category: str
    aliases: tuple[str, ...] = ()


# Categories are free text (like ``jobs.department``/``jobs.location``): a
# curated but unconstrained vocabulary, not a native enum a migration would
# need to widen every time a new category shows up.
SKILL_CATALOG: tuple[SkillSeed, ...] = (
    SkillSeed("Python", "language"),
    SkillSeed("JavaScript", "language", ("JS",)),
    SkillSeed("TypeScript", "language", ("TS",)),
    SkillSeed("Java", "language"),
    SkillSeed("C++", "language", ("Cpp", "C Plus Plus")),
    SkillSeed("C#", "language", ("C Sharp", "CSharp")),
    SkillSeed("SQL", "language"),
    SkillSeed("HTML", "language", ("HTML5",)),
    SkillSeed("CSS", "language", ("CSS3",)),
    SkillSeed("PostgreSQL", "database", ("Postgres", "Postgres SQL")),
    SkillSeed("MySQL", "database", ("My SQL",)),
    SkillSeed("MongoDB", "database", ("Mongo", "Mongo DB")),
    SkillSeed("Redis", "database"),
    SkillSeed("FastAPI", "framework", ("Fast API",)),
    SkillSeed("Django", "framework"),
    SkillSeed("Flask", "framework"),
    SkillSeed("React", "framework", ("ReactJS", "React.js", "React JS")),
    SkillSeed("Node.js", "framework", ("NodeJS", "Node JS")),
    SkillSeed("Express", "framework", ("Express.js", "ExpressJS")),
    SkillSeed("Tailwind CSS", "framework", ("TailwindCSS", "Tailwind")),
    SkillSeed("GraphQL", "concept"),
    SkillSeed("REST APIs", "concept", ("REST API", "RESTful API", "RESTful APIs")),
    SkillSeed("Machine Learning", "concept", ("ML",)),
    SkillSeed("Data Analysis", "concept"),
    SkillSeed("Docker", "devops"),
    SkillSeed("Kubernetes", "devops", ("K8s",)),
    SkillSeed("Terraform", "devops"),
    SkillSeed("GitHub Actions", "devops"),
    SkillSeed("Linux", "devops", ("GNU/Linux",)),
    SkillSeed("AWS", "cloud", ("Amazon Web Services",)),
    SkillSeed("Azure", "cloud", ("Microsoft Azure",)),
    SkillSeed("GCP", "cloud", ("Google Cloud Platform", "Google Cloud")),
    SkillSeed("Git", "tool"),
    SkillSeed("GitHub", "tool", ("Git Hub",)),
    SkillSeed("pytest", "tool"),
    SkillSeed("Testing Library", "tool", ("React Testing Library",)),
    SkillSeed("Pandas", "tool"),
    SkillSeed("NumPy", "tool"),
    SkillSeed("Figma", "tool"),
)


# Phase 4 (readiness/skill-gap engine): an explicit, curated set of skill
# relationships — never inferred at runtime. Each pair is included only where
# the relationship is uncontroversial and independently verifiable (a
# framework built on a language, two tools solving the same class of
# problem), and each entry is seeded as a row in BOTH directions (see
# ``SkillRepository``/migration ``0006_readiness_engine``), so "related to X"
# means the same thing regardless of which side of the pair a lookup starts
# from. A related skill is deliberately never treated as satisfying a
# requirement — see ``SkillGapType.RELATED`` in ``app/models/enums.py``.
SKILL_RELATIONSHIPS: tuple[tuple[str, str], ...] = (
    ("React", "JavaScript"),
    ("React", "TypeScript"),
    ("Node.js", "JavaScript"),
    ("Express", "Node.js"),
    ("Django", "Python"),
    ("Flask", "Python"),
    ("FastAPI", "Python"),
    ("Docker", "Kubernetes"),
    ("PostgreSQL", "SQL"),
    ("MySQL", "SQL"),
    ("TypeScript", "JavaScript"),
    ("Azure", "AWS"),
    ("GCP", "AWS"),
)


# Phase 5 (preparation plan): a short, concrete starting point for each
# catalog skill — plain code, not a database table, since it is static
# reference text rather than a per-skill relational fact (contrast with
# SKILL_RELATIONSHIPS above, which *is* seeded, because "A relates to B" is a
# fact two rows can express; "here is what to study" is just a string).
# Looked up by canonical skill name and copied onto a PreparationItem at
# generation time — see ``services/preparation_guidance.learning_focus_for``.
LEARNING_FOCUS: dict[str, str] = {
    "Python": "Core syntax, data structures, virtual environments, and writing a small script or CLI tool.",
    "JavaScript": "ES6+ syntax, async/await, the DOM, and building a small interactive script.",
    "TypeScript": "Static types, interfaces, generics, and converting a small JS file to TS.",
    "Java": "OOP fundamentals, collections, and building a simple console application.",
    "C++": "Memory management, pointers/references, and STL containers.",
    "C#": ".NET fundamentals, OOP syntax, and building a simple console application.",
    "SQL": "SELECT/JOIN/GROUP BY, indexes, and writing queries against a sample schema.",
    "HTML": "Semantic markup, forms, and accessibility basics.",
    "CSS": "Flexbox, Grid, and responsive layout basics.",
    "PostgreSQL": "Schema design, indexes, transactions, and running queries against a local database.",
    "MySQL": "Schema design, indexes, and running queries against a local database.",
    "MongoDB": "Documents/collections, basic queries, and when to use a document store vs. SQL.",
    "Redis": "Key-value basics, common data structures (lists, sets, hashes), and caching patterns.",
    "FastAPI": "Path/query parameters, Pydantic models, dependency injection, and building a small API.",
    "Django": "Models, views, templates, and the admin site on a small project.",
    "Flask": "Routes, templates, and building a small API or app.",
    "React": "Components, props/state, hooks, and building a small interactive UI.",
    "Node.js": "The event loop, npm, and building a small HTTP server.",
    "Express": "Routing, middleware, and building a small REST API.",
    "Tailwind CSS": "Utility classes, responsive variants, and building a layout without custom CSS.",
    "GraphQL": "Schemas, queries/mutations, and resolvers on a small example API.",
    "REST APIs": "Resource design, status codes, and versioning conventions.",
    "Machine Learning": "Core supervised-learning concepts and training a simple model on a small dataset.",
    "Data Analysis": "Data cleaning, aggregation, and summarizing a dataset with basic statistics.",
    "Docker": "Containers, images, Dockerfile, and basic deployment.",
    "Kubernetes": "Pods, deployments, services, and running a container on a local cluster.",
    "Terraform": "Providers, resources, state, and provisioning a small piece of infrastructure.",
    "GitHub Actions": "Workflows, jobs/steps, and building a simple CI pipeline.",
    "Linux": "The shell, file permissions, and common commands (grep, find, systemd basics).",
    "AWS": "EC2, S3, IAM, and basic cloud deployment.",
    "Azure": "Core compute/storage services and basic cloud deployment, mapped from AWS equivalents if already familiar.",
    "GCP": "Core compute/storage services and basic cloud deployment, mapped from AWS equivalents if already familiar.",
    "Git": "Branching, merging, and resolving a conflict in a practice repository.",
    "GitHub": "Pull requests, code review, and issue tracking on a small repository.",
    "pytest": "Fixtures, parametrization, and writing tests for a small existing project.",
    "Testing Library": "Querying rendered output and simulating user interaction in a component test.",
    "Pandas": "DataFrames, filtering/grouping, and basic data cleaning.",
    "NumPy": "Arrays, vectorized operations, and basic numerical computation.",
    "Figma": "Frames, components, and building a simple UI mockup.",
}
