/* 拾遗阁 - 结算页脚本 */

(function () {
  const state = {
    cart: null,
    addresses: [],
    selectedAddressId: null,
  };

  function formatCurrency(value) {
    const amount = Number(value ?? 0);
    if (typeof window.formatPrice === "function") {
      return window.formatPrice(amount);
    }
    return `¥${amount.toFixed(2)}`;
  }

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

  function getShippingAmount() {
    const cartItems = state.cart?.items || [];
    return cartItems.length > 0 ? 10 : 0;
  }

  function setPlaceOrderButtonDisabled(disabled, text) {
    const button = document.getElementById("place-order-btn");
    if (!button) {
      return;
    }

    button.disabled = disabled;
    button.textContent = text || "提交订单并模拟支付";
  }

  function renderCartSummary(cart) {
    const orderItems = document.getElementById("order-items");
    const cartItems = cart?.items || [];

    if (!orderItems) {
      return;
    }

    if (!cartItems.length) {
      window.location.href = "cart.html";
      return;
    }

    orderItems.innerHTML = cartItems
      .map(function (item) {
        return `
          <div class="order-item mb-3">
            <div class="d-flex justify-content-between align-items-start gap-3">
              <div>
                <div class="fw-bold">${escapeHtml(item.product.name)}</div>
                <div class="text-muted small">${escapeHtml(item.sku.name)} · ${escapeHtml(formatCurrency(item.sku.price))} × ${escapeHtml(item.quantity)}</div>
              </div>
              <div class="fw-semibold">${escapeHtml(formatCurrency(item.subtotal))}</div>
            </div>
          </div>
        `;
      })
      .join("");

    const subtotal = Number(cart.total_amount || 0);
    const shipping = getShippingAmount();
    const total = subtotal + shipping;

    document.getElementById("subtotal").textContent = formatCurrency(subtotal);
    document.getElementById("shipping").textContent = formatCurrency(shipping);
    document.getElementById("total").textContent = formatCurrency(total);
  }

  function renderSelectedAddress(address) {
    const card = document.getElementById("selected-address-card");
    if (!card) {
      return;
    }

    if (!address) {
      card.innerHTML = `
        <div class="card-body">
          <div class="text-muted">请选择一个收货地址后继续。</div>
        </div>
      `;
      return;
    }

    card.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start gap-3">
          <div>
            <div class="fw-semibold mb-1">${escapeHtml(address.recipient_name)}</div>
            <div class="mb-1">${escapeHtml(address.phone)}</div>
            <div class="text-muted">${escapeHtml(address.region)} ${escapeHtml(address.detail_address)}</div>
          </div>
          <span class="badge ${address.is_default ? "bg-success" : "bg-secondary"}">
            ${address.is_default ? "默认地址" : "已保存地址"}
          </span>
        </div>
      </div>
    `;
  }

  function renderAddresses(addresses) {
    const addressSelect = document.getElementById("address-select");
    const emptyAlert = document.getElementById("address-empty-alert");
    if (!addressSelect || !emptyAlert) {
      return;
    }

    state.addresses = addresses;

    if (!addresses.length) {
      state.selectedAddressId = null;
      addressSelect.innerHTML = '<option value="">暂无可用地址</option>';
      addressSelect.disabled = true;
      emptyAlert.classList.remove("d-none");
      renderSelectedAddress(null);
      setPlaceOrderButtonDisabled(true, "请先补充收货地址");
      return;
    }

    emptyAlert.classList.add("d-none");
    addressSelect.disabled = false;
    addressSelect.innerHTML = addresses
      .map(function (address) {
        return `
          <option value="${address.id}">
            ${escapeHtml(address.recipient_name)} · ${escapeHtml(address.region)} ${escapeHtml(address.detail_address)}
          </option>
        `;
      })
      .join("");

    const defaultAddress = addresses.find(function (address) {
      return address.is_default;
    });
    state.selectedAddressId = defaultAddress?.id || addresses[0].id;
    addressSelect.value = String(state.selectedAddressId);
    renderSelectedAddress(
      addresses.find(function (address) {
        return address.id === state.selectedAddressId;
      }) || null
    );
    setPlaceOrderButtonDisabled(false);
  }

  function getSelectedPaymentMethod() {
    return document.querySelector('input[name="payment"]:checked')?.value || null;
  }

  function generateIdempotencyKey() {
    return `checkout-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
  }

  function showOrderSuccess(order) {
    document.getElementById("order-number").textContent = order.order_no;
    document.getElementById("success-payment-method").textContent =
      order.payment_records?.[0]?.payment_method || "alipay";
    document.getElementById("success-order-total").textContent = formatCurrency(
      order.payable_amount
    );

    const modal = new bootstrap.Modal(document.getElementById("orderSuccessModal"));
    modal.show();
  }

  async function submitOrder() {
    if (!state.selectedAddressId) {
      showNotification("请先选择收货地址", "warning");
      return;
    }

    const paymentMethod = getSelectedPaymentMethod();
    if (!paymentMethod) {
      showNotification("请选择支付方式", "error");
      return;
    }

    setPlaceOrderButtonDisabled(true, "正在提交订单...");
    const noteValue = document.getElementById("note")?.value?.trim() || null;

    let createdOrder = null;
    try {
      const createPayload = await window.shiyigeApi.post("/orders", {
        address_id: Number(state.selectedAddressId),
        buyer_note: noteValue,
        idempotency_key: generateIdempotencyKey(),
      });
      createdOrder = createPayload?.data?.order || null;
    } catch (error) {
      showNotification(error?.payload?.message || "订单创建失败", "error");
      setPlaceOrderButtonDisabled(false);
      return;
    }

    try {
      const payPayload = await window.shiyigeApi.post(`/orders/${createdOrder.id}/pay`, {
        payment_method: paymentMethod,
      });
      const paidOrder = payPayload?.data?.order || createdOrder;
      await window.shiyigeCart?.refreshCartCount?.();
      await window.updateNavigation?.();
      setPlaceOrderButtonDisabled(false);
      showNotification("订单已提交并完成模拟支付", "success");
      showOrderSuccess(paidOrder);
    } catch (error) {
      showNotification(error?.payload?.message || "订单已创建，请前往订单页继续支付", "warning");
      window.location.href = "orders.html";
    }
  }

  async function loadCheckoutPage() {
    const user = await window.shiyigeAuth?.fetchCurrentUser?.({ allowRefresh: true });
    if (!user) {
      window.location.href = "login.html";
      return;
    }

    try {
      const [cartPayload, addressPayload] = await Promise.all([
        window.shiyigeApi.get("/cart"),
        window.shiyigeApi.get("/users/addresses"),
      ]);

      state.cart = cartPayload?.data?.cart || null;
      renderCartSummary(state.cart);
      renderAddresses(addressPayload?.data?.items || []);
    } catch (error) {
      showNotification(error?.payload?.message || "结算页加载失败", "error");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("checkout-form")?.addEventListener("submit", function (event) {
      event.preventDefault();
    });

    document.getElementById("address-select")?.addEventListener("change", function () {
      const selectedId = Number(this.value);
      state.selectedAddressId = Number.isInteger(selectedId) ? selectedId : null;
      renderSelectedAddress(
        state.addresses.find(function (address) {
          return address.id === state.selectedAddressId;
        }) || null
      );
    });

    document.getElementById("place-order-btn")?.addEventListener("click", function () {
      void submitOrder();
    });

    void loadCheckoutPage();
  });
})();
