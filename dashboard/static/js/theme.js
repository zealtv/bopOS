(function () {
  "use strict";

  const storageKey = "bopos-theme";
  const media = window.matchMedia("(prefers-color-scheme: light)");

  function storedPreference() {
    try {
      const value = localStorage.getItem(storageKey);
      return value === "light" || value === "dark" ? value : "system";
    } catch (_error) {
      return "system";
    }
  }

  function effectiveTheme(preference) {
    return preference === "system" ? (media.matches ? "light" : "dark") : preference;
  }

  function applyTheme(preference) {
    const theme = effectiveTheme(preference);
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.themePreference = preference;
    root.style.colorScheme = theme;
    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.content = theme === "light" ? "#f4f1f8" : "#101316";
    const control = document.querySelector("#theme-select");
    if (control && control.value !== preference) control.value = preference;
  }

  function savePreference(preference) {
    try {
      if (preference === "system") localStorage.removeItem(storageKey);
      else localStorage.setItem(storageKey, preference);
    } catch (_error) {
      // Theme selection still works for this page when storage is unavailable.
    }
    applyTheme(preference);
  }

  const initialPreference = storedPreference();
  applyTheme(initialPreference);

  document.addEventListener("DOMContentLoaded", function () {
    const control = document.querySelector("#theme-select");
    if (!control) return;
    control.value = storedPreference();
    control.addEventListener("change", function () { savePreference(control.value); });
  });

  media.addEventListener("change", function () {
    if (storedPreference() === "system") applyTheme("system");
  });

  window.addEventListener("storage", function (event) {
    if (event.key === storageKey) applyTheme(storedPreference());
  });
})();
