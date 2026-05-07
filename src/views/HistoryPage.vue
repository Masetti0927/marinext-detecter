<template>
  <div class="history-page">
    <div class="history-header">
      <h2>{{ t('history.title') }}</h2>
      <div class="filter-bar">
        <div class="search-box">
          <input
            type="text"
            v-model="history.searchQuery"
            @input="debouncedFilter"
            :placeholder="t('history.searchPlaceholder')"
          />
        </div>
        <select v-model="history.filterType" @change="history.refreshWithFilters()" class="filter-select">
          <option value="all">{{ t('history.allClasses') }}</option>
          <option v-for="(clsId, clsName) in classOptions" :key="clsId" :value="clsId">
            {{ t('classes.' + clsName) }}
          </option>
        </select>
        <input type="date" v-model="history.dateFrom" @change="history.refreshWithFilters()" class="date-input" title="From date" />
        <input type="date" v-model="history.dateTo" @change="history.refreshWithFilters()" class="date-input" title="To date" />
        <button v-if="history.dateFrom || history.dateTo" class="clear-date-btn" @click="history.clearDateFilter(); history.refreshWithFilters()">{{ t('history.clearDates') }}</button>
        <button class="sort-btn" @click="history.toggleSort(); history.refreshWithFilters()">
          {{ history.sortDesc ? t('history.newestFirst') : t('history.oldestFirst') }}
        </button>
        <button class="reset-btn" @click="resetAllFilters">{{ t('history.resetFilters') }}</button>
        <button class="refresh-btn" @click="history.loadHistory()">{{ t('history.refresh') }}</button>
      </div>
    </div>

    <div class="history-list" v-if="history.groupedItems.length > 0">
      <div
        v-for="[fileName, entries] in history.groupedItems"
        :key="fileName"
        class="history-group"
      >
        <div class="group-header">
          <span class="group-name" :title="fileName">{{ fileName }}</span>
          <span class="group-count">{{ entries.length }} {{ entries.length === 1 ? t('history.result') : t('history.results') }}</span>
        </div>
        <div
          v-for="item in entries"
          :key="item.id"
          class="history-card"
          :class="{ active: history.activeId === item.id }"
          @click="loadItem(item)"
        >
          <div class="card-thumb">
            <img v-if="thumbCache[item.original_path]" :src="thumbCache[item.original_path]" alt="thumb" />
            <div class="thumb-placeholder" v-else>Img</div>
          </div>
          <div class="card-info">
            <div class="file-name">{{ item.date }}</div>
            <div class="file-meta">
              <span class="tag" :style="{ backgroundColor: getClassColor(item) }">
                {{ getPrimaryName(item) }}
              </span>
              <span class="mode-tag">{{ item.mode }}</span>
            </div>
          </div>
          <button class="delete-btn" @click.stop="handleDelete(item.id)" title="Delete">x</button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>{{ t('history.noRecords') }}</p>
      <router-link to="/detect" class="btn btn-primary">{{ t('history.runDetection') }}</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useHistoryStore } from "../stores/history";
import { useDetectionStore } from "../stores/detection";
import { invoke } from "@tauri-apps/api/core";

const router = useRouter();
const { t } = useI18n();
const history = useHistoryStore();
const detection = useDetectionStore();

let filterTimeout = null;
const thumbCache = ref({});
const loadingThumbs = ref(false);

const classOptions = {
  'Marine Debris': 1, 'Dense Sargassum': 2, 'Sparse Floating Algae': 3,
  'Natural Organic Material': 4, 'Ship': 5, 'Oil Spill': 6,
  'Marine Water': 7, 'Sediment-Laden Water': 8, 'Foam': 9,
  'Turbid Water': 10, 'Shallow Water': 11, 'Waves & Wakes': 12,
  'Oil Platform': 13, 'Jellyfish': 14, 'Sea snot': 15
};

const classNameMap = {
  1: 'Debris', 2: 'Sargassum', 3: 'Algae', 4: 'Organic', 5: 'Ship',
  6: 'Oil', 7: 'Water', 8: 'Sediment', 9: 'Foam', 10: 'Turbid',
  11: 'Shallow', 12: 'Waves', 13: 'Platform', 14: 'Jellyfish', 15: 'Sea snot'
};

const classColorMap = {
  1: 'red', 2: 'green', 3: 'limegreen', 4: 'brown', 5: 'orange',
  6: 'purple', 7: 'navy', 8: 'gold', 9: 'thistle', 10: 'darkkhaki',
  11: 'darkturquoise', 12: 'bisque', 13: 'dimgrey', 14: 'hotpink', 15: 'yellow'
};

onMounted(() => {
  history.loadHistory();
});

watch(() => history.items, (items) => {
  if (items && items.length) loadThumbnails(items);
}, { immediate: true });

async function loadThumbnails(items) {
  loadingThumbs.value = true;
  const toLoad = items.filter(item => item.original_path && !thumbCache.value[item.original_path]);
  for (let i = 0; i < toLoad.length; i += 3) {
    const batch = toLoad.slice(i, i + 3);
    await Promise.all(batch.map(async (item) => {
      try {
        const b64 = await invoke("get_image_base64", { path: item.original_path });
        thumbCache.value[item.original_path] = b64;
      } catch { /* ignore */ }
    }));
  }
  loadingThumbs.value = false;
}

function resetAllFilters() {
  history.searchQuery = "";
  history.filterType = "all";
  history.sortDesc = true;
  history.clearDateFilter();
  history.refreshWithFilters();
}

function debouncedFilter() {
  if (filterTimeout) clearTimeout(filterTimeout);
  filterTimeout = setTimeout(() => history.refreshWithFilters(), 300);
}

async function loadItem(item) {
  history.activeId = item.id;
  detection.isLoading = true;
  try {
    // Multi-channel has no original image, skip loading it
    const loadOriginal = item.mode !== 'multichannel'
      ? invoke("get_image_base64", { path: item.original_path })
      : Promise.resolve('');
    const [originalB64, maskB64] = await Promise.all([
      loadOriginal,
      invoke("get_image_base64", { path: item.mask_path }),
    ]);
    detection.loadResult({
      ...item,
      original_base64: originalB64,
      mask_base64: maskB64,
    });
    router.push('/contrast');
  } catch (e) {
    detection.error = String(e);
  } finally {
    detection.isLoading = false;
  }
}

function getClassColor(item) {
  return classColorMap[item.primary_class] || '#999';
}

function getPrimaryName(item) {
  return classNameMap[item.primary_class] || 'N/A';
}

async function handleDelete(id) {
  await history.deleteItem(id);
}
</script>

<style scoped>
.history-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f3f4f6;
}
.history-header {
  padding: 24px 24px 16px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
}
.history-header h2 { font-size: 22px; color: #374151; margin-bottom: 16px; }
.filter-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.search-box input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  width: 200px;
}
.search-box input:focus { border-color: #5b8def; }
.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
}
.date-input {
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 12px;
  outline: none;
  width: 130px;
}
.date-input:focus { border-color: #5b8def; }
.clear-date-btn {
  padding: 6px 10px;
  border: none;
  background: none;
  color: #999;
  cursor: pointer;
  font-size: 12px;
}
.clear-date-btn:hover { color: #e74c3c; }
.sort-btn, .reset-btn, .refresh-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.sort-btn:hover, .reset-btn:hover, .refresh-btn:hover { background: #f0f2f5; }
.reset-btn { color: #e67e22; border-color: #f0c78a; }
.reset-btn:hover { background: #fff8f0; }
.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-group {
  margin-bottom: 16px;
}
.group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #e0e0e0;
  margin-bottom: 8px;
}
.group-name {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}
.group-count {
  font-size: 12px;
  color: #999;
  background: #f0f2f5;
  padding: 2px 10px;
  border-radius: 10px;
  flex-shrink: 0;
}

.history-card {
  display: flex;
  gap: 12px;
  padding: 10px 14px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #eee;
  cursor: pointer;
  transition: all 0.15s ease;
  align-items: center;
  margin-bottom: 4px;
  margin-left: 8px;
}
.history-card:hover {
  border-color: #5b8def;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  transform: translateY(-1px);
}
.history-card.active { border-color: #5b8def; background: #e8f0fe; }
.card-thumb {
  width: 56px; height: 56px;
  border-radius: 6px; overflow: hidden;
  flex-shrink: 0; background: #e0e0e0;
}
.card-thumb img {
  width: 100%; height: 100%; object-fit: cover;
}
.thumb-placeholder {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  color: #999; font-size: 11px;
}
.card-info { flex: 1; min-width: 0; }
.file-name {
  font-size: 13px; font-weight: 600; color: #333;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 4px;
}
.file-meta {
  display: flex; gap: 8px; align-items: center; font-size: 12px; color: #999;
}
.tag {
  color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px;
}
.mode-tag {
  background: #f0f2f5; padding: 2px 8px; border-radius: 10px; font-size: 11px; color: #666;
}
.delete-btn {
  background: transparent; border: none; color: #ccc;
  font-size: 16px; cursor: pointer; padding: 4px 8px;
  border-radius: 4px; transition: all 0.15s;
}
.delete-btn:hover { color: #e74c3c; background: #fff0f0; }
.empty-state {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 16px;
  color: #888; font-size: 14px;
}
.btn {
  padding: 10px 24px; border-radius: 8px; font-size: 14px;
  font-weight: 500; cursor: pointer; border: none; text-decoration: none;
  display: inline-block;
}
.btn-primary { background: #5b8def; color: #fff; }
</style>
