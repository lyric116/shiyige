from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import get_session_factory, reset_database_state
from backend.app.core.security import hash_password
from backend.app.models.base import Base
from backend.app.models.product import Product
from backend.app.models.user import User, UserBehaviorLog, UserProfile
from backend.app.services.embedding import get_embedding_provider
from backend.app.services.recommendations import recommend_products_for_user
from backend.app.services.vector_search import semantic_search_products
from backend.scripts.seed_base_data import seed_base_data

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_PATH = ROOT / "docs" / "recommendation_baseline_metrics.json"

BASELINE_SEARCH_QUERIES = [
    "适合春日出游的素雅汉服",
    "端午香囊送礼",
    "古风发簪饰品",
    "宋韵茶器雅致礼物",
]

BASELINE_USER_CASES = [
    {
        "email": "baseline-hanfu@example.com",
        "username": "baseline-hanfu",
        "display_name": "基线汉服用户",
        "seed_query": "春日汉服",
        "behaviors": [
            {
                "behavior_type": "search",
                "target_type": "search",
                "ext_json": {"query": "春日汉服", "mode": "baseline"},
            },
            {
                "behavior_type": "view_product",
                "target_type": "product",
                "product_name": "明制襦裙",
            },
            {
                "behavior_type": "add_to_cart",
                "target_type": "product",
                "product_name": "明制襦裙",
                "ext_json": {"quantity": 1, "mode": "baseline"},
            },
        ],
    },
    {
        "email": "baseline-gift@example.com",
        "username": "baseline-gift",
        "display_name": "基线送礼用户",
        "seed_query": "香囊发簪送礼",
        "behaviors": [
            {
                "behavior_type": "search",
                "target_type": "search",
                "ext_json": {"query": "端午香囊送礼", "mode": "baseline"},
            },
            {
                "behavior_type": "view_product",
                "target_type": "product",
                "product_name": "故宫宫廷香囊",
            },
            {
                "behavior_type": "search",
                "target_type": "search",
                "ext_json": {"query": "古风发簪", "mode": "baseline"},
            },
            {
                "behavior_type": "add_to_cart",
                "target_type": "product",
                "product_name": "点翠发簪",
                "ext_json": {"quantity": 1, "mode": "baseline"},
            },
        ],
    },
]


def ensure_schema(session: Session) -> None:
    Base.metadata.create_all(bind=session.get_bind())


def ensure_baseline_user(session: Session, *, email: str, username: str, display_name: str) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            username=username,
            password_hash=hash_password("baseline-pass-123"),
            role="user",
            is_active=True,
        )
        user.profile = UserProfile(display_name=display_name)
        session.add(user)
        session.flush()
        return user

    user.username = username
    user.is_active = True
    if user.profile is None:
        user.profile = UserProfile(display_name=display_name)
    else:
        user.profile.display_name = display_name
    session.flush()
    return user


def get_product_id_by_name(session: Session, product_name: str) -> int:
    product_id = session.scalar(select(Product.id).where(Product.name == product_name))
    if product_id is None:
        raise RuntimeError(f"baseline product not found: {product_name}")
    return int(product_id)


def ensure_baseline_behaviors(
    session: Session,
    *,
    user: User,
    behaviors: list[dict[str, object]],
) -> None:
    existing_count = session.scalar(
        select(UserBehaviorLog.id).where(UserBehaviorLog.user_id == user.id).limit(1)
    )
    if existing_count is not None:
        return

    for behavior in behaviors:
        ext_json = dict(behavior.get("ext_json") or {})
        product_name = behavior.get("product_name")
        target_id = None
        if isinstance(product_name, str):
            target_id = get_product_id_by_name(session, product_name)
            ext_json.setdefault("product_name", product_name)

        session.add(
            UserBehaviorLog(
                user_id=user.id,
                behavior_type=str(behavior["behavior_type"]),
                target_type=str(behavior["target_type"]),
                target_id=target_id,
                ext_json=ext_json or None,
            )
        )
    session.flush()


def seed_baseline_dataset(session: Session) -> list[dict[str, object]]:
    seed_base_data(session)

    prepared_users: list[dict[str, object]] = []
    for case in BASELINE_USER_CASES:
        user = ensure_baseline_user(
            session,
            email=case["email"],
            username=case["username"],
            display_name=case["display_name"],
        )
        ensure_baseline_behaviors(session, user=user, behaviors=case["behaviors"])
        prepared_users.append(
            {
                "email": case["email"],
                "seed_query": case["seed_query"],
                "user_id": user.id,
            }
        )

    session.commit()
    return prepared_users


def serialize_result_items(results) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for index, result in enumerate(results, start=1):
        items.append(
            {
                "rank": index,
                "product_id": result.product.id,
                "name": result.product.name,
                "score": round(float(result.score), 6),
                "reason": result.reason,
            }
        )
    return items


def build_case_payload(
    *,
    case_type: str,
    label: str,
    query: str,
    user_id: int | None,
    results,
    latency_ms: float,
) -> dict[str, object]:
    items = serialize_result_items(results)
    return {
        "case_type": case_type,
        "label": label,
        "query": query,
        "user_id": user_id,
        "returned_product_ids": [item["product_id"] for item in items],
        "score": items[0]["score"] if items else None,
        "reason": items[0]["reason"] if items else None,
        "latency_ms": round(latency_ms, 3),
        "items": items,
    }


def export_baseline_metrics(output_path: Path = DEFAULT_OUTPUT_PATH) -> dict[str, object]:
    session = get_session_factory()()
    try:
        ensure_schema(session)
        baseline_users = seed_baseline_dataset(session)
        provider = get_embedding_provider()

        search_cases: list[dict[str, object]] = []
        for query in BASELINE_SEARCH_QUERIES:
            started_at = perf_counter()
            results = semantic_search_products(
                session,
                query=query,
                limit=5,
                provider=provider,
                force_baseline=True,
            )
            latency_ms = (perf_counter() - started_at) * 1000
            search_cases.append(
                build_case_payload(
                    case_type="semantic_search",
                    label=f"search::{query}",
                    query=query,
                    user_id=None,
                    results=results,
                    latency_ms=latency_ms,
                )
            )

        recommendation_cases: list[dict[str, object]] = []
        for user_case in baseline_users:
            started_at = perf_counter()
            results = recommend_products_for_user(
                session,
                user_id=int(user_case["user_id"]),
                limit=5,
                provider=provider,
            )
            latency_ms = (perf_counter() - started_at) * 1000
            recommendation_cases.append(
                build_case_payload(
                    case_type="personalized_recommendation",
                    label=f"recommend::{user_case['email']}",
                    query=str(user_case["seed_query"]),
                    user_id=int(user_case["user_id"]),
                    results=results,
                    latency_ms=latency_ms,
                )
            )

        payload = {
            "provider": provider.describe(),
            "search_cases": search_cases,
            "recommendation_cases": recommendation_cases,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return payload
    finally:
        session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export baseline recommendation metrics.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the exported JSON file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = export_baseline_metrics(output_path=args.output)
    print(
        "Exported baseline recommendation metrics"
        f" search_cases={len(payload['search_cases'])}"
        f" recommendation_cases={len(payload['recommendation_cases'])}"
        f" output={args.output}"
    )


if __name__ == "__main__":
    reset_database_state()
    main()
