<script setup>
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDetectionStore } from "../stores/detection";

const router = useRouter();
const route = useRoute();
const detection = useDetectionStore();
const dragOver = ref(false);
const mode = ref(route.query.mode || "rgb");
const availableModels = ref([]);
const selectedModels = ref([]);

onMounted(() => loadModels());

async function loadModels() {
  availableModels.value = await detection.fetchModels(mode.value);
  // Pre-select all if none selected
  if (selectedModels.value.length === 0 && availableModels.value.length) {
    selectedModels.value = availableModels.value.map(m => m.name);
  }
}

async function onModeChange() {
  selectedModels.value = [];
  await loadModels();
}

function toggleModel(name) {
  const idx = selectedModels.value.indexOf(name);
  if (idx >= 0) selectedModels.value.splice(idx, 1);
  else selectedModels.value.push(name);
}

function selectAll() {
  selectedModels.value = availableModels.value.map(m => m.name);
}

function deselectAll() {
  selectedModels.value = [];
}

async function runDetection() {
  if (selectedModels.value.length === 0) {
    detection.error = "Please select at least one model";
    return;
  }
  const ok = await detection.pickAndDetect(mode.value, selectedModels.value);
  if (ok) router.push("/contrast");
}
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

      <button class="run-btn" :disabled="detection.isLoading" @click="runDetection">
        {{ detection.isLoading ? 'Running...' : `Run ${mode === 'rgb' ? 'RGB' : 'ZIP'} Detection` }}
      </button>

      <div v-if="detection.isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>Running inference...</p>
      </div>

      <div v-if="detection.error" class="error-state">
        <p>{{ detection.error }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detect-page {
  display: flex; align-items: center; justify-content: center;
  height: 100%; padding: 40px; background: #f5f7fa;
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

.run-btn {
  width: 100%; padding: 14px;
  background: #409eff; color: #fff;
  border: none; border-radius: 10px;
  font-size: 16px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.run-btn:hover:not(:disabled) { background: #337ecc; }
.run-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.hint { font-size: 12px; color: #999; margin-top: 4px; }

.loading-state {
  margin-top: 20px; display: flex; flex-direction: column;
  align-items: center; gap: 10px;
}
.spinner {
  width: 28px; height: 28px;
  border: 3px solid #e0e0e0; border-top-color: #409eff;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.error-state {
  margin-top: 16px; padding: 12px;
  background: #fff2f0; border: 1px solid #ffccc7;
  border-radius: 8px; color: #cf1322; font-size: 13px;
}
</style>
