"""Deterministic, explainable skill normalization.

Matches canonical skill names and their seeded aliases against free-form
resume text using word-boundary regular expressions — the same technique
Phase 1's hardcoded extractor used, but now driven by data in the
``skills``/``skill_aliases`` tables (via ``SkillRepository.list_catalog``)
instead of a fixed tuple in code, so a new synonym is a seed-data change, not
a code change.

Why word-boundary matching instead of naive substring search: "Java" must not
match inside "JavaScript". The lookbehind/lookahead below only exclude
adjacent letters/digits, so punctuation-bearing names like "C++" and
"Node.js" still match correctly, and "PostgreSQL" still matches inside the
phrase "PostgreSQL DB" (nothing alphanumeric follows it there).

No external NLP/LLM: this is intentionally the same small, auditable
technique as the rest of the matching code in this repository
(``services/matching.py``), per the SkillBridge direction of staying
deterministic and explainable first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.enums import SkillMatchType
from app.models.skill import Skill

_BOUNDARY_START = r"(?<![A-Za-z0-9])"
_BOUNDARY_END = r"(?![A-Za-z0-9])"


@dataclass(frozen=True)
class NormalizedSkillMatch:
    skill_id: int
    matched_text: str
    match_type: SkillMatchType


def _pattern(term: str) -> re.Pattern[str]:
    return re.compile(_BOUNDARY_START + re.escape(term) + _BOUNDARY_END, re.IGNORECASE)


def normalize_skills(text: str, catalog: list[Skill]) -> list[NormalizedSkillMatch]:
    """Return one match per skill found in ``text``, sorted by ``skill_id``.

    Every skill contributes its canonical name plus each alias as a candidate
    term; candidates are tried longest-first so that, when more than one of a
    skill's own terms would match (e.g. an alias and the canonical name both
    appearing), the more specific one is kept as the reported evidence. This
    does not change *which* skills are found — the word-boundary regex above
    already keeps distinct skills like "Java" and "JavaScript" from colliding
    on their own — it only picks the clearest ``matched_text`` to show back to
    the student.
    """
    if not text:
        return []

    candidates: list[tuple[str, int, SkillMatchType]] = []
    for skill in catalog:
        candidates.append((skill.name, skill.id, SkillMatchType.CANONICAL_NAME))
        for alias in skill.aliases:
            candidates.append((alias.alias, skill.id, SkillMatchType.ALIAS))
    candidates.sort(key=lambda item: len(item[0]), reverse=True)

    matches: dict[int, NormalizedSkillMatch] = {}
    for term, skill_id, match_type in candidates:
        if skill_id in matches or not term:
            continue
        found = _pattern(term).search(text)
        if found:
            matches[skill_id] = NormalizedSkillMatch(
                skill_id=skill_id, matched_text=found.group(0), match_type=match_type
            )
    return sorted(matches.values(), key=lambda match: match.skill_id)
