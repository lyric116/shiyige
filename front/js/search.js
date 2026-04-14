/* 拾遗阁 - 搜索功能 */

(function () {
  const SUGGESTION_LIMIT = 5;
  const SUGGESTION_DEBOUNCE_MS = 150;

  function createSuggestionList(input, index) {
    const listId = `search-suggestions-${index}`;
    input.setAttribute("list", listId);

    let datalist = document.getElementById(listId);
    if (!datalist) {
      datalist = document.createElement("datalist");
      datalist.id = listId;
      document.body.appendChild(datalist);
    }

    return datalist;
  }

  async function updateSuggestions(keyword, datalist) {
    if (!keyword) {
      datalist.innerHTML = "";
      return;
    }

    try {
      const payload = await window.shiyigeApi.get(
        `/api/v1/search/suggestions?q=${encodeURIComponent(
          keyword
        )}&limit=${SUGGESTION_LIMIT}`
      );
      const items = payload.data.items || [];
      datalist.innerHTML = items
        .map((item) => `<option value="${item.keyword}"></option>`)
        .join("");
    } catch (error) {
      datalist.innerHTML = "";
    }
  }

  function bindSearchForm(form, index) {
    const searchInput = form.querySelector('input[type="search"]');
    if (!searchInput) return;

    const datalist = createSuggestionList(searchInput, index);
    let debounceTimer = 0;

    searchInput.addEventListener("input", function () {
      const keyword = this.value.trim();
      window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(function () {
        void updateSuggestions(keyword, datalist);
      }, SUGGESTION_DEBOUNCE_MS);
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const keyword = searchInput.value.trim();

      if (keyword) {
        window.location.href = `category.html?search=${encodeURIComponent(keyword)}`;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".navbar form").forEach((form, index) => {
      bindSearchForm(form, index);
    });
  });
})();
