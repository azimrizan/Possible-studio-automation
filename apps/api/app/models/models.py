import uuid
import time
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.session import Base

def gen_uuid_str() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

    memberships: Mapped[list["WorkspaceMembership"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    daily_budget_limit_cents: Mapped[int] = mapped_column(BigInteger, default=100000)  # $1,000 cap
    lifetime_budget_limit_cents: Mapped[int] = mapped_column(BigInteger, default=500000)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

    members: Mapped[list["WorkspaceMembership"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="VIEWER")  # OWNER, EDITOR, APPROVER, VIEWER
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

    tenant: Mapped["Tenant"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    action_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, APPROVED, REJECTED, EXPIRED
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(36), nullable=True)
    review_comments: Mapped[str] = mapped_column(Text, nullable=True)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

    tenant: Mapped["Tenant"] = relationship(back_populates="approval_requests")

class ApprovalTokenRecord(Base):
    __tablename__ = "approval_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    approval_request_id: Mapped[str] = mapped_column(String(36), ForeignKey("approval_requests.id", ondelete="CASCADE"))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token_jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    is_consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    consumed_at: Mapped[int] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

class CampaignEvent(Base):
    __tablename__ = "campaign_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # AGENT, USER, SYSTEM
    actor_id: Mapped[str] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

class BrandKit(Base):
    __tablename__ = "brand_kits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[str] = mapped_column(Text, nullable=True)
    palette_tokens: Mapped[dict] = mapped_column(JSON, nullable=False)
    typography_tokens: Mapped[dict] = mapped_column(JSON, nullable=False)
    tone_of_voice: Mapped[dict] = mapped_column(JSON, nullable=False)
    product_catalog: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))
    updated_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

    knowledge_items: Mapped[list["BrandKnowledgeItem"]] = relationship(back_populates="brand_kit", cascade="all, delete-orphan")

class BrandKnowledgeItem(Base):
    __tablename__ = "brand_knowledge_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    brand_kit_id: Mapped[str] = mapped_column(String(36), ForeignKey("brand_kits.id", ondelete="CASCADE"), nullable=False)
    content_chunk: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # faq, policy, product_spec, voice_sample
    embedding: Mapped[list] = mapped_column(JSON, nullable=True)  # vector representation
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

    brand_kit: Mapped["BrandKit"] = relationship(back_populates="knowledge_items")

class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")  # DRAFT, PLANNING, CREATIVE, REVIEW, PUBLISHED
    current_step: Mapped[str] = mapped_column(String(50), default="DASHBOARD")
    product_details: Mapped[dict] = mapped_column(JSON, nullable=True)
    advanced_options: Mapped[dict] = mapped_column(JSON, nullable=True)
    attached_files: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(36), nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))
    updated_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

    brief: Mapped[Optional["CreativeBrief"]] = relationship(back_populates="campaign", uselist=False, cascade="all, delete-orphan")
    assets: Mapped[list["CreativeAsset"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")

class CreativeBrief(Base):
    __tablename__ = "creative_briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    objective: Mapped[str] = mapped_column(String(100), nullable=False)
    product_focus: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[dict] = mapped_column(JSON, nullable=False)
    tone: Mapped[str] = mapped_column(String(100), nullable=False)
    deliverables: Mapped[str] = mapped_column(String(50), nullable=False, default="BOTH")  # POSTER, REEL, BOTH
    channels: Mapped[list] = mapped_column(JSON, default=list)
    call_to_action: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[list] = mapped_column(JSON, default=list)
    enhanced_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    diff_summary: Mapped[str] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))
    updated_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

    campaign: Mapped["Campaign"] = relationship(back_populates="brief")

class CreativeAsset(Base):
    __tablename__ = "creative_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), default="POSTER")  # POSTER, REEL
    variant_index: Mapped[int] = mapped_column(Integer, default=1)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    preview_url: Mapped[str] = mapped_column(Text, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(20), default="4:5")  # 1:1, 4:5, 9:16
    layout_spec: Mapped[dict] = mapped_column(JSON, nullable=False)
    copy_captions: Mapped[dict] = mapped_column(JSON, nullable=False)
    compliance_status: Mapped[str] = mapped_column(String(50), default="PASSED")
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

    campaign: Mapped["Campaign"] = relationship(back_populates="assets")

class AssetComment(Base):
    __tablename__ = "asset_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

class CampaignRevision(Base):
    __tablename__ = "campaign_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid_str)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    edit_instructions: Mapped[dict] = mapped_column(JSON, nullable=False)
    diff_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))



