import { createContext, useContext } from 'react';
import { useState, useEffect, useCallback } from 'react';
type Theme = 'dark' | 'light';

interface ThemeValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeValue>({ theme: 'dark', toggleTheme: () => {} });

export function ThemeProvider({ children }: {children: React.ReactNode;}) {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === 'undefined') return 'dark';
    return window.localStorage.getItem('sentinel-theme') as Theme ?? 'dark';
  });

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', theme === 'dark');
    root.classList.toggle('light', theme === 'light');
    root.style.colorScheme = theme;
    window.localStorage.setItem('sentinel-theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(
    () => setTheme((t) => t === 'dark' ? 'light' : 'dark'),
    []
  );

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>);

}

export function useTheme(): ThemeValue {
  return useContext(ThemeContext);
}