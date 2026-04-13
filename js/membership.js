// 会员等级配置
const membershipLevels = {
  bronze: {
    name: "青铜会员",
    minPoints: 0,
    discount: 0.98,
    pointsRate: 1,
  },
  silver: {
    name: "白银会员",
    minPoints: 1000,
    discount: 0.95,
    pointsRate: 1.2,
  },
  gold: {
    name: "黄金会员",
    minPoints: 5000,
    discount: 0.92,
    pointsRate: 1.5,
  },
  platinum: {
    name: "铂金会员",
    minPoints: 20000,
    discount: 0.88,
    pointsRate: 2,
  },
};

// 充值选项
const rechargeOptions = [
  { amount: 100, bonus: 10 },
  { amount: 500, bonus: 60 },
  { amount: 1000, bonus: 150 },
  { amount: 2000, bonus: 400 },
];

// 初始化会员信息
function initMembership() {
  let membership = JSON.parse(localStorage.getItem("shiyige_membership")) || {
    points: 0,
    balance: 0,
    totalSpent: 0,
  };
  return membership;
}

// 获取当前会员等级
function getCurrentLevel(points) {
  let currentLevel = "bronze";
  for (const [level, config] of Object.entries(membershipLevels)) {
    if (points >= config.minPoints) {
      currentLevel = level;
    } else {
      break;
    }
  }
  return membershipLevels[currentLevel];
}

// 获取下一个等级
function getNextLevel(points) {
  for (const [level, config] of Object.entries(membershipLevels)) {
    if (points < config.minPoints) {
      return {
        name: config.name,
        minPoints: config.minPoints,
        remaining: config.minPoints - points,
      };
    }
  }
  return null;
}

// 计算商品可获得的积分
function calculatePoints(price) {
  const membership = initMembership();
  const currentLevel = getCurrentLevel(membership.points);
  return Math.floor(price * currentLevel.pointsRate);
}

// 计算会员折扣价
function calculateDiscountPrice(originalPrice) {
  const membership = initMembership();
  const currentLevel = getCurrentLevel(membership.points);
  return (originalPrice * currentLevel.discount).toFixed(2);
}

// 充值处理
function handleRecharge(amount) {
  const membership = initMembership();
  const option = rechargeOptions.find((opt) => opt.amount === amount);

  if (option) {
    membership.balance += amount + option.bonus;
    membership.points += Math.floor(amount / 10); // 每10元获得1积分
    localStorage.setItem("shiyige_membership", JSON.stringify(membership));
    return true;
  }
  return false;
}

// 使用余额支付
function payWithBalance(amount) {
  const membership = initMembership();
  if (membership.balance >= amount) {
    membership.balance -= amount;
    membership.totalSpent += amount;
    membership.points += calculatePoints(amount);
    localStorage.setItem("shiyige_membership", JSON.stringify(membership));
    return true;
  }
  return false;
}

// 更新会员卡信息显示
function updateMembershipCard() {
  const membership = initMembership();
  const currentLevel = getCurrentLevel(membership.points);
  const nextLevel = getNextLevel(membership.points);

  const membershipCard = document.querySelector(".membership-card");
  if (!membershipCard) return;

  let progressHtml = "";
  if (nextLevel) {
    const progress = (membership.points / nextLevel.minPoints) * 100;
    progressHtml = `
            <div class="member-progress">
                <div class="member-progress-bar" style="width: ${progress}%"></div>
            </div>
            <div class="text-end">
                距离${nextLevel.name}还需${nextLevel.remaining}积分
            </div>
        `;
  }

  membershipCard.innerHTML = `
        <div class="member-level">${currentLevel.name}</div>
        <div class="member-points">
            <div>当前积分：${membership.points}</div>
            <div>账户余额：¥${membership.balance.toFixed(2)}</div>
        </div>
        ${progressHtml}
    `;
}

// 更新会员权益显示
function updateBenefitsDisplay() {
  const membership = initMembership();
  const currentLevel = getCurrentLevel(membership.points);

  const benefitsContainer = document.querySelector(".member-benefits");
  if (!benefitsContainer) return;

  benefitsContainer.innerHTML = `
        <h3>会员权益</h3>
        <div class="benefit-item">
            <div class="benefit-icon">
                <i class="fas fa-tag"></i>
            </div>
            <div class="benefit-info">
                <h4>专属折扣</h4>
                <p>购物享${(100 - currentLevel.discount * 100).toFixed(
                  0
                )}%折扣</p>
            </div>
        </div>
        <div class="benefit-item">
            <div class="benefit-icon">
                <i class="fas fa-coins"></i>
            </div>
            <div class="benefit-info">
                <h4>积分倍率</h4>
                <p>消费享${currentLevel.pointsRate}倍积分</p>
            </div>
        </div>
    `;
}

// 导出函数供其他模块使用
window.membership = {
  initMembership,
  getCurrentLevel,
  calculateDiscountPrice,
  calculatePoints,
  handleRecharge,
  payWithBalance,
  updateMembershipCard,
  updateBenefitsDisplay,
  rechargeOptions,
};
