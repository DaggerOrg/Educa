import { useEffect, useState } from "react";

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

// Reactive read of the current theme -- watches <html data-theme> rather
// than depending on ThemeToggle's own local state, so any component that
// needs to branch on light/dark (e.g. the chat drawer forcing CopilotKit's
// `dark` ancestor class only when Studio is actually dark) stays in sync
// with the toggle without prop-drilling.
export function useTheme(): Theme {
  const [theme, setTheme] = useState<Theme>(getStoredTheme);
  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(getStoredTheme()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);
  return theme;
}
