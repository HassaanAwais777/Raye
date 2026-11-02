import pytest

from app.scraping.registry import DEFAULT_PLATFORMS, platform_meta, resolve_platforms


def test_defaults_include_stable_platforms():
    assert "youtube" in DEFAULT_PLATFORMS and "reddit" in DEFAULT_PLATFORMS


def test_experimental_not_enabled_by_default():
    assert "daraz" not in DEFAULT_PLATFORMS and "amazon" not in DEFAULT_PLATFORMS


def test_resolve_explicit():
    assert resolve_platforms(["daraz"]) == ["daraz"]


def test_resolve_unknown_raises():
    with pytest.raises(ValueError):
        resolve_platforms(["tiktok"])


def test_platform_meta_shape():
    meta = {p["id"]: p for p in platform_meta()}
    assert meta["youtube"]["experimental"] is False
    assert meta["amazon"]["experimental"] is True
