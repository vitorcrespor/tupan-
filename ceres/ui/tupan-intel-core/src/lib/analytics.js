export const computePortfolioStats = (properties, regions) => {
  const active = (properties || []).filter((p) => p.status === 'Active');
  const totalValue = active.reduce((s, p) => s + (p.price || 0), 0);
  const avgPrice = active.length ? totalValue / active.length : 0;
  const prices = active.map((p) => p.price || 0).sort((a, b) => a - b);
  const median = prices.length ? prices[Math.floor(prices.length / 2)] : 0;
  const avgM2 = active.length ? active.reduce((s, p) => s + (p.price_per_m2 || 0), 0) / active.length : 0;
  const avgDom = active.length ? active.reduce((s, p) => s + (p.days_on_market || 0), 0) / active.length : 0;
  const avgDeviation = active.length ? active.reduce((s, p) => s + (p.price_deviation || 0), 0) / active.length : 0;
  const avgConfidence = active.length ? active.reduce((s, p) => s + (p.valuation_confidence || 0), 0) / active.length : 0;
  const overpriced = active.filter((p) => p.valuation_class === 'ABOVE_ESTIMATED_RANGE');
  const underpriced = active.filter((p) => p.valuation_class === 'BELOW_ESTIMATED_RANGE');
  const fair = active.filter((p) => p.valuation_class === 'WITHIN_ESTIMATED_RANGE');
  const avgLiquidity = active.length ? active.reduce((s, p) => s + (p.liquidity_score || 0), 0) / active.length : 0;

  const byRegion = {};
  active.forEach((p) => {
    byRegion[p.neighborhood] = (byRegion[p.neighborhood] || 0) + (p.price || 0);
  });
  const concentration = Object.entries(byRegion)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value, pct: totalValue ? (value / totalValue) * 100 : 0 }));
  const topConcentration = concentration.slice(0, 2).reduce((s, c) => s + c.pct, 0);

  const byType = {};
  active.forEach((p) => {
    byType[p.property_type] = (byType[p.property_type] || 0) + 1;
  });
  const typeDist = Object.entries(byType).map(([name, count]) => ({ name, count }));

  const listingAge = active.length ? active.reduce((s, p) => s + (p.days_on_market || 0), 0) / active.length : 0;

  return {
    totalValue,
    activeCount: active.length,
    avgPrice,
    median,
    avgM2,
    avgDom,
    avgDeviation,
    avgConfidence,
    overpriced,
    underpriced,
    fair,
    avgLiquidity,
    concentration,
    topConcentration,
    typeDist,
    listingAge,
  };
};

export const computeMarketStats = (regions) => {
  const r = regions || [];
  if (!r.length) return { medianM2: 0, avgHeat: 0, avgDom: 0, totalInventory: 0, avgGrowth: 0, avgVelocity: 0 };
  const m2 = r.map((x) => x.avg_price_per_m2 || 0).sort((a, b) => a - b);
  const medianM2 = m2[Math.floor(m2.length / 2)] || 0;
  const avgHeat = r.reduce((s, x) => s + (x.market_heat || 0), 0) / r.length;
  const avgDom = r.reduce((s, x) => s + (x.avg_dom || 0), 0) / r.length;
  const totalInventory = r.reduce((s, x) => s + (x.inventory || 0), 0);
  const avgGrowth = r.reduce((s, x) => s + (x.price_growth || 0), 0) / r.length;
  const avgVelocity = r.reduce((s, x) => s + (x.sales_velocity || 0), 0) / r.length;
  return { medianM2, avgHeat, avgDom, totalInventory, avgGrowth, avgVelocity };
};

export const regionByName = (regions, name) => (regions || []).find((r) => r.name === name);
