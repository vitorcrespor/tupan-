from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from .. import db
from ..utils import security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
auth_scheme = HTTPBearer()


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserOut(BaseModel):
    id: str
    full_name: str | None = None
    email: EmailStr
    role: str | None = None


@router.post('/register', response_model=UserOut)
async def register(body: RegisterIn):
    # check existing
    existing = await db.fetchrow('SELECT id FROM users WHERE email=$1', body.email)
    if existing:
        raise HTTPException(status_code=400, detail='email already registered')
    uid = f'user-{body.email}-{int(__import__("time").time())}'
    hashed = security.get_password_hash(body.password)
    await db.execute('INSERT INTO users (id,full_name,email,role,password_hash,created_date) VALUES ($1,$2,$3,$4,$5,now())', uid, body.full_name or None, body.email, 'user', hashed)
    row = await db.fetchrow('SELECT id,full_name,email,role,created_date FROM users WHERE id=$1', uid)
    return dict(row)


@router.post('/login')
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.fetchrow('SELECT id,full_name,email,role,password_hash FROM users WHERE email=$1', form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail='invalid credentials')
    if not security.verify_password(form_data.password, user['password_hash']):
        raise HTTPException(status_code=400, detail='invalid credentials')
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token({"sub": user['id'], "email": user['email']}, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user['id'], "full_name": user['full_name'], "email": user['email'], "role": user['role']}}


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials
    try:
        payload = security.decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail='invalid token')
    uid = payload.get('sub')
    if not uid:
        raise HTTPException(status_code=401, detail='invalid token')
    user = await db.fetchrow('SELECT id,full_name,email,role,created_date FROM users WHERE id=$1', uid)
    if not user:
        raise HTTPException(status_code=404, detail='user not found')
    return dict(user)


@router.get('/me', response_model=UserOut)
async def me(user = Depends(get_current_user)):
    return user
