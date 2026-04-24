/* 拾遗阁后台管理脚本 */

(function () {
  const ACCESS_TOKEN_KEY = "shiyige_admin_access_token";
  const NAV_LINKS = [
    { page: "dashboard", href: "index.html", label: "仪表盘" },
    { page: "products", href: "products.html", label: "商品管理" },
    { page: "orders", href: "orders.html", label: "订单管理" },
    { page: "recommendation-debug", href: "recommendation-debug.html", label: "推荐调试" },
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

  function formatScore(value, digits = 6) {
    const score = Number(value);
    if (Number.isNaN(score)) {
      return "-";
    }
    return score.toFixed(digits);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderTagList(values) {
    if (!Array.isArray(values) || values.length === 0) {
      return '<span class="empty-state">-</span>';
    }

    return `
      <div class="admin-tag-list">
        ${values.map((value) => `<span class="admin-tag">${escapeHtml(value)}</span>`).join("")}
      </div>
    `;
  }

  function renderRecommendationDebug(snapshot) {
    const emptyState = document.getElementById("recommendation-debug-empty");
    const content = document.getElementById("recommendation-debug-content");
    const metrics = document.getElementById("debug-metrics");
    const userProfileGrid = document.getElementById("debug-user-profile-grid");
    const behaviorTableBody = document.getElementById("debug-behavior-table-body");
    const recommendationList = document.getElementById("debug-recommendation-list");

    if (!content || !metrics || !userProfileGrid || !behaviorTableBody || !recommendationList) {
      return;
    }

    if (emptyState) {
      emptyState.classList.add("d-none");
    }
    content.classList.remove("d-none");

    metrics.innerHTML = `
      <article class="metric-card">
        <span class="metric-label">向量模型</span>
        <div class="metric-value" style="font-size: 1.15rem">${escapeHtml(snapshot.provider.model_name)}</div>
      </article>
      <article class="metric-card">
        <span class="metric-label">已建索引商品</span>
        <div class="metric-value">${snapshot.metrics.indexed_products}</div>
      </article>
      <article class="metric-card">
        <span class="metric-label">用户行为数</span>
        <div class="metric-value">${snapshot.profile.behavior_count}</div>
      </article>
      <article class="metric-card">
        <span class="metric-label">候选商品数</span>
        <div class="metric-value">${snapshot.metrics.candidate_count}</div>
      </article>
      <article class="metric-card">
        <span class="metric-label">向量维度</span>
        <div class="metric-value">${snapshot.profile.vector_dimension}</div>
      </article>
    `;

    const providerSource = [
      `provider=${snapshot.provider.provider}`,
      `source=${snapshot.provider.source}`,
      `revision=${snapshot.provider.revision}`,
      `device=${snapshot.provider.device}`,
      `normalize=${snapshot.provider.normalize}`,
    ].join("\n");

    const consumedProducts = (snapshot.profile.consumed_products || []).map((item) => item.name);

    userProfileGrid.innerHTML = `
      <article class="admin-metadata-card">
        <h3>用户摘要</h3>
        <div class="admin-kv-grid">
          <div class="admin-kv-item">
            <strong>用户邮箱</strong>
            <span>${escapeHtml(snapshot.user.email)}</span>
          </div>
          <div class="admin-kv-item">
            <strong>用户名</strong>
            <span>${escapeHtml(snapshot.user.username)}</span>
          </div>
          <div class="admin-kv-item">
            <strong>展示名</strong>
            <span>${escapeHtml(snapshot.user.display_name || "-")}</span>
          </div>
          <div class="admin-kv-item">
            <strong>最近事件时间</strong>
            <span>${escapeHtml(formatDateTime(snapshot.profile.last_event_at))}</span>
          </div>
          <div class="admin-kv-item">
            <strong>画像重建时间</strong>
            <span>${escapeHtml(formatDateTime(snapshot.profile.last_built_at))}</span>
          </div>
          <div class="admin-kv-item">
            <strong>画像内容哈希</strong>
            <span>${escapeHtml(snapshot.profile.content_hash || "-")}</span>
          </div>
        </div>
        <div class="debug-card-section">
          <strong>模型说明</strong>
          <pre class="admin-code-block">${escapeHtml(providerSource)}</pre>
        </div>
      </article>
      <article class="admin-metadata-card">
        <h3>兴趣画像</h3>
        <div class="debug-card-section">
          <strong>Top Terms</strong>
          ${renderTagList(snapshot.profile.top_terms)}
        </div>
        <div class="debug-card-section">
          <strong>已消费/已排除商品</strong>
          ${renderTagList(consumedProducts)}
        </div>
        <div class="debug-card-section">
          <strong>画像向量预览</strong>
          <pre class="admin-code-block">${escapeHtml((snapshot.profile.vector_preview || []).join(", ") || "-")}</pre>
        </div>
        <div class="debug-card-section">
          <strong>画像文本</strong>
          <pre class="admin-code-block">${escapeHtml(snapshot.profile.profile_text || "-")}</pre>
        </div>
      </article>
    `;

    if (!snapshot.recent_behaviors || snapshot.recent_behaviors.length === 0) {
      behaviorTableBody.innerHTML = `
        <tr>
          <td colspan="4" class="empty-state">当前用户还没有可展示的行为日志。</td>
        </tr>
      `;
    } else {
      behaviorTableBody.innerHTML = snapshot.recent_behaviors.map((item) => {
        const subject = item.query || item.product_names.join(" / ") || "-";
        return `
          <tr>
            <td>${escapeHtml(formatDateTime(item.created_at))}</td>
            <td><span class="admin-status">${escapeHtml(item.behavior_type)}</span></td>
            <td>
              <strong>${escapeHtml(subject)}</strong>
              <div><small>${escapeHtml(item.target_type || "-")}</small></div>
            </td>
            <td>
              <pre class="admin-code-block">${escapeHtml(JSON.stringify(item.ext_json || {}, null, 2))}</pre>
            </td>
          </tr>
        `;
      }).join("");
    }

    if (!snapshot.recommendations || snapshot.recommendations.length === 0) {
      recommendationList.innerHTML = '<div class="result-card">当前没有可展示的推荐候选。</div>';
      return;
    }

    recommendationList.innerHTML = snapshot.recommendations.map((item) => `
      <article class="debug-card">
        <div class="debug-card-header">
          <div>
            <p class="admin-eyebrow">Rank ${item.rank}</p>
            <h3>${escapeHtml(item.name)}</h3>
            <p class="page-copy">${escapeHtml(item.category || "未分类")} · ${escapeHtml(item.reason)}</p>
          </div>
          <span class="admin-status">总分 ${formatScore(item.score)}</span>
        </div>
        <div class="debug-card-section">
          <div class="admin-kv-grid">
            <div class="admin-kv-item">
              <strong>向量相似度</strong>
              <span>${formatScore(item.vector_similarity)}</span>
            </div>
            <div class="admin-kv-item">
              <strong>向量基础分</strong>
              <span>${formatScore(item.vector_score)}</span>
            </div>
            <div class="admin-kv-item">
              <strong>兴趣词加分</strong>
              <span>${formatScore(item.term_bonus)}</span>
            </div>
            <div class="admin-kv-item">
              <strong>向量维度</strong>
              <span>${item.embedding_dimension}</span>
            </div>
          </div>
        </div>
        <div class="debug-card-section">
          <strong>命中兴趣词</strong>
          ${renderTagList(item.matched_terms)}
        </div>
        <div class="debug-card-section">
          <strong>商品标签</strong>
          ${renderTagList(item.tags)}
        </div>
        <div class="debug-card-section">
          <strong>Embedding 文本片段</strong>
          <pre class="admin-code-block">${escapeHtml(item.embedding_text_preview || "-")}</pre>
        </div>
        <div class="debug-card-section">
          <strong>向量预览</strong>
          <pre class="admin-code-block">${escapeHtml((item.embedding_vector_preview || []).join(", ") || "-")}</pre>
        </div>
        <div class="debug-card-section">
          <strong>内容哈希</strong>
          <pre class="admin-code-block">${escapeHtml(item.content_hash || "-")}</pre>
        </div>
      </article>
    `).join("");
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

  function bindRecommendationDebugPage() {
    const form = document.getElementById("recommendation-debug-form");
    const emailInput = document.getElementById("debug-user-email");
    const limitInput = document.getElementById("debug-limit");
    const submitButton = document.getElementById("recommendation-debug-submit");
    if (!form || !emailInput || !limitInput || !submitButton) return;

    form.addEventListener("submit", async function (event) {
      event.preventDefault();

      const email = emailInput.value.trim().toLowerCase();
      const limit = limitInput.value.trim() || "5";
      if (!email) {
        showFlash("请输入要查询的前台用户邮箱。", "warning");
        return;
      }

      submitButton.disabled = true;
      submitButton.textContent = "加载中...";

      try {
        const params = new URLSearchParams({ email, limit });
        const payload = await request(`/api/v1/admin/recommendations/debug?${params.toString()}`);
        renderRecommendationDebug(payload.data);
        showFlash(`已加载 ${email} 的推荐调试信息。`, "success");
      } catch (error) {
        showFlash(error?.payload?.message || "推荐调试信息加载失败。", "danger");
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = "加载推荐证据";
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
      } else if (page === "recommendation-debug") {
        bindRecommendationDebugPage();
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
