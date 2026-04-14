// 花瓣图片数组
const petalImages = [
  "images/背景/花瓣1.png",
  "images/背景/花瓣2.png",
  "images/背景/花瓣3.png",
  "images/背景/花瓣4.png",
  "images/背景/花瓣5.png",
  "images/背景/花瓣6.png",
  "images/背景/花瓣7.png",
  "images/背景/花瓣8.png",
  "images/背景/花瓣9.png",
  "images/背景/花瓣10.png",
  "images/背景/花瓣11.png",
  "images/背景/花瓣12.png",
];

// 创建花瓣元素
function createPetal() {
  const petalsContainer = document.querySelector(".petals-container");
  const petal = document.createElement("div");

  // 随机选择花瓣图片
  const randomImage =
    petalImages[Math.floor(Math.random() * petalImages.length)];

  // 随机设置花瓣大小
  const size = Math.random() * 15 + 20; // 15-30px

  petal.className = "petal";
  petal.style.width = `${size}px`;
  petal.style.height = `${size}px`;
  petal.style.backgroundImage = `url('${randomImage}')`;

  // 随机起始位置（横向）
  petal.style.left = `${Math.random() * 100}vw`;

  // 随机动画持续时间和延迟
  const duration = Math.random() * 4 + 6; // 6-10秒
  const delay = Math.random() * 5; // 0-5秒延迟

  // 应用动画
  petal.style.animation = `
        falling ${duration}s linear ${delay}s infinite,
        sway ${duration / 2}s ease-in-out ${delay}s infinite
    `;

  petalsContainer.appendChild(petal);

  // 动画结束后移除花瓣
  setTimeout(() => {
    petal.remove();
  }, (duration + delay) * 1000);
}

// 初始化花瓣容器
function initPetals() {
  const container = document.createElement("div");
  container.className = "petals-container";
  document.body.insertBefore(container, document.body.firstChild);

  // 初始创建一些花瓣
  for (let i = 0; i < 10; i++) {
    createPetal();
  }

  // 定期创建新的花瓣
  setInterval(createPetal, 500); // 每500ms创建一个新花瓣
}

// 创建并控制背景渐变斑点
function initGradientSpots() {
  const spots = document.querySelectorAll(".gradient-spot");

  // 将视口分成多个区域
  const areas = [
    { x: [0, 33], y: [0, 33] },
    { x: [33, 66], y: [0, 33] },
    { x: [66, 100], y: [0, 33] },
    { x: [0, 33], y: [33, 66] },
    { x: [33, 66], y: [33, 66] },
    { x: [66, 100], y: [33, 66] },
    { x: [0, 33], y: [66, 100] },
    { x: [33, 66], y: [66, 100] },
    { x: [66, 100], y: [66, 100] },
  ];

  function getRandomInRange(min, max) {
    return min + Math.random() * (max - min);
  }

  function updateSpotPosition(spot, areaIndex) {
    const area = areas[areaIndex % areas.length];

    // 在指定区域内生成随机位置
    const x = getRandomInRange(area.x[0], area.x[1]);
    const y = getRandomInRange(area.y[0], area.y[1]);

    // 生成随机大小（200px 到 400px 之间）
    const size = 200 + Math.random() * 200;

    // 生成随机动画持续时间（10s 到 20s 之间）
    const duration = 10 + Math.random() * 10;

    // 设置样式
    spot.style.left = `${x}%`;
    spot.style.top = `${y}%`;
    spot.style.width = `${size}px`;
    spot.style.height = `${size}px`;
    spot.style.opacity = "0";

    // 淡入效果
    setTimeout(() => {
      spot.style.opacity = "0.6";
    }, 100);

    // 创建动画
    const keyframes = [
      { transform: "translate(0, 0) scale(1)", opacity: 0.2 },
      {
        transform: `translate(${Math.random() * 30 - 15}%, ${
          Math.random() * 30 - 15
        }%) scale(1.2)`,
        opacity: 0.8,
      },
      { transform: "translate(0, 0) scale(1)", opacity: 0.2 },
    ];

    const animation = spot.animate(keyframes, {
      duration: duration * 1000,
      iterations: Infinity,
      easing: "ease-in-out",
    });

    // 在动画完成时更新到新的随机位置
    setTimeout(() => {
      updateSpotPosition(spot, Math.floor(Math.random() * areas.length));
    }, duration * 1000);
  }

  // 为每个斑点设置初始随机位置和动画
  spots.forEach((spot, index) => {
    // 错开动画开始时间
    setTimeout(() => {
      updateSpotPosition(spot, index);
    }, index * 2000); // 每个斑点间隔2秒开始动画
  });
}

// 页面加载完成后初始化
document.addEventListener("DOMContentLoaded", function () {
  // 初始化花瓣效果
  initPetals();
  // 初始化渐变斑点
  initGradientSpots();
});
