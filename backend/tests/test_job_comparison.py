"""SkillBridge Phase 7 job-comparison integration tests."""

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


def _create_job(client, token: str, description: str, title: str):
    response = client.post(
        "/api/v1/student/jobs", headers=_headers(token), json={"title": title, "description": description}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _run_readiness(client, token: str, job_id: int):
    response = client.post(f"/api/v1/student/jobs/{job_id}/readiness", headers=_headers(token))
    assert response.status_code == 200, response.text
    return response.json()


def _compare(client, token: str, job_profile_ids: list[int]):
    return client.post(
        "/api/v1/student/job-comparison",
        headers=_headers(token),
        json={"job_profile_ids": job_profile_ids},
    )


BACKEND_JD = "Requirements:\n- Python\n- Docker\n- AWS\n"
DATA_JD = "Requirements:\n- Python\n- SQL\n- Docker\n"


def test_compare_two_jobs_shows_readiness_side_by_side(client):
    token = _create_student(client)
    job_a = _create_job(client, token, BACKEND_JD, "Backend Engineer")
    job_b = _create_job(client, token, DATA_JD, "Data Engineer")
    _run_readiness(client, token, job_a["id"])
    _run_readiness(client, token, job_b["id"])

    response = _compare(client, token, [job_a["id"], job_b["id"]])

    assert response.status_code == 200, response.text
    body = response.json()
    ids = {entry["job_profile_id"] for entry in body["jobs"]}
    assert ids == {job_a["id"], job_b["id"]}
    for entry in body["jobs"]:
        assert "readiness_score" in entry


def test_common_and_unique_missing_skills_are_computed_correctly(client):
    token = _create_student(client)
    job_a = _create_job(client, token, BACKEND_JD, "Backend Engineer")
    job_b = _create_job(client, token, DATA_JD, "Data Engineer")
    _run_readiness(client, token, job_a["id"])
    _run_readiness(client, token, job_b["id"])

    body = _compare(client, token, [job_a["id"], job_b["id"]]).json()

    # Neither job's skills are matched (no resume uploaded), so Docker is
    # missing for both -> common_missing_skills; Python is required by both
    # -> common_skills; AWS/SQL are each unique to one job.
    assert "Docker" in body["common_missing_skills"]
    assert "Python" in body["common_skills"]
    by_id = {entry["job_profile_id"]: entry for entry in body["jobs"]}
    assert "AWS" in by_id[job_a["id"]]["unique_missing_skills"]
    assert "SQL" in by_id[job_b["id"]]["unique_missing_skills"]
    assert "Docker" not in by_id[job_a["id"]]["unique_missing_skills"]


def test_matched_skills_reflect_the_students_current_profile(client):
    token = _create_student(client)
    client.post(
        "/api/v1/student/profile/resume",
        headers=_headers(token),
        files={
            "resume": (
                "resume.docx",
                _resume_bytes("Skilled in Python and Docker."),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    job_a = _create_job(client, token, BACKEND_JD, "Backend Engineer")
    job_b = _create_job(client, token, DATA_JD, "Data Engineer")
    _run_readiness(client, token, job_a["id"])
    _run_readiness(client, token, job_b["id"])

    body = _compare(client, token, [job_a["id"], job_b["id"]]).json()

    by_id = {entry["job_profile_id"]: entry for entry in body["jobs"]}
    assert "Python" in by_id[job_a["id"]]["matched_skills"]
    assert "Docker" in by_id[job_a["id"]]["matched_skills"]
    assert "AWS" in by_id[job_a["id"]]["missing_skills"]


def test_requires_at_least_two_jobs(client):
    token = _create_student(client)
    job_a = _create_job(client, token, BACKEND_JD, "Backend Engineer")
    _run_readiness(client, token, job_a["id"])

    response = _compare(client, token, [job_a["id"]])

    assert response.status_code == 422


def test_rejects_more_than_five_jobs(client):
    token = _create_student(client)
    ids = []
    for i in range(6):
        job = _create_job(client, token, f"Requirements:\n- Python{i}\n", f"Role {i}")
        ids.append(job["id"])

    response = _compare(client, token, ids)

    assert response.status_code == 422


def test_rejects_duplicate_job_ids(client):
    token = _create_student(client)
    job_a = _create_job(client, token, BACKEND_JD, "Backend Engineer")

    response = _compare(client, token, [job_a["id"], job_a["id"]])

    assert response.status_code == 422


def test_fails_with_409_when_a_job_has_not_been_analyzed(client):
    token = _create_student(client)
    job_a = _create_job(client, token, BACKEND_JD, "Backend Engineer")
    job_b = _create_job(client, token, DATA_JD, "Data Engineer")
    _run_readiness(client, token, job_a["id"])
    # job_b never analyzed.

    response = _compare(client, token, [job_a["id"], job_b["id"]])

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "JOBS_NOT_ANALYZED"
    assert job_b["id"] in response.json()["error"]["details"]["job_profile_ids"]


def test_student_cannot_compare_another_students_job(client):
    owner_token = _create_student(client)
    job_a = _create_job(client, owner_token, BACKEND_JD, "Backend Engineer")
    _run_readiness(client, owner_token, job_a["id"])

    other_token = _create_student(client, email="other@example.com")
    job_b = _create_job(client, other_token, DATA_JD, "Data Engineer")
    _run_readiness(client, other_token, job_b["id"])

    response = _compare(client, other_token, [job_a["id"], job_b["id"]])

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_PROFILE_NOT_FOUND"


def test_comparison_requires_authentication(client):
    assert client.post("/api/v1/student/job-comparison", json={"job_profile_ids": [1, 2]}).status_code == 401


def _resume_bytes(text: str) -> bytes:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    document = BytesIO()
    with ZipFile(document, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return document.getvalue()
