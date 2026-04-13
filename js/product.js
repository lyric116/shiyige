/* 拾遗阁 - 商品详情页脚本 */

document.addEventListener("DOMContentLoaded", function () {
  initializeProductPage();
});

/**
 * 初始化商品详情页功能
 */
function initializeProductPage() {
  // 初始化图片放大镜效果
  initMagnifier();

  // 初始化缩略图点击切换
  initThumbnailsSwitch();

  // 初始化数量选择器
  initQuantitySelector();
}

/**
 * 初始化放大镜效果
 */
function initMagnifier() {
  const mainContainer = document.querySelector(".magnifier-container");
  const mainImage = document.querySelector(".product-main-img");
  if (!mainContainer || !mainImage) return;

  // 创建放大镜镜片元素
  const lens = document.createElement("div");
  lens.className = "magnifier-lens";
  mainContainer.appendChild(lens);

  // 设置放大系数和镜片尺寸
  const zoomFactor = 2;
  const lensWidth = 150;
  const lensHeight = 150;

  lens.style.width = `${lensWidth}px`;
  lens.style.height = `${lensHeight}px`;

  // 放大镜事件处理
  mainContainer.addEventListener("mousemove", function (e) {
    const rect = mainContainer.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // 计算镜片位置
    let lensLeft = mouseX - lensWidth / 2;
    let lensTop = mouseY - lensHeight / 2;

    // 限制镜片不超出图片边界
    lensLeft = Math.max(0, Math.min(lensLeft, rect.width - lensWidth));
    lensTop = Math.max(0, Math.min(lensTop, rect.height - lensHeight));

    // 设置镜片位置和背景
    lens.style.left = `${lensLeft}px`;
    lens.style.top = `${lensTop}px`;
    lens.style.backgroundImage = `url(${mainImage.src})`;
    lens.style.backgroundSize = `${rect.width * zoomFactor}px ${
      rect.height * zoomFactor
    }px`;
    lens.style.backgroundPosition = `-${lensLeft * zoomFactor}px -${
      lensTop * zoomFactor
    }px`;
  });

  // 鼠标进入显示放大镜
  mainContainer.addEventListener("mouseenter", function () {
    lens.style.opacity = "1";
  });

  // 鼠标离开隐藏放大镜
  mainContainer.addEventListener("mouseleave", function () {
    lens.style.opacity = "0";
  });

  // 移动设备不显示放大镜
  if (window.matchMedia("(max-width: 768px)").matches) {
    lens.style.display = "none";
  }
}

/**
 * 初始化缩略图点击切换
 */
function initThumbnailsSwitch() {
  const thumbnails = document.querySelectorAll(".product-thumb");
  if (thumbnails.length === 0) return;

  const mainImage = document.querySelector(".product-main-img");
  if (!mainImage) return;

  thumbnails.forEach((thumb) => {
    thumb.addEventListener("click", function () {
      // 更新主图
      mainImage.src = this.dataset.img;

      // 更新选中状态
      thumbnails.forEach((t) => t.classList.remove("active"));
      this.classList.add("active");

      // 重新初始化放大镜效果
      const lens = document.querySelector(".magnifier-lens");
      if (lens) {
        lens.remove();
        initMagnifier();
      }
    });
  });

  // 默认选中第一个缩略图
  if (thumbnails[0]) {
    thumbnails[0].classList.add("active");
    mainImage.src = thumbnails[0].dataset.img;
  }
}

/**
 * 初始化数量选择器
 */
function initQuantitySelector() {
  const quantityInput = document.getElementById("quantity");
  if (!quantityInput) return;

  const maxStock = parseInt(quantityInput.getAttribute("max") || "1");

  // 处理手动输入
  quantityInput.addEventListener("change", function () {
    let value = parseInt(this.value);
    if (isNaN(value) || value < 1) {
      value = 1;
    } else if (value > maxStock) {
      value = maxStock;
    }
    this.value = value;
  });
}

/**
 * 更新商品总价
 */
function updateProductTotal() {
  const quantityInput = document.querySelector(".product-quantity");
  const priceElement = document.querySelector(".product-price");
  const totalElement = document.querySelector(".product-total-price");

  if (quantityInput && priceElement && totalElement) {
    const quantity = parseInt(quantityInput.value);
    const price = parseFloat(
      priceElement.dataset.price ||
        priceElement.textContent.replace(/[^\d.]/g, "")
    );

    if (!isNaN(quantity) && !isNaN(price)) {
      const total = price * quantity;
      totalElement.textContent = formatPrice(total);
    }
  }
}

/**
 * 初始化相关商品滑块
 */
function initRelatedProductsSlider() {
  const container = document.querySelector(".related-products-slider");
  if (!container) return;

  // 初始化变量
  let isDown = false;
  let startX;
  let scrollLeft;

  // 鼠标按下事件
  container.addEventListener("mousedown", (e) => {
    isDown = true;
    container.classList.add("active");
    startX = e.pageX - container.offsetLeft;
    scrollLeft = container.scrollLeft;
  });

  // 鼠标离开事件
  container.addEventListener("mouseleave", () => {
    isDown = false;
    container.classList.remove("active");
  });

  // 鼠标抬起事件
  container.addEventListener("mouseup", () => {
    isDown = false;
    container.classList.remove("active");
  });

  // 鼠标移动事件
  container.addEventListener("mousemove", (e) => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - container.offsetLeft;
    const walk = (x - startX) * 2; // 滚动速度
    container.scrollLeft = scrollLeft - walk;
  });

  // 箭头按钮
  const prevBtn = document.querySelector(".related-prev");
  const nextBtn = document.querySelector(".related-next");

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      container.scrollBy({
        left: -300,
        behavior: "smooth",
      });
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      container.scrollBy({
        left: 300,
        behavior: "smooth",
      });
    });
  }
}

// 显示评价图片全屏预览
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

  const img = document.createElement("img");
  img.src = imageSrc;
  img.style.cssText = `
    max-width: 90%;
    max-height: 90%;
    object-fit: contain;
  `;

  modal.appendChild(img);
  document.body.appendChild(modal);

  modal.onclick = () => {
    modal.remove();
  };
}

// 加载更多评价
let currentPage = 1;
const reviewsPerPage = 5;

function loadMoreReviews() {
  const button = document.querySelector("#reviews .btn-outline-primary");
  button.disabled = true;
  button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 加载中...';

  // 模拟加载更多评价
  setTimeout(() => {
    const reviewsContainer = document.getElementById("reviews-container");

    // 示例评价数据
    const moreReviews = [
      {
        name: "张三",
        avatar: "https://ui-avatars.com/api/?name=张三&background=random",
        rating: 5,
        date: "2025-04-08",
        content:
          "做工精细，穿着舒适，很适合日常穿着。客服态度也很好，耐心解答了我的问题。",
        images: ["images/汉服/明制襦裙1.jpg"],
      },
      {
        name: "李四",
        avatar: "https://ui-avatars.com/api/?name=李四&background=random",
        rating: 4,
        date: "2025-04-05",
        content:
          "衣服很漂亮，就是价格稍微贵了点。不过考虑到是真丝面料，还算合理。",
        images: [],
      },
    ];

    // 创建新的评价元素
    moreReviews.forEach((review) => {
      const reviewElement = document.createElement("div");
      reviewElement.className = "review-item";

      const stars =
        '<i class="fas fa-star"></i>'.repeat(review.rating) +
        '<i class="far fa-star"></i>'.repeat(5 - review.rating);

      reviewElement.innerHTML = `
        <div class="review-header">
          <div class="reviewer-info">
            <img src="${review.avatar}" alt="用户头像" class="reviewer-avatar">
            <div>
              <h5 class="reviewer-name">${review.name}</h5>
              <div class="review-stars">
                ${stars}
              </div>
            </div>
          </div>
          <div class="review-date">${review.date}</div>
        </div>
        <div class="review-content">
          <p>${review.content}</p>
          ${
            review.images.length > 0
              ? `
            <div class="review-images">
              ${review.images
                .map(
                  (img) => `
                <img src="${img}" alt="用户评价图片" onclick="showFullImage('${img}')">
              `
                )
                .join("")}
            </div>
          `
              : ""
          }
        </div>
      `;

      reviewsContainer.appendChild(reviewElement);
    });

    currentPage++;

    // 如果加载到第3页，隐藏加载更多按钮
    if (currentPage >= 3) {
      button.style.display = "none";
    } else {
      button.disabled = false;
      button.innerHTML = "查看更多评价";
    }
  }, 1000);
}

// 更新商品规格信息
function updateProductSpecs(productId) {
  const product = productData[productId];
  if (!product || !product.specs) return;

  const specsContainer = document.getElementById("product-specs");
  specsContainer.innerHTML = Object.entries(product.specs)
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

// 更新评分统计
function updateReviewStats(productId) {
  const product = productData[productId];
  if (!product || !product.reviews) return;

  const stats = {
    average: 4.8,
    total: 26,
    distribution: {
      5: 18,
      4: 5,
      3: 2,
      2: 0,
      1: 1,
    },
  };

  // 更新总体评分
  document.querySelector(".overall-rating h2").textContent = stats.average;
  document.querySelector(
    ".overall-rating + p"
  ).textContent = `基于 ${stats.total} 条评价`;

  // 更新评分分布
  Object.entries(stats.distribution).forEach(([rating, count]) => {
    const percentage = (count / stats.total) * 100;
    const barItem = document.querySelector(
      `.rating-bar-item:nth-child(${6 - rating})`
    );
    if (barItem) {
      barItem.querySelector(".progress-bar").style.width = `${percentage}%`;
      barItem.querySelector("span:last-child").textContent = count;
    }
  });
}
