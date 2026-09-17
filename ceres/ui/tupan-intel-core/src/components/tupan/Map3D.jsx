import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polygon, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { heatColor, heatLabel } from '@/lib/format';

function FitPublishedCells({ cells }) {
  const map = useMap();
  useEffect(() => {
    const points = cells.flatMap((cell) => cell.boundary || []);
    if (points.length) map.fitBounds(points, {padding:[36,36], maxZoom:14});
  }, [map, cells]);
  return null;
}

// São Paulo center (lat, lng — Leaflet order)
/** @type {[number, number]} */
const SP_CENTER = [-23.578, -46.672];

// H3 choropleth over the public OSM basemap. Coordinates arrive from
// the API as [latitude, longitude] tuples, matching Leaflet's Polygon input.
export default function Map3D({ cells, tilt: _tilt, elevation: _elevation, onSelect, onHover }) {
  const polys = useMemo(
    () =>
      (cells || []).map((cell) => ({
        ...cell,
        positions: cell.boundary || [],
      })),
    [cells]
  );

  return (
    <div className="absolute inset-0">
      <MapContainer
        center={cells[0]?.center || SP_CENTER}
        zoom={12}
        zoomSnap={0.25}
        scrollWheelZoom
        zoomControl={false}
        preferCanvas
        className="h-full w-full"
        style={{ background: 'hsl(190 44% 95%)' }}
      >
        <FitPublishedCells cells={cells} />
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          maxZoom={19}
        />
        {polys.map((d) => (
          <Polygon
            key={d.h3_index}
            positions={d.positions}
            pathOptions={{
              color: '#ffffff',
              weight: 1.4,
              fillColor: d.market_heat == null ? '#81949e' : heatColor(d.market_heat),
              fillOpacity: 0.42,
            }}
            eventHandlers={{
              mouseover: () => onHover && onHover(d),
              mouseout: () => onHover && onHover(null),
              click: () => onSelect && onSelect(d),
            }}
          >
            <Tooltip sticky direction="top">
              <div className="text-[11px] leading-tight">
                <div className="font-semibold text-foreground">{d.label}</div>
                {d.dataset_kind === 'transactions' ? <div>{d.transaction_count} transações ITBI · amostra</div> : <div style={{ color: heatColor(d.market_heat ?? 0) }}>
                  Aquecimento {d.market_heat == null ? '—' : `${d.market_heat.toFixed(0)}/100`} · {d.market_heat == null ? 'Indisponível' : heatLabel(d.market_heat)}
                </div>}
              </div>
            </Tooltip>
          </Polygon>
        ))}
      </MapContainer>
    </div>
  );
}
