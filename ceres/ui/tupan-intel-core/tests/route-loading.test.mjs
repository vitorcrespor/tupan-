// Run: node --test tests/route-loading.test.mjs
// PLAYWRIGHT_MODULE and PLAYWRIGHT_CHANNEL follow voice-chat.test.mjs.
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createRequire } from 'node:module';
import { createServer } from 'vite';
import { THEMES } from '../src/lib/themes.js';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
let server, browser, origin;

before(async () => {
  server = await createServer({
    cacheDir: 'node_modules/.vite-route-loading-tests',
    server: { host: '127.0.0.1', port: 0, strictPort: false, open: false },
    define: {
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify('/api/v1'),
      'import.meta.env.VITE_TUPAN_API_URL': JSON.stringify('/api/v1'),
    },
  });
  await server.listen();
  origin = `http://127.0.0.1:${server.httpServer.address().port}`;
  browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
});

after(async () => {
  await browser?.close();
  await server?.close();
});

async function checkViewport(page, viewport) {
  const bounds = await page.getByRole('status').boundingBox();
  assert.equal(bounds.x, 0);
  assert.equal(bounds.y, 0);
  assert.equal(bounds.width, viewport.width);
  assert.equal(bounds.height, viewport.height, 'loading state must cover the viewport');
  const canvas = await page.evaluate(() => ({
    root: getComputedStyle(document.documentElement).backgroundColor,
    body: getComputedStyle(document.body).backgroundColor,
    height: document.body.getBoundingClientRect().height,
    width: document.documentElement.scrollWidth,
  }));
  assert.equal(canvas.root, canvas.body, 'root canvas must match the current theme');
  assert.notEqual(canvas.root, 'rgb(0, 0, 0)', 'no unrelated black canvas beneath the loader');
  assert.equal(canvas.height, viewport.height);
  assert.equal(canvas.width, viewport.width, 'no horizontal overflow');
  const indicator = await page.getByRole('status').locator(':scope > span').boundingBox();
  assert.ok(Math.abs(indicator.y + indicator.height / 2 - viewport.height / 2) < 1);
}

for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`auth loading covers the viewport in all five themes at ${viewport.width}px`, async () => {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let session;
    // Test-only interception: no fixture account or request reaches the backend.
    await context.route('**/api/v1/**', route => {
      if (new URL(route.request().url()).pathname === '/api/v1/auth/session') session = route;
      else return route.abort();
    });
    try {
      await page.goto(`${origin}/overview`, { waitUntil: 'domcontentloaded', timeout: 90000 });
      await page.getByRole('status').filter({ hasText: 'Carregando área de trabalho' }).waitFor({ timeout: 30000 });
      for (const theme of THEMES) {
        await page.evaluate(async id => {
          const { applyTheme } = await import('/src/lib/themes.js');
          applyTheme(id);
        }, theme.id);
        await checkViewport(page, viewport);
        if (process.env.LOADING_SCREENSHOT_DIR && ['midnight', 'sand'].includes(theme.id)) {
          await page.screenshot({ path: `${process.env.LOADING_SCREENSHOT_DIR}/tupan-loading-after-${theme.id}-${viewport.width}.png` });
        }
      }
      assert.ok(session, 'session request is in flight');
      await session.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ code: 'authentication_required', message: 'Sign in required' }) });
      await page.waitForURL('**/login');
      await page.getByRole('status').waitFor({ state: 'hidden' });
      assert.ok(await page.locator('input[type=password]').isVisible(), 'login remains usable after loading');
      assert.deepEqual(errors, []);
    } finally { await context.close(); }
  });
}

test('lazy route loading uses the same full-screen fallback and respects reduced motion', async () => {
  const viewport = { width: 1440, height: 900 };
  const context = await browser.newContext({ viewport, reducedMotion: 'reduce' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  let routeModule;
  await context.route('**/api/v1/**', route => route.fulfill({ status: 401, contentType: 'application/json', body: '{}' }));
  await context.route(/\/src\/pages\/Login\.jsx(?:\?|$)/, route => { routeModule = route; });
  try {
    await page.goto(`${origin}/login`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.getByRole('status').waitFor({ timeout: 30000 });
    await checkViewport(page, viewport);
    assert.equal(await page.locator('[role=status] [aria-hidden=true]').evaluate(el => getComputedStyle(el).animationName), 'none');
    assert.ok(routeModule);
    await routeModule.continue();
    await page.getByRole('status').waitFor({ state: 'hidden' });
    assert.ok(await page.locator('input[type=password]').isVisible());
  } finally { await context.close(); }
});
