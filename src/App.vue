<script setup>
import { ref, watch, onUnmounted, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDetectionStore } from "./stores/detection";

const router = useRouter();
const route = useRoute();
const detection = useDetectionStore();

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

<template>
  <div class="app-shell">
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
        <span class="footer-version">MarineXt v1.0</span>
      </div>
    </footer>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  font-family: Inter, Avenir, Helvetica, Arial, sans-serif;
  font-size: 14px;
  color: #333;
  background: #f0f2f5;
}

.app-shell {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ---- sidebar ---- */
.sidebar {
  width: 200px;
  background: #1a1a2e;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-brand {
  padding: 24px 20px;
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
  letter-spacing: 0.5px;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px 12px;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: transparent;
  border: none;
  color: #a0a0b8;
  font-size: 14px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.15s ease;
  text-align: left;
  width: 100%;
}

.nav-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #e0e0e0;
}

.nav-btn.active {
  background: rgba(64, 158, 255, 0.15);
  color: #409eff;
}

.nav-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
}

/* ---- main ---- */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.view-host {
  flex: 1;
  overflow: hidden;
}

/* ---- unified footer ---- */
.app-footer {
  height: 36px;
  background: #1a1a2e;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
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
  padding: 4px 10px;
  border-radius: 10px;
  white-space: nowrap;
  max-width: 480px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.footer-badge.idle {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.3);
}

.footer-badge.loading {
  background: rgba(255, 193, 7, 0.12);
  color: #ffc107;
}

.footer-badge.ready {
  background: rgba(76, 175, 80, 0.12);
  color: #4caf50;
}

.footer-badge.error {
  background: rgba(231, 76, 60, 0.12);
  color: #e74c3c;
}

.footer-mode {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.footer-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 193, 7, 0.2);
  border-top-color: #ffc107;
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
  color: rgba(255, 255, 255, 0.3);
  cursor: pointer;
  font-size: 14px;
  padding: 0 4px;
  line-height: 1;
}
.footer-dismiss:hover {
  color: #e74c3c;
}

.footer-version {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.2);
}
</style>
