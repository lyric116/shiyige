/* 拾遗阁 - 个人中心页脚本 */

(function () {
  function fillProfileForm(user) {
    const profile = user.profile || {};
    document.getElementById("sidebar-username").textContent =
      profile.display_name || user.username;
    document.getElementById("sidebar-email").textContent = user.email;

    document.getElementById("username").value = user.username || "";
    document.getElementById("email").value = user.email || "";
    document.getElementById("phone").value = profile.phone || "";
    document.getElementById("birthday").value = profile.birthday || "";
  }

  async function fillDefaultAddress() {
    const addressInput = document.getElementById("address");
    if (!addressInput) return;

    addressInput.readOnly = true;
    addressInput.placeholder = "默认收货地址将从地址管理接口读取";

    try {
      const payload = await window.shiyigeApi.get("/users/addresses");
      const addresses = payload?.data?.items || [];
      const address = addresses.find((item) => item.is_default) || addresses[0] || null;
      if (!address) {
        addressInput.value = "";
        return;
      }
      addressInput.value = `${address.region} ${address.detail_address}`;
    } catch {
      addressInput.value = "";
    }
  }

  async function loadProfilePage() {
    const user = await window.shiyigeAuth?.fetchCurrentUser?.({ allowRefresh: true });
    if (!user) {
      window.location.href = "login.html";
      return;
    }

    fillProfileForm(user);
    await fillDefaultAddress();

    const logoutButton = document.getElementById("logout-sidebar-btn");
    if (logoutButton) {
      logoutButton.addEventListener("click", function (event) {
        event.preventDefault();
        void window.logout?.();
      });
    }

    const profileForm = document.getElementById("profile-form");
    if (profileForm) {
      profileForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        try {
          const payload = await window.shiyigeApi.put("/users/me", {
            username: document.getElementById("username").value.trim(),
            email: document.getElementById("email").value.trim(),
            display_name: document.getElementById("username").value.trim(),
            phone: document.getElementById("phone").value.trim() || null,
            birthday: document.getElementById("birthday").value || null,
            bio: null,
            avatar_url: null,
          });
          fillProfileForm(payload.data.user);
          if (typeof showNotification === "function") {
            showNotification("个人信息已更新", "success");
          }
          await window.updateNavigation?.();
        } catch (error) {
          if (typeof showNotification === "function") {
            showNotification(error?.payload?.message || "个人信息更新失败", "error");
          }
        }
      });
    }

    const passwordForm = document.getElementById("password-form");
    if (passwordForm) {
      passwordForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const currentPassword = document.getElementById("current-password").value;
        const newPassword = document.getElementById("new-password").value;
        const confirmPassword = document.getElementById("confirm-password").value;

        if (!currentPassword) {
          showNotification("请输入当前密码", "error");
          return;
        }

        if (!newPassword) {
          showNotification("请输入新密码", "error");
          return;
        }

        if (newPassword !== confirmPassword) {
          showNotification("两次输入的密码不一致", "error");
          return;
        }

        try {
          await window.shiyigeApi.put("/users/password", {
            current_password: currentPassword,
            new_password: newPassword,
          });
          showNotification("密码修改成功", "success");
          document.getElementById("current-password").value = "";
          document.getElementById("new-password").value = "";
          document.getElementById("confirm-password").value = "";
        } catch (error) {
          showNotification(error?.payload?.message || "密码修改失败", "error");
        }
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    void loadProfilePage();
  });
})();
