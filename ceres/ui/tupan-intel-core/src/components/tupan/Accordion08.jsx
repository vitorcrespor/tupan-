import React, { useState } from 'react';

/**
 * Ceres accordion — soft-retro: cream surface, orange accent, mono titles,
 * dashed dividers, ink-bordered icon boxes. Single-open.
 */
const ITEMS = [
  {
    title: 'Our Mission',
    body: 'Ceres turns raw market signals — listings, sales velocity, demand — into clear, actionable intelligence so brokers move with conviction, not guesswork.',
    icon: 'compass',
  },
  {
    title: 'Design Ethos',
    body: 'A calm, glassy workspace where dense data stays legible. Every chart, map, and valuation is built to be read in a glance and trusted at depth.',
    icon: 'grid',
  },
  {
    title: 'Data Integrity',
    body: 'Every valuation and heat score is traceable to source listings and comparable sales. No black boxes — just provenance you can inspect.',
    icon: 'diagonal',
  },
  {
    title: 'Privacy by Design',
    body: 'Your portfolio, searches, and agent context stay scoped to your account. Ceres watches the market for you, never exposes your moves to others.',
    icon: 'hub',
  },
];

function Icon({ name }) {
  const line = { stroke: 'var(--ink)', strokeWidth: 0.75 };
  const dot = { fill: 'var(--ink)' };
  const acc = { fill: 'var(--acc)' };
  switch (name) {
    case 'compass':
      return (
        <svg viewBox="0 0 24 24" width="24" height="24">
          <line x1="12" y1="12" x2="12" y2="4" {...line} />
          <line x1="12" y1="12" x2="20" y2="12" {...line} />
          <line x1="12" y1="12" x2="12" y2="20" {...line} />
          <line x1="12" y1="12" x2="4" y2="12" {...line} />
          <circle cx="12" cy="4" r="1.6" {...dot} />
          <circle cx="20" cy="12" r="1.6" {...dot} />
          <circle cx="12" cy="20" r="1.6" {...dot} />
          <circle cx="4" cy="12" r="1.6" {...dot} />
          <circle cx="12" cy="12" r="2.1" {...acc} />
        </svg>
      );
    case 'grid':
      return (
        <svg viewBox="0 0 24 24" width="24" height="24">
          <circle cx="7" cy="8" r="1.6" {...acc} />
          <circle cx="12" cy="8" r="1.6" {...dot} />
          <circle cx="17" cy="8" r="1.6" {...acc} />
          <circle cx="7" cy="16" r="1.6" {...dot} />
          <circle cx="12" cy="16" r="1.6" {...acc} />
          <circle cx="17" cy="16" r="1.6" {...dot} />
        </svg>
      );
    case 'diagonal':
      return (
        <svg viewBox="0 0 24 24" width="24" height="24">
          <line x1="12" y1="12" x2="17" y2="7" {...line} />
          <line x1="12" y1="12" x2="17" y2="17" {...line} />
          <line x1="12" y1="12" x2="7" y2="17" {...line} />
          <line x1="12" y1="12" x2="7" y2="7" {...line} />
          <circle cx="17" cy="7" r="1.6" {...dot} />
          <circle cx="17" cy="17" r="1.6" {...dot} />
          <circle cx="7" cy="17" r="1.6" {...dot} />
          <circle cx="7" cy="7" r="1.6" {...dot} />
          <circle cx="12" cy="12" r="2.1" {...acc} />
        </svg>
      );
    case 'hub':
      return (
        <svg viewBox="0 0 24 24" width="24" height="24">
          <line x1="12" y1="12" x2="12" y2="4.5" {...line} />
          <line x1="12" y1="12" x2="18.99" y2="8.25" {...line} />
          <line x1="12" y1="12" x2="18.99" y2="15.75" {...line} />
          <line x1="12" y1="12" x2="12" y2="19.5" {...line} />
          <line x1="12" y1="12" x2="5.01" y2="15.75" {...line} />
          <line x1="12" y1="12" x2="5.01" y2="8.25" {...line} />
          <circle cx="12" cy="4.5" r="1.6" {...dot} />
          <circle cx="18.99" cy="8.25" r="1.6" {...dot} />
          <circle cx="18.99" cy="15.75" r="1.6" {...dot} />
          <circle cx="12" cy="19.5" r="1.6" {...dot} />
          <circle cx="5.01" cy="15.75" r="1.6" {...dot} />
          <circle cx="5.01" cy="8.25" r="1.6" {...dot} />
          <circle cx="12" cy="12" r="2.1" {...acc} />
        </svg>
      );
    default:
      return null;
  }
}

function Row({ item, isOpen, onToggle, uid }) {
  return (
    <div className="border-t border-dashed first:border-t-0" style={{ borderColor: 'var(--ink)' }}>
      <h3>
        <button
          type="button"
          aria-expanded={isOpen}
          aria-controls={`ceres-acc-${uid}`}
          onClick={onToggle}
          className="flex items-center gap-3 w-full px-4 sm:px-6 py-5 text-left hover:bg-black/[0.04] transition-colors focus-visible:outline-none focus-visible:shadow-[inset_0_0_0_2px_var(--ink)]"
          style={{ color: 'var(--ink)' }}
        >
          <span className="w-[7px] h-[7px] rounded-full shrink-0" style={{ background: 'var(--acc)' }} />
          <span className="flex-1 min-w-0 break-words font-mono text-base sm:text-lg leading-snug">
            {item.title}
          </span>
          <span
            className="w-3.5 h-3.5 shrink-0 flex items-center justify-center"
            style={{ color: 'var(--ink)' }}
          >
            <svg viewBox="0 0 14 14" width="14" height="14" fill="currentColor">
              <rect x="0" y="6.25" width="14" height="1.5" rx="0.75" />
              <rect
                x="6.25"
                y="0"
                width="1.5"
                height="14"
                rx="0.75"
                style={{
                  transformOrigin: '7px 7px',
                  transform: isOpen ? 'rotate(90deg)' : 'none',
                  transition: 'transform 0.3s ease-in-out',
                }}
              />
            </svg>
          </span>
        </button>
      </h3>
      <div
        id={`ceres-acc-${uid}`}
        role="region"
        className="grid"
        style={{
          gridTemplateRows: isOpen ? '1fr' : '0fr',
          transition: 'grid-template-rows 0.3s cubic-bezier(0.4,0,0.2,1)',
        }}
      >
        <div className="overflow-hidden min-h-0">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-10 px-4 sm:px-6 py-6">
            <span
              className="w-12 h-12 shrink-0 flex items-center justify-center rounded-xl"
              style={{
                border: '1px solid var(--ink)',
                opacity: isOpen ? 1 : 0,
                transform: isOpen ? 'scale(1) rotate(0deg)' : 'scale(0.5) rotate(-12deg)',
                transition: 'opacity 0.4s cubic-bezier(0.22,1,0.36,1) 0.05s, transform 0.4s cubic-bezier(0.22,1,0.36,1) 0.05s',
              }}
            >
              <Icon name={item.icon} />
            </span>
            <p
              className="max-w-[320px] font-body text-sm leading-relaxed break-words"
              style={{
                color: 'var(--ink)',
                opacity: isOpen ? 1 : 0,
                transform: isOpen ? 'translateY(0)' : 'translateY(8px)',
                transition: 'opacity 0.3s ease-out 0.13s, transform 0.3s ease-out 0.13s',
              }}
            >
              {item.body}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Accordion08({ className = '' }) {
  const [open, setOpen] = useState(0);
  /** @type {React.CSSProperties & {'--ink': string, '--acc': string}} */
  const palette = {
    background: '#F2EDE3',
    '--ink': '#1A1A1A',
    '--acc': '#FF5C28',
  };

  return (
    <section className={`flex justify-center px-4 sm:px-8 py-8 sm:py-12 ${className}`}>
      <div
        className="w-full max-w-[720px] rounded-2xl overflow-hidden shadow-[0_12px_30px_-10px_rgba(20,90,105,0.22)]"
        style={palette}
      >
        {ITEMS.map((item, i) => (
          <Row
            key={item.title}
            item={item}
            uid={i}
            isOpen={open === i}
            onToggle={() => setOpen(open === i ? -1 : i)}
          />
        ))}
      </div>
    </section>
  );
}
