// 满减活动规则
const promotionRules = [
  { threshold: 1000, discount: 120 },
  { threshold: 500, discount: 50 },
  { threshold: 300, discount: 25 },
];

// 计算满减金额
function calculateDiscount(totalAmount) {
  // 从高到低排序规则，确保应用最高优惠
  const sortedRules = [...promotionRules].sort(
    (a, b) => b.threshold - a.threshold
  );

  for (const rule of sortedRules) {
    if (totalAmount >= rule.threshold) {
      return rule.discount;
    }
  }
  return 0;
}

// 获取下一个满减目标
function getNextPromotionTarget(totalAmount) {
  // 从低到高排序规则，找到下一个目标
  const sortedRules = [...promotionRules].sort(
    (a, b) => a.threshold - b.threshold
  );

  for (const rule of sortedRules) {
    if (totalAmount < rule.threshold) {
      return {
        target: rule.threshold,
        remaining: rule.threshold - totalAmount,
        discount: rule.discount,
      };
    }
  }
  return null;
}

// 更新满减进度条
function updatePromotionProgress(totalAmount) {
  const promotionBanner = document.querySelector(".promotion-banner");
  if (!promotionBanner) return;

  const nextTarget = getNextPromotionTarget(totalAmount);
  const currentDiscount = calculateDiscount(totalAmount);

  let html = '<h5>满减优惠</h5><ul class="promotion-list">';

  // 显示当前优惠
  if (currentDiscount > 0) {
    html += `
      <li class="promotion-item">
        <i class="fas fa-check-circle text-success"></i>
        已满${totalAmount.toFixed(2)}元，已减${currentDiscount}元
      </li>
    `;
  }

  // 显示下一个目标
  if (nextTarget) {
    const progress = (totalAmount / nextTarget.target) * 100;
    html += `
      <li class="promotion-item">
        <i class="fas fa-gift text-primary"></i>
        再购买${nextTarget.remaining.toFixed(2)}元，可减${nextTarget.discount}元
        <div class="promotion-progress mt-2">
          <div class="progress" style="height: 6px;">
            <div class="progress-bar bg-primary" style="width: ${progress}%"></div>
          </div>
          <div class="promotion-target text-muted small mt-1">
            满${nextTarget.target}减${nextTarget.discount}
          </div>
        </div>
      </li>
    `;
  } else if (currentDiscount > 0) {
    html += `
      <li class="promotion-item">
        <i class="fas fa-crown text-warning"></i>
        已达到最高优惠
      </li>
    `;
  } else {
    html += `
      <li class="promotion-item">
        <i class="fas fa-info-circle text-info"></i>
        满300减25，满500减50，满1000减120
      </li>
    `;
  }

  html += "</ul>";
  promotionBanner.innerHTML = html;
}

// 导出函数供其他模块使用
window.promotion = {
  calculateDiscount,
  getNextPromotionTarget,
  updatePromotionProgress,
};
