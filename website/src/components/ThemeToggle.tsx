import { useState } from "react";
import { applyTheme, getStoredTheme } from "../theme.ts";

export default function ThemeToggle() {
  const [theme, setTheme] = useState(getStoredTheme);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    applyTheme(next);
    setTheme(next);
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    >
      {theme === "dark" ? (
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <circle cx="10" cy="10" r="3.4" />
          <path d="M10 2.6v2M10 15.4v2M17.4 10h-2M4.6 10h-2M15.1 4.9l-1.4 1.4M6.3 13.7l-1.4 1.4M15.1 15.1l-1.4-1.4M6.3 6.3 4.9 4.9" />
        </svg>
      ) : (
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16.5 12.3A6.8 6.8 0 1 1 7.7 3.5a5.3 5.3 0 0 0 8.8 8.8Z" />
        </svg>
      )}
    </button>
  );
}
