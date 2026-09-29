"""SkillBridge Phase 1 student profile and resume intelligence tests."""

from io import BytesIO
from zipfile import ZipFile


def _create_profile(client, **overrides):
    payload = {
        "name": "Jordan Ellis",
        "email": "jordan.ellis@example.com",
        "education": "BSc Computer Science",
        "skills": "Communication",
        "projects": "Built a campus event planner.",
        "experience": "Student developer intern",
    }
    payload.update(overrides)
    response = client.post("/api/v1/student/profiles", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _resume_with_text(text: str) -> BytesIO:
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


def _docx_resume() -> BytesIO:
    return _resume_with_text("Python FastAPI PostgreSQL Docker AWS Git React.")


def _upload_resume(client, token: str, text: str):
    return client.post(
        "/api/v1/student/profile/resume",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "resume": (
                "resume.docx",
                _resume_with_text(text).getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )


def test_create_and_read_student_profile(client):
    created = _create_profile(client)
    response = client.get(
        "/api/v1/student/profile",
        headers={"Authorization": f"Bearer {created['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Jordan Ellis"
    assert response.json()["education"] == "BSc Computer Science"
    assert response.json()["extracted_skills"] == []


def test_student_profile_requires_its_own_token(client):
    created = _create_profile(client)
    assert client.get("/api/v1/student/profile").status_code == 401
    other = _create_profile(client, email="other@example.com")
    response = client.get(
        "/api/v1/student/profile",
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "other@example.com"
    assert response.json()["email"] != created["profile"]["email"]


def test_resume_upload_extracts_and_stores_known_skills(client):
    created = _create_profile(client)
    response = client.post(
        "/api/v1/student/profile/resume",
        headers={"Authorization": f"Bearer {created['access_token']}"},
        files={
            "resume": (
                "jordan.docx",
                _docx_resume().getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["resume_uploaded"] is True
    assert body["resume_filename"] == "jordan.docx"
    names = [skill["name"] for skill in body["extracted_skills"]]
    assert names == ["Python", "PostgreSQL", "FastAPI", "React", "Docker", "AWS", "Git"]

    python_skill = next(s for s in body["extracted_skills"] if s["name"] == "Python")
    assert python_skill["matched_text"] == "Python"
    assert python_skill["match_type"] == "CANONICAL_NAME"
    assert python_skill["category"] == "language"


def test_alias_normalization_maps_synonyms_to_canonical_skills(client):
    """The exact examples from the Phase 2 spec: "Postgres" -> PostgreSQL,
    "ReactJS" -> React, "Python 3" -> Python."""
    created = _create_profile(client)
    response = _upload_resume(
        client, created["access_token"], "Comfortable with Postgres, ReactJS and Python 3 projects."
    )

    assert response.status_code == 200, response.text
    skills = {s["name"]: s for s in response.json()["extracted_skills"]}
    assert skills["PostgreSQL"]["matched_text"] == "Postgres"
    assert skills["PostgreSQL"]["match_type"] == "ALIAS"
    assert skills["React"]["matched_text"] == "ReactJS"
    assert skills["React"]["match_type"] == "ALIAS"
    assert skills["Python"]["matched_text"] == "Python"
    assert skills["Python"]["match_type"] == "CANONICAL_NAME"


def test_canonical_name_embedded_in_a_longer_phrase_still_matches(client):
    """"PostgreSQL DB" -> PostgreSQL, via the canonical name appearing as a
    substring rather than a seeded alias."""
    created = _create_profile(client)
    response = _upload_resume(client, created["access_token"], "Strong PostgreSQL DB administration.")

    assert response.status_code == 200, response.text
    skills = {s["name"]: s for s in response.json()["extracted_skills"]}
    assert skills["PostgreSQL"]["matched_text"] == "PostgreSQL"
    assert skills["PostgreSQL"]["match_type"] == "CANONICAL_NAME"


def test_java_is_not_matched_inside_javascript(client):
    created = _create_profile(client)
    response = _upload_resume(client, created["access_token"], "Five years of JavaScript development.")

    assert response.status_code == 200, response.text
    names = {s["name"] for s in response.json()["extracted_skills"]}
    assert "JavaScript" in names
    assert "Java" not in names


def test_reuploading_a_resume_replaces_previous_skill_evidence(client):
    created = _create_profile(client)
    token = created["access_token"]
    first = _upload_resume(client, token, "Python and Docker experience.")
    assert {s["name"] for s in first.json()["extracted_skills"]} == {"Python", "Docker"}

    second = _upload_resume(client, token, "React and AWS experience.")
    assert {s["name"] for s in second.json()["extracted_skills"]} == {"React", "AWS"}


def test_get_profile_skills_endpoint_returns_normalized_skills(client):
    created = _create_profile(client)
    token = created["access_token"]
    _upload_resume(client, token, "Python and PostgreSQL background.")

    response = client.get(
        "/api/v1/student/profile/skills",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert {s["name"] for s in response.json()} == {"Python", "PostgreSQL"}


def test_profile_skills_endpoint_requires_authentication(client):
    assert client.get("/api/v1/student/profile/skills").status_code == 401


def test_invalid_student_resume_is_rejected(client):
    created = _create_profile(client)
    response = client.post(
        "/api/v1/student/profile/resume",
        headers={"Authorization": f"Bearer {created['access_token']}"},
        files={"resume": ("malware.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_RESUME"


def test_duplicate_student_email_is_rejected(client):
    _create_profile(client)
    response = client.post(
        "/api/v1/student/profiles",
        json={"name": "Another Jordan", "email": "JORDAN.ELLIS@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STUDENT_PROFILE_EXISTS"