document.addEventListener("DOMContentLoaded", function () {
  // 检查登录状态
  if (!isLoggedIn()) {
    window.location.href = "login.html";
    return;
  }

  // 初始化订单信息
  initializeOrder();

  // 监听余额支付复选框变化
  document
    .getElementById("use-balance")
    .addEventListener("change", function () {
      updatePaymentOptions(this.checked);
    });

  // 阻止表单默认提交
  document
    .getElementById("checkout-form")
    .addEventListener("submit", function (e) {
      e.preventDefault();
    });

  // 绑定提交订单按钮事件
  document
    .getElementById("place-order-btn")
    .addEventListener("click", function (e) {
      // 验证表单
      if (validateCheckoutForm()) {
        // 提交订单
        submitOrder();
      }
    });

  // 初始化表单验证
  initFormValidation();
});

// 表单验证
function validateCheckoutForm() {
  const form = document.getElementById("checkout-form");
  const fullName = form.querySelector("#full_name");
  const phone = form.querySelector("#phone");
  const address = form.querySelector("#address");
  let isValid = true;

  // 验证姓名
  if (!validateRequired(fullName, "请输入收货人姓名")) {
    isValid = false;
  }

  // 验证电话
  if (!validatePhone(phone)) {
    isValid = false;
  }

  // 验证地址
  if (!validateRequired(address, "请输入收货地址")) {
    isValid = false;
  }

  return isValid;
}

// 初始化订单信息
function initializeOrder() {
  const cart = JSON.parse(localStorage.getItem("shiyige_cart")) || [];
  const orderItems = document.getElementById("order-items");

  if (cart.length === 0) {
    window.location.href = "cart.html";
    return;
  }

  // 清空订单商品列表
  orderItems.innerHTML = "";

  // 计算订单金额
  let subtotal = 0;
  cart.forEach((item) => {
    const itemSubtotal = parseFloat(item.price) * parseInt(item.quantity);
    subtotal += itemSubtotal;
    // 添加商品到订单列表
    addItemToOrderList(item, itemSubtotal);
  });

  // 初始化会员信息
  const membership = window.membership.initMembership();
  const currentLevel = window.membership.getCurrentLevel(membership.points);

  // 更新会员信息显示
  document.getElementById("member-level").textContent = currentLevel.name;
  document.getElementById("member-discount-rate").textContent = `${(
    100 -
    currentLevel.discount * 100
  ).toFixed(0)}%`;
  document.getElementById(
    "current-balance"
  ).textContent = `¥${membership.balance.toFixed(2)}`;

  // 计算优惠和最终金额
  calculateOrderTotal(subtotal);
}

// 添加商品到订单列表
function addItemToOrderList(item, subtotal) {
  const orderItems = document.getElementById("order-items");
  const itemDiv = document.createElement("div");
  itemDiv.className = "order-item mb-3";
  itemDiv.innerHTML = `
    <div class="d-flex justify-content-between align-items-center">
      <div>
        <div class="fw-bold">${item.name}</div>
        <div class="text-muted small">¥${item.price} × ${item.quantity}</div>
      </div>
      <div>¥${subtotal.toFixed(2)}</div>
    </div>
  `;
  orderItems.appendChild(itemDiv);
}

// 计算订单总金额
function calculateOrderTotal(subtotal) {
  // 获取会员信息
  const membership = window.membership.initMembership();
  const currentLevel = window.membership.getCurrentLevel(membership.points);

  // 计算运费
  const shipping = subtotal > 0 ? 10 : 0;

  // 计算满减优惠
  const promotionDiscount = window.promotion.calculateDiscount(subtotal);

  // 计算会员折扣金额
  const memberDiscount = subtotal * (1 - currentLevel.discount);

  // 计算预计获得的积分
  const expectedPoints = Math.floor(subtotal * currentLevel.pointsRate);

  // 计算最终金额
  const total = subtotal + shipping - promotionDiscount - memberDiscount;

  // 更新页面显示
  document.getElementById("subtotal").textContent = `¥${subtotal.toFixed(2)}`;
  document.getElementById("shipping").textContent = `¥${shipping.toFixed(2)}`;
  document.getElementById(
    "promotion-discount"
  ).textContent = `-¥${promotionDiscount.toFixed(2)}`;
  document.getElementById(
    "member-discount"
  ).textContent = `-¥${memberDiscount.toFixed(2)}`;
  document.getElementById("total").textContent = `¥${total.toFixed(2)}`;
  document.getElementById("expected-points").textContent = expectedPoints;

  // 更新满减进度条
  window.promotion.updatePromotionProgress(subtotal);

  // 更新余额支付选项
  updateBalancePaymentOption(total, membership.balance);
}

// 更新余额支付选项
function updateBalancePaymentOption(total, balance) {
  const useBalanceCheckbox = document.getElementById("use-balance");
  const balanceSection = document.getElementById("balance-payment-section");

  if (balance >= total) {
    balanceSection.classList.remove("d-none");
    useBalanceCheckbox.disabled = false;
  } else {
    balanceSection.classList.add("d-none");
    useBalanceCheckbox.disabled = true;
    useBalanceCheckbox.checked = false;
  }
}

// 更新支付选项
function updatePaymentOptions(useBalance) {
  const paymentOptions = document.querySelectorAll(
    '.payment-options input[type="radio"]'
  );
  paymentOptions.forEach((option) => {
    option.disabled = useBalance;
    if (useBalance) {
      option.checked = false;
    } else {
      if (option.id === "alipay") {
        option.checked = true;
      }
    }
  });
}

// 提交订单
function submitOrder() {
  const form = document.getElementById("checkout-form");
  const formData = new FormData(form);
  const useBalance = document.getElementById("use-balance").checked;
  const total = parseFloat(
    document.getElementById("total").textContent.replace("¥", "")
  );

  // 表单验证
  if (!validateCheckoutForm()) {
    return;
  }

  // 验证支付方式
  if (!useBalance && !document.querySelector('input[name="payment"]:checked')) {
    showNotification("请选择支付方式", "error");
    return;
  }

  // 使用余额支付
  if (useBalance) {
    const membership = window.membership.initMembership();
    if (membership.balance < total) {
      showNotification("余额不足，请选择其他支付方式", "error");
      return;
    }
    // 扣除余额
    membership.balance -= total;
    localStorage.setItem("shiyige_membership", JSON.stringify(membership));
  }

  try {
    // 生成订单号
    const orderNumber = "SYG" + Date.now().toString().slice(-8);

    // 获取当前购物车商品
    const cartItems = JSON.parse(localStorage.getItem("shiyige_cart"));

    // 保存订单信息到本地存储
    const orders = JSON.parse(localStorage.getItem("shiyige_orders")) || [];
    const newOrder = {
      orderNumber,
      date: new Date().toISOString(),
      items: cartItems,
      total,
      status: "待发货",
      shipping: {
        name: formData.get("full_name"),
        phone: formData.get("phone"),
        address: formData.get("address"),
        note: formData.get("note"),
      },
      payment: useBalance
        ? "余额支付"
        : document.querySelector('input[name="payment"]:checked').id,
    };

    orders.push(newOrder);
    localStorage.setItem("shiyige_orders", JSON.stringify(orders));

    // 清空购物车
    localStorage.removeItem("shiyige_cart");

    // 显示成功提示
    showOrderSuccess(orderNumber);
  } catch (error) {
    console.error("提交订单时出错:", error);
    showNotification("订单提交失败，请重试", "error");
  }
}

// 显示订单成功提示
function showOrderSuccess(orderNumber) {
  document.getElementById("order-number").textContent = orderNumber;
  const successModal = new bootstrap.Modal(
    document.getElementById("orderSuccessModal")
  );
  successModal.show();
}

// 显示通知消息
function showNotification(message, type = "success") {
  const flashMessages = document.getElementById("flash-messages");
  const alert = document.createElement("div");
  alert.className = `alert alert-${type} alert-dismissible fade show`;
  alert.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  flashMessages.appendChild(alert);

  // 3秒后自动消失
  setTimeout(() => {
    alert.remove();
  }, 3000);
}
