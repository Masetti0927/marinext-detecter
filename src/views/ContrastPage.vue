<script setup>
import { ref, computed, watch, onMounted, onUnmounted, markRaw } from 'vue';
import { useI18n } from 'vue-i18n';
import * as echarts from 'echarts';
import { useDetectionStore } from '../stores/detection';
import { useMaskProcessing } from '../composables/useMaskProcessing';

const detection = useDetectionStore();
const { t } = useI18n();
const { processMaskData, buildClassOverlay, buildMainOverlay, buildBoundaryOverlay, getClassColor, getClassName } = useMaskProcessing();

function tClassName(cls) {
  return t('classes.' + getClassName(cls));
}

// --- state ---
const chartRef = ref(null);
let chart = null;
let resizeObserver = null;

const imgWidth = ref(0);
const imgHeight = ref(0);
const totalPixels = ref(1);
const pixelCounts = ref({});
const activeClasses = computed(() => Object.keys(pixelCounts.value).map(Number));
const maskOpacity = ref(0.4);
const maskVisible = ref(true);
const maskThreshold = ref(0.1);
const hoveredClass = ref(null);
const lockedClasses = ref(new Set());

let baseImage = null;
let maskImage = null;
let maskArray = null;
const overlayCache = {};
const boundaryCache = {};

const IMAGE_MARGIN = 24;
let zoom = 1, panX = 0, panY = 0;
let dragging = false, lastX = 0, lastY = 0;

const filteredLegend = computed(() => {
  const t = maskThreshold.value;
  return activeClasses.value
    .filter(cls => ((pixelCounts.value[cls] || 0) / totalPixels.value) * 100 >= t)
    .sort((a, b) => (pixelCounts.value[b] || 0) - (pixelCounts.value[a] || 0));
});

const opacitySliderBg = computed(() =>
  `linear-gradient(to right, #b3d8ff 0%, #b3d8ff ${maskOpacity.value * 100}%, #e0e0e0 ${maskOpacity.value * 100}%, #e0e0e0 100%)`
);
const thresholdSliderBg = computed(() =>
  `linear-gradient(to right, #b3d8ff 0%, #b3d8ff ${(maskThreshold.value / 5) * 100}%, #e0e0e0 ${(maskThreshold.value / 5) * 100}%, #e0e0e0 100%)`
);

// --- lifecycle ---
onMounted(async () => {
  if (detection.currentId) await init();
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  chart?.dispose();
});

watch([maskOpacity, maskThreshold, maskVisible], () => {
  refreshMainOverlay();
  applyLayerVisibility();
});

watch(() => detection.currentId, async (id) => {
  if (id && !chart) await init();
});

// --- init ---
async function init() {
  chart = markRaw(echarts.init(chartRef.value));

  const mask = await loadImage(detection.maskBase64);
  maskImage = mask;

  let orig;
  if (detection.originalBase64) {
    orig = await loadImage(detection.originalBase64);
  } else {
    // Multi-channel mode: create a blank canvas with mask dimensions
    orig = new Image();
    orig.width = mask.width;
    orig.height = mask.height;
    const c = document.createElement('canvas');
    c.width = mask.width;
    c.height = mask.height;
    c.getContext('2d').fillStyle = '#1a1a1a';
    c.getContext('2d').fillRect(0, 0, mask.width, mask.height);
    orig.src = c.toDataURL();
    await new Promise(r => { orig.onload = r; });
  }
  baseImage = orig;
  imgWidth.value = orig.width;
  imgHeight.value = orig.height;
  totalPixels.value = orig.width * orig.height;

  const { maskArray: arr, counts } = processMaskData(mask, orig.width, orig.height);
  maskArray = arr;
  pixelCounts.value = counts;

  activeClasses.value.forEach(cls => {
    overlayCache[cls] = buildClassOverlay(maskArray, cls, imgWidth.value, imgHeight.value);
    boundaryCache[cls] = buildBoundaryOverlay(maskArray, cls, imgWidth.value, imgHeight.value);
  });
  refreshMainOverlay();

  zoom = fitZoom();
  const cw = chartRef.value.clientWidth;
  const ch = chartRef.value.clientHeight;
  panX = (cw - imgWidth.value * zoom) / 2;
  panY = (ch - imgHeight.value * zoom) / 2;
  clampPan();

  renderAllLayers();
  bindEvents();

  resizeObserver = new ResizeObserver(() => {
    chart?.resize();
    const mz = fitZoom();
    if (zoom < mz) zoom = mz;
    clampPan();
    applyTransform();
  });
  resizeObserver.observe(chartRef.value);
}

// --- zoom/pan helpers ---
function fitZoom() {
  if (!chartRef.value) return 1;
  const m = IMAGE_MARGIN;
  return Math.min(
    (chartRef.value.clientWidth - 2 * m) / imgWidth.value,
    (chartRef.value.clientHeight - 2 * m) / imgHeight.value
  );
}

function clampPan() {
  if (!chartRef.value) return;
  const cw = chartRef.value.clientWidth;
  const ch = chartRef.value.clientHeight;
  const sw = imgWidth.value * zoom;
  const sh = imgHeight.value * zoom;
  const m = IMAGE_MARGIN;
  // Center when image fits within margin, clamp to margin when it overflows
  panX = sw <= cw - 2 * m ? (cw - sw) / 2 : Math.min(m, Math.max(cw - sw - m, panX));
  panY = sh <= ch - 2 * m ? (ch - sh) / 2 : Math.min(m, Math.max(ch - sh - m, panY));
}

// --- rendering ---
function renderAllLayers() {
  const children = [
    { id: 'base', type: 'image', style: { image: baseImage, width: imgWidth.value, height: imgHeight.value } },
    { id: 'mask-main', type: 'image', style: { image: overlayCache['main'], width: imgWidth.value, height: imgHeight.value, opacity: maskOpacity.value } }
  ];

  activeClasses.value.forEach(cls => {
    children.push({ id: `mask-${cls}`, type: 'image', style: { image: overlayCache[cls], width: imgWidth.value, height: imgHeight.value, opacity: 0 } });
    children.push({ id: `bound-${cls}`, type: 'image', style: { image: boundaryCache[cls], width: imgWidth.value, height: imgHeight.value, opacity: 0 } });
  });

  chart.setOption({
    animation: false,
    graphic: [{ id: 'group', type: 'group', position: [panX, panY], scaleX: zoom, scaleY: zoom, children }]
  }, true);

  applyLayerVisibility();
}

function applyTransform() {
  chart?.setOption({ graphic: [{ id: 'group', position: [panX, panY], scaleX: zoom, scaleY: zoom }] });
}

function applyLayerVisibility() {
  if (!chart) return;
  const active = new Set(lockedClasses.value);
  if (hoveredClass.value) active.add(hoveredClass.value);
  const showMain = maskVisible.value && active.size === 0;

  const updates = [
    { id: 'mask-main', style: { image: overlayCache['main'], opacity: showMain ? maskOpacity.value : 0 } }
  ];
  activeClasses.value.forEach(cls => {
    const on = active.has(cls);
    updates.push({ id: `mask-${cls}`, style: { opacity: on ? 1 : 0 } });
    updates.push({ id: `bound-${cls}`, style: { opacity: on ? 1 : 0 } });
  });

  chart.setOption({ graphic: [{ id: 'group', children: updates }] });
}

function refreshMainOverlay() {
  if (!maskArray) return;
  overlayCache['main'] = buildMainOverlay(maskArray, pixelCounts.value, totalPixels.value, maskThreshold.value, imgWidth.value, imgHeight.value);
}

// --- events ---
function bindEvents() {
  const zr = chart.getZr();
  zr.on('mousedown', e => { dragging = true; lastX = e.offsetX; lastY = e.offsetY; });
  zr.on('mousemove', e => {
    if (!dragging) return;
    panX += e.offsetX - lastX;
    panY += e.offsetY - lastY;
    lastX = e.offsetX;
    lastY = e.offsetY;
    clampPan();
    applyTransform();
  });
  zr.on('mouseup', () => { dragging = false; });
  zr.on('globalout', () => { dragging = false; });
  zr.on('mousewheel', e => {
    e.event?.preventDefault();
    const mz = fitZoom();
    const delta = e.wheelDelta > 0 ? 1.15 : 0.85;
    const nz = Math.max(mz, Math.min(zoom * delta, 30));
    const px = (e.offsetX - panX) / zoom;
    const py = (e.offsetY - panY) / zoom;
    panX = e.offsetX - px * nz;
    panY = e.offsetY - py * nz;
    zoom = nz;
    clampPan();
    applyTransform();
  });
}

function onLegendHover(cls) { hoveredClass.value = cls; applyLayerVisibility(); }
function onLegendLeave() { hoveredClass.value = null; applyLayerVisibility(); }
function toggleLock(cls) {
  if (lockedClasses.value.has(cls)) lockedClasses.value.delete(cls);
  else lockedClasses.value.add(cls);
  applyLayerVisibility();
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = src;
  });
}
</script>

<template>
  <div class="contrast-root" v-if="!detection.currentId">
    <div class="empty-state">
      <p>{{ t('contrast.noData') }}</p>
      <router-link to="/detect" class="btn-primary">{{ t('contrast.runDetection') }}</router-link>
    </div>
  </div>

  <div class="contrast-root" v-else>
    <div class="canvas-panel">
      <div class="hint-bar">
        <span>{{ t('contrast.scrollZoom') }}</span>
        <span>{{ t('contrast.dragPan') }}</span>
        <span v-if="lockedClasses.size">{{ lockedClasses.size }} {{ t('contrast.locked') }}</span>
      </div>
      <div ref="chartRef" class="echarts-host"></div>
    </div>

    <aside class="side-panel">
      <section class="panel-block">
        <h4>{{ t('contrast.controls') }}</h4>
        <div class="toggle-row">
          <span>{{ t('contrast.showMask') }}</span>
          <label class="toggle-switch">
            <input type="checkbox" v-model="maskVisible" />
            <span class="toggle-track"></span>
          </label>
        </div>

        <label class="slider-row">
          <span>{{ t('contrast.opacity') }}</span>
          <span class="slider-val">{{ Math.round(maskOpacity * 100) }}%</span>
        </label>
        <input type="range" min="0" max="1" step="0.05" v-model="maskOpacity" class="slider" :style="{ background: opacitySliderBg }" />

        <label class="slider-row">
          <span>{{ t('contrast.threshold') }}</span>
          <span class="slider-val">{{ maskThreshold }}%</span>
        </label>
        <input type="range" min="0" max="5" step="0.1" v-model="maskThreshold" class="slider" :style="{ background: thresholdSliderBg }" />
        <p class="hint">{{ t('contrast.thresholdHint') }}</p>
      </section>

      <section class="panel-block legend-block">
        <h4>{{ t('contrast.classes') }}</h4>
        <div class="legend-list" v-if="filteredLegend.length">
          <div
            v-for="cls in filteredLegend" :key="cls"
            class="legend-row"
            :class="{ hover: hoveredClass === cls, locked: lockedClasses.has(cls) }"
            @mouseenter="onLegendHover(cls)"
            @mouseleave="onLegendLeave"
            @click="toggleLock(cls)"
          >
            <span class="swatch" :style="{ background: getClassColor(cls) }"></span>
            <span class="cls-name">{{ tClassName(cls) }}</span>
            <span v-if="lockedClasses.has(cls)" class="lock-icon">P</span>
            <div class="cls-detail" v-show="hoveredClass === cls || lockedClasses.has(cls)">
              <span>{{ (pixelCounts[cls] || 0).toLocaleString() }} {{ t('contrast.px') }}</span>
              <span>{{ ((pixelCounts[cls] || 0) / totalPixels * 100).toFixed(3) }}%</span>
            </div>
          </div>
        </div>
        <p v-else class="empty">{{ t('contrast.noClasses') }}</p>
      </section>
    </aside>
  </div>
</template>

<style scoped>
.contrast-root {
  display: flex;
  height: 100%;
  background: #f3f4f6;
  overflow: hidden;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #888;
  font-size: 14px;
  height: 100%;
}

.btn-primary {
  padding: 10px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  background: #5b8def;
  color: #fff;
  text-decoration: none;
  display: inline-block;
}

.canvas-panel {
  flex: 1;
  position: relative;
  background: #f3f4f6;
  overflow: hidden;
}
.hint-bar {
  position: absolute;
  top: 12px; left: 12px;
  z-index: 10;
  display: flex; gap: 16px;
  color: #6b7280;
  font-size: 12px;
  background: rgba(255,255,255,0.85);
  border: 1px solid #e5e7eb;
  padding: 4px 12px;
  border-radius: 8px;
  pointer-events: none;
}
.echarts-host {
  width: 100%;
  height: 100%;
  cursor: grab;
}
.echarts-host:active { cursor: grabbing; }

.side-panel {
  width: 300px;
  background: #fff;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 20px;
}
.panel-block {
  margin-bottom: 24px;
}
.panel-block h4 {
  font-size: 14px;
  color: #374151;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 2px solid #f3f4f6;
}

/* Unified slider styles */
.slider-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #666;
  margin: 8px 0 4px;
}
.slider-val {
  font-weight: 500;
  color: #409eff;
}
.slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e0e0e0;
  outline: none;
  cursor: pointer;
}
.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #409eff;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform 0.1s;
}
.slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}
.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #409eff;
  cursor: pointer;
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.hint { font-size: 11px; color: #999; margin-top: 4px; }

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #666;
  margin-bottom: 16px;
}
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  cursor: pointer;
}
.toggle-switch input { display: none; }
.toggle-track {
  position: absolute;
  inset: 0;
  background: #ccc;
  border-radius: 12px;
  transition: background 0.2s;
}
.toggle-track::before {
  content: '';
  position: absolute;
  top: 2px; left: 2px;
  width: 20px; height: 20px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.toggle-switch input:checked + .toggle-track {
  background: #409eff;
}
.toggle-switch input:checked + .toggle-track::before {
  transform: translateX(20px);
}

.legend-block { flex: 1; }
.legend-list { display: flex; flex-direction: column; gap: 6px; }
.legend-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 10px;
  background: #f8f9fa;
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
  font-size: 13px;
}
.legend-row.hover { background: #e6f7ff; border-color: #91d5ff; }
.legend-row.locked { background: #e6f7ff; border-color: #409eff; }
.swatch {
  width: 14px; height: 14px;
  border-radius: 3px;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.cls-name { flex: 1; font-weight: 500; color: #333; }
.lock-icon { font-size: 11px; color: #409eff; font-weight: 700; }
.cls-detail {
  width: 100%;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
  padding-top: 4px;
  border-top: 1px dashed rgba(0,0,0,0.05);
}
.empty { font-size: 13px; color: #999; text-align: center; padding: 16px 0; }
</style>
