(function () {
  "use strict";

  var STORAGE_KEY = "smartmeds-theme";
  var DEFAULT_THEME = "teal-orange";
  var THEMES = ["teal-orange", "noir-gold", "midnight-crimson"];

  function normalizeTheme(theme) {
    return THEMES.indexOf(theme) !== -1 ? theme : DEFAULT_THEME;
  }

  function currentTheme() {
    return normalizeTheme(document.documentElement.dataset.theme);
  }

  function syncPicker(theme) {
    document.querySelectorAll("[data-theme-picker]").forEach(function (picker) {
      if (picker.value !== theme) {
        picker.value = theme;
      }
    });
  }

  function applyTheme(theme) {
    var nextTheme = normalizeTheme(theme);
    document.documentElement.dataset.theme = nextTheme;
    syncPicker(nextTheme);
    return nextTheme;
  }

  function saveTheme(theme) {
    var nextTheme = applyTheme(theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, nextTheme);
    } catch (error) {}
    return nextTheme;
  }

  function initPicker() {
    document.querySelectorAll("[data-theme-picker]").forEach(function (picker) {
      picker.value = currentTheme();
      picker.addEventListener("change", function () {
        saveTheme(picker.value);
      });
    });
  }

  var savedTheme = DEFAULT_THEME;
  try {
    savedTheme = normalizeTheme(window.localStorage.getItem(STORAGE_KEY));
  } catch (error) {}

  applyTheme(savedTheme);

  window.setSmartMedsTheme = saveTheme;
  window.getSmartMedsTheme = currentTheme;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPicker);
  } else {
    initPicker();
  }
})();
