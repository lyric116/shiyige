/* 拾遗阁 - 登录/注册页脚本 */

(function () {
  function notify(message, type = "info") {
    const flashMessages = document.getElementById("flash-messages");
    if (!flashMessages) return;

    const alertDiv = document.createElement("div");
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = "alert";
    alertDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="关闭"></button>
    `;

    flashMessages.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 3000);
  }

  function redirectAfterDelay(path, delay = 1000) {
    window.setTimeout(() => {
      window.location.href = path;
    }, delay);
  }

  async function ensureGuestOnly() {
    const accessToken = window.shiyigeSession?.getAccessToken?.();
    if (accessToken) {
      window.location.href = "index.html";
      return true;
    }

    try {
      const refreshedToken = await window.shiyigeSession?.refreshAccessToken?.();
      if (refreshedToken) {
        window.location.href = "index.html";
        return true;
      }
    } catch {
      window.shiyigeSession?.clearSession?.();
    }

    return false;
  }

  function bindThirdPartyPlaceholders() {
    document.querySelectorAll(".social-btn").forEach((btn) => {
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        notify("第三方登录/注册首轮降级为占位提示，暂未开放。", "info");
      });
    });
  }

  async function initLoginPage() {
    if (await ensureGuestOnly()) {
      return;
    }

    const loginForm = document.getElementById("login-form");
    if (loginForm) {
      loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        let isValid = true;
        const email = document.getElementById("email");
        const password = document.getElementById("password");

        if (!validateEmail(email)) {
          isValid = false;
        }

        if (!validateRequired(password, "请输入密码")) {
          isValid = false;
        }

        if (!isValid) {
          return;
        }

        try {
          const payload = await window.shiyigeApi.post("/auth/login", {
            email: email.value.trim(),
            password: password.value,
          });
          const accessToken = payload?.data?.access_token;
          if (accessToken) {
            window.shiyigeSession?.setAccessToken?.(accessToken);
          }
          notify("登录成功，正在跳转...", "success");
          redirectAfterDelay("index.html");
        } catch (error) {
          notify(error?.payload?.message || "登录失败，请检查邮箱和密码。", "danger");
        }
      });
    }

    bindThirdPartyPlaceholders();

    const forgotPasswordLink = document.getElementById("forgot-password");
    if (forgotPasswordLink) {
      forgotPasswordLink.addEventListener("click", function (event) {
        event.preventDefault();
        notify("密码重置功能即将上线，请稍后再试。", "info");
      });
    }
  }

  async function initRegisterPage() {
    if (await ensureGuestOnly()) {
      return;
    }

    const registerForm = document.getElementById("register-form");
    if (registerForm) {
      registerForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        let isValid = true;
        const username = document.getElementById("username");
        const email = document.getElementById("email");
        const password = document.getElementById("password");
        const confirmPassword = document.getElementById("confirm_password");
        const agreeTerms = document.getElementById("agree-terms");

        if (!validateUsername(username)) {
          isValid = false;
        }

        if (!validateEmail(email)) {
          isValid = false;
        }

        if (!validatePassword(password)) {
          isValid = false;
        }

        if (!validateConfirmPassword(confirmPassword, password.value)) {
          isValid = false;
        }

        if (!agreeTerms.checked) {
          agreeTerms.classList.add("is-invalid");
          isValid = false;
        } else {
          agreeTerms.classList.remove("is-invalid");
        }

        if (!isValid) {
          return;
        }

        try {
          await window.shiyigeApi.post("/auth/register", {
            username: username.value.trim(),
            email: email.value.trim(),
            password: password.value,
          });
          notify("注册成功，正在前往登录页...", "success");
          redirectAfterDelay("login.html");
        } catch (error) {
          notify(error?.payload?.message || "注册失败，请稍后重试。", "danger");
        }
      });
    }

    bindThirdPartyPlaceholders();

    const termsLink = document.getElementById("terms-link");
    if (termsLink) {
      termsLink.addEventListener("click", function (event) {
        event.preventDefault();
        notify("服务条款内容正在完善中，敬请期待。", "info");
      });
    }

    const privacyLink = document.getElementById("privacy-link");
    if (privacyLink) {
      privacyLink.addEventListener("click", function (event) {
        event.preventDefault();
        notify("隐私政策内容正在完善中，敬请期待。", "info");
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.getElementById("login-form")) {
      void initLoginPage();
    }

    if (document.getElementById("register-form")) {
      void initRegisterPage();
    }
  });
})();
