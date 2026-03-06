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


# ── public routes (no auth required) ──────────────────────────────────────────


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metrics_returns_prometheus_text(client: TestClient):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert b"http_requests_total" in response.content


def test_index_returns_200(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Planner Agent" in response.content


# ── protected routes (require auth) ───────────────────────────────────────────


def test_interview_redirects_when_unauthenticated(client: TestClient):
    response = client.get("/interview", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_interview_page_returns_200(auth_client: TestClient, csrf_token: str):
    response = auth_client.get("/interview")
    assert response.status_code == 200
    assert b"project_name" in response.content


def test_generate_redirects_to_gameplan(auth_client: TestClient, csrf_token: str):
    response = auth_client.post(
        "/generate",
        data={**_VALID_FORM, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/gameplan/")


def test_generate_and_view_gameplan(auth_client: TestClient, csrf_token: str):
    response = auth_client.post(
        "/generate",
        data={**_VALID_FORM, "csrf_token": csrf_token},
    )
    assert response.status_code == 200
    assert b"Test Project" in response.content


def test_gameplans_list(auth_client: TestClient, csrf_token: str):
    auth_client.post("/generate", data={**_VALID_FORM, "csrf_token": csrf_token})
    response = auth_client.get("/gameplans")
    assert response.status_code == 200
    assert b"Test Project" in response.content


def test_edit_gameplan_form_prefilled(auth_client: TestClient, csrf_token: str):
    r = auth_client.post(
        "/generate",
        data={**_VALID_FORM, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    record_id = r.headers["location"].split("/")[-1]
    response = auth_client.get(f"/gameplan/{record_id}/edit")
    assert response.status_code == 200
    assert b"Test Project" in response.content


def test_edit_gameplan_save(auth_client: TestClient, csrf_token: str):
    r = auth_client.post(
        "/generate",
        data={**_VALID_FORM, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    record_id = r.headers["location"].split("/")[-1]
    updated = {**_VALID_FORM, "project_name": "Updated Project", "csrf_token": csrf_token}
    r2 = auth_client.post(f"/gameplan/{record_id}/edit", data=updated, follow_redirects=False)
    assert r2.status_code == 303
    response = auth_client.get(f"/gameplan/{record_id}")
    assert b"Updated Project" in response.content


def test_delete_gameplan(auth_client: TestClient, csrf_token: str):
    r = auth_client.post(
        "/generate",
        data={**_VALID_FORM, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    record_id = r.headers["location"].split("/")[-1]
    r2 = auth_client.post(
        f"/gameplan/{record_id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert r2.status_code == 303
    assert r2.headers["location"] == "/gameplans"
    assert auth_client.get(f"/gameplan/{record_id}").status_code == 404


def test_download_gameplan(auth_client: TestClient, csrf_token: str):
    r = auth_client.post(
        "/generate",
        data={**_VALID_FORM, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    record_id = r.headers["location"].split("/")[-1]
    response = auth_client.get(f"/gameplan/{record_id}/download")
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert b"Test Project" in response.content


def test_generate_invalid_shows_form_errors(auth_client: TestClient, csrf_token: str):
    response = auth_client.post(
        "/generate",
        data={
            "project_name": "",
            "problem_statement": "x",
            "core_features": "y",
            "target_platform": "Web app (frontend + backend)",
            "csrf_token": csrf_token,
        },
    )
    assert response.status_code == 422


# ── shareable public links ─────────────────────────────────────────────────────

def _create_record_id(auth_client: TestClient, csrf_token: str) -> str:
    r = auth_client.post(
        "/generate",
        data={**_VALID_FORM, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    return r.headers["location"].split("/")[-1]


def test_public_view_unknown_token_returns_404(client: TestClient):
    response = client.get("/share/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_share_creates_public_link(auth_client: TestClient, csrf_token: str):
    record_id = _create_record_id(auth_client, csrf_token)
    r = auth_client.post(
        f"/gameplan/{record_id}/share",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    # The gameplan page should now show the share URL.
    page = auth_client.get(f"/gameplan/{record_id}")
    assert b"/share/" in page.content


def test_public_view_accessible_after_share(auth_client: TestClient, client: TestClient, csrf_token: str):
    record_id = _create_record_id(auth_client, csrf_token)
    auth_client.post(f"/gameplan/{record_id}/share", data={"csrf_token": csrf_token})
    # Extract the share token from the gameplan page.
    page = auth_client.get(f"/gameplan/{record_id}")
    # find href="/share/..." in the HTML
    import re
    match = re.search(rb'/share/([0-9a-f-]{36})', page.content)
    assert match, "share token not found in page"
    share_token = match.group(1).decode()
    # Anonymous user can view the shared page.
    public = client.get(f"/share/{share_token}")
    assert public.status_code == 200
    assert b"Test Project" in public.content


def test_public_download_accessible_after_share(auth_client: TestClient, client: TestClient, csrf_token: str):
    record_id = _create_record_id(auth_client, csrf_token)
    auth_client.post(f"/gameplan/{record_id}/share", data={"csrf_token": csrf_token})
    page = auth_client.get(f"/gameplan/{record_id}")
    import re
    match = re.search(rb'/share/([0-9a-f-]{36})', page.content)
    share_token = match.group(1).decode()
    dl = client.get(f"/share/{share_token}/download")
    assert dl.status_code == 200
    assert b"Test Project" in dl.content


def test_revoke_removes_public_access(auth_client: TestClient, client: TestClient, csrf_token: str):
    record_id = _create_record_id(auth_client, csrf_token)
    auth_client.post(f"/gameplan/{record_id}/share", data={"csrf_token": csrf_token})
    page = auth_client.get(f"/gameplan/{record_id}")
    import re
    match = re.search(rb'/share/([0-9a-f-]{36})', page.content)
    share_token = match.group(1).decode()
    # Revoke.
    auth_client.post(f"/gameplan/{record_id}/revoke", data={"csrf_token": csrf_token})
    # Public link should now 404.
    assert client.get(f"/share/{share_token}").status_code == 404


def test_share_is_idempotent(auth_client: TestClient, csrf_token: str):
    record_id = _create_record_id(auth_client, csrf_token)
    auth_client.post(f"/gameplan/{record_id}/share", data={"csrf_token": csrf_token})
    page1 = auth_client.get(f"/gameplan/{record_id}")
    import re
    token1 = re.search(rb'/share/([0-9a-f-]{36})', page1.content).group(1)
    # Share again — token must not change.
    auth_client.post(f"/gameplan/{record_id}/share", data={"csrf_token": csrf_token})
    page2 = auth_client.get(f"/gameplan/{record_id}")
    token2 = re.search(rb'/share/([0-9a-f-]{36})', page2.content).group(1)
    assert token1 == token2


def test_download_post_returns_attachment(auth_client: TestClient, csrf_token: str):
    response = auth_client.post(
        "/download",
        data={**_VALID_FORM, "csrf_token": csrf_token},
    )
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert b"Test Project" in response.content


def test_download_post_missing_field_returns_422(auth_client: TestClient, csrf_token: str):
    response = auth_client.post(
        "/download",
        data={
            "project_name": "",
            "problem_statement": "x",
            "core_features": "y",
            "target_platform": "Web app (frontend + backend)",
            "csrf_token": csrf_token,
        },
    )
    assert response.status_code == 422


def test_csrf_rejection_on_generate(auth_client: TestClient):
    """POST /generate with wrong CSRF token must return 403."""
    response = auth_client.post(
        "/generate",
        data={**_VALID_FORM, "csrf_token": "bad-token"},
    )
    assert response.status_code == 403


def test_ownership_enforced(session, user, auth_client: TestClient, csrf_token: str):
    """A second user cannot view the first user's gameplan."""
    from app.auth import _signer, hash_password
    from app.models.project import User

    other = User(username="other", hashed_password=hash_password("pw"))
    session.add(other)
    session.commit()
    session.refresh(other)

    # Create a gameplan as user 1
    r = auth_client.post(
        "/generate",
        data={**_VALID_FORM, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    record_id = r.headers["location"].split("/")[-1]

    # Try to view it as user 2
    other_token = _signer.sign(str(other.id)).decode()
    from app.auth import _csrf_serializer
    other_csrf = _csrf_serializer.dumps("csrf")
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_session
    app.dependency_overrides[get_session] = lambda: session
    other_client = TestClient(
        app,
        cookies={"session": other_token, "csrf_token": other_csrf},
    )
    resp = other_client.get(f"/gameplan/{record_id}")
    assert resp.status_code == 403
