/* 拾遗阁 - 会员中心真实数据接线 */

(function () {
  function formatPrice(value) {
    return `¥${Number(value || 0).toFixed(2)}`;
  }

  function formatPointsRate(value) {
    return `${Number(value || 0).toString()}倍积分`;
  }

  function formatDiscountLabel(value) {
    return `${Math.round(Number(value || 0) * 100)}折`;
  }

  function renderMembershipCard(profile) {
    const membershipCard = document.querySelector(".membership-card");
    if (!membershipCard) return;

    const currentLevel = profile.current_level;
    const nextLevel = profile.next_level;
    const progressHtml = nextLevel
      ? `
        <div class="member-progress mt-3">
          <div class="member-progress-bar" style="width: ${profile.progress_percent}%"></div>
        </div>
        <div class="text-end mt-2 small text-muted">
          距离${nextLevel.name}还需${nextLevel.remaining_points}积分
        </div>
      `
      : '<div class="small text-muted mt-3">当前已达到最高会员等级</div>';

    membershipCard.innerHTML = `
      <div class="member-level">${currentLevel.name}</div>
      <div class="member-points">
        <div>当前积分：${profile.points_balance}</div>
        <div>累计积分：${profile.lifetime_points}</div>
        <div>累计消费：${formatPrice(profile.total_spent_amount)}</div>
      </div>
      <div class="small text-muted mt-3">当前权益：${formatDiscountLabel(
        currentLevel.discount_rate
      )} / ${formatPointsRate(currentLevel.points_rate)}</div>
      ${progressHtml}
    `;
  }

  function renderBenefits(benefitPayload) {
    const benefitsContainer = document.querySelector(".member-benefits");
    if (!benefitsContainer) return;

    const currentLevel = benefitPayload.current_level;
    const currentBenefits = benefitPayload.items.find((item) => item.is_current) || currentLevel;

    benefitsContainer.innerHTML = `
      <h3>${currentLevel.name}专属权益</h3>
      <div class="benefit-item">
        <div class="benefit-icon">
          <i class="fas fa-tag"></i>
        </div>
        <div class="benefit-info">
          <h4>专属折扣</h4>
          <p>购物享${formatDiscountLabel(currentLevel.discount_rate)}</p>
        </div>
      </div>
      <div class="benefit-item">
        <div class="benefit-icon">
          <i class="fas fa-coins"></i>
        </div>
        <div class="benefit-info">
          <h4>积分倍率</h4>
          <p>消费享${formatPointsRate(currentLevel.points_rate)}</p>
        </div>
      </div>
      <div class="benefit-item">
        <div class="benefit-icon">
          <i class="fas fa-scroll"></i>
        </div>
        <div class="benefit-info">
          <h4>等级说明</h4>
          <p>${currentBenefits.description || "该等级已享有当前阶段默认会员权益。"}</p>
        </div>
      </div>
    `;
  }

  function renderPointsHistory(pointsPayload) {
    const historyBody = document.getElementById("points-history-body");
    if (!historyBody) return;

    const items = pointsPayload.items || [];
    if (items.length === 0) {
      historyBody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center text-muted">暂无积分记录</td>
        </tr>
      `;
      return;
    }

    historyBody.innerHTML = items
      .map(
        (item) => `
          <tr>
            <td>${new Date(item.created_at).toLocaleString("zh-CN", { hour12: false })}</td>
            <td>${item.change_type}</td>
            <td class="${item.change_amount >= 0 ? "text-success" : "text-danger"}">
              ${item.change_amount >= 0 ? "+" : ""}${item.change_amount}
            </td>
            <td>${item.remark || "-"}</td>
          </tr>
        `
      )
      .join("");
  }

  function renderRechargeNotice() {
    const rechargeOptionsContainer = document.querySelector(".recharge-options");
    const rechargeForm = document.getElementById("recharge-form");
    if (rechargeOptionsContainer) {
      rechargeOptionsContainer.innerHTML = `
        <div class="alert alert-light mb-0">
          当前阶段会员中心已接入真实积分与等级数据，在线充值功能将在后续阶段接通。
        </div>
      `;
    }

    if (rechargeForm) {
      rechargeForm.querySelectorAll("input, select, button").forEach((element) => {
        element.disabled = true;
      });
    }
  }

  async function loadMembershipPage() {
    const currentUser = await window.shiyigeAuth?.fetchCurrentUser?.({
      allowRefresh: true,
    });
    if (!currentUser) {
      window.location.href = "login.html";
      return;
    }

    try {
      const [profilePayload, pointsPayload, benefitsPayload] = await Promise.all([
        window.shiyigeApi.get("/member/profile"),
        window.shiyigeApi.get("/member/points"),
        window.shiyigeApi.get("/member/benefits"),
      ]);

      renderMembershipCard(profilePayload.data.profile);
      renderBenefits(benefitsPayload.data);
      renderPointsHistory(pointsPayload.data);
      renderRechargeNotice();
    } catch (error) {
      renderRechargeNotice();
      if (typeof showNotification === "function") {
        showNotification(error?.payload?.message || "会员中心数据加载失败", "error");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    void loadMembershipPage();
  });
})();
