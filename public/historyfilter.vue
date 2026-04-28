<template>
  <div class="history-filter">
    <div class="filter-header">
      <div class="search-box">
        <i class="fas fa-search"></i>
        <input
          type="text"
          v-model="searchQuery"
          placeholder="搜索历史记录文件名..."
        />
      </div>

      <div class="filter-options">
        <select v-model="filterType" class="mini-select">
          <option value="all">所有类别</option>
          <option v-for="(id, name) in mapping" :key="id" :value="id">
            {{ name }}
          </option>
        </select>
        <button class="icon-btn" title="按时间排序" @click="toggleSort">
          <span v-if="sortDesc">▼ 新至旧</span>
          <span v-else>▲ 旧至新</span>
        </button>
      </div>
    </div>

    <div class="history-list">
      <div
        v-for="item in filteredHistory"
        :key="item.id"
        class="history-card"
        :class="{ 'active': activeHistoryId === item.id }"
        @click="selectHistoryItem(item)"
      >
        <div class="card-thumb">
          <img :src="item.originalImage" alt="thumb" />
          <div class="thumb-overlay">查看详情</div>
        </div>
        <div class="card-info">
          <div class="file-name text-ellipsis">{{ item.fileName }}</div>
          <div class="file-meta">
            <span><i class="far fa-calendar-alt"></i> {{ item.date }}</span>
            <span class="tag" :style="{ backgroundColor: getPrimaryColor(item) }">
              {{ getPrimaryName(item) }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="filteredHistory.length === 0" class="empty-state">
        <i class="fas fa-folder-open"></i>
        <p>未找到相关历史记录</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

// 模拟历史数据（实际开发中这里应从 LocalStorage 或 后端 API 获取）
const historyData = ref([
  {
    id: 1,
    fileName: 'S2A_MSIL1C_20230815.png',
    date: '2023-08-15 14:20',
    originalImage: '/7.png', // 示例路径
    maskImage: '/mask.png',
    primaryClass: 6, // Oil Spill
    params: { threshold: 0.45, sensitivity: 0.6 }
  },
  {
    id: 2,
    fileName: 'Coastline_Detection_09.png',
    date: '2023-09-02 09:12',
    originalImage: '/7.png',
    maskImage: '/mask.png',
    primaryClass: 2, // Dense Sargassum
    params: { threshold: 0.3, sensitivity: 0.5 }
  }
]);

const mapping = {
  'Marine Debris': 1, 'Dense Sargassum': 2, 'Oil Spill': 6, 'Ship': 5
};

const searchQuery = ref('');
const filterType = ref('all');
const sortDesc = ref(true);
const activeHistoryId = ref(null);

const filteredHistory = computed(() => {
  let result = historyData.value.filter(item => {
    const matchName = item.fileName.toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchType = filterType.value === 'all' || item.primaryClass === parseInt(filterType.value);
    return matchName && matchType;
  });

  return result.sort((a, b) => {
    const timeA = new Date(a.date).getTime();
    const timeB = new Date(b.date).getTime();
    return sortDesc.value ? timeB - timeA : timeA - timeB;
  });
});

function toggleSort() {
  sortDesc.value = !sortDesc.value;
}

function getPrimaryName(item) {
  const names = { 1: 'Debris', 2: 'Algae', 5: 'Ship', 6: 'Oil' };
  return names[item.primaryClass] || 'Other';
}

function getPrimaryColor(item) {
  const colors = { 1: 'red', 2: 'green', 5: 'orange', 6: 'purple' };
  return colors[item.primaryClass] || '#999';
}

// 👉 关键动作：点击历史项，通知全局切换数据
const emit = defineEmits(['load-history']);
function selectHistoryItem(item) {
  activeHistoryId.value = item.id;
  // 这里可以触发一个全局事件或者通过 mitt 传值
  // 目前我们建议通过 App.vue 统一管理
  console.log("加载历史记录:", item.fileName);
  // 模拟将数据传回主应用
  // window.dispatchEvent(new CustomEvent('load-app-data', { detail: item }));
}
</script>

<style scoped>
.history-filter {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
}

.filter-header {
  padding: 16px;
  border-bottom: 1px solid #eee;
  background: #fcfcfc;
}

.search-box {
  position: relative;
  margin-bottom: 12px;
}

.search-box input {
  width: 100%;
  padding: 8px 12px 8px 32px;
  border: 1px solid #ddd;
  border-radius: 20px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.search-box input:focus {
  border-color: #409eff;
}

.search-box i {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
}

.filter-options {
  display: flex;
  gap: 8px;
}

.mini-select {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 12px;
  outline: none;
}

.icon-btn {
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.icon-btn:hover {
  background: #f0f0f0;
}

/* 列表区域 */
.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-card {
  display: flex;
  gap: 12px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #eee;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
}

.history-card:hover {
  border-color: #409eff;
  background: #f9fbff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.history-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.card-thumb {
  width: 60px;
  height: 60px;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
  flex-shrink: 0;
  background: #000;
}

.card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.8;
}

.thumb-overlay {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(64, 158, 255, 0.6);
  color: white;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.history-card:hover .thumb-overlay {
  opacity: 1;
}

.card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.file-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.text-ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #999;
}

.tag {
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  transform: scale(0.9);
}

.empty-state {
  text-align: center;
  padding-top: 60px;
  color: #ccc;
}

.empty-state i {
  font-size: 40px;
  margin-bottom: 10px;
}

/* 滚动条美化 */
.history-list::-webkit-scrollbar {
  width: 4px;
}
.history-list::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 10px;
}
</style>