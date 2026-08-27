import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import properties, llm, auth, market_regions, users, saved_searches, property_notes, district_boundaries
from . import logging as tlogging
from .routes import embeddings as embeddings_router
from . import db

app = FastAPI(title='Tupan FastAPI Backend')

# CORS: pull allowed origins from env or allow all in dev
origins = [o for o in (os.getenv('CORS_ORIGINS') or '').split(',') if o]
if not origins:
    origins = ['http://localhost:5173']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(properties.router, prefix='/api/properties')
app.include_router(llm.router, prefix='/api/llm')
app.include_router(auth.router, prefix='/api/auth')
app.include_router(market_regions.router, prefix='/api/market-regions')
app.include_router(users.router, prefix='/api/users')
app.include_router(saved_searches.router, prefix='/api/saved-searches')
app.include_router(property_notes.router, prefix='/api/property-notes')
app.include_router(district_boundaries.router, prefix='/api/district-boundaries')
app.include_router(embeddings_router.router, prefix='/api/embeddings')

@app.on_event('startup')
async def startup():
    await db.init_db()

@app.on_event('shutdown')
async def shutdown():
    await db.close_db()

@app.get('/')
async def root():
    return {'status': 'tupan-fastapi', 'env': os.getenv('ENV', 'dev')}
