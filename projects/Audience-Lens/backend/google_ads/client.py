"""Google Ads API integration — YouTube video campaign metrics via GAQL.

This module is structured for real GAQL queries. The `google-ads` SDK is an
optional dependency (heavy); it is imported lazily and only when credentials are
present. Without credentials or the SDK, every call returns an honest
INSUFFICIENT_DATA response — never fabricated metrics.

OAuth flow (production):
  developer token + customer ID + OAuth2 refresh token → GoogleAdsClient →
  GAQL query against video_campaign metrics.
"""
from __future__ import annotations

from typing import Any

from ..config import settings

# GAQL query template for YouTube video campaign performance.
# (Documented; executed only when the SDK + credentials are available.)
GAQL_VIDEO_CAMPAIGN_METRICS = """
SELECT
  campaign.id,
  campaign.name,
  segments.ad_format_type,
  metrics.impressions,
  metrics.views,
  metrics.clicks,
  metrics.ctr,
  metrics.average_cpc,
  metrics.average_cpv,
  metrics.conversions,
  metrics.conversion_rate,
  metrics.cost_per_conversion,
  metrics.cost_micros,
  metrics.value_per_conversion,
  metrics.all_conversions_value
FROM campaign
WHERE segments.ad_format_type IN ('IN_STREAM_VIDEO', 'SHORTS', 'IN_FEED_VIDEO')
  AND segments.date DURING LAST_30_DAYS
"""


def _client_available() -> bool:
    """True only if the google-ads SDK is importable AND credentials are set."""
    if not settings.google_ads_connected:
        return False
    try:
        import google.ads.googleads.client  # noqa: F401
        return True
    except ImportError:
        return False


def status() -> dict[str, Any]:
    return {
        "connected": settings.google_ads_connected,
        "sdk_installed": _sdk_installed(),
        "developer_token_set": bool(settings.google_ads_developer_token),
        "customer_id_set": bool(settings.google_ads_customer_id),
        "refresh_token_set": bool(settings.google_ads_refresh_token),
        "provenance": "LIVE_DATA" if _client_available() else "INSUFFICIENT_DATA",
        "detail": (
            "Google Ads ready — GAQL metrics available."
            if _client_available()
            else "Google Ads not configured. Set GOOGLE_ADS_DEVELOPER_TOKEN, "
                 "GOOGLE_ADS_CUSTOMER_ID, and GOOGLE_ADS_REFRESH_TOKEN. "
                 "Until then, the optimizer runs in ESTIMATED_SCENARIO mode."
        ),
    }


def _sdk_installed() -> bool:
    try:
        import google.ads.googleads.client  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_metrics() -> dict[str, Any]:
    """Fetch real YouTube video campaign metrics via GAQL.

    Returns INSUFFICIENT_DATA when the SDK or credentials are missing. When the
    `google-ads` SDK is installed and all credentials are set, streams the GAQL
    query and normalizes rows into metric records. Micros are converted to
    currency units. Only metrics the GAQL query returns are surfaced.
    """
    if not _client_available():
        return {
            "metrics": [],
            "provenance": "INSUFFICIENT_DATA",
            "detail": "Google Ads SDK not installed or credentials incomplete. "
                      "Install `google-ads` and set GOOGLE_ADS_DEVELOPER_TOKEN, "
                      "GOOGLE_ADS_CUSTOMER_ID, GOOGLE_ADS_REFRESH_TOKEN (plus "
                      "GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET for OAuth).",
            "gaql_reference": GAQL_VIDEO_CAMPAIGN_METRICS.strip(),
        }

    # --- Real path: stream GAQL against the Google Ads API ---
    import os
    from google.ads.googleads.client import GoogleAdsClient

    config = {
        "developer_token": settings.google_ads_developer_token,
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET", ""),
        "refresh_token": settings.google_ads_refresh_token,
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""),
        "use_proto_plus": True,
    }
    client = GoogleAdsClient.load_from_dict(config)
    ga_service = client.get_service("GoogleAdsService")
    request = client.get_type("SearchGoogleAdsStreamRequest")
    request.customer_id = settings.google_ads_customer_id.replace("-", "")
    request.query = GAQL_VIDEO_CAMPAIGN_METRICS

    metrics: list[dict[str, Any]] = []
    for batch in ga_service.search_stream(request):
        for row in batch.results:
            c = row.campaign
            m = row.metrics
            cost_micros = float(m.cost_micros) if m.cost_micros else 0.0
            revenue = float(m.all_conversions_value) if m.all_conversions_value else 0.0
            cost_per_conv = float(m.cost_per_conversion) if m.cost_per_conversion else 0.0
            metrics.append({
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                "format": row.segments.ad_format_type.name if row.segments.ad_format_type else "",
                "impressions": int(m.impressions) if m.impressions else 0,
                "views": int(m.views) if m.views else 0,
                "clicks": int(m.clicks) if m.clicks else 0,
                "ctr": float(m.ctr) if m.ctr else 0.0,
                "cpc": float(m.average_cpc_micros) / 1e6 if m.average_cpc_micros else 0.0,
                "cpv": float(m.average_cpv_micros) / 1e6 if m.average_cpv_micros else 0.0,
                "conversions": float(m.conversions) if m.conversions else 0.0,
                "conversion_rate": float(m.conversion_rate) if m.conversion_rate else 0.0,
                "cpa": cost_per_conv / 1e6,
                "cost": cost_micros / 1e6,
                "revenue": revenue,
                "roas": (revenue / cost_micros) if cost_micros > 0 else 0.0,
                "provenance": "LIVE_DATA",
            })

    return {
        "metrics": metrics,
        "n_rows": len(metrics),
        "provenance": "LIVE_DATA",
        "detail": f"GAQL streamed {len(metrics)} campaign-format rows.",
        "note": "Organic YouTube statistics (separate module) are never blended with these paid metrics.",
    }


# Supported metric labels (only those the GAQL query returns).
SUPPORTED_METRICS = [
    "impressions", "views", "clicks", "ctr", "cpc", "cpv",
    "conversions", "conversion_rate", "cpa", "cost", "revenue", "roas",
]
