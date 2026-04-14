/* 拾遗阁 - 轮播图脚本 */

document.addEventListener("DOMContentLoaded", function () {
  // 初始化所有轮播图
  const carousels = document.querySelectorAll(".carousel");
  carousels.forEach(initializeCarousel);
});

/**
 * 初始化轮播图
 * @param {HTMLElement} carousel - 轮播图容器元素
 */
function initializeCarousel(carousel) {
  const slides = carousel.querySelectorAll(".carousel-item");
  const indicators = carousel.querySelectorAll(".carousel-indicators button");
  const prevBtn = carousel.querySelector(".carousel-control-prev");
  const nextBtn = carousel.querySelector(".carousel-control-next");

  if (slides.length === 0) return;

  let currentIndex = 0;
  let isAnimating = false;
  let touchStartX = 0;
  let touchEndX = 0;
  let interval = null;

  // 获取轮播间隔时间，默认5000ms
  const intervalTime = parseInt(carousel.dataset.bsInterval) || 5000;

  // 切换到指定slide
  function goToSlide(index, direction = null) {
    if (isAnimating || index === currentIndex) return;
    isAnimating = true;

    // 移除当前活动状态
    slides[currentIndex].classList.remove("active");
    if (indicators.length > 0) {
      indicators[currentIndex].classList.remove("active");
      indicators[currentIndex].setAttribute("aria-current", "false");
    }

    // 设置过渡方向
    if (direction === "next" || (direction === null && index > currentIndex)) {
      slides[currentIndex].classList.add("carousel-item-start");
      slides[index].classList.add("carousel-item-next");
      setTimeout(() => slides[index].classList.add("carousel-item-start"), 10);
    } else {
      slides[currentIndex].classList.add("carousel-item-end");
      slides[index].classList.add("carousel-item-prev");
      setTimeout(() => slides[index].classList.add("carousel-item-end"), 10);
    }

    // 延迟切换以等待动画完成
    setTimeout(() => {
      slides[currentIndex].classList.remove(
        "carousel-item-start",
        "carousel-item-end"
      );
      slides[index].classList.remove(
        "carousel-item-next",
        "carousel-item-prev",
        "carousel-item-start",
        "carousel-item-end"
      );

      // 设置新的活动slide
      slides[index].classList.add("active");
      if (indicators.length > 0) {
        indicators[index].classList.add("active");
        indicators[index].setAttribute("aria-current", "true");
      }

      currentIndex = index;
      isAnimating = false;
    }, 600); // 与CSS过渡时间匹配
  }

  // 下一张
  function nextSlide() {
    const newIndex = (currentIndex + 1) % slides.length;
    goToSlide(newIndex, "next");
  }

  // 上一张
  function prevSlide() {
    const newIndex = (currentIndex - 1 + slides.length) % slides.length;
    goToSlide(newIndex, "prev");
  }

  // 开始自动轮播
  function startAutoSlide() {
    if (interval) return;
    interval = setInterval(nextSlide, intervalTime);
  }

  // 停止自动轮播
  function stopAutoSlide() {
    if (interval) {
      clearInterval(interval);
      interval = null;
    }
  }

  // 绑定指示器点击事件
  indicators.forEach((indicator, index) => {
    indicator.addEventListener("click", () => {
      if (isAnimating) return;
      stopAutoSlide();
      goToSlide(index);
      startAutoSlide();
    });
  });

  // 绑定前进/后退按钮事件
  if (prevBtn) {
    prevBtn.addEventListener("click", (e) => {
      e.preventDefault();
      if (isAnimating) return;
      stopAutoSlide();
      prevSlide();
      startAutoSlide();
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", (e) => {
      e.preventDefault();
      if (isAnimating) return;
      stopAutoSlide();
      nextSlide();
      startAutoSlide();
    });
  }

  // 触摸事件处理
  carousel.addEventListener(
    "touchstart",
    (e) => {
      touchStartX = e.changedTouches[0].screenX;
      stopAutoSlide();
    },
    { passive: true }
  );

  carousel.addEventListener(
    "touchend",
    (e) => {
      touchEndX = e.changedTouches[0].screenX;
      handleSwipe();
      startAutoSlide();
    },
    { passive: true }
  );

  function handleSwipe() {
    const swipeThreshold = 50;
    const swipeLength = touchEndX - touchStartX;

    if (Math.abs(swipeLength) > swipeThreshold) {
      if (swipeLength > 0) {
        prevSlide();
      } else {
        nextSlide();
      }
    }
  }

  // 鼠标悬停暂停
  carousel.addEventListener("mouseenter", stopAutoSlide);
  carousel.addEventListener("mouseleave", startAutoSlide);

  // 开始自动轮播
  startAutoSlide();
}

/**
 * 创建自定义轮播内容
 * @param {string} containerId - 容器ID
 * @param {Array} items - 轮播项数组，每项需包含image, title, description, link属性
 */
function createCustomCarousel(containerId, items) {
  if (!items || items.length === 0) return;

  const container = document.getElementById(containerId);
  if (!container) return;

  // 创建轮播结构
  const carouselId = `carousel-${containerId}`;
  let html = `
        <div id="${carouselId}" class="carousel slide" data-interval="5000">
            <div class="carousel-indicators">
    `;

  // 创建指示器
  items.forEach((_, index) => {
    html += `
            <button type="button" data-bs-target="#${carouselId}" data-bs-slide-to="${index}" 
                ${
                  index === 0 ? 'class="active" aria-current="true"' : ""
                } aria-label="Slide ${index + 1}"></button>
        `;
  });

  html += `
            </div>
            <div class="carousel-inner">
    `;

  // 创建轮播项
  items.forEach((item, index) => {
    html += `
            <div class="carousel-item ${index === 0 ? "active" : ""}">
                <img src="${item.image}" class="d-block w-100" alt="${
      item.title
    }">
                <div class="carousel-caption d-none d-md-block">
                    <h3>${item.title}</h3>
                    <p>${item.description}</p>
                    ${
                      item.link
                        ? `<a href="${item.link}" class="btn btn-primary mt-2">了解更多</a>`
                        : ""
                    }
                </div>
            </div>
        `;
  });

  html += `
            </div>
            <button class="carousel-control-prev" type="button" data-bs-target="#${carouselId}" data-bs-slide="prev">
                <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                <span class="visually-hidden">上一个</span>
            </button>
            <button class="carousel-control-next" type="button" data-bs-target="#${carouselId}" data-bs-slide="next">
                <span class="carousel-control-next-icon" aria-hidden="true"></span>
                <span class="visually-hidden">下一个</span>
            </button>
        </div>
    `;

  // 插入HTML
  container.innerHTML = html;

  // 初始化轮播图
  initializeCarousel(document.getElementById(carouselId));
}

// 导出函数供其他模块使用
window.createCustomCarousel = createCustomCarousel;
