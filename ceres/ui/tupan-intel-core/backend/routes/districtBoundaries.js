const express = require('express');
const router = express.Router();
const db = require('../db');
const { v4: uuidv4 } = require('uuid');
const { celebrate, Joi, Segments } = require('celebrate');

const districtSchema = Joi.object({ id: Joi.string().optional(), name: Joi.string().optional(), geojson: Joi.object().optional() });
const filterSchema = Joi.object({ query: Joi.object().optional(), limit: Joi.number().integer().min(1).max(1000).optional() });

// GET /api/district-boundaries
router.get('/', async (req, res) => {
  const limit = Math.min(parseInt(req.query.limit || '200', 10), 1000);
  try {
    const cols = 'id,name,geojson,created_date';
    const result = await db.query(`SELECT ${cols} FROM district_boundaries ORDER BY created_date DESC LIMIT $1`, [limit]);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/district-boundaries
router.post('/', celebrate({ [Segments.BODY]: districtSchema }), async (req, res) => {
  const p = req.body;
  const id = p.id || `district-${uuidv4()}`;
  try {
    await db.query(`INSERT INTO district_boundaries (id,name,geojson,created_date) VALUES ($1,$2,$3,now())`, [id, p.name || null, p.geojson || null]);
    const r = await db.query('SELECT id,name,geojson,created_date FROM district_boundaries WHERE id = $1', [id]);
    res.status(201).json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/district-boundaries/filter
router.post('/filter', celebrate({ [Segments.BODY]: filterSchema }), async (req, res) => {
  const { query = {}, limit = 100 } = req.body;
  try {
    const allowed = ['id','name'];
    const keys = Object.keys(query || {}).filter(k => allowed.includes(k));
    const params = [];
    let sql = 'SELECT id,name,geojson,created_date FROM district_boundaries';
    if (keys.length) {
      const where = keys.map((k, i) => { params.push(query[k]); return `${k} = $${i + 1}`; }).join(' AND ');
      sql += ` WHERE ${where}`;
    }
    sql += ` ORDER BY created_date DESC LIMIT ${Math.min(limit || 100, 1000)}`;
    const result = await db.query(sql, params);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// GET /api/district-boundaries/:id
router.get('/:id', async (req, res) => {
  try {
    const r = await db.query('SELECT id,name,geojson,created_date FROM district_boundaries WHERE id = $1', [req.params.id]);
    if (!r.rows.length) return res.status(404).json({ error: 'not found' });
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// PUT /api/district-boundaries/:id
router.put('/:id', celebrate({ [Segments.BODY]: districtSchema }), async (req, res) => {
  const p = req.body;
  try {
    await db.query(`UPDATE district_boundaries SET name=$1,geojson=$2 WHERE id=$3`, [p.name || null, p.geojson || null, req.params.id]);
    const r = await db.query('SELECT id,name,geojson,created_date FROM district_boundaries WHERE id = $1', [req.params.id]);
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// DELETE /api/district-boundaries/:id
router.delete('/:id', async (req, res) => {
  try {
    await db.query('DELETE FROM district_boundaries WHERE id = $1', [req.params.id]);
    res.json({ success: true });
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

module.exports = router;
