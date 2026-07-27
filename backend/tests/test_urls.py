# backend/tests/test_urls.py

def _get_token(client, email="u@example.com", password="Aa1.gucluSifre"):
    client.post("/signup/", json={"username": "u", "email": email, "password": password})
    resp = client.post("/login/", json={"email": email, "password": password})
    return resp.json()["access_token"]


def test_shorten_url_success(client):
    token = _get_token(client)
    resp = client.post(
        "/shorten",
        json={"original_url": "https://example.com/some/page"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert "short_url" in resp.json()


def test_shorten_url_requires_auth(client):
    resp = client.post("/shorten", json={"original_url": "https://example.com"})
    assert resp.status_code == 401  # HTTPBearer'da token yoksa bu FastAPI sürümünde 401 dönüyor