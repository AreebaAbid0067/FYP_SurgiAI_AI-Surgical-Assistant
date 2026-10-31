"use client";

import { useCallback, useEffect, useState } from "react";

export type Settings = {
  theme: "light" | "dark" | "system";
  textSize: "normal" | "large" | "xlarge";
  voiceLang: string;
  speechRate: number;
  autoRead: boolean;
};

export const DEFAULT_SETTINGS: Settings = {
  theme: "light",
  textSize: "normal",
  voiceLang: "en-US",
  speechRate: 1,
  autoRead: true,
};

const KEY = "surgiai_settings";
const SIZES = { normal: "16px", large: "18px", xlarge: "20px" } as const;

export function loadSettings(): Settings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(KEY) ?? "{}") };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function applySettings(settings: Settings) {
  const dark =
    settings.theme === "dark" ||
    (settings.theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
  document.documentElement.style.fontSize = SIZES[settings.textSize];
}

export function useSettings() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  useEffect(() => setSettings(loadSettings()), []);

  const update = useCallback((changes: Partial<Settings>) => {
    setSettings((previous) => {
      const next = { ...previous, ...changes };
      localStorage.setItem(KEY, JSON.stringify(next));
      applySettings(next);
      return next;
    });
  }, []);

  return { settings, update };
}

// Inline script run before first paint so the saved theme never flashes.
export const NO_FLASH_SCRIPT = `try{var s=JSON.parse(localStorage.getItem("${KEY}")||"{}");var d=s.theme==="dark"||(s.theme==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);if(d)document.documentElement.classList.add("dark");var z={normal:"16px",large:"18px",xlarge:"20px"}[s.textSize];if(z)document.documentElement.style.fontSize=z}catch(e){}`;
