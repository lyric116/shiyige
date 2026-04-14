/* 拾遗阁后台管理脚本 */

(function () {
  const ACCESS_TOKEN_KEY = "shiyige_admin_access_token";
  const NAV_LINKS = [
    { page: "dashboard", href: "index.html", label: "仪表盘" },
    { page: "products", href: "products.html", label: "商品管理" },
    { page: "orders", href: "orders.html", label: "订单管理" },
    { page: "reindex", href: "reindex.html", label: "推荐重建" },
  ];

  function getToken() {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY);
  }

  function setToken(token) {
    if (!token) return;
    sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
  }

  function clearToken() {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  }

  function formatMoney(value) {
    const amount = Number(value);
    if (Number.isNaN(amount)) {
      return "-";
    }

    return new Intl.NumberFormat("zh-CN", {
      style: "currency",
      currency: "CNY",
    }).format(amount);
  }

  function formatDateTime(value) {
    if (!value) {
      return "-";
    }

    return String(value).replace("T", " ").slice(0, 16);
  }

  function showFlash(message, type = "info") {
    const flashContainer = document.getElementById("admin-flash");
    if (!flashContainer) return;

    flashContainer.innerHTML = `
      <div class="alert alert-${type}" role="alert">
        ${message}
      </div>
    `;
  }

  async function request(path, options = {}) {
    const {
      method = "GET",
      body,
      headers = {},
    } = options;

    const requestHeaders = new Headers(headers);
    if (body !== undefined && !requestHeaders.has("Content-Type")) {
      requestHeaders.set("Content-Type", "application/json");
    }

    const accessToken = getToken();
    if (accessToken && !requestHeaders.has("Authorization")) {
      requestHeaders.set("Authorization", `Bearer ${accessToken}`);
    }

    const response = await fetch(path, {
      method,
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "include",
    });
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const error = new Error(payload?.message || `Request failed with status ${response.status}`);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  function redirectToLogin() {
    clearToken();
    window.location.href = "login.html";
  }

  function renderNav(currentPage) {
    const navContainer = document.getElementById("admin-nav");
    if (!navContainer) return;

    navContainer.innerHTML = NAV_LINKS.map((link) => {
      const activeClass = link.page === currentPage ? " active" : "";
      return `
        <a class="admin-nav-link${activeClass}" href="${link.href}">
          ${link.label}
        </a>
      `;
    }).join("");
  }

  function fillAdminProfile(admin) {
    const identity = document.getElementById("admin-email-display");
    const role = document.getElementById("admin-role-display");

    if (identity) {
      identity.textContent = admin.email;
    }

    if (role) {
      role.textContent = admin.role === "super_admin" ? "超级管理员" : "运营管理员";
    }
  }

  async function fetchCurrentAdmin() {
    const payload = await request("/api/v1/admin/auth/me");
    return payload.data.admin;
  }

  function bindLogout() {
    document.getElementById("logout-button")?.addEventListener("click", async function () {
      try {
        await request("/api/v1/admin/auth/logout", { method: "POST" });
      } catch (error) {
        // Ignore logout response failures; local session should still be cleared.
      }
      redirectToLogin();
    });
  }

  function renderDashboard(summary) {
    document.getElementById("summary-users").textContent = String(summary.users_total);
    document.getElementById("summary-products").textContent = String(summary.products_total);
    document.getElementById("summary-orders").textContent = String(summary.orders_total);
    document.getElementById("summary-paid-orders").textContent = String(summary.paid_orders);
    document.getElementById("summary-pending-orders").textContent = String(summary.pending_orders);
  }

  function renderProducts(products) {
    const tableBody = document.getElementById("products-table-body");
    if (!tableBody) return;

    if (products.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-state">当前没有可展示的商品。</td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = products.map((product) => `
      <tr>
        <td>
          <strong>${product.name}</strong>
          <div><small>${product.subtitle || "暂无副标题"}</small></div>
        </td>
        <td>${product.category.name}</td>
        <td>${formatMoney(product.default_sku?.price)}</td>
        <td>${product.default_sku?.inventory ?? 0}</td>
        <td>
          <span class="admin-status">${product.status === 1 ? "上架中" : "已下架"}</span>
        </td>
        <td>${(product.tags || []).join(" / ") || "-"}</td>
      </tr>
    `).join("");
  }

  function renderOrders(orders) {
    const tableBody = document.getElementById("orders-table-body");
    if (!tableBody) return;

    if (orders.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-state">当前没有订单记录。</td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = orders.map((order) => `
      <tr>
        <td>${order.order_no}</td>
        <td>
          <strong>${order.user.username}</strong>
          <div><small>${order.user.email}</small></div>
        </td>
        <td><span class="admin-status">${order.status}</span></td>
        <td>${formatMoney(order.payable_amount)}</td>
        <td>${order.items.length}</td>
        <td>${formatDateTime(order.created_at)}</td>
      </tr>
    `).join("");
  }

  async function loadDashboard() {
    const payload = await request("/api/v1/admin/dashboard/summary");
    renderDashboard(payload.data);
  }

  async function loadProducts() {
    const payload = await request("/api/v1/admin/products?page=1&page_size=20");
    renderProducts(payload.data.items || []);
  }

  async function loadOrders() {
    const payload = await request("/api/v1/admin/orders?page=1&page_size=20");
    renderOrders(payload.data.items || []);
  }

  function renderReindexResult(result) {
    const resultContainer = document.getElementById("reindex-result");
    if (!resultContainer) return;

    resultContainer.innerHTML = `
      <div class="result-card">
        已完成 ${result.indexed} 条商品向量重建，跳过 ${result.skipped} 条，模型：${result.model_name}。
      </div>
    `;
  }

  function bindReindexAction() {
    const button = document.getElementById("reindex-products-btn");
    if (!button) return;

    button.addEventListener("click", async function () {
      button.disabled = true;
      button.textContent = "重建中...";

      try {
        const payload = await request("/api/v1/admin/reindex/products", {
          method: "POST",
          body: { force: true },
        });
        renderReindexResult(payload.data.result);
        showFlash("商品向量索引已完成重建。", "success");
      } catch (error) {
        showFlash(error?.payload?.message || "推荐重建失败，请稍后重试。", "danger");
      } finally {
        button.disabled = false;
        button.textContent = "立即重建商品向量";
      }
    });
  }

  async function handleLoginPage() {
    if (getToken()) {
      try {
        await fetchCurrentAdmin();
        window.location.href = "index.html";
        return;
      } catch (error) {
        clearToken();
      }
    }

    const loginForm = document.getElementById("admin-login-form");
    if (!loginForm) return;

    loginForm.addEventListener("submit", async function (event) {
      event.preventDefault();

      const email = document.getElementById("admin-email")?.value?.trim() || "";
      const password = document.getElementById("admin-password")?.value || "";
      const submitButton = loginForm.querySelector("button[type='submit']");

      if (!email || !password) {
        showFlash("请输入后台账号和密码。", "warning");
        return;
      }

      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "登录中...";
      }

      try {
        const payload = await request("/api/v1/admin/auth/login", {
          method: "POST",
          body: { email, password },
        });
        setToken(payload.data.access_token);
        window.location.href = "index.html";
      } catch (error) {
        showFlash(error?.payload?.message || "后台登录失败，请检查账号密码。", "danger");
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = "进入后台";
        }
      }
    });
  }

  async function bootProtectedPage(page) {
    renderNav(page);
    bindLogout();

    try {
      const admin = await fetchCurrentAdmin();
      fillAdminProfile(admin);
    } catch (error) {
      redirectToLogin();
      return;
    }

    try {
      if (page === "dashboard") {
        await loadDashboard();
      } else if (page === "products") {
        await loadProducts();
      } else if (page === "orders") {
        await loadOrders();
      } else if (page === "reindex") {
        bindReindexAction();
      }
    } catch (error) {
      if (error?.status === 401 || error?.status === 403) {
        redirectToLogin();
        return;
      }
      showFlash(error?.payload?.message || "后台页面数据加载失败。", "danger");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const currentPage = document.body.dataset.page || "";

    if (currentPage === "login") {
      void handleLoginPage();
      return;
    }

    void bootProtectedPage(currentPage);
  });
})();
