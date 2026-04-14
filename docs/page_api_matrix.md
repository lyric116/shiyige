# 页面与接口映射矩阵

本文件把当前 `front/` 中的页面、未来 `/api/v1` 接口、依赖实体、需要替换的假数据和改造优先级对应起来。它的作用不是定义数据库细节，而是给后续开发者一个“页面改造从哪里下手、要接哪些接口、哪些页面先不动”的执行地图。

## 1. 总体约定

### 1.1 统一接口前缀

所有真实业务接口统一使用：

* `/api/v1`

### 1.2 前端改造原则

* 保留 `front/` 现有页面视觉结构，不做首轮框架迁移。
* 首轮只替换数据来源与业务行为，不重写整页样式。
* 页面优先级按“主业务闭环优先”排序。
* 在真实 API 接入前，禁止继续扩散新的 `localStorage` 业务状态。

### 1.3 首轮暂不改造的页面范围

以下能力不进入当前主链路，不单独建页面：

* `favorites.html`
* 第三方支付结果页
* 收藏夹、优惠券、复杂营销活动页
* 长篇文化专题独立站点式页面

---

## 2. 页面级映射

## 2.1 `front/index.html`

页面定位：

* 首页
* 展示轮播、节令专题、精选商品、推荐位、导航入口

首轮要接入的接口：

* `GET /api/v1/categories`
* `GET /api/v1/products`
* `GET /api/v1/products/recommendations`
* `GET /api/v1/search/suggestions`
* `GET /api/v1/member/profile`：仅登录态下用于首页会员推荐区或会员价展示

依赖实体：

* `category`
* `product`
* `product_media`
* `inventory`
* `user_interest_profile`
* `recommendation_log`

当前假数据来源：

* 首页轮播和分类入口是静态写死
* 节令专题商品链接是写死的 `product.html?id=4`、`product.html?id=8`
* 精选商品卡片是静态 HTML
* 推荐区当前不是接口驱动

首轮处理方式：

* 轮播文案可暂时保留静态
* 分类入口和精选商品改为真实类目与商品接口
* 推荐位改为真实推荐接口
* 节令专题先允许“静态壳 + 动态商品数据”的折中实现

优先级：

* 高

---

## 2.2 `front/category.html`

页面定位：

* 分类页
* 展示商品筛选、排序、分页和搜索结果收敛

首轮要接入的接口：

* `GET /api/v1/categories`
* `GET /api/v1/products`
* `GET /api/v1/search`
* `GET /api/v1/products/recommendations`：可用于分类页底部“为你推荐”

依赖实体：

* `category`
* `product`
* `product_media`
* `inventory`
* `product_tag`

当前假数据来源：

* 商品卡片列表写死在 HTML
* 页面内联 `categories` 对象生成分类标题和描述
* 分类、价格、排序都仅对当前 DOM 做前端过滤

首轮处理方式：

* 分类标题和描述改为后端类目数据
* 商品列表改为真实商品列表接口
* 价格筛选、排序、分类切换改为服务端查询参数
* DOM 本地过滤逻辑后续删除

优先级：

* 高

---

## 2.3 `front/product.html`

页面定位：

* 商品详情页
* 展示商品信息、图片、文化背景、规格、评价、相关商品

首轮要接入的接口：

* `GET /api/v1/products/{id}`
* `GET /api/v1/products/{id}/reviews`
* `GET /api/v1/products/{id}/related`
* `GET /api/v1/articles/{id}` 或 `GET /api/v1/products/{id}/related-content`
* `POST /api/v1/cart/items`
* `GET /api/v1/member/profile`

依赖实体：

* `product`
* `product_sku`
* `product_media`
* `inventory`
* `review`
* `review_image`
* `product_embedding`
* `culture_article`
* `product_culture_relation`

当前假数据来源：

* 页面内联 `productData`
* 相关推荐从 `productData` 推导
* 评价头像使用外部占位服务
* 加入购物车直接写 `localStorage`

首轮处理方式：

* 全量移除页面内联 `productData`
* 商品详情、评价、相关推荐全部改为真实接口
* 文化背景首轮允许直接来自商品字段 `culture_summary`
* 加购动作走真实购物车接口

优先级：

* 高

---

## 2.4 `front/cart.html`

页面定位：

* 购物车页
* 展示购物车条目、数量更新、删除、汇总金额和去结算入口

首轮要接入的接口：

* `GET /api/v1/cart`
* `POST /api/v1/cart/items`
* `PUT /api/v1/cart/items/{id}`
* `DELETE /api/v1/cart/items/{id}`

依赖实体：

* `cart`
* `cart_item`
* `product`
* `product_sku`
* `inventory`

当前假数据来源：

* 页面内联脚本直接读取 `shiyige_cart`
* `front/js/cart.js` 也在维护另一套购物车逻辑
* 金额汇总完全由前端本地计算

首轮处理方式：

* 购物车页只保留一个数据源：真实购物车接口
* 页面内联购物车脚本删除
* 统一让共享购物车脚本或新 API 模块接管购物车行为

优先级：

* 高

---

## 2.5 `front/checkout.html`

页面定位：

* 结算页
* 展示地址、订单金额、支付方式、会员优惠和提交订单

首轮要接入的接口：

* `GET /api/v1/cart`
* `GET /api/v1/users/addresses`
* `POST /api/v1/users/addresses`
* `GET /api/v1/member/profile`
* `POST /api/v1/orders`
* `POST /api/v1/orders/{id}/pay`
* `GET /api/v1/orders/{id}`

依赖实体：

* `user_address`
* `cart`
* `cart_item`
* `orders`
* `order_item`
* `payment_record`
* `point_account`
* `member_level`

当前假数据来源：

* 从 `localStorage` 读取购物车
* 本地生成订单号
* 本地生成 `shiyige_orders`
* 本地直接扣会员余额并加积分

首轮处理方式：

* 地址、购物车、会员信息、订单、支付全部后端化
* 页面只负责收集表单和展示结果
* 余额支付是否保留，由后端会员账户决定

优先级：

* 高

---

## 2.6 `front/login.html`

页面定位：

* 登录页

首轮要接入的接口：

* `POST /api/v1/auth/login`
* `POST /api/v1/auth/refresh`
* `POST /api/v1/auth/logout`

依赖实体：

* `users`
* `user_profile`

当前假数据来源：

* 表单验证成功后模拟登录
* 直接写入 `shiyige_user`
* “第三方登录”也是本地构造用户对象

首轮处理方式：

* 邮箱密码登录改为真实登录接口
* 第三方登录按钮首轮降级为占位提示，避免伪造登录成功
* 会话统一由 `front/js/session.js` 管理

优先级：

* 高

---

## 2.7 `front/register.html`

页面定位：

* 注册页

首轮要接入的接口：

* `POST /api/v1/auth/register`
* `POST /api/v1/auth/login`：可选，用于注册后自动登录

依赖实体：

* `users`
* `user_profile`

当前假数据来源：

* 表单验证成功后模拟注册
* 直接写入 `shiyige_user`
* “第三方注册”也是本地构造用户对象

首轮处理方式：

* 注册改为真实接口
* 第三方注册按钮首轮降级为占位提示
* 注册成功后是否自动登录由统一会话模块处理

优先级：

* 高

---

## 2.8 `front/profile.html`

页面定位：

* 个人中心
* 展示用户资料、修改资料、修改密码

首轮要接入的接口：

* `GET /api/v1/users/me`
* `PUT /api/v1/users/me`
* `PUT /api/v1/users/password`
* `GET /api/v1/users/addresses`

依赖实体：

* `users`
* `user_profile`
* `user_address`

当前假数据来源：

* 页面提交后把资料保存回 `localStorage`
* 左侧菜单包含缺失页 `orders.html` 与 `favorites.html`

首轮处理方式：

* 用户资料全部改为真实接口
* 保留 `orders.html` 入口，因为它属于主链路页面
* 移除或隐藏 `favorites.html` 入口

优先级：

* 高

---

## 2.9 `front/membership.html`

页面定位：

* 会员中心
* 展示等级、权益、余额、充值和积分记录

首轮要接入的接口：

* `GET /api/v1/member/profile`
* `GET /api/v1/member/points`
* `GET /api/v1/member/benefits`
* `POST /api/v1/member/recharge`：如果首轮保留充值演示能力

依赖实体：

* `member_level`
* `point_account`
* `point_log`

当前假数据来源：

* 全部会员信息来自 `front/js/membership.js` 的本地规则和 `shiyige_membership`
* 充值行为直接修改本地余额和积分

首轮处理方式：

* 会员等级、积分和余额统一后端化
* 若工期紧，充值可保留为后台脚本种子能力，不在首轮前台开放真实充值

优先级：

* 中

---

## 2.10 `front/orders.html`

页面定位：

* 订单列表页
* 当前文件尚不存在，但属于主业务闭环必须页面

首轮要接入的接口：

* `GET /api/v1/orders`
* `GET /api/v1/orders/{id}`
* `POST /api/v1/orders/{id}/pay`
* `POST /api/v1/orders/{id}/cancel`

依赖实体：

* `orders`
* `order_item`
* `payment_record`

当前假数据来源：

* 当前无页面，属于缺失能力

首轮处理方式：

* 先做最小可用占位页
* 在交易闭环阶段升级为真实订单页

优先级：

* 高

---

## 3. 共享脚本与未来接口归属

### 3.1 `front/js/auth.js`

未来负责：

* 导航登录态渲染
* 统一退出登录
* 页面鉴权守卫

未来依赖接口：

* `POST /api/v1/auth/logout`
* `GET /api/v1/users/me`

当前需要替换：

* 对 `shiyige_user` 的直接依赖

---

### 3.2 `front/js/cart.js`

未来负责：

* 商品卡片加购
* 购物车角标刷新
* 购物车通用操作入口

未来依赖接口：

* `GET /api/v1/cart`
* `POST /api/v1/cart/items`
* `PUT /api/v1/cart/items/{id}`
* `DELETE /api/v1/cart/items/{id}`

当前需要替换：

* 对 `shiyige_cart`、`shiyige_cart_summary` 的直接读写
* 与 `front/cart.html` 内联脚本的重复职责

---

### 3.3 `front/js/checkout.js`

未来负责：

* 结算页表单收集
* 调用订单创建与支付接口
* 展示金额结果和支付结果

未来依赖接口：

* `GET /api/v1/cart`
* `GET /api/v1/users/addresses`
* `GET /api/v1/member/profile`
* `POST /api/v1/orders`
* `POST /api/v1/orders/{id}/pay`

当前需要替换：

* 本地生成订单和本地更新会员数据

---

### 3.4 `front/js/membership.js`

未来负责：

* 会员中心 UI 渲染辅助
* 格式化会员信息

未来依赖接口：

* `GET /api/v1/member/profile`
* `GET /api/v1/member/points`
* `GET /api/v1/member/benefits`

当前需要替换：

* 本地会员等级常量作为事实来源
* 对 `shiyige_membership` 的直接读写

---

### 3.5 新增脚本规划

后续必须新增：

* `front/js/api.js`：统一请求封装
* `front/js/session.js`：统一 access token、刷新逻辑和 401 处理

它们将成为所有页面的 API 入口，不允许页面继续各自直连业务状态。

---

## 4. 首轮改造优先顺序

按业务闭环，优先顺序如下：

1. `front/login.html`
2. `front/register.html`
3. `front/profile.html`
4. `front/index.html`
5. `front/category.html`
6. `front/product.html`
7. `front/cart.html`
8. `front/checkout.html`
9. `front/orders.html`
10. `front/membership.html`

原因：

* 先认证
* 再浏览商品
* 再交易闭环
* 最后补会员展示

---

## 5. 当前明确暂不改造的页面或能力

本阶段先不单独实现：

* `favorites.html`
* 收藏相关接口
* 第三方 OAuth 登录
* 复杂营销页
* 长篇文化专题独立页面

原因：

* 不影响当前比赛版主链路
* 会分散后端闭环和推荐系统的工期

---

## 6. 本文档的执行用途

后续开发者在推进任意页面改造前，应先查看本文件，确认：

* 这个页面应该接哪些 `/api/v1` 接口
* 依赖哪些实体
* 当前假数据藏在哪个文件
* 该页面是否属于首轮主链路

如果页面不在本矩阵中，默认视为：

* 还没有进入首轮实施范围；
* 不应优先于主链路页面开发。
