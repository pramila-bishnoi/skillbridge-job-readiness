"""Unit tests for the deterministic skill-normalization matcher.

These construct the catalog in-memory (no database) since
``normalize_skills`` only reads ``name``/``category``/``aliases`` off the ORM
objects it is given — see ``app/services/skill_normalization.py``.
"""

from app.core.skill_catalog import SKILL_CATALOG, normalize_key
from app.models.enums import SkillMatchType
from app.models.skill import Skill, SkillAlias
from app.services.skill_normalization import normalize_skills


def _catalog() -> list[Skill]:
    catalog = []
    for skill_id, seed in enumerate(SKILL_CATALOG, start=1):
        skill = Skill(id=skill_id, name=seed.name, normalized_key=normalize_key(seed.name), category=seed.category)
        skill.aliases = [
            SkillAlias(skill_id=skill_id, alias=alias, normalized_key=normalize_key(alias))
            for alias in seed.aliases
        ]
        catalog.append(skill)
    return catalog


def _skill(catalog: list[Skill], name: str) -> Skill:
    return next(skill for skill in catalog if skill.name == name)


def test_postgres_alias_normalizes_to_postgresql():
    catalog = _catalog()
    postgres = _skill(catalog, "PostgreSQL")

    matches = normalize_skills("5 years with Postgres and Docker.", catalog)
    match = next(m for m in matches if m.skill_id == postgres.id)

    assert match.matched_text == "Postgres"
    assert match.match_type == SkillMatchType.ALIAS


def test_reactjs_alias_normalizes_to_react():
    catalog = _catalog()
    react = _skill(catalog, "React")

    matches = normalize_skills("Built dashboards in ReactJS.", catalog)
    match = next(m for m in matches if m.skill_id == react.id)

    assert match.matched_text == "ReactJS"
    assert match.match_type == SkillMatchType.ALIAS


def test_python_version_suffix_still_matches_canonical_name():
    catalog = _catalog()
    python = _skill(catalog, "Python")

    matches = normalize_skills("Comfortable with Python 3 and pytest.", catalog)
    match = next(m for m in matches if m.skill_id == python.id)

    assert match.matched_text == "Python"
    assert match.match_type == SkillMatchType.CANONICAL_NAME


def test_postgresql_db_phrase_matches_canonical_name_as_substring():
    catalog = _catalog()
    postgres = _skill(catalog, "PostgreSQL")

    matches = normalize_skills("Managed a PostgreSQL DB in production.", catalog)
    match = next(m for m in matches if m.skill_id == postgres.id)

    assert match.matched_text == "PostgreSQL"
    assert match.match_type == SkillMatchType.CANONICAL_NAME


def test_java_is_not_falsely_matched_inside_javascript():
    catalog = _catalog()
    matches = normalize_skills("Two years of JavaScript.", catalog)
    matched_names = {_id_to_name(catalog, m.skill_id) for m in matches}

    assert "JavaScript" in matched_names
    assert "Java" not in matched_names


def test_cpp_alias_and_punctuation_in_canonical_name_both_match():
    catalog = _catalog()
    matches = normalize_skills("Wrote C++ and used Cpp for embedded work.", catalog)
    matched_names = {_id_to_name(catalog, m.skill_id) for m in matches}

    assert "C++" in matched_names


def test_no_match_is_returned_for_unrelated_text():
    catalog = _catalog()
    assert normalize_skills("Enjoys hiking and painting on weekends.", catalog) == []


def test_empty_text_returns_no_matches():
    assert normalize_skills("", _catalog()) == []


def test_results_are_sorted_by_skill_id_and_deduplicated():
    catalog = _catalog()
    matches = normalize_skills("Python, Python, and more Python.", catalog)
    python = _skill(catalog, "Python")

    assert [m.skill_id for m in matches] == [python.id]


def _id_to_name(catalog: list[Skill], skill_id: int) -> str:
    return next(skill.name for skill in catalog if skill.id == skill_id)
