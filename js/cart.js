/* 拾遗阁 - 购物车管理脚本 */

document.addEventListener("DOMContentLoaded", function () {
  // 初始化购物车功能
  initializeCart();
});

/**
 * 初始化购物车功能
 */
function initializeCart() {
  // 购物车页面相关功能
  if (document.querySelector(".cart-table")) {
    setupCartPage();
  }

  // 初始化加入购物车功能
  setupAddToCartButtons();

  // 更新购物车计数
  updateCartCount();
}

/**
 * 设置购物车页面功能
 */
function setupCartPage() {
  // 全选/取消全选
  const selectAllCheckbox = document.getElementById("select-all");
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener("change", function () {
      const isChecked = this.checked;
      const itemCheckboxes = document.querySelectorAll(".cart-item-checkbox");

      itemCheckboxes.forEach((checkbox) => {
        checkbox.checked = isChecked;
      });

      // 更新总价
      updateCartTotal();
    });
  }

  // 监听购物车项复选框变化
  const itemCheckboxes = document.querySelectorAll(".cart-item-checkbox");
  itemCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", updateCartTotal);
  });

  // 监听数量输入框变化
  const quantityInputs = document.querySelectorAll(".cart-quantity");
  quantityInputs.forEach((input) => {
    input.addEventListener("change", function () {
      const quantity = parseInt(this.value);
      if (isNaN(quantity) || quantity < 1) {
        this.value = 1;
      }

      const form = this.closest("form");
      form.submit();
    });
  });

  // 清空购物车按钮
  const clearCartBtn = document.getElementById("clear-cart");
  if (clearCartBtn) {
    clearCartBtn.addEventListener("click", function (e) {
      e.preventDefault();

      if (confirm("确定要清空购物车吗？")) {
        const forms = document.querySelectorAll(".remove-item-form");

        // 按顺序提交所有删除表单
        Array.from(forms)
          .reduce((promise, form) => {
            return promise.then(() => {
              return new Promise((resolve) => {
                fetch(form.action, {
                  method: "POST",
                  body: new FormData(form),
                }).then(() => resolve());
              });
            });
          }, Promise.resolve())
          .then(() => {
            // 全部删除完成后刷新页面
            window.location.reload();
          });
      }
    });
  }
}

/**
 * 更新购物车总价
 */
function updateCartTotal() {
  const checkedItems = document.querySelectorAll(".cart-item-checkbox:checked");
  let total = 0;

  checkedItems.forEach((checkbox) => {
    const row = checkbox.closest("tr");
    const price = parseFloat(row.dataset.price);
    const quantity = parseInt(row.querySelector(".cart-quantity").value);

    if (!isNaN(price) && !isNaN(quantity)) {
      total += price * quantity;
    }
  });

  // 更新总价显示
  const totalElement = document.getElementById("cart-total-price");
  if (totalElement) {
    totalElement.textContent = formatPrice(total);
  }

  // 更新结算按钮状态
  const checkoutBtn = document.getElementById("checkout-btn");
  if (checkoutBtn) {
    checkoutBtn.disabled = checkedItems.length === 0;
  }
}

// 更新购物车总计
function updateCartTotal() {
  let subtotal = 0;

  // 计算选中商品的总价
  document.querySelectorAll(".cart-item-check:checked").forEach((checkbox) => {
    const productId = checkbox.dataset.id;
    const subtotalElement = document.querySelector(
      `.cart-item[data-id="${productId}"] .cart-item-subtotal`
    );
    subtotal += parseFloat(subtotalElement.dataset.subtotal);
  });

  // 计算满减优惠
  const discount = window.promotion.calculateDiscount(subtotal);

  // 更新满减进度条
  window.promotion.updatePromotionProgress(subtotal);

  // 设置运费（这里简单示例，实际可能有更复杂的逻辑）
  const shipping = subtotal > 0 ? 10 : 0;

  // 计算最终总价
  const total = subtotal + shipping - discount;

  // 更新页面显示
  document.getElementById("cart-subtotal").textContent = `¥${subtotal.toFixed(
    2
  )}`;
  document.getElementById("cart-shipping").textContent = `¥${shipping.toFixed(
    2
  )}`;
  document.getElementById("cart-total").textContent = `¥${total.toFixed(2)}`;

  // 保存当前购物车总价和优惠信息到localStorage，供结算页面使用
  const cartSummary = {
    subtotal,
    shipping,
    discount,
    total,
  };
  localStorage.setItem("shiyige_cart_summary", JSON.stringify(cartSummary));
}

/**
 * 设置加入购物车按钮功能
 */
function setupAddToCartButtons() {
  document.querySelectorAll(".add-to-cart a").forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const productId = this.getAttribute("href").split("=")[1];
      const productName =
        this.closest(".product-card").querySelector(
          ".product-name"
        ).textContent;
      addToCart(productId, 1, productName);
    });
  });
}

/**
 * 添加商品到购物车
 * @param {string} productId - 产品ID
 * @param {number} quantity - 数量
 * @param {string} productName - 产品名称
 */
function addToCart(productId, quantity, productName) {
  // 获取当前购物车数据
  let cart = JSON.parse(localStorage.getItem("shiyige_cart")) || [];

  // 查找商品是否已在购物车中
  const existingItem = cart.find((item) => item.productId === productId);

  if (existingItem) {
    // 如果商品已存在，增加数量
    existingItem.quantity =
      parseInt(existingItem.quantity) + parseInt(quantity);
  } else {
    // 如果是新商品，获取商品信息并添加到购物车
    const productCard = document
      .querySelector(`[href="product.html?id=${productId}"]`)
      .closest(".product-card");
    const productPrice = productCard
      .querySelector(".product-price")
      .textContent.replace("¥", "");
    const productCategory =
      productCard.querySelector(".product-category").textContent;
    const productImage = productCard.querySelector(".product-img img").src;

    cart.push({
      productId: productId,
      name: productName,
      price: parseFloat(productPrice),
      quantity: parseInt(quantity),
      category: productCategory,
      image: productImage,
    });
  }

  // 保存购物车数据
  localStorage.setItem("shiyige_cart", JSON.stringify(cart));

  // 更新购物车计数
  updateCartCount(cart.length);

  // 显示成功提示
  showNotification(`已将 ${productName} 添加到购物车`, "success");
}

/**
 * 更新购物车计数
 * @param {number} count - 购物车商品数量
 */
function updateCartCount(count) {
  const cartCount = document.getElementById("cart-count");
  if (!cartCount) return;

  if (count === undefined) {
    const cart = JSON.parse(localStorage.getItem("shiyige_cart")) || [];
    count = cart.length;
  }

  if (count > 0) {
    cartCount.textContent = count;
    cartCount.classList.remove("d-none");
  } else {
    cartCount.classList.add("d-none");
  }
}

/**
 * 获取CSRF令牌
 * @returns {string} CSRF令牌
 */
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}

/**
 * 显示通知消息
 * @param {string} message - 通知消息
 * @param {string} type - 通知类型 ('success' | 'error' | 'warning' | 'info')
 */
function showNotification(message, type = "info") {
  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.innerHTML = message;

  document.body.appendChild(notification);

  // 显示通知
  setTimeout(() => {
    notification.classList.add("show");
  }, 10);

  // 3秒后隐藏
  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 3000);
}
