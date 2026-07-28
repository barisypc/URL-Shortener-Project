# backend/tests/helpers.py
"""Small helpers shared by the test modules.

Not a test file itself — pytest adds `tests/` to sys.path when it collects the
modules next to it, so `from helpers import ...` works without a package.
"""

import models

PASSWORD = "Aa1.gucluSifre"


def signup(client, username, email, password=PASSWORD):
    resp = client.post(
        "/signup/",
        json={"username": username, "email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def login(client, email, password=PASSWORD):
    resp = client.post("/login/", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def register(client, username="u1", email="u1@example.com", password=PASSWORD):
    """Sign up + log in, return ready-to-use Authorization headers."""
    signup(client, username, email, password)
    return auth_headers(login(client, email, password))


def get_user(db_session, email):
    return db_session.query(models.User).filter(models.User.email == email).first()


def promote_to_admin(db_session, email):
    user = get_user(db_session, email)
    user.is_admin = True
    db_session.commit()
    db_session.refresh(user)
    return user


def ban(db_session, email):
    user = get_user(db_session, email)
    user.is_active = False
    db_session.commit()
    return user


def create_url(client, headers, original_url="https://example.com/page", **extra):
    """Create a short URL and return its short *code* (not the full URL)."""
    payload = {"original_url": original_url, **extra}
    resp = client.post("/shorten", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["short_url"].rsplit("/", 1)[-1]


def get_url_row(db_session, short_code):
    return (
        db_session.query(models.URL)
        .filter(models.URL.short_url == short_code)
        .first()
    )


def create_tag(client, headers, name):
    resp = client.post("/api/create-tag", json={"name": name}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]