const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const SECRET = process.env.JWT_SECRET || process.env.SECRET_KEY;
if (!SECRET) console.warn('Warning: JWT_SECRET is not set — using development secret');
const EXPIRES_IN = process.env.JWT_EXPIRES_IN || '24h';

function hashPassword(password) {
  return bcrypt.hashSync(password, 10);
}

function verifyPassword(password, hash) {
  return bcrypt.compareSync(password, hash);
}

function createToken(payload) {
  return jwt.sign(payload, SECRET, { expiresIn: EXPIRES_IN });
}

function verifyToken(token) {
  try {
    return jwt.verify(token, SECRET);
  } catch (e) {
    return null;
  }
}

module.exports = { hashPassword, verifyPassword, createToken, verifyToken };
