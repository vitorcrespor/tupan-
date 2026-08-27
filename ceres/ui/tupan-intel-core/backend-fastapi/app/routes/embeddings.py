from fastapi import APIRouter, HTTPException
from .. import db
import uuid
from .. import schemas
from typing import List

router = APIRouter()


@router.post('/', summary='Store embedding')
async def store_embedding(payload: schemas.EmbeddingIn):
    vector = payload.vector
    if not isinstance(vector, list):
        raise HTTPException(status_code=400, detail='vector required as array')
    eid = f'embed-{uuid.uuid4()}'
    try:
        await db.execute('''INSERT INTO embeddings (id,entity_type,entity_id,vector,text,created_date) VALUES ($1,$2,$3,$4,$5,now())''', eid, payload.entity_type, payload.entity_id, vector, payload.text)
        row = await db.fetchrow('SELECT id,entity_type,entity_id,text,created_date FROM embeddings WHERE id=$1', eid)
        return dict(row) if row else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/search', summary='Similarity search')
async def search_embeddings(body: schemas.EmbeddingSearchIn):
    vector = body.vector
    top_k = min(int(body.top_k or 10), 100)
    if not isinstance(vector, list):
        raise HTTPException(status_code=400, detail='vector required as array')
    try:
        sql = 'SELECT id,entity_type,entity_id,text, (vector <-> $1) AS distance FROM embeddings ORDER BY vector <-> $1 LIMIT $2'
        rows = await db.fetch(sql, vector, top_k)
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
