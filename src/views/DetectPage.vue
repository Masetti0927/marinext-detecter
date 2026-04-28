<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDetectionStore } from "../stores/detection";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

const router = useRouter();
const route = useRoute();
const detection = useDetectionStore();
const mode = ref(route.query.mode || "rgb");
const availableModels = ref([]);
const selectedModels = ref([]);

onMounted(() => loadModels());

async function loadModels() {
  availableModels.value = await detection.fetchModels(mode.value);
  if (selectedModels.value.length === 0 && availableModels.value.length) {
    selectedModels.value = availableModels.value.map(m => m.name);
  }
}

async function onModeChange() {
  selectedModels.value = [];
  cropImage.value = null;
  cropDataUrl.value = '';
  await loadModels();
}

function toggleModel(name) {
  const idx = selectedModels.value.indexOf(name);
  if (idx >= 0) selectedModels.value.splice(idx, 1);
  else selectedModels.value.push(name);
}

function selectAll() { selectedModels.value = availableModels.value.map(m => m.name); }
function deselectAll() { selectedModels.value = []; }

// --- crop editor state ---
const cropStage = ref(null);
const cropImage = ref(null);
const cropDataUrl = ref('');
const imagePath = ref('');
const scale = ref(1);
const rotation = ref(0);
const cropRect = reactive({ x: 80, y: 60, w: 260, h: 220 });

const drag = reactive({
  active: false,
  mode: '',  // 'move' | 'resize'
  startX: 0,
  startY: 0,
  origX: 0,
  origY: 0,
  origW: 0,
  origH: 0,
});

const imageStyle = computed(() => ({
  transform: `translate(-50%, -50%) scale(${scale.value}) rotate(${rotation.value}deg)`,
  transformOrigin: 'center center',
}));

const cropBoxStyle = computed(() => ({
  left: cropRect.x + 'px',
  top: cropRect.y + 'px',
  width: cropRect.w + 'px',
  height: cropRect.h + 'px',
}));

function initCrop() {
  const el = cropStage.value;
  if (!el) return;
  const cw = el.clientWidth;
  const ch = el.clientHeight;
  cropRect.x = Math.round(cw * 0.15);
  cropRect.y = Math.round(ch * 0.1);
  cropRect.w = Math.round(cw * 0.7);
  cropRect.h = Math.round(ch * 0.8);
}

async function pickImage() {
  const filePath = await open({
    filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "bmp", "tiff"] }],
    multiple: false,
  });
  if (!filePath) return;

  imagePath.value = filePath;
  const b64 = await invoke("get_image_base64", { path: filePath });
  cropDataUrl.value = b64;

  const img = new Image();
  img.onload = () => {
    cropImage.value = img;
    scale.value = 1;
    rotation.value = 0;
    nextTick(() => initCrop());
  };
  img.src = b64;
}

// --- zoom ---
function zoomIn() { scale.value = Math.min(5, scale.value + 0.1); }
function zoomOut() { scale.value = Math.max(0.2, scale.value - 0.1); }
function rotateCw() { rotation.value += 90; }
function rotateCcw() { rotation.value -= 90; }
function resetCrop() { scale.value = 1; rotation.value = 0; nextTick(() => initCrop()); }

function onWheel(e) {
  e.preventDefault();
  if (e.deltaY < 0) zoomIn();
  else zoomOut();
}

// --- mouse handlers ---
function startDrag(e) {
  e.preventDefault();
  drag.active = true;
  drag.mode = 'move';
  drag.startX = e.clientX;
  drag.startY = e.clientY;
  drag.origX = cropRect.x;
  drag.origY = cropRect.y;
}

function startResize(e) {
  e.stopPropagation();
  e.preventDefault();
  drag.active = true;
  drag.mode = 'resize';
  drag.startX = e.clientX;
  drag.startY = e.clientY;
  drag.origW = cropRect.w;
  drag.origH = cropRect.h;
}

function onMouseMove(e) {
  if (!drag.active) return;

  if (drag.mode === 'move') {
    cropRect.x = drag.origX + (e.clientX - drag.startX);
    cropRect.y = drag.origY + (e.clientY - drag.startY);
    // Clamp to stage bounds
    const el = cropStage.value;
    if (el) {
      cropRect.x = Math.max(0, Math.min(el.clientWidth - cropRect.w, cropRect.x));
      cropRect.y = Math.max(0, Math.min(el.clientHeight - cropRect.h, cropRect.y));
    }
  } else if (drag.mode === 'resize') {
    cropRect.w = Math.max(60, drag.origW + (e.clientX - drag.startX));
    cropRect.h = Math.max(60, drag.origH + (e.clientY - drag.startY));
    // Clamp
    const el = cropStage.value;
    if (el) {
      cropRect.w = Math.min(el.clientWidth - cropRect.x, cropRect.w);
      cropRect.h = Math.min(el.clientHeight - cropRect.y, cropRect.h);
    }
  }
}

function onMouseUp() {
  drag.active = false;
  drag.mode = '';
}

// --- detect ---
async function confirmAndDetect() {
  if (!cropImage.value || selectedModels.value.length === 0) {
    detection.error = "Please select an image and at least one model";
    return;
  }

  detection.isLoading = true;
  detection.error = "";

  try {
    const img = cropImage.value;
    const s = scale.value;
    const rot = ((rotation.value % 360) + 360) % 360;
    const cr = cropRect;
    const el = cropStage.value;
    const sw = el.clientWidth;
    const sh = el.clientHeight;

    // Image center is at stage center; image is scaled by s around its center
    // Crop rect is in stage coordinates. Map to image coordinates.
    const cx = cr.x + cr.w / 2 - sw / 2;
    const cy = cr.y + cr.h / 2 - sh / 2;

    // Reverse scale: how many image pixels per stage pixel = 1/s
    // The crop width/height in image pixels = cr.w / s, cr.h / s
    let icx, icy, icw, ich;
    const rad = (rot * Math.PI) / 180;
    const cos = Math.cos(-rad);
    const sin = Math.sin(-rad);

    // Rotate the crop center back to find its position on the unrotated image
    const ricx = cx * cos - cy * sin;
    const ricy = cx * sin + cy * cos;

    // Convert to image coordinates (top-left origin, image space)
    icw = cr.w / s;
    ich = cr.h / s;
    icx = ricx / s + img.width / 2 - icw / 2;
    icy = ricy / s + img.height / 2 - ich / 2;

    // Clamp to image bounds
    icx = Math.max(0, Math.min(img.width - 1, icx));
    icy = Math.max(0, Math.min(img.height - 1, icy));
    icw = Math.min(icw, img.width - icx);
    ich = Math.min(ich, img.height - icy);

    // Render cropped region
    const outCanvas = document.createElement('canvas');
    outCanvas.width = Math.round(icw);
    outCanvas.height = Math.round(ich);
    const ctx = outCanvas.getContext('2d');

    // Draw rotated image then extract crop
    ctx.save();
    ctx.translate(-icx, -icy);
    if (rot !== 0) {
      ctx.translate(img.width / 2, img.height / 2);
      ctx.rotate(rad);
      ctx.translate(-img.width / 2, -img.height / 2);
    }
    ctx.drawImage(img, 0, 0);
    ctx.restore();

    const base64Data = outCanvas.toDataURL('image/png');

    // Extract original filename from path
    const parts = imagePath.value.split(/[/\\]/);
    const originalFileName = parts[parts.length - 1] || "image.png";

    const result = await invoke("detect_rgb_data", {
      base64Data,
      modelNames: selectedModels.value,
      fileName: originalFileName,
    });

    // Pinia unwraps refs — assign directly, no .value needed
    detection.originalPath = result.original_path;
    detection.maskPath = result.mask_path;
    detection.originalBase64 = result.original_base64;
    detection.maskBase64 = result.mask_base64;
    detection.stats = result.stats;
    detection.totalPixels = result.total_pixels;
    detection.currentId = result.id;
    detection.mode = "rgb";

    router.push("/contrast");
  } catch (e) {
    detection.error = String(e);
  } finally {
    detection.isLoading = false;
  }
}

// --- multi mode ---
async function runMultiDetection() {
  if (selectedModels.value.length === 0) {
    detection.error = "Please select at least one model";
    return;
  }
  const ok = await detection.pickAndDetect(mode.value, selectedModels.value);
  if (ok) router.push("/contrast");
}

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
});

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onMouseMove);
  window.removeEventListener('mouseup', onMouseUp);
});
</script>

<template>
  <div class="detect-page">
    <div class="detect-container">
      <h2>Run Detection</h2>

      <div class="mode-tabs">
        <button :class="{ active: mode === 'rgb' }" @click="mode = 'rgb'; onModeChange()">RGB Image</button>
        <button :class="{ active: mode === 'multi' }" @click="mode = 'multi'; onModeChange()">Multi-Channel ZIP</button>
      </div>

      <div class="section">
        <h3>Models <span class="badge">{{ selectedModels.length }}/{{ availableModels.length }}</span></h3>
        <div class="model-actions">
          <button class="link-btn" @click="selectAll">Select all</button>
          <button class="link-btn" @click="deselectAll">Deselect all</button>
        </div>
        <div v-if="availableModels.length === 0" class="hint">
          No .onnx models found in models/{{ mode }}/. Place your models there.
        </div>
        <div class="model-list">
          <label
            v-for="m in availableModels" :key="m.name"
            class="model-chip"
            :class="{ checked: selectedModels.includes(m.name) }"
          >
            <input type="checkbox" :checked="selectedModels.includes(m.name)" @change="toggleModel(m.name)" />
            {{ m.name }}
          </label>
        </div>
      </div>

      <!-- RGB mode: crop editor -->
      <template v-if="mode === 'rgb'">
        <div class="section" v-if="!cropImage">
          <button class="pick-btn" @click="pickImage">Pick Image</button>
        </div>

        <div class="crop-editor" v-if="cropImage">
          <div class="crop-toolbar">
            <button @click="rotateCcw" title="Rotate Left">&#x21BA;</button>
            <button @click="rotateCw" title="Rotate Right">&#x21BB;</button>
            <button @click="zoomOut" title="Zoom Out">&minus;</button>
            <span class="zoom-label">{{ Math.round(scale * 100) }}%</span>
            <button @click="zoomIn" title="Zoom In">+</button>
            <button @click="resetCrop" class="reset-btn">Reset</button>
            <button @click="cropImage = null; cropDataUrl = ''" class="reset-btn">Change Image</button>
          </div>

          <div class="crop-stage" ref="cropStage" @wheel.prevent="onWheel">
            <img
              :src="cropDataUrl"
              class="crop-img"
              :style="imageStyle"
            />
            <div
              class="crop-box"
              :style="cropBoxStyle"
              @mousedown="startDrag"
            >
              <span
                class="resize-handle"
                @mousedown="startResize"
              ></span>
            </div>
          </div>

          <button class="run-btn" :disabled="detection.isLoading" @click="confirmAndDetect">
            {{ detection.isLoading ? 'Running...' : 'Confirm & Detect' }}
          </button>
        </div>
      </template>

      <!-- Multi mode: direct run -->
      <template v-if="mode === 'multi'">
        <button class="run-btn" :disabled="detection.isLoading" @click="runMultiDetection">
          {{ detection.isLoading ? 'Running...' : 'Pick ZIP & Detect' }}
        </button>
      </template>

    </div>
  </div>
</template>

<style scoped>
.detect-page {
  display: flex; align-items: center; justify-content: center;
  height: 100%; padding: 40px; background: #f5f7fa;
  overflow-y: auto;
}
.detect-container {
  max-width: 560px; width: 100%;
}
h2 { font-size: 22px; color: #1a1a2e; margin-bottom: 20px; }

.mode-tabs {
  display: flex; gap: 0; margin-bottom: 24px;
  border-radius: 8px; overflow: hidden; border: 1px solid #d0d5dd;
}
.mode-tabs button {
  flex: 1; padding: 10px; border: none;
  background: #fff; cursor: pointer; font-size: 14px;
  transition: all 0.15s;
}
.mode-tabs button.active {
  background: #409eff; color: #fff;
}

.section { margin-bottom: 24px; }
.section h3 { font-size: 15px; color: #333; margin-bottom: 8px; }
.badge {
  font-size: 12px; color: #409eff;
  background: rgba(64,158,255,0.1);
  padding: 2px 8px; border-radius: 10px; margin-left: 8px;
}
.model-actions { display: flex; gap: 12px; margin-bottom: 8px; }
.link-btn {
  background: none; border: none; color: #409eff;
  font-size: 12px; cursor: pointer;
}
.model-list { display: flex; flex-wrap: wrap; gap: 8px; }
.model-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 14px;
  border: 1px solid #d9d9d9; border-radius: 16px;
  font-size: 13px; cursor: pointer;
  transition: all 0.15s;
  background: #fff;
}
.model-chip.checked { border-color: #409eff; background: #e6f7ff; }
.model-chip input { display: none; }

.pick-btn {
  width: 100%; padding: 14px;
  background: #fff; color: #409eff;
  border: 2px dashed #409eff; border-radius: 10px;
  font-size: 16px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.pick-btn:hover { background: #ecf5ff; }

/* --- crop editor --- */
.crop-editor {
  margin-bottom: 24px;
}
.crop-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.crop-toolbar button {
  width: 32px; height: 32px;
  border: 1px solid #d9d9d9; border-radius: 6px;
  background: #fff; cursor: pointer;
  font-size: 16px; display: flex;
  align-items: center; justify-content: center;
  transition: all 0.15s;
}
.crop-toolbar button:hover { border-color: #409eff; color: #409eff; }
.crop-toolbar .zoom-label {
  font-size: 12px; color: #666;
  min-width: 40px; text-align: center;
}
.crop-toolbar .reset-btn {
  width: auto; padding: 0 10px;
  font-size: 12px; margin-left: auto;
}

.crop-stage {
  position: relative;
  width: 100%;
  height: 360px;
  background: #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
  user-select: none;
}

.crop-img {
  position: absolute;
  left: 50%;
  top: 50%;
  max-width: none;
  pointer-events: none;
}

.crop-box {
  position: absolute;
  border: 2px solid #409eff;
  background: rgba(64,158,255,0.08);
  cursor: move;
  box-shadow: 0 0 0 9999px rgba(0,0,0,0.4);
}

.resize-handle {
  position: absolute;
  right: -7px;
  bottom: -7px;
  width: 14px;
  height: 14px;
  background: #409eff;
  border-radius: 50%;
  cursor: nwse-resize;
}

.hint { font-size: 12px; color: #999; margin-top: 4px; }

.run-btn {
  width: 100%; padding: 14px;
  background: #409eff; color: #fff;
  border: none; border-radius: 10px;
  font-size: 16px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.run-btn:hover:not(:disabled) { background: #337ecc; }
.run-btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
