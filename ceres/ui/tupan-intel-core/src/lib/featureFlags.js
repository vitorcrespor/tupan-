// Deployment-controlled UI capabilities. Set VITE_ENABLE_CHART_EXPANSION=true
// to enable chart expansion interactions in the intelligence workspaces.
export const enableChartExpansion = import.meta.env.VITE_ENABLE_CHART_EXPANSION !== 'false';
