from fastapi import *
from fastapi.responses import *
from sqlmodel import *
import os
import requests
from datetime import timedelta, datetime
import jwt
from jwt.algorithms import RSAAlgorithm


algo = os.environ['ALGORITHM']
secret_key = os.environ['SECRET_KEY']
token_lifetime = int(os.environ['TOKEN_LIFETIME'])


# Валидация JWT
def validate_jwt(token: str):
    # Декодировать токен
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algo],
            options={"verify_exp": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        print(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def create_jwt(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=token_lifetime)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algo)
    return encoded_jwt


def get_user_from_token(token: str):
    payload = jwt.decode(
        token, secret_key, algorithms=[algo], options={"verify_exp": True}
    )
    username: str = payload.get("sub")
    return username
