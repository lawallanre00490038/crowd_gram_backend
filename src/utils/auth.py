from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import jwt, os
import logging


from src.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
logger = logging.getLogger(__name__)


pwd_context = CryptContext(schemes=["bcrypt"])




def generate_passwd_hash(password: str) -> str:
    hash = pwd_context.hash(password)
    return hash

def verify_password(password: str, hash: str) -> bool:
    return pwd_context.verify(password, hash)

def get_password_hash(password: str):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        logging.exception(e)
        return None


