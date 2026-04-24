/* 拾遗阁后台管理脚本 */

(function () {
  const ACCESS_TOKEN_KEY = "shiyige_admin_access_token";
  let latestVectorStatus = null;
  const NAV_LINKS = [
    { page: "dashboard", href: "index.html", label: "仪表盘" },
    { page: "products", href: "products.html", label: "商品管理" },
    { page: "orders", href: "orders.html", label: "订单管理" },
    { page: "recommendation-debug", href: "recommendation-debug.html", label: "推荐调试" },
    { page: "reindex", href: "reindex.html", label: "索引状态" },
    { page: "recommendation-config", href: "recommendation-config.html", label: "实验配置" },
  ];

  function getToken() {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY);
  }

  function setToken(token) {
    if (!token) {
      return;
    }
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

  function formatPercent(value) {
    const amount = Number(value);
    if (Number.isNaN(amount)) {
      return "-";
    }
    return `${(amount * 100).toFixed(2)}%`;
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

  function showFlash(message, type = "info") {
    const flashContainer = document.getElementById("admin-flash");
    if (!flashContainer) {
      return;
    }

    flashContainer.innerHTML = `
      <div class="alert alert-${type}" role="alert">
        ${message}
      </div>
    `;
  }

  async function request(path, options = {}) {
    const { method = "GET", body, headers = {} } = options;
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
    if (!navContainer) {
      return;
    }

    navContainer.innerHTML = NAV_LINKS.map(function (link) {
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
        // Ignore logout failures and still clear local session.
      }
      redirectToLogin();
    });
  }

  function renderExperimentCards(items) {
    if (!Array.isArray(items) || items.length === 0) {
      return '<div class="result-card">当前没有可展示的实验配置。</div>';
    }

    return items
      .map(function (item) {
        return `
          <article class="debug-card">
            <div class="debug-card-header">
              <div>
                <p class="admin-eyebrow">${escapeHtml(item.strategy || "-")}</p>
                <h3>${escapeHtml(item.name || item.key)}</h3>
                <p class="page-copy">${escapeHtml(item.description || "暂无说明")}</p>
              </div>
              <span class="admin-status">${item.is_active ? "当前激活" : "备用方案"}</span>
            </div>
            <div class="debug-card-section">
              <div class="admin-kv-grid">
                <div class="admin-kv-item">
                  <strong>实验键</strong>
                  <span>${escapeHtml(item.key)}</span>
                </div>
                <div class="admin-kv-item">
                  <strong>Pipeline Version</strong>
                  <span>${escapeHtml(item.pipeline_version || "-")}</span>
                </div>
                <div class="admin-kv-item">
                  <strong>Model Version</strong>
                  <span>${escapeHtml(item.model_version || "-")}</span>
                </div>
                <div class="admin-kv-item">
                  <strong>最近更新时间</strong>
                  <span>${escapeHtml(formatDateTime(item.updated_at))}</span>
                </div>
              </div>
            </div>
            <div class="debug-card-section">
              <strong>启用能力</strong>
              ${renderTagList(item.capabilities || [])}
            </div>
            <div class="debug-card-section">
              <strong>配置摘要</strong>
              <pre class="admin-code-block">${escapeHtml(
                JSON.stringify(item.config_json || {}, null, 2)
              )}</pre>
            </div>
          </article>
        `;
      })
      .join("");
  }

  function renderDashboard(summary) {
    document.getElementById("summary-users").textContent = String(summary.users_total);
    document.getElementById("summary-products").textContent = String(summary.products_total);
    document.getElementById("summary-orders").textContent = String(summary.orders_total);
    document.getElementById("summary-paid-orders").textContent = String(summary.paid_orders);
    document.getElementById("summary-pending-orders").textContent = String(summary.pending_orders);

    const recommendationMetrics = summary.recommendation_metrics || {};
    const searchMetrics = summary.search_metrics || {};
    const vectorIndex = summary.vector_index || {};
    const runtime = summary.runtime || {};
    const experiments = summary.experiments || { items: [] };

    const recommendationKpis = document.getElementById("recommendation-kpis");
    if (recommendationKpis) {
      recommendationKpis.innerHTML = `
        <article class="metric-card">
          <span class="metric-label">CTR</span>
          <div class="metric-value">${formatPercent(recommendationMetrics.ctr)}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">加购率</span>
          <div class="metric-value">${formatPercent(recommendationMetrics.add_to_cart_rate)}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">转化率</span>
          <div class="metric-value">${formatPercent(recommendationMetrics.conversion_rate)}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">覆盖率</span>
          <div class="metric-value">${formatPercent(recommendationMetrics.coverage_rate)}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">平均延迟</span>
          <div class="metric-value">${formatScore(
            recommendationMetrics.average_latency_ms,
            1
          )} ms</div>
        </article>
      `;
    }

    const searchKpis = document.getElementById("search-kpis");
    if (searchKpis) {
      searchKpis.innerHTML = `
        <article class="metric-card">
          <span class="metric-label">搜索请求数</span>
          <div class="metric-value">${searchMetrics.request_count ?? 0}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">语义搜索数</span>
          <div class="metric-value">${searchMetrics.semantic_count ?? 0}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">关键词搜索数</span>
          <div class="metric-value">${searchMetrics.keyword_count ?? 0}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">搜索平均延迟</span>
          <div class="metric-value">${formatScore(searchMetrics.average_latency_ms, 1)} ms</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">Qdrant Point 数</span>
          <div class="metric-value">${vectorIndex.qdrant_point_count ?? 0}</div>
        </article>
      `;
    }

    const vectorStatus = document.getElementById("dashboard-vector-status");
    if (vectorStatus) {
      vectorStatus.innerHTML = `
        <article class="admin-metadata-card">
          <h3>向量索引概览</h3>
          <div class="admin-kv-grid">
            <div class="admin-kv-item">
              <strong>Qdrant 可用</strong>
              <span>${vectorIndex.qdrant_available ? "是" : "否"}</span>
            </div>
            <div class="admin-kv-item">
              <strong>Collection</strong>
              <span>${escapeHtml(vectorIndex.collection_name || "-")}</span>
            </div>
            <div class="admin-kv-item">
              <strong>已索引商品</strong>
              <span>${vectorIndex.indexed_product_count ?? 0}</span>
            </div>
            <div class="admin-kv-item">
              <strong>失败商品数</strong>
              <span>${vectorIndex.failed_count ?? 0}</span>
            </div>
          </div>
        </article>
        <article class="admin-metadata-card">
          <h3>当前运行时</h3>
          <div class="admin-kv-grid">
            <div class="admin-kv-item">
              <strong>搜索后端</strong>
              <span>${escapeHtml(runtime.active_search_backend || "-")}</span>
            </div>
            <div class="admin-kv-item">
              <strong>推荐后端</strong>
              <span>${escapeHtml(runtime.active_recommendation_backend || "-")}</span>
            </div>
            <div class="admin-kv-item">
              <strong>推荐版本</strong>
              <span>${escapeHtml(runtime.recommendation_pipeline_version || "-")}</span>
            </div>
            <div class="admin-kv-item">
              <strong>排序器</strong>
              <span>${escapeHtml(runtime.configured_recommendation_ranker || "-")}</span>
            </div>
          </div>
          <div class="debug-card-section">
            <strong>Collection 列表</strong>
            ${renderTagList(runtime.qdrant_collections || [])}
          </div>
        </article>
      `;
    }

    const activeExperiment = document.getElementById("dashboard-active-experiment");
    if (activeExperiment) {
      activeExperiment.textContent = `当前激活方案：${
        experiments.active_key || "unknown"
      }。如果 Qdrant 未就绪，系统会自动退回 baseline 方案。`;
    }

    const experimentList = document.getElementById("dashboard-experiment-list");
    if (experimentList) {
      experimentList.innerHTML = renderExperimentCards((experiments.items || []).slice(0, 4));
    }
  }

  function renderProducts(products) {
    const tableBody = document.getElementById("products-table-body");
    if (!tableBody) {
      return;
    }

    if (products.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-state">当前没有可展示的商品。</td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = products
      .map(function (product) {
        return `
          <tr>
            <td>
              <strong>${escapeHtml(product.name)}</strong>
              <div><small>${escapeHtml(product.subtitle || "暂无副标题")}</small></div>
            </td>
            <td>${escapeHtml(product.category.name)}</td>
            <td>${formatMoney(product.default_sku?.price)}</td>
            <td>${product.default_sku?.inventory ?? 0}</td>
            <td>
              <span class="admin-status">${product.status === 1 ? "上架中" : "已下架"}</span>
            </td>
            <td>${escapeHtml((product.tags || []).join(" / ") || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderOrders(orders) {
    const tableBody = document.getElementById("orders-table-body");
    if (!tableBody) {
      return;
    }

    if (orders.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-state">当前没有订单记录。</td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = orders
      .map(function (order) {
        return `
          <tr>
            <td>${escapeHtml(order.order_no)}</td>
            <td>
              <strong>${escapeHtml(order.user.username)}</strong>
              <div><small>${escapeHtml(order.user.email)}</small></div>
            </td>
            <td><span class="admin-status">${escapeHtml(order.status)}</span></td>
            <td>${formatMoney(order.payable_amount)}</td>
            <td>${order.items.length}</td>
            <td>${formatDateTime(order.created_at)}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderVectorStatus(status, runtime) {
    const metrics = document.getElementById("vector-status-metrics");
    const runtimeGrid = document.getElementById("vector-runtime-grid");
    const failedBody = document.getElementById("vector-failed-body");
    if (metrics) {
      metrics.innerHTML = `
        <article class="metric-card">
          <span class="metric-label">Qdrant 连接</span>
          <div class="metric-value">${status.qdrant_available ? "正常" : "异常"}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">Collection</span>
          <div class="metric-value">${escapeHtml(status.collection_name || "-")}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">活跃商品数</span>
          <div class="metric-value">${status.active_product_count ?? 0}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">已索引商品数</span>
          <div class="metric-value">${status.indexed_product_count ?? 0}</div>
        </article>
        <article class="metric-card">
          <span class="metric-label">失败商品数</span>
          <div class="metric-value">${status.failed_count ?? 0}</div>
        </article>
      `;
    }

    if (runtimeGrid) {
      runtimeGrid.innerHTML = `
        <article class="admin-metadata-card">
          <h3>运行时状态</h3>
          <div class="admin-kv-grid">
            <div class="admin-kv-item">
              <strong>搜索后端</strong>
              <span>${escapeHtml(runtime.active_search_backend || "-")}</span>
            </div>
            <div class="admin-kv-item">
              <strong>推荐后端</strong>
              <span>${escapeHtml(runtime.active_recommendation_backend || "-")}</span>
            </div>
            <div class="admin-kv-item">
              <strong>降级到 Baseline</strong>
              <span>${runtime.degraded_to_baseline ? "是" : "否"}</span>
            </div>
            <div class="admin-kv-item">
              <strong>排序器</strong>
              <span>${escapeHtml(runtime.configured_recommendation_ranker || "-")}</span>
            </div>
          </div>
        </article>
        <article class="admin-metadata-card">
          <h3>Collection 列表</h3>
          ${renderTagList(runtime.qdrant_collections || [])}
          <div class="debug-card-section">
            <strong>运行时说明</strong>
            <pre class="admin-code-block">${escapeHtml(
              JSON.stringify(runtime, null, 2)
            )}</pre>
          </div>
        </article>
      `;
    }

    if (failedBody) {
      const failedProducts = status.failed_products || [];
      if (!failedProducts.length) {
        failedBody.innerHTML = `
          <tr>
            <td colspan="3" class="empty-state">当前没有索引失败商品。</td>
          </tr>
        `;
        return;
      }

      failedBody.innerHTML = failedProducts
        .map(function (item) {
          return `
            <tr>
              <td>${item.product_id}</td>
              <td>${escapeHtml(item.error || "-")}</td>
              <td>${escapeHtml(formatDateTime(item.last_indexed_at))}</td>
            </tr>
          `;
        })
        .join("");
    }
  }

  function renderReindexResult(result) {
    const resultContainer = document.getElementById("reindex-result");
    if (!resultContainer) {
      return;
    }

    resultContainer.innerHTML = `
      <div class="result-card">
        模式：${escapeHtml(result.mode || "full")}；已索引 ${result.indexed ?? 0} 条，跳过 ${
      result.skipped ?? 0
    } 条，失败 ${result.failed ?? 0} 条。模型：${escapeHtml(
      result.dense_model_name || result.model_name || "-"
    )}。
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

    emptyState?.classList.add("d-none");
    content.classList.remove("d-none");

    metrics.innerHTML = `
      <article class="metric-card">
        <span class="metric-label">向量模型</span>
        <div class="metric-value" style="font-size: 1.15rem">${escapeHtml(
          snapshot.provider.model_name
        )}</div>
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
        <span class="metric-label">当前排序器</span>
        <div class="metric-value" style="font-size: 1.15rem">${escapeHtml(
          snapshot.metrics.active_ranker
        )}</div>
      </article>
    `;

    const providerSource = [
      `provider=${snapshot.provider.provider}`,
      `source=${snapshot.provider.source}`,
      `revision=${snapshot.provider.revision}`,
      `device=${snapshot.provider.device}`,
      `normalize=${snapshot.provider.normalize}`,
    ].join("\n");

    const consumedProducts = (snapshot.profile.consumed_products || []).map(function (item) {
      return item.name;
    });

    userProfileGrid.innerHTML = `
      <article class="admin-metadata-card">
        <h3>用户摘要</h3>
        <div class="admin-kv-grid">
          <div class="admin-kv-item">
            <strong>用户 ID</strong>
            <span>${snapshot.user.id}</span>
          </div>
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
          <strong>已消费商品</strong>
          ${renderTagList(consumedProducts)}
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
      behaviorTableBody.innerHTML = snapshot.recent_behaviors
        .map(function (item) {
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
                <pre class="admin-code-block">${escapeHtml(
                  JSON.stringify(item.ext_json || {}, null, 2)
                )}</pre>
              </td>
            </tr>
          `;
        })
        .join("");
    }

    if (!snapshot.recommendations || snapshot.recommendations.length === 0) {
      recommendationList.innerHTML = '<div class="result-card">当前没有可展示的推荐候选。</div>';
      return;
    }

    recommendationList.innerHTML = snapshot.recommendations
      .map(function (item) {
        return `
          <article class="debug-card">
            <div class="debug-card-header">
              <div>
                <p class="admin-eyebrow">Rank ${item.rank}</p>
                <h3>${escapeHtml(item.name)}</h3>
                <p class="page-copy">${escapeHtml(item.category || "未分类")} · ${escapeHtml(
          item.reason
        )}</p>
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
                  <strong>排序器</strong>
                  <span>${escapeHtml(item.ranker_name || "-")}</span>
                </div>
              </div>
            </div>
            <div class="debug-card-section">
              <strong>召回通道</strong>
              ${renderTagList(item.recall_channels)}
            </div>
            <div class="debug-card-section">
              <strong>特征高亮</strong>
              ${renderTagList(item.feature_highlights)}
            </div>
            <div class="debug-card-section">
              <strong>命中兴趣词</strong>
              ${renderTagList(item.matched_terms)}
            </div>
            <div class="debug-card-section">
              <strong>排序特征</strong>
              <pre class="admin-code-block">${escapeHtml(
                JSON.stringify(item.ranking_features || {}, null, 2)
              )}</pre>
            </div>
            <div class="debug-card-section">
              <strong>分数拆解</strong>
              <pre class="admin-code-block">${escapeHtml(
                JSON.stringify(item.score_breakdown || {}, null, 2)
              )}</pre>
            </div>
          </article>
        `;
      })
      .join("");
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

  async function loadVectorIndexStatus() {
    const [statusPayload, dashboardPayload] = await Promise.all([
      request("/api/v1/admin/vector-index/products/status"),
      request("/api/v1/admin/dashboard/summary"),
    ]);
    latestVectorStatus = statusPayload.data.status || null;
    renderVectorStatus(statusPayload.data.status, dashboardPayload.data.runtime || {});
  }

  async function syncVectorIndex(mode, button) {
    if (button) {
      button.disabled = true;
    }

    try {
      const useLegacyReindex =
        mode === "full" &&
        (!latestVectorStatus?.qdrant_available || !latestVectorStatus?.collection_exists);
      const payload = useLegacyReindex
        ? await request("/api/v1/admin/reindex/products", {
            method: "POST",
            body: { force: true },
          })
        : await request("/api/v1/admin/vector-index/products/sync", {
            method: "POST",
            body: { mode },
          });
      renderReindexResult(payload.data.result);
      await loadVectorIndexStatus();
      showFlash("向量索引操作已完成。", "success");
    } catch (error) {
      showFlash(error?.payload?.message || "向量索引操作失败。", "danger");
    } finally {
      if (button) {
        button.disabled = false;
      }
    }
  }

  function bindReindexAction() {
    const fullButton = document.getElementById("reindex-products-btn");
    const retryFailedButton = document.getElementById("retry-failed-btn");

    fullButton?.addEventListener("click", function () {
      void syncVectorIndex("full", fullButton);
    });
    retryFailedButton?.addEventListener("click", function () {
      void syncVectorIndex("retry_failed", retryFailedButton);
    });

    void loadVectorIndexStatus();
  }

  function bindRecommendationDebugPage() {
    const form = document.getElementById("recommendation-debug-form");
    const userIdInput = document.getElementById("debug-user-id");
    const emailInput = document.getElementById("debug-user-email");
    const limitInput = document.getElementById("debug-limit");
    const submitButton = document.getElementById("recommendation-debug-submit");
    if (!form || !emailInput || !limitInput || !submitButton) {
      return;
    }

    form.addEventListener("submit", async function (event) {
      event.preventDefault();

      const userId = userIdInput?.value?.trim() || "";
      const email = emailInput.value.trim().toLowerCase();
      const limit = limitInput.value.trim() || "5";
      if (!userId && !email) {
        showFlash("请输入要查询的前台用户邮箱或用户 ID。", "warning");
        return;
      }

      submitButton.disabled = true;
      submitButton.textContent = "加载中...";

      try {
        const params = new URLSearchParams({ limit });
        if (userId) {
          params.set("user_id", userId);
        }
        if (email) {
          params.set("email", email);
        }
        const payload = await request(`/api/v1/admin/recommendations/debug?${params.toString()}`);
        renderRecommendationDebug(payload.data);
        showFlash("已加载推荐调试信息。", "success");
      } catch (error) {
        showFlash(error?.payload?.message || "推荐调试信息加载失败。", "danger");
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = "加载推荐证据";
      }
    });
  }

  async function loadRecommendationConfigPage() {
    const payload = await request("/api/v1/admin/recommendations/experiments");
    const activeCopy = document.getElementById("recommendation-config-active");
    const list = document.getElementById("recommendation-config-list");

    if (activeCopy) {
      activeCopy.textContent = `当前激活方案：${
        payload.data.active_key || "unknown"
      }。这组配置决定搜索与推荐链路当前启用哪些召回和排序能力。`;
    }
    if (list) {
      list.innerHTML = renderExperimentCards(payload.data.items || []);
    }
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
    if (!loginForm) {
      return;
    }

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
      } else if (page === "recommendation-config") {
        await loadRecommendationConfigPage();
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
