'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light');

  useEffect(() => {
    // Load initial theme from backend or localStorage
    const loadTheme = async () => {
      try {
        const res = await fetch('http://localhost:8000/settings');
        if (res.ok) {
          const settings = await res.json();
          const initialTheme = settings.dark_mode ? 'dark' : 'light';
          setTheme(initialTheme);
          document.documentElement.classList.toggle('dark', settings.dark_mode);
        }
      } catch (err) {
        console.error("Failed to load theme from backend", err);
      }
    };
    loadTheme();
  }, []);

  const toggleTheme = async () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    const isDark = newTheme === 'dark';
    document.documentElement.classList.toggle('dark', isDark);

    // Sync with backend
    try {
      await fetch('http://localhost:8000/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dark_mode: isDark }),
      });
    } catch (err) {
      console.error("Failed to sync theme with backend", err);
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within a ThemeProvider');
  return context;
};
