# backend/tests/test_admin.py
import pytest

from helpers import (
    auth_headers,
    create_url,
    login,
    promote_to_admin,
    register,
    signup,
)


@pytest.fixture()
def admin_headers(client, db_session):
    headers = register(client, "root", "root@example.com")
    promote_to_admin(db_session, "root@example.com")
    return headers


@pytest.fixture()
def victim(client):
    """A plain, non-admin user with one URL. Returns (headers, user_id)."""
    signup(client, "victim", "victim@example.com")
    headers = auth_headers(login(client, "victim@example.com"))
    create_url(client, headers, "https://example.com/victim")
    return headers


# --- authorization ------------------------------------------------------

@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/admin/dashboard"),
        ("get", "/api/admin/users"),
        ("get", "/api/admin/user-urls/1"),
        ("get", "/api/admin/abuse-reports"),
        ("get", "/api/admin/audit-log"),
    ],
)
def test_admin_routes_reject_non_admin(client, method, path):
    headers = register(client, "plain", "plain@example.com")
    resp = getattr(client, method)(path, headers=headers)
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"].lower()


def test_admin_routes_reject_anonymous(client):
    resp = client.get("/api/admin/dashboard")
    assert resp.status_code in (401, 403)


# --- dashboard / users --------------------------------------------------

def test_admin_dashboard_counts(client, db_session, admin_headers, victim):
    resp = client.get("/api/admin/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_users"] == 2
    assert body["active_users"] == 2
    assert body["banned_users"] == 0
    assert body["total_urls"] == 1
    assert body["active_urls"] == 1
    assert body["inactive_urls"] == 0
    assert body["protected_urls"] == 0
    assert body["total_clicks"] == 0


def test_admin_dashboard_counts_protected_urls(client, admin_headers, victim):
    create_url(client, victim, "https://example.com/locked", password="hunter2")

    body = client.get("/api/admin/dashboard", headers=admin_headers).json()
    assert body["protected_urls"] == 1


def test_list_all_users_includes_url_counts(client, admin_headers, victim):
    resp = client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200

    by_email = {row["email"]: row for row in resp.json()}
    assert by_email["victim@example.com"]["url_count"] == 1
    assert by_email["victim@example.com"]["is_admin"] is False
    assert by_email["root@example.com"]["is_admin"] is True
    assert by_email["root@example.com"]["url_count"] == 0


def test_get_user_urls(client, db_session, admin_headers, victim):
    rows = client.get("/api/admin/users", headers=admin_headers).json()
    victim_id = next(u["id"] for u in rows if u["email"] == "victim@example.com")

    resp = client.get(f"/api/admin/user-urls/{victim_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()[0]["original_url"] == "https://example.com/victim"


def test_get_user_urls_unknown_user_returns_404(client, admin_headers):
    resp = client.get("/api/admin/user-urls/9999", headers=admin_headers)
    assert resp.status_code == 404


# --- ban / unban --------------------------------------------------------

def _victim_id(client, admin_headers):
    rows = client.get("/api/admin/users", headers=admin_headers).json()
    return next(u["id"] for u in rows if u["email"] == "victim@example.com")


def test_ban_user_then_unban(client, admin_headers, victim):
    victim_id = _victim_id(client, admin_headers)

    resp = client.patch(
        f"/api/admin/ban-user/{victim_id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # banned users can no longer log in
    blocked = client.post(
        "/login/", json={"email": "victim@example.com", "password": "Aa1.gucluSifre"}
    )
    assert blocked.status_code == 403

    client.patch(
        f"/api/admin/ban-user/{victim_id}",
        json={"is_active": True},
        headers=admin_headers,
    )
    restored = client.post(
        "/login/", json={"email": "victim@example.com", "password": "Aa1.gucluSifre"}
    )
    assert restored.status_code == 200


def test_ban_user_not_found(client, admin_headers):
    resp = client.patch(
        "/api/admin/ban-user/9999", json={"is_active": False}, headers=admin_headers
    )
    assert resp.status_code == 404


def test_cannot_ban_another_admin(client, db_session, admin_headers):
    signup(client, "admin2", "admin2@example.com")
    other_admin = promote_to_admin(db_session, "admin2@example.com")

    resp = client.patch(
        f"/api/admin/ban-user/{other_admin.id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 400


# --- delete user --------------------------------------------------------

def test_delete_user_success(client, admin_headers, victim):
    victim_id = _victim_id(client, admin_headers)

    resp = client.delete(
        f"/api/admin/delete-user/{victim_id}", headers=admin_headers
    )
    assert resp.status_code == 200

    remaining = client.get("/api/admin/users", headers=admin_headers).json()
    assert all(u["email"] != "victim@example.com" for u in remaining)


def test_delete_user_not_found(client, admin_headers):
    resp = client.delete("/api/admin/delete-user/9999", headers=admin_headers)
    assert resp.status_code == 404


def test_cannot_delete_another_admin(client, db_session, admin_headers):
    signup(client, "admin3", "admin3@example.com")
    other_admin = promote_to_admin(db_session, "admin3@example.com")

    resp = client.delete(
        f"/api/admin/delete-user/{other_admin.id}", headers=admin_headers
    )
    assert resp.status_code == 400


# --- abuse moderation ---------------------------------------------------

def _report(client, headers, short_code, reason="spam"):
    resp = client.post(
        "/api/report-abuse",
        json={"short_url": short_code, "reason": reason},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["abuse_id"]


def test_list_all_abuse_reports(client, admin_headers, victim):
    code = create_url(client, victim, "https://example.com/reported")
    _report(client, victim, code)

    resp = client.get("/api/admin/abuse-reports", headers=admin_headers)
    assert resp.status_code == 200
    report = resp.json()[0]
    assert report["short_code"] == code
    assert report["reporter_email"] == "victim@example.com"
    assert report["owner_email"] == "victim@example.com"
    assert report["url_is_active"] is True


def test_accept_abuse_deactivates_url(client, db_session, admin_headers, victim):
    code = create_url(client, victim, "https://example.com/bad")
    abuse_id = _report(client, victim, code)

    resp = client.post(
        "/api/admin/accept-abuse", json={"abuse_id": abuse_id}, headers=admin_headers
    )
    assert resp.status_code == 200

    # report is gone and the short link no longer resolves
    assert client.get("/api/admin/abuse-reports", headers=admin_headers).json() == []
    assert client.get(f"/{code}", follow_redirects=False).status_code == 403


def test_accept_abuse_not_found(client, admin_headers):
    resp = client.post(
        "/api/admin/accept-abuse", json={"abuse_id": 9999}, headers=admin_headers
    )
    assert resp.status_code == 404


def test_refuse_abuse_keeps_url_active(client, admin_headers, victim):
    code = create_url(client, victim, "https://example.com/fine")
    abuse_id = _report(client, victim, code)

    resp = client.post(
        "/api/admin/refuse-abuse", json={"abuse_id": abuse_id}, headers=admin_headers
    )
    assert resp.status_code == 200

    assert client.get("/api/admin/abuse-reports", headers=admin_headers).json() == []
    assert client.get(f"/{code}", follow_redirects=False).status_code in (302, 307)


def test_refuse_abuse_not_found(client, admin_headers):
    resp = client.post(
        "/api/admin/refuse-abuse", json={"abuse_id": 9999}, headers=admin_headers
    )
    assert resp.status_code == 404


# --- audit log ----------------------------------------------------------

def test_audit_log_records_admin_actions(client, admin_headers, victim):
    victim_id = _victim_id(client, admin_headers)
    client.patch(
        f"/api/admin/ban-user/{victim_id}",
        json={"is_active": False},
        headers=admin_headers,
    )

    resp = client.get("/api/admin/audit-log", headers=admin_headers)
    assert resp.status_code == 200

    entries = resp.json()
    assert entries[0]["action"] == "ban_user"
    assert entries[0]["target_type"] == "user"
    assert entries[0]["target_id"] == victim_id
    assert entries[0]["admin_email"] == "root@example.com"


def test_audit_log_respects_limit_param(client, admin_headers, victim):
    victim_id = _victim_id(client, admin_headers)
    for is_active in (False, True, False):
        client.patch(
            f"/api/admin/ban-user/{victim_id}",
            json={"is_active": is_active},
            headers=admin_headers,
        )

    resp = client.get("/api/admin/audit-log?limit=2", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2