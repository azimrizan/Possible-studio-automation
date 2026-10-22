"use client";

import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, BarChart3, CheckCircle2, Clock, Heart, Instagram, MessageCircle, PauseCircle, RefreshCw } from "lucide-react";
import { formatCompact, studioFetch } from "@/lib/studio";

const RANGES = [
  { key: "today", label: "Today" },
  { key: "last_7d", label: "7 days" },
  { key: "last_30d", label: "30 days" },
  { key: "maximum", label: "All time" },
];

// Meta effective_status -> how we show it. Status always ships with an icon + label, never colour alone.
const STATUS: Record<string, { label: string; cls: string; icon: any }> = {
  ACTIVE: { label: "Delivering", cls: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30", icon: CheckCircle2 },
  PAUSED: { label: "Paused", cls: "text-neutral-300 bg-neutral-800 border-neutral-700", icon: PauseCircle },
  CAMPAIGN_PAUSED: { label: "Paused", cls: "text-neutral-300 bg-neutral-800 border-neutral-700", icon: PauseCircle },
  ADSET_PAUSED: { label: "Paused", cls: "text-neutral-300 bg-neutral-800 border-neutral-700", icon: PauseCircle },
  IN_PROCESS: { label: "Processing", cls: "text-sky-300 bg-sky-500/10 border-sky-500/30", icon: Clock },
  PENDING_REVIEW: { label: "In review", cls: "text-sky-300 bg-sky-500/10 border-sky-500/30", icon: Clock },
  WITH_ISSUES: { label: "Has issues", cls: "text-amber-300 bg-amber-500/10 border-amber-500/30", icon: AlertTriangle },
  ARCHIVED: { label: "Archived", cls: "text-neutral-300 bg-neutral-800 border-neutral-700", icon: PauseCircle },
  DELETED: { label: "Deleted", cls: "text-neutral-300 bg-neutral-800 border-neutral-700", icon: PauseCircle },
  DISAPPROVED: { label: "Rejected", cls: "text-rose-300 bg-rose-500/10 border-rose-500/30", icon: AlertTriangle },
};

const sym = (c: string) => ({ INR: "₹", USD: "$", EUR: "€", GBP: "£" } as Record<string, string>)[c] || `${c} `;

function StatusBadge({ status }: { status: string }) {
  const s = STATUS[status] || { label: status ? status.toLowerCase().replace(/_/g, " ") : "unknown", cls: "text-neutral-300 bg-neutral-800 border-neutral-700", icon: Clock };
  const Icon = s.icon;
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border inline-flex items-center gap-1 ${s.cls}`}>
      <Icon className="h-3 w-3" /> {s.label}
    </span>
  );
}

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 px-3.5 py-3">
      <p className="text-[11px] text-neutral-400">{label}</p>
      <p className="text-lg font-semibold text-white mt-0.5">{value}</p>
      {hint && <p className="text-[10px] text-neutral-500 mt-0.5">{hint}</p>}
    </div>
  );
}

function DailySpendChart({ daily, cur }: { daily: any[]; cur: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 640, H = 180, PAD_L = 44, PAD_B = 22, PAD_T = 10;
  const max = Math.max(...daily.map((d) => d.spend), 1);
  const nice = (() => {
    const step = Math.pow(10, Math.floor(Math.log10(max)));
    return Math.ceil(max / step) * step;
  })();
  const plotW = W - PAD_L - 8, plotH = H - PAD_B - PAD_T;
  const slot = plotW / daily.length;
  const barW = Math.min(24, slot * 0.6);
  const y = (v: number) => PAD_T + plotH - (v / nice) * plotH;
  const fmtDate = (s: string) => new Date(s + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" });
  const labelEvery = Math.ceil(daily.length / 6);
  const h = hover != null ? daily[hover] : null;

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto"
        role="img"
        aria-label={`Daily spend over ${daily.length} days, peaking at ${sym(cur)}${Math.round(max).toLocaleString()}`}
        onMouseLeave={() => setHover(null)}
      >
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={PAD_L} x2={W - 8} y1={y(nice * f)} y2={y(nice * f)} stroke="#262626" strokeWidth={1} />
            <text x={PAD_L - 6} y={y(nice * f) + 3} textAnchor="end" className="fill-neutral-500" fontSize={10}>
              {sym(cur)}{formatCompact(Math.round(nice * f))}
            </text>
          </g>
        ))}
        {daily.map((d, i) => {
          const x = PAD_L + i * slot + (slot - barW) / 2;
          const top = y(d.spend);
          const bh = Math.max(PAD_T + plotH - top, d.spend > 0 ? 2 : 0);
          const r = Math.min(4, barW / 2, bh);
          return (
            <g key={d.date} onMouseEnter={() => setHover(i)}>
              {/* hit target is the whole slot, bigger than the bar */}
              <rect x={PAD_L + i * slot} y={PAD_T} width={slot} height={plotH} fill="transparent" />
              {bh > 0 && (
                <path
                  d={`M${x},${PAD_T + plotH} V${PAD_T + plotH - bh + r} Q${x},${PAD_T + plotH - bh} ${x + r},${PAD_T + plotH - bh} H${x + barW - r} Q${x + barW},${PAD_T + plotH - bh} ${x + barW},${PAD_T + plotH - bh + r} V${PAD_T + plotH} Z`}
                  fill="#80CFAE"
                  opacity={hover == null || hover === i ? 1 : 0.45}
                />
              )}
              {i % labelEvery === 0 && (
                <text x={PAD_L + i * slot + slot / 2} y={H - 6} textAnchor="middle" className="fill-neutral-500" fontSize={10}>
                  {fmtDate(d.date)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {h && hover != null && (
        <div
          className="pointer-events-none absolute top-0 -translate-x-1/2 rounded-lg border border-neutral-700 bg-neutral-950/95 px-2.5 py-1.5 text-[11px] text-neutral-200 shadow-xl whitespace-nowrap"
          style={{ left: `${((PAD_L + hover * slot + slot / 2) / W) * 100}%` }}
        >
          <p className="font-semibold text-white">{fmtDate(h.date)}</p>
          <p>Spend {sym(cur)}{h.spend.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
          <p className="text-neutral-400">{formatCompact(h.impressions)} impressions · {h.clicks} clicks · {h.results} results</p>
        </div>
      )}
    </div>
  );
}

export default function CampaignPerformance({ campaignId }: { campaignId: string }) {
  const [range, setRange] = useState("maximum");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (refresh = false) => {
      setLoading(true);
      try {
        setData(await studioFetch(`/campaigns/${campaignId}/performance?range=${range}${refresh ? "&refresh=true" : ""}`));
        setError(null);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [campaignId, range]
  );

  useEffect(() => {
    load();
    const t = setInterval(() => load(), 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [load]);

  const ads = data?.ads;
  const ig = data?.instagram;
  const cur = ads?.currency || "INR";
  const money = (v?: number | null, digits = 0) =>
    v == null ? "—" : `${sym(cur)}${v.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
  const t = ads?.totals;
  const delivered = Boolean(t && t.impressions > 0);
  const updated = data?.fetched_at ? new Date(data.fetched_at * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";

  return (
    <div className="rounded-2xl border border-neutral-800 bg-[#131313] p-5 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <BarChart3 className="h-4 w-4 text-brand" />
          <h3 className="text-sm font-semibold text-white">Performance</h3>
          {ads?.status && <StatusBadge status={ads.status} />}
          {(ads?.mock) && <span className="text-[10px] text-amber-300">demo data</span>}
        </div>
        <div className="flex items-center gap-2">
          {ads && (
            <div className="flex rounded-lg border border-neutral-800 p-0.5">
              {RANGES.map((r) => (
                <button
                  key={r.key}
                  onClick={() => setRange(r.key)}
                  className={`px-2.5 py-1 text-[11px] rounded-md ${range === r.key ? "bg-neutral-800 text-white font-semibold" : "text-neutral-400 hover:text-white"}`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          )}
          <button
            onClick={() => load(true)}
            disabled={loading}
            title={updated ? `Updated ${updated}` : "Refresh"}
            className="h-7 w-7 rounded-lg border border-neutral-800 text-neutral-400 hover:text-white flex items-center justify-center"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <p className="text-xs text-rose-300 flex items-start gap-2">
          <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" /> {error}
        </p>
      )}

      {data?.notes?.map((n: string) => (
        <p key={n} className="text-xs text-neutral-400">{n}</p>
      ))}

      {!data && !error && (
        <p className="text-xs text-neutral-400 flex items-center gap-2">
          <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Loading results from Meta…
        </p>
      )}

      {ads && !delivered && (
        <p className="text-xs text-neutral-400">
          {["PAUSED", "CAMPAIGN_PAUSED", "ARCHIVED", "DELETED"].includes(ads.status)
            ? "No delivery in this period: the campaign is switched off in Meta. Turn it back on in Ads Manager to start spending."
            : "No delivery yet for this period. New ads usually start a few hours after Meta finishes its review."}
        </p>
      )}

      {ads && delivered && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
            <div>
              <p className="text-[11px] text-neutral-400">{ads.result_label}</p>
              <p className="text-5xl font-semibold text-white leading-tight">{formatCompact(Math.round(t.results))}</p>
              <p className="text-xs text-neutral-400 mt-1">
                {t.cost_per_result != null ? `${money(t.cost_per_result, 2)} per result` : "No results attributed yet"}
                {t.roas != null && ` · ${t.roas.toFixed(2)}× return on ad spend`}
              </p>
            </div>
            <div className="sm:col-span-2 grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              <Tile label="Amount spent" value={money(t.spend)} />
              <Tile label="Reach" value={formatCompact(t.reach)} hint={`${t.frequency.toFixed(2)}× per person`} />
              <Tile label="Impressions" value={formatCompact(t.impressions)} hint={`${money(t.cpm, 0)} per 1,000`} />
              <Tile label="Link clicks" value={formatCompact(t.link_clicks)} hint={t.cpc ? `${money(t.cpc, 2)} per click` : undefined} />
              <Tile label="Click-through rate" value={`${t.ctr.toFixed(2)}%`} />
              <Tile label="All clicks" value={formatCompact(t.clicks)} />
            </div>
          </div>

          {ads.daily.length > 1 && (
            <div>
              <p className="text-[11px] text-neutral-400 mb-2">Spend per day</p>
              <DailySpendChart daily={ads.daily} cur={cur} />
              <details className="mt-1">
                <summary className="text-[11px] text-neutral-500 cursor-pointer hover:text-neutral-300">Show as table</summary>
                <table className="mt-2 w-full text-[11px] text-neutral-300">
                  <thead className="text-neutral-500">
                    <tr><th className="text-left font-medium py-1">Date</th><th className="text-right font-medium">Spend</th><th className="text-right font-medium">Impressions</th><th className="text-right font-medium">Clicks</th><th className="text-right font-medium">Results</th></tr>
                  </thead>
                  <tbody>
                    {ads.daily.map((d: any) => (
                      <tr key={d.date} className="border-t border-neutral-800 tabular-nums">
                        <td className="py-1">{d.date}</td><td className="text-right">{money(d.spend)}</td><td className="text-right">{d.impressions.toLocaleString()}</td><td className="text-right">{d.clicks}</td><td className="text-right">{d.results}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            </div>
          )}
        </>
      )}

      {ads?.ads?.length > 0 && (
        <div className="overflow-x-auto">
          <p className="text-[11px] text-neutral-400 mb-2">By ad</p>
          <table className="w-full text-xs text-neutral-300 min-w-[520px]">
            <thead className="text-[11px] text-neutral-500">
              <tr>
                <th className="text-left font-medium py-1.5">Ad</th>
                <th className="text-right font-medium">Spent</th>
                <th className="text-right font-medium">{ads.result_label}</th>
                <th className="text-right font-medium">Per result</th>
                <th className="text-right font-medium">CTR</th>
              </tr>
            </thead>
            <tbody>
              {ads.ads.map((a: any) => (
                <React.Fragment key={a.id}>
                  <tr className="border-t border-neutral-800 tabular-nums">
                    <td className="py-2 pr-2">
                      <div className="flex items-center gap-2">
                        <span className="text-white truncate max-w-[220px]">{a.name}</span>
                        <StatusBadge status={a.status} />
                      </div>
                    </td>
                    <td className="text-right">{money(a.spend)}</td>
                    <td className="text-right">{formatCompact(Math.round(a.results))}</td>
                    <td className="text-right">{money(a.cost_per_result, 2)}</td>
                    <td className="text-right">{a.ctr.toFixed(2)}%</td>
                  </tr>
                  {a.issues?.filter(Boolean).map((msg: string, i: number) => (
                    <tr key={i}>
                      <td colSpan={5} className="pb-2 text-[11px] text-amber-300">
                        <span className="inline-flex items-start gap-1.5"><AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" /> {msg}</span>
                      </td>
                    </tr>
                  ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {ig && (
        <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-neutral-800 text-xs text-neutral-300">
          <span className="flex items-center gap-1.5 text-neutral-400"><Instagram className="h-3.5 w-3.5" /> Instagram post</span>
          <span className="flex items-center gap-1.5"><Heart className="h-3.5 w-3.5 text-neutral-500" /> {formatCompact(ig.likes)} likes</span>
          <span className="flex items-center gap-1.5"><MessageCircle className="h-3.5 w-3.5 text-neutral-500" /> {formatCompact(ig.comments)} comments</span>
        </div>
      )}

      {data && (
        <p className="text-[10px] text-neutral-500">
          From Meta{updated ? `, updated ${updated}` : ""}. Meta's numbers can lag by a few minutes and may be adjusted for up to 28 days.
        </p>
      )}
    </div>
  );
}
