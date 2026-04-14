# 当前仓库现状盘点

## 1. 盘点范围

本盘点基于当前仓库中的以下内容：

* `memory-bank/design.md`
* `front/*.html`
* `front/js/*.js`
* `front/css/*.css`
* `front/images/**`

当前仓库的可运行部分本质上还是一个**静态前端展示层**，尚未具备真实后端业务闭环。

---

## 2. 已存在页面

当前 `front/` 下已经存在的核心页面如下：

* `index.html`：首页，包含轮播、节令专题、推荐位和导航。
* `category.html`：分类页，包含侧边栏筛选、排序和商品卡片列表。
* `product.html`：商品详情页，包含主图、缩略图、文化背景、规格、评价、相关推荐。
* `cart.html`：购物车页，包含列表、勾选、数量修改、汇总金额。
* `checkout.html`：结算页，包含收货信息、支付方式、会员优惠和下单动作。
* `login.html`：登录页，包含邮箱密码登录和第三方登录按钮。
* `register.html`：注册页，包含邮箱注册和第三方注册按钮。
* `profile.html`：个人中心，包含资料维护与密码修改入口。
* `membership.html`：会员中心，包含会员等级、充值入口、积分记录区域。

辅助脚本模块如下：

* `front/js/main.js`：全站通用脚本，如时钟、导航高亮、图片错误兜底、滚动动画。
* `front/js/auth.js`：导航登录态与退出逻辑。
* `front/js/cart.js`：加购、购物车数量、购物车汇总。
* `front/js/checkout.js`：结算、金额计算、下单流程。
* `front/js/product.js`：详情页交互、放大镜、缩略图、更多评价。
* `front/js/membership.js`：会员等级、余额、积分和充值规则。
* `front/js/search.js`：搜索框交互。
* `front/js/promotion.js`：满减和促销规则。
* `front/js/validation.js`：表单校验。
* `front/js/carousel.js`：轮播增强逻辑。
* `front/js/petals.js`：花瓣背景动效。

---

## 3. `localStorage` 使用点

当前前端把多类核心业务数据直接保存在 `localStorage` 中，尚未接入真实后端：

### 3.1 用户登录态

* `front/login.html`：模拟登录后写入 `shiyige_user`
* `front/register.html`：模拟注册后写入 `shiyige_user`
* `front/profile.html`：保存个人资料时写入 `shiyige_user`
* `front/js/auth.js`：从 `localStorage` 读取 `shiyige_user`、退出时删除 `shiyige_user`

### 3.2 购物车数据

* `front/product.html`：加入购物车时写入 `shiyige_cart`
* `front/cart.html`：加载、修改、删除购物车时读写 `shiyige_cart`
* `front/js/cart.js`：加购、购物车角标、购物车汇总时读写 `shiyige_cart`

### 3.3 订单与结算数据

* `front/js/checkout.js`：读取 `shiyige_cart`，创建本地 `shiyige_orders`，提交后清空购物车
* `front/checkout.html`：页面初始化依赖 `localStorage` 购物车数据

### 3.4 会员与积分数据

* `front/js/membership.js`：把会员余额、积分、消费总额存在 `shiyige_membership`
* `front/js/checkout.js`：结算时直接修改 `shiyige_membership`
* `front/js/cart.js`：把购物车汇总信息存入 `shiyige_cart_summary`

结论：

* 当前不仅认证态在 `localStorage` 中；
* 购物车、订单、会员、积分等业务数据也在 `localStorage` 中；
* 这与设计文档要求的真实后端闭环存在直接冲突。

---

## 4. 缺失页面与死链

当前前端存在被引用但缺失的页面：

* `orders.html`：被 `front/js/auth.js` 和 `front/profile.html` 引用，但文件不存在。
* `favorites.html`：被 `front/js/auth.js` 和 `front/profile.html` 引用，但文件不存在。

这意味着当前导航和个人中心存在明显死链，用户点击后会直接失败。

---

## 5. 假数据与硬编码来源

当前前端除了 `localStorage` 以外，还存在大量硬编码假数据来源：

### 5.1 商品与分类数据硬编码

* `front/category.html`：商品卡片列表直接写死在 HTML 中；分类标题与描述由页面内联 `categories` 对象生成。
* `front/product.html`：页面内联 `productData` 对象，包含 12 个商品的名称、价格、库存、文化说明、图片。
* `front/index.html`：轮播、节令专题、精选商品、分类入口均为静态内容。

### 5.2 模拟业务动作

* `front/login.html`：模拟登录成功。
* `front/register.html`：模拟注册成功。
* `front/js/checkout.js`：本地生成订单号、模拟支付成功、直接改会员余额和积分。
* `front/js/product.js`：模拟“加载更多评价”。

### 5.3 外部占位资源

* `front/product.html` 和 `front/js/product.js` 使用 `ui-avatars.com` 生成用户头像，占位性质明显。

### 5.4 API 实际缺位

当前前端基本没有真实业务 API 调用：

* 全仓库没有 `/api/v1` 的真实接入。
* 业务层几乎没有真正的 `fetch` 请求，只有 `front/js/cart.js` 中保留了一个与当前静态结构并不匹配的 `fetch(form.action, ...)` 片段。

结论：

* 当前仓库的商品、用户、购物车、订单、会员、评价，都是“静态内容 + 浏览器本地状态”的组合；
* 还没有形成数据库、接口、状态流转和权限控制。

---

## 6. 与设计文档的主要差距

相对于 `memory-bank/design.md` 的目标，当前至少存在以下差距：

### 6.1 后端和基础设施缺失

* 没有 `backend/`
* 没有 FastAPI 服务
* 没有 PostgreSQL / pgvector
* 没有 Redis
* 没有 MinIO
* 没有 Docker Compose 编排

### 6.2 核心业务闭环缺失

* 没有真实注册登录接口
* 没有真实商品列表与商品详情接口
* 没有真实购物车、订单、支付接口
* 没有真实会员积分结算逻辑
* 没有真实评价接口

### 6.3 推荐与搜索能力缺失

* 没有向量表
* 没有 embedding 生成链路
* 没有语义搜索接口
* 没有相似商品推荐接口
* 没有用户兴趣画像

### 6.4 后台与运营能力缺失

* 没有管理员体系
* 没有商品管理后台
* 没有订单管理后台
* 没有推荐重建任务页
* 没有运营分析与日志查看入口

### 6.5 测试与部署能力缺失

* 没有 `backend/tests/`
* 没有 `tests/e2e/`
* 没有迁移系统
* 没有部署说明
* 没有自动化回归验证入口

---

## 7. 当前前端可复用资产

虽然业务层还是假数据，但以下资产可以直接复用，不必推倒重来：

* 古风视觉风格已经基本成型。
* `index.html`、`category.html`、`product.html`、`cart.html`、`checkout.html`、`login.html`、`register.html`、`profile.html`、`membership.html` 的页面框架已经具备。
* 分类图片、商品图片、Logo、背景素材已经齐备。
* 常见电商流程页面已经出现，可作为比赛演示层基础。

因此正确路线不是重写前端，而是：

* 保留现有 `front/` 页面结构；
* 逐步移除 `localStorage` 伪业务逻辑；
* 用真实 `/api/v1` 接口替换硬编码数据和本地状态。

---

## 8. 第 1 步结论

当前仓库可以被定义为：

**“视觉层较完整，但业务层仍是静态模拟的古风文化商品网站前端原型。”**

在进入下一步之前，已经明确记录了至少以下三类问题：

* `localStorage` 承担了认证、购物车、订单、会员等不应由前端本地保存的业务状态。
* `orders.html` 与 `favorites.html` 存在缺页和死链。
* 商品、分类、评价和订单逻辑大量硬编码在 `index.html`、`category.html`、`product.html`、`cart.html`、`checkout.html` 与多个脚本中。
* 当前没有真实后端、数据库、推荐系统、后台和测试体系。
