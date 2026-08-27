from fastapi import APIRouter, HTTPException
from typing import List
from .. import db
import uuid
from .. import schemas

router = APIRouter()


@router.get('/', summary='List properties', response_model=List[schemas.PropertyOut])
async def list_properties(limit: int = 200):
    limit = min(int(limit or 200), 1000)
    cols = 'id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date'
    rows = await db.fetch(f'SELECT {cols} FROM properties ORDER BY created_date DESC LIMIT $1', limit)
    return [dict(r) for r in rows]


@router.post('/', summary='Create property', response_model=schemas.PropertyOut)
async def create_property(payload: schemas.PropertyIn):
    pid = payload.id or f'property-{uuid.uuid4()}'
    try:
        await db.execute('''INSERT INTO properties (id, title, address, city, neighborhood, latitude, longitude, price, price_per_m2, created_date, updated_date)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,now(),now())''', pid, payload.title, payload.address, payload.city, payload.neighborhood, payload.latitude, payload.longitude, payload.price, payload.price_per_m2)
        row = await db.fetchrow('SELECT id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date FROM properties WHERE id=$1', pid)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/bulk', summary='Bulk create')
async def bulk_create(body: schemas.BulkItems):
    items = (body.items or [])[:500]
    if not items:
        return {'success': True, 'inserted': 0}
    conn = await db.pool.acquire()
    try:
        await conn.execute('BEGIN')
        cols = ['id','title','address','city','neighborhood','latitude','longitude','price','price_per_m2']
        values = []
        parts = []
        for rowIndex, p in enumerate(items):
            pid = p.id or f'property-{uuid.uuid4()}'
            rowVals = [pid, p.title, p.address, p.city, p.neighborhood, p.latitude, p.longitude, p.price, p.price_per_m2]
            values.extend(rowVals)
            start = rowIndex * len(rowVals) + 1
            placeholders = ','.join([f'${start + i}' for i in range(len(rowVals))])
            parts.append(f'({placeholders}, now(), now())')
        insert_cols = ','.join(cols) + ',created_date,updated_date'
        query = f'INSERT INTO properties ({insert_cols}) VALUES ' + ','.join(parts)
        await conn.execute(query, *values)
        await conn.execute('COMMIT')
        return {'success': True, 'inserted': len(items)}
    except Exception as e:
        await conn.execute('ROLLBACK')
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.pool.release(conn)


@router.post('/filter')
async def filter_properties(body: schemas.FilterRequest):
    query = body.query or {}
    limit = min(int(body.limit or 100), 1000)
    allowed = ['id','title','address','city','neighborhood','price','price_per_m2']
    keys = [k for k in (query or {}).keys() if k in allowed]
    try:
        cols = 'id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date'
        if not keys:
            rows = await db.fetch(f'SELECT {cols} FROM properties ORDER BY created_date DESC LIMIT $1', limit)
            return [dict(r) for r in rows]
        where = ' AND '.join([f"{k} = ${i+1}" for i,k in enumerate(keys)])
        params = [query[k] for k in keys]
        sql = f'SELECT {cols} FROM properties WHERE {where} ORDER BY created_date DESC LIMIT {limit}'
        rows = await db.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{id}', response_model=schemas.PropertyOut)
async def get_property(id: str):
    row = await db.fetchrow('SELECT id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date FROM properties WHERE id=$1', id)
    if not row:
        raise HTTPException(status_code=404, detail='not found')
    return dict(row)


@router.put('/{id}', response_model=schemas.PropertyOut)
async def update_property(id: str, payload: schemas.PropertyIn):
    try:
        await db.execute('''UPDATE properties SET title=$1,address=$2,city=$3,neighborhood=$4,latitude=$5,longitude=$6,price=$7,price_per_m2=$8,updated_date=now() WHERE id=$9''', payload.title, payload.address, payload.city, payload.neighborhood, payload.latitude, payload.longitude, payload.price, payload.price_per_m2, id)
        row = await db.fetchrow('SELECT id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date FROM properties WHERE id=$1', id)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{id}')
async def delete_property(id: str):
    try:
        await db.execute('DELETE FROM properties WHERE id=$1', id)
        return {'success': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
