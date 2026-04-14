from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.product import Category, Product
from backend.scripts.seed_base_data import seed_base_data


def test_seed_base_data_creates_expected_category_and_product_counts() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_base_data(session)

        category_count = session.scalar(select(func.count(Category.id)))
        product_count = session.scalar(select(func.count(Product.id)))
        category_names = {category.name for category in session.scalars(select(Category)).all()}

        assert category_count == 5
        assert product_count == 20
        assert category_names == {"汉服", "文创", "非遗", "饰品", "礼盒"}
