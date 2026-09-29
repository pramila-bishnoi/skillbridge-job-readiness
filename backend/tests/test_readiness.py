"""SkillBridge Phase 4 job-readiness / skill-gap engine integration tests."""

from io import BytesIO
from zipfile import ZipFile


def _create_student(client, **overrides):
    payload = {"name": "Jordan Ellis", "email": "jordan.ellis@example.com"}
    payload.update(overrides)
    response = client.post("/api/v1/student/profiles", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _resume_docx(text: str) -> BytesIO:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    document = BytesIO()
    with ZipFile(document, "w") as archive:
        archive.writestr("word/document.xml", xml)
    document.seek(0)
    return document


def _upload_resume(client, token: str, text: str):
    return client.post(
        "/api/v1/student/profile/resume",
        headers=_headers(token),
        files={
            "resume": (
                "resume.docx",
                _resume_docx(text).getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )


def _create_job(client, token: str, description: str, title: str = "Backend Engineer"):
    response = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": title, "description": description},
    )
    assert response.status_code == 201, response.text
    return response.json()


JOB_DESCRIPTION = (
    "We are looking for a backend engineer.\n\n"
    "Requirements:\n"
    "- 3-5 years of experience\n"
    "- Python\n"
    "- FastAPI\n"
    "- PostgreSQL\n"
    "- Docker\n"
    "- AWS\n\n"
    "Preferred:\n"
    "- Git\n"
    "- Redis\n"
)

# Matches Python, FastAPI, PostgreSQL, Git; leaves Docker, AWS (required) and
# Redis (preferred) as gaps; 4 years of experience evidenced.
STUDENT_RESUME = "4 years of experience with Python, FastAPI, PostgreSQL and Git tooling."


def test_analyze_produces_matched_and_missing_skills_matching_the_example(client):
    token = _create_student(client)
    _upload_resume(client, token, STUDENT_RESUME)
    job = _create_job(client, token, JOB_DESCRIPTION)

    response = client.post(f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token))

    assert response.status_code == 200, response.text
    body = response.json()

    matched_required = {
        s["name"] for s in body["matched_skills"] if s["requirement_type"] == "REQUIRED"
    }
    missing_required = {
        s["name"] for s in body["missing_skills"] if s["requirement_type"] == "REQUIRED"
    }
    assert matched_required == {"Python", "FastAPI", "PostgreSQL"}
    assert missing_required == {"Docker", "AWS"}

    matched_preferred = {
        s["name"] for s in body["matched_skills"] if s["requirement_type"] == "PREFERRED"
    }
    missing_preferred = {
        s["name"] for s in body["missing_skills"] if s["requirement_type"] == "PREFERRED"
    }
    assert matched_preferred == {"Git"}
    assert missing_preferred == {"Redis"}

    assert body["required_matched_count"] == 3
    assert body["required_total_count"] == 5
    assert body["preferred_matched_count"] == 1
    assert body["preferred_total_count"] == 2


def test_readiness_score_components_are_all_present_and_explainable(client):
    token = _create_student(client)
    _upload_resume(client, token, STUDENT_RESUME)
    job = _create_job(client, token, JOB_DESCRIPTION)

    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token)
    ).json()

    assert 0.0 <= body["readiness_score"] <= 100.0
    assert body["required_skill_coverage"] == 60.0  # 3/5
    assert body["preferred_skill_coverage"] == 50.0  # 1/2
    assert body["experience_score"] > 0  # 4 detected years vs a 3-5 years requirement
    assert "3-5 years" in body["experience_evidence"]
    assert body["text_similarity_score"] >= 0.0
    assert body["score_version"] == "v1"
    # The formula: required*0.45 + preferred*0.15 + experience*0.20 + text*0.20
    expected = round(
        (
            (body["required_matched_count"] / body["required_total_count"]) * 0.45
            + (body["preferred_matched_count"] / body["preferred_total_count"]) * 0.15
            + (body["experience_score"] / 100) * 0.20
            + (body["text_similarity_score"] / 100) * 0.20
        )
        * 100,
        1,
    )
    assert body["readiness_score"] == expected


def test_related_skill_is_reported_but_never_treated_as_matched(client):
    token = _create_student(client)
    # Student knows Django (related to Python via the seeded relationship)
    # but never mentions "Python" itself.
    _upload_resume(client, token, "Experienced Django developer building web applications.")
    job = _create_job(client, token, "Requirements:\n- Python\n")

    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token)
    ).json()

    assert body["matched_skills"] == []
    python_gap = next(g for g in body["skill_gaps"] if g["name"] == "Python")
    assert python_gap["gap_type"] == "RELATED"
    assert python_gap["related_to_skill_name"] == "Django"
    assert python_gap["importance"] == "LOW"
    # A related skill must never silently count as required coverage.
    assert body["required_matched_count"] == 0


def test_missing_required_skill_has_high_importance_in_gaps(client):
    token = _create_student(client)
    _upload_resume(client, token, "Some unrelated background.")
    job = _create_job(client, token, "Requirements:\n- Docker\n")

    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token)
    ).json()

    gap = next(g for g in body["skill_gaps"] if g["name"] == "Docker")
    assert gap["gap_type"] == "MISSING_REQUIRED"
    assert gap["importance"] == "HIGH"


def test_missing_preferred_skill_has_medium_importance_in_gaps(client):
    token = _create_student(client)
    _upload_resume(client, token, "Some unrelated background.")
    job = _create_job(client, token, "Requirements:\n- Python\n\nPreferred:\n- Redis\n")

    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token)
    ).json()

    gap = next(g for g in body["skill_gaps"] if g["name"] == "Redis")
    assert gap["gap_type"] == "MISSING_PREFERRED"
    assert gap["importance"] == "MEDIUM"


def test_get_returns_404_before_any_analysis_has_run(client):
    token = _create_student(client)
    job = _create_job(client, token, JOB_DESCRIPTION)

    response = client.get(f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MATCH_ANALYSIS_NOT_FOUND"


def test_get_returns_the_latest_analysis_after_it_has_run(client):
    token = _create_student(client)
    _upload_resume(client, token, STUDENT_RESUME)
    job = _create_job(client, token, JOB_DESCRIPTION)
    client.post(f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token))

    response = client.get(f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token))

    assert response.status_code == 200
    assert response.json()["job_profile_id"] == job["id"]


def test_rerunning_analysis_after_a_resume_change_updates_in_place_not_duplicates(client):
    token = _create_student(client)
    _upload_resume(client, token, "No relevant skills at all.")
    job = _create_job(client, token, JOB_DESCRIPTION)

    first = client.post(
        f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token)
    ).json()
    assert first["required_matched_count"] == 0

    _upload_resume(client, token, STUDENT_RESUME)
    second = client.post(
        f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token)
    ).json()

    # Same analysis row (same id) recomputed in place, not a second row.
    assert second["id"] == first["id"]
    assert second["required_matched_count"] == 3

    latest = client.get(f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token)).json()
    assert latest["required_matched_count"] == 3


def test_dedicated_matched_missing_and_gaps_endpoints(client):
    token = _create_student(client)
    _upload_resume(client, token, STUDENT_RESUME)
    job = _create_job(client, token, JOB_DESCRIPTION)
    client.post(f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token))

    matched = client.get(
        f"/api/v1/student/jobs/{job['id']}/readiness/matched", headers=_headers(token)
    ).json()
    missing = client.get(
        f"/api/v1/student/jobs/{job['id']}/readiness/missing", headers=_headers(token)
    ).json()
    gaps = client.get(
        f"/api/v1/student/jobs/{job['id']}/readiness/gaps", headers=_headers(token)
    ).json()

    assert {s["name"] for s in matched} == {"Python", "FastAPI", "PostgreSQL", "Git"}
    assert {s["name"] for s in missing} == {"Docker", "AWS", "Redis"}
    assert {s["name"] for s in gaps} == {"Docker", "AWS", "Redis"}
    assert all(g["gap_type"] != "MATCHED" for g in gaps)


def test_readiness_endpoints_require_authentication(client):
    assert client.post("/api/v1/student/jobs/1/readiness").status_code == 401
    assert client.get("/api/v1/student/jobs/1/readiness").status_code == 401
    assert client.get("/api/v1/student/jobs/1/readiness/matched").status_code == 401
    assert client.get("/api/v1/student/jobs/1/readiness/missing").status_code == 401
    assert client.get("/api/v1/student/jobs/1/readiness/gaps").status_code == 401


def test_student_cannot_analyze_another_students_job(client):
    owner_token = _create_student(client)
    job = _create_job(client, owner_token, JOB_DESCRIPTION)

    other_token = _create_student(client, email="other@example.com")
    response = client.post(
        f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(other_token)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_PROFILE_NOT_FOUND"


def test_unknown_job_profile_id_returns_404(client):
    token = _create_student(client)
    response = client.post("/api/v1/student/jobs/999999/readiness", headers=_headers(token))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_PROFILE_NOT_FOUND"


def test_job_with_no_required_or_preferred_skills_gets_full_skill_coverage(client):
    token = _create_student(client)
    _upload_resume(client, token, "Some background text with no catalog matches.")
    job = _create_job(client, token, "A friendly team looking for a great teammate to join us.")

    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/readiness", headers=_headers(token)
    ).json()

    assert body["required_total_count"] == 0
    assert body["preferred_total_count"] == 0
    assert body["required_skill_coverage"] == 100.0
    assert body["preferred_skill_coverage"] == 100.0
