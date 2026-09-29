"""Resume/job matching and recruiter ranking behavior."""

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.services.matching import score_pair
from tests.conftest import application_form


def test_score_pair_rewards_shared_role_terms():
    strong = score_pair("Python FastAPI PostgreSQL Terraform", "Python FastAPI PostgreSQL")
    weak = score_pair("Python FastAPI PostgreSQL Terraform", "Sales negotiation events")

    assert strong.score > weak.score
    assert "python" in strong.terms


def test_application_submission_persists_a_match_score(client, auth_headers, job):
    response = client.post(
        f"/api/v1/jobs/{job.id}/applications",
        data=application_form(experience="Python FastAPI development"),
    )

    assert response.status_code == 201
    body = client.get(
        "/api/v1/admin/applications", params={"search": response.json()["application_code"]},
        headers=auth_headers,
    )
    assert body.status_code == 200
    assert body.json()["items"][0]["match_score"] is not None


def test_ranked_endpoint_orders_candidates_by_current_job_match(client, db, auth_headers, job):
    first = Application(
        application_code="APP-2026-MATCH01", job_id=job.id, name="Strong Match",
        email="strong@example.com", phone="+91 9000000001", experience="Python FastAPI",
        resume_text="PostgreSQL Terraform", status=ApplicationStatus.APPLIED,
    )
    second = Application(
        application_code="APP-2026-MATCH02", job_id=job.id, name="Weak Match",
        email="weak@example.com", phone="+91 9000000002", experience="Sales events",
        resume_text="Recruiting outreach", status=ApplicationStatus.APPLIED,
    )
    db.add_all([first, second])
    db.commit()

    response = client.get(
        "/api/v1/admin/applications/ranked", params={"job_id": job.id}, headers=auth_headers
    )

    assert response.status_code == 200
    assert [row["name"] for row in response.json()["items"]] == ["Strong Match", "Weak Match"]
    assert response.json()["items"][0]["rank"] == 1