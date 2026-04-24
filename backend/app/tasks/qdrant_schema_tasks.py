from __future__ import annotations

from qdrant_client import QdrantClient

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.services.qdrant_client import create_qdrant_client
from backend.app.services.vector_schema import build_product_collection_schema


def ensure_product_collection(
    *,
    client: QdrantClient | None = None,
    settings: AppSettings | None = None,
) -> dict[str, object]:
    app_settings = settings or get_app_settings()
    schema = build_product_collection_schema(app_settings)
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None

    try:
        collection_exists = qdrant_client.collection_exists(schema.collection_name)
        if not collection_exists:
            qdrant_client.create_collection(
                collection_name=schema.collection_name,
                vectors_config=schema.vectors_config,
                sparse_vectors_config=schema.sparse_vectors_config,
                on_disk_payload=True,
            )

        indexed_fields: list[str] = []
        for field_name, field_schema in schema.payload_indexes.items():
            qdrant_client.create_payload_index(
                schema.collection_name,
                field_name,
                field_schema,
                wait=True,
            )
            indexed_fields.append(field_name)

        collection_info = qdrant_client.get_collection(schema.collection_name)
        return {
            "collection_name": schema.collection_name,
            "created": not collection_exists,
            "dense_dimension": schema.dense_dimension,
            "colbert_dimension": schema.colbert_dimension,
            "named_vectors": sorted(schema.vectors_config.keys()),
            "sparse_vectors": sorted(schema.sparse_vectors_config.keys()),
            "payload_indexes": sorted(indexed_fields),
            "payload_schema_fields": sorted(collection_info.payload_schema.keys()),
        }
    finally:
        if owns_client:
            close = getattr(qdrant_client, "close", None)
            if callable(close):
                close()
