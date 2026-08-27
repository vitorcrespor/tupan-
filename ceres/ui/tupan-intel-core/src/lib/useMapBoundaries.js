import { useEffect, useState } from 'react';
import { appClient } from '@/demo/localAppClient';

// Loads the Google Maps browser key and the district boundary polygons.
export function useMapBoundaries() {
  const [apiKey, setApiKey] = useState(null);
  const [boundaries, setBoundaries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [cfg, bounds] = await Promise.all([
          appClient.functions.invoke('getMapsConfig', {}),
          appClient.entities.DistrictBoundary.list('name', 100),
        ]);
        if (!alive) return;
        setApiKey(cfg.data?.apiKey || null);
        setBoundaries(bounds || []);
      } catch (e) {
        if (alive) setError(e.message || 'Map failed to load');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return { apiKey, boundaries, loading, error };
}
