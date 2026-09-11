// Run: node --test tests/frontend-refinement.test.mjs
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { THEMES } from '../src/lib/themes.js';
import { estate, mockApi, startReview } from './frontend-review.mjs';

let server, browser, origin;
before(async () => { ({ server, browser, origin } = await startReview()); });
after(async () => { await browser?.close(); await server?.close(); });

async function openPage(route, width = 1280) {
  const context = await browser.newContext({ viewport: { width, height: 900 } });
  await mockApi(context);
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(origin + route, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.locator('header h1').waitFor();
  return { page, context };
}
async function withinViewport(locator, page) {
  const box = await locator.boundingBox();
  assert.ok(box, 'element is visible');
  assert.ok(box.x >= -1 && box.x + box.width <= page.viewportSize().width + 1, 'element fits horizontally');
  assert.ok(box.y >= -1 && box.y + box.height <= page.viewportSize().height + 1, 'element fits vertically');
}

test('header, account and notifications remain reachable across five themes and narrow/desktop widths', async () => {
  for (const width of [390, 1280]) {
    const { page, context } = await openPage('/settings', width);
    try {
      for (const theme of THEMES) {
        await page.evaluate(async id => (await import('/src/lib/themes.js')).applyTheme(id), theme.id);
        for (const name of ['Abrir menu', 'Abrir menu da conta', 'Abrir oportunidades da Ceres', 'Recolher cabeçalho']) {
          await withinViewport(page.getByRole('button', { name, exact: true }), page);
        }
        const account = page.getByRole('button', { name: 'Abrir menu da conta' });
        await account.click();
        const menu = page.locator('.user-admin-menu');
        await menu.waitFor();
        await withinViewport(menu, page);
        await page.mouse.click(8, page.viewportSize().height - 8); // Outside the popover, including on narrow screens.
        await menu.waitFor({ state: 'hidden' });

        const bell = page.getByRole('button', { name: 'Abrir oportunidades da Ceres' });
        await bell.click();
        const notifications = page.locator('.notification-anchor aside');
        await notifications.waitFor();
        await withinViewport(notifications, page);
        assert.notEqual(await notifications.evaluate(el => getComputedStyle(el).animationName), 'none', 'entry motion retained');
        await page.mouse.click(8, page.viewportSize().height - 8); // Outside the popover, including on narrow screens.
        await notifications.waitFor({ state: 'hidden' });
      }
      await page.getByRole('button', { name: 'Recolher cabeçalho' }).click();
      const expand = page.getByRole('button', { name: 'Expandir cabeçalho' });
      await expand.click();
      await withinViewport(page.getByRole('button', { name: 'Abrir menu da conta' }), page);
    } finally { await context.close(); }
  }
});

test('distinctive metric selector, context action and dimensional zoom retain their behavior', async () => {
  const { page, context } = await openPage('/overview');
  try {
    const card = page.locator('.kpi-card').first();
    await card.scrollIntoViewIfNeeded();
    const tab = card.getByRole('button', { name: 'Abrir seletor de métricas' });
    const tabBounds = await tab.boundingBox();
    assert.equal(tabBounds.width, 58, 'original tab width');
    await tab.click();
    await card.locator('.metric-knob--open').waitFor();
    await card.locator('.metric-knob__option').filter({ hasText: 'DOM médio' }).click();
    await card.locator('.metric-knob--active').waitFor({ state: 'hidden' });
    assert.ok(await card.getByRole('button', { name: 'Ver série histórica: DOM médio' }).isVisible());
    await card.getByRole('button', { name: 'Adicionar ao painel de contexto', exact: true }).click();
    assert.ok(await page.getByText('Painel de contexto', { exact: true }).isVisible());
    await page.mouse.move(4, 4);
    // Frame sampling checks the actual existing morph, not a replacement animation.
    const samples = await card.evaluate(async el => {
      const samples = [];
      el.querySelector('button[aria-label^="Ver série histórica"]').click();
      const start = performance.now();
      await new Promise(resolve => {
        function frame() {
          const dialog = document.querySelector('.kpi-morph-dialog');
          if (dialog) {
            const rect = dialog.getBoundingClientRect();
            samples.push({ x: rect.x, y: rect.y, width: rect.width, height: rect.height,
              duration: getComputedStyle(dialog).transitionDuration,
              mask: Boolean(dialog.querySelector('.kpi-morph-mask')),
              revealed: Boolean(dialog.querySelector('h2')) });
          }
          if (performance.now() - start < 900) requestAnimationFrame(frame);
          else resolve();
        }
        requestAnimationFrame(frame);
      });
      return samples;
    });
    assert.ok(samples.some(s => s.mask), 'dimensional transition mask remains');
    assert.ok(samples.some(s => s.revealed), 'history revealed after morph');
    assert.ok(new Set(samples.map(s => Math.round(s.width))).size > 3, `zoom is animated rather than a jump; captured widths: ${samples.map(s => Math.round(s.width)).join(', ')}`);
    assert.ok(samples.every(s => s.duration.split(',').every(d => d.trim() === '0.5s')));
    const final = samples.at(-1);
    assert.ok(Math.abs(final.width - 760) < 1);
    assert.ok(Math.abs(final.x - (1280 - 760) / 2) < 1);
    for (let i = 1; i < samples.length; i++) {
      assert.ok(samples[i].width + 0.5 >= samples[i - 1].width, 'direct, monotonic zoom path');
    }
    await page.getByRole('button', { name: 'Fechar série histórica' }).click();
    await page.locator('.kpi-morph-dialog').waitFor({ state: 'hidden' });
    assert.equal(await card.evaluate(el => getComputedStyle(el).opacity), '1', 'original card returns');

    await page.getByRole('button', { name: 'Navegar por seções' }).click();
    await page.getByRole('button', { name: /Mercado e demanda/ }).click();
    assert.ok(await page.getByRole('heading', { name: 'Tendências de mercado', exact: true }).isVisible());
  } finally { await context.close(); }
});

test('narrow split views retain usable content and property details can be closed', async () => {
  const { page, context } = await openPage('/agent-log', 390);
  try {
    const area = page.locator('.workspace-content');
    assert.ok((await area.boundingBox()).width >= 350);
    await page.goto(origin + '/data');
    await page.getByRole('heading', { name: 'Cadastrar imóvel' }).waitFor();
    assert.ok((await page.locator('.workspace-content').boundingBox()).width >= 350);
    await page.goto(origin + '/properties');
    await page.getByRole('cell', { name: /Apartamento Jardim Paulista/ }).first().click();
    const close = page.getByRole('button', { name: 'Fechar detalhes do imóvel' });
    await withinViewport(close, page);
    await close.click();
    await close.waitFor({ state: 'hidden' });
    assert.ok(await page.getByRole('cell', { name: /Apartamento Jardim Paulista/ }).first().isVisible());
  } finally { await context.close(); }
});

test('portfolio context button belongs to its summary; absent profile data has no decorative radar', async () => {
  const { page, context } = await openPage('/portfolio');
  try {
    const summary = page.locator('.sc1-section');
    await summary.waitFor();
    const box = await summary.boundingBox();
    const button = await summary.getByRole('button').boundingBox();
    assert.ok(button.x >= box.x && button.x + button.width <= box.x + box.width);
    assert.ok(button.y >= box.y && button.y + button.height <= box.y + box.height);
    await page.goto(origin + '/properties/review-estate');
    await page.getByText('Perfil ainda não disponível para este imóvel.').waitFor();
    assert.equal(await page.locator('.recharts-radar').count(), 0);
  } finally { await context.close(); }
});

test('comparison handles two selected estates, missing values and meaningful differences', async () => {
  const { page, context } = await openPage('/compare');
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    const second = { ...estate, id: 'review-second', location: { ...estate.location, address: 'Segundo imóvel de teste' }, pricing: { asking_price: 1500000 }, metrics: { ...estate.metrics, area_m2: 120, rooms: 4 } };
    await context.route('**/api/v1/properties*', route => route.fulfill({ json: { items: [estate, second], page: { total: 2, offset: 0, limit: 100 } } }));
    await page.goto(origin + '/compare?a=review-estate&b=review-second');
    await page.getByRole('rowheader', { name: 'Preço de pedido', exact: true }).waitFor();
    assert.ok(await page.getByRole('row', { name: /Preço de pedido/ }).getByText('R$ 1.250.000', { exact: true }).isVisible());
    assert.equal(await page.locator('.comparison-matrix tbody tr').count(), 17, 'all comparison attributes remain');
    assert.ok(await page.getByText('Principais diferenças', { exact: true }).isVisible());
    assert.equal(await page.locator('.recharts-radar').count(), 0, 'no unsupported profile is plotted');
    assert.deepEqual(errors, [], 'selected comparison does not crash');
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'only the matrix scrolls horizontally');
    await page.locator('#compare-b').click();
    await page.getByRole('option', { name: '— Remover seleção —' }).click();
    await page.getByText('Selecione dois imóveis para visualizar a comparação lado a lado.').waitFor();
  } finally { await context.close(); }
});

test('portfolio summary exposes all indicators and retains historical exploration', async () => {
  const { page, context } = await openPage('/portfolio');
  try {
    await page.locator('.portfolio-summary').waitFor();
    assert.equal(await page.locator('.portfolio-summary dt').count(), 13, '11 indicators plus variation and period');
    await page.getByText('Séries e indicadores', { exact: false }).click();
    assert.equal(await page.locator('.portfolio-indicators .kpi-card').count(), 12);
    await page.locator('.portfolio-indicators .kpi-card').first().getByRole('button', { name: 'Ver série histórica: Valor total do portfólio' }).click();
    await page.getByRole('button', { name: 'Fechar série histórica' }).waitFor();
    await page.getByRole('button', { name: 'Fechar série histórica' }).click();
    await page.locator('.kpi-morph-dialog').waitFor({ state: 'hidden' });
  } finally { await context.close(); }
});

test('market history remains visible when changing the display horizon', async () => {
  const { page, context } = await openPage('/overview');
  try {
    await page.getByRole('button', { name: 'Navegar por seções' }).click();
    await page.getByRole('button', { name: /Mercado e demanda/ }).click();
    await page.getByRole('button', { name: /Centro de comando/ }).waitFor({ state: 'hidden' });
    const chart = page.locator('#overview-market .recharts-area-curve').first();
    await page.waitForFunction(() => document.querySelector('#overview-market .recharts-area-curve')?.getBoundingClientRect().height > 1);
    assert.ok((await chart.getAttribute('d')).length > 20, 'real history produces a chart path');
    await page.locator('#overview-market').getByRole('combobox').nth(1).click();
    await page.getByRole('option', { name: '36 meses', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#overview-market .recharts-area-curve')?.getBoundingClientRect().height > 1);
    assert.ok(await page.locator('#overview-market').getByText('R$ 12.500', { exact: true }).first().isVisible());
  } finally { await context.close(); }
});
