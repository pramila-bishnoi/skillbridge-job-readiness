"""SkillBridge Phase 6 interview-preparation integration tests."""

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


def _update_profile(client, token: str, **fields):
    response = client.patch(
        "/api/v1/student/profile", headers=_headers(token), json=fields
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_job(client, token: str, description: str, title: str = "Backend Engineer"):
    response = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": title, "description": description},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _run_readiness(client, token: str, job_id: int):
    response = client.post(f"/api/v1/student/jobs/{job_id}/readiness", headers=_headers(token))
    assert response.status_code == 200, response.text
    return response.json()


JOB_DESCRIPTION = (
    "We are looking for a backend engineer.\n\n"
    "Requirements:\n"
    "- Python\n"
    "- FastAPI\n"
    "- Docker\n\n"
    "Preferred:\n"
    "- Redis\n"
)

# Matches Python, FastAPI; leaves Docker (required) and Redis (preferred) as gaps.
STUDENT_RESUME = "Experience with Python and FastAPI."
PROJECT_TEXT = "Built an ESP32-based home automation system using MQTT and a React dashboard."


def _setup(client, token=None, projects=PROJECT_TEXT, title="Backend Engineer", description=JOB_DESCRIPTION):
    token = token or _create_student(client)
    _upload_resume(client, token, STUDENT_RESUME)
    if projects is not None:
        _update_profile(client, token, projects=projects)
    job = _create_job(client, token, description, title=title)
    _run_readiness(client, token, job["id"])
    return token, job


def test_generate_produces_questions_across_all_four_categories(client):
    token, job = _setup(client)

    response = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    categories = {q["category"] for q in body["questions"]}
    assert categories == {"TECHNICAL", "SKILL_GAP", "RESUME_PROJECT", "ROLE_CONCEPT"}


def test_matched_skill_produces_a_technical_question(client):
    token, job = _setup(client)
    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()

    python_q = next(q for q in body["questions"] if q["related_skill_name"] == "Python")
    assert python_q["category"] == "TECHNICAL"
    assert python_q["difficulty"] == "HARD"  # Python is required
    assert "Python" in python_q["question"]


def test_missing_required_skill_produces_a_skill_gap_question(client):
    token, job = _setup(client)
    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()

    docker_q = next(q for q in body["questions"] if q["related_skill_name"] == "Docker")
    assert docker_q["category"] == "SKILL_GAP"
    assert docker_q["difficulty"] == "MEDIUM"
    assert "Docker" in docker_q["question"]


def test_missing_preferred_skill_produces_an_easy_skill_gap_question(client):
    token, job = _setup(client)
    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()

    redis_q = next(q for q in body["questions"] if q["related_skill_name"] == "Redis")
    assert redis_q["category"] == "SKILL_GAP"
    assert redis_q["difficulty"] == "EASY"


def test_project_question_quotes_the_esp32_project_verbatim(client):
    token, job = _setup(client)
    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()

    project_questions = [q for q in body["questions"] if q["category"] == "RESUME_PROJECT"]
    assert len(project_questions) == 1
    assert "ESP32" in project_questions[0]["question"]
    assert project_questions[0]["related_skill_name"] is None


def test_no_project_questions_when_profile_has_no_projects_text(client):
    token, job = _setup(client, projects="")

    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()

    assert [q for q in body["questions"] if q["category"] == "RESUME_PROJECT"] == []


def test_role_concept_questions_mention_the_job_title(client):
    token, job = _setup(client, title="Data Analyst")
    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()

    role_questions = [q for q in body["questions"] if q["category"] == "ROLE_CONCEPT"]
    assert len(role_questions) == 2
    assert all("Data Analyst" in q["question"] for q in role_questions)


def test_related_skill_gap_produces_a_low_difficulty_question_naming_the_related_skill(client):
    token = _create_student(client)
    _upload_resume(client, token, "Experienced Django developer.")
    job = _create_job(client, token, "Requirements:\n- Python\n")
    _run_readiness(client, token, job["id"])

    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()

    python_q = next(q for q in body["questions"] if q["related_skill_name"] == "Python")
    assert python_q["category"] == "SKILL_GAP"
    assert python_q["difficulty"] == "EASY"
    assert "Django" in python_q["question"]


def test_get_returns_404_before_prep_has_been_generated(client):
    token, job = _setup(client)

    response = client.get(f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INTERVIEW_PREP_NOT_FOUND"


def test_generate_returns_404_before_readiness_has_ever_run(client):
    token = _create_student(client)
    job = _create_job(client, token, JOB_DESCRIPTION)

    response = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MATCH_ANALYSIS_NOT_FOUND"


def test_get_returns_the_prep_after_it_has_been_generated(client):
    token, job = _setup(client)
    client.post(f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token))

    response = client.get(f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token))

    assert response.status_code == 200
    assert response.json()["job_profile_id"] == job["id"]


def test_update_question_completed_and_progress_recomputes(client):
    token, job = _setup(client)
    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()
    question_id = body["questions"][0]["id"]

    response = client.patch(
        f"/api/v1/student/jobs/{job['id']}/interview-prep/questions/{question_id}",
        headers=_headers(token),
        json={"completed": True},
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    changed = next(q for q in updated["questions"] if q["id"] == question_id)
    assert changed["completed"] is True
    assert updated["completed_questions"] == 1
    assert updated["progress_percent"] == round(1 / updated["total_questions"] * 100, 1)


def test_regenerating_preserves_completed_status_for_an_unchanged_question(client):
    token, job = _setup(client)
    first = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()
    docker_q = next(q for q in first["questions"] if q["related_skill_name"] == "Docker")
    client.patch(
        f"/api/v1/student/jobs/{job['id']}/interview-prep/questions/{docker_q['id']}",
        headers=_headers(token),
        json={"completed": True},
    )

    # Regenerate without anything underlying changing.
    regenerated = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()

    docker_after = next(q for q in regenerated["questions"] if q["related_skill_name"] == "Docker")
    assert docker_after["question"] == docker_q["question"]
    assert docker_after["completed"] is True


def test_regenerating_drops_a_question_for_a_skill_that_is_no_longer_a_gap(client):
    token, job = _setup(client)
    client.post(f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token))

    # Student updates their resume to also cover Docker, reruns readiness,
    # then regenerates interview prep.
    _upload_resume(client, token, STUDENT_RESUME + " Also skilled with Docker.")
    _run_readiness(client, token, job["id"])
    regenerated = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token)
    ).json()

    docker_questions = [q for q in regenerated["questions"] if q["related_skill_name"] == "Docker"]
    assert len(docker_questions) == 1
    assert docker_questions[0]["category"] == "TECHNICAL"  # now matched, not a gap


def test_interview_prep_endpoints_require_authentication(client):
    assert client.post("/api/v1/student/jobs/1/interview-prep").status_code == 401
    assert client.get("/api/v1/student/jobs/1/interview-prep").status_code == 401
    assert (
        client.patch(
            "/api/v1/student/jobs/1/interview-prep/questions/1", json={"completed": True}
        ).status_code
        == 401
    )


def test_student_cannot_generate_prep_for_another_students_job(client):
    owner_token, job = _setup(client)
    other_token = _create_student(client, email="other@example.com")

    response = client.post(
        f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(other_token)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_PROFILE_NOT_FOUND"


def test_unknown_question_id_returns_404(client):
    token, job = _setup(client)
    client.post(f"/api/v1/student/jobs/{job['id']}/interview-prep", headers=_headers(token))

    response = client.patch(
        f"/api/v1/student/jobs/{job['id']}/interview-prep/questions/999999",
        headers=_headers(token),
        json={"completed": True},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INTERVIEW_QUESTION_NOT_FOUND"
