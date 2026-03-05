from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_returns_200():
    response = client.get("/")
    assert response.status_code == 200
    assert b"Planner Agent" in response.content


def test_interview_page_returns_200():
    response = client.get("/interview")
    assert response.status_code == 200
    assert b"project_name" in response.content


def test_generate_returns_gameplan():
    response = client.post(
        "/generate",
        data={
            "project_name": "Test Project",
            "problem_statement": "Needs solving.",
            "core_features": "Feature A\nFeature B",
            "target_platform": "Web app (frontend + backend)",
            "preferred_language": "Python",
            "team_size": "solo",
            "timeline": "4 weeks",
            "constraints": "",
        },
    )
    assert response.status_code == 200
    assert b"Test Project" in response.content


def test_generate_missing_required_field_returns_422():
    response = client.post(
        "/generate",
        data={
            "project_name": "",          # required but empty
            "problem_statement": "x",
            "core_features": "y",
            "target_platform": "Web app",
        },
    )
    # FastAPI returns 422 for validation errors
    assert response.status_code == 422


def test_download_returns_markdown_attachment():
    response = client.post(
        "/download",
        data={
            "project_name": "Download Test",
            "problem_statement": "Test problem.",
            "core_features": "Feature A\nFeature B",
            "target_platform": "Web app",
            "preferred_language": "Python",
            "team_size": "solo",
            "timeline": "2 weeks",
            "constraints": "",
        },
    )
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "download-test.md" in response.headers.get("content-disposition", "")
    assert "Download Test" in response.text


def test_download_missing_required_field_returns_422():
    response = client.post(
        "/download",
        data={
            "project_name": "",
            "problem_statement": "x",
            "core_features": "y",
            "target_platform": "Web app",
        },
    )
    assert response.status_code == 422
