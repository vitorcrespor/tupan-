import React, { useMemo } from 'react';
import { MapContainer, TileLayer, Polygon, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { heatColor, heatLabel } from '@/lib/format';

// São Paulo center (lat, lng — Leaflet order)
const SP_CENTER = [-23.578, -46.672];

// H3 choropleth over a clean, key-free CARTO basemap. Coordinates arrive from
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
        center={SP_CENTER}
        zoom={12}
        zoomSnap={0.25}
        scrollWheelZoom
        zoomControl={false}
        preferCanvas
        className="h-full w-full"
        style={{ background: 'hsl(190 44% 95%)' }}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution="&copy; OpenStreetMap &copy; CARTO"
          maxZoom={20}
        />
        {polys.map((d) => (
          <Polygon
            key={d.h3_index}
            positions={d.positions}
            pathOptions={{
              color: '#ffffff',
              weight: 1.4,
              fillColor: heatColor(d.market_heat),
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
                <div style={{ color: heatColor(d.market_heat ?? 0) }}>
                  Aquecimento {d.market_heat == null ? '—' : `${d.market_heat.toFixed(0)}/100`} · {d.market_heat == null ? 'Indisponível' : heatLabel(d.market_heat)}
                </div>
              </div>
            </Tooltip>
          </Polygon>
        ))}
      </MapContainer>
    </div>
  );
}
