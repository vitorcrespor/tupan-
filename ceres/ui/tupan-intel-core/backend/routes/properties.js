const express = require('express');
const router = express.Router();
const db = require('../db');
const { v4: uuidv4 } = require('uuid');
const { celebrate, Joi, Segments } = require('celebrate');

const propertySchema = Joi.object({
  id: Joi.string().optional(),
  title: Joi.string().allow(null, ''),
  address: Joi.string().allow(null, ''),
  city: Joi.string().allow(null, ''),
  neighborhood: Joi.string().allow(null, ''),
  latitude: Joi.number().optional().allow(null),
  longitude: Joi.number().optional().allow(null),
  price: Joi.number().integer().optional().allow(null),
  price_per_m2: Joi.number().integer().optional().allow(null)
});

const bulkSchema = Joi.object({ items: Joi.array().items(propertySchema).max(500) });

const filterSchema = Joi.object({ query: Joi.object().optional(), limit: Joi.number().integer().min(1).max(1000).optional() });

// GET /api/properties?sort=&limit=
router.get('/', async (req, res) => {
  const limit = Math.min(parseInt(req.query.limit || '200', 10), 1000);
  try {
    const cols = 'id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date';
    const result = await db.query(`SELECT ${cols} FROM properties ORDER BY created_date DESC LIMIT $1`, [limit]);
    res.json(result.rows);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

// POST /api/properties
router.post('/', celebrate({ [Segments.BODY]: propertySchema }), async (req, res) => {
  const p = req.body;
  const id = p.id || `property-${uuidv4()}`;
  try {
    await db.query(`INSERT INTO properties (id, title, address, city, neighborhood, latitude, longitude, price, price_per_m2, created_date, updated_date)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,now(),now())`, [id, p.title, p.address, p.city, p.neighborhood, p.latitude, p.longitude, p.price || null, p.price_per_m2 || null]);
    const r = await db.query('SELECT id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date FROM properties WHERE id = $1', [id]);
    res.status(201).json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// POST /api/properties/bulk
router.post('/bulk', celebrate({ [Segments.BODY]: bulkSchema }), async (req, res) => {
  const items = (req.body.items || []).slice(0, 500); // cap bulk size
  if (!items.length) return res.json({ success: true, inserted: 0 });
  const client = await db.pool.connect();
  try {
    await client.query('BEGIN');
    const cols = ['id','title','address','city','neighborhood','latitude','longitude','price','price_per_m2'];
    const values = [];
    const placeholders = items.map((p, rowIndex) => {
      const id = p.id || `property-${uuidv4()}`;
      const rowVals = [id, p.title || null, p.address || null, p.city || null, p.neighborhood || null, p.latitude || null, p.longitude || null, p.price || null, p.price_per_m2 || null];
      values.push(...rowVals);
      const start = rowIndex * rowVals.length + 1;
      const ph = rowVals.map((_, i) => `$${start + i}`).join(',');
      return `(${ph}, now(), now())`;
    });
    // Build query with explicit columns plus created/updated
    const insertCols = cols.join(',') + ',created_date,updated_date';
    const queryText = `INSERT INTO properties (${insertCols}) VALUES ${placeholders.join(',')}`;
    await client.query(queryText, values);
    await client.query('COMMIT');
    res.json({ success: true, inserted: items.length });
  } catch (e) { await client.query('ROLLBACK'); console.error(e); res.status(500).json({ error: e.message }); } finally { client.release(); }
});

// POST /api/properties/filter
router.post('/filter', celebrate({ [Segments.BODY]: filterSchema }), async (req, res) => {
  const { query = {}, limit = 100 } = req.body;
  try {
    const allowed = ['id','title','address','city','neighborhood','price','price_per_m2'];
    const keys = Object.keys(query || {}).filter(k => allowed.includes(k));
    const params = [];
    let sql = 'SELECT id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date FROM properties';
    if (keys.length) {
      const where = keys.map((k, i) => { params.push(query[k]); return `${k} = $${i + 1}`; }).join(' AND ');
      sql += ` WHERE ${where}`;
    }
    sql += ` ORDER BY created_date DESC LIMIT ${Math.min(limit || 100, 1000)}`;
    const result = await db.query(sql, params);
    res.json(result.rows);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// GET /api/properties/:id
router.get('/:id', async (req, res) => {
  try {
    const r = await db.query('SELECT id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date FROM properties WHERE id = $1', [req.params.id]);
    if (!r.rows.length) return res.status(404).json({ error: 'not found' });
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// PUT /api/properties/:id
router.put('/:id', celebrate({ [Segments.BODY]: propertySchema }), async (req, res) => {
  const p = req.body;
  try {
    await db.query(`UPDATE properties SET title=$1,address=$2,city=$3,neighborhood=$4,latitude=$5,longitude=$6,price=$7,price_per_m2=$8,updated_date=now() WHERE id=$9`, [p.title, p.address, p.city, p.neighborhood, p.latitude, p.longitude, p.price || null, p.price_per_m2 || null, req.params.id]);
    const r = await db.query('SELECT id,title,address,city,neighborhood,latitude,longitude,price,price_per_m2,created_date,updated_date FROM properties WHERE id = $1', [req.params.id]);
    res.json(r.rows[0]);
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

// DELETE /api/properties/:id
router.delete('/:id', async (req, res) => {
  try {
    await db.query('DELETE FROM properties WHERE id = $1', [req.params.id]);
    res.json({ success: true });
  } catch (e) { console.error(e); res.status(500).json({ error: e.message }); }
});

module.exports = router;
