<script setup>
import { useRouter, useRoute } from "vue-router";
import { computed } from "vue";
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
</script>

<template>
  <div class="app-shell">
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
      <div class="sidebar-footer">
        <div v-if="detection.isLoading" class="status-badge loading">
          Processing...
        </div>
        <div v-else-if="hasResult" class="status-badge ready">
          Result ready
        </div>
      </div>
    </aside>

    <main class="main-content">
      <router-view />
    </main>
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
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

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
  padding: 0 12px;
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

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.status-badge {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 12px;
  text-align: center;
}

.status-badge.loading {
  background: rgba(255, 193, 7, 0.15);
  color: #ffc107;
}

.status-badge.ready {
  background: rgba(76, 175, 80, 0.15);
  color: #4caf50;
}

.main-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
