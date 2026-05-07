import { createI18n } from "vue-i18n";
import en from "./en.json";
import zh from "./zh.json";

const saved = localStorage.getItem("locale") || "en";

const i18n = createI18n({
  legacy: false,
  locale: saved,
  fallbackLocale: "en",
  messages: { en, zh },
});

export default i18n;

export function t(key, params) {
  return i18n.global.t(key, params);
}

export function translateClassName(enName) {
  return i18n.global.t(`classes.${enName}`);
}
