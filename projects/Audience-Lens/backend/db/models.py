"""Neon PostgreSQL data models — SQLAlchemy 2.x declarative.

These models are the production schema. At runtime the backend works WITHOUT a
live DB connection (NLP/optimizer/audience process requests statelessly); these
tables activate when DATABASE_URL is set and migrations are run via Alembic
using DIRECT_URL.

Foreign keys, unique constraints, indexes, JSONB for variable-shape payloads,
and a provenance column on every insight row.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import sqlalchemy as sa


class Base(DeclarativeBase):
    pass


def _provenance_column():
    return mapped_column(String(32), default="LIVE_DATA", nullable=False)


# --- Tenancy --------------------------------------------------------------


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Agent / research ------------------------------------------------------


class ResearchSession(Base):
    __tablename__ = "research_sessions"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(String(8), default="")
    status: Mapped[str] = mapped_column(String(24), default="draft")
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New session")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    conversation_id: Mapped[str] = mapped_column(ForeignKey("chat_conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)


# --- YouTube collection ----------------------------------------------------


class Video(Base):
    __tablename__ = "videos"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # YouTube video id
    channel_id: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    snippet: Mapped[dict] = mapped_column(JSONB, default=dict)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VideoStatsSnapshot(Base):
    """Time-series of statistics — enables engagement-change analysis & anomalies."""
    __tablename__ = "video_stats_snapshots"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    views: Mapped[int] = mapped_column(BigInteger, default=0)
    likes: Mapped[int] = mapped_column(BigInteger, default=0)
    comments: Mapped[int] = mapped_column(BigInteger, default=0)
    __table_args__ = (UniqueConstraint("video_id", "snapshot_at", name="uq_video_snapshot"),)


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # YouTube comment id
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(120), default="")
    author_channel_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- NLP results -----------------------------------------------------------


class SentimentResult(Base):
    __tablename__ = "sentiment_results"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    comment_id: Mapped[str] = mapped_column(ForeignKey("comments.id"), index=True)
    sentiment: Mapped[str] = mapped_column(String(16))  # positive/negative/neutral/mixed/uncertain
    score: Mapped[float] = mapped_column(sa.Float, default=0.0)
    confidence: Mapped[float] = mapped_column(sa.Float, default=0.0)
    language: Mapped[str] = mapped_column(String(16), default="en")
    aspects: Mapped[dict] = mapped_column(JSONB, default=list)
    provenance: Mapped[str] = _provenance_column()


# --- Audience intelligence -------------------------------------------------


class AudienceCluster(Base):
    __tablename__ = "audience_clusters"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    label: Mapped[str] = mapped_column(String(80))
    size: Mapped[int] = mapped_column(Integer, default=0)
    avg_score: Mapped[float] = mapped_column(sa.Float, default=0.0)
    top_terms: Mapped[list] = mapped_column(JSONB, default=list)
    method: Mapped[str] = mapped_column(String(40))
    provenance: Mapped[str] = _provenance_column()


class AnomalyDetection(Base):
    __tablename__ = "anomaly_detections"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), index=True)
    metric: Mapped[str] = mapped_column(String(60))
    observed: Mapped[float] = mapped_column(sa.Float)
    expected: Mapped[float] = mapped_column(sa.Float)
    deviation: Mapped[float] = mapped_column(sa.Float)
    explanation: Mapped[str] = mapped_column(Text, default="")
    provenance: Mapped[str] = _provenance_column()


# --- Campaign / optimizer --------------------------------------------------


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    objective: Mapped[str] = mapped_column(String(24))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    budget: Mapped[float] = mapped_column(sa.Float, default=0.0)
    google_ads_id: Mapped[str] = mapped_column(String(40), default="", index=True)


class BudgetOptimizationRun(Base):
    __tablename__ = "budget_optimization_runs"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    budget: Mapped[float] = mapped_column(sa.Float)
    strategy: Mapped[str] = mapped_column(String(24))
    allocation: Mapped[dict] = mapped_column(JSONB)
    scenarios: Mapped[dict] = mapped_column(JSONB)
    provenance: Mapped[str] = _provenance_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiQuotaUsage(Base):
    __tablename__ = "api_quota_usage"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    service: Mapped[str] = mapped_column(String(24), index=True)  # youtube / google_ads
    units_used: Mapped[int] = mapped_column(Integer, default=0)
    day: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    __table_args__ = (UniqueConstraint("service", "day", name="uq_quota_day"),)


__all__ = [
    "Base", "User", "Workspace", "ResearchSession", "ChatConversation", "ChatMessage",
    "Video", "VideoStatsSnapshot", "Comment", "SentimentResult",
    "AudienceCluster", "AnomalyDetection", "Campaign", "BudgetOptimizationRun",
    "ApiQuotaUsage",
]
