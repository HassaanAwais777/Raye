"""Pydantic request models."""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    rows: int = Field(100000, ge=10, le=20_000_000)
    locale: str = Field("pk", pattern="^(pk|global)$")
    seed: int = Field(42, ge=0)
    with_csv: bool = Field(True, description="also write the CSV twin (needed for MapReduce)")


class BenchmarkRequest(BaseModel):
    scales: List[int] = Field(default_factory=lambda: [10000, 100000, 1000000])
    engines: List[str] = Field(default_factory=lambda: ["pandas", "polars", "mapreduce"])
    locale: str = Field("pk", pattern="^(pk|global)$")
    repeat: int = Field(3, ge=1, le=7)
    mr_procs: int = Field(2, ge=1, le=8)

    @field_validator("scales")
    @classmethod
    def cap_scales(cls, v):
        cleaned = sorted({int(s) for s in v if 100 <= s <= 20_000_000})
        if not cleaned:
            raise ValueError("need at least one scale between 100 and 20,000,000")
        return cleaned


class RecommendRequest(BaseModel):
    dataset: str
    budget: float = Field(1_000_000, gt=0, le=1_000_000_000)
    with_ci: bool = True
    sentiment_aware: bool = Field(
        False, description="apply Raye brand-health multipliers (sentiment overlay)")
