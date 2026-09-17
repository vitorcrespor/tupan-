import React from 'react';

/** @param {{provenance?:import('@/api/properties').EstateResponse['estimate_provenance']}} props */
export default function EstimateProvenance({ provenance }) {
  if (!provenance) return <small className="block text-text-muted">Origem e data da estimativa não registradas.</small>;
  return <details className="text-xs text-text-secondary">
    <summary>{provenance.status === 'inputs_changed' ? 'Dados alterados após a estimativa · revisar' : 'Origem da estimativa registrada'}</summary>
    <p>Origem: {provenance.source === 'recorded' ? 'Valor informado no cadastro' : provenance.source}.</p>
    <p>Registrada em {new Date(provenance.recorded_at).toLocaleString('pt-BR')}.</p>
    <p>Modelo: {provenance.model_version || 'Não identificado'}.</p>
    <p className="break-all">Versão dos dados: {provenance.input_version}.</p>
  </details>;
}
