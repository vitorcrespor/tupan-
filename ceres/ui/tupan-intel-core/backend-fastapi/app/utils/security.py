import os
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import jwt, JWTError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv('JWT_SECRET') or os.getenv('SECRET_KEY')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES') or 60 * 24)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def _require_secret() -> str:
    if not SECRET_KEY:
        raise RuntimeError('JWT_SECRET is required for this retired scaffold. Use the canonical FastAPI control plane instead.')
    return SECRET_KEY

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _require_secret(), algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _require_secret(), algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise
