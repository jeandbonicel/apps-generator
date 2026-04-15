import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import fr from "./locales/fr.json";

const STORAGE_KEY = "{{ projectName }}_language";

const savedLang = localStorage.getItem(STORAGE_KEY) || "en";

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fr: { translation: fr },
  },
  lng: savedLang,
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

// Sync language to localStorage and to MFEs via window global
i18n.on("languageChanged", (lng) => {
  localStorage.setItem(STORAGE_KEY, lng);
  (window as unknown as Record<string, unknown>).__SHELL_LANGUAGE__ = lng;
  window.dispatchEvent(new CustomEvent("shell-language-change", { detail: lng }));
});

// Set initial value for MFEs
(window as unknown as Record<string, unknown>).__SHELL_LANGUAGE__ = savedLang;

export default i18n;
