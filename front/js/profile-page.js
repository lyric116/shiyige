/* 拾遗阁 - 个人中心页脚本 */

(function () {
  const state = {
    user: null,
    addresses: [],
    editingAddressId: null,
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

  function getAddressById(addressId) {
    return (
      state.addresses.find(function (address) {
        return address.id === addressId;
      }) || null
    );
  }

  function getPrimaryAddress() {
    return (
      state.addresses.find(function (address) {
        return address.is_default;
      }) ||
      state.addresses[0] ||
      null
    );
  }

  function syncAddressListSummary() {
    const summary = document.getElementById("address-list-summary");
    if (!summary) {
      return;
    }
    summary.textContent = `${state.addresses.length} 条`;
  }

  function syncAddressFormMode(address) {
    const formTitle = document.getElementById("address-form-title");
    const saveButton = document.getElementById("save-address-btn");
    const resetButton = document.getElementById("reset-address-btn");
    const deleteButton = document.getElementById("delete-address-btn");
    const isEditing = Boolean(address);

    state.editingAddressId = address?.id || null;

    if (formTitle) {
      formTitle.textContent = isEditing ? "编辑收货地址" : "填写收货地址";
    }
    if (saveButton) {
      saveButton.textContent = isEditing ? "更新收货地址" : "保存收货地址";
    }
    if (resetButton) {
      resetButton.textContent = isEditing ? "新建地址" : "清空表单";
    }
    if (deleteButton) {
      deleteButton.classList.toggle("d-none", !isEditing);
    }
  }

  function prefillNewAddressDraft() {
    const recipientInput = document.getElementById("address-recipient-name");
    const addressPhoneInput = document.getElementById("address-phone");
    const defaultCheckbox = document.getElementById("address-is-default");
    const profile = state.user?.profile || {};

    if (recipientInput && !recipientInput.value.trim()) {
      recipientInput.value = profile.display_name || state.user?.username || "";
    }
    if (addressPhoneInput && !addressPhoneInput.value.trim()) {
      addressPhoneInput.value = profile.phone || "";
    }
    if (defaultCheckbox) {
      defaultCheckbox.checked = state.addresses.length === 0;
    }
  }

  function fillAddressForm(address) {
    const form = document.getElementById("address-form");
    if (!form) {
      return;
    }

    form.reset();

    if (!address) {
      syncAddressFormMode(null);
      prefillNewAddressDraft();
      renderAddressList();
      return;
    }

    syncAddressFormMode(address);
    document.getElementById("address-recipient-name").value = address.recipient_name || "";
    document.getElementById("address-phone").value = address.phone || "";
    document.getElementById("address-region").value = address.region || "";
    document.getElementById("address-detail-address").value = address.detail_address || "";
    document.getElementById("address-postal-code").value = address.postal_code || "";
    document.getElementById("address-is-default").checked = Boolean(address.is_default);
    renderAddressList();
  }

  function renderAddressList() {
    const container = document.getElementById("saved-addresses");
    if (!container) {
      return;
    }

    syncAddressListSummary();

    if (!state.addresses.length) {
      container.innerHTML = `
        <div class="card border-0 bg-light">
          <div class="card-body text-muted">
            当前还没有保存的收货地址，请先填写左侧表单。
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = state.addresses
      .map(function (address) {
        const isActive = address.id === state.editingAddressId;
        return `
          <div class="card ${isActive ? "border-primary shadow-sm" : "border-0 bg-light"}">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                  <div class="fw-semibold mb-1">${escapeHtml(address.recipient_name)}</div>
                  <div class="mb-1">${escapeHtml(address.phone)}</div>
                  <div class="text-muted">${escapeHtml(address.region)} ${escapeHtml(address.detail_address)}</div>
                  <div class="text-muted small mt-2">
                    邮编：${escapeHtml(address.postal_code || "--")}
                  </div>
                </div>
                <span class="badge ${address.is_default ? "bg-success" : "bg-secondary"}">
                  ${address.is_default ? "默认地址" : "已保存"}
                </span>
              </div>
              <div class="d-flex flex-wrap gap-2 mt-3">
                <button
                  type="button"
                  class="btn btn-outline-primary btn-sm"
                  data-address-action="edit"
                  data-address-id="${address.id}"
                >
                  编辑
                </button>
                <button
                  type="button"
                  class="btn btn-outline-danger btn-sm"
                  data-address-action="delete"
                  data-address-id="${address.id}"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  async function loadAddresses(focusAddressId) {
    const payload = await window.shiyigeApi.get("/users/addresses");
    state.addresses = payload?.data?.items || [];

    const requestedAddress = getAddressById(Number(focusAddressId));
    if (requestedAddress) {
      fillAddressForm(requestedAddress);
      return;
    }

    const currentAddress = getAddressById(state.editingAddressId);
    if (currentAddress) {
      fillAddressForm(currentAddress);
      return;
    }

    const primaryAddress = getPrimaryAddress();
    if (primaryAddress) {
      fillAddressForm(primaryAddress);
      return;
    }

    fillAddressForm(null);
  }

  function buildAddressPayload() {
    const recipientName = document.getElementById("address-recipient-name")?.value?.trim();
    const phone = document.getElementById("address-phone")?.value?.trim();
    const region = document.getElementById("address-region")?.value?.trim();
    const detailAddress = document.getElementById("address-detail-address")?.value?.trim();
    const postalCode = document.getElementById("address-postal-code")?.value?.trim();
    const isDefault = Boolean(document.getElementById("address-is-default")?.checked);

    if (!recipientName) {
      showNotification("请输入收件人姓名", "error");
      return null;
    }
    if (!phone) {
      showNotification("请输入联系电话", "error");
      return null;
    }
    if (!region) {
      showNotification("请输入所在地区", "error");
      return null;
    }
    if (!detailAddress) {
      showNotification("请输入详细地址", "error");
      return null;
    }

    return {
      recipient_name: recipientName,
      phone,
      region,
      detail_address: detailAddress,
      postal_code: postalCode || null,
      is_default: isDefault,
    };
  }

  async function submitAddressForm() {
    const payload = buildAddressPayload();
    const saveButton = document.getElementById("save-address-btn");
    if (!payload || !saveButton) {
      return;
    }

    const isEditing = Boolean(state.editingAddressId);
    saveButton.disabled = true;
    saveButton.textContent = isEditing ? "正在更新..." : "正在保存...";

    try {
      const response = isEditing
        ? await window.shiyigeApi.put(`/users/addresses/${state.editingAddressId}`, payload)
        : await window.shiyigeApi.post("/users/addresses", payload);
      const savedAddressId = response?.data?.address?.id;
      await loadAddresses(savedAddressId);
      showNotification("收货地址已保存", "success");
    } catch (error) {
      showNotification(error?.payload?.message || "收货地址保存失败", "error");
      syncAddressFormMode(getAddressById(state.editingAddressId));
    } finally {
      saveButton.disabled = false;
      const activeAddress = getAddressById(state.editingAddressId);
      syncAddressFormMode(activeAddress);
    }
  }

  async function deleteAddress(addressId) {
    const numericAddressId = Number(addressId);
    const address = getAddressById(numericAddressId);
    if (!address) {
      return;
    }

    const confirmed = window.confirm(
      `确认删除收货地址“${address.recipient_name}”吗？`
    );
    if (!confirmed) {
      return;
    }

    const deleteButton = document.getElementById("delete-address-btn");
    if (deleteButton && state.editingAddressId === numericAddressId) {
      deleteButton.disabled = true;
      deleteButton.textContent = "正在删除...";
    }

    try {
      await window.shiyigeApi.delete(`/users/addresses/${numericAddressId}`);
      state.editingAddressId = null;
      await loadAddresses();
      showNotification("收货地址已删除", "success");
    } catch (error) {
      showNotification(error?.payload?.message || "收货地址删除失败", "error");
      const activeAddress = getAddressById(state.editingAddressId);
      syncAddressFormMode(activeAddress);
    } finally {
      if (deleteButton) {
        deleteButton.disabled = false;
        deleteButton.textContent = "删除当前地址";
      }
    }
  }

  function bindProfileForm() {
    const profileForm = document.getElementById("profile-form");
    if (!profileForm) {
      return;
    }

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
        state.user = payload.data.user;
        fillProfileForm(state.user);
        if (!state.editingAddressId) {
          prefillNewAddressDraft();
        }
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

  function bindPasswordForm() {
    const passwordForm = document.getElementById("password-form");
    if (!passwordForm) {
      return;
    }

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

  function bindAddressForm() {
    document.getElementById("address-form")?.addEventListener("submit", function (event) {
      event.preventDefault();
      void submitAddressForm();
    });

    document.getElementById("create-address-btn")?.addEventListener("click", function () {
      fillAddressForm(null);
    });

    document.getElementById("reset-address-btn")?.addEventListener("click", function () {
      fillAddressForm(null);
    });

    document.getElementById("delete-address-btn")?.addEventListener("click", function () {
      void deleteAddress(state.editingAddressId);
    });

    document.getElementById("saved-addresses")?.addEventListener("click", function (event) {
      const actionButton = event.target.closest("[data-address-action]");
      if (!actionButton) {
        return;
      }

      const addressId = Number(actionButton.dataset.addressId);
      if (!Number.isInteger(addressId)) {
        return;
      }

      if (actionButton.dataset.addressAction === "edit") {
        const address = getAddressById(addressId);
        if (address) {
          fillAddressForm(address);
        }
        return;
      }

      if (actionButton.dataset.addressAction === "delete") {
        void deleteAddress(addressId);
      }
    });
  }

  async function loadProfilePage() {
    const user = await window.shiyigeAuth?.fetchCurrentUser?.({ allowRefresh: true });
    if (!user) {
      window.location.href = "login.html";
      return;
    }

    state.user = user;
    fillProfileForm(user);
    bindProfileForm();
    bindAddressForm();
    bindPasswordForm();

    const logoutButton = document.getElementById("logout-sidebar-btn");
    if (logoutButton) {
      logoutButton.addEventListener("click", function (event) {
        event.preventDefault();
        void window.logout?.();
      });
    }

    try {
      await loadAddresses();
    } catch (error) {
      renderAddressList();
      fillAddressForm(null);
      showNotification(error?.payload?.message || "收货地址加载失败", "error");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    void loadProfilePage();
  });
})();
