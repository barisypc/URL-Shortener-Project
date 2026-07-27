from datetime import datetime, timedelta
import hashlib
import jwt
import os
from dotenv import load_dotenv
import bcrypt


load_dotenv()

PEPPER = os.environ.get("PASSWORD_PEPPER")
TOKEN_KEY = os.environ.get("TOKEN_KEY")

if not PEPPER:
    raise RuntimeError("Password pepper is not given.")
if not TOKEN_KEY:
    raise RuntimeError("Token Key is not given.")


#This part does 4 key things:

def hash_password(password: str) -> str:
    peppered_password = password + PEPPER

    hashed_bytes = bcrypt.hashpw(peppered_password.encode(), bcrypt.gensalt())
    return hashed_bytes.decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    peppered = plain_password + PEPPER
    return bcrypt.checkpw(peppered.encode(), hashed_password.encode())


def create_Token(data):
    exp = datetime.utcnow() + timedelta(seconds = 600)
    payload = {**data, "exp": exp} 
    created_token = jwt.encode(payload, TOKEN_KEY, algorithm="HS256")
    return created_token


def verify_Token(token):
    try:
        verified_token = jwt.decode(token, TOKEN_KEY, algorithms=["HS256"])
        return verified_token
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None