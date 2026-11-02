"""Adapter registry — the multi-platform plug-in point.

Adding a new platform = one file in scraping/ + one entry here.
"""
from typing import Dict, List, Optional, Type

from .amazon import AmazonAdapter
from .base import PlatformAdapter
from .daraz import DarazAdapter
from .reddit import RedditAdapter
from .youtube import YouTubeAdapter

ADAPTERS: Dict[str, Type[PlatformAdapter]] = {
    YouTubeAdapter.name: YouTubeAdapter,
    RedditAdapter.name: RedditAdapter,
    DarazAdapter.name: DarazAdapter,
    AmazonAdapter.name: AmazonAdapter,
}

DEFAULT_PLATFORMS: List[str] = [name for name, cls in ADAPTERS.items() if cls.enabled_by_default]


def resolve_platforms(requested: Optional[List[str]]) -> List[str]:
    if not requested:
        return list(DEFAULT_PLATFORMS)
    unknown = [p for p in requested if p not in ADAPTERS]
    if unknown:
        raise ValueError(f"unknown platform(s): {', '.join(unknown)}")
    return list(requested)


def platform_meta() -> List[Dict]:
    return [
        {
            "id": name,
            "label": cls.label,
            "experimental": cls.experimental,
            "enabled_by_default": cls.enabled_by_default,
            "rate_limit_rps": cls.rate,
        }
        for name, cls in ADAPTERS.items()
    ]
