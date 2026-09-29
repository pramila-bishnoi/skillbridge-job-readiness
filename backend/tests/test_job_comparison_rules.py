"""Unit tests for the deterministic job-comparison set math (no database)."""

from app.services.job_comparison_rules import JobSkillSets, compare


def test_common_skills_is_the_intersection_of_every_jobs_skill_set():
    job_a = JobSkillSets(job_profile_id=1, matched=frozenset({"Python"}), missing=frozenset({"Docker"}))
    job_b = JobSkillSets(job_profile_id=2, matched=frozenset({"Python", "SQL"}), missing=frozenset({"Docker"}))

    result = compare([job_a, job_b])

    assert result.common_skills == frozenset({"Python", "Docker"})


def test_common_missing_skills_is_the_intersection_of_missing_sets():
    job_a = JobSkillSets(job_profile_id=1, matched=frozenset(), missing=frozenset({"Docker", "AWS"}))
    job_b = JobSkillSets(job_profile_id=2, matched=frozenset(), missing=frozenset({"Docker", "Redis"}))

    result = compare([job_a, job_b])

    assert result.common_missing_skills == frozenset({"Docker"})


def test_unique_missing_skills_excludes_the_common_ones():
    job_a = JobSkillSets(job_profile_id=1, matched=frozenset(), missing=frozenset({"Docker", "AWS"}))
    job_b = JobSkillSets(job_profile_id=2, matched=frozenset(), missing=frozenset({"Docker", "Redis"}))

    result = compare([job_a, job_b])

    assert result.unique_missing_skills[1] == frozenset({"AWS"})
    assert result.unique_missing_skills[2] == frozenset({"Redis"})


def test_a_skill_matched_in_one_job_and_missing_in_another_is_still_common():
    # "considered" is matched | missing, so the skill is still something
    # every job cares about, even though only one job's analysis found it.
    job_a = JobSkillSets(job_profile_id=1, matched=frozenset({"Python"}), missing=frozenset())
    job_b = JobSkillSets(job_profile_id=2, matched=frozenset(), missing=frozenset({"Python"}))

    result = compare([job_a, job_b])

    assert "Python" in result.common_skills
    # But it is only a *missing* gap for job 2, not job 1.
    assert result.common_missing_skills == frozenset()
    assert result.unique_missing_skills[2] == frozenset({"Python"})


def test_three_way_comparison_intersects_across_all_jobs():
    job_a = JobSkillSets(job_profile_id=1, matched=frozenset(), missing=frozenset({"Docker", "AWS", "Redis"}))
    job_b = JobSkillSets(job_profile_id=2, matched=frozenset(), missing=frozenset({"Docker", "AWS"}))
    job_c = JobSkillSets(job_profile_id=3, matched=frozenset(), missing=frozenset({"Docker"}))

    result = compare([job_a, job_b, job_c])

    assert result.common_missing_skills == frozenset({"Docker"})
    assert result.unique_missing_skills[1] == frozenset({"AWS", "Redis"})
    assert result.unique_missing_skills[2] == frozenset({"AWS"})
    assert result.unique_missing_skills[3] == frozenset()


def test_empty_input_returns_empty_sets():
    result = compare([])
    assert result.common_skills == frozenset()
    assert result.common_missing_skills == frozenset()
    assert result.unique_missing_skills == {}
