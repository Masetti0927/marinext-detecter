<template>
  <div class="charts-page">
    <div class="charts-header">
      <h2>{{ t('charts.title') }}</h2>
      <router-link to="/contrast" class="back-link">{{ t('charts.backToContrast') }}</router-link>
    </div>

    <div v-if="!detection.currentId" class="empty-state">
      <p>{{ t('charts.noData') }}</p>
      <router-link to="/detect" class="btn btn-primary">{{ t('charts.runDetection') }}</router-link>
    </div>

    <div v-else class="charts-grid">
      <div class="chart-card">
        <h3>{{ t('charts.pieChart') }}</h3>
        <div ref="pieChartRef" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <h3>{{ t('charts.barChart') }}</h3>
        <div ref="barChartRef" class="chart-box"></div>
      </div>
      <div class="chart-card chart-card-wide">
        <h3>{{ t('charts.radarChart') }}</h3>
        <div ref="radarChartRef" class="chart-box"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, markRaw, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import * as echarts from "echarts";
import { useDetectionStore } from "../stores/detection";
import { COLOR_MAP } from "../composables/useMaskProcessing";

const detection = useDetectionStore();
const { t } = useI18n();

function tClassName(enName) {
  return t('classes.' + enName);
}

const pieChartRef = ref(null);
const barChartRef = ref(null);
const radarChartRef = ref(null);
let pieInstance = null, barInstance = null, radarInstance = null;

onMounted(() => {
  nextTick(() => {
    if (detection.currentId) initCharts();
  });
});

onUnmounted(() => {
  pieInstance?.dispose();
  barInstance?.dispose();
  radarInstance?.dispose();
});

function initCharts() {
  const stats = detection.stats;
  const names = Object.keys(stats);
  const translatedNames = names.map(n => tClassName(n));
  const percentages = names.map(n => stats[n].percentage);
  const pixelCounts = names.map(n => stats[n].pixel_count);

  function getColor(className) {
    const clsId = stats[className]?.class_id;
    return COLOR_MAP[clsId] || '#999';
  }

  // Pie chart
  pieInstance = markRaw(echarts.init(pieChartRef.value));
  pieInstance.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    series: [{
      type: 'pie',
      radius: ['40%', '75%'],
      data: names.map((n, i) => ({ name: translatedNames[i], value: percentages[i], itemStyle: { color: getColor(n) } })),
      label: { formatter: '{b}\n{d}%', fontSize: 10 }
    }]
  });

  // Bar chart
  barInstance = markRaw(echarts.init(barChartRef.value));
  barInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: translatedNames, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: t('charts.pixels') },
    series: [{
      type: 'bar',
      data: names.map((n, i) => ({ value: pixelCounts[i], itemStyle: { color: getColor(n) } }))
    }],
    grid: { bottom: 120 }
  });

  // Radar chart
  radarInstance = markRaw(echarts.init(radarChartRef.value));
  radarInstance.setOption({
    tooltip: {},
    radar: {
      indicator: translatedNames.map((tname, i) => ({ name: tname, max: Math.max(...percentages) * 1.2 })),
      axisName: { fontSize: 10 }
    },
    series: [{
      type: 'radar',
      data: [{ value: percentages, name: t('charts.classPct'), areaStyle: { opacity: 0.3 } }],
      itemStyle: { color: '#5b8def' }
    }]
  });
}
</script>

<style scoped>
.charts-page {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: #f3f4f6;
}
.charts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.charts-header h2 { font-size: 22px; color: #374151; }
.back-link { color: #5b8def; text-decoration: none; font-size: 14px; }
.empty-state {
  text-align: center; padding: 80px 0; color: #888;
  display: flex; flex-direction: column; align-items: center; gap: 16px;
}
.btn {
  padding: 10px 24px; border-radius: 8px; font-size: 14px;
  font-weight: 500; cursor: pointer; border: none; text-decoration: none;
}
.btn-primary { background: #5b8def; color: #fff; }
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.chart-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.chart-card-wide { grid-column: 1 / -1; }
.chart-card h3 { font-size: 15px; color: #333; margin-bottom: 12px; }
.chart-box { width: 100%; height: 350px; }
</style>
