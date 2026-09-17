import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, Plus } from "lucide-react";
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
import "./KpiCard.css";

const METRIC_CONTEXT_KEY = {
  'median-m2': 'price_m2',
  'market-heat': 'market_heat',
  'active-listings': 'active_listings',
  'avg-dom': 'dom',
  'avm-deviation': 'avm_deviation',
};


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
          "icon-control group relative h-8 w-9 overflow-hidden rounded-lg focus:outline-none",
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
        <div className="surface-popover absolute right-0 top-10 z-40 w-52 overflow-hidden rounded-2xl p-1.5">
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
        "icon-control grid h-8 w-8 place-items-center leading-none focus:outline-none",
        added ? "border-brand/35 bg-brand/15 text-brand" : "border-border/80 bg-card/90 text-text-muted hover:border-brand/45 hover:bg-brand/10 hover:text-brand",
        className,
      )}
    >
      {added ? (
        <Check aria-hidden="true" className={attachedTab ? "h-2.5 w-2.5 stroke-[2]" : "h-3.5 w-3.5 stroke-[2]"} />
      ) : (
        <Plus aria-hidden="true" className={attachedTab ? "h-2.5 w-2.5 stroke-[2]" : "h-3.5 w-3.5 stroke-[2]"} />
      )}
    </button>
  );
}

export function Panel({
  className = "",
  children = null,
  metricOptions = [],
  onMetricSelect = undefined,
  activeMetricId = undefined,
  contextItem = undefined,
  ...props
}) {
  return (
    <div
      className={cn(
        "panel-host relative isolate",
        metricOptions.length || contextItem
          ? "metric-host surface-panel rounded-2xl"
          : "panel-static",
        className,
      )}
      {...props}
    >
      {children}
      <MetricKnob className="" metrics={metricOptions} value={activeMetricId} onChange={onMetricSelect} />
      <InsightButton item={contextItem} className="metric-insight-tab" />
    </div>
  );
}

export function SectionTitle({ children, right = null, className = "" }) {
  return (
    <div className={cn("ceres-section-title flex flex-wrap items-center justify-between gap-2 mb-4 pr-8", className)}>
      <h3 className="text-sm font-semibold leading-snug tracking-tight text-foreground">
        {children}
      </h3>
      {right && <div className="shrink-0 text-xs text-text-secondary">{right}</div>}
    </div>
  );
}

export function ContextTag({ type, children }) {
  const styles = {
    DATA: "text-text-secondary",
    MODEL: "text-text-secondary",
    AI: "text-brand",
  };
  const labels = { DATA: 'Dados', MODEL: 'Modelo', AI: 'IA' };
  const descriptions = {
    DATA: 'Indicador baseado em dados observados.',
    MODEL: 'Indicador calculado por modelo estatístico.',
    AI: 'Interpretação gerada pela Ceres a partir do contexto disponível.',
  };
  return (
    <span
      title={descriptions[type]}
      className={cn(
        "inline-flex items-center text-[11px] font-medium",
        styles[type],
      )}
    >
      {children || labels[type] || type}
    </span>
  );
}

export function Delta({ value, suffix = "", className = "" }) {
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

function KpiThreeMonthSeries({ series = [], glow, label = "Últimos 3 meses" }) {
  const recentSeries = series
    .filter((point) => Number.isFinite(point?.value))
    .slice(-3);
  const hasHistory = recentSeries.length >= 2;

  return (
    <div className="relative mt-auto h-11 w-[calc(100%-2.75rem)] min-w-0" aria-label="Série dos últimos três meses">
      <span className="absolute left-0 top-0 text-[8px] font-semibold uppercase tracking-[0.12em] text-text-muted">
        {label}
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
  id: metricId,
  label,
  value,
  delta = null,
  deltaSuffix = "",
  tag = "DATA",
  sub = null,
  series = [],
  seriesLabel = "Últimos 3 meses",
  seriesValueFormatter = (v) => v,
  metricOptions = [],
  contextItem = null,
  className = "",
}) {

  const [selectedMetric, setSelectedMetric] = useState(null);
  const configuredMetric = metricOptions.find((option) => option.id === selectedMetric);
  const display = configuredMetric || { id: metricId, label, value, delta, deltaSuffix, tag, sub, series, seriesLabel, seriesValueFormatter };
  const displayLabel = display.label;
  const displayValue = display.value;
  const displayDelta = display.delta;
  const displayDeltaSuffix = display.deltaSuffix ?? "";
  const displayTag = display.tag ?? tag;
  const displaySub = display.sub;
  const displaySeries = display.series ?? series;
  const displaySeriesLabel = display.seriesLabel ?? seriesLabel;
  const displaySeriesFormatter = display.seriesValueFormatter ?? seriesValueFormatter;
  const tints = {
    DATA: {
      glow: "var(--aqua)",
      bar: "bg-aqua",
      chip: "bg-aqua/12 text-aqua border-aqua/25",
    },
    MODEL: {
      glow: "var(--lagoon)",
      bar: "bg-lagoon",
      chip: "bg-lagoon/12 text-lagoon border-lagoon/25",
    },
    AI: {
      glow: "var(--positive)",
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
  const [destination, setDestination] = useState(null);
  const openDetail = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const width = Math.min(760, window.innerWidth - 32);
    const height = Math.min(480, window.innerHeight - 32);
    setOrigin({
      left: rect.left,
      top: rect.top,
      width: rect.width,
      height: rect.height,
    });
    setDestination({
      left: Math.round((window.innerWidth - width) / 2),
      top: Math.round((window.innerHeight - height) / 2),
      width,
      height,
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
      setDestination(null);
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
        style={{ background: "hsl(var(--brand) / 0.06)" }}
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
      <KpiThreeMonthSeries series={displaySeries} glow={tint.glow} label={displaySeriesLabel} />
      <InsightButton className="pointer-events-auto absolute bottom-3 right-3 z-10" item={contextItem || {
        id: `kpi-${displayLabel.toLowerCase().replace(/[^a-z0-9]+/gi, "-")}`,
        type: "KPI",
        label: displayLabel,
        data: { metric: METRIC_CONTEXT_KEY[display.id], value: displayValue, delta: displayDelta, unit: displaySub, series: displaySeries },
      }} />
    </>
  );

  return (
    <>
      <div
        className={cn(
          "metric-host kpi-card surface-panel relative w-full min-h-[174px] overflow-visible rounded-[14px] p-5 text-left hover:-translate-y-0.5",
          expanded && "pointer-events-none opacity-0",
          !interactive && "cursor-default hover:translate-y-0",
          className,
        )}
      >
        {interactive && (
          <button
            type="button"
            onClick={openDetail}
            className="absolute inset-0 z-0 cursor-pointer rounded-[inherit] focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/60"
            aria-label={`Ver série histórica: ${displayLabel}`}
          />
        )}
        <div className="relative z-[1] flex h-full flex-col gap-3 pointer-events-none">
          {cardBody}
        </div>
        <MetricKnob className="metric-knob--kpi" metrics={metricOptions} value={selectedMetric} onChange={(option) => setSelectedMetric(option.id)} />
      </div>
      {expanded &&
        origin &&
        destination &&
        createPortal(
          <>
            <div
              className="kpi-morph-backdrop fixed inset-0 z-[90] transition-opacity duration-500"
              onClick={closeDetail}
            />
            <section
              className="kpi-morph-dialog fixed z-[100] overflow-hidden will-change-[left,top,width,height,border-radius]"
              style={
                morphing
                  ? { ...destination, borderRadius: 28 }
                  : { ...origin, borderRadius: 28 }
              }
              onClick={(event) => event.stopPropagation()}
            >
              {!revealed ? (
                <div className="kpi-morph-mask relative h-full overflow-hidden rounded-t-[28px]">
                  <div className="kpi-morph-mask__highlight absolute inset-x-0 top-0 h-1/2 rounded-t-[28px]" />
                </div>
              ) : (
                <div className="h-full animate-in fade-in duration-300">
                  <button
                    onClick={closeDetail}
                    aria-label="Fechar série histórica" className="icon-control absolute right-4 top-3 z-10 text-lg text-text-muted"
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
                      Histórico: {displaySeriesLabel.toLowerCase()}
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

export function ScoreBar({ label, value, tone = undefined }) {
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

export function MetricRow({ label, value, valueClass = "" }) {
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
