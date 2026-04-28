import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { invoke } from "@tauri-apps/api/core";

export const useHistoryStore = defineStore("history", () => {
  const items = ref([]);
  const searchQuery = ref("");
  const filterType = ref("all");
  const sortDesc = ref(true);
  const activeId = ref(null);
  const dateFrom = ref("");
  const dateTo = ref("");

  const filteredItems = computed(() => {
    const from = dateFrom.value || null;
    const to = dateTo.value || null;

    let result = items.value.filter((item) => {
      const matchName = !searchQuery.value ||
        item.file_name.toLowerCase().includes(searchQuery.value.toLowerCase());
      const matchType = filterType.value === "all" ||
        item.primary_class === parseInt(filterType.value);
      let matchDate = true;
      if (from) matchDate = matchDate && item.date >= from;
      if (to) matchDate = matchDate && item.date <= (to + " 23:59:59");
      return matchName && matchType && matchDate;
    });

    return [...result].sort((a, b) => {
      const tA = new Date(a.date).getTime();
      const tB = new Date(b.date).getTime();
      return sortDesc.value ? tB - tA : tA - tB;
    });
  });

  const groupedItems = computed(() => {
    const groups = new Map();
    for (const item of filteredItems.value) {
      const key = item.file_name;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    }
    // Sort groups by most recent item in each group
    const sortedGroups = [...groups.entries()]
      .sort((a, b) => {
        const aMax = Math.max(...a[1].map(i => new Date(i.date).getTime()));
        const bMax = Math.max(...b[1].map(i => new Date(i.date).getTime()));
        return sortDesc.value ? bMax - aMax : aMax - bMax;
      });
    return sortedGroups;
  });

  async function loadHistory() {
    try {
      items.value = await invoke("get_history_list", {
        query: "",
        filterType: null,
        sortDesc: true,
        dateFrom: null,
        dateTo: null,
      });
    } catch (e) {
      console.error("Failed to load history:", e);
    }
  }

  async function refreshWithFilters() {
    try {
      const clsFilter = filterType.value === "all" ? null : parseInt(filterType.value);
      items.value = await invoke("get_history_list", {
        query: searchQuery.value,
        filterType: clsFilter,
        sortDesc: sortDesc.value,
        dateFrom: dateFrom.value || null,
        dateTo: dateTo.value || null,
      });
    } catch (e) {
      console.error("Failed to filter history:", e);
    }
  }

  async function deleteItem(id) {
    try {
      await invoke("delete_history", { id });
      items.value = items.value.filter((item) => item.id !== id);
    } catch (e) {
      console.error("Failed to delete history:", e);
    }
  }

  function toggleSort() {
    sortDesc.value = !sortDesc.value;
  }

  function clearDateFilter() {
    dateFrom.value = "";
    dateTo.value = "";
  }

  return {
    items, searchQuery, filterType, sortDesc, activeId,
    dateFrom, dateTo,
    filteredItems, groupedItems,
    loadHistory, refreshWithFilters, deleteItem, toggleSort, clearDateFilter,
  };
});
