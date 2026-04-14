# 数据库设计说明

## 1. 总览

当前系统采用三类存储：

* PostgreSQL：主业务数据，承载用户、商品、订单、会员、评价、后台和推荐画像表。
* Redis：缓存层，当前用于商品详情、首页推荐、搜索建议等读路径缓存。
* MinIO：对象存储，承载商品图与评价图上传文件。

后端 ORM 以 SQLAlchemy 为主，迁移由 Alembic 管理，正式编排下默认通过 `docker compose` 启动 PostgreSQL。

## 2. 业务表分层

### 2.1 用户域

* `users`：前台用户主表，保存邮箱、用户名、密码哈希、角色、启用状态、最近登录时间。
* `user_profile`：用户资料扩展表，保存昵称、手机号、生日、简介、头像。
* `user_address`：收货地址表，支持默认地址。
* `user_behavior_log`：行为日志表，记录浏览、搜索、加购、下单、支付等推荐输入行为。

### 2.2 商品域

* `category`：商品类目。
* `product`：商品主表，保存文化说明、风格、工艺、节令、场景等推荐特征。
* `product_sku`：SKU 表，当前后台按“单默认 SKU”模型维护。
* `inventory`：库存表，按 SKU 一对一维护数量。
* `product_media`：商品媒体表，当前主要保存图片 URL。
* `product_tag`：商品标签表。

### 2.3 交易域

* `cart` / `cart_item`：购物车主表与明细表。
* `orders`：订单主表，保存收货快照、状态、应付金额、备注和幂等键。
* `order_item`：订单商品快照。
* `payment_record`：支付记录，当前用于模拟支付。

### 2.4 会员域

* `member_level`：会员等级规则。
* `point_account`：用户积分账户与累计消费。
* `point_log`：积分流水，当前主要在订单支付后写入。

### 2.5 推荐域

* `product_embedding`：商品 embedding 文本、向量和内容哈希。
* `user_interest_profile`：用户兴趣画像、top terms、行为计数与画像向量。

### 2.6 评价与后台域

* `review` / `review_image`：商品评价与评价图片。
* `admin_user`：后台管理员账号。
* `operation_log`：后台操作审计日志。

## 3. 关键关系

* 一个 `users` 对应一个 `user_profile`、零到多条 `user_address`、零到多条 `orders`、零到多条 `review`。
* 一个 `product` 对应零到多条 `product_sku`、`product_media`、`product_tag`、`review`。
* 一个 `orders` 对应零到多条 `order_item` 和 `payment_record`。
* 一个 `users` 对应一个 `point_account` 和一个 `user_interest_profile`。

## 4. 设计约束

* 订单只在支付成功时扣库存并累积积分。
* 推荐结果依赖 `user_behavior_log`，行为写入后必须失效该用户的推荐缓存。
* 迁移脚本需要同时兼容 SQLite 测试环境和 PostgreSQL 运行环境，布尔默认值统一使用 `sa.false()` / `sa.true()`。
