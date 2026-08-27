const express = require('express');
const router = express.Router();
const db = require('../db');
const { v4: uuidv4 } = require('uuid');
const { celebrate, Joi, Segments } = require('celebrate');

const embedSchema = Joi.object({ entity_type: Joi.string().optional(), entity_id: Joi.string().optional(), vector: Joi.array().items(Joi.number()).required(), text: Joi.string().optional() });
const embedSearchSchema = Joi.object({ vector: Joi.array().items(Joi.number()).required(), top_k: Joi.number().integer().min(1).max(100).optional() });

// POST /api/embeddings - store an embedding
router.post('/', celebrate({ [Segments.BODY]: embedSchema }), async (req, res) => {
  const { entity_type, entity_id, vector, text } = req.body || {};
  const id = `embed-${uuidv4()}`;
  try {
    // Attempt to insert vector directly; driver must support sending arrays for pgvector cast
    await db.query('INSERT INTO embeddings (id,entity_type,entity_id,vector,text,created_date) VALUES ($1,$2,$3,$4,$5,now())', [id, entity_type || null, entity_id || null, vector, text || null]);
    const r = await db.query('SELECT id,entity_type,entity_id,text,created_date FROM embeddings WHERE id = $1', [id]);
    res.status(201).json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/embeddings/search - similarity search by vector
router.post('/search', celebrate({ [Segments.BODY]: embedSearchSchema }), async (req, res) => {
  const { vector, top_k = 10 } = req.body || {};
  try {
    const k = Math.min(parseInt(top_k, 10) || 10, 100);
    const sql = `SELECT id,entity_type,entity_id,text, (vector <-> $1) AS distance FROM embeddings ORDER BY vector <-> $1 LIMIT $2`;
    const result = await db.query(sql, [vector, k]);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

module.exports = router;
