import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import fr from "./locales/fr.json";

// Read language from shell (when loaded as MFE) or localStorage (standalone)
function getLanguage(): string {
  const shellLang = (window as unknown as Record<string, unknown>).__SHELL_LANGUAGE__ as string | undefined;
  if (shellLang) return shellLang;
  return localStorage.getItem("language") || "en";
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fr: { translation: fr },
  },
  lng: getLanguage(),
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

// Listen for shell language changes (when loaded as MFE)
window.addEventListener("shell-language-change", ((event: CustomEvent) => {
  i18n.changeLanguage(event.detail);
}) as EventListener);

export default i18n;
