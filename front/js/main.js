/* 拾遗阁 - 通用JS脚本 */

document.addEventListener("DOMContentLoaded", function () {
  // 初始化时钟显示
  initializeClock();

  // 导航栏高亮当前页面对应的链接
  highlightNavLink();

  // 初始化工具提示
  initializeTooltips();

  // 显示当前日期
  displayCurrentDate();

  // 监听所有返回顶部按钮
  initializeBackToTop();

  // 监听图片加载失败，使用占位图
  handleImageErrors();

  // 初始化动态效果
  initializeAnimations();
});

/**
 * 初始化时钟显示
 */
function initializeClock() {
  // 获取导航栏容器
  const navbarCollapse = document.querySelector(".navbar-collapse");
  const timeDisplay = document.createElement("div");
  timeDisplay.className = "time-display";
  timeDisplay.innerHTML =
    '<i class="fas fa-clock"></i><span id="current-time"></span>';

  // 将时钟插入到导航栏的最前面
  navbarCollapse.parentNode.insertBefore(timeDisplay, navbarCollapse);

  // 更新时钟显示
  function updateClock() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const date = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    const seconds = String(now.getSeconds()).padStart(2, "0");
    document.getElementById(
      "current-time"
    ).textContent = `${year}年${month}月${date}日 ${hours}:${minutes}:${seconds}`;
  }

  // 立即更新一次
  updateClock();

  // 每秒更新一次
  setInterval(updateClock, 1000);
}

/**
 * 高亮导航栏中当前页面对应的链接
 */
function highlightNavLink() {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll(".navbar-nav .nav-link");

  navLinks.forEach((link) => {
    const href = link.getAttribute("href");
    if (href === currentPath || (href !== "/" && currentPath.includes(href))) {
      link.classList.add("active");
    }
  });
}

/**
 * 初始化Bootstrap工具提示
 */
function initializeTooltips() {
  const tooltipTriggerList = document.querySelectorAll(
    '[data-bs-toggle="tooltip"]'
  );
  [...tooltipTriggerList].map(
    (tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl)
  );
}

/**
 * 显示当前日期
 */
function displayCurrentDate() {
  const dateElement = document.getElementById("current-date");
  if (dateElement) {
    const now = new Date();
    const options = {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "long",
    };
    dateElement.textContent = now.toLocaleDateString("zh-CN", options);
  }
}

/**
 * 初始化返回顶部按钮
 */
function initializeBackToTop() {
  const backToTopButtons = document.querySelectorAll(".back-to-top");

  backToTopButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    });
  });

  // 滚动时显示/隐藏返回顶部按钮
  window.addEventListener("scroll", function () {
    backToTopButtons.forEach((button) => {
      if (window.scrollY > 300) {
        button.classList.add("show");
      } else {
        button.classList.remove("show");
      }
    });
  });
}

/**
 * 处理图片加载错误
 */
function handleImageErrors() {
  const images = document.querySelectorAll("img");
  images.forEach((img) => {
    img.addEventListener("error", function () {
      // 替换为默认图片
      this.src = "/static/images/banner1.svg";
      this.alt = "图片加载失败";
    });
  });
}

/**
 * 初始化动画效果
 */
function initializeAnimations() {
  // 检测元素是否进入视口，添加动画类
  const animatedElements = document.querySelectorAll(".animate-on-scroll");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("animate-fade-in");
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.1,
    }
  );

  animatedElements.forEach((element) => {
    observer.observe(element);
  });
}

/**
 * 显示通知
 * @param {string} message - 通知信息
 * @param {string} type - 通知类型 (success, error, warning, info)
 * @param {number} duration - 显示时长(毫秒)
 */
function showNotification(message, type = "info", duration = 3000) {
  // 创建通知元素
  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.textContent = message;

  // 添加到页面
  document.body.appendChild(notification);

  // 显示通知
  setTimeout(() => {
    notification.classList.add("show");
  }, 10);

  // 设置自动隐藏
  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, duration);
}

/**
 * 格式化价格为人民币格式
 * @param {number} price - 价格
 * @returns {string} 格式化后的价格
 */
function formatPrice(price) {
  return "¥" + price.toFixed(2);
}

/**
 * 加载更多内容（用于无限滚动）
 * @param {Function} loadFunction - 加载内容的函数
 * @param {string} targetSelector - 目标容器选择器
 * @param {number} threshold - 触发阈值
 */
function initInfiniteScroll(loadFunction, targetSelector, threshold = 200) {
  let loading = false;
  let hasMore = true;

  window.addEventListener("scroll", function () {
    const target = document.querySelector(targetSelector);
    if (!target || loading || !hasMore) return;

    const rect = target.getBoundingClientRect();
    const bottomPosition = rect.bottom;
    const windowHeight = window.innerHeight;

    if (bottomPosition - windowHeight < threshold) {
      loading = true;

      // 显示加载指示器
      const loader = document.createElement("div");
      loader.className = "text-center my-3";
      loader.innerHTML = '<div class="loader"></div>';
      target.appendChild(loader);

      // 调用加载函数
      loadFunction()
        .then((result) => {
          // 移除加载指示器
          target.removeChild(loader);

          // 检查是否有更多内容
          hasMore = result.hasMore;
          loading = false;
        })
        .catch((error) => {
          console.error("加载更多内容失败:", error);
          target.removeChild(loader);
          loading = false;
        });
    }
  });
}

(function () {
  const SOURCE_LABELS = {
    personalized: "个性化",
    similar: "相似商品",
    hot: "热门",
    new: "新品探索",
    seasonal: "节令主题",
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

  function dedupeLabels(values) {
    const labels = [];
    for (const value of values || []) {
      const normalized = String(value || "").trim();
      if (!normalized || labels.includes(normalized)) {
        continue;
      }
      labels.push(normalized);
    }
    return labels;
  }

  function buildFallbackSourceType(options = {}) {
    if (options.defaultSourceType) {
      return options.defaultSourceType;
    }

    switch (options.context) {
      case "related":
      case "cart":
      case "order_complete":
        return "similar";
      case "home_guest":
        return "new";
      case "home":
      default:
        return "personalized";
    }
  }

  function inferSourceType(item, options = {}) {
    if (item?.source_type) {
      return item.source_type;
    }

    const reason = String(item?.reason || "");
    if (reason.includes("节令")) {
      return "seasonal";
    }

    return buildFallbackSourceType(options);
  }

  function buildSourceMeta(item, options = {}) {
    const type = inferSourceType(item, options);
    return {
      type,
      label: item?.source_label || SOURCE_LABELS[type] || SOURCE_LABELS.personalized,
    };
  }

  function buildSearchExplanations(item, options = {}) {
    if (Array.isArray(item?.explanations) && item.explanations.length > 0) {
      return dedupeLabels(item.explanations);
    }

    const reason = String(item?.reason || "");
    const mode = options.searchMode || item?.search_mode || "";
    const labels = [];

    if (mode === "semantic" || reason.includes("语义相关") || reason.includes("语义相近")) {
      labels.push("语义相关");
    }
    if (mode === "keyword" || reason.includes("关键词命中")) {
      labels.push("关键词命中");
    }
    if (
      reason.includes("文化标签") ||
      reason.includes("文化特征") ||
      reason.includes("特征")
    ) {
      labels.push("文化标签匹配");
    }
    if (reason.includes("ColBERT")) {
      labels.push("ColBERT 重排");
    }

    return dedupeLabels(labels);
  }

  function renderChips(labels, options = {}) {
    const normalized = dedupeLabels(labels);
    if (!normalized.length) {
      return "";
    }

    const tone = options.tone || "info";
    return normalized
      .map(function (label) {
        return `<span class="recommendation-chip recommendation-chip-${tone}">${escapeHtml(label)}</span>`;
      })
      .join("");
  }

  function renderEvidence(item, options = {}) {
    const sourceMeta = buildSourceMeta(item, options);
    const explanationLabels = buildSearchExplanations(item, options);
    const chips = [];

    if (!options.hideSource) {
      chips.push(
        `<span class="recommendation-chip recommendation-chip-source recommendation-chip-${escapeHtml(
          sourceMeta.type
        )}">${escapeHtml(sourceMeta.label)}</span>`
      );
    }
    if (explanationLabels.length > 0) {
      chips.push(renderChips(explanationLabels, { tone: "explanation" }));
    }

    const chipRow = chips.length
      ? `<div class="recommendation-chip-row">${chips.join("")}</div>`
      : "";
    const reason = item?.reason
      ? `<p class="recommendation-reason">${escapeHtml(item.reason)}</p>`
      : "";

    if (!chipRow && !reason) {
      return "";
    }

    return `
      <div class="recommendation-evidence">
        ${chipRow}
        ${reason}
      </div>
    `;
  }

  function renderProductCard(product, options = {}) {
    const wrapperClass = options.wrapperClass || "col-lg-4 col-md-6 mb-4";
    const extraAttributes = options.extraAttributes || "";
    const price = formatPrice(Number(product?.price || 0));
    const categoryName = product?.category?.name || "未分类";
    const evidence = renderEvidence(product, options);

    return `
      <div class="${wrapperClass}" ${extraAttributes}>
        <div class="product-card" data-product-id="${escapeHtml(product?.id)}">
          <div class="product-img">
            <img src="${escapeHtml(product?.cover_url || "images/logo.svg")}" alt="${escapeHtml(
              product?.name
            )}" />
          </div>
          <div class="product-info">
            <div class="product-name-row">
              <h5 class="product-name">${escapeHtml(product?.name)}</h5>
              <a href="product.html?id=${escapeHtml(
                product?.id
              )}" class="btn btn-sm btn-outline-primary view-details-btn">查看详情</a>
            </div>
            <div class="product-price">${escapeHtml(price)}</div>
            <div class="product-category">${escapeHtml(categoryName)}</div>
            ${evidence}
          </div>
          <div class="add-to-cart">
            <a href="product.html?id=${escapeHtml(product?.id)}" class="text-white">
              <i class="fas fa-shopping-cart me-1"></i> 加入购物车
            </a>
          </div>
        </div>
      </div>
    `;
  }

  window.shiyigeRecommendationUI = {
    escapeHtml,
    buildSearchExplanations,
    buildSourceMeta,
    renderEvidence,
    renderProductCard,
  };
})();
