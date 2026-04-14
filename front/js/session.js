/* 拾遗阁 - 统一会话管理入口 */

(function () {
  const ACCESS_TOKEN_KEY = "shiyige_access_token";

  function getAccessToken() {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY);
  }

  function setAccessToken(token) {
    if (!token) return;
    sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
  }

  function clearSession() {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  }

  async function refreshAccessToken() {
    const response = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      clearSession();
      return null;
    }

    const payload = await response.json();
    const accessToken = payload?.data?.access_token || null;

    if (accessToken) {
      setAccessToken(accessToken);
    }

    return accessToken;
  }

  window.shiyigeSession = {
    getAccessToken,
    setAccessToken,
    clearSession,
    refreshAccessToken,
  };
})();
