"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

const THEME_STORAGE_KEY = "election-news-theme";

const applyTheme = (theme: Theme) => {
  document.documentElement.classList.toggle("dark", theme === "dark");
};

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    const nextTheme: Theme = savedTheme === "dark" ? "dark" : "light";

    setTheme(nextTheme);
    applyTheme(nextTheme);
    setIsReady(true);
  }, []);

  const toggleTheme = () => {
    const nextTheme: Theme = theme === "dark" ? "light" : "dark";

    setTheme(nextTheme);
    applyTheme(nextTheme);
    window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
  };

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="rounded-full border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-blue-400 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:border-violet-300 dark:hover:text-violet-100 dark:focus:ring-violet-300"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {isReady && theme === "dark" ? "Light" : "Dark"}
    </button>
  );
}
