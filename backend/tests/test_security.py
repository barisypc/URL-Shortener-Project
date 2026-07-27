# backend/tests/test_security.py
import security


def test_hash_and_verify_password():
    hashed = security.hash_password("Aa1.gucluSifre")
    assert hashed != "Aa1.gucluSifre"
    assert security.verify_password("Aa1.gucluSifre", hashed)


def test_verify_password_wrong_password_fails():
    hashed = security.hash_password("Aa1.gucluSifre")
    assert not security.verify_password("yanlisSifre1.", hashed)


def test_token_create_and_verify_roundtrip():
    token = security.create_Token({"user_id": 1, "username": "baris"})
    payload = security.verify_Token(token)
    assert payload["user_id"] == 1
    assert payload["username"] == "baris"


def test_verify_token_rejects_garbage():
    assert security.verify_Token("not.a.valid.token") is None