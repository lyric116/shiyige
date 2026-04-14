/* 拾遗阁 - 订单页脚本 */

(function () {
  const state = {
    orders: [],
    selectedOrderId: null,
    selectedOrder: null,
  };

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, function (char) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[char];
    });
  }

  function formatCurrency(value) {
    const amount = Number(value ?? 0);
    if (typeof window.formatPrice === "function") {
      return window.formatPrice(amount);
    }
    return `¥${amount.toFixed(2)}`;
  }

  function formatDateTime(value) {
    if (!value) {
      return "--";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString("zh-CN", {
      hour12: false,
    });
  }

  function getStatusMeta(status) {
    if (status === "PAID") {
      return { label: "已支付", className: "bg-success" };
    }

    if (status === "CANCELLED") {
      return { label: "已取消", className: "bg-secondary" };
    }

    return { label: "待支付", className: "bg-warning text-dark" };
  }

  function updateSidebar(user) {
    const profile = user.profile || {};
    const usernameElement = document.getElementById("sidebar-username");
    const emailElement = document.getElementById("sidebar-email");

    if (usernameElement) {
      usernameElement.textContent = profile.display_name || user.username;
    }

    if (emailElement) {
      emailElement.textContent = user.email;
    }
  }

  function renderSummary() {
    const total = state.orders.length;
    const pending = state.orders.filter((order) => order.status === "PENDING_PAYMENT").length;
    const paid = state.orders.filter((order) => order.status === "PAID").length;

    document.getElementById("summary-total").textContent = String(total);
    document.getElementById("summary-pending").textContent = String(pending);
    document.getElementById("summary-paid").textContent = String(paid);
    document.getElementById("orders-list-count").textContent = String(total);
  }

  function renderOrderList() {
    const listElement = document.getElementById("orders-list");
    if (!listElement) {
      return;
    }

    listElement.innerHTML = state.orders
      .map(function (order) {
        const status = getStatusMeta(order.status);
        const firstItem = order.items?.[0];
        const extraItemsCount = Math.max((order.items?.length || 0) - 1, 0);
        const isSelected = order.id === state.selectedOrderId;
        const preview = firstItem
          ? `${firstItem.product_name}${extraItemsCount > 0 ? ` 等 ${order.items.length} 件商品` : ""}`
          : "暂无商品信息";

        return `
          <button
            type="button"
            class="list-group-item list-group-item-action order-list-item${isSelected ? " active" : ""}"
            data-order-id="${order.id}"
          >
            <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
              <div>
                <div class="fw-semibold">${escapeHtml(order.order_no)}</div>
                <div class="small text-muted">${escapeHtml(formatDateTime(order.created_at))}</div>
              </div>
              <span class="badge ${status.className}">${status.label}</span>
            </div>
            <div class="small text-muted mb-2">${escapeHtml(preview)}</div>
            <div class="fw-semibold">${escapeHtml(formatCurrency(order.payable_amount))}</div>
          </button>
        `;
      })
      .join("");

    listElement.querySelectorAll(".order-list-item").forEach(function (button) {
      button.addEventListener("click", function () {
        const orderId = Number(button.dataset.orderId);
        if (orderId) {
          void loadOrderDetail(orderId);
        }
      });
    });
  }

  function renderOrderDetail(order) {
    const detailElement = document.getElementById("order-detail");
    if (!detailElement) {
      return;
    }

    if (!order) {
      detailElement.innerHTML = '<p class="text-muted mb-0">请选择订单查看详情。</p>';
      return;
    }

    const status = getStatusMeta(order.status);
    const address = order.address || {};
    const buyerNote = order.buyer_note || "无";
    const paymentRecords = order.payment_records || [];
    const actionButtons =
      order.status === "PENDING_PAYMENT"
        ? `
            <div class="d-flex flex-wrap gap-2">
              <button type="button" class="btn btn-primary" id="order-pay-button">立即支付</button>
              <button type="button" class="btn btn-outline-secondary" id="order-cancel-button">取消订单</button>
            </div>
          `
        : "";

    detailElement.innerHTML = `
      <div class="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-4">
        <div>
          <div class="text-muted small mb-2">订单号</div>
          <div class="h5 mb-2" id="order-no">${escapeHtml(order.order_no)}</div>
          <span class="badge ${status.className}" id="order-status">${status.label}</span>
        </div>
        ${actionButtons}
      </div>

      <div class="row g-3 mb-4">
        <div class="col-md-6">
          <div class="card border-0 bg-light h-100">
            <div class="card-body">
              <div class="text-muted small mb-2">订单信息</div>
              <div class="order-detail-item"><span>创建时间</span><strong>${escapeHtml(formatDateTime(order.created_at))}</strong></div>
              <div class="order-detail-item"><span>支付时间</span><strong>${escapeHtml(formatDateTime(order.paid_at))}</strong></div>
              <div class="order-detail-item"><span>取消时间</span><strong>${escapeHtml(formatDateTime(order.cancelled_at))}</strong></div>
              <div class="order-detail-item"><span>买家备注</span><strong>${escapeHtml(buyerNote)}</strong></div>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card border-0 bg-light h-100">
            <div class="card-body">
              <div class="text-muted small mb-2">收货信息</div>
              <div class="fw-semibold mb-1">${escapeHtml(address.recipient_name || "--")}</div>
              <div class="mb-1">${escapeHtml(address.recipient_phone || "--")}</div>
              <div class="text-muted">${escapeHtml(address.recipient_region || "")} ${escapeHtml(address.recipient_detail_address || "")}</div>
              <div class="text-muted small mt-1">邮编：${escapeHtml(address.recipient_postal_code || "--")}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card border-0 bg-light mb-4">
        <div class="card-body">
          <div class="text-muted small mb-3">商品明细</div>
          <div class="table-responsive">
            <table class="table align-middle mb-0">
              <thead>
                <tr>
                  <th>商品</th>
                  <th>规格</th>
                  <th>数量</th>
                  <th>单价</th>
                  <th>小计</th>
                </tr>
              </thead>
              <tbody>
                ${order.items
                  .map(function (item) {
                    return `
                      <tr>
                        <td>${escapeHtml(item.product_name)}</td>
                        <td>${escapeHtml(item.sku_name)}</td>
                        <td>${escapeHtml(item.quantity)}</td>
                        <td>${escapeHtml(formatCurrency(item.unit_price))}</td>
                        <td>${escapeHtml(formatCurrency(item.subtotal_amount))}</td>
                      </tr>
                    `;
                  })
                  .join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-md-6">
          <div class="card border-0 bg-light h-100">
            <div class="card-body">
              <div class="text-muted small mb-2">金额汇总</div>
              <div class="order-detail-item"><span>商品金额</span><strong>${escapeHtml(formatCurrency(order.goods_amount))}</strong></div>
              <div class="order-detail-item"><span>运费</span><strong>${escapeHtml(formatCurrency(order.shipping_amount))}</strong></div>
              <div class="order-detail-item"><span>应付金额</span><strong class="text-danger">${escapeHtml(formatCurrency(order.payable_amount))}</strong></div>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card border-0 bg-light h-100">
            <div class="card-body">
              <div class="text-muted small mb-2">支付记录</div>
              <div id="payment-records">
                ${
                  paymentRecords.length
                    ? paymentRecords
                        .map(function (record) {
                          return `
                            <div class="order-payment-record">
                              <div class="fw-semibold">${escapeHtml(record.payment_no)}</div>
                              <div class="small text-muted">${escapeHtml(record.payment_method)} · ${escapeHtml(formatDateTime(record.paid_at))}</div>
                              <div>${escapeHtml(formatCurrency(record.amount))}</div>
                            </div>
                          `;
                        })
                        .join("")
                    : '<div class="text-muted">当前还没有支付记录。</div>'
                }
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    const payButton = document.getElementById("order-pay-button");
    if (payButton) {
      payButton.addEventListener("click", function () {
        void submitOrderAction(order.id, "pay");
      });
    }

    const cancelButton = document.getElementById("order-cancel-button");
    if (cancelButton) {
      cancelButton.addEventListener("click", function () {
        void submitOrderAction(order.id, "cancel");
      });
    }
  }

  function setLoading(message, isError) {
    const loadingElement = document.getElementById("orders-loading");
    if (!loadingElement) {
      return;
    }

    if (!message) {
      loadingElement.classList.add("d-none");
      loadingElement.classList.remove("alert-danger");
      loadingElement.classList.add("alert-secondary");
      return;
    }

    loadingElement.textContent = message;
    loadingElement.classList.remove("d-none");
    if (isError) {
      loadingElement.classList.remove("alert-secondary");
      loadingElement.classList.add("alert-danger");
    } else {
      loadingElement.classList.remove("alert-danger");
      loadingElement.classList.add("alert-secondary");
    }
  }

  function toggleOrderContainers(hasOrders) {
    document.getElementById("orders-empty-state")?.classList.toggle("d-none", hasOrders);
    document.getElementById("orders-content")?.classList.toggle("d-none", !hasOrders);
  }

  async function loadOrderDetail(orderId) {
    state.selectedOrderId = orderId;
    renderOrderList();
    renderOrderDetail(null);

    try {
      const payload = await window.shiyigeApi.get(`/orders/${orderId}`);
      state.selectedOrder = payload?.data?.order || null;
      renderOrderList();
      renderOrderDetail(state.selectedOrder);
    } catch (error) {
      renderOrderDetail(null);
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "订单详情加载失败", "error");
      }
    }
  }

  async function refreshOrders(selectedOrderId) {
    const payload = await window.shiyigeApi.get("/orders");
    state.orders = payload?.data?.items || [];
    renderSummary();

    if (!state.orders.length) {
      state.selectedOrderId = null;
      state.selectedOrder = null;
      toggleOrderContainers(false);
      renderOrderDetail(null);
      return;
    }

    toggleOrderContainers(true);
    const fallbackOrderId = state.orders[0].id;
    const nextSelectedId = state.orders.some(function (order) {
      return order.id === selectedOrderId;
    })
      ? selectedOrderId
      : fallbackOrderId;

    renderOrderList();
    await loadOrderDetail(nextSelectedId);
  }

  async function submitOrderAction(orderId, action) {
    const payButton = document.getElementById("order-pay-button");
    const cancelButton = document.getElementById("order-cancel-button");

    if (payButton) {
      payButton.disabled = true;
    }
    if (cancelButton) {
      cancelButton.disabled = true;
    }

    try {
      if (action === "pay") {
        await window.shiyigeApi.post(`/orders/${orderId}/pay`, {
          payment_method: "balance",
        });
        if (typeof showNotification === "function") {
          showNotification("订单支付成功", "success");
        }
      } else {
        await window.shiyigeApi.post(`/orders/${orderId}/cancel`);
        if (typeof showNotification === "function") {
          showNotification("订单已取消", "success");
        }
      }

      await refreshOrders(orderId);
    } catch (error) {
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "订单操作失败", "error");
      }
      await refreshOrders(orderId);
    }
  }

  async function loadOrdersPage() {
    const user = await window.shiyigeAuth?.fetchCurrentUser?.({ allowRefresh: true });
    if (!user) {
      window.location.href = "login.html";
      return;
    }

    updateSidebar(user);

    const logoutButton = document.getElementById("logout-sidebar-btn");
    if (logoutButton) {
      logoutButton.addEventListener("click", function (event) {
        event.preventDefault();
        void window.logout?.();
      });
    }

    try {
      setLoading("正在加载订单...", false);
      await refreshOrders();
      setLoading("", false);
    } catch (error) {
      toggleOrderContainers(false);
      setLoading(error?.payload?.message || "订单列表加载失败", true);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    void loadOrdersPage();
  });
})();
