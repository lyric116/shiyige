from statistics import mean

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.v1.users import get_current_user
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.order import Order, OrderItem
from backend.app.models.product import Product
from backend.app.models.review import Review, ReviewImage
from backend.app.models.user import User, UserProfile
from backend.app.schemas.review import CreateReviewRequest


router = APIRouter(prefix="/products", tags=["reviews"])


def get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
    return product


def build_review_query(product_id: int):
    return (
        select(Review)
        .options(
            selectinload(Review.images),
            selectinload(Review.user).selectinload(User.profile),
        )
        .where(Review.product_id == product_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
    )


def serialize_review(review: Review) -> dict[str, object]:
    user = review.user
    profile = user.profile if user else None
    reviewer_name = "匿名用户" if review.is_anonymous else (profile.display_name if profile else None) or user.username
    return {
        "id": review.id,
        "user_id": review.user_id,
        "product_id": review.product_id,
        "order_id": review.order_id,
        "rating": review.rating,
        "content": review.content,
        "is_anonymous": review.is_anonymous,
        "reviewer_name": reviewer_name,
        "image_urls": [image.image_url for image in sorted(review.images, key=lambda item: (item.sort_order, item.id))],
        "created_at": review.created_at.isoformat(),
    }


def get_paid_order_for_review(db: Session, *, user_id: int, product_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .join(Order.items)
        .where(
            Order.user_id == user_id,
            Order.status == "PAID",
            OrderItem.product_id == product_id,
        )
        .order_by(Order.paid_at.desc(), Order.id.desc())
    )


@router.post("/{product_id}/reviews")
def create_review(
    product_id: int,
    payload: CreateReviewRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_product_or_404(db, product_id)

    existing_review = db.scalar(
        select(Review).where(Review.user_id == current_user.id, Review.product_id == product_id)
    )
    if existing_review is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="review already exists")

    paid_order = get_paid_order_for_review(db, user_id=current_user.id, product_id=product_id)
    if paid_order is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="review not allowed")

    review = Review(
        user_id=current_user.id,
        product_id=product_id,
        order_id=paid_order.id,
        rating=payload.rating,
        content=payload.content.strip(),
        is_anonymous=payload.is_anonymous,
    )

    for index, image_url in enumerate(payload.image_urls, start=1):
        cleaned_url = image_url.strip()
        if not cleaned_url:
            continue
        review.images.append(
            ReviewImage(
                image_url=cleaned_url,
                sort_order=index,
            )
        )

    db.add(review)
    db.commit()

    created_review = db.scalar(build_review_query(product_id).where(Review.id == review.id))
    assert created_review is not None

    return build_response(
        request=request,
        code=0,
        message="review created",
        data={"review": serialize_review(created_review)},
        status_code=201,
    )


@router.get("/{product_id}/reviews")
def list_reviews(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
):
    get_product_or_404(db, product_id)

    reviews = db.scalars(build_review_query(product_id)).unique().all()
    total = len(reviews)
    start = (page - 1) * page_size
    end = start + page_size
    items = reviews[start:end]

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "items": [serialize_review(review) for review in items],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        status_code=200,
    )


@router.get("/{product_id}/reviews/stats")
def get_review_stats(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    get_product_or_404(db, product_id)

    ratings = db.scalars(select(Review.rating).where(Review.product_id == product_id)).all()
    rating_counts = {str(star): 0 for star in range(1, 6)}
    for rating in ratings:
        rating_counts[str(rating)] += 1

    average_rating = round(mean(ratings), 2) if ratings else 0.0

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "total": len(ratings),
            "average_rating": average_rating,
            "rating_counts": rating_counts,
        },
        status_code=200,
    )
