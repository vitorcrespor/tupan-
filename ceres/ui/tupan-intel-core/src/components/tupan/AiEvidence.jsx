import React from 'react';

/** Supporting metadata is distinct from the answer and from factual analytics. */
export default function AiEvidence({response}) {
  const sources = response?.sources || [];
  const warnings = response?.warnings || [];
  const insights = response?.interpretation?.insights || [];
  if (!sources.length && !warnings.length && !insights.length) return null;
  return <div className="mt-2 text-xs text-text-secondary">
    {warnings.map((warning, index) => <p role="status" key={index} className="text-warning">{warning}</p>)}
    <details className="mt-1">
      <summary className="cursor-pointer">Fontes e ressalvas</summary>
      <ul className="mt-2 space-y-1">
        {sources.map((source, index) => <li key={index}>{source.label} · dados autorizados do backend</li>)}
        {insights.map((insight, index) => <li key={`insight-${index}`}>{insight.statement}{insight.caveat && <span> — {insight.caveat}</span>}</li>)}
      </ul>
    </details>
  </div>;
}
