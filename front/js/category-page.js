/* 拾遗阁 - 分类页数据接线 */

(function () {
  let categoryMap = new Map();
  let latestLoadToken = 0;

  function buildPath(state) {
    const params = new URLSearchParams();
    const basePath = state.search ? "/search" : "/products";
    if (state.search) params.set("q", state.search);
    if (state.categoryId) params.set("category_id", state.categoryId);
    if (state.minPrice) params.set("min_price", state.minPrice);
    if (state.maxPrice) params.set("max_price", state.maxPrice);
    if (state.sort) params.set("sort", state.sort);
    params.set("page", "1");
    params.set("page_size", "50");
    return `${basePath}?${params.toString()}`;
  }

  function isSemanticSearch(state) {
    return Boolean(state.search) && state.searchMode === "semantic";
  }

  function renderReason(product) {
    if (!product.reason) {
      return "";
    }

    return `<p class="text-muted small mt-2 mb-0 recommendation-reason">${product.reason}</p>`;
  }

  function renderCategoryLinks(categories, activeCategoryId) {
    const list = document.querySelector(".filter-list");
    if (!list) return;

    const items = [
      `<li><a href="#" data-category="" class="${!activeCategoryId ? "active" : ""}">全部商品</a></li>`,
      ...categories.map(
        (category) =>
          `<li><a href="#" data-category="${category.id}" class="${
            String(activeCategoryId) === String(category.id) ? "active" : ""
          }">${category.name}</a></li>`
      ),
    ];
    list.innerHTML = items.join("");
  }

  function renderProductCard(product) {
    return `
      <div class="col-md-4 mb-4 animate-on-scroll product-item" data-product-id="${product.id}">
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
            ${renderReason(product)}
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

  function updateHeader(state) {
    const categoryName = document.getElementById("category-name");
    const categoryDescription = document.getElementById("category-description");
    if (!categoryName || !categoryDescription) return;

    if (isSemanticSearch(state)) {
      categoryName.textContent = `语义搜索：${state.search}`;
      categoryDescription.textContent = "以下商品来自语义搜索结果，并展示命中特征说明。";
      return;
    }

    if (state.search) {
      categoryName.textContent = `搜索：${state.search}`;
      categoryDescription.textContent = "以下商品来自实时商品接口的关键词筛选结果。";
      return;
    }

    if (state.categoryId && categoryMap.has(String(state.categoryId))) {
      const category = categoryMap.get(String(state.categoryId));
      categoryName.textContent = category.name;
      categoryDescription.textContent = category.description || "该类目的精选商品。";
      return;
    }

    categoryName.textContent = "全部商品";
    categoryDescription.textContent = "在这里您可以找到各种精选商品。";
  }

  function syncSearchControls(state) {
    const searchInput = document.getElementById("catalog-search-input");
    const searchModeSelect = document.getElementById("search-mode-select");
    const searchModeTip = document.getElementById("search-mode-tip");
    const sortSelect = document.getElementById("sort-select");

    if (searchInput) {
      searchInput.value = state.search;
    }
    if (searchModeSelect) {
      searchModeSelect.value = state.searchMode;
    }
    document.querySelectorAll(".search-input").forEach((input) => {
      input.value = state.search;
    });

    const semanticMode = state.searchMode === "semantic";
    if (sortSelect) {
      sortSelect.disabled = semanticMode;
    }
    if (searchModeTip) {
      searchModeTip.textContent = semanticMode
        ? "语义搜索支持自然语言描述，排序将按语义相关度固定展示。"
        : "关键词搜索会走实时搜索接口，可继续使用价格与排序筛选。";
    }
  }

  function updateHistory(state) {
    const url = new URL(window.location.href);
    if (state.categoryId) {
      url.searchParams.set("id", state.categoryId);
    } else {
      url.searchParams.delete("id");
    }
    if (state.search) {
      url.searchParams.set("search", state.search);
    } else {
      url.searchParams.delete("search");
    }
    if (state.searchMode === "semantic" && state.search) {
      url.searchParams.set("mode", "semantic");
    } else {
      url.searchParams.delete("mode");
    }
    history.replaceState({}, "", url);
  }

  async function fetchProducts(state) {
    if (isSemanticSearch(state)) {
      return window.shiyigeApi.post("/api/v1/search/semantic", {
        query: state.search,
        limit: 20,
        category_id: state.categoryId ? Number.parseInt(state.categoryId, 10) : undefined,
        min_price: state.minPrice || undefined,
        max_price: state.maxPrice || undefined,
      });
    }

    return window.shiyigeApi.get(`/api/v1${buildPath(state)}`);
  }

  async function loadCategoryPage(state) {
    const productsContainer = document.getElementById("products-container");
    const emptyState = document.getElementById("empty-state");
    if (!productsContainer || !emptyState) return;
    const loadToken = ++latestLoadToken;

    updateHeader(state);
    syncSearchControls(state);

    try {
      const payload = await fetchProducts(state);
      if (loadToken !== latestLoadToken) {
        return;
      }
      const items = payload.data.items || [];
      productsContainer.innerHTML = items.map(renderProductCard).join("");
      emptyState.classList.toggle("d-none", items.length > 0);
    } catch (error) {
      if (loadToken !== latestLoadToken) {
        return;
      }
      productsContainer.innerHTML = "";
      emptyState.classList.remove("d-none");
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "商品列表加载失败", "error");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", async function () {
    const urlParams = new URLSearchParams(window.location.search);
    const state = {
      categoryId: urlParams.get("id") || "",
      search: urlParams.get("search") || "",
      searchMode: urlParams.get("mode") === "semantic" ? "semantic" : "keyword",
      minPrice: "",
      maxPrice: "",
      sort: "default",
    };

    syncSearchControls(state);

    document.addEventListener("click", function (event) {
      const target = event.target.closest("[data-category]");
      if (!target) return;
      event.preventDefault();
      state.categoryId = target.getAttribute("data-category") || "";
      state.search = "";
      state.searchMode = "keyword";
      renderCategoryLinks(Array.from(categoryMap.values()), state.categoryId);
      updateHistory(state);
      void loadCategoryPage(state);
    });

    document.getElementById("price-filter-form")?.addEventListener("submit", function (event) {
      event.preventDefault();
      state.minPrice = document.getElementById("min_price").value.trim();
      state.maxPrice = document.getElementById("max_price").value.trim();
      state.sort =
        state.searchMode === "semantic"
          ? "default"
          : document.getElementById("sort-select").value;
      updateHistory(state);
      void loadCategoryPage(state);
    });

    document.getElementById("search-entry-form")?.addEventListener("submit", function (event) {
      event.preventDefault();
      state.search = document.getElementById("catalog-search-input").value.trim();
      state.searchMode = document.getElementById("search-mode-select").value;
      if (!state.search) {
        state.searchMode = "keyword";
      }
      if (state.searchMode === "semantic") {
        state.sort = "default";
      } else {
        state.sort = document.getElementById("sort-select").value;
      }
      updateHistory(state);
      void loadCategoryPage(state);
    });

    document.getElementById("search-mode-select")?.addEventListener("change", function (event) {
      state.searchMode = event.target.value;
      state.search = document.getElementById("catalog-search-input").value.trim();
      if (state.searchMode === "semantic") {
        state.sort = "default";
      }
      syncSearchControls(state);
    });

    void loadCategoryPage(state);

    try {
      const categoryPayload = await window.shiyigeApi.get("/api/v1/categories");
      const categories = categoryPayload.data.items || [];
      categoryMap = new Map(categories.map((category) => [String(category.id), category]));
      renderCategoryLinks(categories, state.categoryId);
    } catch (error) {
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "分类数据加载失败", "error");
      }
    }
  });
})();
