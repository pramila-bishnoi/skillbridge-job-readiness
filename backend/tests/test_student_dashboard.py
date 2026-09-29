"""SkillBridge Phase 7 student-dashboard-summary integration tests."""

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


def _upload_resume(client, token: str, text: str):
    return client.post(
        "/api/v1/student/profile/resume",
        headers=_headers(token),
        files={
            "resume": (
                "resume.docx",
                _resume_bytes(text),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )


def _create_job(client, token: str, description: str, title: str):
    response = client.post(
        "/api/v1/student/jobs", headers=_headers(token), json={"title": title, "description": description}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_empty_dashboard_for_a_new_student(client):
    token = _create_student(client)

    response = client.get("/api/v1/student/dashboard", headers=_headers(token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tracked_skills_count"] == 0
    assert body["analyzed_jobs_count"] == 0
    assert body["average_readiness_score"] is None
    assert body["best_readiness_job"] is None
    assert body["recent_skill_progress"] == []


def test_dashboard_reflects_skill_progress_counts(client):
    token = _create_student(client)
    profile = _upload_resume(client, token, "Python Docker").json()
    docker_id = next(s["skill_id"] for s in profile["extracted_skills"] if s["name"] == "Docker")
    python_id = next(s["skill_id"] for s in profile["extracted_skills"] if s["name"] == "Python")

    client.patch(f"/api/v1/student/skill-progress/{docker_id}", headers=_headers(token), json={"status": "LEARNING"})
    client.patch(f"/api/v1/student/skill-progress/{python_id}", headers=_headers(token), json={"status": "CONFIDENT"})

    body = client.get("/api/v1/student/dashboard", headers=_headers(token)).json()

    assert body["tracked_skills_count"] == 2
    assert body["learning_count"] == 1
    assert body["confident_count"] == 1
    assert body["not_started_count"] == 0
    assert len(body["recent_skill_progress"]) == 2


def test_dashboard_shows_average_and_best_readiness_score(client):
    token = _create_student(client)
    job_a = _create_job(client, token, "Requirements:\n- Python\n", "Job A")
    job_b = _create_job(client, token, "Requirements:\n- Python\n- Docker\n- AWS\n", "Job B")
    client.post(f"/api/v1/student/jobs/{job_a['id']}/readiness", headers=_headers(token))
    client.post(f"/api/v1/student/jobs/{job_b['id']}/readiness", headers=_headers(token))

    body = client.get("/api/v1/student/dashboard", headers=_headers(token)).json()

    assert body["analyzed_jobs_count"] == 2
    assert body["average_readiness_score"] is not None
    assert body["best_readiness_job"] is not None
    assert body["best_readiness_job"]["job_profile_id"] in {job_a["id"], job_b["id"]}


def test_dashboard_requires_authentication(client):
    assert client.get("/api/v1/student/dashboard").status_code == 401


def test_dashboard_is_scoped_to_the_requesting_student(client):
    owner_token = _create_student(client)
    profile = _upload_resume(client, owner_token, "Python").json()
    python_id = profile["extracted_skills"][0]["skill_id"]
    client.patch(
        f"/api/v1/student/skill-progress/{python_id}", headers=_headers(owner_token), json={"status": "CONFIDENT"}
    )

    other_token = _create_student(client, email="other@example.com")
    body = client.get("/api/v1/student/dashboard", headers=_headers(other_token)).json()

    assert body["tracked_skills_count"] == 0
