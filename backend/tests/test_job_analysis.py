"""Unit tests for the deterministic job-description segmentation and
experience-requirement extraction (no database)."""

from app.services.job_analysis import extract_experience, segment_description


def test_segments_required_and_preferred_sections():
    description = (
        "We are hiring a backend engineer.\n\n"
        "Requirements:\n"
        "- Python\n"
        "- Docker\n\n"
        "Preferred:\n"
        "- AWS\n"
        "- Kubernetes\n"
    )
    segmented = segment_description(description)

    assert segmented.sections_detected is True
    assert "Python" in segmented.required_text
    assert "Docker" in segmented.required_text
    assert "AWS" in segmented.preferred_text
    assert "Kubernetes" in segmented.preferred_text
    assert "AWS" not in segmented.required_text
    assert "Python" not in segmented.preferred_text


def test_intro_text_before_first_heading_is_treated_as_required():
    description = "Join our Python and Docker focused team.\n\nRequirements:\n- SQL\n"
    segmented = segment_description(description)

    assert "Python" in segmented.required_text
    assert "SQL" in segmented.required_text


def test_no_headings_means_everything_is_required_and_nothing_is_preferred():
    description = "Looking for a Python developer with Docker and AWS experience."
    segmented = segment_description(description)

    assert segmented.sections_detected is False
    assert segmented.required_text == description
    assert segmented.preferred_text == ""


def test_requirements_word_mid_sentence_is_not_mistaken_for_a_heading():
    description = "Meeting the following requirements is expected: Python, Docker."
    segmented = segment_description(description)

    # The phrase never appears alone on its own line, so it is not a heading —
    # the whole paragraph stays in the (default) required text either way.
    assert segmented.sections_detected is False
    assert "Python" in segmented.required_text


def test_alternate_header_phrasing_nice_to_have_and_must_have():
    description = "Must have:\n- Java\n\nNice to have:\n- Redis\n"
    segmented = segment_description(description)

    assert "Java" in segmented.required_text
    assert "Redis" in segmented.preferred_text


def test_range_experience_with_to_separator():
    match = extract_experience("Looking for someone with 3 to 5 years of experience.")
    assert match is not None
    assert match.required == "3-5 years"
    assert match.evidence == "3 to 5 years"


def test_range_experience_with_hyphen():
    match = extract_experience("3-5 years in backend development.")
    assert match is not None
    assert match.required == "3-5 years"


def test_plus_experience():
    match = extract_experience("5+ years building production systems.")
    assert match is not None
    assert match.required == "5+ years"
    assert match.evidence == "5+ years"


def test_minimum_experience_phrasing():
    match = extract_experience("Minimum 2 years of professional experience required.")
    assert match is not None
    assert match.required == "2+ years"


def test_at_least_experience_phrasing():
    match = extract_experience("You should have at least 4 years of experience.")
    assert match is not None
    assert match.required == "4+ years"


def test_bare_years_experience():
    match = extract_experience("3 years of experience with SQL databases.")
    assert match is not None
    assert match.required == "3 years"


def test_no_experience_requirement_returns_none():
    assert extract_experience("A great opportunity for a motivated engineer.") is None
