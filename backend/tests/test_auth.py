
def test_signup_success(client):
    resp = client.post("/signup/", json={
        "username": "baris",
        "email": "baris@example.com",
        "password": "Aa1.gucluSifre"
    })
    assert resp.status_code == 200
    assert resp.json()["email"] == "baris@example.com"


def test_signup_rejects_weak_password(client):
    resp = client.post("/signup/", json={
        "username": "baris2",
        "email": "baris2@example.com",
        "password": "123"
    })
    assert resp.status_code == 400


def test_login_success_and_returns_token(client):
    client.post("/signup/", json={
        "username": "baris3", "email": "b3@example.com", "password": "Aa1.gucluSifre"
    })
    resp = client.post("/login/", json={"email": "b3@example.com", "password": "Aa1.gucluSifre"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_fails(client):
    client.post("/signup/", json={
        "username": "baris4", "email": "b4@example.com", "password": "Aa1.gucluSifre"
    })
    resp = client.post("/login/", json={"email": "b4@example.com", "password": "yanlis"})
    assert resp.status_code == 400