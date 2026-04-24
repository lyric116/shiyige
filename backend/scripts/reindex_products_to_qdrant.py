from __future__ import annotations

import argparse

from backend.app.core.database import get_session_factory
from backend.app.tasks.qdrant_index_tasks import (
    delete_product_points,
    retry_failed_product_indexing,
    sync_products_to_qdrant,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync products into Qdrant")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental", "retry_failed", "delete"],
        default="full",
        help="Sync mode",
    )
    parser.add_argument(
        "--product-id",
        action="append",
        dest="product_ids",
        type=int,
        help="Specific product id to sync or delete. Can be provided multiple times.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        if args.mode == "retry_failed":
            result = retry_failed_product_indexing(session)
        elif args.mode == "delete":
            result = delete_product_points(session, product_ids=args.product_ids or [])
        else:
            result = sync_products_to_qdrant(
                session,
                mode=args.mode,
                product_ids=args.product_ids,
            )

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
