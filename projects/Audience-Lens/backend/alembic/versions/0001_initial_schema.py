"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-15

Creates the full AudienceLens schema on Neon PostgreSQL:
tenancy, agent/research, YouTube collection, NLP results, audience
intelligence, campaign/optimizer, and quota tracking. Every insight table
carries a provenance column.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Tenancy ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(120), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "workspaces",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Agent / research ---
    op.create_table(
        "research_sessions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", UUID(as_uuid=False), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("objective", sa.Text, nullable=False),
        sa.Column("country", sa.String(8), server_default=""),
        sa.Column("status", sa.String(24), server_default="draft"),
        sa.Column("config", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_research_sessions_workspace_id", "research_sessions", ["workspace_id"])

    op.create_table(
        "chat_conversations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=False), sa.ForeignKey("research_sessions.id"), nullable=False),
        sa.Column("title", sa.String(200), server_default="New session"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_conversations_session_id", "chat_conversations", ["session_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", UUID(as_uuid=False), sa.ForeignKey("chat_conversations.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("meta", JSONB, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])

    # --- YouTube collection ---
    op.create_table(
        "videos",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("channel_id", sa.String(40), nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("snippet", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_videos_channel_id", "videos", ["channel_id"])

    op.create_table(
        "video_stats_snapshots",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("video_id", sa.String(20), sa.ForeignKey("videos.id"), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("views", sa.BigInteger, server_default="0"),
        sa.Column("likes", sa.BigInteger, server_default="0"),
        sa.Column("comments", sa.BigInteger, server_default="0"),
        sa.UniqueConstraint("video_id", "snapshot_at", name="uq_video_snapshot"),
    )
    op.create_index("ix_video_stats_snapshots_video_id", "video_stats_snapshots", ["video_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("video_id", sa.String(20), sa.ForeignKey("videos.id"), nullable=False),
        sa.Column("text", sa.Text),
        sa.Column("author", sa.String(120), server_default=""),
        sa.Column("author_channel_id", sa.String(40), server_default=""),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("like_count", sa.Integer, server_default="0"),
        sa.Column("reply_count", sa.Integer, server_default="0"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_comments_video_id", "comments", ["video_id"])
    op.create_index("ix_comments_author_channel_id", "comments", ["author_channel_id"])

    # --- NLP results ---
    op.create_table(
        "sentiment_results",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("comment_id", sa.String(40), sa.ForeignKey("comments.id"), nullable=False),
        sa.Column("sentiment", sa.String(16)),
        sa.Column("score", sa.Float, server_default="0"),
        sa.Column("confidence", sa.Float, server_default="0"),
        sa.Column("language", sa.String(16), server_default="en"),
        sa.Column("aspects", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("provenance", sa.String(32), server_default="LIVE_DATA", nullable=False),
    )
    op.create_index("ix_sentiment_results_comment_id", "sentiment_results", ["comment_id"])

    # --- Audience intelligence ---
    op.create_table(
        "audience_clusters",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=False), sa.ForeignKey("research_sessions.id"), nullable=False),
        sa.Column("label", sa.String(80)),
        sa.Column("size", sa.Integer, server_default="0"),
        sa.Column("avg_score", sa.Float, server_default="0"),
        sa.Column("top_terms", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("method", sa.String(40)),
        sa.Column("provenance", sa.String(32), server_default="INFERENCE", nullable=False),
    )
    op.create_index("ix_audience_clusters_session_id", "audience_clusters", ["session_id"])

    op.create_table(
        "anomaly_detections",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("video_id", sa.String(20), sa.ForeignKey("videos.id"), nullable=False),
        sa.Column("metric", sa.String(60)),
        sa.Column("observed", sa.Float),
        sa.Column("expected", sa.Float),
        sa.Column("deviation", sa.Float),
        sa.Column("explanation", sa.Text, server_default=""),
        sa.Column("provenance", sa.String(32), server_default="INFERENCE", nullable=False),
    )
    op.create_index("ix_anomaly_detections_video_id", "anomaly_detections", ["video_id"])

    # --- Campaign / optimizer ---
    op.create_table(
        "campaigns",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", UUID(as_uuid=False), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("name", sa.String(120)),
        sa.Column("objective", sa.String(24)),
        sa.Column("currency", sa.String(8), server_default="USD"),
        sa.Column("budget", sa.Float, server_default="0"),
        sa.Column("google_ads_id", sa.String(40), server_default=""),
    )
    op.create_index("ix_campaigns_workspace_id", "campaigns", ["workspace_id"])
    op.create_index("ix_campaigns_google_ads_id", "campaigns", ["google_ads_id"])

    op.create_table(
        "budget_optimization_runs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id", UUID(as_uuid=False), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("budget", sa.Float),
        sa.Column("strategy", sa.String(24)),
        sa.Column("allocation", JSONB),
        sa.Column("scenarios", JSONB),
        sa.Column("provenance", sa.String(32), server_default="ESTIMATED_SCENARIO", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_budget_optimization_runs_campaign_id", "budget_optimization_runs", ["campaign_id"])

    op.create_table(
        "api_quota_usage",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("service", sa.String(24), nullable=False),
        sa.Column("units_used", sa.Integer, server_default="0"),
        sa.Column("day", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("service", "day", name="uq_quota_day"),
    )
    op.create_index("ix_api_quota_usage_service", "api_quota_usage", ["service"])
    op.create_index("ix_api_quota_usage_day", "api_quota_usage", ["day"])


def downgrade() -> None:
    for tbl in (
        "api_quota_usage", "budget_optimization_runs", "campaigns",
        "anomaly_detections", "audience_clusters", "sentiment_results",
        "comments", "video_stats_snapshots", "videos",
        "chat_messages", "chat_conversations", "research_sessions",
        "workspaces", "users",
    ):
        op.drop_table(tbl)
