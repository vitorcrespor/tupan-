import { useQuery } from '@tanstack/react-query';
import { useApp } from './AppContext';
import { getPortfolioAnalytics } from '@/api/portfolio';
import { liquidityHorizonDays } from '@/lib/tupanData';

export function usePortfolioAnalytics() {
  const { selectedPortfolioId, timePeriod } = useApp();
  const horizonDays = liquidityHorizonDays(timePeriod);
  return useQuery({
    queryKey: ['portfolio-analytics', selectedPortfolioId, horizonDays],
    queryFn: ({ signal }) => getPortfolioAnalytics({ portfolioId: selectedPortfolioId, liquidityHorizonDays: horizonDays, signal }),
    retry: false,
  });
}
