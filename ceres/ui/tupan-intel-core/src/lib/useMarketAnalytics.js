import {useQuery} from '@tanstack/react-query';
import {getPublishedMarketMetrics, publishedMetricHistory, metricHistoryToChartSeries} from '@/api/market';

/** One cached publication for all cards/charts in the same geographic scope.
 * @param {{city?:string,area?:string,h3Index?:string,liquidityHorizonDays?:number}} [scope]
 */
export function useMarketAnalytics({city,area,h3Index,liquidityHorizonDays} = {}) {
  const query = useQuery({
    queryKey:['published-market-metrics',city,area,h3Index,liquidityHorizonDays],
    queryFn:({signal}) => getPublishedMarketMetrics({city,area,h3Index,liquidityHorizonDays,signal}),
    staleTime:60_000, retry:false,
  });
  return {
    ...query,
    value:(metric) => query.data?.metrics.find(item => item.metric === metric)?.value ?? null,
    series:(metric) => metricHistoryToChartSeries(publishedMetricHistory(query.data,metric)),
  };
}
