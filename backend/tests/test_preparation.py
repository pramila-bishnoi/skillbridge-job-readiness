"""SkillBridge Phase 5 preparation-plan integration tests."""

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


def _run_readiness(client, token: str, job_id: int):
    response = client.post(f"/api/v1/student/jobs/{job_id}/readiness", headers=_headers(token))
    assert response.status_code == 200, response.text
    return response.json()


JOB_DESCRIPTION = (
    "We are looking for a backend engineer.\n\n"
    "Requirements:\n"
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
# Redis (preferred) as gaps.
STUDENT_RESUME = "Experience with Python, FastAPI, PostgreSQL and Git tooling."


def _setup_plan(client, token=None):
    token = token or _create_student(client)
    _upload_resume(client, token, STUDENT_RESUME)
    job = _create_job(client, token, JOB_DESCRIPTION)
    _run_readiness(client, token, job["id"])
    return token, job


def test_generate_plan_creates_one_item_per_missing_skill(client):
    token, job = _setup_plan(client)

    response = client.post(f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token))

    assert response.status_code == 200, response.text
    body = response.json()
    names = {item["name"] for item in body["items"]}
    assert names == {"Docker", "AWS", "Redis"}
    assert body["total_items"] == 3
    assert body["not_started_items"] == 3
    assert body["completed_items"] == 0
    assert body["progress_percent"] == 0.0


def test_generated_items_have_deterministic_priority_reason_and_learning_focus(client):
    token, job = _setup_plan(client)
    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token)
    ).json()

    by_name = {item["name"]: item for item in body["items"]}
    assert by_name["Docker"]["priority"] == "HIGH"
    assert by_name["Docker"]["gap_type"] == "MISSING_REQUIRED"
    assert "Docker" in by_name["Docker"]["reason"]
    assert "required" in by_name["Docker"]["reason"]
    assert "Dockerfile" in by_name["Docker"]["learning_focus"]

    assert by_name["Redis"]["priority"] == "MEDIUM"
    assert by_name["Redis"]["gap_type"] == "MISSING_PREFERRED"
    assert "preferred" in by_name["Redis"]["reason"]

    assert by_name["AWS"]["priority"] == "HIGH"
    assert "EC2" in by_name["AWS"]["learning_focus"]

    # Sorted HIGH -> MEDIUM -> LOW.
    priorities = [item["priority"] for item in body["items"]]
    assert priorities == sorted(priorities, key=lambda p: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[p])


def test_related_skill_gap_produces_a_low_priority_item(client):
    token = _create_student(client)
    # Student knows Django (related to Python), never says "Python" itself.
    _upload_resume(client, token, "Experienced Django developer.")
    job = _create_job(client, token, "Requirements:\n- Python\n")
    _run_readiness(client, token, job["id"])

    body = client.post(
        f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token)
    ).json()

    python_item = next(item for item in body["items"] if item["name"] == "Python")
    assert python_item["gap_type"] == "RELATED"
    assert python_item["priority"] == "LOW"
    assert "Django" in python_item["reason"]


def test_get_returns_404_before_a_plan_has_been_generated(client):
    token, job = _setup_plan(client)

    response = client.get(f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PREPARATION_PLAN_NOT_FOUND"


def test_generate_returns_404_before_readiness_has_ever_run(client):
    token = _create_student(client)
    job = _create_job(client, token, JOB_DESCRIPTION)

    response = client.post(f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MATCH_ANALYSIS_NOT_FOUND"


def test_get_returns_the_plan_after_it_has_been_generated(client):
    token, job = _setup_plan(client)
    client.post(f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token))

    response = client.get(f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token))

    assert response.status_code == 200
    assert {item["name"] for item in response.json()["items"]} == {"Docker", "AWS", "Redis"}


def test_update_item_status_changes_it_and_recomputes_progress(client):
    token, job = _setup_plan(client)
    plan = client.post(
        f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token)
    ).json()
    docker_item = next(item for item in plan["items"] if item["name"] == "Docker")

    response = client.patch(
        f"/api/v1/student/jobs/{job['id']}/preparation/items/{docker_item['id']}",
        headers=_headers(token),
        json={"status": "COMPLETED"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    updated = next(item for item in body["items"] if item["id"] == docker_item["id"])
    assert updated["status"] == "COMPLETED"
    assert body["completed_items"] == 1
    assert body["not_started_items"] == 2
    assert body["progress_percent"] == round(1 / 3 * 100, 1)


def test_regenerating_preserves_status_for_a_skill_still_missing(client):
    token, job = _setup_plan(client)
    plan = client.post(
        f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token)
    ).json()
    docker_item = next(item for item in plan["items"] if item["name"] == "Docker")
    client.patch(
        f"/api/v1/student/jobs/{job['id']}/preparation/items/{docker_item['id']}",
        headers=_headers(token),
        json={"status": "IN_PROGRESS"},
    )

    # Regenerate without anything changing — Docker is still missing.
    regenerated = client.post(
        f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token)
    ).json()

    docker_after = next(item for item in regenerated["items"] if item["name"] == "Docker")
    assert docker_after["id"] == docker_item["id"]
    assert docker_after["status"] == "IN_PROGRESS"


def test_regenerating_removes_a_skill_that_is_no_longer_missing(client):
    token, job = _setup_plan(client)
    client.post(f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token))

    # The student updates their resume to also cover Docker, then reruns
    # readiness (Phase 4) and regenerates the plan (Phase 5).
    _upload_resume(client, token, STUDENT_RESUME + " Also skilled with Docker.")
    _run_readiness(client, token, job["id"])
    regenerated = client.post(
        f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token)
    ).json()

    names = {item["name"] for item in regenerated["items"]}
    assert "Docker" not in names
    assert names == {"AWS", "Redis"}
    assert regenerated["total_items"] == 2


def test_preparation_endpoints_require_authentication(client):
    assert client.post("/api/v1/student/jobs/1/preparation").status_code == 401
    assert client.get("/api/v1/student/jobs/1/preparation").status_code == 401
    assert (
        client.patch(
            "/api/v1/student/jobs/1/preparation/items/1", json={"status": "COMPLETED"}
        ).status_code
        == 401
    )


def test_student_cannot_generate_a_plan_for_another_students_job(client):
    owner_token, job = _setup_plan(client)
    other_token = _create_student(client, email="other@example.com")

    response = client.post(
        f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(other_token)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_PROFILE_NOT_FOUND"


def test_unknown_preparation_item_id_returns_404(client):
    token, job = _setup_plan(client)
    client.post(f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token))

    response = client.patch(
        f"/api/v1/student/jobs/{job['id']}/preparation/items/999999",
        headers=_headers(token),
        json={"status": "COMPLETED"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PREPARATION_ITEM_NOT_FOUND"


def test_plan_has_no_items_when_every_skill_is_matched(client):
    token = _create_student(client)
    _upload_resume(client, token, "Skilled in Python and Docker.")
    job = _create_job(client, token, "Requirements:\n- Python\n- Docker\n")
    _run_readiness(client, token, job["id"])

    body = client.post(f"/api/v1/student/jobs/{job['id']}/preparation", headers=_headers(token)).json()

    assert body["items"] == []
    assert body["total_items"] == 0
    assert body["progress_percent"] == 0.0
