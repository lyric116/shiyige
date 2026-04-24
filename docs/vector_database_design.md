# 向量数据库设计

## 1. 目标

本阶段把向量数据库从“业务表里的 JSON 向量”升级为“Qdrant collection + PostgreSQL 同步元数据”的双层结构。

## 2. Qdrant 商品 Collection

Collection 名称：

* `shiyige_products_v1`

Point id：

* 使用业务商品 `product_id`

Named vectors：

* `dense`
  * 维度：`384`
  * 作用：语义召回
* `sparse`
  * 作用：关键词/BM25 通道
* `colbert`
  * 维度：`128`
  * 作用：late interaction rerank 预留

## 3. Payload 字段

当前 collection 设计要求 payload 至少能承载以下字段：

* `product_id`
* `name`
* `subtitle`
* `category_id`
* `category_name`
* `tags`
* `dynasty_style`
* `craft_type`
* `scene_tag`
* `festival_tag`
* `price_min`
* `price_max`
* `stock_available`
* `status`
* `sales_count`
* `review_count`
* `rating_avg`
* `created_at`
* `updated_at`
* `content_hash`
* `embedding_model_version`
* `index_version`

## 4. Payload Index

当前阶段已初始化以下 payload index：

* `status`
* `category_id`
* `category_name`
* `dynasty_style`
* `craft_type`
* `scene_tag`
* `festival_tag`
* `tags`
* `price_min`
* `stock_available`
* `embedding_model_version`

## 5. PostgreSQL 侧同步元数据

`product_embedding` 现在除原有 embedding 文本和 hash 外，还保留：

* `qdrant_point_id`
* `qdrant_collection`
* `index_status`
* `index_error`
* `last_indexed_at`

`user_interest_profile` 现在新增：

* `qdrant_user_point_id`
* `profile_version`
* `last_synced_at`

这些字段的职责是记录“业务对象与 Qdrant 索引之间的同步状态”，而不是继续把 PostgreSQL 当作主检索引擎。
