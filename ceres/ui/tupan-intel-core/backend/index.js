require('dotenv').config();
const express = require('express');
const cors = require('cors');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const { errors: celebrateErrors } = require('celebrate');
const app = express();
const routes = require('./routes');

const PORT = process.env.PORT || 4000;

// Basic middleware
// CORS origins can be set via CORS_ORIGINS (comma separated). Default to localhost dev origin.
const origins = process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',').map(s => s.trim()) : [];
if (origins.length === 0) origins.push('http://localhost:5173');
app.use(cors({ origin: origins, credentials: true }));
app.use(helmet());
app.use(compression());
app.use(express.json({ limit: process.env.BODY_LIMIT || '2mb' }));

// Optional structured logging
try {
	const logger = require('./logger');
	app.use((req, res, next) => {
		logger.info({ msg: 'request', method: req.method, path: req.path });
		next();
	});
} catch (e) {
	// no-op if winston not installed
}

// Simple rate limiter to protect heavy endpoints (per IP), configurable via env
app.use(rateLimit({ windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000', 10), max: parseInt(process.env.RATE_LIMIT_MAX || '200', 10) }));

app.use('/api', routes);

// Celebrate validation errors -> turn into HTTP 400
app.use(celebrateErrors());

app.get('/', (req, res) => res.send({ status: 'tupan backend', env: process.env.NODE_ENV || 'dev' }));

app.listen(PORT, () => console.log(`tupan backend listening on port ${PORT}`));
