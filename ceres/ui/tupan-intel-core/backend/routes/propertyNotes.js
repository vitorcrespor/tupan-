const express = require('express');
const router = express.Router();
const db = require('../db');
const { v4: uuidv4 } = require('uuid');
const { celebrate, Joi, Segments } = require('celebrate');

const noteSchema = Joi.object({ id: Joi.string().optional(), property_id: Joi.string().optional(), user_id: Joi.string().optional(), note: Joi.string().allow(null, '') });
const filterSchema = Joi.object({ query: Joi.object().optional(), limit: Joi.number().integer().min(1).max(1000).optional() });

// GET /api/property-notes
router.get('/', async (req, res) => {
  const limit = Math.min(parseInt(req.query.limit || '200', 10), 1000);
  try {
    const cols = 'id,property_id,user_id,note,created_date';
    const result = await db.query(`SELECT ${cols} FROM property_notes ORDER BY created_date DESC LIMIT $1`, [limit]);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/property-notes
router.post('/', celebrate({ [Segments.BODY]: noteSchema }), async (req, res) => {
  const p = req.body;
  const id = p.id || `note-${uuidv4()}`;
  try {
    await db.query(`INSERT INTO property_notes (id,property_id,user_id,note,created_date) VALUES ($1,$2,$3,$4,now())`, [id, p.property_id || null, p.user_id || null, p.note || null]);
    const r = await db.query('SELECT id,property_id,user_id,note,created_date FROM property_notes WHERE id = $1', [id]);
    res.status(201).json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/property-notes/filter
router.post('/filter', celebrate({ [Segments.BODY]: filterSchema }), async (req, res) => {
  const { query = {}, limit = 100 } = req.body;
  try {
    const allowed = ['id','property_id','user_id'];
    const keys = Object.keys(query || {}).filter(k => allowed.includes(k));
    const params = [];
    let sql = 'SELECT id,property_id,user_id,note,created_date FROM property_notes';
    if (keys.length) {
      const where = keys.map((k, i) => { params.push(query[k]); return `${k} = $${i + 1}`; }).join(' AND ');
      sql += ` WHERE ${where}`;
    }
    sql += ` ORDER BY created_date DESC LIMIT ${Math.min(limit || 100, 1000)}`;
    const result = await db.query(sql, params);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// GET /api/property-notes/:id
router.get('/:id', async (req, res) => {
  try {
    const r = await db.query('SELECT id,property_id,user_id,note,created_date FROM property_notes WHERE id = $1', [req.params.id]);
    if (!r.rows.length) return res.status(404).json({ error: 'not found' });
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// PUT /api/property-notes/:id
router.put('/:id', celebrate({ [Segments.BODY]: noteSchema }), async (req, res) => {
  const p = req.body;
  try {
    await db.query(`UPDATE property_notes SET property_id=$1,user_id=$2,note=$3 WHERE id=$4`, [p.property_id || null, p.user_id || null, p.note || null, req.params.id]);
    const r = await db.query('SELECT id,property_id,user_id,note,created_date FROM property_notes WHERE id = $1', [req.params.id]);
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// DELETE /api/property-notes/:id
router.delete('/:id', async (req, res) => {
  try {
    await db.query('DELETE FROM property_notes WHERE id = $1', [req.params.id]);
    res.json({ success: true });
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

module.exports = router;
