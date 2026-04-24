# Embedding Model Design

## Default Production Models

- Dense retrieval:
  - provider: `fastembed_dense`
  - model: `BAAI/bge-small-zh-v1.5`
  - dimension: `512`
  - purpose: Chinese semantic recall for search and recommendation candidates
- Sparse retrieval:
  - provider: `fastembed_sparse`
  - model: `Qdrant/bm25`
  - dimension: sparse dynamic vector
  - purpose: keyword recall so product names, culture terms, festivals, and niche nouns are not lost by dense semantics
- Late interaction rerank:
  - provider: `fastembed_colbert`
  - model: `answerdotai/answerai-colbert-small-v1`
  - dimension: `96`
  - purpose: token-level rerank on a candidate set, not first-stage full-corpus recall

## Test and Local Fallback

- `local_hash` remains available only as a deterministic fallback for unit tests and lightweight local smoke runs.
- Test fixtures pin:
  - `EMBEDDING_PROVIDER=local_hash`
  - `SPARSE_EMBEDDING_PROVIDER=local_hash`
  - `COLBERT_EMBEDDING_PROVIDER=local_hash`
- This keeps CI and local regression runs free from model downloads while production-like environments still use real models.

## Product Text Construction

The product text builder now emits four explicit text views instead of one flat string:

- `title_text`
  - short identity text for product name and subtitle
- `semantic_text`
  - dense embedding source
  - focuses on category, culture summary, dynasty style, craft, festival, scene, tags, and derived pricing/gift signals
- `keyword_text`
  - sparse embedding source
  - compact keyword list that preserves exact nouns such as `香囊`, `簪子`, `宋代`, `端午`
- `rerank_text`
  - ColBERT source
  - keeps title, description, culture explanation, structured cultural fields, and keyword summary together

Current schema-backed cultural fields:

- product name
- subtitle
- category
- description
- culture summary
- dynasty style
- craft type
- festival tag
- scene tag
- tags
- derived price band
- derived gift attribute when tags or festival/scene imply gifting
- derived pairing attribute when tags imply matching or set combinations

`embedding_text` is still exposed as an alias to `semantic_text` so the current search and recommendation code does not break during the migration.

## Runtime Configuration

The following settings now control embedding runtime:

- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL_NAME`
- `EMBEDDING_DIMENSION`
- `EMBEDDING_CACHE_DIR`
- `SPARSE_EMBEDDING_PROVIDER`
- `SPARSE_EMBEDDING_MODEL_NAME`
- `COLBERT_EMBEDDING_PROVIDER`
- `COLBERT_EMBEDDING_MODEL_NAME`
- `COLBERT_EMBEDDING_DIMENSION`

`docker-compose.yml` mounts `/app/backend/.cache/fastembed` to a named volume so downloaded ONNX weights can be reused between container restarts.

## Replacement Guidance

- To swap dense semantics, change `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL_NAME`, and `EMBEDDING_DIMENSION` together.
- To swap sparse recall, change `SPARSE_EMBEDDING_PROVIDER` and `SPARSE_EMBEDDING_MODEL_NAME`.
- To swap rerank model, change `COLBERT_EMBEDDING_PROVIDER`, `COLBERT_EMBEDDING_MODEL_NAME`, and `COLBERT_EMBEDDING_DIMENSION`.
- If dimensions change, recreate or migrate the Qdrant collection schema before writing new points.
