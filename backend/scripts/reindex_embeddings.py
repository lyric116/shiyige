from __future__ import annotations

import argparse

from backend.app.core.database import get_session_factory
from backend.app.services.embedding import EmbeddingProvider, get_embedding_provider
from backend.app.tasks.embedding_tasks import reindex_product_embeddings


def run_reindex_command(
    *,
    provider: EmbeddingProvider | None = None,
    force: bool = True,
    session_factory=None,
) -> dict[str, object]:
    factory = session_factory or get_session_factory()
    embedding_provider = provider or get_embedding_provider()

    with factory() as session:
        return reindex_product_embeddings(session, provider=embedding_provider, force=force)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild product embeddings")
    parser.add_argument("--incremental", action="store_true", help="Only update changed products")
    args = parser.parse_args()

    result = run_reindex_command(force=not args.incremental)
    print(f"indexed={result['indexed']} skipped={result['skipped']} model={result['model_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
