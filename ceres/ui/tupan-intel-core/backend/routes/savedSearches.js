const express = require('express');
const router = express.Router();
const db = require('../db');
const { v4: uuidv4 } = require('uuid');
const { celebrate, Joi, Segments } = require('celebrate');

const savedSchema = Joi.object({ id: Joi.string().optional(), user_id: Joi.string().optional(), name: Joi.string().optional(), filters: Joi.object().optional() });
const filterSchema = Joi.object({ query: Joi.object().optional(), limit: Joi.number().integer().min(1).max(1000).optional() });

// GET /api/saved-searches
router.get('/', async (req, res) => {
  const limit = Math.min(parseInt(req.query.limit || '200', 10), 1000);
  try {
    const cols = 'id,user_id,name,filters,created_date';
    const result = await db.query(`SELECT ${cols} FROM saved_searches ORDER BY created_date DESC LIMIT $1`, [limit]);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/saved-searches
router.post('/', celebrate({ [Segments.BODY]: savedSchema }), async (req, res) => {
  const p = req.body;
  const id = p.id || `saved-${uuidv4()}`;
  try {
    await db.query(`INSERT INTO saved_searches (id,user_id,name,filters,created_date) VALUES ($1,$2,$3,$4,now())`, [id, p.user_id || null, p.name || null, p.filters || null]);
    const r = await db.query('SELECT id,user_id,name,filters,created_date FROM saved_searches WHERE id = $1', [id]);
    res.status(201).json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/saved-searches/filter
router.post('/filter', celebrate({ [Segments.BODY]: filterSchema }), async (req, res) => {
  const { query = {}, limit = 100 } = req.body;
  try {
    const allowed = ['id','user_id','name'];
    const keys = Object.keys(query || {}).filter(k => allowed.includes(k));
    const params = [];
    let sql = 'SELECT id,user_id,name,filters,created_date FROM saved_searches';
    if (keys.length) {
      const where = keys.map((k, i) => { params.push(query[k]); return `${k} = $${i + 1}`; }).join(' AND ');
      sql += ` WHERE ${where}`;
    }
    sql += ` ORDER BY created_date DESC LIMIT ${Math.min(limit || 100, 1000)}`;
    const result = await db.query(sql, params);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// GET /api/saved-searches/:id
router.get('/:id', async (req, res) => {
  try {
    const r = await db.query('SELECT id,user_id,name,filters,created_date FROM saved_searches WHERE id = $1', [req.params.id]);
    if (!r.rows.length) return res.status(404).json({ error: 'not found' });
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// PUT /api/saved-searches/:id
router.put('/:id', celebrate({ [Segments.BODY]: savedSchema }), async (req, res) => {
  const p = req.body;
  try {
    await db.query(`UPDATE saved_searches SET user_id=$1,name=$2,filters=$3 WHERE id=$4`, [p.user_id || null, p.name || null, p.filters || null, req.params.id]);
    const r = await db.query('SELECT id,user_id,name,filters,created_date FROM saved_searches WHERE id = $1', [req.params.id]);
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// DELETE /api/saved-searches/:id
router.delete('/:id', async (req, res) => {
  try {
    await db.query('DELETE FROM saved_searches WHERE id = $1', [req.params.id]);
    res.json({ success: true });
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

module.exports = router;
