/* 拾遗阁 - 统一 API 请求入口 */

(function () {
  function normalizePath(path) {
    if (path.startsWith("/api/")) {
      return path;
    }
    return `/api/v1${path.startsWith("/") ? path : `/${path}`}`;
  }

  async function request(path, options = {}) {
    const {
      method = "GET",
      headers = {},
      body,
      credentials = "include",
      retryOn401 = true,
    } = options;

    const requestHeaders = new Headers(headers);
    const isFormData = body instanceof FormData;
    const accessToken = window.shiyigeSession?.getAccessToken?.();

    if (!isFormData && body !== undefined && !requestHeaders.has("Content-Type")) {
      requestHeaders.set("Content-Type", "application/json");
    }

    if (accessToken && !requestHeaders.has("Authorization")) {
      requestHeaders.set("Authorization", `Bearer ${accessToken}`);
    }

    const response = await fetch(normalizePath(path), {
      method,
      headers: requestHeaders,
      body: isFormData || body === undefined ? body : JSON.stringify(body),
      credentials,
    });

    if (response.status === 401 && retryOn401 && window.shiyigeSession?.refreshAccessToken) {
      const refreshedToken = await window.shiyigeSession.refreshAccessToken();
      if (refreshedToken) {
        return request(path, {
          ...options,
          retryOn401: false,
        });
      }
    }

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const error = new Error(payload?.message || `Request failed with status ${response.status}`);
      error.response = response;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  window.shiyigeApi = {
    request,
    get(path, options = {}) {
      return request(path, { ...options, method: "GET" });
    },
    post(path, body, options = {}) {
      return request(path, { ...options, method: "POST", body });
    },
    put(path, body, options = {}) {
      return request(path, { ...options, method: "PUT", body });
    },
    delete(path, options = {}) {
      return request(path, { ...options, method: "DELETE" });
    },
  };
})();
