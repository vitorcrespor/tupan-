from fastapi import APIRouter, HTTPException
from .. import db
import uuid
from .. import schemas
from typing import List

router = APIRouter()


@router.get('/', summary='List district boundaries', response_model=List[schemas.DistrictBoundaryOut])
async def list_districts(limit: int = 200):
    limit = min(int(limit or 200), 1000)
    cols = 'id,name,geojson,created_date'
    rows = await db.fetch(f'SELECT {cols} FROM district_boundaries ORDER BY created_date DESC LIMIT $1', limit)
    return [dict(r) for r in rows]


@router.post('/', summary='Create district boundary', response_model=schemas.DistrictBoundaryOut)
async def create_district(payload: schemas.DistrictBoundaryIn):
    did = payload.id or f'district-{uuid.uuid4()}'
    try:
        await db.execute('''INSERT INTO district_boundaries (id,name,geojson,created_date) VALUES ($1,$2,$3,now())''', did, payload.name, payload.geojson)
        row = await db.fetchrow('SELECT id,name,geojson,created_date FROM district_boundaries WHERE id=$1', did)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/filter')
async def filter_districts(body: schemas.FilterRequest):
    query = body.query or {}
    limit = min(int(body.limit or 100), 1000)
    allowed = ['id','name']
    keys = [k for k in (query or {}).keys() if k in allowed]
    try:
        cols = 'id,name,geojson,created_date'
        if not keys:
            rows = await db.fetch(f'SELECT {cols} FROM district_boundaries ORDER BY created_date DESC LIMIT $1', limit)
            return [dict(r) for r in rows]
        where = ' AND '.join([f"{k} = ${i+1}" for i,k in enumerate(keys)])
        params = [query[k] for k in keys]
        sql = f'SELECT {cols} FROM district_boundaries WHERE {where} ORDER BY created_date DESC LIMIT {limit}'
        rows = await db.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{id}', response_model=schemas.DistrictBoundaryOut)
async def get_district(id: str):
    row = await db.fetchrow('SELECT id,name,geojson,created_date FROM district_boundaries WHERE id=$1', id)
    if not row:
        raise HTTPException(status_code=404, detail='not found')
    return dict(row)


@router.put('/{id}', response_model=schemas.DistrictBoundaryOut)
async def update_district(id: str, payload: schemas.DistrictBoundaryIn):
    try:
        await db.execute('''UPDATE district_boundaries SET name=$1,geojson=$2 WHERE id=$3''', payload.name, payload.geojson, id)
        row = await db.fetchrow('SELECT id,name,geojson,created_date FROM district_boundaries WHERE id=$1', id)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{id}')
async def delete_district(id: str):
    try:
        await db.execute('DELETE FROM district_boundaries WHERE id=$1', id)
        return {'success': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
