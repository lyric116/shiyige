/**
 * 用户身份验证与管理相关功能
 */

// 检查用户是否已登录
function isLoggedIn() {
  const user = JSON.parse(localStorage.getItem("shiyige_user") || "null");
  return user && user.isLoggedIn;
}

// 获取当前登录用户信息
function getCurrentUser() {
  return JSON.parse(localStorage.getItem("shiyige_user") || "null");
}

// 更新导航栏以反映登录状态
function updateNavigation() {
  const navbarNav = document.getElementById("navbarNav");
  if (!navbarNav) return;

  const userAuth = navbarNav.querySelector(".navbar-nav:last-child");
  if (!userAuth) return;

  if (isLoggedIn()) {
    const user = getCurrentUser();
    userAuth.innerHTML = `
      <li class="nav-item">
        <a class="nav-link position-relative cart-link" href="cart.html">
          <i class="fas fa-shopping-cart"></i>
          <span>购物车</span>
          <span id="cart-count" class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger d-none">
            0
          </span>
        </a>
      </li>
      <li class="nav-item dropdown">
        <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" 
           data-bs-toggle="dropdown" aria-expanded="false">
          <i class="fas fa-user-circle"></i>
          <span>${user.username}</span>
        </a>
        <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="userDropdown">
          <li><a class="dropdown-item" href="profile.html"><i class="fas fa-user me-2"></i><span>个人中心</span></a></li>
          <li><a class="dropdown-item" href="membership.html"><i class="fas fa-crown me-2"></i><span>会员中心</span></a></li>
          <li><a class="dropdown-item" href="orders.html"><i class="fas fa-shopping-bag me-2"></i><span>我的订单</span></a></li>
          <li><a class="dropdown-item" href="favorites.html"><i class="fas fa-heart me-2"></i><span>我的收藏</span></a></li>
          <li><hr class="dropdown-divider"></li>
          <li><a class="dropdown-item" href="#" id="logout-btn"><i class="fas fa-sign-out-alt me-2"></i><span>退出登录</span></a></li>
        </ul>
      </li>
    `;

    // 添加退出登录功能
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function (e) {
        e.preventDefault();
        logout();
      });
    }
  } else {
    // 用户未登录，显示默认导航
    userAuth.innerHTML = `
      <li class="nav-item">
        <a class="nav-link position-relative cart-link" href="cart.html">
          <i class="fas fa-shopping-cart"></i>
          <span>购物车</span>
          <span id="cart-count" class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger d-none">
            0
          </span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="login.html"><span>登录</span></a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="register.html"><span>注册</span></a>
      </li>
    `;
  }

  // 更新购物车计数
  updateCartCount();
}

// 更新购物车计数
function updateCartCount() {
  const cart = JSON.parse(localStorage.getItem("shiyige_cart") || "[]");
  const cartCount = document.getElementById("cart-count");

  if (cartCount) {
    if (cart.length > 0) {
      cartCount.textContent = cart.length;
      cartCount.classList.remove("d-none");
    } else {
      cartCount.classList.add("d-none");
    }
  }
}

// 退出登录
function logout() {
  // 清除用户登录状态
  localStorage.removeItem("shiyige_user");

  // 显示退出成功消息
  showNotification("已成功退出登录", "success");

  // 更新导航栏
  updateNavigation();

  // 如果在需要登录的页面，重定向到首页
  const restrictedPages = ["profile.html", "orders.html", "favorites.html"];
  const currentPage = window.location.pathname.split("/").pop();

  if (restrictedPages.includes(currentPage)) {
    window.location.href = "index.html";
  }
}

// 显示通知消息
function showNotification(message, type = "info") {
  const flashMessages = document.getElementById("flash-messages");
  if (!flashMessages) return;

  const alertDiv = document.createElement("div");
  alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
  alertDiv.role = "alert";

  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="关闭"></button>
  `;

  flashMessages.appendChild(alertDiv);

  // 3秒后自动消失
  setTimeout(() => {
    alertDiv.remove();
  }, 3000);
}

// 初始化 - 在页面加载时调用
document.addEventListener("DOMContentLoaded", function () {
  // 每当页面加载时更新导航栏
  updateNavigation();
});

// 添加页面可见性变化监听，以在用户切换标签页时更新登录状态
document.addEventListener("visibilitychange", function () {
  if (document.visibilityState === "visible") {
    updateNavigation();
  }
});
