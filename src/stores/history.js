import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { invoke } from "@tauri-apps/api/core";

export const useHistoryStore = defineStore("history", () => {
  const items = ref([]);
  const searchQuery = ref("");
  const filterType = ref("all");
  const sortDesc = ref(true);
  const activeId = ref(null);

  const filteredItems = computed(() => {
    let result = items.value.filter((item) => {
      const matchName = !searchQuery.value ||
        item.file_name.toLowerCase().includes(searchQuery.value.toLowerCase());
      const matchType = filterType.value === "all" ||
        item.primary_class === parseInt(filterType.value);
      return matchName && matchType;
    });

    return [...result].sort((a, b) => {
      const tA = new Date(a.date).getTime();
      const tB = new Date(b.date).getTime();
      return sortDesc.value ? tB - tA : tA - tB;
    });
  });

  async function loadHistory() {
    try {
      items.value = await invoke("get_history_list", {
        query: "",
        filterType: null,
        sortDesc: true,
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

  return {
    items, searchQuery, filterType, sortDesc, activeId,
    filteredItems,
    loadHistory, refreshWithFilters, deleteItem, toggleSort,
  };
});
