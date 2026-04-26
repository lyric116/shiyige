from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.product import Category, Product
from backend.scripts.seed_base_data import PRODUCT_SEEDS, seed_base_data


def test_seed_base_data_populates_complete_product_domain() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        result = seed_base_data(session)

        assert result["categories"] >= 5
        assert result["products"] >= 20

        products = session.scalars(select(Product).order_by(Product.id.asc())).all()
        assert len(products) >= 20
        assert len(session.scalars(select(Category)).all()) >= 5

        for product in products:
            assert product.culture_summary
            assert product.default_sku is not None
            assert product.default_sku.inventory is not None
            assert product.default_sku.inventory.quantity > 0
            assert len(product.media_items) >= 1
            assert len(product.tags) >= 1


def test_seed_base_data_resyncs_existing_product_assets() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_base_data(session)

        seed_product = next(item for item in PRODUCT_SEEDS if item["name"] == "宋风褙子套装")
        product = session.scalar(
            select(Product).where(Product.name == seed_product["name"])
        )
        assert product is not None

        product.cover_url = "images/汉服/明制襦裙1.jpg"
        product.media_items[0].url = "images/汉服/明制襦裙1.jpg"
        session.commit()

        result = seed_base_data(session)

        session.refresh(product)
        assert result["products"] >= len(PRODUCT_SEEDS)
        assert product.cover_url == seed_product["cover_url"]
        assert [media.url for media in product.media_items] == seed_product["media_urls"]
