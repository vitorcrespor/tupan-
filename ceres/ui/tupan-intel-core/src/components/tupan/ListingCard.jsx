import React, { useState, useEffect, useRef } from 'react';
import { Star, Plus, Check, Loader2 } from 'lucide-react';
import { Image } from '@/components/ui/image';
import { formatBRLCompact, formatM2, heatLabel } from '@/lib/format';
import PropertyNotes from '@/components/tupan/PropertyNotes';
import { propertyTypeLabel, valuationLabel } from '@/lib/labels';

const PHOTOS = [
  'https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1200&q=80',
];

export default function ListingCard({ property, onAdd, onClick = undefined, photos = PHOTOS }) {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [state, setState] = useState('idle'); // idle | loading | added
  const timer = useRef(null);

  useEffect(() => {
    if (!open || state === 'added' || photos.length < 2) return;
    const id = setInterval(() => setIndex((i) => (i + 1) % photos.length), 2200);
    return () => clearInterval(id);
  }, [open, state, photos.length]);

  useEffect(() => () => clearTimeout(timer.current), []);

  const handleAdd = (e) => {
    e.stopPropagation();
    if (state === 'loading') return;
    if (state === 'added') {
      setState('idle');
      return;
    }
    setState('loading');
    timer.current = setTimeout(() => {
      setState('added');
      onAdd?.(property);
    }, 750);
  };

  const was = property.suggested_price && property.suggested_price !== property.price ? property.suggested_price : null;

  return (
    <div
      role="group"
      tabIndex={0}
      aria-label={`${property.title} — ${formatBRLCompact(property.price)}`}
      onClick={() => onClick?.(property)}
      onKeyDown={(event) => { if ((event.key === 'Enter' || event.key === ' ') && onClick) { event.preventDefault(); onClick(property); } }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => { setOpen(false); setIndex(0); }}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      className="group relative w-full cursor-pointer overflow-hidden rounded-xl border border-border bg-card/60 outline-none transition-colors duration-200 hover:border-brand/40 focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="relative w-full overflow-hidden aspect-[3/2]">
        <div
          className="flex h-full w-full transition-transform ease-out"
          style={{ transitionDuration: '850ms', transform: `translateX(-${index * 100}%)` }}
        >
          {photos.map((src, i) => (
            <div key={i} className="h-full w-full shrink-0 basis-full">
              <Image src={src} alt={property.title} className="h-full w-full" fittingType="fill" />
            </div>
          ))}
        </div>

        <div className="absolute top-3 left-4 right-4 flex flex-wrap items-start justify-end gap-2 pointer-events-none">
          {photos === PHOTOS && <span className="mr-auto rounded-lg bg-surface/90 px-2 py-1 text-[10px] text-text-secondary">Imagem ilustrativa</span>}
          {property.valuation_class && property.valuation_class !== 'Unavailable' && <span className="flex items-center rounded-full bg-surface/90 backdrop-blur px-3 py-1 text-[11px] font-medium text-text-secondary">
            {valuationLabel(property.valuation_class)}
          </span>}
          {Number.isFinite(property.market_heat) && <span title={heatLabel(property.market_heat)} className="flex items-center gap-1 rounded-full bg-surface/90 backdrop-blur px-2.5 py-1 text-[11px] font-medium text-text-secondary">
            <Star className="w-3 h-3 text-brand fill-brand" />
            {(property.market_heat / 10).toFixed(1)}
          </span>}
        </div>

        {photos.length > 1 && (
          <div className={`absolute inset-x-0 bottom-3 flex items-center justify-center gap-2 transition-all duration-300 ${open ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1.5 pointer-events-none'}`}>
            {photos.map((_, i) => (
              <button
                key={i}
                type="button"
                aria-label={`Mostrar foto ${i + 1}`}
                aria-current={i === index}
                onClick={(e) => { e.stopPropagation(); setIndex(i); }}
                className={`h-2 w-2 rounded-full transition-colors ${i === index ? 'bg-foreground' : 'bg-foreground/25'}`}
              />
            ))}
          </div>
        )}
      </div>

      <div className="px-4 pt-4 pb-2">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h3 className="m-0 text-base font-semibold tracking-tight text-foreground">{property.title}</h3>
          <div className="flex shrink-0 items-baseline gap-2">
            {was && <span className="text-[11px] text-text-secondary tnum">AVM {formatBRLCompact(was)}</span>}
            <span className="text-[13px] font-medium text-foreground tnum">{formatBRLCompact(property.price)}</span>
          </div>
        </div>

            <p className="m-0 py-3 text-xs leading-5 text-text-secondary">
              {property.neighborhood} · {propertyTypeLabel(property.property_type)} · {property.area_m2 == null ? 'Área indisponível' : `${property.area_m2} m²`} · {formatM2(property.price_per_m2)}/m²
              {property.days_on_market != null && ` · ${property.days_on_market}d no mercado`}
            </p>
        <div className={`grid transition-all duration-300 ${open ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}>
          <div className="min-h-0 overflow-hidden">

            <div className="flex items-center justify-between gap-4 pt-5">
              <div className="flex items-baseline gap-3">
                {was && <span className="text-xs text-text-secondary tnum">AVM {formatBRLCompact(was)}</span>}
                <span className="text-[15px] font-semibold text-foreground tnum">{formatBRLCompact(property.price)}</span>
              </div>
              <button
                type="button"
                onClick={handleAdd}
                aria-label={state === 'added' ? 'Adicionado ao contexto do agente' : 'Adicionar ao contexto do agente'}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-xs font-medium text-brand-foreground transition-colors hover:bg-brand/90"
              >
                {state === 'loading' && <Loader2 className="w-4 h-4 animate-spin" />}
                {state === 'added' && <Check className="w-4 h-4" />}
                {state === 'idle' && <Plus className="w-4 h-4" />}
                {state === 'added' ? 'Adicionado' : 'Adicionar'}
              </button>
            </div>
            <PropertyNotes propertyId={property.id} />
          </div>
        </div>
      </div>
    </div>
  );
}


