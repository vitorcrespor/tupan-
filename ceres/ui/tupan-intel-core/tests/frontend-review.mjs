// Isolated visual review of the real routes. Never contacts the production API.
// Run with the same PLAYWRIGHT_MODULE / PLAYWRIGHT_CHANNEL as the browser tests.
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from 'vite';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
export const estate = {
  id: 'review-estate', kind: 'APARTMENT', summary: 'Imóvel de teste visual, sem dados de clientes.',
  location: { address: 'Apartamento Jardim Paulista', city: 'São Paulo', area: 'Jardim Paulista' },
  pricing: { asking_price: 1250000 }, metrics: { area_m2: 100, rooms: 3, bathrooms: 2, price_per_m2: 12500 },
  predictions: { suggested_price: 1200000 }, dom_days: 42,
};
export const portfolio = {
  portfolio_value: 1250000, active_listing_count: 1, sold_listing_count: 0,
  average_asking_price: 1250000, median_asking_price: 1250000,
  average_price_per_m2: 12500, average_dom_days: 42, average_listing_age_days: 50,
  average_price_gap: 0.0417, regional_concentration: [{ region: 'Jardim Paulista', share: 1, portfolio_value: 1250000 }],
  property_type_mix: [{ kind: 'APARTMENT', property_count: 1 }],
  regional_performance: [], above_estimate: [], below_estimate: [],
};
export async function mockApi(context) {
  await context.route('**/api/v1/**', route => {
    const path = new URL(route.request().url()).pathname.replace('/api/v1', '');
    let body;
    if (path === '/auth/session') body = { user: { id: 'review-user', full_name: 'Equipe Ceres', email: 'review@example.test', role: 'admin' } };
    else if (path === '/properties' || path === '/properties/search') body = { items: [estate], page: { total: 1, offset: 0, limit: 100 } };
    else if (path === '/properties/review-estate') body = estate;
    else if (path === '/portfolio/analytics') body = portfolio;
    else if (path === '/market/cells') body = { cells: [], source: {}, filters: {} };
    else if (/^\/metrics\/.+\/history$/.test(path)) body = { metric: 'price_m2', unit: 'BRL', points: [
      { period: '2026-06-01', value: 11800 }, { period: '2026-07-01', value: 12000 }, { period: '2026-08-01', value: 12500 },
    ] };
    else if (path.startsWith('/workspace/')) body = [];
    else return route.fulfill({ status: 503, json: { code: 'dependency_unavailable', message: 'Serviço indisponível neste cenário de teste visual.' } });
    return route.fulfill({ json: body });
  });
}

export async function startReview() {
  const server = await createServer({
    cacheDir: 'node_modules/.vite-frontend-review',
    server: { host: '127.0.0.1', port: 0, strictPort: false, open: false },
    define: {
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify('/api/v1'),
      'import.meta.env.VITE_TUPAN_API_URL': JSON.stringify('/api/v1'),
    },
  });
  await server.listen();
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
  return { server, browser, origin: `http://127.0.0.1:${server.httpServer.address().port}` };
}

// Importable by regression tests without automatically capturing screenshots.
if (process.argv[1]?.replaceAll('\\', '/').endsWith('/frontend-review.mjs')) {
  const directory = join(tmpdir(), `ceres-frontend-${process.env.REVIEW_STAGE || 'before'}`);
  await mkdir(directory, { recursive: true });
  const { server, browser, origin } = await startReview();
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  await mockApi(context);
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    const routes = ['overview', 'portfolio', 'properties', 'properties/review-estate', 'market-trends', 'compare', 'market-map', 'settings', 'data', 'saved-searches', 'report-builder', 'team-management', 'agent-log', 'agent'];
    for (const route of routes) {
      const startErrors = errors.length;
      await page.goto(`${origin}/${route}`, { waitUntil: 'networkidle', timeout: 90000 });
      await page.locator(route === 'agent' ? '.voice-theme-gradient' : 'header h1').first().waitFor();
      await page.locator('.app-route-loading').waitFor({ state: 'hidden' });
      if (route === 'portfolio') await page.waitForTimeout(1600); // Let the existing counter finish.
      await page.screenshot({ path: join(directory, `${route.replaceAll('/', '-')}.png`) });
      console.log(JSON.stringify({ route, errors: errors.slice(startErrors), layout: await page.evaluate(() => ({
        width: innerWidth, documentWidth: document.documentElement.scrollWidth,
        headings: [...document.querySelectorAll('h1,h2,h3')].slice(0, 12).map(el => ({ text: el.textContent, size: getComputedStyle(el).fontSize })),
      })) }));
    }
    // Review the content behind the section navigator and both existing color modes.
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 800 });
      await page.goto(origin + '/overview', { waitUntil: 'networkidle' });
      await page.getByRole('button', { name: 'Navegar por seções' }).click();
      await page.getByRole('button', { name: /Mercado e demanda/ }).click();
      await page.getByRole('heading', { name: 'Tendências de mercado', exact: true }).waitFor();
      await page.getByRole('button', { name: /Centro de comando/ }).waitFor({ state: 'hidden' });
      await page.waitForFunction(() => document.querySelector('#overview-market .recharts-area-curve')?.getBoundingClientRect().height > 1);
      await page.screenshot({ path: join(directory, 'overview-market-' + width + '.png') });
    }
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(origin + '/compare?a=review-estate&b=review-estate', { waitUntil: 'networkidle' });
    await page.screenshot({ path: join(directory, 'compare-selected.png') });
    await page.goto(origin + '/overview', { waitUntil: 'networkidle' });
    await page.evaluate(async () => {
      const { THEMES, applyTheme } = await import('/src/lib/themes.js');
      const light = THEMES.find(theme => !theme.dark);
      if (light) applyTheme(light.id);
    });
    await page.screenshot({ path: join(directory, 'overview-light.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    for (const route of ['overview', 'settings', 'market-trends', 'properties', 'compare', 'report-builder', 'agent-log']) {
      await page.goto(`${origin}/${route}`, { waitUntil: 'networkidle', timeout: 90000 });
      await page.screenshot({ path: join(directory, `${route}-mobile.png`) });
    }
    // Public login stays unauthenticated, with no real session or credentials.
    await context.unroute('**/api/v1/**');
    await context.route('**/api/v1/**', route => route.fulfill({ status: 401, json: {} }));
    await page.goto(`${origin}/login`, { waitUntil: 'networkidle', timeout: 90000 });
    await page.screenshot({ path: join(directory, 'login-mobile.png') });
    console.log('Screenshots: ' + directory);
  } finally { await browser.close(); await server.close(); }
}
