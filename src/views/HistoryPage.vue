<template>
  <div class="history-page">
    <div class="history-header">
      <h2>Detection History</h2>
      <div class="filter-bar">
        <div class="search-box">
          <input
            type="text"
            v-model="history.searchQuery"
            @input="debouncedFilter"
            placeholder="Search by filename..."
          />
        </div>
        <select v-model="history.filterType" @change="history.refreshWithFilters()" class="filter-select">
          <option value="all">All Classes</option>
          <option v-for="(clsId, clsName) in classOptions" :key="clsId" :value="clsId">
            {{ clsName }}
          </option>
        </select>
        <button class="sort-btn" @click="history.toggleSort(); history.refreshWithFilters()">
          {{ history.sortDesc ? 'Newest first' : 'Oldest first' }}
        </button>
        <button class="refresh-btn" @click="history.loadHistory()">Refresh</button>
      </div>
    </div>

    <div class="history-list" v-if="history.filteredItems.length > 0">
      <div
        v-for="item in history.filteredItems"
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
          <div class="file-name">{{ item.file_name }}</div>
          <div class="file-meta">
            <span>{{ item.date }}</span>
            <span class="tag" :style="{ backgroundColor: getClassColor(item) }">
              {{ getPrimaryName(item) }}
            </span>
            <span class="mode-tag">{{ item.mode }}</span>
          </div>
        </div>
        <button class="delete-btn" @click.stop="handleDelete(item.id)" title="Delete">x</button>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>No history records found.</p>
      <router-link to="/detect" class="btn btn-primary">Run Detection</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useHistoryStore } from "../stores/history";
import { useDetectionStore } from "../stores/detection";
import { invoke } from "@tauri-apps/api/core";

const router = useRouter();
const history = useHistoryStore();
const detection = useDetectionStore();

let filterTimeout = null;
const thumbCache = ref({});

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

function debouncedFilter() {
  if (filterTimeout) clearTimeout(filterTimeout);
  filterTimeout = setTimeout(() => history.refreshWithFilters(), 300);
}

async function loadItem(item) {
  history.activeId = item.id;
  detection.isLoading = true;
  try {
    const [originalB64, maskB64] = await Promise.all([
      invoke("get_image_base64", { path: item.original_path }),
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
  background: #f5f7fa;
}
.history-header {
  padding: 24px 24px 16px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
}
.history-header h2 { font-size: 22px; color: #1a1a2e; margin-bottom: 16px; }
.filter-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.search-box input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  width: 220px;
}
.search-box input:focus { border-color: #409eff; }
.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
}
.sort-btn, .refresh-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.sort-btn:hover, .refresh-btn:hover { background: #f0f2f5; }
.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.history-card {
  display: flex;
  gap: 16px;
  padding: 14px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #eee;
  cursor: pointer;
  transition: all 0.15s ease;
  align-items: center;
}
.history-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}
.history-card.active { border-color: #409eff; background: #ecf5ff; }
.card-thumb {
  width: 72px; height: 72px;
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
  font-size: 14px; font-weight: 600; color: #333;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 6px;
}
.file-meta {
  display: flex; gap: 10px; align-items: center; font-size: 12px; color: #999;
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
.btn-primary { background: #409eff; color: #fff; }
</style>
