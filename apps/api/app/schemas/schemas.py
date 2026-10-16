from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, EmailStr, Field

# Auth schemas
class UserSignup(BaseModel):
    email: EmailStr
    full_name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: int

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# Workspace schemas
class WorkspaceCreate(BaseModel):
    name: str
    slug: str
    daily_budget_limit_cents: Optional[int] = 100000

class WorkspaceOut(BaseModel):
    id: str
    name: str
    slug: str
    role: str
    daily_budget_limit_cents: int
    created_at: int

class MembershipCreate(BaseModel):
    email: EmailStr
    role: Literal["OWNER", "EDITOR", "APPROVER", "VIEWER"]

# Approvals schemas
class ApprovalRequestCreate(BaseModel):
    campaign_id: Optional[str] = "standalone"
    action_type: str
    tool_name: str
    action_payload: Dict[str, Any]

class ApprovalDecision(BaseModel):
    approved: bool
    comments: Optional[str] = None

class ApprovalTokenOut(BaseModel):
    token_jti: str
    tenant_id: str
    tool_name: str
    payload_hash: str
    expires_at: int
    signature: str

class ApprovalRequestOut(BaseModel):
    id: str
    tenant_id: str
    action_type: str
    tool_name: str
    action_payload_hash: str
    status: str
    requested_by: str
    reviewed_by: Optional[str]
    expires_at: int
    token: Optional[ApprovalTokenOut] = None

# Phase 1: Brand Kit & Design System Tokens Schemas
class ColorPaletteTokens(BaseModel):
    primary: str = "#6366f1"
    secondary: str = "#4f46e5"
    accent: str = "#ec4899"
    surface: str = "#0f172a"
    background: str = "#080c14"
    text_primary: str = "#f8fafc"
    text_secondary: str = "#94a3b8"

class TypographyTokens(BaseModel):
    headline_font: str = "Inter, sans-serif"
    body_font: str = "Inter, sans-serif"
    headline_weights: List[str] = Field(default_factory=lambda: ["600", "700", "800"])
    body_weights: List[str] = Field(default_factory=lambda: ["400", "500"])

class ToneOfVoice(BaseModel):
    keywords: List[str] = Field(default_factory=lambda: ["Innovative", "Modern", "Authoritative", "Approachable"])
    do_rules: List[str] = Field(default_factory=lambda: ["Use action-oriented verbs", "Highlight customer benefits over specs"])
    dont_rules: List[str] = Field(default_factory=lambda: ["Avoid overly technical jargon without context", "No aggressive sales push"])
    sample_posts: List[str] = Field(default_factory=list)

class ProductItem(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    price: Optional[float] = None
    currency: Optional[str] = "INR"
    key_features: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = None

class BrandKitCreate(BaseModel):
    brand_name: str
    logo_url: Optional[str] = None
    palette_tokens: ColorPaletteTokens = Field(default_factory=ColorPaletteTokens)
    typography_tokens: TypographyTokens = Field(default_factory=TypographyTokens)
    tone_of_voice: ToneOfVoice = Field(default_factory=ToneOfVoice)
    product_catalog: List[ProductItem] = Field(default_factory=list)

class BrandKitOut(BaseModel):
    id: str
    tenant_id: str
    brand_name: str
    logo_url: Optional[str]
    palette_tokens: Dict[str, Any]
    typography_tokens: Dict[str, Any]
    tone_of_voice: Dict[str, Any]
    product_catalog: List[Dict[str, Any]]
    version: int
    is_active: bool
    created_at: int
    updated_at: int

# Phase 1: Campaign Draft Schemas (Prompt Bar)
class CampaignCreate(BaseModel):
    title: Optional[str] = None
    raw_prompt: str
    product_details: Optional[Dict[str, Any]] = None
    advanced_options: Optional[Dict[str, Any]] = None
    attached_files: List[Dict[str, Any]] = Field(default_factory=list)

class CampaignOut(BaseModel):
    id: str
    tenant_id: str
    title: str
    raw_prompt: str
    status: str
    current_step: str
    product_details: Optional[Dict[str, Any]]
    advanced_options: Optional[Dict[str, Any]]
    attached_files: List[Dict[str, Any]]
    created_by: Optional[str]
    created_at: int
    updated_at: int

# Phase 2: Creative Brief & Prompt Enhancer Schemas
class TargetAudienceSchema(BaseModel):
    age_range: str = "22-35 years"
    location: str = "India (Top cities)"
    interests: List[str] = Field(default_factory=lambda: ["Tech", "Wearables", "Productivity", "Fitness"])
    estimated_reach: Optional[str] = "1.2M - 1.8M people"

class CreativeBriefCreate(BaseModel):
    objective: str = "Drive sales"
    product_focus: str
    target_audience: TargetAudienceSchema = Field(default_factory=TargetAudienceSchema)
    tone: str = "Inspiring, energetic, and authoritative"
    deliverables: Literal["POSTER", "REEL", "BOTH"] = "BOTH"
    channels: List[str] = Field(default_factory=lambda: ["INSTAGRAM", "META_ADS"])
    call_to_action: str = "Shop Now"
    constraints: List[str] = Field(default_factory=lambda: ["Do not make medical claims", "Highlight 7-day battery life"])
    enhanced_prompt: str
    diff_summary: Optional[str] = None

class CreativeBriefUpdate(BaseModel):
    objective: Optional[str] = None
    product_focus: Optional[str] = None
    target_audience: Optional[TargetAudienceSchema] = None
    tone: Optional[str] = None
    deliverables: Optional[Literal["POSTER", "REEL", "BOTH"]] = None
    channels: Optional[List[str]] = None
    call_to_action: Optional[str] = None
    constraints: Optional[List[str]] = None
    enhanced_prompt: Optional[str] = None

class CreativeBriefOut(BaseModel):
    id: str
    campaign_id: str
    tenant_id: str
    objective: str
    product_focus: str
    target_audience: Dict[str, Any]
    tone: str
    deliverables: str
    channels: List[str]
    call_to_action: str
    constraints: List[str]
    enhanced_prompt: str
    diff_summary: Optional[str]
    version: int
    is_approved: bool
    created_at: int
    updated_at: int

# Phase 3: Creative Asset Schemas
class CreativeAssetOut(BaseModel):
    id: str
    campaign_id: str
    tenant_id: str
    asset_type: str
    variant_index: int
    storage_key: str
    preview_url: str
    aspect_ratio: str
    layout_spec: Dict[str, Any]
    copy_captions: Dict[str, Any]
    compliance_status: str
    created_at: int

class GenerateCreativeRequest(BaseModel):
    aspect_ratio: Optional[str] = "4:5"
    regenerate: Optional[bool] = False

# Phase 4: Reel & Video Pipeline Schemas
class GenerateReelRequest(BaseModel):
    audio_track: Optional[str] = "cinematic_synth_anthem"
    caption_style: Optional[str] = "kinetic_highlight"

class ReelJobStatusOut(BaseModel):
    job_id: str
    status: str
    progress_percent: int
    output_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    scenes_count: Optional[int] = None

# Phase 5: Human-in-the-Loop Review and Approval Gate Schemas
class ReviewDecisionRequest(BaseModel):
    decision: str  # "APPROVE" or "REQUEST_CHANGES"
    feedback: Optional[str] = None
    target_asset_id: Optional[str] = None

class AssetCommentCreate(BaseModel):
    asset_id: Optional[str] = None
    content: str

class AssetCommentOut(BaseModel):
    id: str
    campaign_id: str
    tenant_id: str
    asset_id: Optional[str] = None
    author_id: str
    author_name: str
    content: str
    created_at: int

class CampaignRevisionOut(BaseModel):
    id: str
    campaign_id: str
    version: int
    feedback_text: str
    edit_instructions: Dict[str, Any]
    diff_summary: Optional[str] = None
    created_at: int

class ReviewGateStatusOut(BaseModel):
    campaign_id: str
    version: int
    status: str
    compliance_report: Dict[str, Any]
    diff_summary: Optional[str] = None
    approval_token: Optional[Dict[str, Any]] = None
    revisions: List[CampaignRevisionOut] = Field(default_factory=list)
    comments: List[AssetCommentOut] = Field(default_factory=list)
