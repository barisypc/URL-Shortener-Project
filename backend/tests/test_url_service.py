# backend/tests/test_url_service.py
from services.url_service import generate_short_code

def test_generate_short_code_length_and_charset():
    code = generate_short_code(length=8)
    assert len(code) == 8
    assert code.isalnum()

def test_generate_short_code_is_randomized():
    codes = {generate_short_code() for _ in range(50)}
    assert len(codes) > 1  # hepsi aynı çıkmamalı