<script setup>
import { useRouter } from "vue-router";
import { useHistoryStore } from "../stores/history";

const router = useRouter();
const history = useHistoryStore();

function goDetect(mode) {
  router.push({ path: "/detect", query: { mode } });
}

async function goToHistory() {
  await history.loadHistory();
  router.push("/history");
}
</script>

<template>
  <div class="home-page">
    <div class="hero">
      <h1>MarineXt Detector</h1>
      <p class="subtitle">15-Class Marine Semantic Segmentation</p>
    </div>

    <div class="card-grid">
      <button class="mode-card" @click="goDetect('rgb')">
        <div class="card-icon">🖼</div>
        <h2>RGB Image Detection</h2>
        <p>Load a 240x240 RGB satellite image and run semantic segmentation inference.</p>
        <span class="card-tag">PNG / JPG / TIFF</span>
      </button>

      <button class="mode-card" @click="goDetect('multi')">
        <div class="card-icon">📦</div>
        <h2>Multi-Channel ZIP</h2>
        <p>Load a ZIP archive containing multi-spectral channel images for inference.</p>
        <span class="card-tag">ZIP Archive</span>
      </button>

      <button class="mode-card" @click="goToHistory">
        <div class="card-icon">⏰</div>
        <h2>View History</h2>
        <p>Browse, search, and filter previous detection results and reports.</p>
        <span class="card-tag">Browse Records</span>
      </button>
    </div>

  </div>
</template>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 48px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f2 100%);
}

.hero {
  text-align: center;
  margin-bottom: 48px;
}

.hero h1 {
  font-size: 36px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 16px;
  color: #666;
}

.card-grid {
  display: flex;
  gap: 24px;
  max-width: 900px;
  width: 100%;
}

.mode-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 24px;
  background: #fff;
  border: 2px solid #e0e0e0;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.mode-card:hover {
  border-color: #409eff;
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.12);
}

.card-icon {
  font-size: 40px;
  margin-bottom: 16px;
}

.mode-card h2 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.mode-card p {
  font-size: 13px;
  color: #888;
  line-height: 1.5;
  flex: 1;
}

.card-tag {
  margin-top: 16px;
  font-size: 11px;
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
  padding: 4px 12px;
  border-radius: 12px;
}

.error-banner {
  margin-top: 24px;
  padding: 12px 24px;
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 8px;
  color: #cf1322;
  font-size: 13px;
}
</style>
