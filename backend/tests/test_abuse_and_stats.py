# backend/tests/test_abuse_and_stats.py
from helpers import auth_headers, create_url, login, register, signup

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
PC_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# --- report-abuse -------------------------------------------------------

def test_report_abuse_anonymously(client):
    headers = register(client, "ra1", "ra1@example.com")
    code = create_url(client, headers, "https://example.com/spam")

    resp = client.post(
        "/api/report-abuse", json={"short_url": code, "reason": "phishing"}
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["abuse_id"], int)


def test_report_abuse_while_logged_in(client):
    headers = register(client, "ra2", "ra2@example.com")
    code = create_url(client, headers, "https://example.com/spam")

    resp = client.post(
        "/api/report-abuse",
        json={"short_url": code, "reason": "malware"},
        headers=headers,
    )
    assert resp.status_code == 200


def test_report_abuse_rejects_duplicate_from_same_user(client):
    headers = register(client, "ra3", "ra3@example.com")
    code = create_url(client, headers, "https://example.com/spam")

    client.post("/api/report-abuse", json={"short_url": code}, headers=headers)
    resp = client.post("/api/report-abuse", json={"short_url": code}, headers=headers)

    assert resp.status_code == 400
    assert "already" in resp.json()["detail"].lower()


def test_anonymous_reports_are_not_deduped(client):
    headers = register(client, "ra4", "ra4@example.com")
    code = create_url(client, headers, "https://example.com/spam")

    first = client.post("/api/report-abuse", json={"short_url": code})
    second = client.post("/api/report-abuse", json={"short_url": code})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["abuse_id"] != second.json()["abuse_id"]


def test_report_abuse_unknown_short_url_returns_404(client):
    resp = client.post("/api/report-abuse", json={"short_url": "does-not-exist"})
    assert resp.status_code == 404


def test_report_abuse_with_garbage_token_falls_back_to_anonymous(client):
    headers = register(client, "ra5", "ra5@example.com")
    code = create_url(client, headers, "https://example.com/spam")

    resp = client.post(
        "/api/report-abuse",
        json={"short_url": code},
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert resp.status_code == 200

    # attributed to nobody, so the reporter can still file their own report
    mine = client.post("/api/report-abuse", json={"short_url": code}, headers=headers)
    assert mine.status_code == 200


# --- get-abuse ----------------------------------------------------------

def test_get_abuse_lists_only_own_reports(client):
    headers_a = register(client, "ga1", "ga1@example.com")
    code = create_url(client, headers_a, "https://example.com/spam")
    client.post("/api/report-abuse", json={"short_url": code}, headers=headers_a)

    signup(client, "ga2", "ga2@example.com")
    headers_b = auth_headers(login(client, "ga2@example.com"))
    client.post("/api/report-abuse", json={"short_url": code}, headers=headers_b)

    resp = client.get("/api/get-abuse", headers=headers_a)
    assert resp.status_code == 200

    reports = resp.json()
    assert len(reports) == 1
    assert reports[0]["short_code"] == code
    assert reports[0]["original_url"] == "https://example.com/spam"


def test_get_abuse_empty_for_new_user(client):
    headers = register(client, "ga3", "ga3@example.com")
    assert client.get("/api/get-abuse", headers=headers).json() == []


def test_get_abuse_requires_auth(client):
    resp = client.get("/api/get-abuse")
    assert resp.status_code in (401, 403)


# --- show-statistics ----------------------------------------------------

def test_show_statistics_aggregates_clicks(client):
    headers = register(client, "st1", "st1@example.com")
    code = create_url(client, headers, "https://example.com/tracked")
    url_id = client.get("/api/my-urls", headers=headers).json()[0]["id"]

    client.get(f"/{code}", follow_redirects=False, headers={"user-agent": PC_UA})
    client.get(f"/{code}", follow_redirects=False, headers={"user-agent": PC_UA})
    client.get(f"/{code}", follow_redirects=False, headers={"user-agent": MOBILE_UA})

    resp = client.get(f"/api/show-statistics/{url_id}", headers=headers)
    assert resp.status_code == 200

    body = resp.json()
    assert body["url_id"] == url_id
    assert body["short_url"] == code
    assert body["total_clicks"] == 3
    assert len(body["recent_clicks"]) == 3

    platforms = {item["label"]: item["count"] for item in body["by_platform"]}
    assert platforms["PC"] == 2
    assert platforms["Mobile"] == 1

    countries = {item["label"]: item["count"] for item in body["by_country"]}
    assert countries["Unknown"] == 3


def test_show_statistics_with_no_clicks(client):
    headers = register(client, "st2", "st2@example.com")
    create_url(client, headers)
    url_id = client.get("/api/my-urls", headers=headers).json()[0]["id"]

    body = client.get(f"/api/show-statistics/{url_id}", headers=headers).json()
    assert body["total_clicks"] == 0
    assert body["by_platform"] == []
    assert body["recent_clicks"] == []


def test_show_statistics_not_found(client):
    headers = register(client, "st3", "st3@example.com")
    resp = client.get("/api/show-statistics/9999", headers=headers)
    assert resp.status_code == 404


def test_show_statistics_of_other_users_url_is_not_found(client):
    headers_a = register(client, "st4", "st4@example.com")
    create_url(client, headers_a)
    url_id = client.get("/api/my-urls", headers=headers_a).json()[0]["id"]

    signup(client, "st5", "st5@example.com")
    headers_b = auth_headers(login(client, "st5@example.com"))

    resp = client.get(f"/api/show-statistics/{url_id}", headers=headers_b)
    assert resp.status_code == 404