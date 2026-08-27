// Simple smoke test for backend endpoints
const fetch = require('node-fetch');

async function check(url) {
  try {
    const r = await fetch(url, { timeout: 5000 });
    console.log(url, r.status);
    return r.ok;
  } catch (e) {
    console.error(url, 'error', e.message);
    return false;
  }
}

(async () => {
  const urls = [
    process.env.NODE_BACKEND_URL || 'http://localhost:4000/api/properties',
    process.env.PY_BACKEND_URL || 'http://localhost:8000/api/properties',
  ];
  let ok = true;
  for (const u of urls) {
    const r = await check(u);
    ok = ok && r;
  }
  process.exit(ok ? 0 : 2);
})();
