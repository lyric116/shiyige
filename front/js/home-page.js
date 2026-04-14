/* 拾遗阁 - 首页数据接线 */

(function () {
  function renderCategoryCard(category) {
    return `
      <div class="col-md-4 mb-4 animate-on-scroll">
        <div class="product-card" style="height: 100%">
          <div class="product-info">
            <h4 class="product-name">${category.name}</h4>
            <p>${category.description || "浏览该类目的精选商品。"}</p>
            <a href="category.html?id=${category.id}" class="btn btn-outline-primary category-browse-btn">浏览商品</a>
          </div>
        </div>
      </div>
    `;
  }

  function renderProductCard(product) {
    const recommendationReason = product.reason
      ? `<p class="text-muted small mt-2 mb-0 recommendation-reason">${product.reason}</p>`
      : "";

    return `
      <div class="col-lg-4 col-md-6 mb-4 animate-on-scroll">
        <div class="product-card">
          <div class="product-img">
            <img src="${product.cover_url || "images/logo.svg"}" alt="${product.name}" />
          </div>
          <div class="product-info">
            <div class="product-name-row">
              <h5 class="product-name">${product.name}</h5>
              <a href="product.html?id=${product.id}" class="btn btn-sm btn-outline-primary view-details-btn">查看详情</a>
            </div>
            <div class="product-price">¥${Number(product.price).toFixed(2)}</div>
            <div class="product-category">${product.category.name}</div>
            ${recommendationReason}
          </div>
          <div class="add-to-cart">
            <a href="product.html?id=${product.id}" class="text-white">
              <i class="fas fa-shopping-cart me-1"></i> 加入购物车
            </a>
          </div>
        </div>
      </div>
    `;
  }

  async function loadHomePageData() {
    const categoryContainer = document.getElementById("home-category-list");
    const featuredContainer = document.getElementById("home-featured-products");
    const recommendationTitle = document.getElementById("home-recommendation-title");
    const recommendationCopy = document.getElementById("home-recommendation-copy");
    if (!categoryContainer || !featuredContainer) return;

    try {
      const currentUser = await window.shiyigeAuth?.fetchCurrentUser?.({
        allowRefresh: true,
      });
      const categoryPayloadPromise = window.shiyigeApi.get("/api/v1/categories");
      let featuredPayload;

      if (currentUser) {
        try {
          featuredPayload = await window.shiyigeApi.get(
            "/api/v1/products/recommendations?limit=3"
          );
          if (recommendationTitle) {
            recommendationTitle.textContent = "猜你喜欢";
          }
          if (recommendationCopy) {
            recommendationCopy.textContent = "基于你近期浏览、搜索和加购行为生成个性化推荐。";
          }
        } catch (error) {
          featuredPayload = await window.shiyigeApi.get(
            "/api/v1/products?sort=newest&page=1&page_size=3"
          );
          if (recommendationTitle) {
            recommendationTitle.textContent = "猜你喜欢";
          }
          if (recommendationCopy) {
            recommendationCopy.textContent = "个性化推荐暂时不可用，当前展示最新上架商品。";
          }
        }
      } else {
        featuredPayload = await window.shiyigeApi.get(
          "/api/v1/products?sort=newest&page=1&page_size=3"
        );
        if (recommendationTitle) {
          recommendationTitle.textContent = "猜你喜欢";
        }
        if (recommendationCopy) {
          recommendationCopy.textContent = "登录后可查看个性化推荐，当前先展示最新上架商品。";
        }
      }

      const categoryPayload = await categoryPayloadPromise;

      categoryContainer.innerHTML = (categoryPayload.data.items || [])
        .map(renderCategoryCard)
        .join("");
      featuredContainer.innerHTML = (featuredPayload.data.items || [])
        .map(renderProductCard)
        .join("");
    } catch (error) {
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "首页数据加载失败", "error");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    void loadHomePageData();
  });
})();
