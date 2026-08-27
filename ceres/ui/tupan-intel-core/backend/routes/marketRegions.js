const express = require('express');
const router = express.Router();
const db = require('../db');
const { v4: uuidv4 } = require('uuid');
const { celebrate, Joi, Segments } = require('celebrate');

const regionSchema = Joi.object({ id: Joi.string().optional(), name: Joi.string().optional(), city: Joi.string().optional(), average_price_per_m2: Joi.number().integer().optional().allow(null), market_heat: Joi.number().integer().optional().allow(null), demand_score: Joi.number().integer().optional().allow(null), liquidity_score: Joi.number().integer().optional().allow(null) });
const bulkSchema = Joi.object({ items: Joi.array().items(regionSchema).max(500) });
const filterSchema = Joi.object({ query: Joi.object().optional(), limit: Joi.number().integer().min(1).max(1000).optional() });

// GET /api/market-regions
router.get('/', async (req, res) => {
  const limit = Math.min(parseInt(req.query.limit || '200', 10), 1000);
  try {
    const cols = 'id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date';
    const result = await db.query(`SELECT ${cols} FROM market_regions ORDER BY created_date DESC LIMIT $1`, [limit]);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/market-regions
router.post('/', celebrate({ [Segments.BODY]: regionSchema }), async (req, res) => {
  const p = req.body;
  const id = p.id || `region-${uuidv4()}`;
  try {
    await db.query(`INSERT INTO market_regions (id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date)
      VALUES ($1,$2,$3,$4,$5,$6,$7,now())`, [id, p.name || null, p.city || null, p.average_price_per_m2 || null, p.market_heat || null, p.demand_score || null, p.liquidity_score || null]);
    const r = await db.query('SELECT id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date FROM market_regions WHERE id = $1', [id]);
    res.status(201).json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/market-regions/bulk
router.post('/bulk', celebrate({ [Segments.BODY]: bulkSchema }), async (req, res) => {
  const items = (req.body.items || []).slice(0, 500);
  if (!items.length) return res.json({ success: true, inserted: 0 });
  const client = await db.pool.connect();
  try {
    await client.query('BEGIN');
    const cols = ['id','name','city','average_price_per_m2','market_heat','demand_score','liquidity_score'];
    const values = [];
    const placeholders = items.map((p, rowIndex) => {
      const id = p.id || `region-${uuidv4()}`;
      const rowVals = [id, p.name || null, p.city || null, p.average_price_per_m2 || null, p.market_heat || null, p.demand_score || null, p.liquidity_score || null];
      values.push(...rowVals);
      const start = rowIndex * rowVals.length + 1;
      const ph = rowVals.map((_, i) => `$${start + i}`).join(',');
      return `(${ph}, now())`;
    });
    const insertCols = cols.join(',') + ',created_date';
    const queryText = `INSERT INTO market_regions (${insertCols}) VALUES ${placeholders.join(',')}`;
    await client.query(queryText, values);
    await client.query('COMMIT');
    res.json({ success: true, inserted: items.length });
  } catch (e) { await client.query('ROLLBACK'); console.error(e); res.status(500).json({ error: e.message }); } finally { client.release(); }
});

// POST /api/market-regions/filter
router.post('/filter', celebrate({ [Segments.BODY]: filterSchema }), async (req, res) => {
  const { query = {}, limit = 100 } = req.body;
  try {
    const allowed = ['id','name','city'];
    const keys = Object.keys(query || {}).filter(k => allowed.includes(k));
    const params = [];
    let sql = 'SELECT id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date FROM market_regions';
    if (keys.length) {
      const where = keys.map((k, i) => { params.push(query[k]); return `${k} = $${i + 1}`; }).join(' AND ');
      sql += ` WHERE ${where}`;
    }
    sql += ` ORDER BY created_date DESC LIMIT ${Math.min(limit || 100, 1000)}`;
    const result = await db.query(sql, params);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// GET /api/market-regions/:id
router.get('/:id', async (req, res) => {
  try {
    const r = await db.query('SELECT id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date FROM market_regions WHERE id = $1', [req.params.id]);
    if (!r.rows.length) return res.status(404).json({ error: 'not found' });
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// PUT /api/market-regions/:id
router.put('/:id', async (req, res) => {
  const p = req.body;
  try {
    await db.query(`UPDATE market_regions SET name=$1,city=$2,average_price_per_m2=$3,market_heat=$4,demand_score=$5,liquidity_score=$6 WHERE id=$7`, [p.name || null, p.city || null, p.average_price_per_m2 || null, p.market_heat || null, p.demand_score || null, p.liquidity_score || null, req.params.id]);
    const r = await db.query('SELECT id,name,city,average_price_per_m2,market_heat,demand_score,liquidity_score,created_date FROM market_regions WHERE id = $1', [req.params.id]);
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// DELETE /api/market-regions/:id
router.delete('/:id', async (req, res) => {
  try {
    await db.query('DELETE FROM market_regions WHERE id = $1', [req.params.id]);
    res.json({ success: true });
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

module.exports = router;
