"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowLeft, Copy, Download, ImagePlus, Palette, Plus, RefreshCw, Sparkles, Wand2, X } from "lucide-react";
import { studioFetch } from "@/lib/studio";

const SIZES = [
  { key: "portrait", label: "Post 4:5" },
  { key: "square", label: "Post 1:1" },
  { key: "story", label: "Story 9:16" },
  { key: "landscape", label: "Banner 1.91:1" },
];
const GOALS = [
  { key: "promote", label: "Promote a product" },
  { key: "offer", label: "Offer / sale" },
  { key: "launch", label: "New launch" },
  { key: "event", label: "Event" },
  { key: "testimonial", label: "Customer review" },
  { key: "educate", label: "Tips / how it works" },
  { key: "announce", label: "Announcement" },
];
const MODES = [
  { key: "basic", title: "Basic: Claude design", blurb: "Layouts, typography and your photos (products cut out automatically).", meta: "~30-60 s · about ₹40-85 per set" },
  { key: "advanced", title: "Advanced: + AI imagery", blurb: "Basic plus AI-generated backgrounds behind the text (Gemini).", meta: "~1-2 min · about ₹85-170 per set" },
];
const TEMPLATES: Record<string, string> = {
  hero_product: "Product hero",
  big_statement: "Big statement",
  split_photo: "Split photo",
  offer_burst: "Offer burst",
  testimonial: "Testimonial",
  list_steps: "List / steps",
  event: "Event",
  announcement: "Announcement",
};
const FONTS: Record<string, string> = { modern: "Modern sans", editorial: "Editorial serif", bold_condensed: "Bold condensed", elegant: "Elegant serif" };
const BG: Record<string, string> = { solid: "Solid", gradient: "Gradient", photo: "Your photo", plate: "AI background" };
const DECOR: Record<string, string> = { none: "None", circles: "Circles", grid: "Dot grid", burst: "Rays", waves: "Waves" };
const BUSY = new Set(["generating", "rendering"]);

const input = "w-full bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-200 px-2.5 py-2 focus:outline-none focus:border-brand/60";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-[11px] text-neutral-400 space-y-1">
      <span>{label}</span>
      {children}
    </label>
  );
}

type Auth = () => { api_key?: string; oauth_token?: string };

function NewDesign({ onCreated, getAuth }: { onCreated: (id: string) => void; getAuth: Auth }) {
  const [brief, setBrief] = useState("");
  const [goal, setGoal] = useState("promote");
  const [mode, setMode] = useState("basic");
  const [sizes, setSizes] = useState<string[]>(["portrait", "square", "story"]);
  const [photos, setPhotos] = useState<{ asset_id: string; url: string; kind: string }[]>([]);
  const [useBrand, setUseBrand] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const upload = async (file: File) => {
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await studioFetch("/uploads/creative", { method: "POST", body: form });
      if (r.kind !== "image") throw new Error("Upload a photo (JPG, PNG or WebP)");
      setPhotos((p) => [...p, { asset_id: r.asset_id, url: r.url, kind: "product" }].slice(0, 3));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await studioFetch("/designs", {
        method: "POST",
        body: JSON.stringify({ brief, goal, mode, sizes, photos: photos.map(({ asset_id, kind }) => ({ asset_id, kind })), use_brand_kit: useBrand, ...(mode === "advanced" ? getAuth() : {}) }),
      });
      onCreated(r.id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl border border-neutral-800 bg-[#131313] p-5 space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {MODES.map((m) => (
          <button key={m.key} onClick={() => setMode(m.key)} className={`text-left rounded-xl border p-4 space-y-1 ${mode === m.key ? "border-brand/70 bg-brand/5" : "border-neutral-800 bg-neutral-900/50 hover:border-neutral-700"}`}>
            <p className="text-sm font-semibold text-white">{m.title}</p>
            <p className="text-xs text-neutral-300">{m.blurb}</p>
            <p className="text-[11px] text-neutral-500">{m.meta}</p>
          </button>
        ))}
      </div>
      <Field label="What should the design say? Include prices, features, dates and offers exactly as they are.">
        <textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={4} maxLength={1500} className={input}
          placeholder="e.g. MR Plus electric kettle 1.8L, stainless steel, anti dry, 5GT control. Launch offer ₹1,499 (MRP ₹2,199). For Kerala families." />
      </Field>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Goal">
          <select value={goal} onChange={(e) => setGoal(e.target.value)} className={input}>
            {GOALS.map((g) => <option key={g.key} value={g.key}>{g.label}</option>)}
          </select>
        </Field>
        <div className="space-y-1">
          <p className="text-[11px] text-neutral-400">Sizes</p>
          <div className="flex flex-wrap gap-2">
            {SIZES.map((s) => (
              <button key={s.key} onClick={() => setSizes((v) => (v.includes(s.key) ? v.filter((x) => x !== s.key) : [...v, s.key]))}
                className={`px-2.5 py-1.5 rounded-lg text-[11px] border ${sizes.includes(s.key) ? "border-brand/60 text-white bg-brand/10" : "border-neutral-800 text-neutral-400"}`}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="space-y-2">
        <p className="text-[11px] text-neutral-400">Photos (optional, up to 3). Products get their background removed; photos of people or places are used as they are.</p>
        <div className="flex flex-wrap gap-3 items-start">
          {photos.map((ph, i) => (
            <div key={ph.asset_id} className="space-y-1">
              <div className="relative">
                <img src={ph.url} alt="" className="h-20 w-20 rounded-lg object-cover" />
                <button onClick={() => setPhotos((p) => p.filter((_, j) => j !== i))} className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-neutral-800 text-neutral-300 flex items-center justify-center">
                  <X className="h-3 w-3" />
                </button>
              </div>
              <select value={ph.kind} onChange={(e) => setPhotos((p) => p.map((x, j) => (j === i ? { ...x, kind: e.target.value } : x)))} className="w-20 bg-neutral-900 border border-neutral-800 rounded text-[10px] text-neutral-300 px-1 py-1">
                <option value="product">Product</option>
                <option value="photo">Photo</option>
              </select>
            </div>
          ))}
          {photos.length < 3 && (
            <button onClick={() => fileRef.current?.click()} className="h-20 w-20 rounded-lg border border-dashed border-neutral-700 text-neutral-400 hover:text-white hover:border-brand/60 flex flex-col items-center justify-center gap-1 text-[10px]">
              <ImagePlus className="h-4 w-4" /> Add
            </button>
          )}
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
        </div>
      </div>
      <label className="flex items-center gap-2 text-xs text-neutral-300">
        <input type="checkbox" checked={useBrand} onChange={(e) => setUseBrand(e.target.checked)} className="accent-emerald-400" /> Use my brand kit (colours, logo, tone)
      </label>
      {error && <p className="text-xs text-rose-300 flex gap-2"><AlertTriangle className="h-4 w-4 shrink-0" /> {error}</p>}
      <button onClick={create} disabled={busy || brief.trim().length < 3 || !sizes.length}
        className="w-full px-4 py-2.5 rounded-xl bg-brand hover:bg-brand-hover text-brand-ink text-xs font-semibold inline-flex items-center justify-center gap-1.5 disabled:opacity-50">
        <Sparkles className="h-4 w-4" /> {busy ? "Starting…" : "Design 3 concepts"}
      </button>
    </div>
  );
}

function ConceptCard({ d, c, i, onChanged }: { d: any; c: any; i: number; onChanged: (r: any) => void }) {
  const [size, setSize] = useState<string>(d.sizes[0]);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<any>(c);
  const [ask, setAsk] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => setDraft(c), [c]);
  const busy = BUSY.has(d.status);
  const render = c.renders?.[size];
  const set = (patch: any) => setDraft((x: any) => ({ ...x, ...patch }));

  const save = async () => {
    setError(null);
    try {
      const body: any = {};
      for (const k of ["template", "font_pair", "bg_style", "decoration", "headline", "subline", "cta", "price", "old_price", "badge", "quote", "author", "event_date", "event_place", "use_photo"]) body[k] = draft[k];
      body.points = draft.points;
      body.features = draft.features;
      body.palette = draft.palette;
      onChanged(await studioFetch(`/designs/${d.id}/concepts/${i}`, { method: "PUT", body: JSON.stringify(body) }));
      setEditing(false);
    } catch (e: any) {
      setError(e.message);
    }
  };
  const revise = async () => {
    setError(null);
    try {
      onChanged(await studioFetch(`/designs/${d.id}/concepts/${i}/revise`, { method: "POST", body: JSON.stringify({ instruction: ask }) }));
      setAsk("");
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="rounded-2xl border border-neutral-800 bg-[#131313] p-4 space-y-3">
      <div>
        <p className="text-sm font-semibold text-white">{c.name || `Concept ${i + 1}`}</p>
        <p className="text-[11px] text-neutral-500">{TEMPLATES[c.template]} · {FONTS[c.font_pair]}</p>
        {c.rationale && <p className="text-[11px] text-neutral-400 mt-1">{c.rationale}</p>}
      </div>
      <div className="relative rounded-xl overflow-hidden bg-neutral-950 flex items-center justify-center min-h-[200px]">
        {render ? <img src={render.url} alt="" className="w-full h-auto" /> : <RefreshCw className="h-5 w-5 animate-spin text-neutral-600" />}
        {busy && <div className="absolute inset-0 bg-black/40 flex items-center justify-center"><RefreshCw className="h-5 w-5 animate-spin text-white" /></div>}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {d.sizes.map((s: string) => (
          <button key={s} onClick={() => setSize(s)} className={`px-2 py-1 rounded-md text-[10px] border ${size === s ? "border-brand/60 text-white" : "border-neutral-800 text-neutral-400"}`}>
            {SIZES.find((x) => x.key === s)?.label}
          </button>
        ))}
        {render && (
          <a href={render.url} download={`design-${i + 1}-${size}.png`} className="ml-auto px-2 py-1 rounded-md text-[10px] border border-neutral-700 text-neutral-200 inline-flex items-center gap-1">
            <Download className="h-3 w-3" /> PNG
          </a>
        )}
      </div>
      {c.last_change?.notes && <p className="text-[11px] text-brand/80">Claude: {c.last_change.notes}</p>}
      <div className="flex gap-2">
        <input value={ask} onChange={(e) => setAsk(e.target.value)} placeholder="Ask Claude: e.g. make the price bigger, more premium" className={input} onKeyDown={(e) => e.key === "Enter" && ask.trim().length > 1 && !busy && revise()} />
        <button disabled={busy || ask.trim().length < 2} onClick={revise} className="px-3 rounded-lg bg-neutral-800 text-white disabled:opacity-40" title="Ask Claude">
          <Wand2 className="h-3.5 w-3.5" />
        </button>
      </div>
      <button onClick={() => setEditing((v) => !v)} className="text-[11px] text-neutral-400 hover:text-white inline-flex items-center gap-1">
        <Palette className="h-3 w-3" /> {editing ? "Close editor" : "Edit text, layout and colours"}
      </button>
      {editing && (
        <div className="space-y-2.5 pt-2 border-t border-neutral-800">
          <Field label="Headline (wrap words in *asterisks* for the accent colour)"><input value={draft.headline} maxLength={90} onChange={(e) => set({ headline: e.target.value })} className={input} /></Field>
          <Field label="Subline"><input value={draft.subline} maxLength={140} onChange={(e) => set({ subline: e.target.value })} className={input} /></Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Button"><input value={draft.cta} maxLength={24} onChange={(e) => set({ cta: e.target.value })} className={input} /></Field>
            <Field label="Badge"><input value={draft.badge} maxLength={16} onChange={(e) => set({ badge: e.target.value })} className={input} /></Field>
            <Field label="Price"><input value={draft.price} maxLength={14} onChange={(e) => set({ price: e.target.value })} className={input} /></Field>
            <Field label="Old price"><input value={draft.old_price} maxLength={14} onChange={(e) => set({ old_price: e.target.value })} className={input} /></Field>
          </div>
          {draft.template === "list_steps" && (
            <Field label="Points (one per line)">
              <textarea rows={3} value={(draft.points || []).join("\n")} onChange={(e) => set({ points: e.target.value.split("\n").filter((x: string) => x.trim()).slice(0, 4) })} className={input} />
            </Field>
          )}
          {(draft.features || []).length > 0 && (
            <Field label="Features (labels)">
              <input value={draft.features.map((f: any) => f.label).join(", ")} onChange={(e) => set({ features: e.target.value.split(",").map((l: string, k: number) => ({ icon: draft.features[k]?.icon || "Check", label: l.trim() })).filter((f: any) => f.label).slice(0, 3) })} className={input} />
            </Field>
          )}
          {draft.template === "testimonial" && (
            <>
              <Field label="Quote"><textarea rows={2} value={draft.quote} maxLength={220} onChange={(e) => set({ quote: e.target.value })} className={input} /></Field>
              <Field label="Name"><input value={draft.author} maxLength={40} onChange={(e) => set({ author: e.target.value })} className={input} /></Field>
            </>
          )}
          {draft.template === "event" && (
            <div className="grid grid-cols-2 gap-2">
              <Field label="Date"><input value={draft.event_date} maxLength={30} onChange={(e) => set({ event_date: e.target.value })} className={input} /></Field>
              <Field label="Place"><input value={draft.event_place} maxLength={50} onChange={(e) => set({ event_place: e.target.value })} className={input} /></Field>
            </div>
          )}
          <div className="grid grid-cols-2 gap-2">
            <Field label="Layout"><select value={draft.template} onChange={(e) => set({ template: e.target.value })} className={input}>{Object.entries(TEMPLATES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
            <Field label="Fonts"><select value={draft.font_pair} onChange={(e) => set({ font_pair: e.target.value })} className={input}>{Object.entries(FONTS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
            <Field label="Background"><select value={draft.bg_style} onChange={(e) => set({ bg_style: e.target.value })} className={input}>{Object.entries(BG).filter(([k]) => k !== "plate" || Object.keys(c.plates || {}).length).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
            <Field label="Decoration"><select value={draft.decoration} onChange={(e) => set({ decoration: e.target.value })} className={input}>{Object.entries(DECOR).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
          </div>
          <div className="flex flex-wrap gap-3">
            {(["bg", "text", "accent", "accent_text"] as const).map((k) => (
              <label key={k} className="text-[10px] text-neutral-400 flex items-center gap-1.5">
                <input type="color" value={draft.palette[k]} onChange={(e) => set({ palette: { ...draft.palette, [k]: e.target.value } })} className="h-6 w-6 rounded bg-transparent" />
                {k === "bg" ? "Background" : k === "text" ? "Text" : k === "accent" ? "Accent" : "Button text"}
              </label>
            ))}
          </div>
          {d.photos.length > 0 && (
            <label className="flex items-center gap-2 text-[11px] text-neutral-300">
              <input type="checkbox" checked={!!draft.use_photo} onChange={(e) => set({ use_photo: e.target.checked })} /> Use the photo
            </label>
          )}
          <p className="text-[10px] text-neutral-500">Text that's hard to read on the background is adjusted automatically.</p>
          <button disabled={busy} onClick={save} className="w-full px-3 py-2 rounded-lg bg-brand text-brand-ink text-xs font-semibold disabled:opacity-50">Apply changes</button>
        </div>
      )}
      {error && <p className="text-[11px] text-rose-300">{error}</p>}
    </div>
  );
}

export default function DesignStudio({ getGeminiAuth }: { getGeminiAuth: Auth }) {
  const [list, setList] = useState<any[] | null>(null);
  const [id, setId] = useState<string | null>(null);
  const [d, setD] = useState<any>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(() => studioFetch("/designs").then(setList).catch((e) => setError(e.message)), []);
  const load = useCallback(async () => {
    if (!id) return;
    try {
      setD(await studioFetch(`/designs/${id}`));
    } catch (e: any) {
      setError(e.message);
    }
  }, [id]);

  useEffect(() => {
    if (!id) loadList();
    else load();
  }, [id, load, loadList]);
  useEffect(() => {
    if (!d || !BUSY.has(d.status)) return;
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [d, load]);

  if (!id) {
    return (
      <div className="space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-white">AI Design</h2>
            <p className="text-xs text-neutral-400 mt-1 max-w-xl">
              Claude art-directs three on-brand concepts. Text is set as real type, so spelling is exact in any language, and every design comes in every size and stays editable.
            </p>
          </div>
          <button onClick={() => setCreating((v) => !v)} className="px-4 py-2.5 rounded-xl bg-brand hover:bg-brand-hover text-brand-ink text-xs font-semibold inline-flex items-center gap-1.5">
            <Plus className="h-4 w-4" /> New design
          </button>
        </div>
        {creating && <NewDesign onCreated={(newId) => { setCreating(false); setId(newId); }} getAuth={getGeminiAuth} />}
        {error && <p className="text-xs text-rose-300">{error}</p>}
        {list && list.length === 0 && !creating && <p className="text-xs text-neutral-500">No designs yet.</p>}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          {list?.map((x) => (
            <button key={x.id} onClick={() => setId(x.id)} className="text-left rounded-xl border border-neutral-800 bg-[#131313] overflow-hidden hover:border-brand/50">
              <div className="aspect-[4/5] bg-neutral-900 flex items-center justify-center">
                {x.thumb ? <img src={x.thumb} alt="" className="h-full w-full object-cover" /> : <Palette className="h-6 w-6 text-neutral-600" />}
              </div>
              <div className="p-2.5">
                <p className="text-xs text-white truncate">{x.brief}</p>
                <p className="text-[10px] text-neutral-500 capitalize">{x.mode} · {x.status}</p>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (!d) return <p className="text-xs text-neutral-400 flex items-center gap-2"><RefreshCw className="h-4 w-4 animate-spin" /> Loading…</p>;
  const meta = d.plan_meta || {};
  return (
    <div className="space-y-5 pb-10">
      <div className="flex items-center gap-3">
        <button onClick={() => { setId(null); setD(null); }} className="h-9 w-9 rounded-full border border-neutral-700 text-neutral-300 hover:bg-neutral-800 flex items-center justify-center" title="All designs">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="min-w-0">
          <h2 className="text-lg font-bold text-white truncate">{d.brief}</h2>
          <p className="text-[11px] text-neutral-500 capitalize">{d.mode} · {d.status}{meta.reviewed ? " · checked by Claude against the renders" : ""}</p>
        </div>
      </div>
      {d.modes?.director === "demo" && (
        <div className="p-3 rounded-xl border border-amber-700/50 bg-amber-950/30 text-amber-200 text-xs flex gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" /> Demo mode: layouts are real but the copy and art direction are placeholders. Add ANTHROPIC_API_KEY to .env and restart the API.
        </div>
      )}
      {(d.error || error) && (
        <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex gap-2"><AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" /> {d.error || error}</div>
      )}
      {d.status === "generating" && (
        <div className="rounded-2xl border border-brand/25 bg-[#0b0b0b] p-8 text-center">
          <RefreshCw className="h-6 w-6 animate-spin text-brand mx-auto" />
          <p className="text-sm text-white font-semibold mt-3">Designing</p>
          <p className="text-xs text-neutral-400 mt-1">{d.progress || "Working…"}</p>
        </div>
      )}
      {meta.notes && d.status !== "generating" && <p className="text-xs text-neutral-300 rounded-xl border border-neutral-800 bg-neutral-900/40 p-3">{meta.notes}</p>}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
        {(d.concepts || []).map((c: any, i: number) => <ConceptCard key={i} d={d} c={c} i={i} onChanged={setD} />)}
      </div>
      {meta.caption && (
        <button onClick={() => navigator.clipboard?.writeText(`${meta.caption}\n\n${(meta.hashtags || []).map((t: string) => `#${t}`).join(" ")}`)}
          className="px-3 py-1.5 rounded-lg border border-neutral-700 text-[11px] text-neutral-200 inline-flex items-center gap-1">
          <Copy className="h-3 w-3" /> Copy caption
        </button>
      )}
    </div>
  );
}
