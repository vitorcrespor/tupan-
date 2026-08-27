import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { cn } from "@/lib/utils";
import { useApp } from "@/lib/AppContext";
import MetricKnob from "./MetricKnob";


function MetricPicker({ options = [], onSelect, className }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const onPointerDown = (event) => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);
  if (!options.length) return null;
  return (
    <div ref={ref} className={cn("relative", className)} onClick={(event) => event.stopPropagation()}>
      <button
        type="button"
        aria-label="Trocar métrica"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "group relative grid h-7 w-8 place-items-center overflow-hidden rounded-lg border border-border/80 bg-gradient-to-br from-card via-card to-brand/[0.07] shadow-[0_5px_14px_hsl(var(--foreground)/0.10),inset_0_1px_0_hsl(0_0%_100%/0.65)] backdrop-blur-sm transition-all hover:-translate-y-0.5 hover:border-brand/45 hover:shadow-[0_8px_20px_hsl(var(--brand)/0.18)] focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/50",
          open && "border-brand/45 bg-brand/10 text-brand",
        )}
      >
        <span className="absolute inset-x-0 bottom-0 h-px bg-brand/35" />
        <span className="relative flex h-3.5 w-4 flex-col justify-between">
          <span className="block h-px w-full rounded-full bg-current/80" />
          <span className="ml-auto block h-px w-2.5 rounded-full bg-current/70" />
          <span className="block h-px w-3.5 rounded-full bg-current/55" />
        </span>
      </button>
      {open && (
        <div className="absolute right-0 top-9 z-40 w-52 overflow-hidden rounded-2xl border border-border/85 bg-card/95 p-1.5 shadow-[0_24px_60px_hsl(var(--foreground)/0.20),inset_0_1px_0_hsl(0_0%_100%/0.6)] backdrop-blur-xl">
          <div className="mb-1 flex items-center gap-2 border-b border-border/65 px-2 py-2">
            <span className="grid h-5 w-5 place-items-center rounded-md bg-brand/10 text-brand"><span className="h-2 w-2 rounded-sm border border-current/80" /></span>
            <p className="text-[9px] font-bold uppercase tracking-[0.14em] text-text-muted">Trocar métrica</p>
          </div>
          {options.map((option) => (
            <button key={option.id || option.label} type="button" onClick={() => { onSelect?.(option); setOpen(false); }} className="group flex w-full items-center gap-2 rounded-xl px-2 py-2 text-left text-xs font-medium text-text-secondary transition-colors hover:bg-brand/10 hover:text-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-brand/45 transition-transform group-hover:scale-125 group-hover:bg-brand" />
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function InsightButton({ item, className }) {
  const { addSavedInsight, savedInsights } = useApp();
  if (!item) return null;
  const added = savedInsights.some((saved) => saved.id === item.id);
  const attachedTab = className?.includes("metric-insight-tab");
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        addSavedInsight(item);
      }}
      aria-label={added ? "Indicador adicionado" : "Adicionar ao painel de contexto"}
      title={added ? "Adicionado ao painel" : "Adicionar ao painel de contexto"}
      className={cn(
        "grid h-7 w-7 place-items-center rounded-full border text-sm font-light leading-none shadow-[0_5px_14px_hsl(var(--foreground)/0.12)] backdrop-blur-sm transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/50",
        !attachedTab && "hover:-translate-y-0.5",
        added ? "border-brand/35 bg-brand/15 text-brand" : "border-border/80 bg-card/90 text-text-muted hover:border-brand/45 hover:bg-brand/10 hover:text-brand",
        className,
      )}
    >
      {added ? "✓" : "+"}
    </button>
  );
}

export function Panel({ className, children, metricOptions, onMetricSelect, activeMetricId, contextItem, ...props }) {
  return (
    <div
      className={cn(
        "metric-host panel-host relative isolate rounded-2xl border border-white/75 bg-card/38 shadow-[0_10px_28px_hsl(220_12%_18%/0.09),inset_0_1px_0_hsl(0_0%_100%/0.88),inset_0_-1px_0_hsl(220_10%_55%/0.10)] backdrop-blur-2xl",

        className,
      )}
      {...props}
    >
      {children}
      <MetricKnob metrics={metricOptions} value={activeMetricId} onChange={onMetricSelect} />
      <InsightButton item={contextItem} className="metric-insight-tab" />
    </div>
  );
}

export function SectionTitle({ children, right, className }) {
  return (
    <div className={cn("flex items-center justify-between mb-3 pr-8", className)}>
      <h3 className="text-[11px] font-bold uppercase tracking-wider text-text-secondary">
        {children}
      </h3>
      {right}
    </div>
  );
}

export function ContextTag({ type, children }) {
  const styles = {
    DATA: "bg-brand/10 text-brand border-brand/20",
    MODEL: "bg-chart-4/10 text-chart-4 border-chart-4/25",
    AI: "bg-positive/10 text-positive border-positive/20",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider uppercase border",
        styles[type],
      )}
    >
      {children || type}
    </span>
  );
}

export function Delta({ value, suffix = "", className }) {
  if (value == null || Number.isNaN(value))
    return <span className="text-text-muted">—</span>;
  const positive = value > 0;
  const neutral = value === 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-xs font-medium tnum",
        neutral
          ? "text-text-muted"
          : positive
            ? "text-positive"
            : "text-negative",
        className,
      )}
    >
      {positive ? "▲" : "▼"} {Math.abs(value).toFixed(1)}
      {suffix}
    </span>
  );
}

function KpiThreeMonthSeries({ series = [], glow }) {
  const recentSeries = series
    .filter((point) => Number.isFinite(point?.value))
    .slice(-3);
  const hasHistory = recentSeries.length >= 2;

  return (
    <div className="relative mt-auto h-11 w-[calc(100%-2.75rem)] min-w-0" aria-label="Série dos últimos três meses">
      <span className="absolute left-0 top-0 text-[8px] font-semibold uppercase tracking-[0.12em] text-text-muted">
        Últimos 3 meses
      </span>
      {hasHistory ? (
        <div className="absolute inset-x-0 bottom-0 h-6">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={recentSeries} margin={{ top: 1, right: 1, bottom: 1, left: 1 }}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={`hsl(${glow})`}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <span className="absolute bottom-0 left-0 text-[10px] text-text-muted">
          Série indisponível
        </span>
      )}
    </div>
  );
}
export function KpiCard({
  label,
  value,
  delta,
  deltaSuffix = "",
  tag = "DATA",
  sub,
  series = [],
  seriesValueFormatter = (v) => v,
  metricOptions = [],
  contextItem,
  className,
}) {

  const [selectedMetric, setSelectedMetric] = useState(null);
  const configuredMetric = metricOptions.find((option) => option.id === selectedMetric);
  const display = configuredMetric || { label, value, delta, deltaSuffix, tag, sub, series, seriesValueFormatter };
  const displayLabel = display.label;
  const displayValue = display.value;
  const displayDelta = display.delta;
  const displayDeltaSuffix = display.deltaSuffix ?? "";
  const displayTag = display.tag ?? tag;
  const displaySub = display.sub;
  const displaySeries = display.series ?? series;
  const displaySeriesFormatter = display.seriesValueFormatter ?? seriesValueFormatter;
  const tints = {
    DATA: {
      glow: "188 78% 52%",
      bar: "bg-aqua",
      chip: "bg-aqua/12 text-aqua border-aqua/25",
    },
    MODEL: {
      glow: "196 72% 46%",
      bar: "bg-lagoon",
      chip: "bg-lagoon/12 text-lagoon border-lagoon/25",
    },
    AI: {
      glow: "158 62% 42%",
      bar: "bg-positive",
      chip: "bg-positive/12 text-positive border-positive/25",
    },
  };
  const tint = tints[displayTag] || tints.DATA;
  const interactive = Boolean(displayLabel);
  const [expanded, setExpanded] = useState(false);
  const [morphing, setMorphing] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [origin, setOrigin] = useState(null);
  const openDetail = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setOrigin({
      left: rect.left,
      top: rect.top,
      width: rect.width,
      height: rect.height,
    });
    setExpanded(true);
    requestAnimationFrame(() => requestAnimationFrame(() => setMorphing(true)));
    window.setTimeout(() => setRevealed(true), 520);
  };
  const closeDetail = () => {
    setRevealed(false);
    setMorphing(false);
    window.setTimeout(() => {
      setExpanded(false);
      setOrigin(null);
    }, 430);
  };
  useEffect(() => {
    const onKey = (event) =>
      event.key === "Escape" && expanded && closeDetail();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expanded]);
  const cardBody = (
    <>
      <div
        className="absolute -top-8 -right-8 w-20 h-20 rounded-full blur-2xl opacity-20 pointer-events-none"
        style={{ background: "hsl(220 12% 55% / 0.045)" }}
      />
      <div className="relative flex items-center justify-between">
        <span className="text-[11px] text-text-secondary font-semibold">
          {displayLabel}
        </span>
        <div className="mr-7 flex items-center gap-1.5">
          <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[8px] font-bold tracking-wider uppercase border ${tint.chip}`}>
            {displayTag}
          </span>
        </div>
      </div>
      <div className="relative flex items-center min-h-11 rounded-lg border border-border/65 bg-foreground/[0.035] px-2.5 shadow-inner shadow-foreground/[0.025]">
        <span className="text-[23px] font-black tracking-[-0.045em] tnum tabular-nums text-foreground leading-none">
          {displayValue}
        </span>
      </div>
      <div className="relative flex items-center gap-2 h-4">
        {displayDelta != null && <Delta value={displayDelta} suffix={displayDeltaSuffix} />}
        {displaySub && <span className="text-[11px] text-text-muted">{displaySub}</span>}
      </div>
      <KpiThreeMonthSeries series={displaySeries} glow={tint.glow} />
      <InsightButton className="absolute bottom-3 right-3 z-10" item={contextItem || {
        id: `kpi-${displayLabel.toLowerCase().replace(/[^a-z0-9]+/gi, "-")}`,
        type: "KPI",
        label: displayLabel,
        data: { value: displayValue, delta: displayDelta, unit: displaySub, series: displaySeries },
      }} />
    </>
  );

  return (
    <>
      <div

        role={interactive ? "button" : undefined}
        tabIndex={interactive ? 0 : undefined}
        onClick={interactive ? openDetail : undefined}
        onKeyDown={(event) => {
          if (interactive && (event.key === "Enter" || event.key === " ")) openDetail(event);
        }}
        className={cn(
          "metric-host relative w-full min-h-[174px] overflow-visible rounded-[14px] border border-white/75 bg-card/36 p-5 flex flex-col gap-3 text-left shadow-[0_4px_12px_hsl(220_12%_18%/0.07),0_14px_30px_hsl(220_12%_18%/0.06),inset_0_1px_0_hsl(0_0%_100%/0.9)] backdrop-blur-2xl transition-all duration-300 hover:-translate-y-0.5 hover:border-brand/35 hover:shadow-[0_8px_18px_hsl(220_12%_18%/0.10),0_20px_38px_hsl(220_12%_18%/0.08),inset_0_1px_0_hsl(0_0%_100%/0.96)] focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/60",
          expanded && "pointer-events-none opacity-0",
          !interactive && "cursor-default hover:translate-y-0 hover:border-border/80 hover:shadow-[0_2px_5px_hsl(var(--foreground)/0.04),0_12px_24px_hsl(var(--foreground)/0.055)]",
          className,
        )}
        style={{
          backgroundColor: "var(--metric-knob-background-color)",
          backgroundImage: "var(--metric-knob-background-image)",
          "--metric-knob-background-color": "hsl(var(--card) / 0.44)",
          "--metric-knob-background-image": "linear-gradient(145deg, hsl(0 0% 100% / 0.55) 0%, hsl(var(--card) / 0.44) 38%, hsl(188 60% 90% / 0.14) 100%)",
          "--metric-tab-radius": "14px",
          "--metric-tab-border": "hsl(0 0% 100% / .84)",
        }}
        aria-label={interactive ? `Ver série histórica: ${displayLabel}` : undefined}
      >

        {cardBody}
        <MetricKnob className="metric-knob--kpi" metrics={metricOptions} value={selectedMetric} onChange={(option) => setSelectedMetric(option.id)} />
      </div>
      {expanded &&
        origin &&
        createPortal(
          <>
            <div
              className="fixed inset-0 z-[90] bg-slate-700/45 backdrop-blur-md transition-opacity duration-500"
              onClick={closeDetail}
            />
            <section
              className="fixed z-[100] overflow-hidden border border-white/40 bg-card shadow-[0_32px_90px_hsl(215_25%_12%/0.32),0_10px_32px_hsl(215_25%_12%/0.18)] will-change-[transform,left,top,width,height] transition-[left,top,width,height,transform] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]"
              style={
                morphing
                  ? {
                      left: "50%",
                      top: "50%",
                      width: "min(760px, calc(100vw - 32px))",
                      height: "min(480px, calc(100vh - 32px))",
                      transform: "translate(-50%, -50%)",
                      borderRadius: 28,
                    }
                  : {
                      ...origin,
                      transform: "translate(0, 0)",
                      borderRadius: 28,
                    }
              }
              onClick={(event) => event.stopPropagation()}
            >
              {!revealed ? (
                <div className="relative h-full overflow-hidden rounded-t-[28px] bg-gradient-to-br from-slate-100 via-slate-200 to-slate-300 shadow-[inset_0_1px_0_rgb(255_255_255/0.9),inset_0_-14px_26px_rgb(71_85_105/0.18)]">
                  <div className="absolute inset-x-0 top-0 h-1/2 rounded-t-[28px] bg-gradient-to-b from-white/55 to-transparent" />
                </div>
              ) : (
                <div className="h-full animate-in fade-in duration-300">
                  <button
                    onClick={closeDetail}
                    className="absolute right-4 top-3 z-10 text-lg text-text-muted"
                  >
                    ×
                  </button>
                  <div className="border-b border-border/70 px-6 py-5">
                    <div className="flex gap-2">
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[9px] font-bold ${tint.chip}`}
                      >
                        {displayTag}
                      </span>
                      <h2 className="font-semibold">{displayLabel}</h2>
                    </div>
                    <p className="text-sm text-text-muted">
                      Histórico dos últimos 12 meses
                    </p>
                  </div>
                  <div className="p-4">
                    <ResponsiveContainer width="100%" height={280}>
                      <LineChart data={displaySeries}>
                        <CartesianGrid
                          stroke="hsl(var(--border))"
                          strokeDasharray="3 4"
                          vertical={false}
                        />
                        <XAxis dataKey="label" />
                        <YAxis tickFormatter={displaySeriesFormatter} />
                        <Tooltip
                          formatter={(v) => [displaySeriesFormatter(v), displayLabel]}
                        />
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke={`hsl(${tint.glow})`}
                          strokeWidth={2.5}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </section>
          </>,
          document.body,
        )}
    </>
  );
}

export function StatPill({ label, value, tone = "default" }) {
  const tones = {
    default: "text-foreground",
    positive: "text-positive",
    negative: "text-negative",
    warning: "text-warning",
    brand: "text-brand",
  };
  return (
    <div className="flex flex-col gap-0.5 px-3 py-2 rounded-xl border border-border bg-elevated/50">
      <span className="text-[10px] uppercase tracking-wide text-text-muted">
        {label}
      </span>
      <span className={cn("text-sm font-semibold tnum", tones[tone])}>
        {value}
      </span>
    </div>
  );
}

export function ScoreBar({ label, value, tone }) {
  const color =
    tone ||
    (value >= 75
      ? "bg-positive"
      : value >= 50
        ? "bg-brand"
        : value >= 30
          ? "bg-warning"
          : "bg-negative");
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-text-secondary">{label}</span>
        <span className="font-medium tnum text-foreground">{value}</span>
      </div>
      <div className="h-1.5 rounded-full bg-border overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  );
}

export function MetricRow({ label, value, valueClass }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border/60 last:border-0">
      <span className="text-xs text-text-secondary">{label}</span>
      <span
        className={cn("text-xs font-medium tnum text-foreground", valueClass)}
      >
        {value}
      </span>
    </div>
  );
}

export function StatusDot({ status }) {
  const map = {
    Operational: "bg-positive",
    Active: "bg-positive",
    Error: "bg-negative",
    Degraded: "bg-warning",
  };
  return (
    <span
      className={cn(
        "inline-block w-1.5 h-1.5 rounded-full",
        map[status] || "bg-text-muted",
      )}
    />
  );
}
