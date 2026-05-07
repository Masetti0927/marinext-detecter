<template>
  <div class="report-page">
    <div class="report-header">
      <h2>{{ t('report.title') }}</h2>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="goToCharts">{{ t('report.charts') }}</button>
        <button class="btn btn-primary" @click="exportXlsx">{{ t('report.exportXlsx') }}</button>
      </div>
    </div>

    <div v-if="!detection.currentId" class="empty-state">
      <p>{{ t('report.noData') }}</p>
      <router-link to="/detect" class="btn btn-primary">{{ t('report.runDetection') }}</router-link>
    </div>

    <div v-else class="report-body" ref="reportRef">
      <div class="report-section pollution-card" :class="pollutionLevelClass">
        <p class="methodology-note">{{ t('report.methodologyNote') }}</p>
        <div class="pollution-main">
          <div class="pollution-score-wrap">
            <div class="pollution-score">{{ pollutionIndex }}</div>
            <div class="pollution-scale">{{ t('report.per10') }}</div>
          </div>
          <div class="pollution-info">
            <h3>{{ t('report.pollutionIndex') }}</h3>
            <div class="pollution-level">{{ pollutionLabel }}</div>
            <p class="pollution-desc">{{ pollutionDesc }}</p>
          </div>
        </div>
        <div class="pollution-bar-wrap">
          <div class="pollution-bar">
            <div class="pollution-fill" :style="{ width: (pollutionIndex / 10 * 100) + '%' }"></div>
          </div>
          <div class="pollution-ticks">
            <span>{{ t('pollution.clean') }}</span><span>{{ t('pollution.light') }}</span><span>{{ t('pollution.moderate') }}</span><span>{{ t('pollution.heavy') }}</span><span>{{ t('pollution.severe') }}</span>
          </div>
        </div>
        <details class="methodology-details">
          <summary>{{ t('report.methodology') }}</summary>
          <div class="methodology-content" v-html="t('report.methodologyContent')"></div>
        </details>
      </div>

      <!-- Summary -->
      <div class="report-section">
        <h3>{{ t('report.summary') }}</h3>
        <table class="info-table">
          <tr><td class="label">{{ t('report.file') }}</td><td>{{ fileName }}</td></tr>
          <tr><td class="label">{{ t('report.mode') }}</td><td>{{ detection.mode }}</td></tr>
          <tr><td class="label">{{ t('report.imageSize') }}</td><td>{{ detection.totalPixels?.toLocaleString() }} px</td></tr>
          <tr><td class="label">{{ t('report.classesDetected') }}</td><td>{{ Object.keys(detection.stats).length }} / 15</td></tr>
          <tr><td class="label">{{ t('report.dominantClass') }}</td><td>{{ tClassName(dominantClassName) }}</td></tr>
          <tr><td class="label">{{ t('report.pollutionLevel') }}</td><td><span :class="'level-badge ' + pollutionLevelClass">{{ pollutionLabel }}</span></td></tr>
        </table>
      </div>

      <!-- Pollution Contribution Breakdown -->
      <div class="report-section">
        <h3>{{ t('report.pollutionContribution') }}</h3>
        <table class="stats-table">
          <thead>
            <tr><th>{{ t('report.classCol') }}</th><th>{{ t('report.idCol') }}</th><th>{{ t('report.pixelPctCol') }}</th><th>{{ t('report.weightCol') }}</th><th>{{ t('report.contributionCol') }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(stat, name) in sortedStats" :key="name"
              :class="{ 'polluter-row': POLLUTION_WEIGHTS[stat.class_id] >= 7 }">
              <td>{{ tClassName(name) }}</td>
              <td>{{ stat.class_id }}</td>
              <td>{{ stat.percentage }}%</td>
              <td>{{ POLLUTION_WEIGHTS[stat.class_id] || 0 }}/10</td>
              <td>
                <div class="contrib-bar-wrap">
                  <div class="contrib-bar" :style="{ width: contribPercent(stat) + '%', backgroundColor: getBarColor(stat) }"></div>
                  <span class="contrib-val">{{ contribPercent(stat) }}%</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Per-Class Statistics -->
      <div class="report-section">
        <h3>{{ t('report.perClassStats') }}</h3>
        <table class="stats-table">
          <thead>
            <tr><th>{{ t('report.classCol') }}</th><th>{{ t('report.idCol') }}</th><th>{{ t('report.pixelCountCol') }}</th><th>{{ t('report.percentageCol') }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(stat, name) in sortedStats" :key="name">
              <td>{{ tClassName(name) }}</td>
              <td>{{ stat.class_id }}</td>
              <td>{{ stat.pixel_count?.toLocaleString() }}</td>
              <td>{{ stat.percentage }}%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Chart -->
      <div class="report-section">
        <h3>{{ t('report.classCoverage') }}</h3>
        <div ref="miniChartRef" class="mini-chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, markRaw, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import * as echarts from "echarts";
import * as XLSX from "xlsx";
import { useRouter } from "vue-router";
import { useDetectionStore } from "../stores/detection";
import { COLOR_MAP, CLASS_NAMES } from "../composables/useMaskProcessing";
import { invoke } from "@tauri-apps/api/core";
import { save } from "@tauri-apps/plugin-dialog";

const router = useRouter();
const detection = useDetectionStore();
const { t } = useI18n();

function tClassName(enName) {
  return t('classes.' + enName);
}

const reportRef = ref(null);
const miniChartRef = ref(null);
let miniChart = null;

const POLLUTION_WEIGHTS = {
  1: 9,   // Marine Debris - anthropogenic
  2: 5,   // Dense Sargassum
  3: 3,   // Sparse Floating Algae
  4: 2,   // Natural Organic Material
  5: 7,   // Ship
  6: 10,  // Oil Spill - severe
  7: 0,   // Marine Water - clean
  8: 3,   // Sediment-Laden Water
  9: 4,   // Foam
  10: 4,  // Turbid Water
  11: 1,  // Shallow Water
  12: 1,  // Waves & Wakes
  13: 8,  // Oil Platform - industrial
  14: 3,  // Jellyfish
  15: 7,  // Sea snot - mucilage
};

const fileName = computed(() => {
  const parts = detection.originalPath?.split(/[/\\]/) || [];
  return parts[parts.length - 1] || '';
});

const sortedStats = computed(() => {
  const entries = Object.entries(detection.stats);
  entries.sort((a, b) => b[1].percentage - a[1].percentage);
  return Object.fromEntries(entries);
});

const dominantClassName = computed(() => {
  const sorted = Object.entries(detection.stats);
  sorted.sort((a, b) => b[1].percentage - a[1].percentage);
  return sorted[0]?.[0] || 'N/A';
});

const pollutionIndex = computed(() => {
  const stats = detection.stats;
  let weightedSum = 0;
  for (const [name, stat] of Object.entries(stats)) {
    const w = POLLUTION_WEIGHTS[stat.class_id] || 0;
    weightedSum += stat.percentage * w;
  }
  // percentages sum to 100, weights are 0-10, so weightedSum in [0, 1000]
  // divide by 100 to normalize to [0, 10]
  const raw = weightedSum / 100;
  return Math.round(raw * 10) / 10;
});

const pollutionLevelClass = computed(() => {
  const v = pollutionIndex.value;
  if (v <= 1.5) return 'level-clean';
  if (v <= 3.0) return 'level-light';
  if (v <= 5.0) return 'level-moderate';
  if (v <= 7.0) return 'level-heavy';
  return 'level-severe';
});

const pollutionLabel = computed(() => {
  const v = pollutionIndex.value;
  if (v <= 1.5) return t('pollution.clean');
  if (v <= 3.0) return t('pollution.light');
  if (v <= 5.0) return t('pollution.moderate');
  if (v <= 7.0) return t('pollution.heavy');
  return t('pollution.severe');
});

const pollutionDesc = computed(() => {
  const v = pollutionIndex.value;
  if (v <= 1.5) return t('pollution.descClean');
  if (v <= 3.0) return t('pollution.descLight');
  if (v <= 5.0) return t('pollution.descModerate');
  if (v <= 7.0) return t('pollution.descHeavy');
  return t('pollution.descSevere');
});

function contribPercent(stat) {
  const stats = detection.stats;
  let weightedSum = 0;
  for (const [, s] of Object.entries(stats)) {
    weightedSum += s.percentage * (POLLUTION_WEIGHTS[s.class_id] || 0);
  }
  if (weightedSum === 0) return 0;
  const sw = stat.percentage * (POLLUTION_WEIGHTS[stat.class_id] || 0);
  return Math.round((sw / weightedSum) * 1000) / 10;
}

function getBarColor(stat) {
  const w = POLLUTION_WEIGHTS[stat.class_id] || 0;
  if (w >= 8) return '#e74c3c';
  if (w >= 5) return '#f39c12';
  return '#5b8def';
}

function goToCharts() { router.push('/charts'); }

async function exportXlsx() {
  const stats = detection.stats;
  const names = Object.keys(stats).sort((a, b) => stats[b].percentage - stats[a].percentage);

  // Sheet 1: Summary
  const summaryData = [
    [t('report.xlsxTitle')],
    [],
    [t('report.file'), fileName.value],
    [t('report.mode'), detection.mode],
    [t('report.imageSize'), detection.totalPixels],
    [t('report.classesDetected'), `${Object.keys(stats).length} / 15`],
    [t('report.dominantClass'), tClassName(dominantClassName.value)],
    [t('report.pollutionIndex'), `${pollutionIndex.value} / 10`],
    [t('report.pollutionLevel'), pollutionLabel.value],
    [t('report.xlsxAssessment'), pollutionDesc.value],
  ];

  // Sheet 2: Per-Class Statistics
  const classData = [[t('report.classCol'), t('report.xlsxClassId'), t('report.pixelCountCol'), t('report.percentageCol'), t('report.weightCol'), t('report.contributionCol')]];
  for (const name of names) {
    const s = stats[name];
    classData.push([
      tClassName(name), s.class_id, s.pixel_count, s.percentage,
      POLLUTION_WEIGHTS[s.class_id] || 0,
      contribPercent(s)
    ]);
  }

  // Sheet 3: Pollution Weights Reference
  const weightData = [[t('report.xlsxClassId'), t('report.xlsxClassName'), t('report.xlsxPollutionWeight'), t('report.xlsxCategory')]];
  const weightCategories = {
    1: 'Anthropogenic', 2: 'Biological', 3: 'Biological', 4: 'Natural', 5: 'Anthropogenic',
    6: 'Anthropogenic', 7: 'Natural', 8: 'Natural', 9: 'Mixed', 10: 'Mixed',
    11: 'Natural', 12: 'Natural', 13: 'Anthropogenic', 14: 'Biological', 15: 'Biological',
  };
  for (const [clsId, weight] of Object.entries(POLLUTION_WEIGHTS)) {
    weightData.push([parseInt(clsId), CLASS_NAMES[clsId] || `Class ${clsId}`, weight, t('weightCategory.' + (weightCategories[clsId] || ''))]);
  }

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(summaryData), t('report.xlsxSheet1'));
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(classData), t('report.xlsxSheet2'));
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(weightData), t('report.xlsxSheet3'));

  const wbData = XLSX.write(wb, { type: 'array', bookType: 'xlsx' });

  // Encode as base64 for IPC
  const bytes = new Uint8Array(wbData);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = btoa(binary);

  const filePath = await save({
    filters: [{ name: 'Excel Files', extensions: ['xlsx'] }],
    defaultPath: `marinext_report_${Date.now()}.xlsx`,
  });

  if (filePath) {
    await invoke('write_file_base64', { path: filePath, base64Data: base64 });
  }
}

onMounted(() => {
  nextTick(() => {
    if (detection.currentId && miniChartRef.value) {
      const stats = detection.stats;
      const names = Object.keys(stats);
      const percentages = names.map(n => stats[n].percentage);
      const translatedNames = names.map(n => tClassName(n));
      miniChart = markRaw(echarts.init(miniChartRef.value));
      miniChart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: translatedNames, axisLabel: { rotate: 45, fontSize: 9 } },
        yAxis: { type: 'value', name: '%' },
        series: [{
          type: 'bar',
          data: names.map((n, i) => ({
            value: percentages[i],
            itemStyle: { color: COLOR_MAP[stats[n]?.class_id] || '#999' }
          }))
        }],
        grid: { bottom: 100 }
      });
    }
  });
});

onUnmounted(() => { miniChart?.dispose(); });
</script>

<style scoped>
.report-page {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: #f3f4f6;
}
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.report-header h2 { font-size: 22px; color: #374151; }
.header-actions { display: flex; gap: 12px; }
.btn {
  padding: 10px 24px; border-radius: 8px; font-size: 14px;
  font-weight: 500; cursor: pointer; border: none; text-decoration: none;
}
.btn-primary { background: #5b8def; color: #fff; }
.btn-secondary { background: #f0f2f5; color: #333; }
.empty-state {
  text-align: center; padding: 80px 0; color: #888;
  display: flex; flex-direction: column; align-items: center; gap: 16px;
}
.report-body { display: flex; flex-direction: column; gap: 20px; }
.report-section {
  background: #fff; border-radius: 12px; padding: 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.report-section h3 { font-size: 16px; color: #374151; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #f0f2f5; }

/* Pollution card */
.pollution-card {
  border-left: 4px solid #5b8def;
}
.pollution-card.level-clean { border-left-color: #27ae60; }
.pollution-card.level-light { border-left-color: #f39c12; }
.pollution-card.level-moderate { border-left-color: #e67e22; }
.pollution-card.level-heavy { border-left-color: #e74c3c; }
.pollution-card.level-severe { border-left-color: #8e44ad; }

.pollution-main {
  display: flex;
  gap: 24px;
  align-items: center;
  margin-bottom: 16px;
}
.pollution-score-wrap {
  display: flex;
  align-items: baseline;
  gap: 2px;
}
.pollution-score {
  font-size: 48px;
  font-weight: 700;
  color: #374151;
  line-height: 1;
}
.pollution-scale {
  font-size: 18px;
  color: #999;
}
.pollution-info h3 {
  font-size: 18px;
  margin: 0 0 4px;
  padding: 0;
  border: none;
}
.pollution-level {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}
.level-clean .pollution-level { color: #27ae60; }
.level-light .pollution-level { color: #f39c12; }
.level-moderate .pollution-level { color: #e67e22; }
.level-heavy .pollution-level { color: #e74c3c; }
.level-severe .pollution-level { color: #8e44ad; }
.pollution-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  margin: 0;
}

.pollution-bar-wrap {
  margin-top: 4px;
}
.pollution-bar {
  height: 8px;
  background: #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
}
.pollution-fill {
  height: 100%;
  background: linear-gradient(to right, #27ae60, #f39c12, #e67e22, #e74c3c, #8e44ad);
  border-radius: 4px;
  transition: width 0.3s;
}
.pollution-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 10px;
  color: #bbb;
}

.methodology-note {
  font-size: 11px;
  color: #9ca3af;
  margin: 0 0 12px;
  font-style: italic;
}

.methodology-details {
  margin-top: 12px;
  font-size: 12px;
  color: #9ca3af;
}

.methodology-details summary {
  cursor: pointer;
  color: #6b7280;
  font-weight: 500;
}

.methodology-details summary:hover {
  color: #5b8def;
}

.methodology-content {
  margin-top: 8px;
  padding: 12px;
  background: #f8f9fb;
  border-radius: 8px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
}

.methodology-content p {
  margin-bottom: 8px;
}

.methodology-content ul {
  margin: 8px 0;
  padding-left: 18px;
}

.methodology-content li {
  margin-bottom: 4px;
}

.info-table { width: 100%; max-width: 400px; }
.info-table td { padding: 6px 0; font-size: 14px; }
.info-table .label { color: #888; width: 140px; }
.level-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
}
.level-badge.level-clean { background: #27ae60; }
.level-badge.level-light { background: #f39c12; }
.level-badge.level-moderate { background: #e67e22; }
.level-badge.level-heavy { background: #e74c3c; }
.level-badge.level-severe { background: #8e44ad; }

.stats-table {
  width: 100%; border-collapse: collapse;
}
.stats-table th { text-align: left; padding: 8px 12px; font-size: 12px; color: #888; border-bottom: 1px solid #e0e0e0; }
.stats-table td { padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #f0f0f0; }
.polluter-row td { background: #fff5f5; }

.contrib-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.contrib-bar {
  height: 6px;
  border-radius: 3px;
  min-width: 4px;
}
.contrib-val {
  font-size: 12px;
  color: #666;
  flex-shrink: 0;
}

.mini-chart { width: 100%; height: 300px; }

@media print {
  .report-header, .header-actions { display: none; }
  .report-page { background: #fff; padding: 0; }
  .report-section { box-shadow: none; border: 1px solid #e0e0e0; break-inside: avoid; }
}
</style>
