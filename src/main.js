import { createApp } from "vue";
import { createPinia } from "pinia";
import i18n from "./i18n";
import App from "./App.vue";
import router from "./router";

const app = createApp(App);

app.config.errorHandler = (err, _vm, info) => {
  console.error("Vue error:", err, info);
  const el = document.getElementById("app");
  if (el) {
    el.innerHTML = `<div style="padding:40px;color:red;font-family:monospace;">
      <h2>App Error</h2><pre>${err}</pre><p>${info}</p></div>`;
  }
};

app.use(createPinia());
app.use(router);
app.use(i18n);
app.mount("#app");
