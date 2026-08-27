-- Seed a couple of regions and properties for quick testing
INSERT INTO market_regions (id, name, city, average_price_per_m2, market_heat, demand_score, liquidity_score)
VALUES ('region-1', 'Pinheiros', 'São Paulo', 9800, 60, 58, 50)
ON CONFLICT (id) DO NOTHING;

INSERT INTO properties (id, title, address, city, neighborhood, latitude, longitude, price, price_per_m2)
VALUES ('property-1', 'Apartamento Pinheiros', 'Rua Pinheiros, 100', 'São Paulo', 'Pinheiros', -23.55, -46.62, 800000, 10000)
ON CONFLICT (id) DO NOTHING;

-- example user
INSERT INTO users (id, full_name, email, role)
VALUES ('user-1', 'Test User', 'test@example.com', 'admin')
ON CONFLICT (id) DO NOTHING;

-- example saved search
INSERT INTO saved_searches (id, user_id, name, filters)
VALUES ('search-1', 'user-1', 'My Search', '{"city":"São Paulo","neighborhood":"Pinheiros"}'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- example district
INSERT INTO district_boundaries (id, name, geojson)
VALUES ('district-1', 'Pinheiros Area', '{"type":"FeatureCollection","features":[]}'::jsonb)
ON CONFLICT (id) DO NOTHING;
