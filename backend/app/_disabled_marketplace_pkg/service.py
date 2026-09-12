"""The curriculum marketplace: teachers list one of their own courses for
sale, other teachers browse/search/buy it, and buying hands the buyer an
independent, editable copy of the course (not a link back to the
seller's) -- see `db/models.py`'s `Listing`/`Purchase` docstrings.

Payment is mocked: `purchase_listing` grants the copy immediately with no
payment processor involved, matching this prototype's "zero external
dependencies" spirit elsewhere (courses/service.py, auth/security.py).
Wire a real processor (Stripe et al.) behind `purchase_listing`'s call
site in marketplace/router.py before this ever takes real money.

A listed course keeps working as the seller's own live course throughout
-- `Listing.course_id` just points at it for browsing; nothing about
listing a course freezes or forks it. Only `purchase_listing` copies.
"""
import logging

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..courses.service import COURSE_LOAD, get_course
from ..db.models import Course, Lesson, Listing, Module, Purchase, Quiz, QuizItem, User
from ..db.session import SessionLocal

logger = logging.getLogger(__name__)


def _serialize_listing(listing: Listing, course: Course, seller: User) -> dict:
    week_count = len(course.modules)
    lesson_count = sum(len(m.lessons) for m in course.modules)
    return {
        "id": listing.id,
        "courseId": listing.course_id,
        "sellerId": listing.seller_id,
        "sellerName": seller.name,
        "title": listing.title,
        "description": listing.description,
        "priceCents": listing.price_cents,
        "isActive": listing.is_active,
        "createdAt": listing.created_at.isoformat(),
        "weekCount": week_count,
        "lessonCount": lesson_count,
        "audience": course.audience,
    }


def _serialize_listing_detail(listing: Listing, course: Course, seller: User) -> dict:
    """Adds the syllabus *outline* (week/lesson titles + objectives) as a
    preview -- but never slides, speaker notes, or quiz content. Those stay
    behind the paywall until `purchase_listing` hands over a real copy."""
    base = _serialize_listing(listing, course, seller)
    base["weeks"] = [
        {
            "week": m.week_number,
            "title": m.title,
            "lessons": [{"title": l.title, "objective": l.objective} for l in m.lessons],
        }
        for m in course.modules
    ]
    return base


def create_listing(seller_id: str, course_id: str, title: str, description: str, price_cents: int) -> dict:
    if price_cents <= 0:
        raise ValueError("Price must be greater than zero")
    with SessionLocal() as session:
        course = session.scalar(select(Course).where(Course.id == course_id).options(COURSE_LOAD))
        if not course:
            raise ValueError(f"No course with id {course_id}")
        if course.teacher_id != seller_id:
            raise PermissionError("You don't own this course")
        if not any(l.title for m in course.modules for l in m.lessons):
            raise ValueError("Add at least one lesson before listing this course")
        # One active listing per course -- the frontend (course cards, the
        # topbar badge) assumes at most one, and a second active listing for
        # the same course would just be an invisible, un-unlistable orphan.
        duplicate = session.scalar(
            select(Listing).where(Listing.course_id == course_id, Listing.is_active == True)  # noqa: E712
        )
        if duplicate:
            raise ValueError("This course is already listed")
        listing = Listing(
            course_id=course_id, seller_id=seller_id, title=title, description=description, price_cents=price_cents
        )
        session.add(listing)
        session.commit()
        seller = session.get(User, seller_id)
        logger.info("create_listing: seller=%s course=%s listing=%s price_cents=%d", seller_id, course_id, listing.id, price_cents)
        return _serialize_listing(listing, course, seller)


def deactivate_listing(listing_id: str, seller_id: str) -> dict | None:
    with SessionLocal() as session:
        listing = session.get(Listing, listing_id)
        if not listing:
            return None
        if listing.seller_id != seller_id:
            raise PermissionError("You don't own this listing")
        listing.is_active = False
        session.commit()
        course = session.scalar(select(Course).where(Course.id == listing.course_id).options(COURSE_LOAD))
        seller = session.get(User, seller_id)
        logger.info("deactivate_listing: seller=%s listing=%s", seller_id, listing_id)
        return _serialize_listing(listing, course, seller)


def list_active_listings(query: str | None, exclude_seller_id: str | None = None) -> list[dict]:
    with SessionLocal() as session:
        stmt = select(Listing).where(Listing.is_active == True).options(  # noqa: E712
            selectinload(Listing.course).options(COURSE_LOAD)
        )
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(Listing.title.ilike(like), Listing.description.ilike(like)))
        if exclude_seller_id:
            stmt = stmt.where(Listing.seller_id != exclude_seller_id)
        stmt = stmt.order_by(Listing.created_at.desc())
        listings = session.scalars(stmt).all()
        seller_ids = {l.seller_id for l in listings}
        sellers = {u.id: u for u in session.scalars(select(User).where(User.id.in_(seller_ids)))} if seller_ids else {}
        return [_serialize_listing(l, l.course, sellers[l.seller_id]) for l in listings]


def get_listing(listing_id: str) -> dict | None:
    with SessionLocal() as session:
        listing = session.scalar(
            select(Listing).where(Listing.id == listing_id).options(selectinload(Listing.course).options(COURSE_LOAD))
        )
        if not listing:
            return None
        seller = session.get(User, listing.seller_id)
        return _serialize_listing_detail(listing, listing.course, seller)


def list_my_listings(seller_id: str) -> list[dict]:
    with SessionLocal() as session:
        listings = session.scalars(
            select(Listing)
            .where(Listing.seller_id == seller_id)
            .options(selectinload(Listing.course).options(COURSE_LOAD))
            .order_by(Listing.created_at.desc())
        ).all()
        seller = session.get(User, seller_id)
        return [_serialize_listing(l, l.course, seller) for l in listings]


def purchase_listing(listing_id: str, buyer_id: str) -> dict:
    with SessionLocal() as session:
        listing = session.scalar(
            select(Listing).where(Listing.id == listing_id).options(selectinload(Listing.course).options(COURSE_LOAD))
        )
        if not listing or not listing.is_active:
            raise ValueError("Listing not found")
        if listing.seller_id == buyer_id:
            raise ValueError("You can't buy your own listing")
        # Pre-check for a fast, friendly error in the common case -- but
        # `Purchase`'s (listing_id, buyer_id) unique constraint is the real
        # guard against a double-purchase raced by two concurrent requests
        # for the same buyer (see the IntegrityError handling below).
        existing = session.scalar(
            select(Purchase).where(Purchase.listing_id == listing_id, Purchase.buyer_id == buyer_id)
        )
        if existing:
            raise ValueError("You already own this course")

        source = listing.course
        copy = Course(teacher_id=buyer_id, title=source.title, audience=source.audience)
        for m in source.modules:
            module = Module(week_number=m.week_number, title=m.title)
            for l in m.lessons:
                lesson = Lesson(
                    title=l.title,
                    objective=l.objective,
                    slides=l.slides,
                    speaker_notes=l.speaker_notes,
                    # A purchased course is a fresh draft for the buyer to review
                    # and publish to *their* students -- the same trust gate every
                    # other course goes through, not a shortcut around it.
                    approved=False,
                    published=False,
                )
                for q in l.quizzes:
                    quiz = Quiz(version=q.version)
                    for item in q.items:
                        quiz.items.append(
                            QuizItem(kind=item.kind, prompt=item.prompt, options=item.options, correct_answer=item.correct_answer)
                        )
                    lesson.quizzes.append(quiz)
                module.lessons.append(lesson)
            copy.modules.append(module)
        session.add(copy)
        session.flush()  # assigns copy.id without committing yet

        purchase = Purchase(listing_id=listing_id, buyer_id=buyer_id, course_id=copy.id, price_cents=listing.price_cents)
        session.add(purchase)
        try:
            session.commit()
        except IntegrityError:
            # Two concurrent purchase requests for the same buyer+listing
            # both passed the pre-check above; the unique constraint on
            # Purchase(listing_id, buyer_id) catches the loser here instead
            # of granting a second course copy.
            session.rollback()
            logger.warning("purchase_listing: race on listing=%s buyer=%s, already purchased", listing_id, buyer_id)
            raise ValueError("You already own this course") from None
        new_course_id = copy.id
        logger.info(
            "purchase_listing: buyer=%s listing=%s seller=%s new_course=%s price_cents=%d",
            buyer_id, listing_id, listing.seller_id, new_course_id, listing.price_cents,
        )

    return get_course(new_course_id)


def list_my_purchases(buyer_id: str) -> list[dict]:
    with SessionLocal() as session:
        purchases = session.scalars(
            select(Purchase).where(Purchase.buyer_id == buyer_id).order_by(Purchase.purchased_at.desc())
        ).all()
        listing_ids = {p.listing_id for p in purchases}
        listings = {
            l.id: l for l in session.scalars(select(Listing).where(Listing.id.in_(listing_ids)))
        } if listing_ids else {}
        return [
            {
                "id": p.id,
                "listingId": p.listing_id,
                "listingTitle": listings[p.listing_id].title if p.listing_id in listings else None,
                "courseId": p.course_id,
                "priceCents": p.price_cents,
                "purchasedAt": p.purchased_at.isoformat(),
            }
            for p in purchases
        ]
