# API 使用指南

## 1. 基础约定

* 基础前缀：`/api/v1`
* 统一响应结构：`code`、`message`、`data`、`request_id`
* 前台鉴权：`Authorization: Bearer <access_token>`，刷新依赖 `refresh_token` Cookie
* 后台鉴权：独立后台 access token，不复用前台 refresh cookie

## 2. 核心接口分组

### 2.1 认证与用户

* `POST /auth/register`
* `POST /auth/login`
* `POST /auth/refresh`
* `POST /auth/logout`
* `GET /users/me`
* `PUT /users/me`
* `PUT /users/password`
* `GET /users/addresses`
* `POST /users/addresses`
* `PUT /users/addresses/{id}`
* `DELETE /users/addresses/{id}`

### 2.2 会员

* `GET /member/profile`
* `GET /member/points`
* `GET /member/benefits`

### 2.3 商品、搜索与评价

* `GET /categories`
* `GET /products`
* `GET /products/{id}`
* `GET /products/{id}/related`
* `GET /products/recommendations`
* `GET /search`
* `GET /search/suggestions`
* `POST /search/semantic`
* `GET /products/{id}/reviews`
* `GET /products/{id}/reviews/stats`
* `POST /products/{id}/reviews`

### 2.4 购物车与订单

* `GET /cart`
* `POST /cart/items`
* `PUT /cart/items/{id}`
* `DELETE /cart/items/{id}`
* `GET /orders`
* `GET /orders/{id}`
* `POST /orders`
* `POST /orders/{id}/pay`
* `POST /orders/{id}/cancel`

### 2.5 媒体上传

* `POST /media/reviews`
* `POST /admin/media/products`

### 2.6 后台

* `POST /admin/auth/login`
* `GET /admin/auth/me`
* `POST /admin/auth/logout`
* `GET /admin/dashboard/summary`
* `GET /admin/products`
* `POST /admin/products`
* `PUT /admin/products/{id}`
* `GET /admin/orders`
* `GET /admin/orders/{id}`
* `POST /admin/reindex/products`

## 3. 演示账号

* 前台演示用户：`user@shiyige-demo.com` / `user123456`
* 后台演示管理员：`admin@shiyige-demo.com` / `admin123456`

## 4. 使用建议

* 前台页面统一通过 `front/js/api.js` 发请求。
* 后台页面统一通过 `admin/js/app.js` 发请求。
* 需要演示个性化推荐变化时，优先走“浏览 -> 搜索 -> 加购 -> 支付”链路，因为这条链路会刷新用户兴趣画像并失效推荐缓存。
