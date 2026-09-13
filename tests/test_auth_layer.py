from auth_layer import create_access_token, decode_access_token
import pytest
from jwt import InvalidTokenError

def test_encode_decode(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test_secret_key")
    token = create_access_token(15)
    user_id = decode_access_token(token)
    assert user_id == 15

def test_token_wrong_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "secret_1")
    token = create_access_token(15)
    monkeypatch.setenv("SECRET_KEY", "secret_2")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_token_broken(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "secret_1")
    fake_token = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxNSIsImV4cCI6MTc4OTEyMzQ1Nn0."
    "invalid_signature"
)
    with pytest.raises(InvalidTokenError):
        decode_access_token(fake_token)