/* 拾遗阁 - 商品详情页脚本 */

(function () {
  const REVIEW_PAGE_SIZE = 2;
  let currentProduct = null;
  let currentReviewPage = 0;
  let loadedReviewCount = 0;
  let totalReviewCount = 0;
  let reviewRequestSerial = 0;

  function getProductIdFromUrl() {
    const rawProductId = new URLSearchParams(window.location.search).get("id");
    const productId = Number.parseInt(rawProductId || "", 10);

    if (!Number.isInteger(productId) || productId <= 0) {
      return null;
    }

    return productId;
  }

  function getDefaultSku(product) {
    return product.skus.find((sku) => sku.is_default) || product.skus[0] || null;
  }

  function getProductStock(product) {
    const sku = getDefaultSku(product);
    return sku?.inventory || 0;
  }

  function getProductImageUrls(product) {
    const mediaUrls = (product.media || [])
      .filter((media) => media.media_type === "image" && media.url)
      .map((media) => media.url);

    if (mediaUrls.length > 0) {
      return mediaUrls;
    }

    return product.cover_url ? [product.cover_url] : ["images/logo.svg"];
  }

  function clampQuantity() {
    const quantityInput = document.getElementById("quantity");
    if (!quantityInput) return;

    const maxStock = Number.parseInt(quantityInput.max || "1", 10);
    let quantity = Number.parseInt(quantityInput.value || "1", 10);

    if (!Number.isInteger(quantity) || quantity < 1) {
      quantity = 1;
    }

    if (maxStock > 0) {
      quantity = Math.min(quantity, maxStock);
    }

    quantityInput.value = String(quantity);
  }

  function initQuantityControls() {
    const quantityInput = document.getElementById("quantity");
    if (!quantityInput) return;

    document.querySelectorAll("[data-quantity-step]").forEach((button) => {
      button.addEventListener("click", function () {
        const step = Number.parseInt(this.dataset.quantityStep || "0", 10);
        const currentQuantity = Number.parseInt(quantityInput.value || "1", 10) || 1;
        quantityInput.value = String(currentQuantity + step);
        clampQuantity();
      });
    });

    quantityInput.addEventListener("change", clampQuantity);
  }

  function initMagnifier() {
    const container = document.querySelector(".magnifier-container");
    const mainImage = document.getElementById("mainImage");
    const lens = document.querySelector(".magnifier-lens");
    if (!container || !mainImage || !lens) return;

    if (window.matchMedia("(max-width: 768px)").matches) {
      lens.style.display = "none";
      return;
    }

    lens.style.display = "block";

    container.addEventListener("mousemove", function (event) {
      if (!mainImage.src) return;

      const rect = container.getBoundingClientRect();
      const lensWidth = 150;
      const lensHeight = 150;
      const zoomFactor = 2;
      const mouseX = event.clientX - rect.left;
      const mouseY = event.clientY - rect.top;

      let lensLeft = mouseX - lensWidth / 2;
      let lensTop = mouseY - lensHeight / 2;

      lensLeft = Math.max(0, Math.min(lensLeft, rect.width - lensWidth));
      lensTop = Math.max(0, Math.min(lensTop, rect.height - lensHeight));

      lens.style.width = `${lensWidth}px`;
      lens.style.height = `${lensHeight}px`;
      lens.style.left = `${lensLeft}px`;
      lens.style.top = `${lensTop}px`;
      lens.style.backgroundImage = `url(${mainImage.src})`;
      lens.style.backgroundSize = `${rect.width * zoomFactor}px ${
        rect.height * zoomFactor
      }px`;
      lens.style.backgroundPosition = `-${lensLeft * zoomFactor}px -${
        lensTop * zoomFactor
      }px`;
      lens.style.opacity = "1";
    });

    container.addEventListener("mouseleave", function () {
      lens.style.opacity = "0";
    });
  }

  function renderProductImages(product) {
    const mainImage = document.getElementById("mainImage");
    const thumbsContainer = document.getElementById("product-thumbs");
    if (!mainImage || !thumbsContainer) return;

    const imageUrls = getProductImageUrls(product);
    mainImage.src = imageUrls[0];
    mainImage.alt = product.name;

    thumbsContainer.innerHTML = imageUrls
      .map(
        (imageUrl, index) => `
          <img
            src="${imageUrl}"
            alt="${product.name} - 图片${index + 1}"
            class="product-thumb${index === 0 ? " active" : ""}"
            data-img="${imageUrl}"
          />
        `
      )
      .join("");

    thumbsContainer.querySelectorAll(".product-thumb").forEach((thumb) => {
      thumb.addEventListener("click", function () {
        mainImage.src = this.dataset.img;
        mainImage.alt = product.name;
        thumbsContainer.querySelectorAll(".product-thumb").forEach((item) => {
          item.classList.remove("active");
        });
        this.classList.add("active");
      });
    });
  }

  function renderSpecs(product) {
    const specsContainer = document.getElementById("product-specs");
    if (!specsContainer) return;

    const specs = [
      ["商品副标题", product.subtitle],
      ["类目", product.category?.name],
      ["形制风格", product.dynasty_style],
      ["工艺类型", product.craft_type],
      ["节令标签", product.festival_tag],
      ["适用场景", product.scene_tag],
      ["标签", (product.tags || []).join(" / ")],
    ].filter(([, value]) => value);

    specsContainer.innerHTML = specs
      .map(
        ([key, value]) => `
          <tr>
            <th>${key}</th>
            <td>${value}</td>
          </tr>
        `
      )
      .join("");
  }

  function renderProduct(product) {
    const stock = getProductStock(product);
    const defaultSku = getDefaultSku(product);
    const quantityInput = document.getElementById("quantity");
    const submitButton = document.querySelector('#add-to-cart-form button[type="submit"]');
    const memberPriceValue = document.querySelector("#member-price .text-danger");

    document.getElementById("product-name").textContent = product.name;
    document.getElementById("product-price").textContent = formatPrice(Number(product.price));
    document.getElementById("product-category").textContent = product.category?.name || "-";
    document.getElementById("product-stock").textContent = String(stock);
    document.getElementById("product-description").textContent = product.description || "暂无介绍";
    document.getElementById("product-culture").textContent =
      product.culture_summary || "暂无文化背景介绍";
    document.getElementById("product-id").value = String(product.id);
    document.title = `拾遗阁 - ${product.name}`;

    if (memberPriceValue) {
      memberPriceValue.textContent = defaultSku?.member_price
        ? formatPrice(Number(defaultSku.member_price))
        : "-";
    }

    if (quantityInput) {
      quantityInput.max = String(Math.max(stock, 1));
      quantityInput.value = stock > 0 ? "1" : "0";
      quantityInput.disabled = stock <= 0;
    }

    if (submitButton) {
      submitButton.disabled = stock <= 0;
      submitButton.innerHTML =
        stock > 0
          ? '<i class="fas fa-shopping-cart me-2"></i> 加入购物车'
          : '<i class="fas fa-ban me-2"></i> 暂无库存';
    }

    renderProductImages(product);
    renderSpecs(product);
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
            <div class="product-price">${formatPrice(Number(product.price))}</div>
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

  function buildStarIcons(rating, { allowHalf = false } = {}) {
    const numericRating = Number(rating) || 0;
    const clampedRating = Math.max(0, Math.min(numericRating, 5));
    const normalizedRating = allowHalf
      ? Math.round(clampedRating * 2) / 2
      : Math.round(clampedRating);
    const fullStarCount = Math.floor(normalizedRating);
    const halfStarCount = allowHalf && normalizedRating % 1 !== 0 ? 1 : 0;
    const emptyStarCount = Math.max(0, 5 - fullStarCount - halfStarCount);

    return [
      '<i class="fas fa-star"></i>'.repeat(fullStarCount),
      halfStarCount ? '<i class="fas fa-star-half-alt"></i>' : "",
      '<i class="far fa-star"></i>'.repeat(emptyStarCount),
    ].join("");
  }

  function buildRatingBars(total, ratingCounts = {}) {
    return [5, 4, 3, 2, 1]
      .map((star) => {
        const count = Number(ratingCounts[String(star)] || 0);
        const percentage = total > 0 ? Math.round((count / total) * 100) : 0;

        return `
          <div class="rating-bar-item" data-rating="${star}">
            <span>${star}星</span>
            <div class="progress">
              <div
                class="progress-bar"
                role="progressbar"
                style="width: ${percentage}%"
                aria-valuenow="${percentage}"
                aria-valuemin="0"
                aria-valuemax="100"
              ></div>
            </div>
            <span>${count}</span>
          </div>
        `;
      })
      .join("");
  }

  function formatAverageRating(averageRating) {
    return (Number(averageRating) || 0).toFixed(1);
  }

  function formatReviewDate(reviewDate) {
    if (!reviewDate) {
      return "-";
    }

    return String(reviewDate).split("T")[0];
  }

  function getReviewerAvatarUrl(reviewerName) {
    const name = reviewerName || "匿名用户";
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random`;
  }

  function renderReviewLoadingState() {
    const averageRating = document.getElementById("reviews-average-rating");
    const averageStars = document.getElementById("reviews-average-stars");
    const totalCopy = document.getElementById("reviews-total-copy");
    const ratingBars = document.getElementById("reviews-rating-bars");
    const reviewsContainer = document.getElementById("reviews-container");
    const loadMoreWrapper = document.getElementById("reviews-load-more-wrapper");

    if (averageRating) {
      averageRating.textContent = "--";
    }

    if (averageStars) {
      averageStars.innerHTML = '<i class="far fa-star"></i>'.repeat(5);
    }

    if (totalCopy) {
      totalCopy.textContent = "评价加载中...";
    }

    if (ratingBars) {
      ratingBars.innerHTML = buildRatingBars(0);
    }

    if (reviewsContainer) {
      reviewsContainer.innerHTML =
        '<div class="alert alert-light review-empty mb-0">评价加载中...</div>';
    }

    if (loadMoreWrapper) {
      loadMoreWrapper.classList.add("d-none");
    }
  }

  function renderReviewStats(stats) {
    const averageRating = document.getElementById("reviews-average-rating");
    const averageStars = document.getElementById("reviews-average-stars");
    const totalCopy = document.getElementById("reviews-total-copy");
    const ratingBars = document.getElementById("reviews-rating-bars");
    const total = Number(stats?.total || 0);
    const average = Number(stats?.average_rating || 0);
    const ratingCounts = stats?.rating_counts || {};

    if (averageRating) {
      averageRating.textContent = formatAverageRating(average);
    }

    if (averageStars) {
      averageStars.innerHTML = buildStarIcons(average, { allowHalf: true });
    }

    if (totalCopy) {
      totalCopy.textContent = total > 0 ? `基于 ${total} 条评价` : "当前商品还没有评价";
    }

    if (ratingBars) {
      ratingBars.innerHTML = buildRatingBars(total, ratingCounts);
    }
  }

  function createReviewItem(review) {
    const reviewElement = document.createElement("div");
    const header = document.createElement("div");
    const reviewerInfo = document.createElement("div");
    const avatar = document.createElement("img");
    const reviewerMeta = document.createElement("div");
    const reviewerName = document.createElement("h5");
    const reviewStars = document.createElement("div");
    const reviewDate = document.createElement("div");
    const reviewContent = document.createElement("div");
    const contentParagraph = document.createElement("p");
    const displayName = review.reviewer_name || "匿名用户";

    reviewElement.className = "review-item";
    reviewElement.dataset.reviewId = String(review.id);

    header.className = "review-header";
    reviewerInfo.className = "reviewer-info";
    avatar.className = "reviewer-avatar";
    avatar.src = getReviewerAvatarUrl(displayName);
    avatar.alt = `${displayName}头像`;

    reviewerName.className = "reviewer-name";
    reviewerName.textContent = displayName;

    reviewStars.className = "review-stars";
    reviewStars.innerHTML = buildStarIcons(review.rating);

    reviewerMeta.appendChild(reviewerName);
    reviewerMeta.appendChild(reviewStars);
    reviewerInfo.appendChild(avatar);
    reviewerInfo.appendChild(reviewerMeta);

    reviewDate.className = "review-date";
    reviewDate.textContent = formatReviewDate(review.created_at);

    header.appendChild(reviewerInfo);
    header.appendChild(reviewDate);

    reviewContent.className = "review-content";
    contentParagraph.textContent = review.content || "用户未填写评价内容";
    reviewContent.appendChild(contentParagraph);

    if ((review.image_urls || []).length > 0) {
      const reviewImages = document.createElement("div");
      reviewImages.className = "review-images";

      review.image_urls.forEach((imageUrl, index) => {
        if (!imageUrl) {
          return;
        }

        const image = document.createElement("img");
        image.src = imageUrl;
        image.alt = `${displayName}的评价图片 ${index + 1}`;
        image.loading = "lazy";
        image.addEventListener("click", function () {
          showFullImage(imageUrl);
        });
        reviewImages.appendChild(image);
      });

      if (reviewImages.childElementCount > 0) {
        reviewContent.appendChild(reviewImages);
      }
    }

    reviewElement.appendChild(header);
    reviewElement.appendChild(reviewContent);

    return reviewElement;
  }

  function renderReviewList(reviews, { append = false } = {}) {
    const reviewsContainer = document.getElementById("reviews-container");
    if (!reviewsContainer) return;

    if (!append) {
      reviewsContainer.innerHTML = "";
    }

    if (!Array.isArray(reviews) || reviews.length === 0) {
      if (!append) {
        reviewsContainer.innerHTML =
          '<div class="alert alert-light review-empty mb-0">当前商品还没有评价，欢迎成为第一位晒单用户。</div>';
      }
      return;
    }

    if (reviewsContainer.querySelector(".review-empty")) {
      reviewsContainer.innerHTML = "";
    }

    reviews.forEach((review) => {
      reviewsContainer.appendChild(createReviewItem(review));
    });
  }

  function updateLoadMoreButton() {
    const button = document.getElementById("load-more-reviews-btn");
    const wrapper = document.getElementById("reviews-load-more-wrapper");
    if (!button || !wrapper) return;

    const hasMore = loadedReviewCount < totalReviewCount;

    wrapper.classList.toggle("d-none", !hasMore);
    button.disabled = false;
    button.textContent = "查看更多评价";
  }

  async function fetchReviewsPage(productId, page) {
    const payload = await window.shiyigeApi.get(
      `/api/v1/products/${productId}/reviews?page=${page}&page_size=${REVIEW_PAGE_SIZE}`
    );
    return payload.data;
  }

  async function loadReviewSection(productId) {
    const requestId = ++reviewRequestSerial;

    currentReviewPage = 0;
    loadedReviewCount = 0;
    totalReviewCount = 0;
    renderReviewLoadingState();

    try {
      const [statsPayload, listData] = await Promise.all([
        window.shiyigeApi.get(`/api/v1/products/${productId}/reviews/stats`),
        fetchReviewsPage(productId, 1),
      ]);

      if (requestId !== reviewRequestSerial) {
        return;
      }

      const reviewStats = statsPayload.data || {};
      const reviewItems = listData.items || [];
      totalReviewCount = Number(listData.total ?? reviewStats.total) || 0;
      loadedReviewCount = reviewItems.length;
      currentReviewPage = reviewItems.length > 0 ? 1 : 0;

      renderReviewStats({
        ...reviewStats,
        total: totalReviewCount,
      });
      renderReviewList(reviewItems);
      updateLoadMoreButton();
    } catch (error) {
      if (requestId !== reviewRequestSerial) {
        return;
      }

      renderReviewStats({
        total: 0,
        average_rating: 0,
        rating_counts: {},
      });
      renderReviewList([], { append: false });

      const reviewsContainer = document.getElementById("reviews-container");
      if (reviewsContainer) {
        reviewsContainer.innerHTML =
          '<div class="alert alert-warning review-empty mb-0">评价加载失败，请稍后重试。</div>';
      }

      updateLoadMoreButton();
    }
  }

  async function loadRelatedProducts(product) {
    const relatedContainer = document.getElementById("related-products");
    const relatedCopy = document.getElementById("related-products-copy");
    if (!relatedContainer) return;

    try {
      const payload = await window.shiyigeApi.get(
        `/api/v1/products/${product.id}/related?limit=3`
      );
      const relatedProducts = payload.data.items || [];

      if (relatedProducts.length === 0) {
        relatedContainer.innerHTML =
          '<div class="col-12"><div class="alert alert-light">暂无相关推荐</div></div>';
        if (relatedCopy) {
          relatedCopy.textContent = "当前商品暂时没有可展示的相似推荐。";
        }
        return;
      }

      if (relatedCopy) {
        relatedCopy.textContent = "根据当前商品的类目、工艺和文化特征推荐相似商品。";
      }
      relatedContainer.innerHTML = relatedProducts.map(renderProductCard).join("");
    } catch (error) {
      relatedContainer.innerHTML =
        '<div class="col-12"><div class="alert alert-warning">相关推荐加载失败</div></div>';
      if (relatedCopy) {
        relatedCopy.textContent = "相关推荐暂时不可用，请稍后重试。";
      }
    }
  }

  function renderError(message) {
    const productContainer = document.getElementById("product-container");
    if (!productContainer) return;

    productContainer.innerHTML = `
      <div class="alert alert-warning">
        ${message}
      </div>
    `;
  }

  async function addCurrentProductToCart(quantity) {
    if (!currentProduct) return false;

    const currentUser = await window.shiyigeAuth?.fetchCurrentUser?.({
      allowRefresh: true,
    });
    if (!currentUser) {
      showNotification("请先登录后再加入购物车", "warning");
      window.location.href = "login.html";
      return false;
    }

    const defaultSku = getDefaultSku(currentProduct);
    if (!defaultSku) {
      showNotification("当前商品暂无可用规格", "error");
      return false;
    }

    try {
      await window.shiyigeApi.post("/cart/items", {
        product_id: currentProduct.id,
        sku_id: defaultSku.id,
        quantity,
      });
      await window.updateNavigation?.();
      return true;
    } catch (error) {
      showNotification(error?.payload?.message || "商品加入购物车失败", "error");
      return false;
    }
  }

  function bindAddToCartForm() {
    const form = document.getElementById("add-to-cart-form");
    const quantityInput = document.getElementById("quantity");
    if (!form || !quantityInput) return;

    form.addEventListener("submit", async function (event) {
      event.preventDefault();

      if (!currentProduct) {
        showNotification("商品信息尚未加载完成", "error");
        return;
      }

      clampQuantity();
      const quantity = Number.parseInt(quantityInput.value || "1", 10);
      const stock = getProductStock(currentProduct);

      if (!Number.isInteger(quantity) || quantity < 1) {
        showNotification("请选择正确的购买数量", "error");
        return;
      }

      if (quantity > stock) {
        showNotification("库存不足，请调整购买数量", "error");
        quantityInput.value = String(stock);
        return;
      }

      const succeeded = await addCurrentProductToCart(quantity);
      if (succeeded) {
        showNotification("商品已成功加入购物车", "success");
      }
    });
  }

  function showFullImage(imageSrc) {
    const modal = document.createElement("div");
    modal.className = "image-preview-modal";
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.9);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
      cursor: zoom-out;
    `;

    const image = document.createElement("img");
    image.src = imageSrc;
    image.style.cssText = `
      max-width: 90%;
      max-height: 90%;
      object-fit: contain;
    `;

    modal.appendChild(image);
    modal.addEventListener("click", function () {
      modal.remove();
    });

    document.body.appendChild(modal);
  }

  async function loadMoreReviews() {
    const button = document.getElementById("load-more-reviews-btn");
    if (!button || !currentProduct) return;

    if (loadedReviewCount >= totalReviewCount) {
      updateLoadMoreButton();
      return;
    }

    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 加载中...';

    try {
      const nextPage = currentReviewPage + 1;
      const listData = await fetchReviewsPage(currentProduct.id, nextPage);
      const reviewItems = listData.items || [];

      totalReviewCount = Number(listData.total ?? totalReviewCount) || totalReviewCount;

      if (reviewItems.length > 0) {
        currentReviewPage = nextPage;
        loadedReviewCount += reviewItems.length;
        renderReviewList(reviewItems, { append: true });
      } else {
        loadedReviewCount = totalReviewCount;
      }

      updateLoadMoreButton();
    } catch (error) {
      button.disabled = false;
      button.textContent = "查看更多评价";
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "评价加载失败", "error");
      }
    }
  }

  function bindReviewControls() {
    document
      .getElementById("load-more-reviews-btn")
      ?.addEventListener("click", function () {
        void loadMoreReviews();
      });
  }

  async function loadProductPage() {
    const productId = getProductIdFromUrl();

    if (!productId) {
      renderError("缺少有效的商品 ID");
      return;
    }

    try {
      const payload = await window.shiyigeApi.get(`/api/v1/products/${productId}`);
      currentProduct = payload.data.product;
      renderProduct(currentProduct);
      await Promise.all([
        loadRelatedProducts(currentProduct),
        loadReviewSection(currentProduct.id),
      ]);
    } catch (error) {
      renderError(error?.payload?.message || "商品详情加载失败");
      showNotification(error?.payload?.message || "商品详情加载失败", "error");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    initQuantityControls();
    initMagnifier();
    bindAddToCartForm();
    bindReviewControls();
    void loadProductPage();
  });
})();
