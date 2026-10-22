"use client";

import React, { useRef, useState } from "react";
import { Film, ImagePlus, RefreshCw, X } from "lucide-react";
import { CreativeAsset, studioFetch } from "@/lib/studio";

interface Props {
  assets: CreativeAsset[];
  onChange: (assets: CreativeAsset[]) => void;
  max?: number;
}

// Drop zone for ready-made creatives: posters (JPG/PNG/WebP) and optional videos (MP4).
export default function CreativeUploader({ assets, onChange, max = 10 }: Props) {
  const [uploading, setUploading] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = async (files: FileList | File[] | null) => {
    if (!files) return;
    const list = Array.from(files).slice(0, Math.max(0, max - assets.length));
    if (!list.length) return;
    setError(null);
    setUploading(list.length);
    const added: CreativeAsset[] = [];
    for (const file of list) {
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await studioFetch("/uploads/creative", { method: "POST", body: form });
        added.push({ asset_id: res.asset_id, url: res.url, kind: res.kind, name: res.name || file.name });
      } catch (e: any) {
        setError(`${file.name}: ${e.message}`);
      } finally {
        setUploading((n) => n - 1);
      }
    }
    onChange([...assets, ...added].slice(0, max));
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed p-6 sm:p-8 text-center transition-all ${
          dragging ? "border-brand bg-brand/5" : "border-neutral-700/80 hover:border-brand/70 bg-neutral-900/30"
        }`}
      >
        <div className="h-12 w-12 mx-auto rounded-2xl bg-brand/10 border border-brand/30 flex items-center justify-center text-brand mb-3">
          {uploading ? <RefreshCw className="h-6 w-6 animate-spin" /> : <ImagePlus className="h-6 w-6" />}
        </div>
        <p className="text-sm font-semibold text-white">
          {uploading ? `Uploading ${uploading}…` : "Drop your posters and videos here"}
        </p>
        <p className="text-[11px] text-neutral-400 mt-1">
          JPG, PNG or WebP posters · MP4 video optional · up to {max} files · 2+ files post as a carousel
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,video/mp4"
          multiple
          className="hidden"
          onChange={(e) => {
            upload(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {assets.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {assets.map((a) => (
            <div key={a.asset_id} className="relative h-28 w-[90px] rounded-xl overflow-hidden border border-neutral-700 bg-neutral-950 group">
              {a.kind === "video" ? (
                <video src={a.url} className="h-full w-full object-cover" muted playsInline />
              ) : (
                <img src={a.url} alt={a.name} className="h-full w-full object-cover" />
              )}
              {a.kind === "video" && (
                <span className="absolute bottom-1 left-1 text-[9px] font-semibold px-1.5 py-0.5 rounded bg-black/70 text-white flex items-center gap-1">
                  <Film className="h-2.5 w-2.5" /> Video
                </span>
              )}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onChange(assets.filter((x) => x.asset_id !== a.asset_id));
                }}
                className="absolute top-1 right-1 h-6 w-6 rounded-full bg-black/70 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                title="Remove"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}
      {error && <p className="text-[11px] text-rose-400">{error}</p>}
    </div>
  );
}
