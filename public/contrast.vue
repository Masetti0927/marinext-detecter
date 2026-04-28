<template>
  <div class="contrast-container">
    <div class="left-panel">
      <div class="interaction-hint">
        <span>🖱️ 滚轮缩放</span>
        <span>👋 按住拖拽</span>
        <span v-if="lockedClasses.size > 0">📌 已锁定 {{ lockedClasses.size }} 个区域</span>
      </div>
      <div ref="chartRef" class="chart"></div>
    </div>

    <div class="right-panel">
      <div class="panel-section">
        <h3 class="section-title">参数控制</h3>

        <div class="control-item">
          <div class="label-row">
            <span>掩模透明度 (Opacity)</span>
            <span>{{ (maskOpacity * 100).toFixed(0) }}%</span>
          </div>
          <input type="range" min="0" max="1" step="0.05" v-model="maskOpacity" />
        </div>

        <div class="control-item">
          <div class="label-row">
            <span>显示阈值 (Threshold)</span>
            <span>{{ maskThreshold }}%</span>
          </div>
          <input type="range" min="0" max="5" step="0.1" v-model="maskThreshold" />
          <div class="hint">低于该占比的污染区域及图例将被隐藏</div>
        </div>
      </div>

      <div class="panel-section flex-grow">
        <h3 class="section-title">类别图例与数据</h3>
        <div class="legend-list">
          <div
              v-for="cls in filteredLegendClasses"
              :key="cls"
              class="legend-item-wrapper"
              @mouseenter="onLegendHover(cls)"
              @mouseleave="onLegendLeave"
              @click="toggleLock(cls)"
              :class="{
                'is-active': hoveredClass === cls,
                'is-locked': lockedClasses.has(cls)
              }"
          >
            <div class="legend-item">
              <span class="color-box" :style="{ backgroundColor: idColorMap[cls] }"></span>
              <span class="name">{{ idNameMap[cls] }}</span>
              <span class="pin-icon" v-if="lockedClasses.has(cls)">📌</span>
            </div>

            <div class="legend-details" v-show="hoveredClass === cls && !lockedClasses.has(cls)">
              <div class="detail-row">
                <span>像素数量:</span>
                <span class="highlight-text">{{ pixelCounts[cls] }} px</span>
              </div>
              <div class="detail-row">
                <span>原图占比:</span>
                <span class="highlight-text">{{ ((pixelCounts[cls] / totalPixels) * 100).toFixed(3) }}%</span>
              </div>
            </div>
          </div>

          <div v-if="filteredLegendClasses.length === 0" class="empty-hint">当前阈值下无符合条件的掩模</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, markRaw } from "vue";
import * as echarts from "echarts";

const chartRef = ref(null);
let chartInstance = null;
let baseImageObj = null;
let resizeObserver = null;

let currentZoom = 1;
let panX = 0;
let panY = 0;
let isDragging = false;
let lastMouseX = 0;
let lastMouseY = 0;

const overlayCache = {};
const boundaryCache = {};
let maskArray = null;

let imgWidth = 0;
let imgHeight = 0;

const totalPixels = ref(1);
const pixelCounts = ref({});
const maskOpacity = ref(0.6);
const maskThreshold = ref(0.1);
const hoveredClass = ref(null);

const lockedClasses = ref(new Set());

const mapping = {
  'Marine Debris': 1, 'Dense Sargassum': 2, 'Sparse Floating Algae': 3,
  'Natural Organic Material': 4, 'Ship': 5, 'Oil Spill': 6,
  'Marine Water': 7, 'Sediment-Laden Water': 8, 'Foam': 9,
  'Turbid Water': 10, 'Shallow Water': 11, 'Waves & Wakes': 12,
  'Oil Platform': 13, 'Jellyfish': 14, 'Sea snot': 15
};

const color_map = {
  'Marine Debris': 'red', 'Dense Sargassum': 'green', 'Sparse Floating Algae': 'limegreen',
  'Natural Organic Material': 'brown', 'Ship': 'orange', 'Oil Spill': 'thistle',
  'Marine Water': 'navy', 'Sediment-Laden Water': 'gold', 'Foam': 'purple',
  'Turbid Water': 'darkkhaki', 'Shallow Water': 'darkturquoise', 'Waves & Wakes': 'bisque',
  'Oil Platform': 'dimgrey', 'Jellyfish': 'hotpink', 'Sea snot': 'yellow'
};

const idColorMap = {};
const idNameMap = {};

Object.entries(mapping).forEach(([name, id]) => {
  idColorMap[id] = color_map[name];
  idNameMap[id] = name;
});

const filteredLegendClasses = computed(() => {
  const threshold = maskThreshold.value;
  return Object.keys(pixelCounts.value)
      .map(Number)
      .filter(cls => ((pixelCounts.value[cls] / totalPixels.value) * 100) >= threshold)
      .sort((a, b) => pixelCounts.value[b] - pixelCounts.value[a]);
});

onMounted(() => {
  chartInstance = markRaw(echarts.init(chartRef.value));
  init();

  resizeObserver = new ResizeObserver(() => {
    if (chartInstance) {
      chartInstance.resize();

      // 屏幕缩放时重新校验最小缩放值，防止溢出黑边
      const minZoom = getMinZoom();
      if (currentZoom < minZoom) currentZoom = minZoom;

      clampPan();
      updateTransform();
    }
  });
  resizeObserver.observe(chartRef.value);
});

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect();
  if (chartInstance) chartInstance.dispose();
});

async function init() {
  const [img, mask] = await Promise.all([
    loadImage("/7.png"),
    loadImage("/mask.png")
  ]);

  baseImageObj = img;
  imgWidth = img.width;
  imgHeight = img.height;
  totalPixels.value = imgWidth * imgHeight;

  // 👉 核心修复：使用 cover 模式充满整个容器
  currentZoom = getMinZoom();

  // 初始居中计算
  const containerW = chartRef.value.clientWidth;
  const containerH = chartRef.value.clientHeight;
  panX = (containerW - imgWidth * currentZoom) / 2;
  panY = (containerH - imgHeight * currentZoom) / 2;

  clampPan();

  processMaskData(mask);
  renderChart(); // 只执行一次全量节点挂载
  bindInteractionEvents();
}

// 👉 辅助计算：获取铺满父容器的最小缩放比例 (Cover 模式)
function getMinZoom() {
  if (!chartRef.value) return 1;
  const containerW = chartRef.value.clientWidth;
  const containerH = chartRef.value.clientHeight;
  // 使用 Math.max 确保图片的短边撑满容器，长边溢出，从而彻底消除黑边
  return Math.max(containerW / imgWidth, containerH / imgHeight);
}

// 👉 空气墙限制：限制平移不能露出背景
function clampPan() {
  if (!chartRef.value) return;
  const containerW = chartRef.value.clientWidth;
  const containerH = chartRef.value.clientHeight;
  const scaledW = imgWidth * currentZoom;
  const scaledH = imgHeight * currentZoom;

  // 因为 currentZoom 始终 >= getMinZoom()，所以 scaledW 必定 >= containerW
  // 我们将坐标严格限制在 0 到 负向最大溢出距离 之间
  panX = Math.min(0, Math.max(containerW - scaledW, panX));
  panY = Math.min(0, Math.max(containerH - scaledH, panY));
}

function processMaskData(maskImg) {
  const canvas = document.createElement("canvas");
  canvas.width = imgWidth;
  canvas.height = imgHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(maskImg, 0, 0, imgWidth, imgHeight);

  const raw = ctx.getImageData(0, 0, imgWidth, imgHeight).data;
  maskArray = new Uint8Array(imgWidth * imgHeight);
  const counts = {};

  for (let i = 0; i < raw.length; i += 4) {
    const cls = raw[i];
    const idx = i / 4;
    maskArray[idx] = cls;
    if (cls > 0) counts[cls] = (counts[cls] || 0) + 1;
  }
  pixelCounts.value = counts;

  const activeClasses = Object.keys(counts).map(Number);
  activeClasses.forEach(cls => {
    overlayCache[cls] = buildOverlayForClass(cls);
    boundaryCache[cls] = buildBoundaryCache(cls);
  });

  updateMainOverlay();
}

function buildOverlayForClass(targetClass) {
  const canvas = document.createElement("canvas");
  canvas.width = imgWidth; canvas.height = imgHeight;
  const ctx = canvas.getContext("2d");
  const imgData = ctx.createImageData(imgWidth, imgHeight);
  const data = imgData.data;

  for (let i = 0; i < maskArray.length; i++) {
    if (maskArray[i] !== targetClass) continue;
    const idx = i * 4;
    const rgb = parseRGB(idColorMap[maskArray[i]]);
    data[idx] = rgb.r; data[idx + 1] = rgb.g; data[idx + 2] = rgb.b; data[idx + 3] = 255;
  }
  ctx.putImageData(imgData, 0, 0);
  return canvas.toDataURL();
}

function buildBoundaryCache(targetCls) {
  const canvas = document.createElement("canvas");
  canvas.width = imgWidth; canvas.height = imgHeight;
  const ctx = canvas.getContext("2d");
  const imgData = ctx.createImageData(imgWidth, imgHeight);
  const data = imgData.data;

  for (let y = 0; y < imgHeight; y++) {
    for (let x = 0; x < imgWidth; x++) {
      const i = y * imgWidth + x;
      if (maskArray[i] === targetCls) {
        const isEdge = (x === 0 || x === imgWidth - 1 || y === 0 || y === imgHeight - 1) ||
                       (maskArray[i - 1] !== targetCls) || (maskArray[i + 1] !== targetCls) ||
                       (maskArray[i - imgWidth] !== targetCls) || (maskArray[i + imgWidth] !== targetCls);
        if (isEdge) {
          const idx = i * 4;
          data[idx] = 255; data[idx + 1] = 255; data[idx + 2] = 255; data[idx + 3] = 255;
        }
      }
    }
  }
  ctx.putImageData(imgData, 0, 0);
  return canvas.toDataURL();
}

function updateMainOverlay() {
  if (!maskArray) return;
  const canvas = document.createElement("canvas");
  canvas.width = imgWidth; canvas.height = imgHeight;
  const ctx = canvas.getContext("2d");
  const imgData = ctx.createImageData(imgWidth, imgHeight);
  const data = imgData.data;
  const threshold = maskThreshold.value;

  for (let i = 0; i < maskArray.length; i++) {
    const cls = maskArray[i];
    if (!cls) continue;
    if (((pixelCounts.value[cls] / totalPixels.value) * 100) < threshold) continue;

    const idx = i * 4;
    const rgb = parseRGB(idColorMap[cls]);
    data[idx] = rgb.r; data[idx + 1] = rgb.g; data[idx + 2] = rgb.b; data[idx + 3] = 255;
  }
  ctx.putImageData(imgData, 0, 0);
  overlayCache["main"] = canvas.toDataURL();
}

// 👉 核心修复：全量预挂载图层
function renderChart() {
  const children = [
    { id: 'base-layer', type: "image", style: { image: baseImageObj, width: imgWidth, height: imgHeight } },
    { id: 'mask-main', type: "image", style: { image: overlayCache["main"], width: imgWidth, height: imgHeight, opacity: maskOpacity.value } }
  ];

  // 将所有单类别图层一并挂载上去，默认透明度为 0（隐藏）
  const activeClasses = Object.keys(pixelCounts.value).map(Number);
  activeClasses.forEach(cls => {
    children.push({
      id: `mask-${cls}`, type: 'image',
      style: { image: overlayCache[cls], width: imgWidth, height: imgHeight, opacity: 0 }
    });
    children.push({
      id: `bound-${cls}`, type: 'image',
      style: { image: boundaryCache[cls], width: imgWidth, height: imgHeight, opacity: 0 }
    });
  });

  chartInstance.setOption({
    animation: false,
    graphic: [{
      id: 'main-group',
      type: "group",
      position: [panX, panY],
      scaleX: currentZoom,
      scaleY: currentZoom,
      children: children
    }]
  }, true);

  updateLayers();
}

function updateTransform() {
  chartInstance.setOption({
    graphic: [{
      id: 'main-group',
      position: [panX, panY],
      scaleX: currentZoom,
      scaleY: currentZoom
    }]
  });
}

// 👉 核心修复：现在只需修改对应 ID 的 Opacity，不再增删 DOM，彻底告别渲染错乱
function updateLayers() {
  if (!chartInstance) return;

  const activeSet = new Set(lockedClasses.value);
  if (hoveredClass.value) {
    activeSet.add(hoveredClass.value);
  }

  const showMain = activeSet.size === 0;

  // 1. 更新主遮罩
  const childrenUpdates = [
    {
      id: 'mask-main',
      style: { image: overlayCache["main"], opacity: showMain ? maskOpacity.value : 0 }
    }
  ];

  // 2. 更新独立图层透明度
  const activeClasses = Object.keys(pixelCounts.value).map(Number);
  activeClasses.forEach(cls => {
    const isActive = activeSet.has(cls);
    childrenUpdates.push({ id: `mask-${cls}`, style: { opacity: isActive ? 1 : 0 } });
    childrenUpdates.push({ id: `bound-${cls}`, style: { opacity: isActive ? 1 : 0 } });
  });

  chartInstance.setOption({
    graphic: [{
      id: 'main-group',
      children: childrenUpdates
    }]
  });
}

function bindInteractionEvents() {
  const zr = chartInstance.getZr();

  zr.on('mousedown', (e) => {
    isDragging = true;
    lastMouseX = e.offsetX;
    lastMouseY = e.offsetY;
  });

  zr.on('mousemove', (e) => {
    if (!isDragging) return;
    panX += e.offsetX - lastMouseX;
    panY += e.offsetY - lastMouseY;
    lastMouseX = e.offsetX;
    lastMouseY = e.offsetY;

    clampPan();
    updateTransform();
  });

  zr.on('mouseup', () => { isDragging = false; });
  zr.on('globalout', () => { isDragging = false; });

  zr.on('mousewheel', (e) => {
    if (e.event) e.event.preventDefault();

    const minZoom = getMinZoom();

    const zoomDelta = e.wheelDelta > 0 ? 1.15 : 0.85;
    // 强制不得小于 minZoom
    const newZoom = Math.max(minZoom, Math.min(currentZoom * zoomDelta, 30));

    const pointX = (e.offsetX - panX) / currentZoom;
    const pointY = (e.offsetY - panY) / currentZoom;

    panX = e.offsetX - pointX * newZoom;
    panY = e.offsetY - pointY * newZoom;
    currentZoom = newZoom;

    clampPan();
    updateTransform();
  });
}

watch([maskOpacity, maskThreshold], () => {
  updateMainOverlay();
  updateLayers();
});

function onLegendHover(cls) {
  hoveredClass.value = cls;
  updateLayers();
}

function onLegendLeave() {
  hoveredClass.value = null;
  updateLayers();
}

function toggleLock(cls) {
  if (lockedClasses.value.has(cls)) {
    lockedClasses.value.delete(cls);
  } else {
    lockedClasses.value.add(cls);
  }
  updateLayers();
}

function loadImage(imgSrc) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.src = imgSrc;
  });
}

function parseRGB(color) {
  const temp = document.createElement("div");
  temp.style.color = color;
  document.body.appendChild(temp);
  const rgbStr = window.getComputedStyle(temp).color;
  document.body.removeChild(temp);
  const rgb = rgbStr.match(/\d+/g).map(Number);
  return { r: rgb[0], g: rgb[1], b: rgb[2] };
}
</script>

<style scoped>
.contrast-container {
  display: flex;
  width: 100%;
  height: 100%;
  background: #f0f2f5;
  overflow: hidden;
}

.left-panel {
  flex: 1;
  position: relative;
  background: #000;
  overflow: hidden;
}

.interaction-hint {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 10;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
  pointer-events: none;
  display: flex;
  gap: 16px;
  background: rgba(0, 0, 0, 0.4);
  padding: 6px 12px;
  border-radius: 4px;
}

.chart {
  width: 100%;
  height: 100%;
  cursor: grab;
}
.chart:active {
  cursor: grabbing;
}

.right-panel {
  width: 340px;
  background: #ffffff;
  border-left: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  padding: 24px;
  box-shadow: -2px 0 10px rgba(0,0,0,0.05);
  overflow-y: auto;
}

.panel-section {
  margin-bottom: 30px;
}

.flex-grow {
  flex-grow: 1;
}

.section-title {
  font-size: 16px;
  color: #333;
  margin: 0 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #f0f2f5;
}

.control-item {
  margin-bottom: 20px;
}

.label-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
  font-weight: 500;
}

input[type="range"] {
  width: 100%;
  cursor: pointer;
}

.hint {
  font-size: 12px;
  color: #999;
  margin-top: 6px;
}

.legend-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-item-wrapper {
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
  overflow: hidden;
  user-select: none;
}

.legend-item-wrapper.is-active,
.legend-item-wrapper.is-locked {
  background: #e6f7ff;
  border-color: #91d5ff;
}

.legend-item-wrapper.is-active:not(.is-locked) {
  transform: translateX(4px);
}

.legend-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
}

.color-box {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  margin-right: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.pin-icon {
  margin-left: auto;
  font-size: 14px;
}

.legend-details {
  padding: 0 12px 12px 12px;
  font-size: 13px;
  color: #666;
  border-top: 1px dashed rgba(0,0,0,0.05);
  margin-top: -4px;
  padding-top: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.highlight-text {
  font-weight: bold;
  color: #409eff;
}

.empty-hint {
  font-size: 13px;
  color: #999;
  text-align: center;
  padding: 10px 0;
}
</style>