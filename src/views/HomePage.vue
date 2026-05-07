<script setup>
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useHistoryStore } from "../stores/history";

const router = useRouter();
const history = useHistoryStore();
const { t } = useI18n();

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
      <h1>{{ t('home.heroTitle') }}</h1>
      <p class="subtitle">{{ t('home.heroSubtitle') }}</p>
    </div>

    <div class="card-grid">
      <button class="mode-card" @click="goDetect('rgb')">
        <div class="card-icon">🖼</div>
        <h2>{{ t('home.rgbTitle') }}</h2>
        <p>{{ t('home.rgbDesc') }}</p>
        <span class="card-tag">{{ t('home.rgbTag') }}</span>
      </button>

      <button class="mode-card" @click="goDetect('multi')">
        <div class="card-icon">📦</div>
        <h2>{{ t('home.multiTitle') }}</h2>
        <p>{{ t('home.multiDesc') }}</p>
        <span class="card-tag">{{ t('home.multiTag') }}</span>
      </button>

      <button class="mode-card" @click="goToHistory">
        <div class="card-icon">⏰</div>
        <h2>{{ t('home.historyTitle') }}</h2>
        <p>{{ t('home.historyDesc') }}</p>
        <span class="card-tag">{{ t('home.historyTag') }}</span>
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
  background: linear-gradient(135deg, #f8fafc 0%, #eef1f5 100%);
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
  border: 1.5px solid #e5e7eb;
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
