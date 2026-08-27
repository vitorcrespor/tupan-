import React, { useEffect, useRef, useState } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import { GoogleMapsOverlay } from '@deck.gl/google-maps';
import { PolygonLayer } from '@deck.gl/layers';
import { heatRgb } from '@/lib/format';

const SP_CENTER = { lat: -23.58, lng: -46.66 };

/**
 * Optional Deck.gl renderer for the same API-provided H3 cells used by the
 * Leaflet map. It receives already-calculated values and performs no fetching
 * or heat calculation itself.
 */
export default function Heatmap3D({ cells = [], onSelectCell, tilt = 55 }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const overlayRef = useRef(null);
  const [error, setError] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const key = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
        if (!key) throw new Error('A chave do Google Maps não está configurada.');
        const loader = new Loader({ apiKey: key, version: 'weekly' });
        const { Map } = await loader.importLibrary('maps');
        if (cancelled || !containerRef.current) return;
        mapRef.current = new Map(containerRef.current, {
          center: SP_CENTER,
          zoom: 12.4,
          tilt,
          heading: 18,
          mapId: import.meta.env.VITE_GOOGLE_MAPS_MAP_ID || undefined,
          disableDefaultUI: true,
          gestureHandling: 'greedy',
        });
        overlayRef.current = new GoogleMapsOverlay({ interleaved: true });
        overlayRef.current.setMap(mapRef.current);
        setReady(true);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'Não foi possível carregar o mapa 3D.');
      }
    })();
    return () => {
      cancelled = true;
      if (overlayRef.current) overlayRef.current.setMap(null);
    };
  }, [tilt]);

  useEffect(() => {
    if (!ready || !overlayRef.current) return;
    const layer = new PolygonLayer({
      id: 'h3-market-heat',
      data: cells,
      extruded: true,
      wireframe: true,
      filled: true,
      pickable: true,
      elevationScale: 14,
      // H3 API boundaries are [latitude, longitude]; deck.gl expects [lng, lat].
      getPolygon: (cell) => (cell.boundary || []).map(([latitude, longitude]) => [longitude, latitude]),
      getElevation: (cell) => cell.market_heat || 0,
      getFillColor: (cell) => [...heatRgb(cell.market_heat || 0), 190],
      getLineColor: [255, 255, 255, 210],
      getLineWidth: 12,
      material: { ambient: 0.55, diffuse: 0.7, shininess: 120, specularColor: [255, 255, 255] },
      onClick: ({ object }) => object && onSelectCell?.(object),
      updateTriggers: { getFillColor: [cells], getElevation: [cells], getPolygon: [cells] },
    });
    overlayRef.current.setProps({ layers: [layer] });
  }, [ready, cells, onSelectCell]);

  if (error) {
    return <div className="absolute inset-0 flex items-center justify-center text-xs text-text-secondary p-6 text-center">Mapa 3D indisponível: {error}</div>;
  }

  return <div ref={containerRef} className="absolute inset-0" />;
}
