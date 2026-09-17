// Optional integration presentation check using the real, read-only backend
// snapshot produced by backend.verify_demo_portfolio. No login/session writes.
import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { test } from 'node:test';
import { startReview } from './frontend-review.mjs';

test('seeded portfolio and published ITBI cells render from backend responses', {skip: !process.env.DEMO_SNAPSHOT_PATH, timeout: 180000}, async () => {
  const snapshot = JSON.parse(await readFile(process.env.DEMO_SNAPSHOT_PATH, 'utf8'));
  const {server, browser, origin} = await startReview();
  const directory = join(tmpdir(), 'ceres-demo-20260913');
  await mkdir(directory, {recursive:true});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:900}});
    await context.route('**/api/v1/**', route => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace('/api/v1', '');
      const body = snapshot[path + url.search] ?? snapshot[path];
      if (body) return route.fulfill({json:body});
      if (path.startsWith('/workspace/')) return route.fulfill({json:[]});
      return route.fulfill({status:503,json:{message:'Not captured in this read-only scenario'}});
    });
    const page = await context.newPage();
    page.setDefaultTimeout(45000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin + '/portfolio', {waitUntil:'domcontentloaded',timeout:90000});
    await page.getByRole('heading', {name:'Inteligência de Portfólio'}).waitFor();
    await page.getByText('Carteira mock para testar Ceres.', {exact:false}).waitFor();
    await page.locator('.recharts-pie').first().waitFor();
    await page.screenshot({path:join(directory,'portfolio.png')});
    await page.goto(origin + '/market-map', {waitUntil:'domcontentloaded',timeout:90000});
    await page.locator('.leaflet-container').waitFor();
    await page.getByText('Transações ITBI · cobertura parcial geocodificada', {exact:true}).waitFor();
    const cellCount = snapshot['/market/heatmap'].cells.length;
    await page.getByText(`${cellCount} células H3`, {exact:false}).waitFor();
    const box = await page.locator('.leaflet-container').boundingBox();
    assert.ok(box.width > 500 && box.height > 300, 'map occupies usable space');
    await page.screenshot({path:join(directory,'map.png')});
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({cellCount,screenshots:directory}));
  } finally {
    await browser.close();
    await server.close();
  }
});
