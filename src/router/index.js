import { createRouter, createWebHashHistory } from "vue-router";
import HomePage from "../views/HomePage.vue";
import DetectPage from "../views/DetectPage.vue";
import ContrastPage from "../views/ContrastPage.vue";
import ChartsPage from "../views/ChartsPage.vue";
import ReportPage from "../views/ReportPage.vue";
import HistoryPage from "../views/HistoryPage.vue";

const routes = [
  { path: "/", name: "home", component: HomePage },
  { path: "/detect", name: "detect", component: DetectPage },
  { path: "/contrast", name: "contrast", component: ContrastPage },
  { path: "/charts", name: "charts", component: ChartsPage },
  { path: "/report", name: "report", component: ReportPage },
  { path: "/history", name: "history", component: HistoryPage },
];

export default createRouter({
  history: createWebHashHistory(),
  routes,
});
