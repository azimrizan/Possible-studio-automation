"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Camera,
  Check,
  Copy,
  Download,
  Film,
  Highlighter,
  LayoutTemplate,
  Plus,
  RefreshCw,
  Scissors,
  Sparkles,
  Type,
  Upload,
  Wand2,
  X,
  ZoomIn,
  Trash2,
} from "lucide-react";
import { studioFetch } from "@/lib/studio";

const ANGLES = [
  { key: "left_side", label: "Left side" },
  { key: "right_side", label: "Right side" },
  { key: "close_profile", label: "Close profile" },
  { key: "from_above", label: "From above" },
  { key: "front", label: "Front" },
  { key: "other", label: "Other" },
];
const BUSY = new Set(["planning", "rendering"]);
type WordMode = "cut" | "highlight" | "zoom" | "title";
const LANGUAGES = [
  { key: "en", label: "English" },
  { key: "ml", label: "Malayalam" },
  { key: "hi", label: "Hindi" },
  { key: "ta", label: "Tamil" },
  { key: "te", label: "Telugu" },
  { key: "kn", label: "Kannada" },
  { key: "ar", label: "Arabic" },
  { key: "other", label: "Other" },
];
const MODES = [
  {
    key: "basic",
    title: "Basic: Claude edit",
    blurb: "Cuts, captions, zooms, graphics, text behind your head, sound effects, 3 hooks.",
    meta: "~5-10 min · about ₹85-250 per video (Claude only)",
  },
  {
    key: "advanced",
    title: "Advanced: Claude + AI cameras",
    blurb: "Everything in Basic, plus new camera angles, a drone shot and a new room (coming next).",
    meta: "~20-40 min · about ₹1,000-2,100 per video",
  },
];
const BEAT_LABELS: Record<string, string> = {
  statement_card: "Statement card",
  counter: "Number counter",
  list: "List",
  before_after: "Before / after",
  cta_comment: "Comment CTA",
  backtext: "Big word behind you",
};

function Card({ title, icon: Icon, children, right }: { title: string; icon: any; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-neutral-800 bg-[#131313] p-5 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Icon className="h-4 w-4 text-brand" /> {title}
        </h3>
        {right}
      </div>
      {children}
    </div>
  );
}

function FilePick({ accept, label, onPick, disabled }: { accept: string; label: string; onPick: (f: File) => void; disabled?: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <>
      <button
        type="button"
        disabled={disabled}
        onClick={() => ref.current?.click()}
        className="px-3.5 py-2 rounded-xl border border-dashed border-neutral-700 text-xs text-neutral-300 hover:border-brand/60 hover:text-white inline-flex items-center gap-1.5 disabled:opacity-50"
      >
        <Plus className="h-3.5 w-3.5" /> {label}
      </button>
      <input
        ref={ref}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onPick(f);
          e.target.value = "";
        }}
      />
    </>
  );
}

function ProjectList({ onOpen }: { onOpen: (id: string) => void }) {
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [picking, setPicking] = useState(false);
  const [language, setLanguage] = useState("en");
  useEffect(() => {
    studioFetch("/reels").then(setItems).catch((e) => setError(e.message));
  }, []);
  const create = async (mode: string) => {
    try {
      const r = await studioFetch("/reels", { method: "POST", body: JSON.stringify({ name: `Video ${new Date().toLocaleDateString()}`, mode, language }) });
      onOpen(r.id);
    } catch (e: any) {
      setError(e.message);
    }
  };
  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-white">AI Video Edit</h2>
          <p className="text-xs text-neutral-400 mt-1 max-w-xl">
            Upload one raw take from your phone. Claude cuts the pauses and mistakes, adds word-by-word subtitles and builds a version for each hook.
          </p>
        </div>
        <button onClick={() => setPicking((v) => !v)} className="px-4 py-2.5 rounded-xl bg-brand hover:bg-brand-hover text-brand-ink text-xs font-semibold inline-flex items-center gap-1.5">
          <Plus className="h-4 w-4" /> New video
        </button>
      </div>
      {picking && (
        <div className="rounded-2xl border border-neutral-800 bg-[#131313] p-5 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm font-semibold text-white">How should we edit it?</p>
            <label className="text-[11px] text-neutral-400 flex items-center gap-2 ml-auto">
              Spoken language
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className="bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-1.5">
                {LANGUAGES.map((l) => (
                  <option key={l.key} value={l.key}>{l.label}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {MODES.map((m) => (
              <button key={m.key} onClick={() => create(m.key)} className="text-left rounded-xl border border-neutral-800 hover:border-brand/60 bg-neutral-900/50 p-4 space-y-1.5">
                <p className="text-sm font-semibold text-white">{m.title}</p>
                <p className="text-xs text-neutral-300">{m.blurb}</p>
                <p className="text-[11px] text-neutral-500">{m.meta}</p>
              </button>
            ))}
          </div>
        </div>
      )}
      {error && <p className="text-xs text-rose-300">{error}</p>}
      {items && items.length === 0 && <p className="text-xs text-neutral-500">No videos yet.</p>}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        {items?.map((r) => (
          <button key={r.id} onClick={() => onOpen(r.id)} className="text-left rounded-xl border border-neutral-800 bg-[#131313] overflow-hidden hover:border-brand/50">
            <div className="aspect-[9/16] bg-neutral-900 flex items-center justify-center">
              {r.cover_url ? <img src={r.cover_url} alt="" className="h-full w-full object-cover" /> : <Film className="h-6 w-6 text-neutral-600" />}
            </div>
            <div className="p-2.5">
              <p className="text-xs text-white truncate">{r.name}</p>
              <p className="text-[10px] text-neutral-500 capitalize">{r.mode || "basic"} · {r.status}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ReelEditStudio() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [reel, setReel] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string>("");
  const [instruction, setInstruction] = useState("");
  const [glossary, setGlossary] = useState("");
  const [plan, setPlan] = useState<any>(null);
  const [dirty, setDirty] = useState(false);
  const [mode, setMode] = useState<WordMode>("cut");
  const [refAngle, setRefAngle] = useState("left_side");

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      const r = await studioFetch(`/reels/${projectId}`);
      setReel(r);
      if (!dirty) setPlan(r.plan);
      if (r.instruction && !instruction) setInstruction(r.instruction);
      if (r.glossary && !glossary) setGlossary(r.glossary);
    } catch (e: any) {
      setError(e.message);
    }
  }, [projectId, dirty, instruction, glossary]);

  useEffect(() => {
    setReel(null);
    setPlan(null);
    setDirty(false);
    setInstruction("");
    setGlossary("");
    if (projectId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // Poll while the server is planning or rendering.
  useEffect(() => {
    if (!reel || !BUSY.has(reel.status)) return;
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [reel, load]);

  if (!projectId) return <ProjectList onOpen={setProjectId} />;
  if (!reel) {
    return (
      <p className="text-xs text-neutral-400 flex items-center gap-2">
        <RefreshCw className="h-4 w-4 animate-spin" /> Loading…
      </p>
    );
  }

  const busy = BUSY.has(reel.status);
  const files = reel.files;
  const modes = reel.modes || {};

  const upload = async (role: string, file: File, angle?: string) => {
    setError(null);
    setUploading(role === "reference" ? "photo" : role === "main" ? "main take" : "hook take");
    try {
      const form = new FormData();
      form.append("role", role);
      form.append("angle", angle || "other");
      form.append("file", file);
      const r = await studioFetch(`/reels/${projectId}/files`, { method: "POST", body: form });
      setReel(r);
      setPlan(r.plan);
      setDirty(false);
    } catch (e: any) {
      setError(`${file.name}: ${e.message}`);
    } finally {
      setUploading("");
    }
  };

  const removeFile = async (assetId: string) => {
    try {
      const r = await studioFetch(`/reels/${projectId}/files/${assetId}`, { method: "DELETE" });
      setReel(r);
      setPlan(r.plan);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const patchSettings = async (patch: any) => {
    try {
      setReel(await studioFetch(`/reels/${projectId}`, { method: "PATCH", body: JSON.stringify(patch) }));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const startPlan = async () => {
    setError(null);
    try {
      setDirty(false);
      setReel(await studioFetch(`/reels/${projectId}/plan`, { method: "POST", body: JSON.stringify({ instruction, glossary }) }));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const savePlan = async () => {
    const body = {
      remove_word_ids: plan.remove_word_ids,
      emphasis_word_ids: plan.emphasis_word_ids,
      punch_word_ids: plan.punch_word_ids || [],
      corrections: plan.corrections || [],
      beats: plan.beats || [],
      grade: plan.grade || "natural",
      hooks: plan.hooks,
      caption: plan.caption,
      hashtags: plan.hashtags,
      title_text: plan.title_text,
      title_at_word_id: plan.title_at_word_id,
      subtitle_position: plan.subtitle_position,
    };
    const r = await studioFetch(`/reels/${projectId}/plan`, { method: "PUT", body: JSON.stringify(body) });
    setReel(r);
    setPlan(r.plan);
    setDirty(false);
    return r;
  };

  const render = async () => {
    setError(null);
    try {
      if (dirty) await savePlan();
      setReel(await studioFetch(`/reels/${projectId}/render`, { method: "POST" }));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const update = (patch: any) => {
    setPlan((p: any) => ({ ...p, ...patch }));
    setDirty(true);
  };

  const toggleWord = (id: string) => {
    if (!plan) return;
    if (mode === "title") return update({ title_at_word_id: plan.title_at_word_id === id ? "" : id });
    const key = mode === "cut" ? "remove_word_ids" : mode === "zoom" ? "punch_word_ids" : "emphasis_word_ids";
    const set = new Set<string>(plan[key] || []);
    set.has(id) ? set.delete(id) : set.add(id);
    update({ [key]: Array.from(set) });
  };

  const sourceLabel = (name: string) => (name === "main" ? "Main take" : `Hook take ${name.replace("hook", "")}`);
  const hookSources = ["main", ...files.hooks.map((_: any, i: number) => `hook${i + 1}`)];

  return (
    <div className="space-y-6 pb-10">
      <div className="flex items-center gap-3">
        <button onClick={() => setProjectId(null)} className="h-9 w-9 rounded-full border border-neutral-700 text-neutral-300 hover:bg-neutral-800 flex items-center justify-center" title="All videos">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <h2 className="text-lg font-bold text-white">{reel.name}</h2>
          <p className="text-[11px] text-neutral-500 capitalize">{reel.status}</p>
        </div>
        <div className="ml-auto flex rounded-lg border border-neutral-800 p-0.5">
          {MODES.map((m) => (
            <button
              key={m.key}
              disabled={busy}
              onClick={() => patchSettings({ mode: m.key })}
              title={m.blurb}
              className={`px-3 py-1.5 text-[11px] rounded-md ${reel.mode === m.key ? "bg-neutral-800 text-white font-semibold" : "text-neutral-400 hover:text-white"}`}
            >
              {m.key === "basic" ? "Basic" : "Advanced"}
            </button>
          ))}
        </div>
      </div>

      {(modes.transcription === "demo" || modes.director === "demo") && (
        <div className="p-3 rounded-xl border border-amber-700/50 bg-amber-950/30 text-amber-200 text-xs flex gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>
            Demo mode:{" "}
            {modes.transcription === "demo" &&
              (reel.mode === "basic"
                ? "subtitles use placeholder words (install the free speech models: bash scripts/setup_reel_models.sh)"
                : "subtitles use placeholder words (add ELEVENLABS_API_KEY to .env, or install the free speech models)")}
            {modes.transcription === "demo" && modes.director === "demo" && "; "}
            {modes.director === "demo" && "the edit plan is rule-based (add ANTHROPIC_API_KEY to .env for Claude)"}. Restart the API after adding keys.
          </span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)}><X className="h-3.5 w-3.5" /></button>
        </div>
      )}
      {reel.status === "failed" && reel.error && (
        <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" /> {reel.error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ---------------- inputs ---------------- */}
        <div className="lg:col-span-5 space-y-6">
          <Card title="Your footage" icon={Film}>
            <div className="space-y-3">
              <p className="text-[11px] text-neutral-400">Main take: up to 3 minutes, phone on a tripod, microphone on.</p>
              {files.main ? (
                <div className="flex items-center gap-3">
                  <video src={files.main.url} className="h-24 aspect-[9/16] rounded-lg object-cover bg-black" muted />
                  <div className="text-xs text-neutral-300 flex-1 min-w-0">
                    <p className="truncate">{files.main.name || "Main take"}</p>
                    <p className="text-neutral-500">{files.main.duration.toFixed(1)}s</p>
                  </div>
                  <FilePick accept="video/*" label="Replace" disabled={busy || !!uploading} onPick={(f) => upload("main", f)} />
                </div>
              ) : (
                <FilePick accept="video/*" label="Upload main take" disabled={busy || !!uploading} onPick={(f) => upload("main", f)} />
              )}
            </div>
            <div className="space-y-2 pt-3 border-t border-neutral-800">
              <p className="text-[11px] text-neutral-400">Hook takes (optional, up to 3): short alternative openings. Each becomes its own version.</p>
              <div className="flex flex-wrap gap-2">
                {files.hooks.map((h: any, i: number) => (
                  <div key={h.asset_id} className="relative">
                    <video src={h.url} className="h-20 aspect-[9/16] rounded-lg object-cover bg-black" muted />
                    <span className="absolute bottom-1 left-1 text-[9px] font-bold px-1 rounded bg-black/70 text-white">Hook {i + 1}</span>
                    <button disabled={busy} onClick={() => removeFile(h.asset_id)} className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-neutral-800 text-neutral-300 flex items-center justify-center">
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
                {files.hooks.length < 3 && <FilePick accept="video/*" label="Add hook take" disabled={busy || !!uploading} onPick={(f) => upload("hook", f)} />}
              </div>
            </div>
            {uploading && (
              <p className="text-xs text-neutral-400 flex items-center gap-2">
                <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Uploading and preparing the {uploading}…
              </p>
            )}
          </Card>

          {reel.mode === "advanced" && (
          <Card title="Reference photos" icon={Camera}>
            <p className="text-[11px] text-neutral-400">
              Photos of you from other angles, in the same outfit. They're saved now and used for new camera angles and the drone shot in the next update.
            </p>
            <div className="flex flex-wrap gap-2">
              {files.references.map((x: any) => (
                <div key={x.asset_id} className="relative">
                  <img src={x.url} alt="" className="h-20 w-16 rounded-lg object-cover" />
                  <span className="absolute bottom-1 left-1 right-1 text-[8px] font-semibold px-1 rounded bg-black/70 text-white truncate">
                    {ANGLES.find((a) => a.key === x.angle)?.label}
                  </span>
                  <button onClick={() => removeFile(x.asset_id)} className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-neutral-800 text-neutral-300 flex items-center justify-center">
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
            {files.references.length < 6 && (
              <div className="flex items-center gap-2">
                <select value={refAngle} onChange={(e) => setRefAngle(e.target.value)} className="bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-2">
                  {ANGLES.map((a) => (
                    <option key={a.key} value={a.key}>{a.label}</option>
                  ))}
                </select>
                <FilePick accept="image/*" label="Add photo" disabled={!!uploading} onPick={(f) => upload("reference", f, refAngle)} />
              </div>
            )}
            <p className="text-[11px] text-amber-300/80">
              New camera angles, the drone shot and the room makeover arrive in the next update (they need fal.ai and Gemini credits). Until then Advanced renders the same edit as Basic, with ElevenLabs captions.
            </p>
          </Card>
          )}

          <Card title="What should Claude do?" icon={Wand2}>
            <label className="text-[11px] text-neutral-400 flex items-center gap-2">
              Spoken language
              <select
                value={reel.language}
                disabled={busy}
                onChange={(e) => patchSettings({ language: e.target.value })}
                className="bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-1.5"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.key} value={l.key}>{l.label}</option>
                ))}
              </select>
            </label>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              rows={3}
              maxLength={1500}
              placeholder="e.g. Keep it under 45 seconds, cut my mistakes, highlight the price. CTA keyword: PRICE."
              className="w-full bg-neutral-900 border border-neutral-800 rounded-xl text-xs text-neutral-200 p-3 focus:outline-none focus:border-brand/60"
            />
            <input
              value={glossary}
              onChange={(e) => setGlossary(e.target.value)}
              maxLength={1000}
              placeholder="Glossary (optional): brand and product names, prices, e.g. Possible Studio, ₹4,999, Kerala"
              className="w-full bg-neutral-900 border border-neutral-800 rounded-xl text-xs text-neutral-200 px-3 py-2.5 focus:outline-none focus:border-brand/60"
            />
            <p className="text-[10px] text-neutral-500">The glossary helps Claude spell names and numbers correctly in the captions.</p>
            <button
              onClick={startPlan}
              disabled={busy || !files.main || !!uploading}
              className="w-full px-4 py-2.5 rounded-xl bg-brand hover:bg-brand-hover text-brand-ink text-xs font-semibold inline-flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4" /> {reel.plan ? "Plan the edit again" : "Plan my edit"}
            </button>
          </Card>
        </div>

        {/* ---------------- plan / results ---------------- */}
        <div className="lg:col-span-7 space-y-6">
          {busy && (
            <div className="rounded-2xl border border-brand/25 bg-[#0b0b0b] p-8 text-center">
              <RefreshCw className="h-6 w-6 animate-spin text-brand mx-auto" />
              <p className="text-sm text-white font-semibold mt-3">{reel.status === "planning" ? "Planning your edit" : "Rendering your videos"}</p>
              <p className="text-xs text-neutral-400 mt-1">{reel.progress || "Working…"}</p>
            </div>
          )}

          {!busy && !plan && (
            <div className="rounded-2xl border border-dashed border-neutral-800 p-8 text-center text-xs text-neutral-500">
              Upload your main take and press "Plan my edit". You'll review Claude's plan before anything is rendered.
            </div>
          )}

          {!busy && plan && (
            <>
              {plan.notes && (
                <div className="rounded-2xl border border-brand/25 bg-brand/5 p-4 text-xs text-neutral-200 flex gap-2.5">
                  <Sparkles className="h-4 w-4 text-brand shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold text-white mb-1">
                      {plan.mode === "claude" ? "Claude's edit" : "Demo plan"}
                      {plan.reviewed && <span className="ml-2 text-[10px] font-normal text-brand">checked against test frames</span>}
                    </p>
                    <p className="whitespace-pre-line">{plan.notes}</p>
                  </div>
                </div>
              )}

              <Card
                title="Transcript"
                icon={Scissors}
                right={
                  <div className="flex rounded-lg border border-neutral-800 p-0.5">
                    {([
                      ["cut", "Cut", Scissors],
                      ["highlight", "Highlight", Highlighter],
                      ["zoom", "Zoom", ZoomIn],
                      ["title", "Title here", Type],
                    ] as const).map(([k, label, Icon]) => (
                      <button
                        key={k}
                        onClick={() => setMode(k)}
                        className={`px-2.5 py-1 text-[11px] rounded-md inline-flex items-center gap-1 ${mode === k ? "bg-neutral-800 text-white font-semibold" : "text-neutral-400 hover:text-white"}`}
                      >
                        <Icon className="h-3 w-3" /> {label}
                      </button>
                    ))}
                  </div>
                }
              >
                <p className="text-[11px] text-neutral-500">
                  Click words to change the edit. <span className="line-through text-rose-300">Struck words</span> are cut, <span className="text-amber-300 font-semibold">gold words</span> are highlighted, <span className="underline decoration-sky-400 decoration-2">underlined words</span> get a quick zoom. Pauses are tightened automatically.
                </p>
                {Object.entries(reel.transcript || {}).map(([name, words]: [string, any]) => (
                  <div key={name} className="space-y-1.5">
                    <p className="text-[11px] font-semibold text-neutral-400">{sourceLabel(name)}</p>
                    <div className="flex flex-wrap gap-x-1 gap-y-0.5 leading-relaxed max-h-64 overflow-y-auto">
                      {words.map((w: any) => {
                        const cut = plan.remove_word_ids.includes(w.id);
                        const hi = plan.emphasis_word_ids.includes(w.id);
                        const isTitle = plan.title_at_word_id === w.id;
                        const zoom = (plan.punch_word_ids || []).includes(w.id);
                        const fixed = (plan.corrections || []).find((c: any) => c.word_id === w.id);
                        return (
                          <button
                            key={w.id}
                            onClick={() => toggleWord(w.id)}
                            title={fixed ? `Heard "${w.text}", captioned as "${fixed.text}"` : undefined}
                            className={`text-xs px-0.5 rounded ${cut ? "line-through text-rose-300/80" : hi ? "text-amber-300 font-semibold" : "text-neutral-200"} ${isTitle ? "ring-1 ring-brand" : ""} ${zoom ? "underline decoration-sky-400 decoration-2" : ""} ${fixed ? "italic" : ""} hover:bg-neutral-800`}
                          >
                            {fixed ? fixed.text : w.text}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-neutral-800">
                  <label className="text-[11px] text-neutral-400 space-y-1">
                    <span>On-screen title (appears at the ringed word)</span>
                    <input value={plan.title_text} maxLength={60} onChange={(e) => update({ title_text: e.target.value })} placeholder="None" className="w-full bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2.5 py-2" />
                  </label>
                  <label className="text-[11px] text-neutral-400 space-y-1">
                    <span>Subtitle position</span>
                    <select value={plan.subtitle_position} onChange={(e) => update({ subtitle_position: e.target.value })} className="w-full bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-2">
                      <option value="upper">Upper</option>
                      <option value="middle">Middle</option>
                      <option value="lower">Lower</option>
                    </select>
                  </label>
                  <label className="text-[11px] text-neutral-400 space-y-1">
                    <span>Colour</span>
                    <select value={plan.grade || "natural"} onChange={(e) => update({ grade: e.target.value })} className="w-full bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-2">
                      <option value="none">Original</option>
                      <option value="natural">Natural</option>
                      <option value="cinematic">Cinematic</option>
                    </select>
                  </label>
                </div>
              </Card>

              <Card title="Graphics" icon={LayoutTemplate}>
                {(plan.beats || []).length === 0 && <p className="text-[11px] text-neutral-500">No graphics in this edit.</p>}
                {(plan.beats || []).map((b: any, i: number) => {
                  const setBeat = (patch: any) => update({ beats: plan.beats.map((x: any, j: number) => (j === i ? { ...x, ...patch } : x)) });
                  const words = (reel.transcript?.main || []) as any[];
                  const at = (id: string) => words.find((w) => w.id === id)?.text || "?";
                  return (
                    <div key={i} className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-3 space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold text-white">{BEAT_LABELS[b.type] || b.type}</span>
                        <span className="text-[10px] text-neutral-500 truncate">
                          on "{at(b.start_word_id)}" … "{at(b.end_word_id)}"
                        </span>
                        <button onClick={() => update({ beats: plan.beats.filter((_: any, j: number) => j !== i) })} className="ml-auto text-neutral-500 hover:text-rose-300" title="Remove">
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      {b.type === "list" ? (
                        <input
                          value={b.items.map((it: any) => it.text).join(", ")}
                          onChange={(e) => setBeat({ items: e.target.value.split(",").map((t, k) => ({ text: t.trim(), at_word_id: b.items[k]?.at_word_id || b.start_word_id })).filter((it) => it.text) })}
                          className="w-full bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2.5 py-2"
                          placeholder="Items, comma separated"
                        />
                      ) : b.type === "counter" ? (
                        <div className="grid grid-cols-4 gap-2">
                          <input value={b.prefix} onChange={(e) => setBeat({ prefix: e.target.value })} placeholder="₹" className="bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-2" />
                          <input type="number" value={b.value} onChange={(e) => setBeat({ value: Number(e.target.value) })} className="bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-2" />
                          <input value={b.suffix} onChange={(e) => setBeat({ suffix: e.target.value })} placeholder="K+" className="bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-2" />
                          <input value={b.text} onChange={(e) => setBeat({ text: e.target.value })} placeholder="label" className="bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-2" />
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          <input value={b.type === "cta_comment" ? b.keyword : b.text} onChange={(e) => setBeat(b.type === "cta_comment" ? { keyword: e.target.value } : { text: e.target.value })} className="bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2.5 py-2" />
                          {(b.type === "statement_card" || b.type === "before_after" || b.type === "cta_comment") && (
                            <input
                              value={b.type === "cta_comment" ? b.text : b.sub}
                              onChange={(e) => setBeat(b.type === "cta_comment" ? { text: e.target.value } : { sub: e.target.value })}
                              placeholder={b.type === "before_after" ? "after" : b.type === "cta_comment" ? "prompt line" : "small line"}
                              className="bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2.5 py-2"
                            />
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </Card>

              <Card title="Hooks: one video each" icon={Type}>
                {plan.hooks.map((h: any, i: number) => (
                  <div key={i} className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center">
                    <select
                      value={h.source}
                      onChange={(e) => update({ hooks: plan.hooks.map((x: any, j: number) => (j === i ? { ...x, source: e.target.value } : x)) })}
                      className="sm:col-span-3 bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2 py-2"
                    >
                      {hookSources.map((s) => (
                        <option key={s} value={s}>{s === "main" ? "Starts with main take" : sourceLabel(s)}</option>
                      ))}
                    </select>
                    <input
                      value={h.overlay_text}
                      maxLength={120}
                      onChange={(e) => update({ hooks: plan.hooks.map((x: any, j: number) => (j === i ? { ...x, overlay_text: e.target.value } : x)) })}
                      className="sm:col-span-6 bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2.5 py-2"
                    />
                    <input
                      value={(h.accent_words || []).join(", ")}
                      placeholder="gold words"
                      onChange={(e) =>
                        update({ hooks: plan.hooks.map((x: any, j: number) => (j === i ? { ...x, accent_words: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) } : x)) })
                      }
                      className="sm:col-span-3 bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2.5 py-2"
                    />
                  </div>
                ))}
                <label className="block text-[11px] text-neutral-400 space-y-1 pt-2 border-t border-neutral-800">
                  <span>Instagram caption</span>
                  <textarea value={plan.caption} rows={3} maxLength={2200} onChange={(e) => update({ caption: e.target.value })} className="w-full bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 p-2.5" />
                </label>
                <p className="text-[11px] text-neutral-500">{plan.hashtags.map((t: string) => `#${t}`).join(" ")}</p>
              </Card>

              <div className="flex flex-wrap items-center justify-end gap-3">
                {dirty && (
                  <button onClick={() => savePlan().catch((e) => setError(e.message))} className="px-4 py-2.5 rounded-xl border border-neutral-700 text-neutral-200 text-xs font-semibold inline-flex items-center gap-1.5">
                    <Check className="h-4 w-4" /> Save changes
                  </button>
                )}
                <button onClick={render} disabled={!modes.renderer_ready} className="px-5 py-2.5 rounded-xl bg-brand hover:bg-brand-hover text-brand-ink text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50">
                  <Film className="h-4 w-4" /> {reel.status === "rendered" && !dirty ? "Render again" : `Render ${plan.hooks.length || 1} video${(plan.hooks.length || 1) > 1 ? "s" : ""}`}
                </button>
              </div>
            </>
          )}

          {!busy && reel.status === "rendered" && reel.variants?.length > 0 && (
            <Card title="Your videos" icon={Upload}>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {reel.variants.map((v: any) => (
                  <div key={v.index} className="space-y-2">
                    <video src={v.video_url} poster={v.cover_url} controls playsInline className="w-full aspect-[9/16] rounded-xl bg-black object-cover" />
                    <p className="text-xs text-white font-semibold">{v.label} · {v.duration_s}s</p>
                    {v.hook_text && <p className="text-[11px] text-neutral-400 line-clamp-2">{v.hook_text}</p>}
                    <div className="flex gap-2">
                      <a href={v.video_url} download className="px-3 py-1.5 rounded-lg border border-neutral-700 text-[11px] text-neutral-200 inline-flex items-center gap-1">
                        <Download className="h-3 w-3" /> Video
                      </a>
                      <a href={v.cover_url} download className="px-3 py-1.5 rounded-lg border border-neutral-700 text-[11px] text-neutral-200 inline-flex items-center gap-1">
                        <Download className="h-3 w-3" /> Cover
                      </a>
                    </div>
                  </div>
                ))}
              </div>
              {plan?.caption && (
                <button
                  onClick={() => navigator.clipboard?.writeText(`${plan.caption}\n\n${plan.hashtags.map((t: string) => `#${t}`).join(" ")}`)}
                  className="px-3 py-1.5 rounded-lg border border-neutral-700 text-[11px] text-neutral-200 inline-flex items-center gap-1"
                >
                  <Copy className="h-3 w-3" /> Copy caption
                </button>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
