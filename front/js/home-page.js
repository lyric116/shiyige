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

  function renderProductCard(product, options = {}) {
    return (
      window.shiyigeRecommendationUI?.renderProductCard?.(product, {
        context: options.context || "home",
        defaultSourceType: options.defaultSourceType,
        wrapperClass: "col-lg-4 col-md-6 mb-4 animate-on-scroll",
      }) || ""
    );
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
      let featuredRenderOptions = {
        context: "home_guest",
        defaultSourceType: "new",
      };

      if (currentUser) {
        try {
          featuredPayload = await window.shiyigeApi.get(
            "/api/v1/products/recommendations?limit=3&slot=home&debug=true"
          );
          featuredRenderOptions = {
            context: "home",
            defaultSourceType: "personalized",
          };
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
          featuredRenderOptions = {
            context: "home_guest",
            defaultSourceType: "new",
          };
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
        featuredRenderOptions = {
          context: "home_guest",
          defaultSourceType: "new",
        };
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
        .map((product) => renderProductCard(product, featuredRenderOptions))
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
