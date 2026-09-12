export type Theme = "dark" | "light";

const STORAGE_KEY = "educa_theme";

export function getStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // localStorage unavailable -- theme still applies for this load, just won't persist
  }
}

// Called once from main.tsx before React mounts, so there's no flash of the
// wrong theme on load.
export function initTheme() {
  applyTheme(getStoredTheme());
}
