<template>
  <div class="report-page">
    <div class="report-header">
      <h2>Detection Report</h2>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="goToCharts">Charts</button>
        <button class="btn btn-primary" @click="exportPdf">Export PDF</button>
      </div>
    </div>

    <div v-if="!detection.currentId" class="empty-state">
      <p>No detection data available. Run a detection first.</p>
      <router-link to="/detect" class="btn btn-primary">Run Detection</router-link>
    </div>

    <div v-else class="report-body" ref="reportRef">
      <div class="report-section">
        <h3>Summary</h3>
        <table class="info-table">
          <tr><td class="label">File</td><td>{{ fileName }}</td></tr>
          <tr><td class="label">Mode</td><td>{{ detection.mode }}</td></tr>
          <tr><td class="label">Image Size</td><td>{{ detection.totalPixels?.toLocaleString() }} px</td></tr>
          <tr><td class="label">Classes Detected</td><td>{{ Object.keys(detection.stats).length }} / 15</td></tr>
          <tr><td class="label">Dominant Class</td><td>{{ dominantClassName }}</td></tr>
        </table>
      </div>

      <div class="report-section">
        <h3>Per-Class Statistics</h3>
        <table class="stats-table">
          <thead>
            <tr><th>Class</th><th>ID</th><th>Pixel Count</th><th>Percentage</th></tr>
          </thead>
          <tbody>
            <tr v-for="(stat, name) in sortedStats" :key="name">
              <td>{{ name }}</td>
              <td>{{ stat.class_id }}</td>
              <td>{{ stat.pixel_count?.toLocaleString() }}</td>
              <td>{{ stat.percentage }}%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="report-section">
        <h3>Class Coverage</h3>
        <div ref="miniChartRef" class="mini-chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, markRaw, nextTick } from "vue";
import * as echarts from "echarts";
import { useRouter } from "vue-router";
import { useDetectionStore } from "../stores/detection";

const router = useRouter();
const detection = useDetectionStore();

const reportRef = ref(null);
const miniChartRef = ref(null);
let miniChart = null;

const colorMap = [
  '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
  '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
  '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000'
];

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

function goToCharts() { router.push('/charts'); }

function exportPdf() {
  window.print();
}

onMounted(() => {
  nextTick(() => {
    if (detection.currentId && miniChartRef.value) {
      const stats = detection.stats;
      const names = Object.keys(stats);
      const percentages = names.map(n => stats[n].percentage);
      miniChart = markRaw(echarts.init(miniChartRef.value));
      miniChart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: names, axisLabel: { rotate: 45, fontSize: 9 } },
        yAxis: { type: 'value', name: '%' },
        series: [{
          type: 'bar',
          data: names.map((n, i) => ({ value: percentages[i], itemStyle: { color: colorMap[i % colorMap.length] } }))
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
  background: #f5f7fa;
}
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.report-header h2 { font-size: 22px; color: #1a1a2e; }
.header-actions { display: flex; gap: 12px; }
.btn {
  padding: 10px 24px; border-radius: 8px; font-size: 14px;
  font-weight: 500; cursor: pointer; border: none; text-decoration: none;
}
.btn-primary { background: #409eff; color: #fff; }
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
.report-section h3 { font-size: 16px; color: #1a1a2e; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #f0f2f5; }
.info-table { width: 100%; max-width: 400px; }
.info-table td { padding: 6px 0; font-size: 14px; }
.info-table .label { color: #888; width: 140px; }
.stats-table {
  width: 100%; border-collapse: collapse;
}
.stats-table th { text-align: left; padding: 8px 12px; font-size: 12px; color: #888; border-bottom: 1px solid #e0e0e0; }
.stats-table td { padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #f0f0f0; }
.mini-chart { width: 100%; height: 300px; }

@media print {
  .report-header, .header-actions { display: none; }
  .report-page { background: #fff; padding: 0; }
  .report-section { box-shadow: none; border: 1px solid #e0e0e0; break-inside: avoid; }
}
</style>
