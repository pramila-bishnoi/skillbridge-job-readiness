"""SkillBridge Phase 3 job-description intelligence tests."""


def _create_student(client, **overrides):
    payload = {
        "name": "Jordan Ellis",
        "email": "jordan.ellis@example.com",
    }
    payload.update(overrides)
    response = client.post("/api/v1/student/profiles", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


JOB_DESCRIPTION = (
    "We are looking for a backend engineer to join our growing platform team.\n\n"
    "Requirements:\n"
    "- 3-5 years of experience\n"
    "- Strong Python and FastAPI skills\n"
    "- Experience with PostgreSQL\n\n"
    "Preferred:\n"
    "- Familiarity with Docker\n"
    "- AWS experience\n"
)


def test_create_job_profile_classifies_required_and_preferred_skills(client):
    token = _create_student(client)
    response = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={
            "title": "Backend Engineer",
            "company": "Acme Corp",
            "description": JOB_DESCRIPTION,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Backend Engineer"
    assert body["company"] == "Acme Corp"
    assert body["description"] == JOB_DESCRIPTION

    required_names = {s["name"] for s in body["required_skills"]}
    preferred_names = {s["name"] for s in body["preferred_skills"]}
    assert required_names == {"Python", "FastAPI", "PostgreSQL"}
    assert preferred_names == {"Docker", "AWS"}
    assert required_names.isdisjoint(preferred_names)


def test_create_job_profile_extracts_experience_requirement(client):
    token = _create_student(client)
    response = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": "Backend Engineer", "description": JOB_DESCRIPTION},
    )

    body = response.json()
    assert body["experience_required"] == "3-5 years"
    assert body["experience_evidence"] == "3-5 years"


def test_create_job_profile_without_sections_treats_everything_as_required(client):
    token = _create_student(client)
    description = "Looking for a Python developer with Docker and AWS experience for our team."
    response = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": "Python Developer", "description": description},
    )

    body = response.json()
    required_names = {s["name"] for s in body["required_skills"]}
    assert required_names == {"Python", "Docker", "AWS"}
    assert body["preferred_skills"] == []


def test_company_is_optional(client):
    token = _create_student(client)
    response = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": "Python Developer", "description": "Needs Python and SQL for this role today."},
    )

    assert response.status_code == 201, response.text
    assert response.json()["company"] is None


def test_get_job_profile_returns_full_detail(client):
    token = _create_student(client)
    created = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": "Backend Engineer", "description": JOB_DESCRIPTION},
    ).json()

    response = client.get(f"/api/v1/student/jobs/{created['id']}", headers=_headers(token))

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["title"] == "Backend Engineer"


def test_list_job_profiles_returns_summaries_with_skill_counts(client):
    token = _create_student(client)
    client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": "Backend Engineer", "description": JOB_DESCRIPTION},
    )
    client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": "Data Analyst", "description": "Needs SQL and Pandas experience for reporting."},
    )

    response = client.get("/api/v1/student/jobs", headers=_headers(token))

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    backend = next(i for i in items if i["title"] == "Backend Engineer")
    assert backend["required_skill_count"] == 3
    assert backend["preferred_skill_count"] == 2
    assert "description" not in backend


def test_reanalyze_job_profile_recomputes_skills(client):
    token = _create_student(client)
    created = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": "Backend Engineer", "description": JOB_DESCRIPTION},
    ).json()

    response = client.post(f"/api/v1/student/jobs/{created['id']}/analyze", headers=_headers(token))

    assert response.status_code == 200
    required_names = {s["name"] for s in response.json()["required_skills"]}
    assert required_names == {"Python", "FastAPI", "PostgreSQL"}


def test_job_profile_endpoints_require_authentication(client):
    assert client.get("/api/v1/student/jobs").status_code == 401
    assert client.get("/api/v1/student/jobs/1").status_code == 401
    assert client.post("/api/v1/student/jobs/1/analyze").status_code == 401
    assert (
        client.post(
            "/api/v1/student/jobs", json={"title": "X", "description": "y" * 30}
        ).status_code
        == 401
    )


def test_student_cannot_access_another_students_job_profile(client):
    owner_token = _create_student(client)
    created = client.post(
        "/api/v1/student/jobs",
        headers=_headers(owner_token),
        json={"title": "Backend Engineer", "description": JOB_DESCRIPTION},
    ).json()

    other_token = _create_student(client, email="other@example.com")

    get_response = client.get(f"/api/v1/student/jobs/{created['id']}", headers=_headers(other_token))
    analyze_response = client.post(
        f"/api/v1/student/jobs/{created['id']}/analyze", headers=_headers(other_token)
    )

    assert get_response.status_code == 404
    assert get_response.json()["error"]["code"] == "JOB_PROFILE_NOT_FOUND"
    assert analyze_response.status_code == 404


def test_unknown_job_profile_id_returns_404(client):
    token = _create_student(client)
    response = client.get("/api/v1/student/jobs/999999", headers=_headers(token))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_PROFILE_NOT_FOUND"


def test_description_too_short_is_rejected(client):
    token = _create_student(client)
    response = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={"title": "Backend Engineer", "description": "too short"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_is_empty_for_a_student_with_no_saved_jobs(client):
    token = _create_student(client)
    response = client.get("/api/v1/student/jobs", headers=_headers(token))
    assert response.status_code == 200
    assert response.json() == []
