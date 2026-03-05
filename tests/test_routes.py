from fastapi.testclient import TestClient

_VALID_FORM = {
    "project_name": "Test Project",
    "problem_statement": "Needs solving.",
    "core_features": "Feature A\nFeature B",
    "target_platform": "Web app (frontend + backend)",
    "preferred_language": "Python",
    "team_size": "solo",
    "timeline": "4 weeks",
    "constraints": "",
}


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_returns_200(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Planner Agent" in response.content


def test_interview_page_returns_200(client: TestClient):
    response = client.get("/interview")
    assert response.status_code == 200
    assert b"project_name" in response.content


def test_generate_redirects_to_gameplan(client: TestClient):
    response = client.post("/generate", data=_VALID_FORM, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/gameplan/")


def test_generate_and_view_gameplan(client: TestClient):
    response = client.post("/generate", data=_VALID_FORM)
    assert response.status_code == 200
    assert b"Test Project" in response.content


def test_gameplans_list(client: TestClient):
    client.post("/generate", data=_VALID_FORM)
    response = client.get("/gameplans")
    assert response.status_code == 200
    assert b"Test Project" in response.content


def test_edit_gameplan_form_prefilled(client: TestClient):
    r = client.post("/generate", data=_VALID_FORM, follow_redirects=False)
    record_id = r.headers["location"].split("/")[-1]
    response = client.get(f"/gameplan/{record_id}/edit")
    assert response.status_code == 200
    assert b"Test Project" in response.content


def test_edit_gameplan_save(client: TestClient):
    r = client.post("/generate", data=_VALID_FORM, follow_redirects=False)
    record_id = r.headers["location"].split("/")[-1]
    updated = {**_VALID_FORM, "project_name": "Updated Project"}
    r2 = client.post(f"/gameplan/{record_id}/edit", data=updated, follow_redirects=False)
    assert r2.status_code == 303
    response = client.get(f"/gameplan/{record_id}")
    assert b"Updated Project" in response.content


def test_delete_gameplan(client: TestClient):
    r = client.post("/generate", data=_VALID_FORM, follow_redirects=False)
    record_id = r.headers["location"].split("/")[-1]
    r2 = client.post(f"/gameplan/{record_id}/delete", follow_redirects=False)
    assert r2.status_code == 303
    assert r2.headers["location"] == "/gameplans"
    assert client.get(f"/gameplan/{record_id}").status_code == 404


def test_download_gameplan(client: TestClient):
    r = client.post("/generate", data=_VALID_FORM, follow_redirects=False)
    record_id = r.headers["location"].split("/")[-1]
    response = client.get(f"/gameplan/{record_id}/download")
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert b"Test Project" in response.content


def test_generate_invalid_shows_form_errors(client: TestClient):
    response = client.post(
        "/generate",
        data={
            "project_name": "",
            "problem_statement": "x",
            "core_features": "y",
            "target_platform": "Web app (frontend + backend)",
        },
    )
    assert response.status_code == 422
    assert b"This field is required" in response.content


def test_download_post_returns_attachment(client: TestClient):
    response = client.post("/download", data=_VALID_FORM)
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert b"Test Project" in response.content


def test_download_post_missing_field_returns_422(client: TestClient):
    response = client.post(
        "/download",
        data={
            "project_name": "",
            "problem_statement": "x",
            "core_features": "y",
            "target_platform": "Web app (frontend + backend)",
        },
    )
    assert response.status_code == 422
