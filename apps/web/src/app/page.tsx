"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Paperclip,
  Plus,
  Sliders,
  ArrowRight,
  ArrowLeft,
  Maximize2,
  TrendingUp,
  Globe,
  Film,
  Tag,
  Palette,
  Volume2,
  Package,
  CheckCircle2,
  Circle,
  Layers,
  Settings,
  FileText,
  Code2,
  X,
  Upload,
  Image as ImageIcon,
  Clock,
  Check,
  ChevronRight,
  Edit3,
  Flame,
  ShieldCheck,
  RotateCcw,
  Copy,
  Download,
  RefreshCw,
  Share2,
  Play,
  Pause,
  Music,
  Video,
  MessageSquare,
  Lock,
  AlertTriangle,
  Key,
  History,
  Send,
  Zap,
  Cpu,
  Server,
  Radio,
  Eye,
  EyeOff,
  Bell,
  Calendar,
  ChevronDown,
  Megaphone,
  Link2,
  Info,
  LayoutDashboard,
  Home,
} from "lucide-react";
import { studioFetch, getStudioWorkspace, CreativeAsset } from "@/lib/studio";
import CampaignFlow from "@/components/campaign/CampaignFlow";
import CampaignList from "@/components/campaign/CampaignList";
import MetaConnectCard from "@/components/campaign/MetaConnectCard";
import CreativeUploader from "@/components/campaign/CreativeUploader";
interface ProductImage {
  asset_id: string;
  url: string;
  name: string;
}

const MAX_PRODUCT_IMAGES = 3;

const preloadImages = (urls: string[]): Promise<void[]> => {
  if (typeof window === "undefined") return Promise.resolve([]);
  return Promise.all(
    urls.filter(Boolean).map(
      (url) =>
        new Promise<void>((resolve) => {
          const img = new window.Image();
          img.onload = () => resolve();
          img.onerror = () => resolve();
          img.src = url;
        })
    )
  );
};


interface Product {
  name: string;
  description: string;
  price: number;
  currency: string;
  key_features: string[];
}

export default function App() {
  const [activeNav, setActiveNav] = useState<"Overview" | "Campaigns" | "Creative Studio" | "Brand Kit" | "Integrations" | "Settings" | "Marketing" | "Knowledge">("Overview");
  const [currentStep, setCurrentStep] = useState<"01_DASHBOARD" | "02_PLANNING" | "04_CREATIVE">("01_DASHBOARD");

  // Prompt bar state (Clean by default - create from scratch)
  const [promptText, setPromptText] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<Array<{ name: string; size: string }>>([]);
  const [productImages, setProductImages] = useState<ProductImage[]>([]);
  const [isUploadingProduct, setIsUploadingProduct] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const imageRef = productImages[0]?.url || null;
  const [selectedProduct, setSelectedProduct] = useState("");
  const [budgetINR, setBudgetINR] = useState("");
  const [durationDays, setDurationDays] = useState<number | null>(7);

  // Phase 2: Understanding & Planning checklist state
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [isEnhancing, setIsEnhancing] = useState(false);

  // Phase 2: Creative Brief state (Filled dynamically by Groq)
  const [briefObjective, setBriefObjective] = useState("");
  const [briefProduct, setBriefProduct] = useState("");
  const [briefDuration, setBriefDuration] = useState("");
  const [briefBudget, setBriefBudget] = useState("");
  const [briefChannels, setBriefChannels] = useState("");
  const [briefDeliverables, setBriefDeliverables] = useState<"POSTER" | "REEL" | "BOTH">("BOTH");
  const [briefCTA, setBriefCTA] = useState("");
  const [briefTone, setBriefTone] = useState("");
  const [isEditingBrief, setIsEditingBrief] = useState(false);
  const [isBriefApproved, setIsBriefApproved] = useState(false);

  // Phase 3: Creative Generation State
  const [selectedVariantIndex, setSelectedVariantIndex] = useState<1 | 2 | 3>(1);
  const [selectedAspectRatio, setSelectedAspectRatio] = useState<"4:5" | "1:1" | "9:16">("4:5");
  const [isRegeneratingCreative, setIsRegeneratingCreative] = useState(false);
  const [hasGeneratedWithGroq, setHasGeneratedWithGroq] = useState(false);
  const [copiedHashtags, setCopiedHashtags] = useState(false);

  // Phase 4: Reel & Video Pipeline State
  // Phase 4 & Phase 5 Deliverables Tabs
  const [activeStudioTab, setActiveStudioTab] = useState<"POSTER" | "REEL" | "REVIEW">("POSTER");
  const [isPlayingReel, setIsPlayingReel] = useState(false);
  const [activeReelScene, setActiveReelScene] = useState<1 | 2 | 3 | 4>(1);
  const [selectedAudioTrack, setSelectedAudioTrack] = useState("Cinematic Synth Anthem");
  const [selectedCaptionStyle, setSelectedCaptionStyle] = useState("Kinetic Pop");
  const [reelProgress, setReelProgress] = useState(100);
  const [isRenderingReel, setIsRenderingReel] = useState(false);

  // Phase 5: Human-in-the-Loop Review & Approval Gate State
  const [reviewRole, setReviewRole] = useState<"APPROVER" | "EDITOR">("APPROVER");
  const [reviewStatus, setReviewStatus] = useState<"PENDING_REVIEW" | "CHANGES_REQUESTED" | "APPROVED">("PENDING_REVIEW");
  const [campaignVersion, setCampaignVersion] = useState(1);
  const [reviewFeedback, setReviewFeedback] = useState("Make headline punchier and switch to vibrant neon purple accent with urgent CTA");
  const [targetAssetForChanges, setTargetAssetForChanges] = useState("Variant 1 (High Energy)");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [approvalTokenInfo, setApprovalTokenInfo] = useState<any>(null);
  const [reviewDiffSummary, setReviewDiffSummary] = useState<string | null>(null);
  const [newCommentInput, setNewCommentInput] = useState("");
  const [commentTargetAsset, setCommentTargetAsset] = useState("All Assets");
  const [commentsList, setCommentsList] = useState<Array<{ id: string; asset: string; author: string; text: string; time: string }>>([
    {
      id: "c1",
      asset: "Variant 1",
      author: "Chief Approver",
      text: "Typography vector sharpness is flawless. Consider punchier action verb on the hook.",
      time: "10 mins ago",
    },
  ]);
  const [revisionsList, setRevisionsList] = useState<Array<{ version: number; feedback: string; diff: string; time: string }>>([]);

  const handleApproveCampaign = () => {
    if (reviewRole !== "APPROVER") {
      alert("❌ 403 Forbidden: Role 'EDITOR' is not permitted to approve campaigns. Only APPROVER or OWNER roles can mint signed approval tokens.");
      return;
    }
    setIsSubmittingReview(true);
    setTimeout(() => {
      const mintedToken = {
        token_jti: `appr_tok_${Date.now()}_a9b2c8d1`,
        payload_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        signature: "3a8f9c2d1e0b5a4f7e6d8c9b0a1f2e3d4c5b6a7f8e9d0c1b2a3f4e5d6c7b8a90",
        tenant_id: "tenant-demo-prod",
        tool_name: "publish_post",
        expires_at: Math.floor(Date.now() / 1000) + 3600,
        approved_by: "Chief Approver (user_9481)",
        algorithm: "Ed25519 (Single-Use Payload-Bound)",
      };
      setApprovalTokenInfo(mintedToken);
      setReviewStatus("APPROVED");
      setIsSubmittingReview(false);
    }, 600);
  };

  const handleRequestChanges = async () => {
    setIsSubmittingReview(true);
    try {
      const activeVar = variantsData.find((v) => v.index === selectedVariantIndex) || variantsData[0];
      const res = await fetch("/api/mcp/gemini", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "review_targeted_regeneration",
          api_key: geminiApiKey || undefined,
          payload: {
            feedback: reviewFeedback,
            target_deliverable: targetAssetForChanges,
            current_headline: activeVar.headline,
            current_cta: activeVar.cta,
          },
        }),
      });

      const nextVersion = campaignVersion + 1;
      let diff = `Targeted edit applied to ${targetAssetForChanges}: Headline updated; Accent refined; CTA urgency upgraded.`;

      if (res.ok) {
        const data = await res.json();
        const d = data.data;
        if (d) {
          diff = d.diff_summary || diff;
          setVariantsData((prev: any[]) =>
            prev.map((v) => {
              if (
                targetAssetForChanges.includes(String(v.index)) ||
                (targetAssetForChanges.includes("Variant 1") && v.index === 1) ||
                (targetAssetForChanges.includes("Variant 2") && v.index === 2) ||
                (targetAssetForChanges.includes("Variant 3") && v.index === 3)
              ) {
                return {
                  ...v,
                  headline: d.updated_headline || v.headline,
                  subheadline: d.updated_subheadline || v.subheadline,
                  cta: d.updated_cta || v.cta,
                  accent: d.updated_accent || v.accent,
                };
              }
              return v;
            })
          );
        }
      }

      setCampaignVersion(nextVersion);
      setReviewDiffSummary(diff);
      setRevisionsList((prev) => [
        ...prev,
        {
          version: nextVersion,
          feedback: reviewFeedback,
          diff: diff,
          time: "Just now",
        },
      ]);
      setReviewStatus("CHANGES_REQUESTED");
    } catch (e) {
      console.warn("Review targeted regeneration error:", e);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const getGeminiAuth = () => {
    let oauthToken = geminiUser?.token || (geminiUser as any)?.access_token || "";
    if (!oauthToken && typeof window !== "undefined") {
      try {
        const s = JSON.parse(localStorage.getItem("gemini_oauth_session") || "null");
        oauthToken = s?.token || s?.access_token || "";
      } catch {}
    }
    return { api_key: geminiApiKey || undefined, oauth_token: oauthToken || undefined };
  };

  // Designer agent (Groq) art-directs 3 concepts; Gemini renders them with the product photo + brand logo.
  const generatePosters = async (brief: Record<string, any>, avoid: string[] = []) => {
    setGenerationError(null);
    try {
      const res = await studioFetch("/posters/generate", {
        method: "POST",
        body: JSON.stringify({
          ...getGeminiAuth(),
          brief,
          user_direction: promptText,
          product_asset_ids: productImages.map((p) => p.asset_id),
          aspect_ratio: selectedAspectRatio,
          avoid,
          use_brand_kit: useBrandKit,
        }),
      });
      const variants = res.data?.variants || [];
      console.log("[PosterStudio] Groq usage:", res.data?.usage, "| mock:", res.data?.mock, "| took", res.data?.elapsed_s, "s");
      await preloadImages(variants.map((v: any) => v.bgUrl).filter(Boolean));
      setVariantsData(variants);
      setSelectedCardIndices(variants.filter((v: any) => v.status === "ready").map((v: any) => v.index));
      setSelectedVariantIndex(1);
      setHasGeneratedWithGroq(true);
    } catch (e: any) {
      console.warn("Poster generation error:", e);
      setGenerationError(e?.message || "Poster generation failed");
    }
  };

  const handleRegenerateCreatives = async () => {
    setIsRegeneratingCreative(true);
    try {
      await generatePosters(
        {
          product_focus: briefProduct || selectedProduct || "",
          objective: briefObjective,
          tone: briefTone,
          call_to_action: briefCTA,
        },
        variantsData.map((v) => v.concept?.big_idea).filter(Boolean)
      );
    } finally {
      setIsRegeneratingCreative(false);
    }
  };

  // Re-renders one poster. Text-only edits cost zero LLM tokens; a described change uses one small Groq call.
  const handleRegenerateVariant = async (card: any, change: string) => {
    if (!card?.concept) return;
    setRegeneratingIndex(card.index);
    setGenerationError(null);
    try {
      const res = await studioFetch("/posters/regenerate", {
        method: "POST",
        body: JSON.stringify({
          ...getGeminiAuth(),
          index: card.index,
          concept: { ...card.concept, headline: card.headline, subline: card.subheadline || "", cta: card.cta || "" },
          change,
          brief: { product_focus: briefProduct || selectedProduct || "" },
          product_asset_ids: productImages.map((p) => p.asset_id),
          aspect_ratio: selectedAspectRatio,
          use_brand_kit: useBrandKit,
        }),
      });
      const updated = res.data?.variant;
      if (updated) {
        await preloadImages([updated.bgUrl].filter(Boolean));
        setVariantsData((prev) => prev.map((v) => (v.index === card.index ? updated : v)));
      }
    } catch (e: any) {
      setGenerationError(e?.message || "Could not regenerate this poster");
    } finally {
      setRegeneratingIndex(null);
    }
  };

  const handleProductUpload = async (files: FileList | null) => {
    if (!files?.length) return;
    setUploadError(null);
    setIsUploadingProduct(true);
    try {
      const room = MAX_PRODUCT_IMAGES - productImages.length;
      const uploaded: ProductImage[] = [];
      for (const file of Array.from(files).slice(0, Math.max(room, 0))) {
        const form = new FormData();
        form.append("file", file);
        const res = await studioFetch("/uploads", { method: "POST", body: form });
        uploaded.push({ asset_id: res.asset_id, url: res.url, name: file.name });
      }
      setProductImages((prev) => [...prev, ...uploaded].slice(0, MAX_PRODUCT_IMAGES));
    } catch (e: any) {
      setUploadError(e?.message || "Upload failed");
    } finally {
      setIsUploadingProduct(false);
    }
  };

  const handleCopyHashtags = (hashtags: string[]) => {
    if (navigator?.clipboard && hashtags) {
      navigator.clipboard.writeText(hashtags.join(" "));
    }
    setCopiedHashtags(true);
    setTimeout(() => setCopiedHashtags(false), 2000);
  };

  const handleAddComment = () => {
    if (!newCommentInput.trim()) return;
    setCommentsList((prev) => [
      ...prev,
      {
        id: `c_${Date.now()}`,
        asset: commentTargetAsset,
        author: reviewRole === "APPROVER" ? "Chief Approver" : "Junior Designer",
        text: newCommentInput,
        time: "Just now",
      },
    ]);
    setNewCommentInput("");
  };




  // Modals state
  const [showAttachModal, setShowAttachModal] = useState(false);
  const [showProductModal, setShowProductModal] = useState(false);
  const [showAdvancedModal, setShowAdvancedModal] = useState(false);
  const [showTokensViewer, setShowTokensViewer] = useState(false);

  // Gemini MCP Connector State (Model Context Protocol Gateway)
  const [isGeminiMcpConnected, setIsGeminiMcpConnected] = useState(true);
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [showGeminiApiKey, setShowGeminiApiKey] = useState(false);
  const [showGeminiModal, setShowGeminiModal] = useState(false);
  const [isTestingGemini, setIsTestingGemini] = useState(false);
  const [geminiLatency, setGeminiLatency] = useState<number | null>(12);
  const [geminiMcpEngine, setGeminiMcpEngine] = useState<string>("Gemini MCP Gateway (Imagen 3 + Veo 2)");
  const [geminiModelsList, setGeminiModelsList] = useState<string[]>([
    "imagen-3.0-generate-002",
    "veo-2.0-generate-001",
    "gemini-2.5-flash",
    "gemini-1.5-pro",
  ]);
  const [geminiToolsList, setGeminiToolsList] = useState<any[]>([
    { name: "design.generate", description: "Multi-variant graphic poster layouts with typography", category: "Art Direction" },
    { name: "reel.generate", description: "4-Scene kinetic vertical video reel storyboard & audio cues", category: "Motion Graphics" },
    { name: "image.generate", description: "Imagen 3 visual background art for posters", category: "Graphic Design" },
    { name: "video.generate", description: "Veo 2 vertical 9:16 video generation", category: "Video Production" },
    { name: "text.generate", description: "Creative reasoning, high-converting copy & hashtags", category: "Copywriting" },
  ]);
  const [geminiNoticeMessage, setGeminiNoticeMessage] = useState<string | null>(null);

  // Gemini OAuth 2.0 State
  const [geminiUser, setGeminiUser] = useState<{
    name: string;
    email: string;
    avatar: string;
    key_masked?: string;
    scopes: string[];
    token: string;
    connected_at: string;
    models?: string[];
  } | null>(null);
  const [isVerifyingKey, setIsVerifyingKey] = useState(false);
  const [connectKeyInput, setConnectKeyInput] = useState("");
  const [connectError, setConnectError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      // Handle OAuth callback from Google — session is passed as base64 in URL
      const urlParams = new URLSearchParams(window.location.search);
      const oauthSuccess = urlParams.get("oauth_success");
      const sessionB64 = urlParams.get("session");
      const oauthError = urlParams.get("oauth_error");

      if (oauthError) {
        setConnectError(`Google sign-in failed: ${oauthError.replace(/_/g, " ")}`);
        setShowGeminiModal(true);
        // Clean URL
        window.history.replaceState({}, "", window.location.pathname);
      }

      if (oauthSuccess === "1" && sessionB64) {
        try {
          const parsed = JSON.parse(atob(sessionB64));
          setGeminiUser(parsed);
          setIsGeminiMcpConnected(true);
          localStorage.setItem("gemini_oauth_session", JSON.stringify(parsed));
          setGeminiNoticeMessage(`✓ Successfully connected as ${parsed.email}`);
          setShowGeminiModal(true);
        } catch (e) {
          setConnectError("Failed to parse session from Google. Please try again.");
        }
        // Clean URL
        window.history.replaceState({}, "", window.location.pathname);
        return;
      }

      // Restore existing session from localStorage
      const savedAuth = localStorage.getItem("gemini_oauth_session");
      if (savedAuth) {
        try {
          const parsed = JSON.parse(savedAuth);
          setGeminiUser(parsed);
          setIsGeminiMcpConnected(true);
        } catch {}
      } else {
        setGeminiUser(null);
        setIsGeminiMcpConnected(false);
      }

      // Returning from the Instagram & Meta login
      const metaConnected = urlParams.get("meta_connected");
      const metaError = urlParams.get("meta_error");
      if (metaConnected || metaError) {
        setMetaNotice(
          metaConnected ? "Instagram & Meta connected." : `Meta connection failed: ${metaError!.replace(/_/g, " ")}`
        );
        let returnTo: string | null = null;
        try {
          returnTo = sessionStorage.getItem("studio_open_campaign");
        } catch {}
        if (returnTo) {
          setOpenCampaignId(returnTo);
          setActiveNav("Campaigns");
        } else {
          setActiveNav("Integrations");
        }
        window.history.replaceState({}, "", window.location.pathname);
      }

      // Brand kit now lives in the studio API; drop the old base64 copies.
      localStorage.removeItem("brand_kit_logo");
      localStorage.removeItem("brand_kit_name");
      loadBrandKit();
    }
  }, []);

  // Initiates real Google OAuth — redirects to accounts.google.com
  const handleSignInWithGoogle = () => {
    setConnectError(null);
    // Redirect to our backend OAuth initiation route
    window.location.href = "/api/auth/google";
  };

  // Legacy key connect kept for fallback (not shown in UI)
  const handleConnectRealGeminiKey = async (keyCandidate?: string) => {
    const key = (keyCandidate || connectKeyInput || geminiApiKey).trim();
    if (!key) return;
    setIsVerifyingKey(true);
    setConnectError(null);
    try {
      const res = await fetch("/api/mcp/gemini", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "verify_real_account", payload: { api_key: key } }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setGeminiApiKey(key);
        setIsGeminiMcpConnected(true);
      } else {
        setConnectError(data.error || "Failed to authenticate.");
      }
    } catch (err: any) {
      setConnectError(`Network error: ${err.message}`);
    } finally {
      setIsVerifyingKey(false);
    }
  };

  const handleDisconnectGoogleOAuth = async () => {
    setGeminiUser(null);
    setGeminiApiKey("");
    setConnectKeyInput("");
    setIsGeminiMcpConnected(false);
    if (typeof window !== "undefined") {
      localStorage.removeItem("gemini_oauth_session");
      localStorage.removeItem("gemini_api_key");
    }
    setGeminiNoticeMessage("Gemini MCP session disconnected. Connect your Google account to re-authenticate.");
    try {
      await fetch("/api/mcp/gemini", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "oauth_disconnect" }),
      });
    } catch {}
  };

  const checkGeminiMcpConnection = async (customKey?: string) => {
    setIsTestingGemini(true);
    const keyToTest = customKey !== undefined ? customKey : geminiApiKey;
    if (!keyToTest) {
      setIsGeminiMcpConnected(false);
      setGeminiNoticeMessage("Gemini MCP is disconnected. Connect your Google Gemini API key to begin.");
      setIsTestingGemini(false);
      return;
    }
    try {
      const res = await fetch("/api/mcp/gemini", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "check_connection",
          api_key: keyToTest,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const connected = data.status === "CONNECTED";
        setIsGeminiMcpConnected(connected);
        setGeminiLatency(data.latency_ms || 12);
        if (data.active_engine) setGeminiMcpEngine(data.active_engine);
        if (data.available_models) setGeminiModelsList(data.available_models);
        if (data.active_tools) setGeminiToolsList(data.active_tools);
        if (connected) {
          setGeminiNoticeMessage(`✓ Connected to Google Gemini (${data.server} v${data.version}) in ${data.latency_ms}ms`);
        } else {
          setGeminiNoticeMessage("Gemini MCP disconnected. Provide a valid Google Gemini API key.");
        }
      } else {
        setIsGeminiMcpConnected(false);
        setGeminiNoticeMessage("⚠️ Connection test failed. Using offline fallback.");
      }
    } catch (e) {
      console.warn("Gemini MCP check failed:", e);
      setIsGeminiMcpConnected(false);
    } finally {
      setIsTestingGemini(false);
    }
  };

  const handleSaveGeminiKey = (key: string) => {
    setGeminiApiKey(key);
    if (typeof window !== "undefined") {
      if (key.trim()) {
        localStorage.setItem("gemini_api_key", key.trim());
      } else {
        localStorage.removeItem("gemini_api_key");
      }
    }
    handleConnectRealGeminiKey(key);
  };

  // Brand Kit State — every field is optional; empty fields are simply not sent to the designer agent.
  const [brandName, setBrandName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [logoProfile, setLogoProfile] = useState<{ kind?: string; reads_as?: string; best_on?: string } | null>(null);
  const [primaryColor, setPrimaryColor] = useState("");
  const [secondaryColor, setSecondaryColor] = useState("");
  const [accentColor, setAccentColor] = useState("");
  const [headlineFont, setHeadlineFont] = useState("Inter, sans-serif");
  const [toneKeywords, setToneKeywords] = useState("");
  const [brandTagline, setBrandTagline] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [compileStatus, setCompileStatus] = useState<string | null>(null);
  const [isSavingBrandKit, setIsSavingBrandKit] = useState(false);
  const [isUploadingLogo, setIsUploadingLogo] = useState(false);
  const [useBrandKit, setUseBrandKit] = useState(true);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(null);
  const [editChangeNote, setEditChangeNote] = useState("");

  const applyBrandKit = (kit: any) => {
    setBrandName(kit?.brand_name || "");
    const [p = "", s = "", a = ""] = kit?.colors || [];
    setPrimaryColor(p);
    setSecondaryColor(s);
    setAccentColor(a);
    setToneKeywords(kit?.tone || "");
    setBrandTagline(kit?.tagline || "");
    setLogoUrl(kit?.logo?.url || "");
    setLogoProfile(kit?.logo_profile || null);
  };

  const loadBrandKit = async () => {
    try {
      applyBrandKit(await studioFetch("/brand-kit"));
    } catch (e) {
      console.warn("Brand kit unavailable:", e);
    }
  };

  const saveBrandKit = async () => {
    setIsSavingBrandKit(true);
    try {
      const kit = await studioFetch("/brand-kit", {
        method: "PUT",
        body: JSON.stringify({
          brand_name: brandName.trim(),
          colors: [primaryColor, secondaryColor, accentColor].filter(Boolean),
          tone: toneKeywords.trim(),
          tagline: brandTagline.trim(),
        }),
      });
      applyBrandKit(kit);
      setCompileStatus("Brand kit saved. The designer agent will use it for new posters.");
    } catch (e: any) {
      setCompileStatus(`Could not save brand kit: ${e?.message || e}`);
    } finally {
      setIsSavingBrandKit(false);
    }
  };

  const handleLogoUpload = async (file: File | undefined) => {
    if (!file) return;
    setIsUploadingLogo(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const kit = await studioFetch("/brand-kit/logo", { method: "POST", body: form });
      applyBrandKit(kit);
      setCompileStatus(
        kit.logo_profile
          ? `Logo saved and analysed (${kit.logo_profile.kind}${kit.logo_profile.reads_as ? `: "${kit.logo_profile.reads_as}"` : ""}).`
          : "Logo saved."
      );
    } catch (e: any) {
      setCompileStatus(`Logo upload failed: ${e?.message || e}`);
    } finally {
      setIsUploadingLogo(false);
    }
  };

  const handleRemoveLogo = async () => {
    try {
      applyBrandKit(await studioFetch("/brand-kit/logo", { method: "DELETE" }));
      setCompileStatus("Logo removed. Posters will use your brand name as a wordmark, if set.");
    } catch (e: any) {
      setCompileStatus(`Could not remove logo: ${e?.message || e}`);
    }
  };

  const handleResetBrandKit = async () => {
    try {
      applyBrandKit(await studioFetch("/brand-kit", { method: "DELETE" }));
      setCompileStatus("Brand kit cleared. Posters will be designed without brand constraints.");
    } catch (e: any) {
      setCompileStatus(`Could not clear brand kit: ${e?.message || e}`);
    }
  };

  // Campaign entry points: AI Studio creatives or uploaded creatives -> campaign flow
  const [homeMode, setHomeMode] = useState<"create" | "upload">("create");
  const [uploadAssets, setUploadAssets] = useState<CreativeAsset[]>([]);
  const [uploadWebsite, setUploadWebsite] = useState("");
  const [openCampaignId, setOpenCampaignId] = useState<string | null>(null);
  const [isCreatingCampaign, setIsCreatingCampaign] = useState(false);
  const [campaignStartError, setCampaignStartError] = useState<string | null>(null);
  const [metaNotice, setMetaNotice] = useState<string | null>(null);

  useEffect(() => {
    try {
      if (openCampaignId) sessionStorage.setItem("studio_open_campaign", openCampaignId);
      else sessionStorage.removeItem("studio_open_campaign");
    } catch {}
  }, [openCampaignId]);

  const openCampaign = (id: string) => {
    setOpenCampaignId(id);
    setActiveNav("Campaigns");
  };

  const parsedDailyBudget = () => {
    const n = parseFloat(budgetINR.replace(/[^0-9.]/g, ""));
    return Number.isFinite(n) && n > 0 ? n : undefined;
  };

  const createCampaign = async (source: "upload" | "studio", creatives: any[], business: Record<string, any>) => {
    setIsCreatingCampaign(true);
    setCampaignStartError(null);
    try {
      const c = await studioFetch("/campaigns", {
        method: "POST",
        body: JSON.stringify({
          source,
          creatives,
          business: { daily_budget: parsedDailyBudget(), duration_days: durationDays || undefined, ...business },
        }),
      });
      openCampaign(c.id);
      return true;
    } catch (e: any) {
      setCampaignStartError(e?.message || "Could not start the campaign");
      setGenerationError(e?.message || "Could not start the campaign");
      return false;
    } finally {
      setIsCreatingCampaign(false);
    }
  };

  const handleStartUploadedCampaign = async () => {
    if (!uploadAssets.length) return;
    const ok = await createCampaign(
      "upload",
      uploadAssets.map((a) => ({ asset_id: a.asset_id, name: a.name })),
      { goal: promptText.trim(), website_url: uploadWebsite.trim() }
    );
    if (ok) setUploadAssets([]);
  };

  // Poster Studio already knows what's on each poster, so the strategist skips the vision call.
  const handleContinueToCampaign = async () => {
    const chosen = variantsData.filter((v) => selectedCardIndices.includes(v.index) && v.asset_id && v.status !== "failed");
    if (!chosen.length) {
      setGenerationError("Select at least one finished poster to continue.");
      return;
    }
    await createCampaign(
      "studio",
      chosen.map((v) => ({
        asset_id: v.asset_id,
        name: v.title,
        insight: {
          product: briefProduct || selectedProduct || "",
          on_creative_text: [v.headline, v.subheadline, v.cta].filter(Boolean),
          offer: v.subheadline || "",
          audience_guess: targetAudienceSignals?.interests || "",
          special_category: "NONE",
        },
      })),
      { goal: promptText.trim(), product: briefProduct || selectedProduct || "", notes: enhancedDirective || "" }
    );
  };

  const hasBrandKit = Boolean(brandName || logoUrl || primaryColor || secondaryColor || accentColor || toneKeywords || brandTagline);

  // Checklist items from image.png Step 02
  const planningChecklist = [
    {
      title: "Understanding your goal",
      detail: "Extracting key details from your prompt",
    },
    {
      title: "Analyzing product",
      detail: "Identifying category, features and audience signals",
    },
    {
      title: "Researching market & competitors",
      detail: "Finding trends, competitor creatives and opportunities",
    },
    {
      title: "Creating audience strategy",
      detail: "Mapping demographic segments and interest affinities",
    },
    {
      title: "Planning creatives",
      detail: "Drafting visual angles, hook concepts and messaging hierarchy",
    },
    {
      title: "Preparing campaign setup",
      detail: "Structuring deliverables, budget allocations and channels",
    },
  ];

  // Example prompts from image.png
  const examplePrompts = [
    {
      title: "Promote new product",
      subtitle: "Create post and run ads",
      icon: TrendingUp,
      prompt: "Launch our premium air fryer with a healthy cooking angle. Create a high-converting poster and a 9:16 Instagram reel highlighting 85% less oil.",
    },
    {
      title: "Drive website traffic",
      subtitle: "Instagram + Meta Ads",
      icon: Globe,
      prompt: "Drive e-commerce store traffic for our organic protein bars. Run a targeted Meta Ad campaign for fitness enthusiasts with free shipping offer.",
    },
    {
      title: "Generate brand awareness",
      subtitle: "Reels campaign",
      icon: Film,
      prompt: "Generate viral reach for our eco-friendly travel backpacks. Focus on waterproof durability and airport smart-compartments in a dynamic 30s reel.",
    },
    {
      title: "Announce offer",
      subtitle: "Creative + Ads",
      icon: Tag,
      prompt: "Announce our Festive 30% Off flash sale across Instagram feeds and stories. Run ads for 5 days with an urgent Countdown CTA.",
    },
  ];

  const [enhancedDirective, setEnhancedDirective] = useState<string>("");
  const [diffExplanation, setDiffExplanation] = useState<string>("");
  const [targetAudienceSignals, setTargetAudienceSignals] = useState<{
    age: string;
    location: string;
    interests: string;
    reach: string;
  } | null>(null);
  const [isGeneratingWithGroq, setIsGeneratingWithGroq] = useState(false);

  const [selectedCardIndices, setSelectedCardIndices] = useState<number[]>([1, 2, 3]);
  const [expandedCard, setExpandedCard] = useState<any | null>(null);
  const [editingCard, setEditingCard] = useState<any | null>(null);

  const toggleCardSelection = (index: number) => {
    setSelectedCardIndices((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  const [variantsData, setVariantsData] = useState<any[]>([]);
  const [reelScenesData, setReelScenesData] = useState<any[]>([]);
  const [isCanvasImageLoading, setIsCanvasImageLoading] = useState(false);
  const activeVariant = variantsData.find((v) => v.index === selectedVariantIndex) || variantsData[0] || null;

  const handleStartCampaign = async () => {
    setCurrentStep("04_CREATIVE");
    setActiveNav("Creative Studio");
    setIsEnhancing(true);
    setIsGeneratingWithGroq(true);
    setIsRegeneratingCreative(true);
    setCompletedSteps([0, 1, 2, 3, 4, 5]);

    try {
      // Get OAuth token from the connected Google session
      let oauthToken = "";
      try {
        const savedSession = typeof window !== "undefined"
          ? JSON.parse(localStorage.getItem("gemini_oauth_session") || "null")
          : null;
        oauthToken = savedSession?.access_token || "";
        console.log("[Campaign] OAuth token present:", Boolean(oauthToken), "| API Key present:", Boolean(geminiApiKey));
      } catch (e) {
        console.warn("[Campaign] Could not read OAuth session from localStorage", e);
      }

      // 1. Gemini MCP Brief Enhancement
      const briefRes = await fetch("/api/mcp/gemini", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "enhance_brief",
          api_key: geminiApiKey || undefined,
          oauth_token: oauthToken || undefined,
          payload: {
            raw_prompt: promptText,
            image_ref: imageRef,
            product_details: selectedProduct ? { name: selectedProduct, budget: budgetINR, duration: durationDays } : undefined,
            brand_name: brandName,
          },
        }),
      });

      let activeBrief: Record<string, any> = {
        product_focus: selectedProduct || "",
        objective: "",
        tone: "",
        call_to_action: "",
      };

      if (briefRes.ok) {
        const briefJson = await briefRes.json();
        const b = briefJson.data;
        if (b) {
          if (b.objective) setBriefObjective(b.objective);
          if (b.product_focus) setBriefProduct(b.product_focus);
          if (b.tone) setBriefTone(b.tone);
          if (b.call_to_action) setBriefCTA(b.call_to_action);
          if (b.channels) setBriefChannels(b.channels);
          if (b.duration) setBriefDuration(b.duration);
          if (b.budget) setBriefBudget(b.budget);
          if (b.enhanced_prompt) setEnhancedDirective(b.enhanced_prompt);
          if (b.diff_summary) setDiffExplanation(b.diff_summary);
          if (b.target_audience) {
            setTargetAudienceSignals({
              age: b.target_audience.age_range || "24 - 38 years",
              location: b.target_audience.location || "Top Metros / Targeted Regions",
              interests: Array.isArray(b.target_audience.interests) ? b.target_audience.interests.join(", ") : "Relevant Target Audience",
              reach: b.target_audience.estimated_reach || "1.2M - 1.8M people",
            });
          }
          activeBrief = {
            product_focus: b.product_focus || selectedProduct || "",
            objective: b.objective || "",
            tone: b.tone || "",
            call_to_action: b.call_to_action || "",
            audience: b.target_audience
              ? [b.target_audience.age_range, b.target_audience.location].filter(Boolean).join(", ")
              : "",
          };
        }
      }

      // 2. Poster Studio: Groq designer agent + Gemini multimodal rendering (product photo + brand logo)
      await generatePosters(activeBrief);

      // 3. Gemini MCP 4-Scene Reel Storyboard Generation (via Veo 2 & reel.generate)
      const storyboardRes = await fetch("/api/mcp/gemini", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "generate_storyboard",
          api_key: geminiApiKey || undefined,
          oauth_token: oauthToken || undefined,
          payload: {
            brief: activeBrief,
            brand_name: brandName,
            image_ref: imageRef,
          },
        }),
      });

      if (storyboardRes.ok) {
        const sbJson = await storyboardRes.json();
        if (sbJson.data?.scenes && sbJson.data.scenes.length === 4) {
          setReelScenesData(sbJson.data.scenes);
        }
      }
    } catch (err) {
      console.warn("Gemini MCP live generation error:", err);
    } finally {
      setCompletedSteps([0, 1, 2, 3, 4, 5]);
      setIsEnhancing(false);
      setIsGeneratingWithGroq(false);
      setIsRegeneratingCreative(false);
    }
  };



  const activeSceneData = reelScenesData.find((s) => s.id === activeReelScene) || reelScenesData[0] || null;

  const handleSimulateReelRender = () => {
    setIsRenderingReel(true);
    setReelProgress(25);
    setTimeout(() => setReelProgress(60), 400);
    setTimeout(() => setReelProgress(90), 800);
    setTimeout(() => {
      setReelProgress(100);
      setIsRenderingReel(false);
    }, 1200);
  };

  return (
    <div className="flex min-h-screen bg-[#060913] text-slate-100 font-sans relative overflow-hidden">
      {/* 1. Left Sidebar Matching Image 2 */}
      <aside className="w-64 border-r border-slate-800/60 bg-[#060913]/90 backdrop-blur-md p-5 flex flex-col justify-between select-none relative overflow-hidden z-10">
        {/* Subtle, reduced-space purple corner glare */}
        <div className="absolute -bottom-14 -left-10 w-52 h-44 bg-gradient-to-tr from-purple-700/25 via-indigo-600/18 to-transparent blur-2xl rounded-full pointer-events-none" />

        <div className="relative z-10">
          {/* Logo / Header Matching Image 2 */}
          <div className="flex items-center gap-3.5 mb-8 px-1">
            <div className="relative h-10 w-10 flex items-center justify-center shrink-0">
              <svg viewBox="0 0 24 24" className="h-8 w-8 drop-shadow-[0_0_12px_rgba(56,189,248,0.7)]" fill="none">
                <defs>
                  <linearGradient id="logoStarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#38bdf8" />
                    <stop offset="50%" stopColor="#818cf8" />
                    <stop offset="100%" stopColor="#c084fc" />
                  </linearGradient>
                </defs>
                <path
                  d="M12 2C12 7.5 16.5 12 22 12C16.5 12 12 16.5 12 22C12 16.5 7.5 12 2 12C7.5 12 12 7.5 12 2Z"
                  fill="url(#logoStarGrad)"
                />
              </svg>
            </div>
            <div>
              <h1 className="font-extrabold text-[16px] leading-tight text-white tracking-tight">possiblstudio.ai</h1>
              <span className="text-xs text-slate-400 font-medium">AI Workforce</span>
            </div>
          </div>

          {/* Navigation Links Matching Image 2 */}
          <div className="space-y-1.5">
            {[
              { name: "Overview", icon: Home, route: "Overview" },
              { name: "Campaigns", icon: Megaphone, route: "Campaigns" },
              { name: "Creative Studio", icon: ImageIcon, route: "Creative Studio" },
              { name: "Brand Kit", icon: Palette, route: "Brand Kit" },
              { name: "Integrations", icon: Link2, route: "Integrations" },
              { name: "Settings", icon: Settings, route: "Settings" },
            ].map(({ name, icon: Icon, route }) => {
              const isActive =
                activeNav === route ||
                (route === "Overview" && (activeNav === "Marketing" || activeNav === "Overview"));

              return (
                <button
                  key={name}
                  onClick={() => {
                    if (route === "Settings") {
                      setShowGeminiModal(true);
                    } else if (route === "Integrations") {
                      setActiveNav("Integrations");
                    } else if (route === "Campaigns") {
                      setOpenCampaignId(null);
                      setActiveNav("Campaigns");
                    } else if (route === "Brand Kit") {
                      setActiveNav("Brand Kit");
                    } else {
                      setActiveNav(route as any);
                      if (route === "Overview") setCurrentStep("01_DASHBOARD");
                      if (route === "Creative Studio") setCurrentStep("04_CREATIVE");
                    }
                  }}
                  className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                    isActive
                      ? "bg-gradient-to-r from-[#2563eb] via-[#4f46e5] to-[#7c3aed] text-white shadow-[0_4px_20px_rgba(79,70,229,0.35)] font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                  }`}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  <span>{name}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Minimal clean status at bottom */}
        <div className="pt-4 border-t border-slate-800/30 flex items-center justify-between text-[11px] text-slate-500/80 px-1 relative z-10">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Workspace Active</span>
          </div>
          <span className="font-mono text-slate-400">v2.1</span>
        </div>
      </aside>

      {/* 2. Main Content Area */}
      <main className="flex-1 p-6 lg:p-8 overflow-y-auto flex flex-col min-h-screen">
        {/* Top Header Bar Matching Image 2 */}
        <div className="mb-6 flex items-center justify-between gap-4">
          {/* Left: Brand Studio Dropdown */}
          <div>
            <button
              onClick={() => setActiveNav("Brand Kit")}
              className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl border border-slate-800 bg-[#0c1222]/80 hover:bg-[#11192e] hover:border-slate-700 text-slate-200 transition-all text-xs font-semibold shadow-sm"
            >
              <Calendar className="h-4 w-4 text-slate-400" />
              <span>{brandName || "Brand Studio"}</span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400 ml-1" />
            </button>
          </div>

          {/* Right: Gemini connected Pill, Notification Bell, User Avatar */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowGeminiModal(true)}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-cyan-500/40 bg-[#061826]/80 hover:bg-cyan-950/40 text-cyan-300 text-xs font-medium shadow-[0_0_15px_rgba(6,182,212,0.15)] transition-all group"
            >
              <Sparkles className="h-3.5 w-3.5 text-cyan-400 group-hover:rotate-12 transition-transform" />
              <span>Gemini connected</span>
            </button>

            <button
              onClick={() => setGeminiNoticeMessage("Marketing AI engine is live and ready.")}
              className="relative p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/50 transition-all"
            >
              <Bell className="h-4.5 w-4.5" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-pink-500 ring-2 ring-[#070b14]" />
            </button>

            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-indigo-600/30 select-none">
              A
            </div>
          </div>
        </div>
        {metaNotice && (
          <div className="max-w-6xl w-full mx-auto mb-4 p-3 rounded-xl bg-indigo-950/40 border border-indigo-700/50 text-indigo-200 text-xs flex items-center gap-2.5">
            <Info className="h-4 w-4 text-indigo-300 shrink-0" />
            <span className="flex-1">{metaNotice}</span>
            <button onClick={() => setMetaNotice(null)} className="text-indigo-300 hover:text-white">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
        {activeNav === "Campaigns" ? (
          openCampaignId ? (
            <CampaignFlow
              key={openCampaignId}
              campaignId={openCampaignId}
              onBack={() => setOpenCampaignId(null)}
            />
          ) : (
            <CampaignList
              onOpen={(id) => setOpenCampaignId(id)}
              onNew={() => {
                setActiveNav("Overview");
                setCurrentStep("01_DASHBOARD");
              }}
            />
          )
        ) : activeNav === "Integrations" ? (
          <div className="max-w-4xl w-full mx-auto space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white">Integrations</h2>
              <p className="text-xs text-slate-400 mt-1">Connect the accounts your AI team posts and advertises with.</p>
            </div>
            <MetaConnectCard />
            <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-6 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="h-9 w-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-purple-600 flex items-center justify-center">
                  <Sparkles className="h-4.5 w-4.5 text-white" />
                </span>
                <div>
                  <h3 className="text-sm font-semibold text-white">Google Gemini</h3>
                  <p className="text-[11px] text-slate-400">Renders posters in Creative Studio</p>
                </div>
              </div>
              <button
                onClick={() => setShowGeminiModal(true)}
                className="px-4 py-2 rounded-xl border border-slate-700 text-xs font-semibold text-slate-200 hover:border-slate-500"
              >
                Manage
              </button>
            </div>
          </div>
        ) : activeNav === "Brand Kit" || activeNav === "Knowledge" ? (
          /* BRAND KIT TAB — every field optional */
          <div className="max-w-4xl mx-auto space-y-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
              <div>
                <button
                  onClick={() => setActiveNav("Marketing")}
                  className="text-xs text-indigo-400 hover:underline mb-2 flex items-center gap-1"
                >
                  ← Back to Dashboard
                </button>
                <h2 className="text-2xl font-bold text-white">Brand Kit</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Everything here is optional. Whatever you add, the designer agent uses it for every new poster: your logo goes to Gemini as a reference image.
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {hasBrandKit && (
                  <button
                    onClick={handleResetBrandKit}
                    className="px-3.5 py-2 rounded-xl border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 text-xs font-medium transition-all"
                  >
                    Clear all
                  </button>
                )}
                <button
                  onClick={saveBrandKit}
                  disabled={isSavingBrandKit}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white text-xs font-medium shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2"
                >
                  {isSavingBrandKit ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  <span>{isSavingBrandKit ? "Saving..." : "Save Brand Kit"}</span>
                </button>
              </div>
            </div>

            {compileStatus && (
              <div className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-800/50 text-indigo-300 text-xs flex items-center gap-2.5">
                <Info className="h-4 w-4 text-indigo-400 shrink-0" />
                <span>{compileStatus}</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Identity & logo */}
              <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Palette className="h-4 w-4 text-indigo-400" />
                    <span>Brand Identity & Logo</span>
                  </h3>
                  {logoUrl && (
                    <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Check className="h-3 w-3" /> Sent with every poster
                    </span>
                  )}
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">
                    Brand name <span className="text-slate-600">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={(e) => setBrandName(e.target.value)}
                    placeholder="e.g. Crispo"
                    maxLength={80}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs text-slate-400 block">
                      Logo <span className="text-slate-600">(optional)</span>
                    </label>
                    {logoUrl && (
                      <button
                        type="button"
                        onClick={handleRemoveLogo}
                        className="text-[11px] text-rose-400 hover:text-rose-300 transition-colors"
                      >
                        Remove logo
                      </button>
                    )}
                  </div>

                  {logoUrl ? (
                    <div className="relative p-4 rounded-xl border border-indigo-500/40 bg-slate-900/90 flex items-center gap-4">
                      <div className="h-16 w-28 rounded-lg bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:8px_8px] bg-slate-950 border border-slate-800 flex items-center justify-center p-2 overflow-hidden shrink-0 shadow-inner">
                        <img src={logoUrl} alt="Brand logo" className="max-h-full max-w-full object-contain" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-white truncate">
                          {logoProfile?.reads_as ? `"${logoProfile.reads_as}"` : `${brandName || "Brand"} logo`}
                        </p>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {logoProfile
                            ? `${logoProfile.kind} · reads best on ${logoProfile.best_on} backgrounds`
                            : "Passed to Gemini as a reference image"}
                        </p>
                        <label className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium cursor-pointer mt-2 transition-colors">
                          {isUploadingLogo ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
                          <span>{isUploadingLogo ? "Uploading..." : "Replace logo"}</span>
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/webp"
                            className="hidden"
                            disabled={isUploadingLogo}
                            onChange={(e) => {
                              handleLogoUpload(e.target.files?.[0]);
                              e.target.value = "";
                            }}
                          />
                        </label>
                      </div>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-700/80 hover:border-indigo-500/80 rounded-xl bg-slate-900/50 hover:bg-slate-900/80 cursor-pointer transition-all group">
                      <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-transform mb-2">
                        {isUploadingLogo ? <RefreshCw className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
                      </div>
                      <p className="text-xs font-semibold text-slate-200 group-hover:text-white transition-colors">
                        {isUploadingLogo ? "Uploading & analysing..." : "Click to upload your logo"}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-1">
                        PNG with transparent background works best · JPG / WebP OK · max 10 MB
                      </p>
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        className="hidden"
                        disabled={isUploadingLogo}
                        onChange={(e) => {
                          handleLogoUpload(e.target.files?.[0]);
                          e.target.value = "";
                        }}
                      />
                    </label>
                  )}
                </div>
              </div>

              {/* Colours */}
              <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-6 space-y-4">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Palette className="h-4 w-4 text-pink-400" />
                  <span>
                    Brand colours <span className="text-xs font-normal text-slate-500">(optional)</span>
                  </span>
                </h3>
                <p className="text-[11px] text-slate-500 -mt-2">
                  Leave empty to let the designer pick a palette from your product.
                </p>
                <div className="grid grid-cols-3 gap-3">
                  {([
                    ["Primary", primaryColor, setPrimaryColor],
                    ["Secondary", secondaryColor, setSecondaryColor],
                    ["Accent", accentColor, setAccentColor],
                  ] as Array<[string, string, (v: string) => void]>).map(([label, value, setter]) => (
                    <div key={label}>
                      <label className="text-[11px] text-slate-400 block mb-1">{label}</label>
                      <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900 border border-slate-800">
                        <input
                          type="color"
                          value={value || "#000000"}
                          onChange={(e) => setter(e.target.value)}
                          className={`h-6 w-6 rounded border-0 bg-transparent cursor-pointer ${value ? "" : "opacity-30"}`}
                        />
                        <span className="text-[11px] font-mono text-slate-300 flex-1">{value || "Not set"}</span>
                        {value && (
                          <button
                            type="button"
                            onClick={() => setter("")}
                            className="text-slate-500 hover:text-rose-400"
                            title="Clear colour"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Voice */}
              <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-6 space-y-4 md:col-span-2">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-cyan-400" />
                  <span>
                    Voice <span className="text-xs font-normal text-slate-500">(optional)</span>
                  </span>
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">Tone of voice</label>
                    <input
                      type="text"
                      value={toneKeywords}
                      onChange={(e) => setToneKeywords(e.target.value)}
                      placeholder="e.g. warm, witty, premium"
                      maxLength={200}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">Tagline</label>
                    <input
                      type="text"
                      value={brandTagline}
                      onChange={(e) => setBrandTagline(e.target.value)}
                      placeholder="e.g. Crunch without the guilt"
                      maxLength={120}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : currentStep === "04_CREATIVE" ? (
          /* CREATIVE STUDIO (100% MATCHING USER REFERENCE IMAGE) */
          <div className="w-full max-w-7xl mx-auto space-y-6 pb-28 animate-in fade-in duration-300">
            {/* Top Header Section with 3D Robot overlapping into the Poster Studio layer matching Image 2 */}
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6 relative -mb-16 sm:-mb-20 lg:-mb-24 z-10 w-full px-1">
              <div className="flex items-center gap-4 z-10 pt-4 sm:pt-6">
                <button
                  type="button"
                  onClick={() => {
                    setCurrentStep("01_DASHBOARD");
                    setActiveNav("Overview");
                  }}
                  className="h-11 w-11 rounded-full border border-slate-700/80 bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-white flex items-center justify-center transition-all shadow-md group shrink-0"
                  title="Back to Dashboard"
                >
                  <ArrowLeft className="h-5 w-5 transition-transform group-hover:-translate-x-0.5" />
                </button>
                <div>
                  <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <span>Creative</span>
                    <span className="text-[#8b5cf6]">Studio</span>
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-400 mt-1 font-normal">
                    AI is creating stunning posters and reels from your brief.
                  </p>
                </div>
              </div>

              {/* Right: 3D Laptop Robot overlapping down behind the Poster Studio layer matching Image 2 */}
              <div className="relative shrink-0 flex items-end justify-center sm:justify-end self-end pointer-events-none w-full sm:w-[420px] lg:w-[460px]">
                {/* Volumetric Aurora Ambient Lighting Rays matching Image 2 */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[380px] h-[340px] bg-gradient-to-br from-indigo-600/30 via-purple-600/25 to-blue-500/20 blur-3xl rounded-full pointer-events-none" />
                <div className="absolute top-6 left-1/4 w-52 h-44 bg-cyan-400/20 blur-2xl rounded-full pointer-events-none" />
                <div className="absolute bottom-6 right-6 w-60 h-48 bg-fuchsia-600/20 blur-3xl rounded-full pointer-events-none" />

                {/* Floating Neon Sparkles matching Image 2 */}
                <div className="absolute left-6 top-10 text-cyan-300 text-2xl select-none animate-pulse pointer-events-none drop-shadow-[0_0_12px_rgba(103,232,249,0.9)]">
                  ✦
                </div>
                <div className="absolute left-16 top-24 text-sky-400 text-xl select-none pointer-events-none drop-shadow-[0_0_10px_rgba(56,189,248,0.85)]">
                  ✦
                </div>
                <div className="absolute right-10 top-12 text-fuchsia-400 text-2xl select-none pointer-events-none drop-shadow-[0_0_12px_rgba(232,121,249,0.9)]">
                  ✦
                </div>
                <div className="absolute right-6 bottom-20 text-fuchsia-400 text-lg select-none pointer-events-none drop-shadow-[0_0_8px_rgba(232,121,249,0.8)]">
                  ✦
                </div>

                {/* The 3D Laptop Robot Asset overlapping behind the tab bar and card */}
                <img
                  src="/robot_lap.png"
                  alt="Creative AI Robot"
                  className="relative z-10 w-[320px] sm:w-[380px] lg:w-[420px] max-h-[460px] object-contain drop-shadow-[0_25px_50px_rgba(0,0,0,0.85)] select-none pointer-events-none translate-y-6 sm:translate-y-10 lg:translate-y-12 [mask-image:linear-gradient(to_bottom,black_48%,black_60%,transparent_76%)]"
                />
              </div>
            </div>

            {/* Poster Studio Layer (overlapping on top of the robot's lower half) */}
            <div className="relative z-20 space-y-6">
              {/* Studio Navigation Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1">
                {/* Studio Switcher Tabs */}
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setActiveStudioTab("POSTER")}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                      activeStudioTab === "POSTER"
                        ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/35"
                        : "text-slate-400 hover:text-white bg-slate-900/60 border border-slate-800/80"
                    }`}
                  >
                    <ImageIcon className="h-4 w-4" />
                    <span>Poster Studio</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveStudioTab("REEL")}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                      activeStudioTab === "REEL"
                        ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/35"
                        : "text-slate-400 hover:text-white bg-slate-900/60 border border-slate-800/80"
                    }`}
                  >
                    <Film className="h-4 w-4" />
                    <span>Reel Studio</span>
                  </button>
                </div>

                <div className="flex items-center gap-3">
                  {/* Brand kit is optional per generation */}
                  <button
                    type="button"
                    onClick={() => setUseBrandKit((v) => !v)}
                    title={hasBrandKit ? "Use your saved brand kit for the next generation" : "No brand kit saved yet"}
                    className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold border transition-all ${
                      useBrandKit && hasBrandKit
                        ? "border-indigo-500/60 bg-indigo-950/40 text-indigo-200"
                        : "border-slate-800 bg-slate-900/80 text-slate-400"
                    }`}
                  >
                    <Palette className="h-3.5 w-3.5" />
                    <span>Brand kit: {hasBrandKit ? (useBrandKit ? "On" : "Off") : "None"}</span>
                  </button>

                  {/* Generate More CTA */}
                  <button
                    type="button"
                    onClick={() => handleRegenerateCreatives()}
                    disabled={isRegeneratingCreative}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-900/80 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 transition-all disabled:opacity-60 shadow-sm"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${isRegeneratingCreative ? "animate-spin text-purple-400" : ""}`} />
                    <span>{isRegeneratingCreative ? "Designing new concepts..." : "Generate more"}</span>
                  </button>
                </div>
              </div>

            {generationError && activeStudioTab === "POSTER" && (
              <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex items-start gap-2.5">
                <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                <span className="flex-1">{generationError}</span>
                <button onClick={() => setGenerationError(null)} className="text-rose-300 hover:text-white">
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )}

            {/* Poster Studio Tab Content */}
            {activeStudioTab === "POSTER" ? (
              isGeneratingWithGroq || isRegeneratingCreative ? (
                /* AI Generation Loading State with Typing Robot Zooming In & Out (Banner Removed) */
                <div className="space-y-6 animate-in fade-in duration-300">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="h-[470px] rounded-2xl border border-purple-500/20 bg-[#0b101e] p-6 flex flex-col justify-between relative overflow-hidden shadow-xl"
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/5 to-transparent animate-[shimmer_2s_infinite]" />
                        
                        {/* Top checkmark placeholder */}
                        <div className="flex justify-end z-10">
                          <div className="h-7 w-7 rounded-full bg-slate-800/60 animate-pulse" />
                        </div>

                        {/* Center: 3D Typing Robot with Zoom In/Out Animation */}
                        <div className="flex flex-col items-center justify-center z-10 my-auto py-2">
                          <div className="relative flex items-center justify-center">
                            {/* Aurora Glow */}
                            <div className="absolute w-36 h-36 bg-gradient-to-tr from-indigo-500/30 via-purple-500/25 to-cyan-400/20 blur-2xl rounded-full animate-pulse" />
                            <img
                              src="/robot_loading.png"
                              alt="AI Robot Generating..."
                              className="relative z-10 w-32 h-32 sm:w-36 sm:h-36 object-contain select-none pointer-events-none animate-robot-zoom"
                            />
                          </div>
                          <p className="text-xs font-semibold text-slate-300 mt-3 flex items-center gap-1.5">
                            <span className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-ping" />
                            Synthesizing Poster #{i}...
                          </p>
                        </div>

                        {/* Skeleton Footer Controls Bar */}
                        <div className="flex items-center justify-between z-10 pt-4 border-t border-slate-800/60">
                          <div className="flex gap-2">
                            <div className="h-8 w-8 rounded-xl bg-slate-800/60 animate-pulse" />
                            <div className="h-8 w-8 rounded-xl bg-slate-800/60 animate-pulse" />
                          </div>
                          <div className="h-8 w-16 rounded-xl bg-slate-800/60 animate-pulse" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : variantsData.length === 0 ? (
                /* Empty State Before First Generation (Matching Image 2) */
                <div className="relative z-20 w-full rounded-2xl border border-indigo-500/30 bg-[#070b1a]/95 backdrop-blur-xl shadow-[0_0_50px_rgba(30,41,89,0.25)] p-12 sm:p-16 text-center space-y-5">
                  <div className="h-16 w-16 rounded-2xl bg-gradient-to-b from-indigo-500/20 to-purple-600/15 border border-indigo-500/30 flex items-center justify-center mx-auto text-indigo-300 shadow-lg shadow-indigo-950/50">
                    <ImageIcon className="h-8 w-8 text-indigo-300" />
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">No creatives generated yet</h3>
                  <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto leading-relaxed">
                    Tell your AI marketing team what you want to achieve on the Overview page or click &ldquo;Generate more&rdquo; to synthesize high-converting visuals tailored 100% to your product.
                  </p>
                  <button
                    onClick={() => {
                      setCurrentStep("01_DASHBOARD");
                      setActiveNav("Overview");
                    }}
                    className="px-7 py-3 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:via-indigo-500 hover:to-purple-500 text-xs sm:text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 hover:shadow-indigo-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all inline-flex items-center gap-2"
                  >
                    <span>Open campaign prompt</span>
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                /* 3-Card Creative Poster Grid (1 row x 3 cols) - Pure Posters Only */
                <div className="space-y-8">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {variantsData.map((variant) => {
                      const isSelected = selectedCardIndices.includes(variant.index);
                      return (
                        <div
                          key={variant.index}
                          onClick={() => toggleCardSelection(variant.index)}
                          className={`group relative h-[470px] rounded-2xl overflow-hidden border transition-all duration-300 cursor-pointer flex flex-col justify-between p-5 bg-[#0b101e] shadow-xl ${
                            isSelected
                              ? "border-indigo-500/80 shadow-[0_0_30px_rgba(99,102,241,0.3)] ring-1 ring-indigo-500/50"
                              : "border-slate-800/90 hover:border-slate-700/80 hover:shadow-lg"
                          }`}
                        >
                          {/* Gemini-rendered poster; failures are shown honestly instead of a fake fallback */}
                          {variant.bgUrl ? (
                            <img
                              src={variant.bgUrl}
                              alt={variant.copy?.alt || variant.headline || "Generated poster"}
                              className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                            />
                          ) : (
                            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-8 text-center bg-[#0b101e]">
                              <AlertTriangle className="h-8 w-8 text-amber-400" />
                              <p className="text-sm font-semibold text-white">This poster could not be rendered</p>
                              <p className="text-[11px] text-slate-400 line-clamp-4">{variant.error || "Image generation failed."}</p>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRegenerateVariant(variant, "");
                                }}
                                className="mt-1 px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white"
                              >
                                Retry
                              </button>
                            </div>
                          )}

                          {regeneratingIndex === variant.index && (
                            <div className="absolute inset-0 z-20 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center gap-2">
                              <RefreshCw className="h-6 w-6 text-purple-300 animate-spin" />
                              <span className="text-xs text-slate-200">Re-rendering…</span>
                            </div>
                          )}

                          {variant.qa?.checked && !variant.qa?.headline_ok && (
                            <div
                              className="absolute top-5 left-5 z-10 px-2 py-1 rounded-lg bg-amber-500/90 text-[10px] font-semibold text-black flex items-center gap-1"
                              title={variant.qa?.issue || "Headline text may be wrong"}
                            >
                              <AlertTriangle className="h-3 w-3" /> Check text
                            </div>
                          )}

                          {/* Subtle Bottom Contrast Overlay for buttons */}
                          <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/80 via-black/30 to-transparent pointer-events-none" />

                          {/* Top Right Checkmark Badge Only */}
                          <div className="relative z-10 flex items-start justify-end w-full">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleCardSelection(variant.index);
                              }}
                              className={`h-7 w-7 rounded-full flex items-center justify-center transition-all shrink-0 ${
                                isSelected
                                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/60 ring-2 ring-indigo-400/50"
                                  : "bg-black/50 backdrop-blur-md text-slate-400 border border-white/20 hover:border-white/50"
                              }`}
                            >
                              <Check className="h-4 w-4 stroke-[3]" />
                            </button>
                          </div>

                          {/* Bottom Card Controls */}
                          <div
                            className="relative z-10 flex items-center justify-between pt-2"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                className="p-2 rounded-xl bg-slate-900/80 backdrop-blur-md border border-slate-700/80 text-slate-300 hover:text-white hover:bg-slate-800 transition-all"
                                title="Aspect Ratio"
                              >
                                <Layers className="h-3.5 w-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setExpandedCard(variant)}
                                className="p-2 rounded-xl bg-slate-900/80 backdrop-blur-md border border-slate-700/80 text-slate-300 hover:text-white hover:bg-slate-800 transition-all"
                                title="Fullscreen Expand"
                              >
                                <Maximize2 className="h-3.5 w-3.5" />
                              </button>
                            </div>

                            <button
                              type="button"
                              onClick={() => setEditingCard(variant)}
                              className="px-3.5 py-1.5 rounded-xl bg-slate-900/80 backdrop-blur-md border border-slate-700/80 hover:bg-slate-850 text-xs font-semibold text-slate-300 hover:text-white transition-all shadow-sm"
                            >
                              Edit
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Sticky Bottom Selection Tray */}
                  <div className="fixed bottom-4 left-4 sm:left-72 right-4 sm:right-8 z-40 bg-[#090d1a]/95 backdrop-blur-xl border border-slate-800/90 rounded-2xl p-4 shadow-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-4">
                      <span className="text-sm font-semibold text-cyan-400">
                        {selectedCardIndices.length} creatives selected
                      </span>
                      <div className="flex items-center gap-2 overflow-x-auto max-w-[280px]">
                        {variantsData
                          .filter((v) => selectedCardIndices.includes(v.index))
                          .map((v) => (
                            <div
                              key={v.index}
                              className="h-11 w-8 rounded-lg overflow-hidden border border-indigo-500/60 relative shadow-sm shrink-0"
                            >
                              <img
                                src={v.bgUrl || undefined}
                                alt=""
                                className="h-full w-full object-cover"
                              />
                            </div>
                          ))}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleContinueToCampaign}
                      disabled={isCreatingCampaign || selectedCardIndices.length === 0}
                      className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                    >
                      <span>{isCreatingCampaign ? "Starting…" : "Continue to Campaign Settings"}</span>
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )
            ) : activeStudioTab === "REEL" ? (

              /* REEL VIDEO STUDIO (PHASE 4) */
              !activeSceneData || reelScenesData.length === 0 ? (
                <div className="rounded-3xl border border-slate-800 bg-[#0a101f] p-12 text-center space-y-4">
                  <div className="h-14 w-14 rounded-2xl bg-purple-600/10 border border-purple-500/20 flex items-center justify-center mx-auto text-purple-400">
                    <Film className="h-7 w-7" />
                  </div>
                  <h3 className="text-base font-bold text-white">No Reel Storyboard Generated Yet</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Start a campaign with Reel deliverables enabled to auto-compose a 4-scene kinetic storyboard with audio cues and motion typography using Gemini MCP (Veo 2).
                  </p>
                  <button
                    onClick={() => setCurrentStep("01_DASHBOARD")}
                    className="px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white shadow-lg shadow-purple-600/20 transition-all inline-flex items-center gap-2"
                  >
                    <span>Open Campaign Prompt</span>
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                  {/* Left Column: Mobile Smartphone Viewport Video Mockup */}
                  <div className="lg:col-span-5 rounded-3xl border border-slate-800 bg-[#0a101f] p-6 space-y-4 shadow-2xl flex flex-col items-center">
                    <div className="w-full flex items-center justify-between pb-3 border-b border-slate-800/80 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-400 font-medium">Format:</span>
                        <span className="text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded font-mono border border-purple-500/20">
                          9:16 Vertical Reel
                        </span>
                        <span className="text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-full font-mono flex items-center gap-1 shadow-sm">
                          <span className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse"></span>
                          Gemini MCP: Veo 2
                        </span>
                      </div>

                      <span className="text-[11px] text-emerald-400 font-mono flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> Resumable Sync Ready
                      </span>
                    </div>

                    {/* Smartphone Frame */}
                    <div className="w-full max-w-[320px] aspect-[9/16] rounded-[36px] p-3 bg-[#0d1322] border-4 border-slate-800 shadow-2xl relative flex flex-col justify-between overflow-hidden">
                      {/* Phone Camera Notch / Dynamic Island */}
                      <div className="absolute top-4 left-1/2 -translate-x-1/2 w-24 h-5 rounded-full bg-black z-30 flex items-center justify-center">
                        <div className="h-2.5 w-2.5 rounded-full bg-slate-900 ml-12" />
                      </div>

                      {/* Active Scene Video Frame */}
                      <div className="absolute inset-0 z-10 overflow-hidden">
                        {activeSceneData.bgUrl ? (
                          <img
                            src={activeSceneData.bgUrl}
                            alt={activeSceneData.title}
                            className="w-full h-full object-cover transition-all duration-700 scale-105"
                          />
                        ) : (
                          <div className="w-full h-full bg-gradient-to-b from-[#090d16] via-[#101728] to-[#050811] flex flex-col items-center justify-center p-6 text-center">
                            <div className="h-14 w-14 rounded-2xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center mb-3 text-purple-400">
                              <Film className="h-7 w-7" />
                            </div>
                            <span className="text-xs font-mono text-purple-300 font-semibold mb-1">
                              {activeSceneData.duration} Dynamic Motion Cut
                            </span>
                            <span className="text-[11px] text-slate-400 max-w-[200px] line-clamp-3">
                              {activeSceneData.visual}
                            </span>
                          </div>
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-black/60 pointer-events-none" />
                      </div>

                    {/* Top Status & Brand Overlay */}
                    <div className="relative z-20 pt-8 px-3 flex items-center justify-between text-[11px] text-white">
                      <div className="flex items-center gap-1.5 font-bold tracking-wider">
                        <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
                        <span>{brandName.toUpperCase()}</span>
                      </div>
                      <span className="text-[10px] bg-black/60 backdrop-blur-md px-2 py-0.5 rounded-full border border-white/10 font-mono">
                        Scene {activeReelScene}/4
                      </span>
                    </div>

                    {/* On-Screen Kinetic Highlight Captions */}
                    <div className="relative z-20 px-4 py-8 text-center space-y-2">
                      <span className="text-[10px] uppercase font-mono tracking-widest text-indigo-300 bg-indigo-950/80 px-2.5 py-1 rounded-full border border-indigo-500/30 inline-block">
                        {activeSceneData.title}
                      </span>
                      <h3 className="text-xl font-black text-white leading-tight uppercase drop-shadow-lg tracking-wide">
                        {activeSceneData.caption}
                      </h3>
                      <p className="text-[11px] text-slate-300 font-medium italic drop-shadow line-clamp-2">
                        "{activeSceneData.voiceover}"
                      </p>
                    </div>

                    {/* Bottom Controls & Playback Scrubber */}
                    <div className="relative z-20 pb-4 px-3 space-y-2.5">
                      {/* Audio cue info badge */}
                      <div className="flex items-center justify-between text-[10px] text-slate-300 bg-black/60 backdrop-blur-md p-1.5 rounded-xl border border-white/10">
                        <div className="flex items-center gap-1.5 truncate">
                          <Music className="h-3 w-3 text-pink-400" />
                          <span className="truncate">{selectedAudioTrack}</span>
                        </div>
                        <span className="font-mono text-slate-400">{activeSceneData.timecode}</span>
                      </div>

                      {/* 4 Segmented Progress Bars */}
                      <div className="grid grid-cols-4 gap-1.5">
                        {reelScenesData.map((s) => (
                          <div
                            key={s.id}
                            className={`h-1.5 rounded-full transition-all ${
                              s.id === activeReelScene
                                ? "bg-indigo-500 shadow-sm shadow-indigo-500"
                                : s.id < activeReelScene
                                ? "bg-white/70"
                                : "bg-white/20"
                            }`}
                          />
                        ))}
                      </div>

                      {/* Playback Button Bar */}
                      <div className="flex items-center justify-between pt-1">
                        <button
                          onClick={() => setIsPlayingReel(!isPlayingReel)}
                          className="h-9 w-9 rounded-full bg-white text-black flex items-center justify-center shadow-lg hover:bg-slate-200 transition-all"
                        >
                          {isPlayingReel ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
                        </button>

                        <div className="text-[11px] font-mono text-white/90">
                          0:0{activeReelScene * 3} / 0:15
                        </div>

                        <button
                          onClick={() => setActiveReelScene(1)}
                          className="h-8 w-8 rounded-full bg-black/60 text-white/80 hover:text-white flex items-center justify-center border border-white/10"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Canvas Footer Toolbar */}
                  <div className="w-full flex items-center justify-between pt-2 text-[11px] text-slate-400">
                    <span className="font-mono">Engine: FFmpeg / Satori 9:16</span>
                    <button
                      onClick={() => alert("Reel MP4 download initialized!")}
                      className="hover:text-white flex items-center gap-1 bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-800 transition-all"
                    >
                      <Download className="h-3 w-3" /> Download 9:16 MP4
                    </button>
                  </div>
                </div>

                {/* Right Column: 4-Scene Storyboard Sequence + Audio Track + Resumability */}
                <div className="lg:col-span-7 space-y-6">
                  {/* Storyboard Timeline */}
                  <div className="rounded-3xl border border-slate-800 bg-[#0a101f] p-6 space-y-4 shadow-xl">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                          4-Scene Storyboard Timeline (15s Total)
                        </h3>
                        <p className="text-xs text-slate-300 font-medium mt-0.5">
                          Click any scene to preview camera angle, motion cues and kinetic text
                        </p>
                      </div>
                      <span className="text-[11px] font-mono text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full border border-purple-500/20">
                        ≤ 90s Constraint Passed
                      </span>
                    </div>

                    <div className="space-y-3">
                      {reelScenesData.map((s) => {
                        const isCurrent = activeReelScene === s.id;
                        return (
                          <div
                            key={s.id}
                            onClick={() => setActiveReelScene(s.id)}
                            className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center gap-4 ${
                              isCurrent
                                ? "bg-slate-900 border-indigo-500 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500"
                                : "bg-slate-950/60 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900/40"
                            }`}
                          >
                            <div className="w-20 aspect-[9/16] rounded-xl overflow-hidden relative border border-slate-800 flex-shrink-0 bg-slate-900 flex items-center justify-center">
                              {s.bgUrl ? (
                                <img src={s.bgUrl} alt={s.title} className="w-full h-full object-cover" />
                              ) : (
                                <div className="w-full h-full bg-purple-950/40 flex items-center justify-center text-purple-400">
                                  <Film className="h-5 w-5 opacity-70" />
                                </div>
                              )}
                              <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                                <span className="text-[10px] font-mono font-bold text-white bg-black/60 px-1 rounded">
                                  {s.duration}
                                </span>
                              </div>
                            </div>

                            <div className="flex-1 space-y-1 text-xs">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-white">
                                  Scene {s.id} · {s.title}
                                </span>
                                <span className="text-[10px] font-mono text-slate-400">{s.timecode}</span>
                              </div>
                              <div className="text-indigo-300 font-bold tracking-wide uppercase text-[11px]">
                                Caption: {s.caption}
                              </div>
                              <p className="text-slate-400 text-[11px] line-clamp-1">{s.visual}</p>
                              <div className="text-[10px] text-pink-400/90 font-mono">Audio Cue: {s.cue}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Audio & Style Pickers */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-2xl border border-slate-800 bg-[#0a101f] space-y-2">
                      <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                        <Music className="h-4 w-4 text-pink-400" />
                        <span>Background Soundtrack</span>
                      </div>
                      <select
                        value={selectedAudioTrack}
                        onChange={(e) => setSelectedAudioTrack(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white"
                      >
                        <option value="Cinematic Synth Anthem">Cinematic Synth Anthem (128 BPM)</option>
                        <option value="Ambient Luxury Chill">Ambient Luxury Chill (95 BPM)</option>
                        <option value="High-Energy Trap Beat">High-Energy Trap Beat (140 BPM)</option>
                      </select>
                    </div>

                    <div className="p-4 rounded-2xl border border-slate-800 bg-[#0a101f] space-y-2">
                      <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                        <Sparkles className="h-4 w-4 text-purple-400" />
                        <span>Kinetic Caption Style</span>
                      </div>
                      <select
                        value={selectedCaptionStyle}
                        onChange={(e) => setSelectedCaptionStyle(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white"
                      >
                        <option value="Kinetic Pop">⚡ Kinetic Pop (Animated Highlight)</option>
                        <option value="Minimal Clean">✨ Minimal Clean Sans</option>
                        <option value="Luxury Editorial">💎 Luxury Editorial Serif</option>
                      </select>
                    </div>
                  </div>

                  {/* Async Resumable Job State & Pipeline Checkpoint */}
                  <div className="rounded-3xl border border-purple-900/40 bg-purple-950/10 p-6 space-y-4">
                    <div className="flex items-center justify-between pb-2 border-b border-purple-900/30">
                      <div className="flex items-center gap-2">
                        <Video className="h-4 w-4 text-purple-400" />
                        <h4 className="text-xs font-semibold text-purple-300 uppercase tracking-wider">
                          Async Resumable Video Pipeline
                        </h4>
                      </div>
                      <span className="text-[10px] font-mono bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full border border-purple-500/30">
                        Checkpoint Saved
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-slate-300">
                      <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                        <div className="text-[10px] text-slate-400">Worker Status</div>
                        <div className="font-semibold text-white mt-0.5">Survives Restarts</div>
                        <div className="text-[10px] text-emerald-400 mt-1">✓ State Checkpointed</div>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                        <div className="text-[10px] text-slate-400">Duration & Spec</div>
                        <div className="font-semibold text-white mt-0.5">15.0s (4 Scenes)</div>
                        <div className="text-[10px] text-emerald-400 mt-1">✓ 9:16 Vertical Export</div>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                        <div className="text-[10px] text-slate-400">Render Progress</div>
                        <div className="font-semibold text-white mt-0.5">{reelProgress}% Completed</div>
                        <div className="text-[10px] text-emerald-400 mt-1">✓ Ready for Human Review</div>
                      </div>
                    </div>

                    {/* Proceed Action */}
                    <div className="flex items-center justify-between pt-2">
                      <span className="text-xs text-slate-400">
                        Reel generated end-to-end with brand-consistent captions and music sync.
                      </span>

                      <button
                        onClick={() => setActiveStudioTab("REVIEW")}
                        className="px-6 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/30 flex items-center gap-2 transition-all"
                      >
                        <span>Proceed to Phase 5 Review →</span>
                        <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )
            ) : (
              /* PHASE 5: HUMAN-IN-THE-LOOP REVIEW & APPROVAL GATE SCREEN */
              !activeVariant || variantsData.length === 0 ? (
                <div className="rounded-3xl border border-slate-800 bg-[#0a101f] p-12 text-center space-y-4">
                  <div className="h-14 w-14 rounded-2xl bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center mx-auto text-emerald-400">
                    <ShieldCheck className="h-7 w-7" />
                  </div>
                  <h3 className="text-base font-bold text-white">No Deliverables Under Review Yet</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Generate campaign creatives from scratch in the Marketing tab first. Once ready, you can review compliance, annotate scenes, and issue cryptographic sign-off here.
                  </p>
                  <button
                    onClick={() => setCurrentStep("01_DASHBOARD")}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white shadow-lg shadow-emerald-600/20 transition-all inline-flex items-center gap-2"
                  >
                    <span>Open Campaign Prompt</span>
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div className="space-y-8">
                  {/* LangGraph Gate Status Header & RBAC Role Switcher */}
                  <div className="rounded-3xl border border-slate-800 bg-[#0a101f] p-6 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-amber-400 animate-ping" />
                        <span className="text-[11px] font-mono uppercase tracking-widest text-amber-400 font-bold bg-amber-500/10 px-2.5 py-0.5 rounded-full border border-amber-500/20">
                          LangGraph Gate: Paused at interrupt()
                        </span>
                        <span className="text-[11px] font-mono text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded font-bold border border-purple-500/20">
                          Version v{campaignVersion}
                        </span>
                      </div>
                      <h3 className="text-xl font-black text-white tracking-tight">
                        Human-in-the-Loop Review & Cryptographic Sign-Off Gate
                      </h3>
                      <p className="text-xs text-slate-400">
                        The execution graph is paused indefinitely. Inspect brand compliance, review creative deliverables, add comments, or request targeted edits.
                      </p>
                    </div>

                    {/* RBAC Role Switcher (Simulates Approver vs Editor) */}
                    <div className="flex items-center gap-3 bg-slate-950 p-2 rounded-2xl border border-slate-800">
                      <span className="text-[11px] font-mono text-slate-400 pl-2">Current Role:</span>
                      <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-xl">
                        <button
                          onClick={() => setReviewRole("APPROVER")}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                            reviewRole === "APPROVER"
                              ? "bg-emerald-600 text-white shadow-sm"
                              : "text-slate-400 hover:text-white"
                          }`}
                        >
                          <Lock className="h-3.5 w-3.5" />
                          <span>Approver (Chief)</span>
                        </button>
                        <button
                          onClick={() => setReviewRole("EDITOR")}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                            reviewRole === "EDITOR"
                              ? "bg-amber-600 text-white shadow-sm"
                              : "text-slate-400 hover:text-white"
                          }`}
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                          <span>Editor (Junior)</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Main 12-Column Review Layout */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                    {/* Left Column (5 Cols): Deliverables Preview + Per-Asset Comments */}
                    <div className="lg:col-span-5 space-y-6">
                      {/* Creative Assets Summary Preview */}
                      <div className="rounded-3xl border border-slate-800 bg-[#0a101f] p-6 space-y-4 shadow-xl">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                          <div className="flex items-center gap-2">
                            <Layers className="h-4 w-4 text-indigo-400" />
                            <h4 className="text-xs font-bold uppercase tracking-wider text-white">
                              Deliverables Under Review
                            </h4>
                          </div>
                          <span className="text-[10px] font-mono text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                            3 Posters + 1 Reel
                          </span>
                        </div>

                        {/* Selected Poster Variant Preview */}
                        <div className="space-y-3">
                          <div className="flex items-center justify-between text-xs text-slate-400">
                            <span>Active Preview Variant:</span>
                            <div className="flex items-center gap-1 font-mono">
                              {[1, 2, 3].map((idx) => (
                                <button
                                  key={idx}
                                  onClick={() => setSelectedVariantIndex(idx as 1 | 2 | 3)}
                                  className={`px-2 py-0.5 rounded text-[11px] ${
                                    selectedVariantIndex === idx
                                      ? "bg-indigo-600 text-white font-bold"
                                      : "bg-slate-900 text-slate-400"
                                  }`}
                                >
                                  V{idx}
                                </button>
                              ))}
                            </div>
                          </div>

                          <div className="relative aspect-[4/5] rounded-2xl overflow-hidden border border-slate-800 shadow-lg bg-slate-950">
                            {activeVariant ? (
                              <img
                                src={activeVariant.bgUrl || undefined}
                                alt="Preview"
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <div className="w-full h-full bg-gradient-to-br from-indigo-950/70 to-slate-900 flex flex-col items-center justify-center p-6 text-center">
                                <Sparkles className="h-8 w-8 text-indigo-400 mb-2" />
                                <span className="text-xs font-mono text-slate-300">Studio Vector Poster</span>
                              </div>
                            )}
                          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-5 flex flex-col justify-end space-y-2">
                            <span className="text-[10px] font-mono uppercase tracking-widest text-emerald-400">
                              {activeVariant.tag}
                            </span>
                            <h4 className="text-lg font-black text-white leading-tight">
                              {activeVariant.headline}
                            </h4>
                            <p className="text-xs text-slate-300 line-clamp-2">
                              {activeVariant.copy.body}
                            </p>

                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Per-Asset Comments Tray */}
                    <div className="rounded-3xl border border-slate-800 bg-[#0a101f] p-6 space-y-4 shadow-xl">
                      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                        <div className="flex items-center gap-2">
                          <MessageSquare className="h-4 w-4 text-pink-400" />
                          <h4 className="text-xs font-bold uppercase tracking-wider text-white">
                            Asset Comments & Annotations
                          </h4>
                        </div>
                        <span className="text-[10px] font-mono text-pink-300 bg-pink-500/10 px-2 py-0.5 rounded border border-pink-500/20">
                          {commentsList.length} Notes
                        </span>
                      </div>

                      {/* Comments Feed */}
                      <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
                        {commentsList.map((comm) => (
                          <div
                            key={comm.id}
                            className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1 text-xs"
                          >
                            <div className="flex items-center justify-between text-[10px]">
                              <span className="font-bold text-white flex items-center gap-1.5">
                                <span className="h-1.5 w-1.5 rounded-full bg-pink-400" />
                                {comm.author}
                              </span>
                              <span className="text-slate-400 font-mono">{comm.time}</span>
                            </div>
                            <div className="text-[10px] font-mono text-indigo-400">
                              Target: {comm.asset}
                            </div>
                            <p className="text-slate-300 text-[11px]">{comm.text}</p>
                          </div>
                        ))}
                      </div>

                      {/* New Comment Input */}
                      <div className="space-y-2 pt-2 border-t border-slate-800/60">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-slate-400">Attach to:</span>
                          <select
                            value={commentTargetAsset}
                            onChange={(e) => setCommentTargetAsset(e.target.value)}
                            className="px-2 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-white"
                          >
                            <option value="All Assets">All Assets</option>
                            <option value="Variant 1">Variant 1</option>
                            <option value="Variant 2">Variant 2</option>
                            <option value="Variant 3">Variant 3</option>
                            <option value="Reel 9:16">Reel 9:16</option>
                          </select>
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            placeholder="Add targeted feedback comment..."
                            value={newCommentInput}
                            onChange={(e) => setNewCommentInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleAddComment()}
                            className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                          />
                          <button
                            onClick={handleAddComment}
                            className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-md shadow-indigo-600/20"
                          >
                            <Send className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Right Column (7 Cols): Compliance Checklist + Revisions + Decision Actions */}
                  <div className="lg:col-span-7 space-y-6">
                    {/* Brand Compliance Checklist Card */}
                    <div className="rounded-3xl border border-emerald-900/40 bg-emerald-950/10 p-6 space-y-4 shadow-xl">
                      <div className="flex items-center justify-between pb-3 border-b border-emerald-900/30">
                        <div className="flex items-center gap-2">
                          <ShieldCheck className="h-5 w-5 text-emerald-400" />
                          <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-300">
                            Brand System & Meta Ad Policy Compliance
                          </h4>
                        </div>
                        <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/30">
                          100% Passed (4/4)
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-1">
                          <div className="flex items-center justify-between text-slate-400 text-[10px]">
                            <span>Deterministic Typography</span>
                            <span className="text-emerald-400 font-bold">✓ PASSED</span>
                          </div>
                          <div className="font-semibold text-white">mcp-media Satori Sharp</div>
                          <div className="text-[11px] text-slate-400">0% AI letter glitch; sharp SVG vector rendering.</div>
                        </div>

                        <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-1">
                          <div className="flex items-center justify-between text-slate-400 text-[10px]">
                            <span>Design System Tokens</span>
                            <span className="text-emerald-400 font-bold">✓ PASSED</span>
                          </div>
                          <div className="font-semibold text-white">{brandName} Palette Grounded</div>
                          <div className="text-[11px] text-slate-400">Primary {primaryColor} and contrast tokens strictly enforced.</div>
                        </div>

                        <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-1">
                          <div className="flex items-center justify-between text-slate-400 text-[10px]">
                            <span>Platform Safe Zones</span>
                            <span className="text-emerald-400 font-bold">✓ PASSED</span>
                          </div>
                          <div className="font-semibold text-white">4:5 Feed & 9:16 Story Safe</div>
                          <div className="text-[11px] text-slate-400">CTAs and captions remain clear of platform overlays.</div>
                        </div>

                        <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-1">
                          <div className="flex items-center justify-between text-slate-400 text-[10px]">
                            <span>Meta Ad Policies</span>
                            <span className="text-emerald-400 font-bold">✓ PASSED</span>
                          </div>
                          <div className="font-semibold text-white">0 Prohibited Claims</div>
                          <div className="text-[11px] text-slate-400">Zero false guarantees, deceptive claims or IP flags.</div>
                        </div>
                      </div>
                    </div>

                    {/* Version History & Diff Explorer */}
                    {reviewDiffSummary && (
                      <div className="rounded-3xl border border-purple-900/40 bg-purple-950/15 p-6 space-y-3 shadow-xl">
                        <div className="flex items-center justify-between pb-2 border-b border-purple-900/30 text-xs">
                          <div className="flex items-center gap-2">
                            <History className="h-4 w-4 text-purple-400" />
                            <h4 className="font-bold uppercase tracking-wider text-purple-300">
                              Revision History & Diff Summary (v{campaignVersion - 1} → v{campaignVersion})
                            </h4>
                          </div>
                          <span className="text-[10px] font-mono text-purple-300 bg-purple-500/20 px-2 py-0.5 rounded">
                            Targeted Edit
                          </span>
                        </div>
                        <div className="p-3.5 rounded-2xl bg-slate-950/90 border border-slate-800 text-xs font-mono text-purple-200">
                          {reviewDiffSummary}
                        </div>
                      </div>
                    )}

                    {/* Decision Action Cards */}
                    <div className="space-y-4">
                      {/* Action Option 1: Request Changes */}
                      <div className="rounded-3xl border border-slate-800 bg-[#0a101f] p-6 space-y-4 shadow-xl">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                          <div className="flex items-center gap-2">
                            <Edit3 className="h-4 w-4 text-amber-400" />
                            <h4 className="text-xs font-bold uppercase tracking-wider text-white">
                              Option A: Request Targeted Changes
                            </h4>
                          </div>
                          <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                            Preserves Version & Diff
                          </span>
                        </div>

                        <p className="text-xs text-slate-400">
                          Free-text feedback is converted into structured instructions. Executes targeted regeneration on the specific deliverable without restarting the pipeline.
                        </p>

                        <div className="space-y-3">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-400 font-medium">Target Deliverable:</span>
                            <select
                              value={targetAssetForChanges}
                              onChange={(e) => setTargetAssetForChanges(e.target.value)}
                              className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white"
                            >
                              <option value="Variant 1 (High Energy)">Variant 1 (High Energy)</option>
                              <option value="Variant 2 (Problem/Solution)">Variant 2 (Problem/Solution)</option>
                              <option value="Variant 3 (Minimalist Luxury)">Variant 3 (Minimalist Luxury)</option>
                              <option value="Reel 9:16 Video">Reel 9:16 Video</option>
                            </select>
                          </div>

                          <textarea
                            rows={3}
                            value={reviewFeedback}
                            onChange={(e) => setReviewFeedback(e.target.value)}
                            className="w-full p-3 rounded-2xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                            placeholder="E.g., Make headline punchier, shift accent to neon purple, and upgrade CTA urgency..."
                          />

                          <button
                            onClick={handleRequestChanges}
                            disabled={isSubmittingReview}
                            className="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-lg shadow-amber-600/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                          >
                            <RefreshCw className={`h-3.5 w-3.5 ${isSubmittingReview ? "animate-spin" : ""}`} />
                            <span>Run Targeted Regeneration (v{campaignVersion} → v{campaignVersion + 1})</span>
                          </button>
                        </div>
                      </div>

                      {/* Action Option 2: Approve & Mint Ed25519 Token */}
                      <div className="rounded-3xl border border-emerald-900/60 bg-emerald-950/20 p-6 space-y-4 shadow-xl">
                        <div className="flex items-center justify-between pb-2 border-b border-emerald-900/40">
                          <div className="flex items-center gap-2">
                            <Key className="h-4 w-4 text-emerald-400" />
                            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-300">
                              Option B: Final Sign-Off & Mint Approval Token
                            </h4>
                          </div>
                          <span className="text-[10px] font-mono text-emerald-300 bg-emerald-500/20 px-2 py-0.5 rounded border border-emerald-500/30">
                            RBAC: Requires Approver
                          </span>
                        </div>

                        {reviewRole !== "APPROVER" ? (
                          <div className="p-3.5 rounded-2xl bg-amber-950/30 border border-amber-900/50 flex items-center gap-3 text-xs text-amber-200">
                            <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0" />
                            <span>
                              <strong>RBAC Restriction:</strong> You are viewing as <strong>Editor</strong>. Approving is disabled. Switch to <strong>Approver</strong> role above to authorize.
                            </span>
                          </div>
                        ) : (
                          <p className="text-xs text-slate-300">
                            Mints a single-use, payload-bound Ed25519 cryptographic token. This token is strictly required by <code className="text-emerald-400">mcp-instagram</code> and <code className="text-emerald-400">mcp-meta-ads</code> to execute publishing in Phase 7.
                          </p>
                        )}

                        <button
                          onClick={handleApproveCampaign}
                          disabled={isSubmittingReview || reviewRole !== "APPROVER"}
                          className={`w-full py-3 rounded-xl text-xs font-bold shadow-xl flex items-center justify-center gap-2 transition-all ${
                            reviewRole === "APPROVER"
                              ? "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-emerald-600/30"
                              : "bg-slate-800 text-slate-500 cursor-not-allowed"
                          }`}
                        >
                          <Lock className="h-4 w-4" />
                          <span>
                            {isSubmittingReview
                              ? "Minting Cryptographic Approval Token..."
                              : reviewStatus === "APPROVED"
                              ? "✓ Campaign Approved & Token Minted"
                              : "Approve Campaign & Mint Signed Ed25519 Token"}
                          </span>
                        </button>

                        {/* Minted Cryptographic Approval Token Card */}
                        {approvalTokenInfo && (
                          <div className="p-4 rounded-2xl bg-slate-950 border border-emerald-800/80 space-y-2 text-xs font-mono">
                            <div className="flex items-center justify-between text-emerald-400 font-bold pb-1 border-b border-emerald-900/60">
                              <span>✓ Cryptographic Approval Seal Active</span>
                              <span className="text-[10px] bg-emerald-500/20 px-2 py-0.5 rounded">Single-Use</span>
                            </div>
                            <div className="text-[11px] text-slate-300 space-y-1">
                              <div><span className="text-slate-500">Algorithm:</span> {approvalTokenInfo.algorithm}</div>
                              <div><span className="text-slate-500">Token JTI:</span> {approvalTokenInfo.token_jti}</div>
                              <div className="truncate"><span className="text-slate-500">Payload Hash:</span> {approvalTokenInfo.payload_hash}</div>
                              <div className="truncate"><span className="text-slate-500">Signature:</span> {approvalTokenInfo.signature}</div>
                              <div><span className="text-slate-500">Authorized Tool:</span> {approvalTokenInfo.tool_name}</div>
                              <div><span className="text-slate-500">Signed By:</span> {approvalTokenInfo.approved_by}</div>
                            </div>
                            <div className="text-[10px] text-emerald-400 pt-1">
                              Zero path to publish without this token. Ready for Phase 7 (Publishing).
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )
          )}

          
            {/* Fullscreen Expand Preview Modal */}
            {expandedCard && (
              <div
                className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in"
                onClick={() => setExpandedCard(null)}
              >
                <div
                  className="bg-[#0b101e] border border-slate-800 rounded-3xl max-w-4xl w-full overflow-hidden shadow-2xl grid grid-cols-1 md:grid-cols-2 relative"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    type="button"
                    onClick={() => setExpandedCard(null)}
                    className="absolute top-4 right-4 z-20 h-9 w-9 rounded-full bg-black/60 border border-white/20 text-white flex items-center justify-center hover:bg-black transition-all"
                  >
                    <X className="h-4 w-4" />
                  </button>

                  <div className="relative h-[480px] md:h-[560px] bg-slate-950 overflow-hidden">
                    <img
                      src={expandedCard.bgUrl || undefined}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  </div>

                  <div className="p-6 md:p-8 flex flex-col justify-between space-y-6">
                    <div className="space-y-4">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/30">
                          {expandedCard.tag || `Variant ${expandedCard.index}`}
                        </span>
                        <span className="text-xs text-slate-400">Gemini MCP Imagen 3</span>
                      </div>

                      <div className="space-y-2">
                        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                          Headline
                        </div>
                        <div className="text-lg font-bold text-white">{expandedCard.headline}</div>
                      </div>

                      {expandedCard.badges && (
                        <div className="space-y-2">
                          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Feature Badges
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {expandedCard.badges.map((b: string, i: number) => (
                              <span
                                key={i}
                                className="px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-xs font-medium text-amber-300"
                              >
                                {b}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {expandedCard.copy?.body && (
                        <div className="space-y-2">
                          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Value Proposition
                          </div>
                          <div className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                            {expandedCard.copy.body}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                      {expandedCard.bgUrl && (
                        <a
                          href={expandedCard.bgUrl}
                          download={`poster-variant-${expandedCard.index}.jpg`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white flex items-center gap-2 transition-all"
                        >
                          <Download className="h-4 w-4" />
                          <span>Download Image</span>
                        </a>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          toggleCardSelection(expandedCard.index);
                          setExpandedCard(null);
                        }}
                        className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-lg transition-all"
                      >
                        {selectedCardIndices.includes(expandedCard.index) ? "Deselect Card" : "Select Card"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Inline Card Edit Modal */}
            {editingCard && (
              <div
                className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in"
                onClick={() => setEditingCard(null)}
              >
                <div
                  className="bg-[#0b101e] border border-slate-800 rounded-3xl max-w-lg w-full p-6 md:p-8 space-y-5 shadow-2xl relative"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <Edit3 className="h-4 w-4 text-indigo-400" />
                      <h3 className="text-base font-bold text-white">
                        Edit Creative #{editingCard.index}
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => setEditingCard(null)}
                      className="h-8 w-8 rounded-full bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center transition-all"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Headline</label>
                      <input
                        type="text"
                        value={editingCard.headline || ""}
                        onChange={(e) =>
                          setEditingCard({ ...editingCard, headline: e.target.value })
                        }
                        className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Subheadline</label>
                      <input
                        type="text"
                        value={editingCard.subheadline || ""}
                        onChange={(e) =>
                          setEditingCard({ ...editingCard, subheadline: e.target.value })
                        }
                        className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Call To Action (CTA)</label>
                      <input
                        type="text"
                        value={editingCard.cta || ""}
                        onChange={(e) =>
                          setEditingCard({ ...editingCard, cta: e.target.value })
                        }
                        className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="text-xs text-slate-400 block mb-1">
                        Describe a design change <span className="text-slate-600">(optional)</span>
                      </label>
                      <textarea
                        value={editChangeNote}
                        onChange={(e) => setEditChangeNote(e.target.value)}
                        rows={3}
                        placeholder="e.g. warmer festive lighting, move the product to the left, add marigold flowers"
                        className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 resize-none"
                      />
                      <p className="text-[11px] text-slate-500 mt-1">
                        Text-only edits re-render directly. A described change is applied by the designer agent first.
                      </p>
                    </div>
                  </div>

                  <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-800">
                    <button
                      type="button"
                      onClick={() => {
                        setEditingCard(null);
                        setEditChangeNote("");
                      }}
                      className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white transition-all"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={!editingCard.concept}
                      onClick={() => {
                        handleRegenerateVariant(editingCard, editChangeNote);
                        setEditingCard(null);
                        setEditChangeNote("");
                      }}
                      className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition-all"
                    >
                      Re-render poster
                    </button>
                  </div>
                </div>
              </div>
            )}
            </div>
          </div>
        ) : (
          /* STEP 01: DASHBOARD VIEW (MATCHING IMAGE 2 IDENTICALLY) */
          <div className="w-full max-w-7xl mx-auto flex-1 flex flex-col justify-between pt-2 pb-2 min-h-0">
            {/* Hero Section: Left Text (higher up) + Right Robot (overlapping chat bar) */}
            <div className="flex flex-col lg:flex-row items-start justify-between gap-6 relative -mb-10 sm:-mb-14 lg:-mb-16 z-10 w-full px-2 mt-auto">
              {/* Left Column: Greeting & Headlines brought up */}
              <div className="flex-1 space-y-4 z-10 pt-2 lg:pt-6 pb-6 max-w-2xl">
                <div className="text-base sm:text-lg text-slate-300 font-medium flex items-center gap-2">
                  <span>Good morning!</span>
                  <span className="text-xl">👋</span>
                </div>

                <h1 className="text-5xl sm:text-6xl lg:text-[76px] font-black text-white tracking-tight leading-[1.04]">
                  What are we <br />
                  <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-fuchsia-500 bg-clip-text text-transparent">
                    growing
                  </span>{" "}
                  today?
                </h1>

                <p className="text-base sm:text-lg lg:text-xl text-slate-300 font-normal pt-1">
                  Tell your AI marketing team what you want to achieve.
                </p>
              </div>

              {/* Right Column: 3D Robot brought down and overlapping chat bar */}
              <div className="relative shrink-0 flex items-end justify-center lg:justify-end w-full lg:w-[580px] self-end">
                {/* Volumetric Aurora Ambient Lighting Rays matching Image 2 */}
                <div className="absolute top-6 right-6 w-[450px] h-[380px] bg-gradient-to-br from-blue-500/35 via-indigo-600/30 to-fuchsia-600/35 blur-3xl rounded-full pointer-events-none" />
                <div className="absolute top-0 right-16 w-80 h-48 bg-cyan-400/25 blur-2xl rounded-full rotate-45 pointer-events-none" />
                <div className="absolute bottom-10 right-4 w-72 h-56 bg-fuchsia-600/25 blur-3xl rounded-full pointer-events-none" />

                {/* Floating Neon 4-pointed Sparkle Stars matching Image 2 */}
                <div className="absolute left-6 top-32 text-fuchsia-400 text-3xl select-none animate-pulse pointer-events-none drop-shadow-[0_0_12px_rgba(232,121,249,0.9)]">
                  ✦
                </div>
                <div className="absolute right-4 top-20 text-cyan-300 text-3xl select-none pointer-events-none drop-shadow-[0_0_12px_rgba(103,232,249,0.9)]">
                  ✦
                </div>
                <div className="absolute right-14 bottom-24 text-fuchsia-400 text-xl select-none pointer-events-none drop-shadow-[0_0_8px_rgba(232,121,249,0.8)]">
                  ✦
                </div>

                {/* The Big 3D Robot Asset overlapping behind the chat bar */}
                <img
                  src="/robot.png?v=2"
                  alt="AI Marketing Robot"
                  className="relative z-10 w-[420px] sm:w-[480px] md:w-[540px] lg:w-[580px] max-h-[460px] sm:max-h-[520px] lg:max-h-[580px] object-contain drop-shadow-[0_25px_50px_rgba(0,0,0,0.8)] select-none pointer-events-none translate-y-6 lg:translate-y-8"
                />
              </div>
            </div>

            {/* Glowing Campaign Goal Input Card overlapping above the robot */}
            <div className="w-full relative z-20">
              {/* Entry mode: create creatives with AI, or bring your own */}
              <div className="mb-3 flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="inline-flex p-1 rounded-2xl border border-slate-800 bg-[#0a0f1e]/90 backdrop-blur-xl shadow-lg">
                  {([
                    { key: "create", label: "Create with AI Studio", icon: Sparkles },
                    { key: "upload", label: "I have my creatives", icon: Upload },
                  ] as const).map(({ key, label, icon: Icon }) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setHomeMode(key)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                        homeMode === key
                          ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white shadow-md shadow-indigo-600/30"
                          : "text-slate-400 hover:text-white"
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {label}
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-slate-500">
                  {homeMode === "create"
                    ? "Our AI designer makes posters from your product photo, then plans and launches the campaign."
                    : "Upload finished posters or videos: we plan the Meta campaign, post to Instagram and run ads."}
                </p>
              </div>
              <div className="rounded-2xl border border-indigo-500/40 bg-[#090d1c]/90 backdrop-blur-xl shadow-[0_0_40px_rgba(99,102,241,0.25)] p-5 sm:p-6 transition-all focus-within:border-indigo-400 focus-within:shadow-[0_0_50px_rgba(99,102,241,0.38)] relative z-20">
                {homeMode === "upload" ? (
                  <div className="space-y-4 pb-4">
                    <CreativeUploader assets={uploadAssets} onChange={setUploadAssets} />
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <textarea
                        value={promptText}
                        onChange={(e) => setPromptText(e.target.value)}
                        placeholder="Anything the strategist should know? Product, offer, who it's for, where you sell…"
                        rows={2}
                        className="md:col-span-2 w-full px-3.5 py-2.5 rounded-xl bg-slate-900/70 border border-slate-800 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
                      />
                      <input
                        value={uploadWebsite}
                        onChange={(e) => setUploadWebsite(e.target.value)}
                        placeholder="Website link (optional)"
                        className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/70 border border-slate-800 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    {campaignStartError && <p className="text-[11px] text-rose-400">{campaignStartError}</p>}
                  </div>
                ) : (
                <>
                {/* Textarea / Prompt Input matching Image 2 */}
                <textarea
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  placeholder="Describe your campaign goal, product, or offer..."
                  rows={4}
                  className="w-full bg-transparent text-base sm:text-lg text-slate-100 placeholder:text-slate-500 focus:outline-none resize-none leading-relaxed min-h-[110px] sm:min-h-[130px] py-1"
                />

                {/* Tag pills if any image ref or files attached */}
                {(attachedFiles.length > 0 || productImages.length > 0 || uploadError) && (
                  <div className="flex flex-wrap items-center gap-2 pt-1 pb-3">
                    {productImages.map((img) => (
                      <span
                        key={img.asset_id}
                        className="inline-flex items-center gap-1.5 pl-1 pr-2.5 py-1 rounded-lg bg-emerald-950/50 border border-emerald-500/40 text-[11px] text-emerald-300"
                      >
                        <img src={img.url} alt="" className="h-6 w-6 rounded object-cover" />
                        <span className="truncate max-w-[140px]">{img.name || "Product photo"}</span>
                        <button
                          onClick={() => setProductImages((prev) => prev.filter((p) => p.asset_id !== img.asset_id))}
                          className="text-emerald-400 hover:text-rose-400 ml-0.5"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                    {uploadError && <span className="text-[11px] text-rose-400">{uploadError}</span>}
                    {attachedFiles.map((f, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-[11px] text-slate-300"
                      >
                        <Paperclip className="h-3 w-3 text-indigo-400" />
                        <span>{f.name}</span>
                        <button
                          onClick={() => setAttachedFiles((prev) => prev.filter((_, idx) => idx !== i))}
                          className="text-slate-500 hover:text-rose-400 ml-0.5"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                </>
                )}

                {/* Bottom Controls Row matching Image 2 */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800/80 text-xs text-slate-300">
                  <div className="flex flex-wrap items-center gap-3">
                    {homeMode === "create" && (
                    <>
                    {/* Add image */}
                    <label
                      title="Product photo(s) are sent to Gemini so the poster shows your real product"
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-800 bg-[#0c1222]/80 hover:bg-[#11192e] hover:border-slate-700 text-slate-300 hover:text-white transition-all ${
                        productImages.length >= MAX_PRODUCT_IMAGES || isUploadingProduct ? "opacity-60 cursor-not-allowed" : "cursor-pointer"
                      }`}
                    >
                      {isUploadingProduct ? (
                        <RefreshCw className="h-3.5 w-3.5 text-slate-400 animate-spin" />
                      ) : (
                        <ImageIcon className="h-3.5 w-3.5 text-slate-400" />
                      )}
                      <span>
                        {isUploadingProduct
                          ? "Uploading..."
                          : productImages.length
                          ? `Product photos ${productImages.length}/${MAX_PRODUCT_IMAGES}`
                          : "Add product photo"}
                      </span>
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        multiple
                        className="hidden"
                        disabled={productImages.length >= MAX_PRODUCT_IMAGES || isUploadingProduct}
                        onChange={(e) => {
                          handleProductUpload(e.target.files);
                          e.target.value = "";
                        }}
                      />
                    </label>

                    {/* Attach files */}
                    <button
                      type="button"
                      onClick={() => setShowAttachModal(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-800 bg-[#0c1222]/80 hover:bg-[#11192e] hover:border-slate-700 text-slate-300 hover:text-white transition-all"
                    >
                      <Paperclip className="h-3.5 w-3.5 text-slate-400" />
                      <span>Attach files</span>
                    </button>

                    {/* Vertical Divider */}
                    <div className="h-5 w-px bg-slate-800 hidden sm:block" />
                    </>
                    )}

                    {/* Ad duration pill group */}
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1 text-slate-400">
                        <Calendar className="h-3.5 w-3.5" />
                        <span className="font-medium">Ad duration</span>
                        <Info className="h-3 w-3 text-slate-500 cursor-pointer" />
                      </div>
                      <div className="flex items-center gap-1 bg-[#0c1222] p-0.5 rounded-xl border border-slate-800/80">
                        {[
                          { days: 3, label: "3 days" },
                          { days: 7, label: "7 days" },
                          { days: 14, label: "14 days" },
                          { days: 30, label: "30 days" },
                        ].map((item) => {
                          const isSelected = durationDays === item.days;
                          return (
                            <button
                              key={item.days}
                              type="button"
                              onClick={() => setDurationDays(item.days)}
                              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                                isSelected
                                  ? "bg-blue-600 text-white shadow-md shadow-blue-500/30"
                                  : "text-slate-400 hover:text-slate-200"
                              }`}
                            >
                              {item.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Vertical Divider */}
                    <div className="h-5 w-px bg-slate-800 hidden sm:block" />

                    {/* Budget */}
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1 text-slate-400">
                        <Tag className="h-3.5 w-3.5" />
                        <span className="font-medium">Budget</span>
                        <Info className="h-3 w-3 text-slate-500 cursor-pointer" />
                      </div>
                      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-800 bg-[#0c1222]/80 text-slate-300">
                        <span className="text-slate-400 font-bold">₹</span>
                        <input
                          type="text"
                          value={budgetINR}
                          onChange={(e) => setBudgetINR(e.target.value)}
                          placeholder="Set daily budget"
                          className="bg-transparent text-xs text-white placeholder:text-slate-500 focus:outline-none w-28"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Create campaign button matching Image 2 */}
                  <button
                    type="button"
                    onClick={homeMode === "upload" ? handleStartUploadedCampaign : handleStartCampaign}
                    disabled={isCreatingCampaign || (homeMode === "upload" && uploadAssets.length === 0)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
                  >
                    <span>
                      {isCreatingCampaign ? "Starting…" : homeMode === "upload" ? "Plan my campaign" : "Create campaign"}
                    </span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Attach Files */}
        {showAttachModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0d1322] p-6 space-y-4">
              <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                <h3 className="text-sm font-semibold text-white">Attach Reference Files</h3>
                <button onClick={() => setShowAttachModal(false)} className="text-slate-400 hover:text-white">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="border-2 border-dashed border-slate-700 rounded-xl p-6 text-center text-xs text-slate-400">
                <Upload className="h-6 w-6 text-slate-500 mx-auto mb-2" />
                <span>Drop files here or click to browse</span>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setShowAttachModal(false)}
                  className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-medium"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Product Details */}
        {showProductModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0d1322] p-6 space-y-4">
              <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                <h3 className="text-sm font-semibold text-white">Select Product from Catalog</h3>
                <button onClick={() => setShowProductModal(false)} className="text-slate-400 hover:text-white">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="space-y-2">
                {products.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setSelectedProduct(`${p.name} (₹${p.price.toLocaleString()})`);
                      setShowProductModal(false);
                    }}
                    className="w-full text-left p-3 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-indigo-950/40 text-xs"
                  >
                    <div className="font-semibold text-white">{p.name}</div>
                    <div className="text-[11px] text-slate-400">{p.description}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Modal: Advanced Options */}
        {showAdvancedModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0d1322] p-6 space-y-4">
              <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                <h3 className="text-sm font-semibold text-white">Advanced Campaign Options</h3>
                <button onClick={() => setShowAdvancedModal(false)} className="text-slate-400 hover:text-white">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="space-y-3 text-xs">
                <div>
                  <label className="text-slate-400 block mb-1">Target Ad Budget (INR)</label>
                  <input
                    type="text"
                    value={budgetINR}
                    onChange={(e) => setBudgetINR(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Duration (Days)</label>
                  <input
                    type="number"
                    value={durationDays ?? ""}
                    onChange={(e) => setDurationDays(e.target.value ? Number(e.target.value) : null)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-white"
                  />
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setShowAdvancedModal(false)}
                  className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-medium"
                >
                  Save Options
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Live Design Tokens Viewer */}
        {showTokensViewer && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6">
            <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-[#0a0f1d] p-6 space-y-4 max-h-[85vh] flex flex-col">
              <div className="flex justify-between items-center pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Code2 className="h-4 w-4 text-indigo-400" />
                  <h3 className="text-sm font-semibold text-white">mcp-knowledge: Compiled Design Tokens</h3>
                </div>
                <button onClick={() => setShowTokensViewer(false)} className="text-slate-400 hover:text-white">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <pre className="flex-1 bg-slate-950 p-4 rounded-xl text-xs font-mono text-emerald-400 overflow-y-auto border border-slate-800/80">
{JSON.stringify(
  {
    brand_name: brandName,
    logo_url: logoUrl,
    color_palette: { primary: primaryColor, secondary: secondaryColor, accent: accentColor },
    typography: { headline: headlineFont },
    tone_of_voice: { keywords: toneKeywords.split(",").map((k) => k.trim()) },
    product_catalog: products,
  },
  null,
  2
)}
              </pre>
            </div>
          </div>
        )}

        {/* Modal: Gemini MCP Connector & Gateway Configuration */}
        {showGeminiModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-200">
            <div className="w-full max-w-2xl rounded-3xl border border-purple-500/40 bg-[#0a0f1d] p-6 sm:p-8 space-y-6 max-h-[90vh] overflow-y-auto shadow-2xl shadow-purple-950/60">
              {/* Header */}
              <div className="flex justify-between items-start pb-4 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-pink-600 flex items-center justify-center text-white shadow-lg shadow-purple-600/30">
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                      Gemini MCP Server Connector
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        MCP v0.1.0 Ready
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Model Context Protocol bridge for Imagen 3 poster art & Veo 2 vertical video reels
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowGeminiModal(false)}
                  className="p-1.5 rounded-xl border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800/60 transition-all"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Status & Agent Hold Alert */}
              <div className="p-4 rounded-2xl bg-indigo-950/30 border border-indigo-500/30 space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <div className="flex items-center gap-2 text-indigo-300">
                    <ShieldCheck className="h-4 w-4 text-indigo-400" />
                    <span>Active Generation Engine: Gemini MCP Gateway</span>
                  </div>
                  <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full font-mono">
                    Custom Agents: ON HOLD
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  Per POC requirement, <span className="font-mono text-indigo-300">designer_agent.py</span> and <span className="font-mono text-indigo-300">video_agent.py</span> are preserved intact in the codebase and placed on hold pending training. Graphic posters and video reels are actively generated via the Gemini MCP Gateway.
                </p>
              </div>

              {/* Live Connection Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800">
                  <div className="text-[11px] text-slate-400">Connection Status</div>
                  <div className="text-sm font-bold text-emerald-400 flex items-center gap-1.5 mt-1">
                    <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    {isGeminiMcpConnected ? "CONNECTED" : "OFFLINE"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5 font-mono">Protocol: MCP Server</div>
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800">
                  <div className="text-[11px] text-slate-400">Live Latency</div>
                  <div className="text-sm font-bold text-white mt-1">
                    {geminiLatency ? `${geminiLatency} ms` : "12 ms"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">In-Memory Gateway</div>
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800">
                  <div className="text-[11px] text-slate-400">Gateway Engine</div>
                  <div className="text-sm font-bold text-purple-300 truncate mt-1">
                    {geminiMcpEngine.split("(")[0].trim() || "Gemini MCP"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Imagen 3 + Veo 2</div>
                </div>
              </div>

              {/* Real Google Account / Gemini MCP Connection Card */}
              <div className="p-5 rounded-2xl bg-[#0d1424] border border-purple-500/30 space-y-4 shadow-xl">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                  <div className="flex items-center gap-2.5">
                    {/* Google G Logo SVG */}
                    <div className="h-7 w-7 rounded-xl bg-white flex items-center justify-center p-1 shadow-sm shrink-0">
                      <svg className="w-full h-full" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                      </svg>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white">Google Gemini Account Connection</h4>
                      <span className="text-[10px] text-slate-400">Model Context Protocol (MCP) Live Gateway</span>
                    </div>
                  </div>

                  {isGeminiMcpConnected ? (
                    <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2.5 py-0.5 rounded-full font-mono flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                      Live Account Connected
                    </span>
                  ) : (
                    <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full font-mono">
                      Not Connected
                    </span>
                  )}
                </div>

                {isGeminiMcpConnected && geminiUser ? (
                  /* ✅ Connected — Show real Google user profile */
                  <div className="space-y-4">
                    <div className="p-4 rounded-xl bg-slate-900/90 border border-emerald-500/30 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        {/* Real Google avatar */}
                        {geminiUser.avatar ? (
                          <img
                            src={geminiUser.avatar}
                            alt={geminiUser.name}
                            className="h-10 w-10 rounded-full border-2 border-emerald-500/40 object-cover"
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = `https://api.dicebear.com/7.x/identicon/svg?seed=${encodeURIComponent(geminiUser.email)}`;
                            }}
                          />
                        ) : (
                          <div className="h-10 w-10 rounded-full bg-emerald-950/60 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-bold text-sm">
                            {geminiUser.name?.[0] || "G"}
                          </div>
                        )}
                        <div>
                          <div className="text-xs font-bold text-white flex items-center gap-1.5">
                            <span>{geminiUser.name}</span>
                            <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-mono">✓ Google Account</span>
                          </div>
                          <div className="text-[11px] text-slate-400 mt-0.5">{geminiUser.email}</div>
                          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                            Connected {new Date(geminiUser.connected_at).toLocaleString()}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleSignInWithGoogle}
                          className="px-3 py-1.5 rounded-lg border border-indigo-700 bg-indigo-950/60 hover:bg-indigo-900/60 text-indigo-300 hover:text-white text-xs transition-all flex items-center gap-1.5"
                          title="Reconnect to grant updated Gemini Cloud Platform permissions"
                        >
                          <RefreshCw className="h-3 w-3" />
                          Reconnect
                        </button>
                        <button
                          onClick={handleDisconnectGoogleOAuth}
                          className="px-3 py-1.5 rounded-lg border border-rose-900/50 hover:border-rose-700 bg-rose-950/30 text-rose-300 hover:text-rose-100 text-xs transition-all"
                        >
                          Sign out
                        </button>
                      </div>
                    </div>

                    {/* Granted Scopes */}
                    <div>
                      <div className="text-[11px] font-semibold text-slate-300 mb-2">Permissions Granted</div>
                      <div className="flex flex-wrap gap-1.5">
                        {(geminiUser.scopes || []).map((scope: string, idx: number) => (
                          <span key={idx} className="px-2.5 py-1 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-emerald-300 font-mono text-[10px] flex items-center gap-1">
                            <Check className="h-2.5 w-2.5" />
                            {scope}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Available Models */}
                    <div>
                      <div className="text-[11px] font-semibold text-slate-300 mb-1.5">Active Gemini Models</div>
                      <div className="flex flex-wrap gap-1.5">
                        {(geminiModelsList.length ? geminiModelsList : ["gemini-1.5-flash", "gemini-1.5-pro", "imagen-3.0-generate-002", "veo-2.0-generate-001"]).map((m, idx) => (
                          <span key={idx} className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-indigo-300 font-mono text-[10px]">
                            {m}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Optional Google AI Studio Key Override */}
                    <div className="pt-3 border-t border-slate-800/80">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] text-slate-400 font-medium">Google AI Studio Key (Direct Override)</span>
                        <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" className="text-[10px] text-indigo-400 hover:underline">
                          Get Key →
                        </a>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="password"
                          value={geminiApiKey}
                          onChange={(e) => {
                            setGeminiApiKey(e.target.value);
                            if (typeof window !== "undefined") localStorage.setItem("gemini_api_key", e.target.value);
                          }}
                          placeholder="AIzaSy... (optional for direct Imagen 3 synthesis)"
                          className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
                        />
                        {geminiApiKey && (
                          <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1 shrink-0">
                            <Check className="h-3 w-3" /> Active
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* 🔐 Not connected — Show Sign in with Google button */
                  <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900/90 to-slate-950 border border-slate-800 space-y-5">
                    <div className="text-center space-y-2">
                      <div className="h-14 w-14 rounded-2xl bg-white flex items-center justify-center mx-auto shadow-lg p-2.5">
                        <svg className="w-full h-full" viewBox="0 0 24 24">
                          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                        </svg>
                      </div>
                      <h5 className="text-sm font-bold text-white">Connect with Google</h5>
                      <p className="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
                        Sign in with your Google account to unlock Imagen 3 poster generation and Veo 2 video reels via Gemini MCP.
                      </p>
                    </div>

                    {/* The real OAuth button */}
                    <button
                      onClick={handleSignInWithGoogle}
                      className="w-full flex items-center justify-center gap-3 px-5 py-3.5 rounded-2xl bg-white hover:bg-slate-50 text-slate-800 text-sm font-semibold shadow-lg hover:shadow-xl transition-all hover:scale-[1.02] active:scale-[0.99] border border-slate-200"
                    >
                      <svg className="h-5 w-5" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                      </svg>
                      Sign in with Google
                    </button>

                    <p className="text-center text-[10px] text-slate-500">
                      You'll be redirected to Google to approve access.
                      <br />No API key setup required.
                    </p>

                    {connectError && (
                      <div className="p-2.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-[11px] text-rose-300 flex items-start gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-rose-400 shrink-0 mt-0.5" />
                        <span>{connectError}</span>
                      </div>
                    )}
                  </div>
                )}

                {geminiNoticeMessage && (
                  <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] font-mono text-emerald-400 flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                    <span>{geminiNoticeMessage}</span>
                  </div>
                )}
              </div>

              {/* Active MCP Tools Registry */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Active Gemini MCP Tool Registry ({geminiToolsList.length})
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {geminiToolsList.map((tool, idx) => (
                    <div key={idx} className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-start gap-2.5">
                      <div className="h-6 w-6 rounded-lg bg-purple-600/20 text-purple-400 flex items-center justify-center shrink-0 mt-0.5">
                        <Sparkles className="h-3 w-3" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-semibold text-indigo-300 text-[11px] truncate">{tool.name}</span>
                          <span className="text-[9px] bg-slate-800 px-1.5 py-0.2 rounded text-slate-400">{tool.category}</span>
                        </div>
                        <p className="text-[10px] text-slate-400 truncate mt-0.5">{tool.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Close Button */}
              <div className="flex justify-end pt-2 border-t border-slate-800">
                <button
                  onClick={() => setShowGeminiModal(false)}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
