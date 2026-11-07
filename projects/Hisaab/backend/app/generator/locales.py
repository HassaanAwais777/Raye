"""Locale packs: the same generator produces a Pakistani-market dataset or a
global one — currency, cities, cost levels and seasonality all switch.

Calibration (see docs/ARCHITECTURE.md §2): per-platform CPC / CTR / CVR are chosen so the
BLENDED ROAS lands near 3.0 with a credible spread (Google strongest, TikTok weakest) —
in both locales, so the optimizer story is locale-independent.
"""
from dataclasses import dataclass, field

PLATFORMS = ("facebook", "instagram", "google", "tiktok", "youtube")

# Campaign catalogue: name → platform (a campaign belongs to exactly one platform)
CAMPAIGNS = {
    "facebook": ("FB_Prospecting_AlwaysOn", "FB_Retargeting_Cart", "FB_Lookalike_Scale"),
    "instagram": ("IG_Reels_Awareness", "IG_Stories_Offer", "IG_Influencer_Boost"),
    "google": ("GO_Search_Brand", "GO_Search_NonBrand", "GO_Shopping_Feed", "GO_PMax_Scale"),
    "tiktok": ("TT_Creator_Sparks", "TT_InFeed_Awareness"),
    "youtube": ("YT_Skippable_InStream", "YT_Shorts_Bump", "YT_Masthead_Splash"),
}


@dataclass(frozen=True)
class LocalePack:
    code: str                       # "pk" | "global"
    label: str
    currency: str                   # "PKR" | "USD"
    symbol: str                     # "Rs." | "$"
    cities: tuple                   # (name, weight)
    aov_base: float                 # average order value, local currency
    seasons: tuple                  # (name, start-mm, end-mm, multiplier)
    ctr: dict                       # platform → click-through rate
    cvr: dict                       # platform → conversion rate (click → purchase)
    cpc: dict                       # platform → cost per click (local currency)
    daily_spend: dict               # platform → baseline daily spend (local currency)
    platform_weights: dict          # platform → share of rows
    age: dict                       # platform → age-band distribution
    gender: dict                    # platform → (male, female, unknown)
    device: dict                    # platform → (mobile, desktop, tablet)


_AGE = {
    "facebook": (.18, .30, .27, .15, .10), "instagram": (.30, .38, .19, .09, .04),
    "google": (.15, .30, .28, .17, .10), "tiktok": (.45, .33, .15, .05, .02),
    "youtube": (.22, .32, .25, .13, .08),
}
_AGE_BANDS = ("18-24", "25-34", "35-44", "45-54", "55+")

PK = LocalePack(
    code="pk", label="Pakistan", currency="PKR", symbol="Rs.",
    cities=(("Karachi", 0.26), ("Lahore", 0.19), ("Islamabad", 0.10), ("Rawalpindi", 0.06),
            ("Faisalabad", 0.08), ("Multan", 0.05), ("Peshawar", 0.05), ("Quetta", 0.04),
            ("Sialkot", 0.04), ("Hyderabad", 0.05), ("Other", 0.08)),
    aov_base=2800.0,
    seasons=(("Ramadan", "03", "04", 1.45), ("Eid", "05", "05", 1.30),
             ("11.11", "11", "11", 1.25), ("12.12", "12", "12", 1.20),
             ("Independence", "08", "08", 1.12)),
    ctr={"facebook": .0110, "instagram": .0090, "google": .0280, "tiktok": .0060, "youtube": .0050},
    cvr={"facebook": .0240, "instagram": .0220, "google": .0200, "tiktok": .0095, "youtube": .0135},
    cpc={"facebook": 22.0, "instagram": 20.0, "google": 13.0, "tiktok": 12.0, "youtube": 16.0},
    daily_spend={"facebook": 60000., "instagram": 45000., "google": 55000.,
                 "tiktok": 30000., "youtube": 25000.},
    platform_weights={"facebook": .26, "instagram": .22, "google": .24,
                      "tiktok": .16, "youtube": .12},
    age=_AGE, gender={
        "facebook": (.47, .51, .02), "instagram": (.42, .56, .02), "google": (.52, .46, .02),
        "tiktok": (.52, .46, .02), "youtube": (.58, .40, .02)},
    device={
        "facebook": (.78, .18, .04), "instagram": (.88, .10, .02), "google": (.64, .32, .04),
        "tiktok": (.94, .05, .01), "youtube": (.72, .24, .04)},
)

GLOBAL = LocalePack(
    code="global", label="Global (tier-1 mix)", currency="USD", symbol="$",
    cities=(("New York", 0.14), ("London", 0.13), ("Dubai", 0.10), ("Toronto", 0.08),
            ("Berlin", 0.08), ("Singapore", 0.08), ("Sydney", 0.07), ("Mumbai", 0.10),
            ("Lagos", 0.06), ("São Paulo", 0.08), ("Other", 0.08)),
    aov_base=58.0,
    seasons=(("Black Friday", "11", "11", 1.55), ("Christmas", "12", "12", 1.35),
             ("Back to school", "08", "09", 1.15), ("Summer", "06", "07", 1.08)),
    ctr={"facebook": .0110, "instagram": .0090, "google": .0280, "tiktok": .0060, "youtube": .0050},
    cvr={"facebook": .0200, "instagram": .0190, "google": .0340, "tiktok": .0100, "youtube": .0140},
    cpc={"facebook": 0.40, "instagram": 0.38, "google": 0.50, "tiktok": 0.28, "youtube": 0.30},
    daily_spend={"facebook": 1400., "instagram": 1050., "google": 1300.,
                 "tiktok": 700., "youtube": 600.},
    platform_weights={"facebook": .26, "instagram": .22, "google": .24,
                      "tiktok": .16, "youtube": .12},
    age=_AGE, gender={
        "facebook": (.47, .51, .02), "instagram": (.42, .56, .02), "google": (.52, .46, .02),
        "tiktok": (.52, .46, .02), "youtube": (.58, .40, .02)},
    device={
        "facebook": (.78, .18, .04), "instagram": (.88, .10, .02), "google": (.64, .32, .04),
        "tiktok": (.94, .05, .01), "youtube": (.72, .24, .04)},
)

LOCALES = {lp.code: lp for lp in (PK, GLOBAL)}
AGE_BANDS = _AGE_BANDS


def get_locale(code: str) -> LocalePack:
    try:
        return LOCALES[code]
    except KeyError:
        raise ValueError(f"unknown locale '{code}'; available: {', '.join(LOCALES)}") from None
