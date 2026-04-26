from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.product import Product, ProductMedia
from backend.scripts.generate_synthetic_catalog import (
    ensure_synthetic_catalog,
    select_synthetic_media_urls,
)
from backend.scripts.seed_base_data import PRODUCT_SEEDS, seed_base_data


def test_synthetic_catalog_rotates_template_media_pool() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_base_data(session)
        ensure_synthetic_catalog(
            session,
            target_products=len(PRODUCT_SEEDS) + len(PRODUCT_SEEDS) + 1,
        )

        template = session.scalar(select(Product).where(Product.name == "明制襦裙"))
        assert template is not None

        clones = session.scalars(
            select(Product)
            .where(Product.name.like("Synthetic % 明制襦裙"))
            .order_by(Product.id.asc())
        ).all()
        assert len(clones) == 2

        expected_first = select_synthetic_media_urls(template=template, rotation_index=0)
        expected_second = select_synthetic_media_urls(template=template, rotation_index=1)

        assert clones[0].cover_url == expected_first[0]
        assert [media.url for media in clones[0].media_items] == expected_first
        assert clones[1].cover_url == expected_second[0]
        assert [media.url for media in clones[1].media_items] == expected_second
        assert clones[0].cover_url != clones[1].cover_url


def test_synthetic_catalog_resyncs_existing_clone_assets() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_base_data(session)
        ensure_synthetic_catalog(session, target_products=len(PRODUCT_SEEDS) + 20)

        template = session.scalar(select(Product).where(Product.name == "点翠发簪"))
        clone = session.scalar(
            select(Product)
            .where(Product.name.like("Synthetic % 点翠发簪"))
            .order_by(Product.id.asc())
        )
        assert template is not None
        assert clone is not None

        clone.cover_url = "images/文创产品/故宫星空折扇1.jpg"
        clone.media_items = [
            ProductMedia(
                media_type="image",
                url="images/文创产品/故宫星空折扇1.jpg",
                sort_order=1,
            )
        ]
        session.commit()

        result = ensure_synthetic_catalog(session, target_products=len(PRODUCT_SEEDS) + 20)
        session.refresh(clone)

        expected_media = select_synthetic_media_urls(template=template, rotation_index=0)
        assert result["updated_products"] >= 1
        assert clone.cover_url == expected_media[0]
        assert [media.url for media in clone.media_items] == expected_media
