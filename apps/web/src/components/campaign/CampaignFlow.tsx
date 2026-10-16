"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Calendar,
  Check,
  CheckCircle2,
  ExternalLink,
  Film,
  Globe,
  Instagram,
  Lightbulb,
  MapPin,
  Megaphone,
  RefreshCw,
  Rocket,
  ShieldCheck,
  Sparkles,
  Target,
  Users,
  Wallet,
  X,
} from "lucide-react";
import { CTA_LABELS, MetaConnection, OBJECTIVE_LABELS, formatCompact, studioFetch } from "@/lib/studio";
import MetaConnectCard from "./MetaConnectCard";

interface Props {
  campaignId: string;
  onBack: () => void;
}

const TRANSITIONAL = new Set(["approved", "publishing", "published", "building_ads", "launching"]);
const PROGRESS = new Set(["approved", "publishing", "published", "building_ads", "ads_ready", "launching", "live", "done"]);
const PLANNING_STEPS = [
  "Reading your creatives",
  "Researching your market & competitors",
  "Checking real audiences with Meta",
  "Choosing objective, budget & schedule",
  "Writing ad copy for each creative",
];

const currencySymbol = (c: string) => ({ INR: "₹", USD: "$", EUR: "€", GBP: "£" } as Record<string, string>)[c] || `${c} `;

function Why({ text }: { text?: string }) {
  if (!text) return null;
  return (
    <p className="text-[11px] text-indigo-200/70 mt-1.5 flex gap-1.5 leading-relaxed">
      <Sparkles className="h-3 w-3 mt-0.5 shrink-0 text-indigo-300" />
      <span>{text}</span>
    </p>
  );
}

function Field({ label, icon: Icon, children }: { label: string; icon: any; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
        <Icon className="h-3.5 w-3.5 text-slate-500" /> {label}
      </label>
      {children}
    </div>
  );
}

function RobotStage({ src, title, subtitle, children, pulse }: { src: string; title: string; subtitle?: string; children?: React.ReactNode; pulse?: boolean }) {
  return (
    <div className="relative rounded-3xl border border-indigo-500/25 bg-[#070b1a] overflow-hidden px-6 py-10 sm:py-12 text-center">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.18),transparent_65%)] pointer-events-none" />
      <img
        src={src}
        alt=""
        className={`relative mx-auto h-52 sm:h-64 w-auto object-contain drop-shadow-[0_20px_40px_rgba(0,0,0,0.6)] ${pulse ? "animate-robot-zoom" : ""}`}
      />
      <h3 className="relative mt-6 text-xl sm:text-2xl font-bold text-white">{title}</h3>
      {subtitle && <p className="relative mt-2 text-sm text-slate-400 max-w-lg mx-auto">{subtitle}</p>}
      {children && <div className="relative mt-6">{children}</div>}
    </div>
  );
}

export default function CampaignFlow({ campaignId, onBack }: Props) {
  const [campaign, setCampaign] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"" | "strategy" | "save" | "approve" | "launch">("");
  const [stage, setStage] = useState<"settings" | "review">("settings");
  const [planStep, setPlanStep] = useState(0);
  const [instruction, setInstruction] = useState("");
  const [draft, setDraft] = useState<any>(null);
  const [conn, setConn] = useState<MetaConnection | null>(null);
  const [doPublish, setDoPublish] = useState(true);
  const [doAds, setDoAds] = useState(true);
  const startedStrategy = useRef(false);

  const load = useCallback(async () => {
    const c = await studioFetch(`/campaigns/${campaignId}`);
    setCampaign(c);
    return c;
  }, [campaignId]);

  const runStrategy = useCallback(
    async (instr = "") => {
      setBusy("strategy");
      setError(null);
      try {
        setCampaign(await studioFetch(`/campaigns/${campaignId}/strategy`, { method: "POST", body: JSON.stringify({ instruction: instr }) }));
        setStage("settings");
      } catch (e: any) {
        setError(e.message);
        await load().catch(() => {});
      } finally {
        setBusy("");
      }
    },
    [campaignId, load]
  );

  useEffect(() => {
    load()
      .then((c) => {
        if (c.status === "draft" && !startedStrategy.current) {
          startedStrategy.current = true;
          runStrategy();
        }
      })
      .catch((e) => setError(e.message));
  }, [load, runStrategy]);

  // Rotate the "what the agent is doing" labels while it works.
  useEffect(() => {
    if (busy !== "strategy") return;
    setPlanStep(0);
    const t = setInterval(() => setPlanStep((s) => Math.min(s + 1, PLANNING_STEPS.length - 1)), 2600);
    return () => clearInterval(t);
  }, [busy]);

  // Poll while background steps run.
  useEffect(() => {
    if (!campaign || !TRANSITIONAL.has(campaign.status)) return;
    const t = setInterval(() => load().catch(() => {}), 1500);
    return () => clearInterval(t);
  }, [campaign, load]);

  // Local editable copy of the plan.
  useEffect(() => {
    if (campaign?.strategy && campaign.status === "planned") {
      const p = campaign.strategy.plan;
      setDraft({
        name: p.name,
        objective: p.objective,
        daily_budget: p.daily_budget,
        duration_days: p.duration_days,
        start_local: p.start_time_iso.slice(0, 16),
        start_offset: p.start_time_iso.slice(16),
        age_min: p.audience.age_min,
        age_max: p.audience.age_max,
        genders: p.audience.genders,
        removed: [] as string[],
        ads: p.ads.map((a: any) => ({ ...a })),
        caption: campaign.strategy.caption || "",
        website_url: campaign.business.website_url || "",
      });
    }
  }, [campaign?.strategy, campaign?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const plan = campaign?.strategy?.plan;
  const currency = plan?.currency || "INR";
  const sym = currencySymbol(currency);
  const special = (plan?.special_ad_categories || []).length > 0;

  const allowedObjectives = useMemo(() => {
    const site = Boolean(draft?.website_url);
    const pixel = Boolean(campaign?.business?.pixel_id);
    return ["OUTCOME_AWARENESS", "OUTCOME_ENGAGEMENT", ...(site ? ["OUTCOME_TRAFFIC"] : []), ...(site && pixel ? ["OUTCOME_SALES", "OUTCOME_LEADS"] : [])];
  }, [draft?.website_url, campaign?.business?.pixel_id]);

  const savePlan = async () => {
    if (!draft || !plan) return true;
    setBusy("save");
    setError(null);
    try {
      const body: any = {
        name: draft.name,
        website_url: draft.website_url,
        daily_budget: Number(draft.daily_budget),
        duration_days: Number(draft.duration_days),
        start_time_iso: `${draft.start_local}:00${draft.start_offset.replace(/^:\d\d/, "")}`,
        remove_interest_ids: draft.removed,
        ads: draft.ads,
        caption: draft.caption,
      };
      if (draft.objective !== plan.objective) body.objective = draft.objective;
      if (!special) {
        body.age_min = Number(draft.age_min);
        body.age_max = Number(draft.age_max);
        body.genders = draft.genders;
      }
      setCampaign(await studioFetch(`/campaigns/${campaignId}/plan`, { method: "PUT", body: JSON.stringify(body) }));
      return true;
    } catch (e: any) {
      setError(e.message);
      return false;
    } finally {
      setBusy("");
    }
  };

  const approve = async () => {
    setBusy("approve");
    setError(null);
    try {
      setCampaign(
        await studioFetch(`/campaigns/${campaignId}/approve`, {
          method: "POST",
          body: JSON.stringify({ publish_instagram: doPublish, create_ads: doAds }),
        })
      );
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  };

  const launch = async () => {
    setBusy("launch");
    setError(null);
    try {
      setCampaign(await studioFetch(`/campaigns/${campaignId}/launch`, { method: "POST" }));
    } catch (e: any) {
      setError(e.message);
      await load().catch(() => {});
    } finally {
      setBusy("");
    }
  };

  // ---------------------------------------------------------------- render helpers
  const status: string = campaign?.status || "draft";
  const inProgress = PROGRESS.has(status) || (status === "failed" && campaign?.approval?.approved_at);
  const currentStep = inProgress ? 3 : stage === "review" ? 3 : 2;
  const connReady = Boolean(conn?.connected && conn.selection?.ig_user_id && conn.selection?.ad_account_id);
  const totalSpend = draft ? Number(draft.daily_budget || 0) * Number(draft.duration_days || 0) : 0;

  const Stepper = (
    <div className="flex items-center gap-2 sm:gap-3">
      {["Creative", "Settings", "Review & Launch"].map((label, i) => {
        const n = i + 1;
        const done = n < currentStep;
        const active = n === currentStep;
        return (
          <React.Fragment key={label}>
            <div className="flex items-center gap-2">
              <span
                className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold border ${
                  done
                    ? "bg-emerald-500/20 border-emerald-500/60 text-emerald-300"
                    : active
                    ? "bg-gradient-to-br from-indigo-500 to-purple-600 border-transparent text-white shadow-lg shadow-indigo-600/40"
                    : "border-slate-700 text-slate-500"
                }`}
              >
                {done ? <Check className="h-4 w-4" /> : n}
              </span>
              <span className={`text-xs hidden sm:inline ${active ? "text-white font-semibold" : "text-slate-500"}`}>{label}</span>
            </div>
            {n < 3 && <div className={`h-px w-6 sm:w-12 ${done ? "bg-emerald-500/50" : "bg-slate-700"}`} />}
          </React.Fragment>
        );
      })}
    </div>
  );

  const Header = (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="h-10 w-10 rounded-full border border-slate-700 bg-slate-900/80 hover:bg-slate-800 text-slate-300 flex items-center justify-center"
          title="Back"
        >
          <ArrowLeft className="h-4.5 w-4.5" />
        </button>
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            {status === "live" || status === "done"
              ? "Campaign live"
              : inProgress
              ? "Launching your campaign"
              : stage === "review"
              ? "Review & approve"
              : "Campaign settings"}
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            {status === "live" || status === "done"
              ? "Everything is published. Track results in Meta Ads Manager."
              : inProgress
              ? "Your AI team is posting and setting up ads."
              : "Planned by your Meta strategist agent. Everything is editable."}
          </p>
        </div>
      </div>
      {Stepper}
    </div>
  );

  const ErrorBar = error && (
    <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex items-start gap-2.5">
      <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
      <span className="flex-1">{error}</span>
      <button onClick={() => setError(null)} className="text-rose-300 hover:text-white">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );

  const CreativeThumbs = ({ size = "md" }: { size?: "md" | "sm" }) => (
    <div className={`grid ${size === "md" ? "grid-cols-2 sm:grid-cols-3" : "grid-cols-4"} gap-3`}>
      {campaign.creatives.map((c: any, i: number) => (
        <div key={c.asset_id} className={`relative ${size === "md" ? "aspect-[4/5]" : "aspect-square"} rounded-xl overflow-hidden border border-slate-700 bg-slate-950`}>
          {c.kind === "video" ? (
            <video src={c.url} className="h-full w-full object-cover" muted playsInline loop autoPlay />
          ) : (
            <img src={c.url} alt="" className="h-full w-full object-cover" />
          )}
          <span className="absolute top-1.5 left-1.5 text-[9px] font-bold px-1.5 py-0.5 rounded bg-black/70 text-white flex items-center gap-1">
            {c.kind === "video" && <Film className="h-2.5 w-2.5" />}#{i + 1}
          </span>
        </div>
      ))}
    </div>
  );

  // ---------------------------------------------------------------- states
  if (!campaign) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        {ErrorBar || (
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <RefreshCw className="h-4 w-4 animate-spin" /> Loading campaign…
          </div>
        )}
      </div>
    );
  }

  // Strategist agent working
  if (busy === "strategy" || status === "planning") {
    return (
      <div className="max-w-6xl mx-auto space-y-6 pb-10">
        {Header}
        <RobotStage
          src="/robots/meta-loading.webp"
          pulse
          title="Your Meta strategist is planning the campaign"
          subtitle="Reading your creatives, researching the market and checking real audiences with Meta."
        >
          <div className="max-w-sm mx-auto space-y-2 text-left">
            {PLANNING_STEPS.map((s, i) => (
              <div key={s} className={`flex items-center gap-2.5 text-xs transition-all ${i <= planStep ? "text-slate-200" : "text-slate-600"}`}>
                {i < planStep ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : i === planStep ? (
                  <RefreshCw className="h-4 w-4 text-indigo-300 animate-spin" />
                ) : (
                  <span className="h-4 w-4 rounded-full border border-slate-700" />
                )}
                {s}
              </div>
            ))}
          </div>
        </RobotStage>
      </div>
    );
  }

  // Failed before a plan exists
  if (!campaign.strategy) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        {Header}
        {ErrorBar}
        <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-10 text-center space-y-4">
          <AlertTriangle className="h-8 w-8 text-amber-400 mx-auto" />
          <p className="text-sm text-white font-semibold">The strategist could not finish</p>
          <p className="text-xs text-slate-400">{campaign.error || "Try again in a moment."}</p>
          <button onClick={() => runStrategy()} className="px-5 py-2.5 rounded-xl bg-indigo-600 text-white text-xs font-semibold">
            Try again
          </button>
        </div>
      </div>
    );
  }

  const strategy = campaign.strategy;
  const ig = campaign.instagram;
  const meta = campaign.meta;
  const handle = campaign.connection?.ig_username || conn?.selection?.ig_username;

  // ---------------------------------------------------------------- progress (after approval)
  if (inProgress) {
    let stageView: React.ReactNode;
    if (status === "failed") {
      stageView = (
        <div className="rounded-3xl border border-rose-800/50 bg-[#0d1322] p-10 text-center space-y-4">
          <AlertTriangle className="h-10 w-10 text-rose-400 mx-auto" />
          <h3 className="text-lg font-bold text-white">Something needs your attention</h3>
          <p className="text-xs text-slate-300 max-w-lg mx-auto">{campaign.error}</p>
          <p className="text-[11px] text-slate-500">Retrying is safe: anything already posted will not be posted twice.</p>
          <button onClick={approve} disabled={busy === "approve"} className="px-5 py-2.5 rounded-xl bg-indigo-600 text-white text-xs font-semibold">
            {busy === "approve" ? "Retrying…" : "Retry"}
          </button>
        </div>
      );
    } else if (status === "approved" || status === "publishing") {
      stageView = (
        <RobotStage src="/robot_loading.png" pulse title="Posting to Instagram…" subtitle={handle ? `Publishing to @${handle}` : undefined} />
      );
    } else if (status === "published" || status === "building_ads" || status === "launching") {
      stageView = (
        <RobotStage
          src="/robots/meta-loading.webp"
          pulse
          title={status === "launching" ? "Turning your ads on…" : "Setting up your Meta campaign…"}
          subtitle={
            status === "launching"
              ? "Activating ads, ad set and campaign in your ad account."
              : "Creating the campaign, ad set and ads in your ad account. Everything stays paused until you launch."
          }
        >
          {ig?.permalink && (
            <a href={ig.permalink} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs text-pink-300 hover:underline">
              <Instagram className="h-3.5 w-3.5" /> Posted to Instagram · view post <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </RobotStage>
      );
    } else if (status === "ads_ready") {
      stageView = (
        <RobotStage
          src="/robots/insta-done.webp"
          title={ig ? "Posted on Instagram! 🎉" : "Your ads are ready"}
          subtitle="Your Meta campaign is built and paused. Review the spend below and launch when you're ready."
        >
          <div className="max-w-md mx-auto space-y-4">
            {ig?.permalink && (
              <a href={ig.permalink} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs text-pink-300 hover:underline">
                View post{handle ? ` on @${handle}` : ""} <ExternalLink className="h-3 w-3" />
              </a>
            )}
            <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4 grid grid-cols-3 gap-3 text-left">
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wide">Daily</p>
                <p className="text-sm font-bold text-white">{sym}{plan.daily_budget}</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wide">Duration</p>
                <p className="text-sm font-bold text-white">{plan.duration_days} days</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wide">Max total</p>
                <p className="text-sm font-bold text-white">{sym}{Math.round(plan.daily_budget * plan.duration_days).toLocaleString()}</p>
              </div>
            </div>
            <button
              onClick={launch}
              disabled={busy === "launch"}
              className="w-full px-6 py-3 rounded-xl bg-gradient-to-r from-[#1877F2] via-indigo-600 to-purple-600 text-white text-sm font-semibold shadow-lg shadow-indigo-700/40 flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <Rocket className="h-4 w-4" /> {busy === "launch" ? "Launching…" : "Launch ads"}
            </button>
            <p className="text-[11px] text-slate-500">
              Spend starts at {new Date(plan.start_time_iso).toLocaleString()} ({plan.timezone}). You can pause anytime in Meta Ads Manager.
            </p>
          </div>
        </RobotStage>
      );
    } else {
      // live or done
      stageView = (
        <RobotStage
          src="/robots/all-done.webp"
          title="All done! Your campaign is live 🚀"
          subtitle={status === "live" ? "Posted on Instagram and your Meta ads are running." : "Your post is live on Instagram."}
        >
          <div className="flex flex-wrap items-center justify-center gap-3">
            {ig?.permalink && (
              <a href={ig.permalink} target="_blank" rel="noreferrer" className="px-4 py-2 rounded-xl border border-pink-500/40 text-pink-200 text-xs font-semibold inline-flex items-center gap-1.5">
                <Instagram className="h-3.5 w-3.5" /> View post
              </a>
            )}
            {meta?.campaign_id && !meta.mock && (
              <a
                href={`https://adsmanager.facebook.com/adsmanager/manage/campaigns?selected_campaign_ids=${meta.campaign_id}`}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 rounded-xl border border-blue-500/40 text-blue-200 text-xs font-semibold inline-flex items-center gap-1.5"
              >
                <BarChart3 className="h-3.5 w-3.5" /> Open in Ads Manager
              </a>
            )}
            <button onClick={onBack} className="px-4 py-2 rounded-xl bg-slate-800 text-white text-xs font-semibold">
              Back to dashboard
            </button>
          </div>
          {(ig?.mock || meta?.mock) && (
            <p className="text-[11px] text-amber-300 mt-4">Demo mode: nothing was actually posted or spent.</p>
          )}
        </RobotStage>
      );
    }

    const steps = [
      { key: "approve", label: "Approved", icon: ShieldCheck },
      { key: "publish", label: "Posted to Instagram", icon: Instagram, skip: !campaign.approval?.publish_instagram },
      { key: "build_ads", label: "Meta campaign built (paused)", icon: Megaphone, skip: !campaign.approval?.create_ads },
      { key: "launch", label: "Ads launched", icon: Rocket, skip: !campaign.approval?.create_ads },
    ];
    return (
      <div className="max-w-6xl mx-auto space-y-6 pb-10">
        {Header}
        {ErrorBar}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-8">{stageView}</div>
          <div className="lg:col-span-4 rounded-2xl border border-slate-800 bg-[#0d1322] p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">Progress</h3>
            {steps
              .filter((s) => !s.skip)
              .map((s) => {
                const st = campaign.steps?.[s.key];
                const Icon = s.icon;
                return (
                  <div key={s.key} className="flex items-center gap-3">
                    <span
                      className={`h-8 w-8 rounded-xl flex items-center justify-center ${
                        st === "done"
                          ? "bg-emerald-500/15 text-emerald-300"
                          : st === "running"
                          ? "bg-indigo-500/15 text-indigo-300"
                          : st === "failed"
                          ? "bg-rose-500/15 text-rose-300"
                          : "bg-slate-800 text-slate-500"
                      }`}
                    >
                      {st === "running" ? <RefreshCw className="h-4 w-4 animate-spin" /> : st === "done" ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                    </span>
                    <span className={`text-xs ${st === "done" ? "text-slate-200" : "text-slate-500"}`}>{s.label}</span>
                  </div>
                );
              })}
            <div className="pt-3 border-t border-slate-800">
              <CreativeThumbs size="sm" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!draft) return null;

  // ---------------------------------------------------------------- review stage
  if (stage === "review") {
    const aud = plan.audience;
    const where = [...aud.cities.map((c: any) => c.name), ...aud.countries].join(", ");
    return (
      <div className="max-w-6xl mx-auto space-y-6 pb-32">
        {Header}
        {ErrorBar}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7 space-y-4">
            <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-5 space-y-4">
              <h3 className="text-sm font-semibold text-white">What happens when you approve</h3>
              <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-800 bg-slate-900/50 cursor-pointer">
                <input type="checkbox" checked={doPublish} onChange={(e) => setDoPublish(e.target.checked)} className="mt-0.5 accent-pink-500" />
                <div>
                  <p className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Instagram className="h-3.5 w-3.5 text-pink-400" /> Post {campaign.creatives.length > 1 ? `a carousel of ${campaign.creatives.length}` : "the creative"} to{" "}
                    {handle ? `@${handle}` : "Instagram"}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1 whitespace-pre-line line-clamp-3">{draft.caption}</p>
                </div>
              </label>
              <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-800 bg-slate-900/50 cursor-pointer">
                <input type="checkbox" checked={doAds} onChange={(e) => setDoAds(e.target.checked)} className="mt-0.5 accent-blue-500" />
                <div>
                  <p className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Megaphone className="h-3.5 w-3.5 text-blue-400" /> Build the Meta campaign (paused, no spend yet)
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    {OBJECTIVE_LABELS[plan.objective]} · {sym}
                    {plan.daily_budget}/day × {plan.duration_days} days · {where} · {aud.age_min}-{aud.age_max}
                    {aud.genders !== "all" ? ` · ${aud.genders}` : ""} · {plan.ads.length} ad{plan.ads.length > 1 ? "s" : ""}
                    {plan.delivery === "boost_instagram_post" ? " · promotes your Instagram post" : ""}
                  </p>
                </div>
              </label>
              <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 flex items-start gap-3">
                <Rocket className="h-4 w-4 text-purple-300 mt-0.5" />
                <p className="text-[11px] text-slate-400">
                  Ads only start spending after you press <span className="text-white font-semibold">Launch</span> on the next screen.
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400" /> Pre-launch checks
              </h3>
              {[...(strategy.warnings || []), ...(strategy.edit_warnings || [])].length === 0 ? (
                <p className="text-xs text-emerald-300 flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5" /> No issues found
                </p>
              ) : (
                [...(strategy.warnings || []), ...(strategy.edit_warnings || [])].map((w: string, i: number) => (
                  <p key={i} className="text-[11px] text-amber-200 flex gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400" /> {w}
                  </p>
                ))
              )}
            </div>
            {(doPublish || doAds) && <MetaConnectCard compact onChange={setConn} />}
          </div>
          <div className="lg:col-span-5 rounded-2xl border border-slate-800 bg-[#0d1322] p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">Creatives</h3>
            <CreativeThumbs />
            {plan.ads.map((a: any) => (
              <div key={a.creative_index} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                <p className="text-[10px] text-slate-500 mb-1">Ad for creative #{a.creative_index + 1}</p>
                <p className="text-xs text-slate-200 line-clamp-3">{a.primary_text}</p>
                <div className="mt-2 flex items-center justify-between">
                  <p className="text-xs font-semibold text-white truncate">{a.headline}</p>
                  <span className="text-[10px] px-2 py-1 rounded-lg bg-slate-800 text-slate-200 shrink-0">{CTA_LABELS[a.cta] || a.cta}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="fixed bottom-4 left-4 sm:left-72 right-4 sm:right-8 z-40 bg-[#090d1a]/95 backdrop-blur-xl border border-slate-800/90 rounded-2xl p-4 shadow-2xl flex items-center justify-between gap-3">
          <button onClick={() => setStage("settings")} className="px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-2">
            <ArrowLeft className="h-4 w-4" /> Back to settings
          </button>
          <button
            onClick={approve}
            disabled={busy === "approve" || (!doPublish && !doAds) || (conn?.mode !== "mock" && !connReady)}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 flex items-center gap-2 disabled:opacity-50"
          >
            {busy === "approve" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            Approve & {doPublish ? "post" : "build ads"}
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------- settings stage
  const aud = plan.audience;
  const r = strategy.rationale || {};
  const est = strategy.estimate || {};
  const inputCls =
    "w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors";

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-32">
      {Header}
      {ErrorBar}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: campaign details */}
        <div className="lg:col-span-7 space-y-5">
          <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-5 sm:p-6 space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Target className="h-4 w-4 text-indigo-400" /> Campaign details
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                Advantage+ campaign
              </span>
            </div>

            <Field label="Campaign name" icon={Megaphone}>
              <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className={inputCls} maxLength={120} />
            </Field>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Website link (optional)" icon={Globe}>
                <input
                  value={draft.website_url}
                  onChange={(e) => setDraft({ ...draft, website_url: e.target.value })}
                  placeholder="https://yourstore.com/product"
                  className={inputCls}
                />
              </Field>
              <Field label="Objective" icon={Target}>
                <select value={draft.objective} onChange={(e) => setDraft({ ...draft, objective: e.target.value })} className={inputCls}>
                  {Array.from(new Set([...allowedObjectives, draft.objective])).map((o) => (
                    <option key={o} value={o} disabled={!allowedObjectives.includes(o)}>
                      {OBJECTIVE_LABELS[o]}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <Why text={r.objective} />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label={`Daily budget (${currency})`} icon={Wallet}>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs text-slate-400">{sym}</span>
                  <input
                    type="number"
                    min={1}
                    value={draft.daily_budget}
                    onChange={(e) => setDraft({ ...draft, daily_budget: e.target.value })}
                    className={`${inputCls} pl-8`}
                  />
                </div>
                <p className="text-[11px] text-emerald-400">
                  Max total {sym}
                  {Math.round(totalSpend).toLocaleString()} over {draft.duration_days} days
                </p>
              </Field>
              <Field label="Start" icon={Calendar}>
                <input
                  type="datetime-local"
                  value={draft.start_local}
                  onChange={(e) => setDraft({ ...draft, start_local: e.target.value })}
                  className={inputCls}
                />
                <p className="text-[11px] text-slate-500">{plan.timezone}</p>
              </Field>
            </div>
            <Why text={r.budget} />

            <Field label="Duration" icon={Calendar}>
              <div className="flex flex-wrap gap-2">
                {[3, 7, 14, 30].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDraft({ ...draft, duration_days: d })}
                    className={`px-3.5 py-2 rounded-xl text-xs font-medium border transition-all ${
                      Number(draft.duration_days) === d
                        ? "bg-indigo-600/30 border-indigo-500 text-white"
                        : "border-slate-700 text-slate-400 hover:text-white"
                    }`}
                  >
                    {d} days
                  </button>
                ))}
                <input
                  type="number"
                  min={1}
                  max={90}
                  value={draft.duration_days}
                  onChange={(e) => setDraft({ ...draft, duration_days: e.target.value })}
                  className="w-20 px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white"
                />
              </div>
            </Field>
            <Why text={r.schedule} />
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-5 sm:p-6 space-y-5">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Users className="h-4 w-4 text-cyan-400" /> Audience
            </h3>
            <Field label="Locations" icon={MapPin}>
              <div className="flex flex-wrap gap-2">
                {[...aud.cities.map((c: any) => `${c.name}${c.region ? `, ${c.region}` : ""}`), ...aud.countries].map((l: string) => (
                  <span key={l} className="px-2.5 py-1 rounded-lg bg-slate-800 text-xs text-slate-200">
                    {l}
                  </span>
                ))}
              </div>
            </Field>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <Field label="Age from" icon={Users}>
                <input type="number" min={18} max={65} disabled={special} value={draft.age_min} onChange={(e) => setDraft({ ...draft, age_min: e.target.value })} className={inputCls} />
              </Field>
              <Field label="Age to" icon={Users}>
                <input type="number" min={18} max={65} disabled={special} value={draft.age_max} onChange={(e) => setDraft({ ...draft, age_max: e.target.value })} className={inputCls} />
              </Field>
              <Field label="Gender" icon={Users}>
                <select disabled={special} value={draft.genders} onChange={(e) => setDraft({ ...draft, genders: e.target.value })} className={inputCls}>
                  <option value="all">All</option>
                  <option value="female">Women</option>
                  <option value="male">Men</option>
                </select>
              </Field>
            </div>
            <Field label="Interest signals (verified with Meta)" icon={Sparkles}>
              <div className="flex flex-wrap gap-2">
                {aud.interests.filter((i: any) => !draft.removed.includes(i.id)).length === 0 && (
                  <span className="text-[11px] text-slate-500">Broad audience (Meta finds the right people)</span>
                )}
                {aud.interests
                  .filter((i: any) => !draft.removed.includes(i.id))
                  .map((i: any) => (
                    <span key={i.id} className="pl-2.5 pr-1.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-xs text-cyan-100 flex items-center gap-1.5">
                      {i.name}
                      {i.size_lower ? <span className="text-[10px] text-cyan-300/70">{formatCompact(i.size_lower)}+</span> : null}
                      <button type="button" onClick={() => setDraft({ ...draft, removed: [...draft.removed, i.id] })} className="text-cyan-300/60 hover:text-rose-300">
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
              </div>
              {aud.advantage_audience && (
                <p className="text-[11px] text-slate-500 mt-1">Advantage+ audience is on: interests guide Meta, which can reach beyond them when it finds better results.</p>
              )}
            </Field>
            <Why text={r.audience} />
          </div>
        </div>

        {/* Right: creatives, copy, insights */}
        <div className="lg:col-span-5 space-y-5">
          <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Selected creatives ({campaign.creatives.length})</h3>
              <span className="text-[10px] text-slate-500">{plan.delivery === "boost_instagram_post" ? "Promotes your Instagram post" : "Link ads"}</span>
            </div>
            <CreativeThumbs />
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">Ad copy</h3>
            {draft.ads.map((a: any, i: number) => (
              <div key={a.creative_index} className="space-y-2 rounded-xl border border-slate-800 bg-slate-900/50 p-3">
                <p className="text-[10px] text-slate-500">Creative #{a.creative_index + 1}</p>
                <textarea
                  rows={3}
                  value={a.primary_text}
                  onChange={(e) => {
                    const ads = [...draft.ads];
                    ads[i] = { ...a, primary_text: e.target.value };
                    setDraft({ ...draft, ads });
                  }}
                  className={`${inputCls} resize-none`}
                />
                <div className="flex gap-2">
                  <input
                    value={a.headline}
                    onChange={(e) => {
                      const ads = [...draft.ads];
                      ads[i] = { ...a, headline: e.target.value };
                      setDraft({ ...draft, ads });
                    }}
                    className={inputCls}
                    maxLength={60}
                  />
                  <span className="px-3 py-2 rounded-xl bg-slate-800 text-[11px] text-slate-200 whitespace-nowrap flex items-center">
                    {CTA_LABELS[a.cta] || a.cta}
                  </span>
                </div>
              </div>
            ))}
            <Field label="Instagram caption" icon={Instagram}>
              <textarea rows={4} value={draft.caption} onChange={(e) => setDraft({ ...draft, caption: e.target.value })} className={`${inputCls} resize-none`} maxLength={2200} />
            </Field>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-5 space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-400" /> Estimated audience
            </h3>
            {est.audience_lower ? (
              <>
                <p className="text-2xl font-bold text-white">
                  {formatCompact(est.audience_lower)} – {formatCompact(est.audience_upper)}
                  <span className="text-xs font-normal text-slate-400"> people</span>
                </p>
                <p className="text-[11px] text-slate-500">Meta's own estimate for this targeting{est.mock ? " (demo data)" : ""}. Estimates are not guarantees.</p>
              </>
            ) : (
              <p className="text-[11px] text-slate-500">Connect Instagram & Meta to get Meta's audience estimate.</p>
            )}
            {(strategy.kpis || []).length > 0 && (
              <div className="pt-2 space-y-1.5">
                <p className="text-[11px] font-semibold text-slate-300">What we'll watch</p>
                {strategy.kpis.map((k: any, i: number) => (
                  <p key={i} className="text-[11px] text-slate-400">
                    <span className="text-slate-200">{k.metric}:</span> {k.expectation}
                  </p>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-5 space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-amber-300" /> Market research
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">{strategy.research?.summary}</p>
            {(strategy.research?.sources || []).slice(0, 5).map((s: any, i: number) => (
              <a key={i} href={s.url} target="_blank" rel="noreferrer" className="block text-[11px] text-indigo-300 hover:underline truncate">
                {s.title || s.url}
              </a>
            ))}
            {strategy.research?.web_search === "not configured" && (
              <p className="text-[11px] text-slate-500">Web research is off: add TAVILY_API_KEY (free tier) for competitor & trend research.</p>
            )}
            {[...(strategy.warnings || []), ...(strategy.risks || [])].length > 0 && (
              <div className="pt-2 space-y-1.5">
                {(strategy.warnings || []).map((w: string, i: number) => (
                  <p key={`w${i}`} className="text-[11px] text-amber-200 flex gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400" /> {w}
                  </p>
                ))}
                {(strategy.risks || []).map((w: string, i: number) => (
                  <p key={`r${i}`} className="text-[11px] text-slate-400">• {w}</p>
                ))}
              </div>
            )}
          </div>

          <MetaConnectCard compact onChange={setConn} />

          <div className="rounded-2xl border border-indigo-500/30 bg-indigo-950/20 p-4 space-y-2">
            <p className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-indigo-300" /> Ask the strategist to change the plan
            </p>
            <div className="flex gap-2">
              <input
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="e.g. focus on Bangalore and Pune, women 25-40"
                className={inputCls}
                maxLength={500}
              />
              <button
                onClick={() => runStrategy(instruction)}
                disabled={!instruction.trim()}
                className="px-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-40 whitespace-nowrap"
              >
                Re-plan
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="fixed bottom-4 left-4 sm:left-72 right-4 sm:right-8 z-40 bg-[#090d1a]/95 backdrop-blur-xl border border-slate-800/90 rounded-2xl p-4 shadow-2xl flex items-center justify-between gap-3">
        <button onClick={onBack} className="px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-2">
          <ArrowLeft className="h-4 w-4" /> Back to creatives
        </button>
        <button
          onClick={async () => {
            if (await savePlan()) setStage("review");
          }}
          disabled={busy === "save"}
          className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 flex items-center gap-2 disabled:opacity-60"
        >
          {busy === "save" ? "Saving…" : "Save settings & continue"} <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
