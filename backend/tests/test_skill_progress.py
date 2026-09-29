"""SkillBridge Phase 7 skill-progress integration tests."""


def _create_student(client, **overrides):
    payload = {"name": "Jordan Ellis", "email": "jordan.ellis@example.com"}
    payload.update(overrides)
    response = client.post("/api/v1/student/profiles", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _skill_id(client, token: str, name: str) -> int:
    """Skill ids aren't exposed anywhere a student creates them directly, so
    tests discover a real catalog id via the normalized-skill list after a
    tiny resume upload — the same catalog every other Phase 2+ test uses."""
    from io import BytesIO
    from zipfile import ZipFile

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{name}</w:t></w:r></w:p></w:body></w:document>"
    )
    document = BytesIO()
    with ZipFile(document, "w") as archive:
        archive.writestr("word/document.xml", xml)
    response = client.post(
        "/api/v1/student/profile/resume",
        headers=_headers(token),
        files={
            "resume": (
                "resume.docx",
                document.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    skills = response.json()["extracted_skills"]
    match = next(s for s in skills if s["name"] == name)
    return match["skill_id"]


def test_list_is_empty_before_any_status_is_set(client):
    token = _create_student(client)
    response = client.get("/api/v1/student/skill-progress", headers=_headers(token))
    assert response.status_code == 200
    assert response.json() == []


def test_update_creates_a_progress_row(client):
    token = _create_student(client)
    skill_id = _skill_id(client, token, "Docker")

    response = client.patch(
        f"/api/v1/student/skill-progress/{skill_id}",
        headers=_headers(token),
        json={"status": "LEARNING"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["skill_id"] == skill_id
    assert body["name"] == "Docker"
    assert body["status"] == "LEARNING"
    assert body["updated_at"]


def test_update_again_changes_status_in_place_not_a_second_row(client):
    token = _create_student(client)
    skill_id = _skill_id(client, token, "Docker")

    client.patch(
        f"/api/v1/student/skill-progress/{skill_id}", headers=_headers(token), json={"status": "LEARNING"}
    )
    client.patch(
        f"/api/v1/student/skill-progress/{skill_id}", headers=_headers(token), json={"status": "CONFIDENT"}
    )

    response = client.get("/api/v1/student/skill-progress", headers=_headers(token))
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["status"] == "CONFIDENT"


def test_updated_at_changes_on_a_status_update(client):
    token = _create_student(client)
    skill_id = _skill_id(client, token, "Docker")

    first = client.patch(
        f"/api/v1/student/skill-progress/{skill_id}", headers=_headers(token), json={"status": "LEARNING"}
    ).json()
    second = client.patch(
        f"/api/v1/student/skill-progress/{skill_id}", headers=_headers(token), json={"status": "PRACTICED"}
    ).json()

    assert second["updated_at"] >= first["updated_at"]


def test_progress_can_be_set_for_a_skill_not_on_the_current_resume(client):
    token = _create_student(client)
    python_id = _skill_id(client, token, "Python")
    # Re-uploading replaces normalized skills (Phase 2), so Python is no
    # longer in extracted_skills after this — but its skill id is still a
    # valid, settable catalog id, since progress tracks intent to learn a
    # skill, not just what the resume currently says.
    _skill_id(client, token, "Docker")

    response = client.patch(
        f"/api/v1/student/skill-progress/{python_id}",
        headers=_headers(token),
        json={"status": "LEARNING"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Python"


def test_unknown_skill_id_returns_404(client):
    token = _create_student(client)
    response = client.patch(
        "/api/v1/student/skill-progress/999999", headers=_headers(token), json={"status": "LEARNING"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SKILL_NOT_FOUND"


def test_invalid_status_value_is_rejected(client):
    token = _create_student(client)
    skill_id = _skill_id(client, token, "Docker")
    response = client.patch(
        f"/api/v1/student/skill-progress/{skill_id}",
        headers=_headers(token),
        json={"status": "EXPERT"},
    )
    assert response.status_code == 422


def test_skill_progress_endpoints_require_authentication(client):
    assert client.get("/api/v1/student/skill-progress").status_code == 401
    assert client.get("/api/v1/student/skill-progress/catalog").status_code == 401
    assert (
        client.patch("/api/v1/student/skill-progress/1", json={"status": "LEARNING"}).status_code
        == 401
    )


def test_catalog_lists_skills_alphabetically_including_ones_not_tracked(client):
    token = _create_student(client)

    response = client.get("/api/v1/student/skill-progress/catalog", headers=_headers(token))

    assert response.status_code == 200
    entries = response.json()
    assert len(entries) > 30  # the full Phase 2 catalog, not just tracked ones
    names = [e["name"] for e in entries]
    assert names == sorted(names)
    assert all(e["skill_id"] and e["name"] for e in entries)


def test_one_students_progress_is_not_visible_to_another(client):
    owner_token = _create_student(client)
    skill_id = _skill_id(client, owner_token, "Docker")
    client.patch(
        f"/api/v1/student/skill-progress/{skill_id}",
        headers=_headers(owner_token),
        json={"status": "CONFIDENT"},
    )

    other_token = _create_student(client, email="other@example.com")
    response = client.get("/api/v1/student/skill-progress", headers=_headers(other_token))

    assert response.status_code == 200
    assert response.json() == []
