/* 拾遗阁 - 搜索功能 */

// 初始化搜索功能
document.addEventListener("DOMContentLoaded", function () {
  // 获取所有搜索表单
  const searchForms = document.querySelectorAll(".navbar form");

  searchForms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      // 获取搜索关键词
      const searchInput = this.querySelector('input[type="search"]');
      const keyword = searchInput.value.trim();

      if (keyword) {
        // 将搜索关键词添加到 URL 参数中并跳转到分类页面
        window.location.href = `category.html?search=${encodeURIComponent(
          keyword
        )}`;
      }
    });
  });
});

// 在分类页面处理搜索
function handleSearch() {
  const urlParams = new URLSearchParams(window.location.search);
  const searchKeyword = urlParams.get("search");

  if (searchKeyword) {
    // 更新页面标题
    document.getElementById(
      "category-name"
    ).textContent = `搜索：${searchKeyword}`;
    document.getElementById("category-description").textContent =
      "以下是搜索结果：";
    document.title = `拾遗阁 - 搜索：${searchKeyword}`;

    // 搜索商品
    filterProductsByKeyword(searchKeyword);
  }
}

// 根据关键词筛选商品
function filterProductsByKeyword(keyword) {
  const productItems = document.querySelectorAll(".product-item");
  let visibleCount = 0;
  const keywordLower = keyword.toLowerCase();

  productItems.forEach((item) => {
    const productName = item
      .querySelector(".product-name")
      .textContent.toLowerCase();
    const productCategory =
      item.querySelector(".product-category")?.textContent.toLowerCase() || "";
    const isVisible =
      productName.includes(keywordLower) ||
      productCategory.includes(keywordLower);

    if (isVisible) {
      item.classList.remove("d-none");
      visibleCount++;
    } else {
      item.classList.add("d-none");
    }
  });

  // 显示空状态提示（如果没有符合条件的商品）
  const emptyState = document.getElementById("empty-state");
  if (visibleCount === 0) {
    emptyState.classList.remove("d-none");
  } else {
    emptyState.classList.add("d-none");
  }
}
