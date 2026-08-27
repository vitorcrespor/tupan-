import { LayoutDashboard, Building2 } from 'lucide-react';

// Single source of truth for the app's primary navigation groups.
// Used by both VoiceNav (collapsible) and MenuWindow (home/voice modal)
// so they always stay in sync.
export const NAV_GROUPS = [
  {
    title: 'Espaço de trabalho',
    icon: LayoutDashboard,
    items: [
      { label: 'Visão Geral', to: '/overview' },
      { label: 'Mapa de mercado', to: '/market-map' },
      { label: 'Análise de imóveis', to: '/market-trends' },
    ],
  },
  {
    title: 'Imóveis',
    icon: Building2,
    items: [
      { label: 'Portfólio', to: '/portfolio' },
      { label: 'Imóveis', to: '/properties' },
      { label: 'Comparar imóveis', to: '/compare' },
      { label: 'Buscas salvas', to: '/saved-searches' },
    ],
  },

];

