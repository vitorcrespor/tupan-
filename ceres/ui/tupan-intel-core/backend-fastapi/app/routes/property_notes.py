from fastapi import APIRouter, HTTPException
from .. import db
import uuid
from .. import schemas
from typing import List

router = APIRouter()


@router.get('/', summary='List property notes', response_model=List[schemas.PropertyNoteOut])
async def list_notes(limit: int = 200):
    limit = min(int(limit or 200), 1000)
    cols = 'id,property_id,user_id,note,created_date'
    rows = await db.fetch(f'SELECT {cols} FROM property_notes ORDER BY created_date DESC LIMIT $1', limit)
    return [dict(r) for r in rows]


@router.post('/', summary='Create property note', response_model=schemas.PropertyNoteOut)
async def create_note(payload: schemas.PropertyNoteIn):
    nid = payload.id or f'note-{uuid.uuid4()}'
    try:
        await db.execute('''INSERT INTO property_notes (id,property_id,user_id,note,created_date) VALUES ($1,$2,$3,$4,now())''', nid, payload.property_id, payload.user_id, payload.note)
        row = await db.fetchrow('SELECT id,property_id,user_id,note,created_date FROM property_notes WHERE id=$1', nid)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/filter')
async def filter_notes(body: schemas.FilterRequest):
    query = body.query or {}
    limit = min(int(body.limit or 100), 1000)
    allowed = ['id','property_id','user_id']
    keys = [k for k in (query or {}).keys() if k in allowed]
    try:
        cols = 'id,property_id,user_id,note,created_date'
        if not keys:
            rows = await db.fetch(f'SELECT {cols} FROM property_notes ORDER BY created_date DESC LIMIT $1', limit)
            return [dict(r) for r in rows]
        where = ' AND '.join([f"{k} = ${i+1}" for i,k in enumerate(keys)])
        params = [query[k] for k in keys]
        sql = f'SELECT {cols} FROM property_notes WHERE {where} ORDER BY created_date DESC LIMIT {limit}'
        rows = await db.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{id}', response_model=schemas.PropertyNoteOut)
async def get_note(id: str):
    row = await db.fetchrow('SELECT id,property_id,user_id,note,created_date FROM property_notes WHERE id=$1', id)
    if not row:
        raise HTTPException(status_code=404, detail='not found')
    return dict(row)


@router.put('/{id}', response_model=schemas.PropertyNoteOut)
async def update_note(id: str, payload: schemas.PropertyNoteIn):
    try:
        await db.execute('''UPDATE property_notes SET property_id=$1,user_id=$2,note=$3 WHERE id=$4''', payload.property_id, payload.user_id, payload.note, id)
        row = await db.fetchrow('SELECT id,property_id,user_id,note,created_date FROM property_notes WHERE id=$1', id)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{id}')
async def delete_note(id: str):
    try:
        await db.execute('DELETE FROM property_notes WHERE id=$1', id)
        return {'success': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
