from fastapi import APIRouter, HTTPException
from .. import db
import uuid
from .. import schemas
from typing import List

router = APIRouter()


@router.get('/', summary='List users', response_model=List[schemas.UserOut])
async def list_users(limit: int = 200):
    limit = min(int(limit or 200), 1000)
    cols = 'id,full_name,email,role,created_date'
    rows = await db.fetch(f'SELECT {cols} FROM users ORDER BY created_date DESC LIMIT $1', limit)
    return [dict(r) for r in rows]


@router.post('/', summary='Create user', response_model=schemas.UserOut)
async def create_user(payload: schemas.UserIn):
    uid = payload.id or f'user-{uuid.uuid4()}'
    try:
        # Note: password hashing handled elsewhere (auth.register). Here we accept a pre-hashed password if provided.
        password_hash = getattr(payload, 'password', None)
        await db.execute('''INSERT INTO users (id,full_name,email,role,password_hash,created_date) VALUES ($1,$2,$3,$4,$5,now())''', uid, payload.full_name, payload.email, payload.role or 'user', password_hash)
        row = await db.fetchrow('SELECT id,full_name,email,role,created_date FROM users WHERE id=$1', uid)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/filter')
async def filter_users(body: schemas.FilterRequest):
    query = body.query or {}
    limit = min(int(body.limit or 100), 1000)
    allowed = ['id','email','role']
    keys = [k for k in (query or {}).keys() if k in allowed]
    try:
        cols = 'id,full_name,email,role,created_date'
        if not keys:
            rows = await db.fetch(f'SELECT {cols} FROM users ORDER BY created_date DESC LIMIT $1', limit)
            return [dict(r) for r in rows]
        where = ' AND '.join([f"{k} = ${i+1}" for i,k in enumerate(keys)])
        params = [query[k] for k in keys]
        sql = f'SELECT {cols} FROM users WHERE {where} ORDER BY created_date DESC LIMIT {limit}'
        rows = await db.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{id}', response_model=schemas.UserOut)
async def get_user(id: str):
    row = await db.fetchrow('SELECT id,full_name,email,role,created_date FROM users WHERE id=$1', id)
    if not row:
        raise HTTPException(status_code=404, detail='not found')
    return dict(row)


@router.put('/{id}', response_model=schemas.UserOut)
async def update_user(id: str, payload: schemas.UserIn):
    try:
        await db.execute('''UPDATE users SET full_name=$1,email=$2,role=$3 WHERE id=$4''', payload.full_name, payload.email, payload.role, id)
        row = await db.fetchrow('SELECT id,full_name,email,role,created_date FROM users WHERE id=$1', id)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{id}')
async def delete_user(id: str):
    try:
        await db.execute('DELETE FROM users WHERE id=$1', id)
        return {'success': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
