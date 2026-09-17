import { useEffect, useState } from 'react';
import { getProperties } from '@/api/properties';
import { getMarketCells } from '@/api/market';
import { useApp } from '@/lib/AppContext';
import { liquidityHorizonDays as liquidityHorizonForPeriod } from '@/lib/tupanData';

function marketCellToRegion(cell) {
  const [latitude, longitude] = Array.isArray(cell?.center) ? cell.center : [];
  return {
    id: cell.id,
    name: cell.neighborhood || cell.label,
    city: cell.city || '—',
    latitude,
    longitude,
    avg_price_per_m2: cell.average_price_m2,
    average_price_per_m2: cell.average_price_m2,
    market_heat: cell.market_heat,
    liquidity: cell.liquidity,
    liquidity_details: cell.liquidity_details,
    inventory: cell.inventory,
    avg_dom: cell.average_dom_days,
    price_growth: cell.price_growth_pct,
    sales_velocity: cell.sales_velocity,
  };
}

/**
 * Read tenant estates and published market cells in one explicit geography.
 * The two sources remain separate: estates are tenant-owned, while cells are
 * platform aggregates.  Passing no city deliberately means the published
 * global scope; it must not silently become Sao Paulo.
 *
 * @param {{city?: string, h3Resolution?: number}} [scope]
 */
export function useTupanData({ city, h3Resolution = 9 } = {}) {
  const { timePeriod } = useApp();
  const liquidityHorizonDays = liquidityHorizonForPeriod(timePeriod);
  const [properties, setProperties] = useState([]);
  const [regions, setRegions] = useState([]);
  const [propertiesStatus, setPropertiesStatus] = useState('idle');
  const [regionsStatus, setRegionsStatus] = useState('idle');
  const [propertiesError, setPropertiesError] = useState(null);
  const [regionsError, setRegionsError] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setPropertiesStatus('loading');
        setRegionsStatus('loading');
        const [propertyResult, regionResult] = await Promise.allSettled([
          getProperties({ city, liquidity_horizon_days: liquidityHorizonDays }),
          getMarketCells({ city, h3Resolution, liquidityHorizonDays }),
        ]);
        if (!alive) return;
        if (propertyResult.status === 'fulfilled') {
          setProperties(Array.isArray(propertyResult.value.items) ? propertyResult.value.items : []);
          setPropertiesError(null);
          setPropertiesStatus('success');
        } else {
          setPropertiesError(propertyResult.reason);
          setPropertiesStatus('error');
        }
        if (regionResult.status === 'fulfilled') {
          const cells = Array.isArray(regionResult.value.cells) ? regionResult.value.cells : [];
          setRegions(cells.filter(Boolean).map(marketCellToRegion));
          setRegionsError(null);
          setRegionsStatus('success');
        } else {
          setRegionsError(regionResult.reason);
          setRegionsStatus('error');
        }
      } catch (error) {
        if (!alive) return;
        setPropertiesError(error);
        setRegionsError(error);
        setPropertiesStatus('error');
        setRegionsStatus('error');
      }
    })();
    return () => {
      alive = false;
    };
  }, [city, h3Resolution, liquidityHorizonDays]);

  return {
    properties,
    regions,
    loading: propertiesStatus === 'loading' || regionsStatus === 'loading',
    propertiesStatus,
    regionsStatus,
    propertiesError,
    regionsError,
  };
}
