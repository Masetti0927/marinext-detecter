import { defineStore } from "pinia";
import { ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

export const useDetectionStore = defineStore("detection", () => {
  const originalPath = ref("");
  const maskPath = ref("");
  const originalBase64 = ref("");
  const maskBase64 = ref("");
  const stats = ref({});
  const totalPixels = ref(0);
  const isLoading = ref(false);
  const error = ref("");
  const currentId = ref("");
  const mode = ref("");

async function pickAndDetect(detectMode, modelNames, useTta = false) {
  try {
      let filePath;
      if (detectMode === "rgb") {
        filePath = await open({
          filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "bmp", "tiff"] }],
          multiple: false,
        });
      } else {
        filePath = await open({
          filters: [{ name: "ZIP Archives", extensions: ["zip"] }],
          multiple: false,
        });
      }

      if (!filePath) return false;

      isLoading.value = true;
      error.value = "";
      mode.value = detectMode;

      const cmd = detectMode === "rgb" ? "detect_rgb" : "detect_multichannel";
      const argKey = detectMode === "rgb" ? "imagePath" : "zipPath";
       const result = await invoke(cmd, { [argKey]: filePath, modelNames, useTta });

      originalPath.value = result.original_path;
      maskPath.value = result.mask_path;
      originalBase64.value = result.original_base64;
      maskBase64.value = result.mask_base64;
      stats.value = result.stats;
      totalPixels.value = result.total_pixels;
      currentId.value = result.id;

      return true;
    } catch (e) {
      error.value = String(e);
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchModels(mode) {
    try {
      return await invoke("list_models", { mode });
    } catch {
      return [];
    }
  }

  function loadResult(result) {
    originalPath.value = result.original_path || "";
    maskPath.value = result.mask_path || "";
    originalBase64.value = result.original_base64 || "";
    maskBase64.value = result.mask_base64 || "";
    stats.value = result.stats || {};
    totalPixels.value = result.total_pixels || 0;
    currentId.value = result.id || "";
    mode.value = result.mode || "";
  }

  function clearResult() {
    originalPath.value = "";
    maskPath.value = "";
    originalBase64.value = "";
    maskBase64.value = "";
    stats.value = {};
    totalPixels.value = 0;
    currentId.value = "";
    mode.value = "";
    error.value = "";
  }

  return {
    originalPath, maskPath, originalBase64, maskBase64,
    stats, totalPixels, isLoading, error, currentId, mode,
    pickAndDetect, fetchModels, loadResult, clearResult,
  };
});
