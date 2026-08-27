// Maps each MarketRegion (commercial bairro) to the official São Paulo district
// whose boundary polygon is used for the choropleth. Several bairros share a
// district, so district metrics are averages of the regions inside them.
export const REGION_TO_DISTRICT = {
  Pinheiros: 'Pinheiros',
  'Vila Madalena': 'Pinheiros',
  Jardins: 'Jardim Paulista',
  'Cerqueira César': 'Jardim Paulista',
  'Itaim Bibi': 'Itaim Bibi',
  'Vila Olímpia': 'Itaim Bibi',
  Moema: 'Moema',
  Brooklin: 'Campo Belo',
  Santana: 'Santana',
  Tatuapé: 'Tatuapé',
};

const avg = (arr, key) => (arr.length ? arr.reduce((s, r) => s + (r[key] || 0), 0) / arr.length : 0);

// Joins boundary polygons with averaged region metrics.
export function buildDistrictHeat(boundaries, regions) {
  return boundaries
    .map((b) => {
      const members = regions.filter((r) => REGION_TO_DISTRICT[r.name] === b.name);
      if (!members.length) return null;
      return {
        name: b.name,
        polygon: b.polygon,
        center: [b.center_lng, b.center_lat],
        members,
        market_heat: Math.round(avg(members, 'market_heat')),
        avg_price_per_m2: Math.round(avg(members, 'avg_price_per_m2')),
        price_growth: Number(avg(members, 'price_growth').toFixed(1)),
        avg_dom: Math.round(avg(members, 'avg_dom')),
        inventory: Math.round(members.reduce((s, r) => s + (r.inventory || 0), 0)),
        listing_count: Math.round(members.reduce((s, r) => s + (r.listing_count || 0), 0)),
      };
    })
    .filter(Boolean);
}