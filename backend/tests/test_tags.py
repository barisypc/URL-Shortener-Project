# backend/tests/test_tags.py
from helpers import auth_headers, create_tag, create_url, login, register, signup


# --- create-tag ---------------------------------------------------------

def test_create_tag_success(client):
    headers = register(client, "tagger", "tagger@example.com")
    resp = client.post("/api/create-tag", json={"name": "work"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "work"
    assert isinstance(body["id"], int)


def test_create_tag_trims_whitespace(client):
    headers = register(client, "t2", "t2@example.com")
    resp = client.post("/api/create-tag", json={"name": "  spaced  "}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "spaced"


def test_create_tag_rejects_empty_name(client):
    headers = register(client, "t3", "t3@example.com")
    resp = client.post("/api/create-tag", json={"name": "   "}, headers=headers)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_create_tag_rejects_too_long_name(client):
    headers = register(client, "t4", "t4@example.com")
    resp = client.post("/api/create-tag", json={"name": "x" * 31}, headers=headers)
    assert resp.status_code == 400


def test_create_tag_rejects_duplicate_case_insensitive(client):
    headers = register(client, "t5", "t5@example.com")
    create_tag(client, headers, "Work")
    resp = client.post("/api/create-tag", json={"name": "wOrK"}, headers=headers)
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"].lower()


def test_create_tag_requires_auth(client):
    resp = client.post("/api/create-tag", json={"name": "work"})
    assert resp.status_code in (401, 403)


# --- my-tags ------------------------------------------------------------

def test_list_my_tags_returns_only_own_tags_sorted(client):
    headers_a = register(client, "owner", "owner@example.com")
    create_tag(client, headers_a, "zebra")
    create_tag(client, headers_a, "alpha")

    signup(client, "other", "other@example.com")
    headers_b = auth_headers(login(client, "other@example.com"))
    create_tag(client, headers_b, "not-mine")

    resp = client.get("/api/my-tags", headers=headers_a)
    assert resp.status_code == 200
    names = [tag["name"] for tag in resp.json()]
    assert names == ["alpha", "zebra"]


# --- rename-tag ---------------------------------------------------------

def test_rename_tag_success(client):
    headers = register(client, "r1", "r1@example.com")
    tag_id = create_tag(client, headers, "old")

    resp = client.patch(
        f"/api/rename-tag/{tag_id}", json={"name": "new"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "new"


def test_rename_tag_with_null_name_is_a_noop(client):
    headers = register(client, "r2", "r2@example.com")
    tag_id = create_tag(client, headers, "keep")

    resp = client.patch(
        f"/api/rename-tag/{tag_id}", json={"name": None}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "keep"


def test_rename_tag_rejects_empty_name(client):
    headers = register(client, "r3", "r3@example.com")
    tag_id = create_tag(client, headers, "keep")

    resp = client.patch(
        f"/api/rename-tag/{tag_id}", json={"name": "   "}, headers=headers
    )
    assert resp.status_code == 400


def test_rename_tag_rejects_duplicate_name(client):
    headers = register(client, "r4", "r4@example.com")
    create_tag(client, headers, "first")
    second_id = create_tag(client, headers, "second")

    resp = client.patch(
        f"/api/rename-tag/{second_id}", json={"name": "FIRST"}, headers=headers
    )
    assert resp.status_code == 400


def test_rename_tag_not_found(client):
    headers = register(client, "r5", "r5@example.com")
    resp = client.patch("/api/rename-tag/9999", json={"name": "x"}, headers=headers)
    assert resp.status_code == 404


def test_rename_other_users_tag_is_not_found(client):
    headers_a = register(client, "a1", "a1@example.com")
    tag_id = create_tag(client, headers_a, "mine")

    signup(client, "b1", "b1@example.com")
    headers_b = auth_headers(login(client, "b1@example.com"))

    resp = client.patch(
        f"/api/rename-tag/{tag_id}", json={"name": "stolen"}, headers=headers_b
    )
    assert resp.status_code == 404


# --- change-tag (assign tags to a URL) ----------------------------------

def test_change_tag_assigns_tags_to_url(client):
    headers = register(client, "c1", "c1@example.com")
    code = create_url(client, headers)
    tag_one = create_tag(client, headers, "one")
    tag_two = create_tag(client, headers, "two")

    url_id = client.get("/api/my-urls", headers=headers).json()[0]["id"]

    resp = client.patch(
        f"/api/change-tag/{url_id}",
        json={"tag_ids": [tag_one, tag_two, tag_one]},  # duplicate is de-duped
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {tag["id"] for tag in body["tags"]} == {tag_one, tag_two}
    assert body["short_url"].endswith(code)


def test_change_tag_with_empty_list_clears_tags(client):
    headers = register(client, "c2", "c2@example.com")
    create_url(client, headers)
    tag_id = create_tag(client, headers, "temp")
    url_id = client.get("/api/my-urls", headers=headers).json()[0]["id"]

    client.patch(
        f"/api/change-tag/{url_id}", json={"tag_ids": [tag_id]}, headers=headers
    )
    resp = client.patch(
        f"/api/change-tag/{url_id}", json={"tag_ids": []}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["tags"] == []


def test_change_tag_url_not_found(client):
    headers = register(client, "c3", "c3@example.com")
    resp = client.patch("/api/change-tag/9999", json={"tag_ids": []}, headers=headers)
    assert resp.status_code == 404


def test_change_tag_rejects_unknown_tag_ids(client):
    headers = register(client, "c4", "c4@example.com")
    create_url(client, headers)
    url_id = client.get("/api/my-urls", headers=headers).json()[0]["id"]

    resp = client.patch(
        f"/api/change-tag/{url_id}", json={"tag_ids": [4242]}, headers=headers
    )
    assert resp.status_code == 400
    assert "4242" in resp.json()["detail"]


# --- delete-tag ---------------------------------------------------------

def test_delete_tag_success(client):
    headers = register(client, "d1", "d1@example.com")
    tag_id = create_tag(client, headers, "doomed")

    resp = client.delete(f"/api/delete-tag/{tag_id}", headers=headers)
    assert resp.status_code == 200
    assert "doomed" in resp.json()["message"]

    assert client.get("/api/my-tags", headers=headers).json() == []


def test_delete_tag_not_found(client):
    headers = register(client, "d2", "d2@example.com")
    resp = client.delete("/api/delete-tag/9999", headers=headers)
    assert resp.status_code == 404