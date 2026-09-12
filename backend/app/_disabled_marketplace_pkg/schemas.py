"""Request body for creating a listing (marketplace/router.py)."""
from pydantic import BaseModel, Field


class ListingCreate(BaseModel):
    courseId: str
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    # Bounded above as a sanity ceiling against a fat-fingered or abusive
    # price, not a real business limit -- $50,000 (mocked payment, no
    # processor to enforce anything tighter yet).
    priceCents: int = Field(gt=0, le=50_000_00)
