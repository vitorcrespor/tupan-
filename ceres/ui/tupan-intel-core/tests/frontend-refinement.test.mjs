// Run: node --test tests/frontend-refinement.test.mjs
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { THEMES } from '../src/lib/themes.js';
import { estate, estateRecord, mockApi, startReview } from './frontend-review.mjs';

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

// Product motion intentionally moves several anchored controls while their
// panels enter/exit. Playwright's default actionability check requires a
// perfectly stationary bounding box, which real pointer input does not. Every
// forced action below is followed by an assertion on the resulting behavior.
const activate = locator => locator.evaluate(element => element.click());

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
        await activate(account);
        const menu = page.locator('.user-admin-menu');
        await menu.waitFor({ state: 'attached' });
        assert.equal(await account.getAttribute('aria-expanded'), 'true');
        await withinViewport(menu, page);
        await page.mouse.click(8, page.viewportSize().height - 8); // Outside the popover, including on narrow screens.
        assert.equal(await account.getAttribute('aria-expanded'), 'false');
        assert.ok((await menu.getAttribute('class')).includes('anchored-popover--exit'));

        const bell = page.getByRole('button', { name: 'Abrir oportunidades da Ceres' });
        await activate(bell);
        const notifications = page.locator('.notification-anchor aside');
        await notifications.waitFor({ state: 'attached' });
        assert.equal(await bell.getAttribute('aria-expanded'), 'true');
        await withinViewport(notifications, page);
        assert.notEqual(await notifications.evaluate(el => getComputedStyle(el).animationName), 'none', 'entry motion retained');
        await page.mouse.click(8, page.viewportSize().height - 8); // Outside the popover, including on narrow screens.
        assert.equal(await bell.getAttribute('aria-expanded'), 'false');
        assert.ok((await notifications.getAttribute('class')).includes('anchored-popover--exit'));
      }
      await activate(page.getByRole('button', { name: 'Recolher cabeçalho' }));
      const expand = page.getByRole('button', { name: 'Expandir cabeçalho' });
      await activate(expand);
      await withinViewport(page.getByRole('button', { name: 'Abrir menu da conta' }), page);
    } finally { await context.close(); }
  }
});

test('distinctive metric selector, context action and dimensional zoom retain their behavior', async () => {
  const { page, context } = await openPage('/overview');
  try {
    const card = page.locator('.kpi-card').first();
    await card.evaluate(element => element.scrollIntoView({ block: 'center' }));
    const tab = card.getByRole('button', { name: 'Abrir seletor de métricas' });
    const tabBounds = await tab.boundingBox();
    assert.equal(tabBounds.width, 58, 'original tab width');
    await activate(tab);
    await card.locator('.metric-knob--open').waitFor();
    await activate(card.locator('.metric-knob__option').filter({ hasText: 'DOM médio' }));
    await card.locator('.metric-knob--active').waitFor({ state: 'hidden' });
    assert.ok(await card.getByRole('button', { name: 'Ver série histórica: DOM médio' }).isVisible());
    await activate(card.getByRole('button', { name: 'Adicionar ao painel de contexto', exact: true }));
    assert.ok(await page.getByText('Painel de contexto', { exact: true }).isVisible());
    await page.mouse.move(4, 4);
    // The product uses two requestAnimationFrame callbacks to separate origin
    // and destination renders. Headless Edge can throttle those callbacks for
    // minutes, so this test flushes that scheduling boundary and then samples
    // the browser's real CSS transition at its midpoint.
    const transition = await card.evaluate(async el => {
      const originWidth = el.getBoundingClientRect().width;
      let maskSeen = false;
      const styleWidths = [];
      const observer = new MutationObserver(() => {
        if (document.querySelector('.kpi-morph-mask')) maskSeen = true;
        const width = Number.parseFloat(document.querySelector('.kpi-morph-dialog')?.style.width || '');
        if (Number.isFinite(width) && !styleWidths.includes(width)) styleWidths.push(width);
      });
      observer.observe(document.body, { childList: true, subtree: true });
      const nativeRequestAnimationFrame = window.requestAnimationFrame;
      const frameQueue = [];
      window.requestAnimationFrame = callback => {
        frameQueue.push(callback);
        return frameQueue.length;
      };
      el.querySelector('button[aria-label^="Ver série histórica"]').click();
      await Promise.resolve();
      await new Promise(resolve => setTimeout(resolve, 0));
      while (frameQueue.length) {
        frameQueue.shift()(performance.now());
        await Promise.resolve();
      }
      window.requestAnimationFrame = nativeRequestAnimationFrame;
      await new Promise(resolve => setTimeout(resolve, 0));
      const dialog = document.querySelector('.kpi-morph-dialog');
      const style = getComputedStyle(dialog);
      const animations = dialog?.getAnimations() || [];
      animations.forEach(animation => {
        animation.pause();
        animation.currentTime = 250;
      });
      const intermediateWidth = dialog?.getBoundingClientRect().width;
      animations.forEach(animation => animation.finish());
      const finalRect = dialog?.getBoundingClientRect();
      await new Promise(resolve => setTimeout(resolve, 560));
      const revealed = Boolean(dialog?.querySelector('h2'));
      observer.disconnect();
      return {
        maskSeen,
        originWidth,
        styleWidths,
        intermediateWidth,
        duration: style.transitionDuration,
        properties: style.transitionProperty,
        revealed,
        final: finalRect ? { x: finalRect.x, width: finalRect.width } : null,
      };
    });
    assert.ok(transition.maskSeen, 'dimensional transition mask remains');
    assert.ok(transition.revealed, 'history revealed after morph');
    assert.ok(transition.styleWidths.length >= 2, `zoom changes from origin to destination geometry: ${transition.styleWidths.join(', ')}`);
    assert.ok(transition.styleWidths.at(-1) > transition.styleWidths[0], 'zoom path expands directly toward the dialog');
    assert.ok(transition.duration.split(',').every(d => d.trim() === '0.5s'));
    assert.ok(['left', 'top', 'width', 'height'].every(property => transition.properties.includes(property)));
    const final = transition.final;
    assert.ok(Math.abs(final.width - 760) < 1);
    assert.ok(Math.abs(final.x - (1280 - 760) / 2) < 1);
    await activate(page.getByRole('button', { name: 'Fechar série histórica' }));
    await page.locator('.kpi-morph-dialog').waitFor({ state: 'hidden' });
    await page.waitForFunction(
      element => getComputedStyle(element).opacity === '1',
      await card.elementHandle(),
    );
    assert.equal(await card.evaluate(el => getComputedStyle(el).opacity), '1', 'original card returns');

    await activate(page.getByRole('button', { name: 'Navegar por seções' }));
    await activate(page.getByRole('button', { name: /Mercado e demanda/ }));
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
    await activate(page.getByRole('cell', { name: /Apartamento Jardim Paulista/ }).first());
    const close = page.getByRole('button', { name: 'Fechar detalhes do imóvel' });
    await withinViewport(close, page);
    await activate(close);
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
    const second = { ...estateRecord, id: 'review-second', title: 'Segundo imóvel de teste', asking_price: 1500000, area_m2: 120, rooms: 4 };
    await context.route('**/api/v1/analytics/estates*', route => route.fulfill({ json: { items: [estateRecord, second], page: { total: 2, offset: 0, limit: 100 } } }));
    await context.route('**/api/v1/analytics/estate-pair*', route => route.fulfill({ json: {
      a: estateRecord, b: second,
      metrics: [{ key: 'price', a_value: 1250000, b_value: 1500000, difference: 250000, unit: 'BRL' }],
      valuation_basis: 'stored_estimate',
    } }));
    await page.goto(origin + '/compare?a=review-estate&b=review-second');
    await page.getByRole('rowheader', { name: 'Preço de pedido', exact: true }).waitFor();
    assert.ok(await page.getByRole('row', { name: /Preço de pedido/ }).getByText('R$ 1.250.000', { exact: true }).isVisible());
    for (const label of ['Preço de pedido', 'Aquecimento', 'Liquidez', 'Alavancagem']) {
      assert.ok(await page.getByRole('rowheader', { name: label, exact: true }).isVisible(), `${label} remains available`);
    }
    assert.ok(await page.getByText('Diferenças disponíveis', { exact: true }).isVisible());
    assert.equal(await page.locator('.recharts-radar').count(), 0, 'no unsupported profile is plotted');
    assert.deepEqual(errors, [], 'selected comparison does not crash');
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'only the matrix scrolls horizontally');
    await activate(page.locator('#compare-b'));
    await activate(page.getByRole('option', { name: '— Remover seleção —' }));
    await page.getByText('Selecione dois imóveis para visualizar a comparação lado a lado.').waitFor();
  } finally { await context.close(); }
});

test('portfolio summary exposes all indicators and retains historical exploration', async () => {
  const { page, context } = await openPage('/portfolio');
  try {
    await page.locator('.portfolio-summary').waitFor();
    assert.ok(await page.locator('.portfolio-summary dt', { hasText: 'Valor estimado registrado' }).isVisible());
    assert.ok(await page.locator('.portfolio-summary dt', { hasText: 'Preço/m² mediano' }).isVisible());
    assert.ok(await page.locator('.portfolio-summary dt', { hasText: 'Liquidez prevista' }).isVisible());
    await activate(page.getByText('Referências de mercado por região', { exact: false }));
    assert.ok(await page.getByRole('columnheader', { name: 'Aquecimento', exact: true }).isVisible());
    assert.ok(await page.getByRole('cell', { name: '72/100', exact: true }).isVisible());
    await activate(page.getByText('Séries e indicadores', { exact: false }));
    assert.ok(await page.getByText('13 indicadores', { exact: false }).isVisible());
    await activate(page.locator('.portfolio-indicators .kpi-card').first().getByRole('button', { name: 'Ver série histórica: Valor total do portfólio' }));
    await page.getByRole('button', { name: 'Fechar série histórica' }).waitFor();
    await activate(page.getByRole('button', { name: 'Fechar série histórica' }));
    await page.locator('.kpi-morph-dialog').waitFor({ state: 'hidden' });
  } finally { await context.close(); }
});

test('market history remains visible when changing the display horizon', async () => {
  const { page, context } = await openPage('/overview');
  try {
    await activate(page.getByRole('button', { name: 'Navegar por seções' }));
    await activate(page.getByRole('button', { name: /Mercado e demanda/ }));
    await page.getByRole('button', { name: /Centro de comando/ }).waitFor({ state: 'hidden' });
    const chart = page.locator('#overview-market .recharts-area-curve').first();
    await page.waitForFunction(() => document.querySelector('#overview-market .recharts-area-curve')?.getBoundingClientRect().height > 1);
    assert.ok((await chart.getAttribute('d')).length > 20, 'real history produces a chart path');
    await activate(page.locator('#overview-market').getByRole('combobox').nth(1));
    await activate(page.getByRole('option', { name: '36 meses', exact: true }));
    await page.waitForFunction(() => document.querySelector('#overview-market .recharts-area-curve')?.getBoundingClientRect().height > 1);
    assert.ok(await page.locator('#overview-market').getByText('R$ 12.500', { exact: true }).first().isVisible());
  } finally { await context.close(); }
});

test('market map requests the selected published H3 resolution', async () => {
  const { page, context } = await openPage('/market-map');
  try {
    const request = page.waitForRequest((candidate) => {
      const url = new URL(candidate.url());
      return url.pathname.endsWith('/market/heatmap') && url.searchParams.get('h3_resolution') === '8';
    });
    await activate(page.getByRole('combobox', { name: 'Resolução H3', exact: true }));
    await activate(page.getByRole('option', { name: 'Regional · H3 8', exact: true }));
    await request;
    await page.getByText('Nenhuma célula H3 encontrada', { exact: true }).waitFor();
  } finally { await context.close(); }
});
