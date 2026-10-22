"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Facebook, Instagram, Link2, LogOut, RefreshCw } from "lucide-react";
import { MetaConnection, metaConnectUrl, studioFetch } from "@/lib/studio";

interface Props {
  compact?: boolean;
  onChange?: (conn: MetaConnection | null) => void;
}

export default function MetaConnectCard({ compact = false, onChange }: Props) {
  const [conn, setConn] = useState<MetaConnection | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showToken, setShowToken] = useState(false);
  const [tokenInput, setTokenInput] = useState("");

  const apply = (data: any) => {
    setConn(data.meta);
    onChange?.(data.meta);
  };

  useEffect(() => {
    studioFetch("/connections")
      .then(apply)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const select = async (pageId: string, adAccountId?: string) => {
    setSaving(true);
    setError(null);
    try {
      apply(
        await studioFetch("/connections/meta/selection", {
          method: "PUT",
          body: JSON.stringify({ page_id: pageId, ad_account_id: adAccountId || undefined }),
        })
      );
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const disconnect = async () => {
    setSaving(true);
    try {
      apply(await studioFetch("/connections/meta", { method: "DELETE" }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const connectWithToken = async () => {
    setSaving(true);
    setError(null);
    try {
      apply(await studioFetch("/connections/meta/system-token", { method: "POST", body: JSON.stringify({ token: tokenInput }) }));
      setTokenInput("");
      setShowToken(false);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const tokenPanel = conn?.mode === "live" && (
    <div className="pt-1">
      <button
        type="button"
        onClick={() => setShowToken((v) => !v)}
        className="text-[11px] text-brand hover:text-brand underline-offset-2 hover:underline"
      >
        {showToken ? "Hide" : conn?.connected ? "Switch to a Business System User token" : "Use a Business System User token instead"}
      </button>
      {showToken && (
        <div className="mt-2 space-y-2 rounded-xl border border-neutral-800 bg-neutral-900/60 p-3">
          <p className="text-[11px] text-neutral-400">
            Generate it in Meta Business settings → Users → System users → Generate token (app: Possible Studio). It belongs to
            your business, not a person, so personal login security checks don&apos;t block it. Stored encrypted; never shown again.
          </p>
          <div className="flex gap-2">
            <input
              type="password"
              autoComplete="off"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Paste System User access token"
              className="flex-1 px-3 py-2 rounded-xl bg-neutral-950 border border-neutral-700 text-xs text-white focus:outline-none focus:border-brand"
            />
            <button
              type="button"
              onClick={connectWithToken}
              disabled={saving || tokenInput.trim().length < 20}
              className="px-3.5 rounded-xl bg-brand hover:bg-brand-hover text-brand-ink text-xs font-semibold disabled:opacity-40 whitespace-nowrap"
            >
              {saving ? "Verifying…" : "Connect"}
            </button>
          </div>
        </div>
      )}
    </div>
  );

  const connect = () => {
    window.location.href = metaConnectUrl();
  };

  const sel = conn?.selection || {};
  const ready = Boolean(conn?.connected && sel.ig_user_id && sel.ad_account_id && !conn?.needs_reauth);

  if (loading) {
    return (
      <div className="rounded-2xl border border-neutral-800 bg-[#131313] p-5 flex items-center gap-3 text-xs text-neutral-400">
        <RefreshCw className="h-4 w-4 animate-spin" /> Checking Instagram & Meta connection…
      </div>
    );
  }

  return (
    <div className={`rounded-2xl border ${ready ? "border-emerald-700/40" : "border-neutral-800"} bg-[#131313] ${compact ? "p-4" : "p-6"} space-y-4`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex -space-x-2">
            <span className="h-9 w-9 rounded-xl bg-gradient-to-tr from-amber-400 via-pink-500 to-purple-600 flex items-center justify-center ring-2 ring-[#131313]">
              <Instagram className="h-4.5 w-4.5 text-white" />
            </span>
            <span className="h-9 w-9 rounded-xl bg-[#1877F2] flex items-center justify-center ring-2 ring-[#131313]">
              <Facebook className="h-4.5 w-4.5 text-white" />
            </span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Instagram & Meta Ads</h3>
            <p className="text-[11px] text-neutral-400">
              {conn?.connected
                ? `Connected as ${conn.user_name}${conn.kind === "system_user" ? " (Business System User)" : ""}`
                : "Post to Instagram and run Meta ads from Possible Studio"}
            </p>
          </div>
        </div>
        {conn?.mode === "mock" && (
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 shrink-0"
            title="No Meta app configured (META_APP_ID) or MOCK_META_GRAPH=true. Nothing is actually posted or spent."
          >
            Demo mode
          </span>
        )}
      </div>

      {conn?.mode === "not_configured" ? (
        <div className="space-y-2 rounded-xl border border-amber-500/30 bg-amber-950/20 p-3">
          <p className="text-xs font-semibold text-amber-200 flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5" /> Meta app not set up yet
          </p>
          <p className="text-[11px] text-neutral-300">
            Add <code className="text-amber-200">META_APP_ID</code> and <code className="text-amber-200">META_APP_SECRET</code> to{" "}
            <code>.env</code> and restart the API. In your Meta app, allow this redirect URI:
          </p>
          <code className="block text-[11px] text-brand bg-neutral-950 rounded-lg px-2.5 py-1.5 break-all">{conn.redirect_uri}</code>
        </div>
      ) : !conn?.connected || conn.needs_reauth ? (
        <div className="space-y-3">
          {conn?.needs_reauth && (
            <p className="text-[11px] text-amber-300 flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5" /> Your Meta login expired. Reconnect to keep posting and running ads.
            </p>
          )}
          {!compact && (
            <ul className="text-[11px] text-neutral-400 space-y-1">
              <li>• Needs an Instagram Business or Creator account linked to a Facebook Page</li>
              <li>• Ads run from your own Meta ad account; you stay in control of spend</li>
              <li>• We never see your password; access can be removed any time</li>
            </ul>
          )}
          <button
            type="button"
            onClick={connect}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand hover:bg-brand-hover hover:opacity-95 text-brand-ink text-xs font-semibold shadow-lg shadow-brand/20 transition-all"
          >
            <Link2 className="h-4 w-4" />
            {conn?.needs_reauth ? "Reconnect Instagram & Meta" : "Connect Instagram & Meta"}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="text-[11px] text-neutral-400 mb-1 block">Instagram account</span>
              <select
                value={sel.page_id || ""}
                disabled={saving}
                onChange={(e) => select(e.target.value, sel.ad_account_id)}
                className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-700 text-xs text-white focus:outline-none focus:border-brand"
              >
                <option value="" disabled>
                  Choose a Page with Instagram
                </option>
                {conn.pages.map((p) => (
                  <option key={p.id} value={p.id} disabled={!p.ig_user_id}>
                    {p.ig_username ? `@${p.ig_username}` : "(no Instagram linked)"} · {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-[11px] text-neutral-400 mb-1 block">Ad account</span>
              <select
                value={sel.ad_account_id || ""}
                disabled={saving || !sel.page_id}
                onChange={(e) => sel.page_id && select(sel.page_id, e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-700 text-xs text-white focus:outline-none focus:border-brand disabled:opacity-50"
              >
                <option value="" disabled>
                  Choose an ad account
                </option>
                {conn.ad_accounts.map((a) => (
                  <option key={a.id} value={a.id} disabled={!a.active}>
                    {a.name} · {a.currency}
                    {a.active ? "" : " (inactive)"}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            {ready ? (
              <span className="text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> Ready: @{sel.ig_username} · {sel.ad_account_name}
              </span>
            ) : (
              <span className="text-amber-300">Pick an Instagram account and an ad account</span>
            )}
            <button type="button" onClick={disconnect} disabled={saving} className="text-neutral-500 hover:text-rose-400 flex items-center gap-1">
              <LogOut className="h-3 w-3" /> Disconnect
            </button>
          </div>
        </div>
      )}
      {tokenPanel}
      {error && <p className="text-[11px] text-rose-400">{error}</p>}
    </div>
  );
}
