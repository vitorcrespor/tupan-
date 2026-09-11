import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import useOutsideDismiss from '@/lib/useOutsideDismiss';

export default function SectionNav({ sections, activeId, onSelect, className, scrollContainerRef }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [railHovered, setRailHovered] = useState(false);
  const ref = useRef(null);
  const collapseThresholdRef = useRef(0);

  useOutsideDismiss(ref, open, () => setOpen(false));


  useEffect(() => {
    const scrollContainer = scrollContainerRef?.current;
    const nav = ref.current;
    if (!scrollContainer || !nav) return undefined;

    let frame = 0;
    const measureCollapseThreshold = () => {
      // Preserve the full pill while it occupies its natural document space.
      // It only becomes the rail after its natural bottom would leave the viewport.
      collapseThresholdRef.current = Math.max(0, nav.offsetTop + nav.offsetHeight);
    };
    const updateScrollState = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        setScrolled(scrollContainer.scrollTop >= collapseThresholdRef.current);
      });
    };
    const handleResize = () => {
      measureCollapseThreshold();
      updateScrollState();
    };

    measureCollapseThreshold();
    updateScrollState();
    scrollContainer.addEventListener('scroll', updateScrollState, { passive: true });
    window.addEventListener('resize', handleResize);
    return () => {
      cancelAnimationFrame(frame);
      scrollContainer.removeEventListener('scroll', updateScrollState);
      window.removeEventListener('resize', handleResize);
    };
  }, [scrollContainerRef]);

  const chooseSection = (id) => {
    onSelect?.(id);
    setOpen(false);
  };

  const activeSection = sections.find((section) => section.id === activeId);
  const compact = scrolled && !open && !railHovered;

  return (
    <section
      ref={ref}
      className={cn('mx-auto flex w-full max-w-[1320px] flex-col items-center', className)}
      aria-label="Navegação da visão geral"
      onFocusCapture={() => setRailHovered(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setRailHovered(false);
      }}
    >
      <button
        type="button"
        aria-label="Navegar por seções"
        title={compact ? 'Passe o cursor ou pressione para expandir as seções' : 'Navegar por seções'}
        aria-expanded={open}
        aria-controls="overview-section-menu"
        onClick={() => setOpen((value) => !value)}
        onMouseEnter={() => setRailHovered(true)}
        onMouseLeave={() => setRailHovered(false)}
        className={cn(
          'relative flex h-8 w-24 items-center justify-center rounded-full border text-text-secondary transition-[border-color,background-color,color,box-shadow] duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/55',
          compact ? 'border-transparent bg-transparent' : 'gap-1.5 border-border/70 bg-card/25 px-3 backdrop-blur-md hover:border-brand/50 hover:text-foreground',
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            'absolute h-1 rounded-full bg-text-muted/65 transition-all duration-200 ease-out',
            compact ? 'w-12 opacity-100' : 'w-5 opacity-0',
          )}
        />
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full transition-all duration-200 ease-out',
            compact ? 'scale-75 opacity-0' : 'scale-100 opacity-100',
          )}
          style={{ background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%))', boxShadow: '0 0 6px -1px hsl(188 82% 52% / 0.6)' }}
        />
        <span className={cn('font-mono text-[10px] uppercase tracking-[0.2em] transition-all duration-200 ease-out', compact ? 'translate-y-0.5 scale-95 opacity-0' : 'translate-y-0 scale-100 opacity-100')}>Seções</span>
      </button>
      <p className="sr-only" aria-live="polite">Seção ativa: {activeSection?.label || 'Visão geral'}</p>

      <div
        className="grid w-full"
        style={{
          gridTemplateRows: open ? '1fr' : '0fr',
          transition: 'grid-template-rows 0.42s cubic-bezier(0.22,1,0.36,1)',
        }}
      >
        <div className="min-h-0 overflow-hidden">
          <nav
            id="overview-section-menu"
            aria-label="Seções da visão geral"
            aria-hidden={!open}
            className="mx-auto mt-3 w-full max-w-3xl rounded-2xl border border-border/70 bg-card/55 p-2 shadow-soft-lg backdrop-blur-md"
            style={{
              opacity: open ? 1 : 0,
              transform: open ? 'translateY(0) scale(1)' : 'translateY(-8px) scale(0.975)',
              transformOrigin: 'center top',
              transition: 'opacity 0.3s ease 0.08s, transform 0.36s cubic-bezier(0.22,1,0.36,1)',
            }}
          >
            <p className="px-3 pb-1 pt-2 font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Navegar por seções</p>
            <ul className="grid list-none grid-cols-1 gap-0.5 p-0 sm:grid-cols-2 lg:grid-cols-3">
              {sections.map(({ id, label, detail }, index) => {
                const active = id === activeId;
                return (
                  <li key={id}>
                    <button
                      type="button"
                      tabIndex={open ? 0 : -1}
                      aria-current={active ? 'page' : undefined}
                      onClick={() => chooseSection(id)}
                      className={cn(
                        'flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-[13px] transition-colors',
                        active ? 'bg-brand/10 font-semibold text-foreground' : 'text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground',
                      )}
                    >
                      <span className="w-5 font-mono text-[10px] text-text-muted">{String(index + 1).padStart(2, '0')}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate">{label}</span>
                        {detail && <span className="block truncate text-[11px] font-normal text-text-muted">{detail}</span>}
                      </span>
                      <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', active ? 'bg-brand' : 'bg-foreground/20')} />
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
        </div>
      </div>
    </section>
  );
}