import { useState } from "react";
import { applyTheme, getStoredTheme } from "../theme.ts";
import { IconMoon, IconSun } from "./icons.tsx";

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
      className="btn theme-toggle"
      onClick={toggle}
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    >
      {theme === "dark" ? <IconSun /> : <IconMoon />}
    </button>
  );
}
