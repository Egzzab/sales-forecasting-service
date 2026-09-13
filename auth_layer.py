from pwdlib import PasswordHash
import jwt
from datetime import datetime, UTC, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

_password_hash = PasswordHash.recommended()


def hash_password(password):
    return _password_hash.hash(password)

def verify_password(password, password_hash):
    return _password_hash.verify(password, password_hash)

def create_access_token(user_id):
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(hours=1)
    }

    token = jwt.encode(
        payload = payload,
        key = os.getenv("SECRET_KEY"),
        algorithm = "HS256"
        )
    
    return token

def decode_access_token(token):
    payload = jwt.decode(
        jwt = token,
        key = os.getenv("SECRET_KEY"),
        algorithms = ["HS256"]
    )
    return int(payload["sub"])