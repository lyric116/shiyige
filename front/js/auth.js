/* 拾遗阁 - 全站认证与导航状态 */

(function () {
  let currentUser = null;

  function hasAccessToken() {
    return Boolean(window.shiyigeSession?.getAccessToken?.());
  }

  function isLoggedIn() {
    return hasAccessToken() || currentUser !== null;
  }

  function getCurrentUser() {
    return currentUser;
  }

  async function updateCartCount(user = currentUser) {
    const cartCount = document.getElementById("cart-count");
    if (!cartCount) {
      return;
    }

    if (!user || !window.shiyigeApi) {
      cartCount.classList.add("d-none");
      return;
    }

    try {
      const payload = await window.shiyigeApi.get("/cart");
      const totalQuantity = payload?.data?.cart?.total_quantity || 0;

      if (totalQuantity > 0) {
        cartCount.textContent = String(totalQuantity);
        cartCount.classList.remove("d-none");
      } else {
        cartCount.classList.add("d-none");
      }
    } catch {
      cartCount.classList.add("d-none");
    }
  }

  async function fetchCurrentUser(options = {}) {
    const { allowRefresh = true } = options;
    const session = window.shiyigeSession;
    const api = window.shiyigeApi;

    if (!session || !api) {
      currentUser = null;
      return null;
    }

    let accessToken = session.getAccessToken();
    if (!accessToken && allowRefresh) {
      try {
        accessToken = await session.refreshAccessToken();
      } catch {
        session.clearSession();
      }
    }

    if (!accessToken) {
      currentUser = null;
      return null;
    }

    try {
      const payload = await api.get("/users/me", { retryOn401: allowRefresh });
      currentUser = payload?.data?.user || null;
      return currentUser;
    } catch {
      currentUser = null;
      session.clearSession();
      return null;
    }
  }

  function renderGuestNavigation(userAuth) {
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

  function renderUserNavigation(userAuth, user) {
    const displayName = user.profile?.display_name || user.username;
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
          <span>${displayName}</span>
        </a>
        <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="userDropdown">
          <li><a class="dropdown-item" href="profile.html"><i class="fas fa-user me-2"></i><span>个人中心</span></a></li>
          <li><a class="dropdown-item" href="membership.html"><i class="fas fa-crown me-2"></i><span>会员中心</span></a></li>
          <li><a class="dropdown-item" href="orders.html"><i class="fas fa-shopping-bag me-2"></i><span>我的订单</span></a></li>
          <li><hr class="dropdown-divider"></li>
          <li><a class="dropdown-item" href="#" id="logout-btn"><i class="fas fa-sign-out-alt me-2"></i><span>退出登录</span></a></li>
        </ul>
      </li>
    `;

    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function (event) {
        event.preventDefault();
        void logout();
      });
    }
  }

  async function updateNavigation() {
    const navbarNav = document.getElementById("navbarNav");
    if (!navbarNav) return;

    const userAuth = navbarNav.querySelector(".navbar-nav:last-child");
    if (!userAuth) return;

    const user = await fetchCurrentUser({ allowRefresh: true });
    if (user) {
      renderUserNavigation(userAuth, user);
    } else {
      renderGuestNavigation(userAuth);
    }

    await updateCartCount(user);
  }

  async function logout() {
    try {
      await window.shiyigeApi?.post("/auth/logout", undefined, { retryOn401: false });
    } catch {
      // Logout should still clear the local session if the backend request fails.
    }

    window.shiyigeSession?.clearSession?.();
    currentUser = null;
    if (typeof showNotification === "function") {
      showNotification("已成功退出登录", "success");
    }

    await updateNavigation();

    const restrictedPages = ["profile.html", "orders.html"];
    const currentPage = window.location.pathname.split("/").pop();
    if (restrictedPages.includes(currentPage)) {
      window.location.href = "login.html";
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    void updateNavigation();
  });

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      void updateNavigation();
    }
  });

  window.isLoggedIn = isLoggedIn;
  window.getCurrentUser = getCurrentUser;
  window.updateNavigation = updateNavigation;
  window.logout = logout;
  window.shiyigeAuth = {
    fetchCurrentUser,
    getCurrentUser,
    isLoggedIn,
    logout,
    updateNavigation,
  };
})();
