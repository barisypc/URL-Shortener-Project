# backend/tests/test_urls_extra.py
from datetime import datetime, timedelta

from helpers import (
    auth_headers,
    ban,
    create_url,
    get_url_row,
    login,
    register,
    signup,
)

PC_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# --- /shorten variants --------------------------------------------------

def test_shorten_with_custom_code(client):
    headers = register(client, "s1", "s1@example.com")
    resp = client.post(
        "/shorten",
        json={"original_url": "https://example.com/a", "custom_code": "my-code"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["short_url"].endswith("/my-code")


def test_shorten_rejects_invalid_custom_code(client):
    headers = register(client, "s2", "s2@example.com")
    resp = client.post(
        "/shorten",
        json={"original_url": "https://example.com/a", "custom_code": "no spaces!"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_shorten_rejects_taken_custom_code(client):
    headers = register(client, "s3", "s3@example.com")
    client.post(
        "/shorten",
        json={"original_url": "https://example.com/a", "custom_code": "taken"},
        headers=headers,
    )
    resp = client.post(
        "/shorten",
        json={"original_url": "https://example.com/b", "custom_code": "taken"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_shorten_same_url_twice_reuses_existing_code(client):
    headers = register(client, "s4", "s4@example.com")
    first = create_url(client, headers, "https://example.com/same")
    second = create_url(client, headers, "https://example.com/same")
    assert first == second


def test_shorten_with_qr_code_returns_base64_image(client):
    headers = register(client, "s5", "s5@example.com")
    resp = client.post(
        "/shorten",
        json={"original_url": "https://example.com/qr", "qr_code": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["qr_code_image"].startswith("data:image/png;base64,")


def test_shorten_rejects_non_positive_expiration(client):
    headers = register(client, "s6", "s6@example.com")
    resp = client.post(
        "/shorten",
        json={"original_url": "https://example.com/e", "expiration_minutes": 0},
        headers=headers,
    )
    assert resp.status_code == 400


def test_shorten_rejects_non_positive_count_limit(client):
    headers = register(client, "s7", "s7@example.com")
    resp = client.post(
        "/shorten",
        json={"original_url": "https://example.com/c", "count_limit": 0},
        headers=headers,
    )
    assert resp.status_code == 400


def test_shorten_rejected_for_banned_user(client, db_session):
    headers = register(client, "s8", "s8@example.com")
    ban(db_session, "s8@example.com")

    resp = client.post(
        "/shorten", json={"original_url": "https://example.com/x"}, headers=headers
    )
    assert resp.status_code == 403


# --- my-urls / delete / validate ---------------------------------------

def test_list_my_urls_returns_only_own(client):
    headers_a = register(client, "m1", "m1@example.com")
    create_url(client, headers_a, "https://example.com/mine")

    signup(client, "m2", "m2@example.com")
    headers_b = auth_headers(login(client, "m2@example.com"))
    create_url(client, headers_b, "https://example.com/theirs")

    body = client.get("/api/my-urls", headers=headers_a).json()
    assert len(body) == 1
    assert body[0]["original_url"] == "https://example.com/mine"


def test_delete_url_success(client):
    headers = register(client, "del1", "del1@example.com")
    create_url(client, headers)
    url_id = client.get("/api/my-urls", headers=headers).json()[0]["id"]

    resp = client.delete(f"/api/delete-url/{url_id}", headers=headers)
    assert resp.status_code == 200
    assert client.get("/api/my-urls", headers=headers).json() == []


def test_delete_url_not_found(client):
    headers = register(client, "del2", "del2@example.com")
    resp = client.delete("/api/delete-url/9999", headers=headers)
    assert resp.status_code == 404


def test_validate_url_toggles_active_flag(client):
    headers = register(client, "v1", "v1@example.com")
    create_url(client, headers)
    url_id = client.get("/api/my-urls", headers=headers).json()[0]["id"]

    resp = client.patch(
        f"/api/validate-url/{url_id}", json={"is_active": False}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_validate_url_not_found(client):
    headers = register(client, "v2", "v2@example.com")
    resp = client.patch(
        "/api/validate-url/9999", json={"is_active": True}, headers=headers
    )
    assert resp.status_code == 404


# --- redirect (/{short_code}) -------------------------------------------

def test_redirect_success_and_records_click(client, db_session):
    headers = register(client, "rd1", "rd1@example.com")
    code = create_url(client, headers, "https://example.com/target")

    resp = client.get(
        f"/{code}", follow_redirects=False, headers={"user-agent": PC_UA}
    )
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "https://example.com/target"

    row = get_url_row(db_session, code)
    db_session.refresh(row)
    assert row.clicks == 1
    assert len(row.click_logs) == 1
    assert row.click_logs[0].accessed_platform == "PC"


def test_redirect_unknown_code_returns_404(client):
    resp = client.get("/nope404", follow_redirects=False)
    assert resp.status_code == 404


def test_redirect_inactive_url_returns_403(client, db_session):
    headers = register(client, "rd2", "rd2@example.com")
    code = create_url(client, headers)

    row = get_url_row(db_session, code)
    row.is_active = False
    db_session.commit()

    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 403


def test_redirect_expired_url_returns_410(client, db_session):
    headers = register(client, "rd3", "rd3@example.com")
    code = create_url(client, headers)

    row = get_url_row(db_session, code)
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 410


def test_redirect_click_limit_reached_returns_410_and_deactivates(client, db_session):
    headers = register(client, "rd4", "rd4@example.com")
    code = create_url(client, headers, "https://example.com/limited", count_limit=1)

    first = client.get(f"/{code}", follow_redirects=False)
    assert first.status_code in (302, 307)

    second = client.get(f"/{code}", follow_redirects=False)
    assert second.status_code == 410

    row = get_url_row(db_session, code)
    db_session.refresh(row)
    assert row.is_active is False


def test_redirect_blocked_when_owner_is_banned(client, db_session):
    headers = register(client, "rd5", "rd5@example.com")
    code = create_url(client, headers)
    ban(db_session, "rd5@example.com")

    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 403


def test_redirect_password_protected_goes_to_frontend_gate(client):
    headers = register(client, "rd6", "rd6@example.com")
    code = create_url(client, headers, "https://example.com/secret", password="hunter2")

    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].endswith(f"/protected/{code}")


# --- /api/protected/{short_code} ---------------------------------------

def test_verify_password_success(client, db_session):
    headers = register(client, "p1", "p1@example.com")
    code = create_url(client, headers, "https://example.com/secret", password="hunter2")

    resp = client.post(
        f"/api/protected/{code}",
        json={"password": "hunter2"},
        headers={"user-agent": PC_UA},
    )
    assert resp.status_code == 200
    assert resp.json()["original_url"] == "https://example.com/secret"

    row = get_url_row(db_session, code)
    db_session.refresh(row)
    assert row.clicks == 1


def test_verify_password_wrong_password_returns_401(client):
    headers = register(client, "p2", "p2@example.com")
    code = create_url(client, headers, "https://example.com/secret", password="hunter2")

    resp = client.post(f"/api/protected/{code}", json={"password": "wrong"})
    assert resp.status_code == 401


def test_verify_password_on_unprotected_url_returns_400(client):
    headers = register(client, "p3", "p3@example.com")
    code = create_url(client, headers, "https://example.com/open")

    resp = client.post(f"/api/protected/{code}", json={"password": "anything"})
    assert resp.status_code == 400


def test_verify_password_unknown_code_returns_404(client):
    resp = client.post("/api/protected/missing", json={"password": "x"})
    assert resp.status_code == 404


def test_verify_password_expired_url_returns_410(client, db_session):
    headers = register(client, "p4", "p4@example.com")
    code = create_url(client, headers, "https://example.com/secret", password="hunter2")

    row = get_url_row(db_session, code)
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    resp = client.post(f"/api/protected/{code}", json={"password": "hunter2"})
    assert resp.status_code == 410


# --- /api/bulk-upload ---------------------------------------------------

def test_bulk_upload_csv_mixed_results(client):
    headers = register(client, "b1", "b1@example.com")
    csv_bytes = b"URL\nhttps://example.com/one\nhttps://example.com/two\nnot-a-url\n"

    resp = client.post(
        "/api/bulk-upload",
        files={"file": ("urls.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 3

    statuses = [row["status"] for row in results]
    assert statuses.count("success") == 2
    assert statuses.count("failed") == 1


def test_bulk_upload_rejects_unsupported_file_type(client):
    headers = register(client, "b2", "b2@example.com")
    resp = client.post(
        "/api/bulk-upload",
        files={"file": ("urls.txt", b"https://example.com", "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_bulk_upload_rejects_oversized_file(client):
    headers = register(client, "b3", "b3@example.com")
    payload = b"URL\n" + b"x" * (5 * 1024 * 1024 + 1)

    resp = client.post(
        "/api/bulk-upload",
        files={"file": ("big.csv", payload, "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 413


def test_bulk_upload_rejects_malformed_csv(client):
    headers = register(client, "b4", "b4@example.com")
    # invalid UTF-8 bytes -> decode blows up -> 400 from the generic handler
    resp = client.post(
        "/api/bulk-upload",
        files={"file": ("bad.csv", b"\xff\xfe\x00broken", "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 400