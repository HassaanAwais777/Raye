"""Pydantic request models. Responses are plain JSON-serializable dicts (see analysis/verdict.py)."""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200, description="Product to research, e.g. 'Galaxy S24 review'")
    platforms: Optional[List[str]] = Field(None, description="Subset of platform ids; None = all stable platforms")
    max_comments: int = Field(3000, ge=10, le=200000)
    sources_per_platform: int = Field(10, ge=1, le=100, description="Videos / posts / products to crawl per platform")
    comments_per_source: int = Field(200, ge=10, le=5000)
    sort: str = Field("top", pattern="^(top|new)$")

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be empty")
        return v
