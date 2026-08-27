// Fallback neighborhood areas.
// Real bairro polygons (GeoSampa / IBGE GeoJSON) can be dropped in later —
// this generates a stable, organic pseudo-boundary around each region centroid
// so the choropleth + 3D extrusion can be previewed without extra API calls.

const seeded = (seed) => {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
};

const hash = (str) => {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) % 233280;
  return h || 7;
};

/** Organic blob polygon around a centroid, in [lng, lat] pairs. */
export function fallbackNeighborhoodPolygon(region, sizeKm = 1.5) {
  const rand = seeded(hash(region.name));
  const steps = 14;
  const latDeg = sizeKm / 111;
  const lngDeg = sizeKm / (111 * Math.cos((region.latitude * Math.PI) / 180));
  const ring = [];
  for (let i = 0; i < steps; i++) {
    const angle = (i / steps) * Math.PI * 2;
    const wobble = 0.72 + rand() * 0.55;
    ring.push([
      region.longitude + Math.cos(angle) * lngDeg * wobble,
      region.latitude + Math.sin(angle) * latDeg * wobble,
    ]);
  }
  ring.push(ring[0]);
  return ring;
}

export function buildNeighborhoodAreas(regions = []) {
  return regions.map((r) => ({
    ...r,
    polygon: fallbackNeighborhoodPolygon(r, 1.1 + (r.inventory || 100) / 220),
  }));
}
