const express = require('express');
const router = express.Router();
const fetch = require('node-fetch');
const rateLimit = require('express-rate-limit');

// Simple in-memory circuit breaker state
let llmFailures = 0;
let llmCircuitOpenUntil = 0;
const MAX_FAILURES = parseInt(process.env.LLM_CIRCUIT_MAX_FAILURES || '5', 10);
const CIRCUIT_COOLDOWN_MS = parseInt(process.env.LLM_CIRCUIT_COOLDOWN_MS || '60000', 10);
const MAX_RETRIES = parseInt(process.env.LLM_MAX_RETRIES || '2', 10);

// Per-route rate limiter for LLM endpoint (default stricter limits)
const llmLimiter = rateLimit({ windowMs: parseInt(process.env.LLM_RATE_LIMIT_WINDOW_MS || '60000', 10), max: parseInt(process.env.LLM_RATE_LIMIT_MAX || '20', 10) });

// POST /api/llm/invoke
router.post('/invoke', llmLimiter, async (req, res) => {
  const { prompt } = req.body || {};
  if (!process.env.LLM_API_URL) {
    return res.json({ text: `Local LLM stub: ${String(prompt || '').slice(0,180)}` });
  }

  // Circuit open? fast-fail
  if (llmCircuitOpenUntil && Date.now() < llmCircuitOpenUntil) {
    return res.status(503).json({ error: 'LLM provider temporarily unavailable (circuit open)' });
  }

  const timeoutMs = parseInt(process.env.LLM_TIMEOUT_MS || '15000', 10);
  const headers = { 'Content-Type': 'application/json' };
  if (process.env.LLM_API_KEY) headers.Authorization = `Bearer ${process.env.LLM_API_KEY}`;

  let lastErr = null;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const r = await fetch(process.env.LLM_API_URL, {
        method: 'POST',
        headers,
        body: JSON.stringify({ prompt }),
        signal: controller.signal,
      });
      clearTimeout(timeout);
      if (!r.ok) {
        lastErr = new Error(`LLM provider returned ${r.status}`);
        // treat 5xx as retryable
        if (r.status >= 500 && attempt < MAX_RETRIES) {
          await new Promise((s) => setTimeout(s, 200 * Math.pow(2, attempt)));
          continue;
        }
        // non-retryable
        throw lastErr;
      }
      const data = await r.json();
      // success -> reset failures and return
      llmFailures = 0;
      return res.json(data);
    } catch (e) {
      clearTimeout(timeout);
      lastErr = e;
      if (e.name === 'AbortError') {
        // timeout
        lastErr = new Error('LLM request timed out');
      }
      // retryable network/server errors
      if (attempt < MAX_RETRIES) {
        await new Promise((s) => setTimeout(s, 200 * Math.pow(2, attempt)));
        continue;
      }
      // mark failure
      llmFailures++;
      if (llmFailures >= MAX_FAILURES) {
        llmCircuitOpenUntil = Date.now() + CIRCUIT_COOLDOWN_MS;
      }
      console.error('LLM proxy error:', e);
      if (e.message && e.message.includes('timed out')) return res.status(504).json({ error: 'LLM request timed out' });
      return res.status(502).json({ error: lastErr.message || 'LLM error' });
    }
  }
});

module.exports = router;
