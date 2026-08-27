from fastapi import APIRouter, HTTPException
from .. import db
import uuid
from .. import schemas
from typing import List

router = APIRouter()


@router.get('/', summary='List saved searches', response_model=List[schemas.SavedSearchOut])
async def list_saved(limit: int = 200):
    limit = min(int(limit or 200), 1000)
    cols = 'id,user_id,name,filters,created_date'
    rows = await db.fetch(f'SELECT {cols} FROM saved_searches ORDER BY created_date DESC LIMIT $1', limit)
    return [dict(r) for r in rows]


@router.post('/', summary='Create saved search', response_model=schemas.SavedSearchOut)
async def create_saved(payload: schemas.SavedSearchIn):
    sid = payload.id or f'saved-{uuid.uuid4()}'
    try:
        await db.execute('''INSERT INTO saved_searches (id,user_id,name,filters,created_date) VALUES ($1,$2,$3,$4,now())''', sid, payload.user_id, payload.name, payload.filters)
        row = await db.fetchrow('SELECT id,user_id,name,filters,created_date FROM saved_searches WHERE id=$1', sid)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/filter')
async def filter_saved(body: schemas.FilterRequest):
    query = body.query or {}
    limit = min(int(body.limit or 100), 1000)
    allowed = ['id','user_id','name']
    keys = [k for k in (query or {}).keys() if k in allowed]
    try:
        cols = 'id,user_id,name,filters,created_date'
        if not keys:
            rows = await db.fetch(f'SELECT {cols} FROM saved_searches ORDER BY created_date DESC LIMIT $1', limit)
            return [dict(r) for r in rows]
        where = ' AND '.join([f"{k} = ${i+1}" for i,k in enumerate(keys)])
        params = [query[k] for k in keys]
        sql = f'SELECT {cols} FROM saved_searches WHERE {where} ORDER BY created_date DESC LIMIT {limit}'
        rows = await db.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{id}', response_model=schemas.SavedSearchOut)
async def get_saved(id: str):
    row = await db.fetchrow('SELECT id,user_id,name,filters,created_date FROM saved_searches WHERE id=$1', id)
    if not row:
        raise HTTPException(status_code=404, detail='not found')
    return dict(row)


@router.put('/{id}', response_model=schemas.SavedSearchOut)
async def update_saved(id: str, payload: schemas.SavedSearchIn):
    try:
        await db.execute('''UPDATE saved_searches SET user_id=$1,name=$2,filters=$3 WHERE id=$4''', payload.user_id, payload.name, payload.filters, id)
        row = await db.fetchrow('SELECT id,user_id,name,filters,created_date FROM saved_searches WHERE id=$1', id)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{id}')
async def delete_saved(id: str):
    try:
        await db.execute('DELETE FROM saved_searches WHERE id=$1', id)
        return {'success': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
