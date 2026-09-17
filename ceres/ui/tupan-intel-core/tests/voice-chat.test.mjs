// Run: node --test tests/voice-chat.test.mjs
// Requires Playwright (or PLAYWRIGHT_MODULE pointing to an installed package).
// PLAYWRIGHT_CHANNEL may select an installed browser, e.g. chrome or msedge.
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createRequire } from 'node:module';
import { createServer } from 'vite';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
let server;
let browser;
let origin;

before(async () => {
  server = await createServer({
    cacheDir: 'node_modules/.vite-voice-chat-tests',
    server: { host: '127.0.0.1', port: 0, strictPort: false, open: false },
    define: {
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify('/api/v1'),
      'import.meta.env.VITE_TUPAN_API_URL': JSON.stringify('/api/v1'),
    },
    plugins: [{
      name: 'voice-chat-test-entry',
      configureServer(vite) {
        vite.middlewares.use('/__voice-chat-test.html', async (_req, res, next) => {
          try {
            const html = await vite.transformIndexHtml('/__voice-chat-test.html',
              '<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="root"></div><script type="module" src="/tests/fixtures/voice-chat.jsx"></script></body></html>');
            res.setHeader('Content-Type', 'text/html');
            res.end(html);
          } catch (error) { next(error); }
        });
      },
    }],
  });
  await server.listen();
  origin = `http://127.0.0.1:${server.httpServer.address().port}`;
  const entry = await fetch(`${origin}/__voice-chat-test.html`);
  if (!entry.ok) throw new Error(`Voice-chat test entry failed to warm up: HTTP ${entry.status}`);
  await entry.text();
  await server.warmupRequest('/tests/fixtures/voice-chat.jsx');
  const fixture = await fetch(`${origin}/tests/fixtures/voice-chat.jsx`);
  if (!fixture.ok) throw new Error(`Voice-chat test module failed to warm up: HTTP ${fixture.status}`);
  await fixture.text();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.PLAYWRIGHT_CHANNEL,
    args: [
      '--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows',
      '--disable-renderer-backgrounding',
    ],
  });
});

after(async () => {
  await browser?.close();
  await server?.close();
});

for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`agent history: native scroll, fading and chronological flow at ${viewport.width}px`, async () => {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const runtimeErrors = [];
    page.on('pageerror', error => runtimeErrors.push(error.message));
    let pending;
    await context.route('**/api/v1/**', route => {
      // No test data or AI requests may reach a real backend.
      if (new URL(route.request().url()).pathname === '/api/v1/agent/chat') pending = route;
      else return route.abort();
    });
    try {
      await page.goto(`${origin}/__voice-chat-test.html`, { waitUntil: 'domcontentloaded', timeout: 60000 });
      const input = page.getByPlaceholder('Fale ou digite para o Ceres…');
      await input.waitFor({ state: 'attached', timeout: 120000 });
      const stage = page.locator('#voice-chat-history');
      const messages = page.locator('.voice-chat-message');
      const send = async text => {
        pending = null;
        await input.fill(text);
        const sendButton = page.getByTitle('Enviar');
        await page.waitForFunction(
          () => !document.querySelector('button[title="Enviar"]')?.disabled,
          null,
          { polling: 25, timeout: 10000 },
        );
        await sendButton.evaluate(element => element.click());
        for (let i = 0; !pending && i < 100; i++) await page.waitForTimeout(30);
        assert.ok(pending, 'question must reach the frontend API service');
      };
      const respond = async (text, status = 200) => {
        await pending.fulfill({ status, contentType: 'application/json', body: JSON.stringify(
          status === 200 ? { message: { content: text } } : { message: text, code: 'dependency_unavailable' },
        ) });
        await page.getByRole('status').waitFor({ state: 'hidden' });
      };

      await send('Primeira pergunta de teste');
      await page.waitForTimeout(700); // Allow the existing shell entrance animation.
      const stageBox = await stage.boundingBox();
      const firstBox = await messages.first().boundingBox();
      assert.ok(firstBox.y >= stageBox.y + 112, 'pending question must be below the fade zone');
      assert.ok(firstBox.y + firstBox.height <= stageBox.y + stageBox.height, 'pending question fits the viewport');
      await respond('Resposta de teste.');
      await send('Segunda pergunta\ncom uma nova linha');
      const boxes = await messages.evaluateAll(elements => elements.map(el => {
        const r = el.getBoundingClientRect();
        return { x: r.x, y: r.y, bottom: r.bottom, width: r.width };
      }));
      assert.equal(boxes.length, 3);
      for (let i = 1; i < boxes.length; i++) {
        assert.ok(boxes[i].y >= boxes[i - 1].bottom, 'messages must never overlap or sit side by side');
        assert.equal(boxes[i].x, boxes[0].x);
        assert.equal(boxes[i].width, boxes[0].width);
      }
      assert.equal(await messages.last().evaluate(el => getComputedStyle(el).whiteSpace), 'pre-wrap');
      await respond('Falha simulada no provedor de teste.', 503);
      assert.ok(await page.getByRole('alert').isVisible(), 'backend errors remain visible');

      for (let i = 0; i < 6; i++) {
        await send(`Pergunta longa ${i}`);
        await respond(`Resposta ${i}: ` + 'Conteúdo de teste para validar a leitura do histórico. '.repeat(32));
      }
      const hoverStage = async () => {
        const box = await stage.boundingBox();
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      };
      await hoverStage();
      await stage.focus();
      const bottom = await stage.evaluate(el => ({ top: el.scrollTop, height: el.clientHeight, total: el.scrollHeight, width: el.clientWidth }));
      assert.ok(bottom.total > bottom.height * 2, 'long history has positive reachable overflow');
      assert.ok(bottom.top > 0, 'new replies initially follow the conversation end');
      for (let i = 0; i < 20; i++) {
        await page.mouse.wheel(0, -24);
        await page.waitForTimeout(20);
      }
      await page.waitForFunction(
        initialTop => document.querySelector('#voice-chat-history')?.scrollTop < initialTop - 100,
        bottom.top,
        { polling: 50, timeout: 15000 },
      );
      const afterWheel = await stage.evaluate(el => el.scrollTop);
      assert.ok(afterWheel < bottom.top - 100, 'small trackpad-style wheel deltas scroll the history');
      assert.notEqual(await stage.evaluate(el => getComputedStyle(el).scrollbarColor), 'rgba(0, 0, 0, 0) rgba(0, 0, 0, 0)', 'scrollbar thumb is visible on hover');
      await page.mouse.move(4, 4);
      assert.equal(await stage.evaluate(el => el.clientWidth), bottom.width, 'hover scrollbar never shifts the text');
      assert.notEqual(await stage.evaluate(el => getComputedStyle(el).maskImage), 'none', 'HeroUI top fade is applied');
      const blur = await page.locator('.voice-chat-edge-blur').evaluate(el => {
        const s = getComputedStyle(el);
        return { filter: s.backdropFilter, mask: s.maskImage, background: s.backgroundColor, events: s.pointerEvents };
      });
      assert.equal(blur.filter, 'blur(6px)');
      assert.notEqual(blur.mask, 'none');
      assert.equal(blur.background, 'rgba(0, 0, 0, 0)');
      assert.equal(blur.events, 'none');

      await stage.focus();
      await page.keyboard.press('Control+Home');
      await page.waitForTimeout(250);
      assert.equal(await stage.evaluate(el => el.scrollTop), 0, 'oldest messages are reachable');
      await page.keyboard.press('PageDown');
      await page.waitForTimeout(250);
      assert.ok(await stage.evaluate(el => el.scrollTop) > 0, 'keyboard scrolling works too');
      if (process.env.VOICE_CHAT_SCREENSHOT_DIR) {
        await page.screenshot({ path: `${process.env.VOICE_CHAT_SCREENSHOT_DIR}/voice-chat-${viewport.width}.png` });
      }
      const messageCount = await messages.count();
      await page.getByRole('button', { name: 'Recolher conversa' }).evaluate(element => element.click());
      await page.waitForFunction(
        () => Number(getComputedStyle(document.querySelector('.voice-chat-frame')).opacity) < 0.02,
        null,
        { polling: 25, timeout: 5000 },
      );
      assert.ok(
        Number(await page.locator('.voice-chat-frame').evaluate(el => getComputedStyle(el).opacity)) < 0.02,
        'collapsed history is visually absent',
      );
      await send('Pergunta após recolher');
      assert.equal(await messages.count(), messageCount + 1, 'collapsing must not erase history');
      await hoverStage();
      await page.mouse.wheel(0, -320);
      await page.waitForTimeout(250);
      const readingPosition = await stage.evaluate(el => el.scrollTop);
      const anchor = messages.nth(Math.max(0, (await messages.count()) - 2));
      const readingAnchorY = (await anchor.boundingBox()).y;
      await respond('Nova resposta de teste.');
      await page.waitForTimeout(150);
      const updatedPosition = await stage.evaluate(el => el.scrollTop);
      const updatedAnchorY = (await anchor.boundingBox()).y;
      assert.ok(Math.abs(updatedAnchorY - readingAnchorY) < 2, `a reply must not move the message being read (${readingPosition} → ${updatedPosition})`);
      assert.deepEqual(runtimeErrors, [], 'no browser runtime errors');
      console.log(JSON.stringify({ viewport, scroll: bottom, afterWheel, blur }));
    } finally { await context.close(); }
  });
}
