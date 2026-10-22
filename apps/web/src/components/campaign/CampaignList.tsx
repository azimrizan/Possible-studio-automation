"use client";

import React, { useEffect, useState } from "react";
import { ArrowRight, ExternalLink, Megaphone, RefreshCw } from "lucide-react";
import { studioFetch } from "@/lib/studio";

export const STATUS_STYLES: Record<string, { label: string; cls: string }> = {
  draft: { label: "Draft", cls: "bg-neutral-800 text-neutral-300" },
  planning: { label: "Planning", cls: "bg-brand/10 text-brand" },
  planned: { label: "Ready for review", cls: "bg-brand/10 text-brand" },
  approved: { label: "Approved", cls: "bg-sky-500/15 text-sky-300" },
  publishing: { label: "Posting", cls: "bg-pink-500/15 text-pink-300" },
  published: { label: "Posted", cls: "bg-pink-500/15 text-pink-300" },
  building_ads: { label: "Building ads", cls: "bg-blue-500/15 text-blue-300" },
  ads_ready: { label: "Ads paused · ready to launch", cls: "bg-amber-500/15 text-amber-300" },
  launching: { label: "Launching", cls: "bg-blue-500/15 text-blue-300" },
  live: { label: "Live", cls: "bg-emerald-500/15 text-emerald-300" },
  done: { label: "Posted", cls: "bg-emerald-500/15 text-emerald-300" },
  failed: { label: "Needs attention", cls: "bg-rose-500/15 text-rose-300" },
};

interface Props {
  onOpen: (id: string) => void;
  onNew: () => void;
}

export default function CampaignList({ onOpen, onNew }: Props) {
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    studioFetch("/campaigns")
      .then((d) => setItems(d.campaigns))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Campaigns</h2>
          <p className="text-xs text-neutral-400 mt-1">Every campaign you have planned, posted or launched.</p>
        </div>
        <button
          onClick={onNew}
          className="px-4 py-2.5 rounded-xl bg-brand hover:bg-brand-hover text-brand-ink text-xs font-semibold flex items-center gap-2"
        >
          New campaign <ArrowRight className="h-4 w-4" />
        </button>
      </div>

      {error && <p className="text-xs text-rose-400">{error}</p>}
      {items === null && !error && (
        <div className="text-xs text-neutral-400 flex items-center gap-2">
          <RefreshCw className="h-4 w-4 animate-spin" /> Loading…
        </div>
      )}
      {items?.length === 0 && (
        <div className="rounded-2xl border border-neutral-800 bg-[#131313] p-12 text-center space-y-3">
          <Megaphone className="h-8 w-8 text-brand mx-auto" />
          <p className="text-sm font-semibold text-white">No campaigns yet</p>
          <p className="text-xs text-neutral-400">Create posters with AI or upload your own, and the strategist plans the rest.</p>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items?.map((c) => {
          const st = STATUS_STYLES[c.status] || STATUS_STYLES.draft;
          return (
            <button
              key={c.id}
              onClick={() => onOpen(c.id)}
              className="text-left rounded-2xl border border-neutral-800 hover:border-brand/60 bg-[#131313] p-4 flex gap-4 transition-all"
            >
              <div className="h-24 w-20 rounded-xl overflow-hidden bg-neutral-900 shrink-0">
                {c.thumbnail && <img src={c.thumbnail} alt="" className="h-full w-full object-cover" />}
              </div>
              <div className="min-w-0 flex-1 space-y-2">
                <p className="text-sm font-semibold text-white truncate">{c.name}</p>
                <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full ${st.cls}`}>{st.label}</span>
                <p className="text-[11px] text-neutral-500">{new Date(c.created_at * 1000).toLocaleString()}</p>
                {c.instagram?.permalink && (
                  <a
                    href={c.instagram.permalink}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-[11px] text-pink-300 hover:underline inline-flex items-center gap-1"
                  >
                    View post <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
