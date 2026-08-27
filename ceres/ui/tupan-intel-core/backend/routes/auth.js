const express = require('express');
const router = express.Router();
const db = require('../db');
const { hashPassword, verifyPassword, createToken, verifyToken } = require('../utils/security');

// Register
router.post('/register', async (req, res) => {
  const { email, password, full_name } = req.body || {};
  if (!email || !password) return res.status(400).json({ error: 'email and password required' });
  try {
    const exists = await db.query('SELECT id FROM users WHERE email = $1', [email]);
    if (exists.rows.length) return res.status(400).json({ error: 'email already registered' });
    const id = `user-${Date.now()}`;
    const hashed = hashPassword(password);
    await db.query('INSERT INTO users (id,full_name,email,role,password_hash,created_date) VALUES ($1,$2,$3,$4,$5,now())', [id, full_name || null, email, 'user', hashed]);
    const r = await db.query('SELECT id,full_name,email,role,created_date FROM users WHERE id=$1', [id]);
    return res.status(201).json(r.rows[0]);
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: e.message });
  }
});

// Login
router.post('/login', async (req, res) => {
  const { email, password } = req.body || {};
  if (!email || !password) return res.status(400).json({ error: 'email and password required' });
  try {
    const r = await db.query('SELECT id,full_name,email,role,password_hash FROM users WHERE email = $1', [email]);
    if (!r.rows.length) return res.status(400).json({ error: 'invalid credentials' });
    const user = r.rows[0];
    if (!verifyPassword(password, user.password_hash)) return res.status(400).json({ error: 'invalid credentials' });
    const token = createToken({ sub: user.id, email: user.email });
    return res.json({ access_token: token, token_type: 'bearer', user: { id: user.id, full_name: user.full_name, email: user.email, role: user.role } });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: e.message });
  }
});

// Me
router.get('/me', async (req, res) => {
  const auth = req.headers.authorization;
  if (!auth) return res.status(401).json({ error: 'missing authorization' });
  const parts = auth.split(' ');
  if (parts.length !== 2) return res.status(401).json({ error: 'invalid auth header' });
  const token = parts[1];
  const payload = verifyToken(token);
  if (!payload || !payload.sub) return res.status(401).json({ error: 'invalid token' });
  try {
    const r = await db.query('SELECT id,full_name,email,role,created_date FROM users WHERE id = $1', [payload.sub]);
    if (!r.rows.length) return res.status(404).json({ error: 'not found' });
    const user = r.rows[0];
    // Do not leak sensitive fields
    return res.json({ id: user.id, full_name: user.full_name, email: user.email, role: user.role, created_date: user.created_date });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: e.message });
  }
});

module.exports = router;
