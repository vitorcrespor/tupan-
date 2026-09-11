export default function RouteLoading() {
  return (
    <div role="status" aria-live="polite" className="app-route-loading flex items-center justify-center p-6 text-sm text-text-muted">
      <span className="surface-control inline-flex items-center gap-3 rounded-full px-4 py-2">
        <span aria-hidden="true" className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-border border-t-brand motion-reduce:animate-none" />
        Carregando área de trabalho…
      </span>
    </div>
  );
}
