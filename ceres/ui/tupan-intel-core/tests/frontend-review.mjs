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
export const estateRecord = {
  id: estate.id, portfolio_id: 'portfolio-review', title: estate.location.address,
  summary: estate.summary, property_type: 'apartment', status: 'active',
  asking_price: estate.pricing.asking_price, estimated_price: estate.predictions.suggested_price,
  area_m2: estate.metrics.area_m2, price_per_m2: estate.metrics.price_per_m2,
  rooms: estate.metrics.rooms, bathrooms: estate.metrics.bathrooms, parking_spaces: 1,
  age_years: 8, days_on_market: estate.dom_days, city: estate.location.city, area: estate.location.area,
  address: estate.location.address, attributes: {}, source_name: 'fixture',
};
const analysis = {
  estate: estateRecord,
  valuation: {
    listed_price: 1250000, estimated_price: 1200000, difference: 50000,
    difference_percent: 4.1667, price_per_m2: 12500, estimated_price_per_m2: 12000, inference_ms: 5,
  },
  comparables: [{ ...estateRecord, id: 'review-peer', title: 'Comparável Jardim Paulista', asking_price: 1180000, distance_meters: 480 }],
  local_statistics: { comparable_count: 1, average_asking_price: 1180000, median_asking_price: 1180000, average_price_per_m2: 11800, median_price_per_m2: 11800, average_days_on_market: 38 },
  market_context: [], location_metrics: null,
  timing: { total_ms: 20, components: [{ name: 'avm', state: 'success', duration_ms: 5, code: null, message: null }] },
};
const portfolioResponse = {
  portfolio: { id: 'portfolio-review', name: 'Portfólio de revisão', description: null },
  valuation_summary: { active_estate_count: 1, portfolio_value: 1250000, estimated_value: 1200000, average_price_gap: 0.0417 },
  geographic_concentration: [{ city: 'São Paulo', area: 'Jardim Paulista', estate_count: 1, portfolio_value: 1250000, share: 1 }],
  pricing_statistics: { average_asking_price: 1250000, median_asking_price: 1250000, average_price_per_m2: 12500, median_price_per_m2: 12500, average_days_on_market: 42 },
  property_distribution: [{ property_type: 'apartment', estate_count: 1, share: 1 }],
  market_exposure: [{ city: 'São Paulo', area: 'Jardim Paulista', estate_count: 1, average_price_m2: 12500, market_heat: 72, latest_observed_on: '2026-08-01' }], positions: { above_count: 1, below_count: 0, equal_count: 0, missing_count: 0, asking_count: 1, estimated_count: 1, rows: [{ property_id: estate.id, title: estateRecord.title, region: estateRecord.area, asking_price: 1250000, estimated_price: 1200000, price_gap: 0.0417, difference: 50000 }] },
  top_region_share: 1, timing: { total_ms: 20, components: [] },
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
    else if (path === '/portfolios') body = [{ id: 'portfolio-review', name: 'Portfólio de revisão', description: null }];
    else if (path === '/analytics/estates') body = { items: [estateRecord], page: { total: 1, offset: 0, limit: 100 } };
    else if (path === '/analytics/report-summary') body = {
      scope: { city: 'São Paulo', area: null, active_only: true },
      summary: { active_estate_count: 1, asking_price_count: 1, price_per_m2_count: 1, days_on_market_count: 1, average_asking_price: 1250000, average_price_per_m2: 12500, average_days_on_market: 42 },
      featured_estates: [{ id: estateRecord.id, title: estateRecord.title, city: estateRecord.city, area: estateRecord.area, asking_price: estateRecord.asking_price, price_per_m2: estateRecord.price_per_m2, days_on_market: estateRecord.days_on_market, updated_at: '2026-09-14T00:00:00+00:00' }],
      market_metrics: [{ metric: 'sales_velocity', unit: 'sales/day', value: 1.25, observed_on: '2026-09-01', source_name: 'Contract fixture', status: 'available', reason: null }],
      timing: { total_ms: 1, components: [] },
    };
    else if (path === '/estates/review-estate/analysis') body = analysis;
    else if (path === '/estates/review-estate') body = estateRecord;
    else if (path === '/portfolios/portfolio-review/overview') body = portfolioResponse;
    else if (path === '/analytics/estate-pair') body = { a: estateRecord, b: estateRecord, metrics: [], valuation_basis: 'stored_estimate' };
    else if (path === '/market/heatmap') body = { cells: [], source: { kind: 'LIVE' }, filters: {} };
    else if (path === '/market/published-metrics') body = {scope:'platform',city:'São Paulo',area:null,h3_index:null,aggregation:'published',metrics:[
      {metric:'price_m2',unit:'BRL/m²',value:12500,observed_on:'2026-08-01',source_name:'Contract fixture',status:'available',reason:null,points:[{period:'2026-06-01',value:11800},{period:'2026-07-01',value:12000},{period:'2026-08-01',value:12500}]},
      {metric:'market_heat',unit:'score_0_100',value:72,observed_on:'2026-08-01',source_name:'Contract fixture',status:'available',reason:null,points:[{period:'2026-06-01',value:68},{period:'2026-07-01',value:70},{period:'2026-08-01',value:72}]},
      {metric:'active_listings',unit:'count',value:42,observed_on:'2026-08-01',source_name:'Contract fixture',status:'available',reason:null,points:[{period:'2026-06-01',value:30},{period:'2026-07-01',value:40},{period:'2026-08-01',value:42}]},
    ]};
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
  await server.warmupRequest('/src/main.jsx');
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.PLAYWRIGHT_CHANNEL,
    args: [
      '--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows',
      '--disable-renderer-backgrounding',
    ],
  });
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
