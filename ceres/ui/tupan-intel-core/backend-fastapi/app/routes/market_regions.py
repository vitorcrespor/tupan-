from fastapi import APIRouter, HTTPException
from .. import db
import uuid
from .. import schemas
from typing import List

router = APIRouter()


@router.get('/', summary='List market regions', response_model=List[schemas.MarketRegionOut])
async def list_regions(limit: int = 200):
    limit = min(int(limit or 200), 1000)
    cols = 'id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date'
    rows = await db.fetch(f'SELECT {cols} FROM market_regions ORDER BY created_date DESC LIMIT $1', limit)
    return [dict(r) for r in rows]


@router.post('/', summary='Create market region', response_model=schemas.MarketRegionOut)
async def create_region(payload: schemas.MarketRegionIn):
    rid = payload.id or f'region-{uuid.uuid4()}'
    try:
        await db.execute('''INSERT INTO market_regions (id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date) VALUES ($1,$2,$3,$4,$5,$6,$7,now())''', rid, payload.name, payload.city, payload.average_price_per_m2, payload.market_heat, payload.demand_score, payload.liquidity_score)
        row = await db.fetchrow('SELECT id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date FROM market_regions WHERE id=$1', rid)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/bulk', summary='Bulk create regions')
async def bulk_create(body: List[schemas.MarketRegionIn]):
    items = (body or [])[:500]
    if not items:
        return {'success': True, 'inserted': 0}
    conn = await db.pool.acquire()
    try:
        await conn.execute('BEGIN')
        cols = ['id','name','city','average_price_per_m2','market_heat','demand_score','liquidity_score']
        values = []
        parts = []
        for rowIndex, p in enumerate(items):
            rid = p.id or f'region-{uuid.uuid4()}'
            rowVals = [rid, p.name, p.city, p.average_price_per_m2, p.market_heat, p.demand_score, p.liquidity_score]
            values.extend(rowVals)
            start = rowIndex * len(rowVals) + 1
            placeholders = ','.join([f'${start + i}' for i in range(len(rowVals))])
            parts.append(f'({placeholders}, now())')
        insert_cols = ','.join(cols) + ',created_date'
        query = f'INSERT INTO market_regions ({insert_cols}) VALUES ' + ','.join(parts)
        await conn.execute(query, *values)
        await conn.execute('COMMIT')
        return {'success': True, 'inserted': len(items)}
    except Exception as e:
        await conn.execute('ROLLBACK')
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.pool.release(conn)


@router.post('/filter')
async def filter_regions(body: schemas.FilterRequest):
    query = body.query or {}
    limit = min(int(body.limit or 100), 1000)
    allowed = ['id','name','city']
    keys = [k for k in (query or {}).keys() if k in allowed]
    try:
        cols = 'id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date'
        if not keys:
            rows = await db.fetch(f'SELECT {cols} FROM market_regions ORDER BY created_date DESC LIMIT $1', limit)
            return [dict(r) for r in rows]
        where = ' AND '.join([f"{k} = ${i+1}" for i,k in enumerate(keys)])
        params = [query[k] for k in keys]
        sql = f'SELECT {cols} FROM market_regions WHERE {where} ORDER BY created_date DESC LIMIT {limit}'
        rows = await db.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{id}', response_model=schemas.MarketRegionOut)
async def get_region(id: str):
    row = await db.fetchrow('SELECT id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date FROM market_regions WHERE id=$1', id)
    if not row:
        raise HTTPException(status_code=404, detail='not found')
    return dict(row)


@router.put('/{id}', response_model=schemas.MarketRegionOut)
async def update_region(id: str, payload: schemas.MarketRegionIn):
    try:
        await db.execute('''UPDATE market_regions SET name=$1,city=$2,average_price_per_m2=$3,market_heat=$4,demand_score=$5,liquidity_score=$6 WHERE id=$7''', payload.name, payload.city, payload.average_price_per_m2, payload.market_heat, payload.demand_score, payload.liquidity_score, id)
        row = await db.fetchrow('SELECT id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date FROM market_regions WHERE id=$1', id)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{id}')
async def delete_region(id: str):
    try:
        await db.execute('DELETE FROM market_regions WHERE id=$1', id)
        return {'success': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
