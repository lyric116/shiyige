/* 拾遗阁 - 购物车脚本 */

(function () {
  function parseProductIdFromHref(href) {
    if (!href) return null;

    try {
      const url = new URL(href, window.location.href);
      const productId = Number.parseInt(url.searchParams.get("id") || "", 10);
      return Number.isInteger(productId) ? productId : null;
    } catch (error) {
      return null;
    }
  }

  function updateCartCountBadge(totalQuantity) {
    const cartCount = document.getElementById("cart-count");
    if (!cartCount) return;

    if (totalQuantity > 0) {
      cartCount.textContent = String(totalQuantity);
      cartCount.classList.remove("d-none");
      return;
    }

    cartCount.classList.add("d-none");
  }

  async function fetchCart() {
    const payload = await window.shiyigeApi.get("/cart");
    const cart = payload?.data?.cart || {
      id: null,
      items: [],
      total_quantity: 0,
      total_amount: 0,
    };
    updateCartCountBadge(cart.total_quantity || 0);
    return cart;
  }

  async function refreshCartCount() {
    const user = await window.shiyigeAuth?.fetchCurrentUser?.({ allowRefresh: true });
    if (!user) {
      updateCartCountBadge(0);
      return null;
    }

    try {
      return await fetchCart();
    } catch (error) {
      updateCartCountBadge(0);
      return null;
    }
  }

  async function ensureCartUser() {
    const user = await window.shiyigeAuth?.fetchCurrentUser?.({ allowRefresh: true });
    if (user) {
      return user;
    }

    if (typeof showNotification === "function") {
      showNotification("请先登录后使用购物车", "warning");
    }
    window.location.href = "login.html";
    return null;
  }

  async function resolveDefaultSku(productId) {
    const payload = await window.shiyigeApi.get(`/products/${productId}`);
    const product = payload?.data?.product;
    const sku = (product?.skus || []).find((item) => item.is_default) || product?.skus?.[0];

    if (!product || !sku) {
      throw new Error("sku not found");
    }

    return { product, sku };
  }

  async function addItem({ productId, skuId, quantity = 1, productName = "" }) {
    const user = await ensureCartUser();
    if (!user) return null;

    try {
      const payload = await window.shiyigeApi.post("/cart/items", {
        product_id: Number(productId),
        sku_id: Number(skuId),
        quantity: Number(quantity),
      });
      const cart = payload?.data?.cart;
      updateCartCountBadge(cart?.total_quantity || 0);

      if (typeof showNotification === "function") {
        showNotification(
          `已将 ${productName || payload?.data?.item?.product?.name || "商品"} 添加到购物车`,
          "success"
        );
      }
      return payload?.data || null;
    } catch (error) {
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "加入购物车失败", "error");
      }
      return null;
    }
  }

  function renderCartPage(cart) {
    const cartItemsBody = document.getElementById("cart-items-body");
    const emptyCart = document.getElementById("empty-cart");
    const cartItems = document.getElementById("cart-items");
    const cartSummary = document.getElementById("cart-summary");
    if (!cartItemsBody || !emptyCart || !cartItems || !cartSummary) return;

    const items = cart?.items || [];
    cartItemsBody.innerHTML = "";

    if (items.length === 0) {
      emptyCart.classList.remove("d-none");
      cartItems.classList.add("d-none");
      cartSummary.classList.add("d-none");
      updateCartTotal();
      return;
    }

    emptyCart.classList.add("d-none");
    cartItems.classList.remove("d-none");
    cartSummary.classList.remove("d-none");

    cartItemsBody.innerHTML = items
      .map(
        (item) => `
          <tr class="cart-item" data-item-id="${item.id}">
            <td>
              <div class="form-check">
                <input class="form-check-input cart-item-check" type="checkbox" data-item-id="${item.id}" checked />
              </div>
            </td>
            <td>
              <div class="cart-product">
                <img src="${item.product.cover_url || "images/logo.svg"}" alt="${item.product.name}" />
                <div class="cart-product-info">
                  <h5 class="cart-product-name">${item.product.name}</h5>
                  <span class="text-muted">${item.product.category || ""}</span>
                </div>
              </div>
            </td>
            <td>${formatPrice(Number(item.sku.price || 0))}</td>
            <td>
              <div class="input-group cart-quantity-group">
                <button type="button" class="btn btn-outline-secondary cart-quantity-decrease" data-item-id="${item.id}">-</button>
                <input
                  type="number"
                  class="form-control cart-quantity"
                  value="${item.quantity}"
                  min="1"
                  data-item-id="${item.id}"
                />
                <button type="button" class="btn btn-outline-secondary cart-quantity-increase" data-item-id="${item.id}">+</button>
              </div>
            </td>
            <td class="cart-item-subtotal" data-subtotal="${Number(item.subtotal || 0)}">
              ${formatPrice(Number(item.subtotal || 0))}
            </td>
            <td>
              <button type="button" class="btn btn-sm btn-danger cart-item-remove" data-item-id="${item.id}">
                <i class="fas fa-trash"></i>
              </button>
            </td>
          </tr>
        `
      )
      .join("");

    bindCartPageEvents();
    updateCartTotal();
  }

  function updateCartTotal() {
    const subtotal = Array.from(document.querySelectorAll(".cart-item-check:checked")).reduce(
      (sum, checkbox) => {
        const itemId = checkbox.dataset.itemId;
        const subtotalElement = document.querySelector(
          `.cart-item[data-item-id="${itemId}"] .cart-item-subtotal`
        );
        return sum + Number.parseFloat(subtotalElement?.dataset.subtotal || "0");
      },
      0
    );

    const shipping = subtotal > 0 ? 10 : 0;
    document.getElementById("cart-subtotal").textContent = formatPrice(subtotal);
    document.getElementById("cart-shipping").textContent = formatPrice(shipping);
    document.getElementById("cart-total").textContent = formatPrice(subtotal + shipping);

    const checkoutButton = document.getElementById("checkout-btn");
    if (checkoutButton) {
      checkoutButton.classList.toggle("disabled", subtotal === 0);
      checkoutButton.setAttribute("aria-disabled", subtotal === 0 ? "true" : "false");
    }
  }

  async function updateCartItemQuantity(itemId, quantity) {
    const normalizedQuantity = Math.max(1, Number.parseInt(quantity || "1", 10) || 1);

    try {
      const payload = await window.shiyigeApi.put(`/cart/items/${itemId}`, {
        quantity: normalizedQuantity,
      });
      renderCartPage(payload?.data?.cart);
      updateCartCountBadge(payload?.data?.cart?.total_quantity || 0);
    } catch (error) {
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "购物车更新失败", "error");
      }
      void loadCartPage();
    }
  }

  async function removeCartItem(itemId) {
    try {
      const payload = await window.shiyigeApi.delete(`/cart/items/${itemId}`);
      renderCartPage(payload?.data?.cart);
      updateCartCountBadge(payload?.data?.cart?.total_quantity || 0);
    } catch (error) {
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "购物车删除失败", "error");
      }
    }
  }

  function bindCartPageEvents() {
    document.getElementById("select-all")?.addEventListener("change", function () {
      const isChecked = this.checked;
      document.querySelectorAll(".cart-item-check").forEach((checkbox) => {
        checkbox.checked = isChecked;
      });
      updateCartTotal();
    });

    document.querySelectorAll(".cart-item-check").forEach((checkbox) => {
      checkbox.addEventListener("change", updateCartTotal);
    });

    document.querySelectorAll(".cart-quantity-decrease").forEach((button) => {
      button.addEventListener("click", function () {
        const input = document.querySelector(
          `.cart-quantity[data-item-id="${this.dataset.itemId}"]`
        );
        const nextQuantity = Math.max(
          1,
          (Number.parseInt(input?.value || "1", 10) || 1) - 1
        );
        void updateCartItemQuantity(this.dataset.itemId, nextQuantity);
      });
    });

    document.querySelectorAll(".cart-quantity-increase").forEach((button) => {
      button.addEventListener("click", function () {
        const input = document.querySelector(
          `.cart-quantity[data-item-id="${this.dataset.itemId}"]`
        );
        const nextQuantity = (Number.parseInt(input?.value || "1", 10) || 1) + 1;
        void updateCartItemQuantity(this.dataset.itemId, nextQuantity);
      });
    });

    document.querySelectorAll(".cart-quantity").forEach((input) => {
      input.addEventListener("change", function () {
        void updateCartItemQuantity(this.dataset.itemId, this.value);
      });
    });

    document.querySelectorAll(".cart-item-remove").forEach((button) => {
      button.addEventListener("click", function () {
        void removeCartItem(this.dataset.itemId);
      });
    });
  }

  async function loadCartPage() {
    const cartPage = document.getElementById("cart-items-body");
    if (!cartPage) return;

    const user = await ensureCartUser();
    if (!user) return;

    try {
      const cart = await fetchCart();
      renderCartPage(cart);
    } catch (error) {
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "购物车加载失败", "error");
      }
    }
  }

  function bindAddToCartButtons() {
    document.querySelectorAll(".add-to-cart a").forEach((button) => {
      button.addEventListener("click", async function (event) {
        const href = this.getAttribute("href") || "";
        const productCard = this.closest(".product-card");
        const productId =
          Number.parseInt(productCard?.dataset.productId || "", 10) || parseProductIdFromHref(href);

        if (!productId) {
          return;
        }

        event.preventDefault();

        try {
          const resolved = await resolveDefaultSku(productId);
          await addItem({
            productId,
            skuId: resolved.sku.id,
            quantity: 1,
            productName:
              productCard?.querySelector(".product-name")?.textContent?.trim() || resolved.product.name,
          });
        } catch (error) {
          if (typeof showNotification === "function") {
            showNotification("商品规格加载失败", "error");
          }
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.querySelector(".add-to-cart a")) {
      bindAddToCartButtons();
    }
    void loadCartPage();
    void refreshCartCount();
  });

  window.shiyigeCart = {
    addItem,
    loadCartPage,
    refreshCartCount,
  };
})();
