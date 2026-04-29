
<template>
  <div class="app-shell">
    <!-- Custom title bar -->
    <header class="app-header" data-tauri-drag-region>
      <div class="header-title" data-tauri-drag-region>MarineXt Detector</div>
      <div class="header-controls">
        <button class="win-btn" @click="minimize" title="Minimize">&minus;</button>
        <button class="win-btn" @click="toggleMaximize" title="Maximize">□</button>
        <button class="win-btn win-close" @click="close" title="Close">&times;</button>
      </div>
    </header>

    <div class="app-body">
      <aside class="sidebar">
        <div class="sidebar-brand">MarineXt</div>
        <nav class="sidebar-nav">
          <button
            v-for="item in navItems"
            :key="item.path"
            class="nav-btn"
            :class="{ active: route.path === item.path }"
            @click="navigateTo(item.path)"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </button>
        </nav>
      </aside>

      <main class="main-content">
        <div class="view-host">
          <router-view />
        </div>
      </main>
    </div>

    <footer class="app-footer">
      <div class="footer-left">
        <template v-if="detection.isLoading">
          <span class="footer-spinner"></span>
          <span class="footer-badge loading">Processing{{ elapsed ? ' ' + elapsed : '' }}</span>
        </template>
        <template v-else-if="detection.error">
          <span class="footer-badge error">{{ detection.error }}</span>
          <button class="footer-dismiss" @click="dismissError">&times;</button>
        </template>
        <template v-else-if="hasResult">
          <span class="footer-badge ready">Result ready</span>
          <span class="footer-mode">{{ detection.mode }}</span>
        </template>
        <template v-else>
          <span class="footer-badge idle">Ready</span>
        </template>
      </div>
      <div class="footer-right">
        <span class="footer-version">v1.0</span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDetectionStore } from "./stores/detection";
import { getCurrentWindow } from "@tauri-apps/api/window";

const router = useRouter();
const route = useRoute();
const detection = useDetectionStore();
const appWindow = getCurrentWindow();

const navItems = [
  { path: "/", label: "Home", icon: "⌂" },
  { path: "/detect", label: "Detect", icon: "◎" },
  { path: "/contrast", label: "Contrast", icon: "◉" },
  { path: "/charts", label: "Charts", icon: "▤" },
  { path: "/report", label: "Report", icon: "☰" },
  { path: "/history", label: "History", icon: "⏰" },
];

const hasResult = computed(() => !!detection.currentId);

function navigateTo(path) {
  router.push(path);
}

// Window controls
const minimize = () => appWindow.minimize();
const close = () => appWindow.close();
const toggleMaximize = async () => {
  const isMax = await appWindow.isMaximized();
  isMax ? appWindow.unmaximize() : appWindow.maximize();
};

// Elapsed time tracker
const elapsed = ref("");
let elapsedTimer = null;

watch(() => detection.isLoading, (loading) => {
  if (loading) {
    const start = Date.now();
    elapsed.value = "0s";
    elapsedTimer = setInterval(() => {
      const sec = Math.floor((Date.now() - start) / 1000);
      elapsed.value = sec < 60 ? `${sec}s` : `${Math.floor(sec / 60)}m ${sec % 60}s`;
    }, 1000);
  } else {
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
});

onUnmounted(() => {
  if (elapsedTimer) clearInterval(elapsedTimer);
});

function dismissError() {
  detection.error = "";
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  background: transparent;
}

:root {
  font-family: Inter, system-ui, -apple-system, sans-serif;
  font-size: 14px;
  color: #374151;
  background: transparent;
}

.app-shell {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #f3f4f6;
  border-radius: 12px;
}

/* ---- custom header ---- */
.app-header {
  height: 38px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  background: #fafbfc;
  border-bottom: 1px solid #e5e7eb;
  user-select: none;
  flex-shrink: 0;
  border-radius: 12px 12px 0 0;
}

.header-title {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  letter-spacing: 0.3px;
}

.header-controls {
  display: flex;
  gap: 4px;
  -webkit-app-region: no-drag;
}

.win-btn {
  width: 32px;
  height: 24px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.win-btn:hover {
  background: #e5e7eb;
  color: #374151;
}

.win-close:hover {
  background: #ef4444;
  color: #fff;
}

/* ---- app body ---- */
.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ---- sidebar ---- */
.sidebar {
  width: 200px;
  background: #f8f9fb;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-brand {
  padding: 20px 20px 16px;
  font-size: 18px;
  font-weight: 700;
  color: #5b8def;
  letter-spacing: 0.3px;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 10px 12px;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: transparent;
  border: none;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.15s ease;
  text-align: left;
  width: 100%;
}

.nav-btn:hover {
  background: #eef1f5;
  color: #374151;
}

.nav-btn.active {
  background: #e8f0fe;
  color: #5b8def;
}

.nav-icon {
  font-size: 15px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

/* ---- main ---- */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f3f4f6;
}

.view-host {
  flex: 1;
  overflow: hidden;
}

/* ---- footer ---- */
.app-footer {
  height: 34px;
  background: #fafbfc;
  border-top: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  border-radius: 0 0 12px 12px;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.footer-right {
  display: flex;
  align-items: center;
}

.footer-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 8px;
  white-space: nowrap;
  max-width: 480px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.footer-badge.idle {
  background: #f3f4f6;
  color: #9ca3af;
}

.footer-badge.loading {
  background: #fef3c7;
  color: #b45309;
}

.footer-badge.ready {
  background: #d1fae5;
  color: #065f46;
}

.footer-badge.error {
  background: #fee2e2;
  color: #991b1b;
}

.footer-mode {
  font-size: 10px;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.footer-spinner {
  display: inline-block;
  width: 13px;
  height: 13px;
  border: 2px solid #fde68a;
  border-top-color: #d97706;
  border-radius: 50%;
  animation: footer-spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes footer-spin {
  to { transform: rotate(360deg); }
}

.footer-dismiss {
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  font-size: 14px;
  padding: 0 4px;
  line-height: 1;
}
.footer-dismiss:hover {
  color: #ef4444;
}

.footer-version {
  font-size: 10px;
  color: #d1d5db;
}
</style>
