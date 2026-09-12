"""Teacher-to-teacher marketplace routes (not the student catalog -- see
enrollment/router.py): list a course for sale, browse/search others' active
listings, buy one (mocked payment, grants an independent copy
immediately). See marketplace/service.py's module docstring."""
from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.context import require_role
from . import service
from .schemas import ListingCreate

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


@router.get("/listings")
def browse_listings(q: str | None = Query(default=None, max_length=200), user: dict = Depends(require_role("teacher"))):
    # Excludes the caller's own listings -- browsing to buy from yourself
    # isn't a real scenario, and it keeps a seller's feed from cluttering
    # their own search results.
    return service.list_active_listings(q, exclude_seller_id=user["id"])


@router.get("/listings/{listing_id}")
def listing_detail(listing_id: str, _: dict = Depends(require_role("teacher"))):
    listing = service.get_listing(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing


@router.post("/listings", status_code=201)
def create_listing(body: ListingCreate, user: dict = Depends(require_role("teacher"))):
    try:
        return service.create_listing(user["id"], body.courseId, body.title, body.description, body.priceCents)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/listings/{listing_id}/deactivate")
def deactivate_listing(listing_id: str, user: dict = Depends(require_role("teacher"))):
    try:
        listing = service.deactivate_listing(listing_id, user["id"])
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing


@router.post("/listings/{listing_id}/purchase", status_code=201)
def purchase_listing(listing_id: str, user: dict = Depends(require_role("teacher"))):
    try:
        return service.purchase_listing(listing_id, user["id"])
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/mine/listings")
def my_listings(user: dict = Depends(require_role("teacher"))):
    return service.list_my_listings(user["id"])


@router.get("/mine/purchases")
def my_purchases(user: dict = Depends(require_role("teacher"))):
    return service.list_my_purchases(user["id"])
